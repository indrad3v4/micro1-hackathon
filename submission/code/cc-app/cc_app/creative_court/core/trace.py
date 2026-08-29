"""Trajectory recorder — append-only JSONL with atomic writes.

Every agent action lands here. This is BOTH the submission requirement
(micro1: "submit the required trajectories") and the sellable asset
(trace acquisition $2-15/trace, cap $100-200).
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Optional

from .models import TraceEvent


class TraceRecorder:
    """Thread-safe append-only JSONL trajectory store.

    Usage:
        rec = TraceRecorder("traces/run_001.jsonl")
        rec.event(agent="creator", type=EVENT_AGENT_STEP, action="...", feedback="...")
        # or the helpers:
        rec.tool_call(agent, tool, instruction)
        rec.tool_response(agent, tool, output)
        rec.human_checkpoint(agent, note)
        rec.veto(agent, direction, reason)
        rec.retry(agent, retry_of, reason)
    """

    def __init__(self, path: str, meta: Optional[dict] = None):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._lock = threading.Lock()
        self._fh = open(path, "a", encoding="utf-8")
        if meta:
            self.event(agent="harness", type="agent_start", data={"meta": meta})

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

    def event(self, *, agent: str, type: str, instruction: Optional[str] = None,
              action: Optional[str] = None, tool: Optional[str] = None,
              tool_response: Optional[str] = None, feedback: Optional[str] = None,
              retry_of: Optional[str] = None, human_checkpoint: Optional[str] = None,
              verdict: Optional[str] = None, data: Optional[dict] = None) -> None:
        ev = TraceEvent(
            ts=self._now(), agent=agent, type=type, instruction=instruction,
            action=action, tool=tool, tool_response=tool_response,
            feedback=feedback, retry_of=retry_of,
            human_checkpoint=human_checkpoint, verdict=verdict,
            data=data or {},
        )
        line = json.dumps(ev.to_dict(), ensure_ascii=False)
        with self._lock:
            self._fh.write(line + "\n")
            self._fh.flush()
            os.fsync(self._fh.fileno())

    # --- convenience helpers ---
    def tool_call(self, agent: str, tool: str, instruction: str, action: str = "") -> None:
        self.event(agent=agent, type="tool_call", tool=tool, instruction=instruction, action=action)

    def tool_response(self, agent: str, tool: str, output: str) -> None:
        # truncate huge tool outputs to keep files small; full evidence kept separately
        if len(output) > 4000:
            output = output[:4000] + f"\n...[truncated, total {len(output)} chars]"
        self.event(agent=agent, type="tool_response", tool=tool, tool_response=output)

    def human_checkpoint(self, agent: str, note: str) -> None:
        self.event(agent=agent, type="human_checkpoint", human_checkpoint=note)

    def veto(self, agent: str, target: str, reason: str) -> None:
        self.event(agent=agent, type="veto", action=target, feedback=reason)

    def retry(self, agent: str, retry_of: str, reason: str) -> None:
        self.event(agent=agent, type="retry", retry_of=retry_of, feedback=reason)

    def close(self) -> None:
        with self._lock:
            self._fh.close()

    def __enter__(self) -> "TraceRecorder":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def read_traces(path: str) -> list[dict]:
    """Read a trajectory file back as a list of events (for tests/exports)."""
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def export_trace_metrics(path: str) -> dict:
    """Count event types — used for the trace-acquisition manifest."""
    events = read_traces(path)
    counts: dict[str, int] = {}
    for ev in events:
        counts[ev["type"]] = counts.get(ev["type"], 0) + 1
    return {
        "path": path,
        "total_events": len(events),
        "by_type": counts,
    }
