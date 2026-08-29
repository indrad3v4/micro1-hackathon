"""Creator agent — brief -> fan of creative directions across ИКРА frames.

Every step is recorded to the trajectory. LLM-backed when a key is present,
heuristic fallback otherwise (keeps the pipeline runnable offline).
"""
from __future__ import annotations

import json
import os
import re

from ..core.models import Brief, Direction
from ..core.trace import TraceRecorder
from ..core.llm import LLMClient, FRAMES, heuristic_directions, load_prompt

# Load improved prompt from disk
# Resolve prompts: repo root has prompts/ (creative-court/prompts does not exist).
# Try several candidate dirs so the package works from any CWD / deployment.
_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "prompts"),
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "prompts"),
    os.path.join(os.path.dirname(__file__), "..", "..", "prompts"),
]
_PROMPTS_DIR = next((p for p in _CANDIDATES
                     if os.path.isfile(os.path.join(p, "creator_prompt.txt"))),
                    _CANDIDATES[0])
_CREATOR_SYSTEM = load_prompt(os.path.join(_PROMPTS_DIR, "creator_prompt.txt"))


class CreatorAgent:
    def __init__(self, recorder: TraceRecorder, llm: LLMClient | None = None):
        self.recorder = recorder
        self.llm = llm or LLMClient()

    def generate(self, brief: Brief, rework: dict | None = None) -> list[Direction]:
        """Generate creative directions.

        rework: optional {direction_id, reason} — the human vetoed one direction
        and wants THAT direction reworked to address the reason (brand-champion
        rule: the human's signature re-enters the work). When present, the
        rework reason is injected as a hard requirement for the target frame.
        """
        agent = "creator"
        self.recorder.event(
            agent=agent, type="agent_start",
            instruction=f"Generate creative directions for brief: {brief.title}"
                        + (f" (rework {rework['direction_id']}: {rework['reason']})" if rework else ""),
        )
        if self.llm.available and _CREATOR_SYSTEM:
            try:
                raw = self._build_user_prompt(brief, rework=rework)
                response = self.llm.chat(system=_CREATOR_SYSTEM, user=raw, max_tokens=4096)
                self.recorder.tool_response(agent, "llm", response)
                payload = _parse_json(response)
                directions = [
                    Direction(**{**d, "risks": d.get("risks", [])})
                    for d in payload.get("directions", [])
                ]
            except Exception as exc:
                self.recorder.retry(agent, "llm_generate", f"LLM failed ({exc}); using heuristic")
                directions = [Direction(**d) for d in heuristic_directions(brief)]
        else:
            self.recorder.event(agent=agent, type="agent_step",
                                action="no LLM key — heuristic fallback")
            directions = [Direction(**d) for d in heuristic_directions(brief)]

        for d in directions:
            self.recorder.event(
                agent=agent, type="agent_step",
                action=f"produced direction {d.frame}: {d.name}",
                feedback=d.rationale,
                data={"concept": d.concept, "risks": d.risks},
            )
        self.recorder.event(agent=agent, type="agent_end",
                            action=f"returned {len(directions)} directions")
        return directions

    @staticmethod
    def _build_user_prompt(brief: Brief, rework: dict | None = None) -> str:
        parts = [f"Title: {brief.title}", f"Description: {brief.description}"]
        if brief.audience:
            parts.append(f"Audience: {brief.audience}")
        if brief.goal:
            parts.append(f"Goal: {brief.goal}")
        if brief.constraints:
            parts.append(f"Constraints:\n" + "\n".join(f"- {c}" for c in brief.constraints))
        if rework and rework.get("direction_id") and rework.get("reason"):
            # hard human requirement: rework THE SAME direction to address the reason
            parts.append(
                "REWORK REQUIREMENT (human veto): "
                f"direction '{rework['direction_id']}' was rejected by the human. "
                f"Reason: {rework['reason']}. "
                "Provide a NEW version of THIS direction that resolves the reason "
                "while keeping the same frame. Do not replace it with a different frame."
            )
        return "\n".join(parts)


def _parse_json(raw: str) -> dict:
    """Extract JSON from LLM output, stripping markdown fences if present."""
    cleaned = raw.strip()
    m = re.search(r"```(?:json)?\s*\n(.*?)\n```\s*$", cleaned, re.DOTALL)
    if m:
        cleaned = m.group(1).strip()
    # Try full parse first, then bracket-fallback
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    m2 = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not m2:
        raise ValueError("no JSON object in LLM output")
    return json.loads(m2.group(0))
