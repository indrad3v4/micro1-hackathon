"""Smoke tests: pipeline runs offline, trajectories are recorded correctly."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from creative_court.core.models import Brief
from creative_court.core.trace import TraceRecorder, read_traces, export_trace_metrics
from creative_court.agents.creator import CreatorAgent
from creative_court.agents.judge import JudgeAgent


def test_full_pipeline():
    os.environ.pop("COMETAPI_KEY", None)  # force heuristic fallback
    with tempfile.TemporaryDirectory() as tmp:
        trace_path = os.path.join(tmp, "run.jsonl")
        brief = Brief(title="Test brief", description="A widget for busy people",
                      audience="testers")
        with TraceRecorder(trace_path) as rec:
            judge = JudgeAgent(rec)
            directions = CreatorAgent(rec).generate(brief)
            verdicts = judge.judge(brief, directions)
            judge.veto(verdicts[0], "too risky")

        assert len(directions) == 6, f"expected 6 directions, got {len(directions)}"
        assert len(verdicts) == 6
        assert verdicts[0].total >= verdicts[-1].total  # sorted desc
        assert verdicts[0].vetoed is True

        events = read_traces(trace_path)
        types = {e["type"] for e in events}
        assert "agent_start" in types and "agent_end" in types
        assert "veto" in types
        assert any(e["type"] == "tool_response" for e in events) is False  # no LLM key

        m = export_trace_metrics(trace_path)
        assert m["total_events"] == len(events)
        print("test_full_pipeline OK:", m["by_type"])


def test_trace_truncation():
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "t.jsonl")
        with TraceRecorder(p) as rec:
            rec.tool_response("codex", "bash", "x" * 10000)
        events = read_traces(p)
        body = events[0]["tool_response"]
        assert len(body) < 4500, f"expected truncation, got {len(body)}"
        print("test_trace_truncation OK")


if __name__ == "__main__":
    test_full_pipeline()
    test_trace_truncation()
    print("ALL TESTS PASSED")
