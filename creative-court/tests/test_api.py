"""Integration tests for Creative Court FastAPI demo."""

import json
import os
import sys
from pathlib import Path

# Ensure creative_court package is importable
sys.path.insert(0, "/root/.hermes/micro1-hackathon/creative-court/src")
sys.path.insert(0, "/root/.hermes/micro1-hackathon/creative-court")

os.environ.pop("COMETAPI_KEY", None)
os.environ.pop("LLM_API_KEY", None)

import pytest
from starlette.testclient import TestClient

TRACE_DIR = Path("/root/.hermes/micro1-hackathon/creative-court/traces")


def _get_client():
    """Create a fresh TestClient."""
    return TestClient(app, raise_server_exceptions=False)


def _load_app():
    """Lazy-load app on first use."""
    global app
    if '_APP_LOADED' not in globals():
        from app.main import app as _app
        from app.main import TRACE_DIR as _TD
        global app, TRACE_DIR
        app = _app
        TRACE_DIR = _TD
        globals()['_APP_LOADED'] = True


def _clean_traces():
    """Clear ALL trace files."""
    _load_app()
    if TRACE_DIR.exists():
        for f in TRACE_DIR.glob("*.jsonl"):
            f.unlink()


@pytest.fixture(autouse=True)
def clean_before_test():
    """Clear traces before each test."""
    _clean_traces()
    yield
    _clean_traces()  # cleanup after


class TestHealth:
    def test_health_ok(self):
        with _get_client() as c:
            r = c.get("/health")
            assert r.status_code == 200
            data = r.json()
            assert data["status"] == "ok"
            assert "version" in data
            assert isinstance(data["llm_available"], bool)


class TestDemoEndpoint:
    def test_demo_inline_brief(self):
        with _get_client() as c:
            r = c.post("/demo", json={
                "title": "Test Coffee Maker",
                "description": "A smart coffee maker for busy professionals",
                "audience": "urban workers 25-40",
                "goal": "turn morning coffee into a ritual",
                "constraints": ["works without smartphone"],
            })
            assert r.status_code == 200
            data = r.json()
            assert data["brief"]["title"] == "Test Coffee Maker"
            assert data["directions_count"] > 0
            assert len(data["verdicts"]) >= 6

            expected_dims = {"relevance", "novelty", "feasibility", "risk", "quality"}
            for v in data["verdicts"]:
                assert "total" in v
                assert 0 < v["total"] <= 100
                assert "scores" in v
                assert len(v["scores"]) == 5
                dims = {s["dimension"] for s in v["scores"]}
                assert dims == expected_dims
                assert "summary" in v
                assert isinstance(v["approved"], bool)

    def test_demo_from_file(self):
        with _get_client() as c:
            r = c.post("/demo", json={"brief_file": "eval_01_coffee.json"})
            assert r.status_code == 200
            data = r.json()
            assert data["brief"]["title"] == "Умная кофеварка"
            assert data["directions_count"] >= 1

    def test_demo_missing_fields(self):
        with _get_client() as c:
            r = c.post("/demo", json={"title": "Only title"})
            assert r.status_code == 400

    def test_demo_invalid_brief_file(self):
        with _get_client() as c:
            r = c.post("/demo", json={"brief_file": "nonexistent.json"})
            assert r.status_code == 404

    def test_verdicts_sorted_descending(self):
        with _get_client() as c:
            r = c.post("/demo", json={
                "title": "Sort test brief",
                "description": "Testing sort order",
            })
            assert r.status_code == 200
            totals = [v["total"] for v in r.json()["verdicts"]]
            assert totals == sorted(totals, reverse=True)

    def test_trace_recording(self):
        with _get_client() as c:
            r = c.post("/demo", json={
                "title": "Trace test brief",
                "description": "For tracing API tests",
            })
            assert r.status_code == 200
            data = r.json()
            trace_file = TRACE_DIR / f"{data['run_identifier']}.jsonl"
            assert trace_file.is_file(), f"Trace not found: {trace_file}"

        from creative_court.core.trace import read_traces
        events = read_traces(str(trace_file))
        types = {e["type"] for e in events}
        assert "agent_start" in types
        assert "agent_end" in types
        judge_events = [e for e in events if e.get("agent") == "judge"]
        assert len(judge_events) > 0


class TestTracesEndpoint:
    def test_get_trace_by_identifier(self):
        with _get_client() as c:
            c.post("/demo", json={
                "title": "Trace test brief",
                "description": "For tracing API tests",
            })

        _load_app()
        traces = list(TRACE_DIR.glob("run_*.jsonl"))
        assert len(traces) >= 1
        latest = sorted(traces, key=lambda x: x.stat().st_mtime, reverse=True)[0]
        identifier = latest.stem

        with _get_client() as c:
            r = c.get(f"/traces/run/{identifier}")
            assert r.status_code == 200
            events = r.json()
            assert len(events) > 0
            types_found = {e["type"] for e in events}
            assert "agent_start" in types_found

    def test_get_trace_not_found(self):
        with _get_client() as c:
            r = c.get("/traces/run/nonexistent_run_xyz_12345")
            assert r.status_code == 404


class TestVetoFlow:
    def test_veto_records_event(self):
        reason = "Too risky for production deployment"

        with _get_client() as c:
            result = c.post("/demo", json={
                "title": "Veto test brief",
                "description": "Testing veto flow",
            })
            assert result.status_code == 200
            verdicts = result.json()["verdicts"]
            top_direction = verdicts[0]["direction_id"]

        with _get_client() as c:
            r = c.post("/veto", json={
                "direction_id": top_direction,
                "reason": reason,
            })
            assert r.status_code == 200
            data = r.json()
            assert data["status"] == "recorded"
            assert data["direction_id"] == top_direction
            assert data["reason"] == reason

        # Verify veto is in trace
        from creative_court.core.trace import read_traces
        found = False
        for p in TRACE_DIR.glob("*.jsonl"):
            evts = read_traces(str(p))
            if any(reason in str(e.get('feedback', '')) or
                   reason in str(e.get('action', '')) or
                   reason in str(e.get('tool_response', '') or '')
                   for e in evts):
                found = True
                break
        assert found, f"Veto reason '{reason}' not found in any trace"

    def test_veto_unknown_direction(self):
        with _get_client() as c:
            r = c.post("/veto", json={
                "direction_id": "ritual:GhostDirectionThatDoesNotExist999",
                "reason": "Should fail",
            })
            assert r.status_code == 404


class TestExportAndListRuns:
    def test_export_all_traces(self):
        # Run demos first
        with _get_client() as c:
            c.post("/demo", json={"title": "Export test 1", "description": "First"})

        _load_app()
        with _get_client() as c:
            r = c.get("/api/traces/export", params={"limit": 10})
            assert r.status_code == 200
            ct = r.headers.get("content-type", "")
            assert "application/x-jsonlines" in ct
            assert "Content-Disposition" in r.headers
            lines = [l for l in r.text.strip().split("\n") if l.strip()]
            assert len(lines) >= 1
            for line in lines:
                json.loads(line)

    def test_list_runs(self):
        # Create at least one run
        with _get_client() as c:
            c.post("/demo", json={"title": "Run list test", "description": "Test"})

        _load_app()
        with _get_client() as c:
            r = c.get("/api/runs")
            assert r.status_code == 200
            data = r.json()
            assert "runs" in data
            assert len(data["runs"]) >= 1
