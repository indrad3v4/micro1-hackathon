"""Integration tests for Creative Court FastAPI demo."""

import json
import os
import sys
from pathlib import Path

# Ensure creative_court package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Disable LLM so the heuristic fallback always runs
os.environ.pop("COMETAPI_KEY", None)
os.environ.pop("LLM_API_KEY", None)

import pytest
from starlette.testclient import TestClient

# Lazy-load the app to avoid circular import issues
_app = None
_client = None
_trace_dir = None


def _get_app():
    global _app
    if _app is None:
        from app.main import app
        _app = app
    return _app


def _get_client():
    """Create (or reuse) a TestClient instance."""
    global _client, _trace_dir
    app = _get_app()
    if _client is None:
        _trace_dir = Path(app.state.__dict__.get("_trace_dir")
                           or Path("/root/.hermes/micro1-hackathon/creative-court/traces"))
        _client = TestClient(app, raise_server_exceptions=False)
    return _client


def _get_trace_dir():
    global _trace_dir
    if _trace_dir is None:
        _trace_dir = Path("/root/.hermes/micro1-hackathon/creative-court/traces")
    return _trace_dir


def _clean_traces():
    """Clear ALL .jsonl trace files."""
    td = _get_trace_dir()
    if td.exists():
        for f in td.glob("*.jsonl"):
            f.unlink()


@pytest.fixture(autouse=True, scope="session")
def load_app_and_cleanup():
    """Load the app once and clean traces before the test suite starts."""
    _get_app()  # triggers app loading (and lifespan init)
    _clean_traces()
    yield
    _clean_traces()  # cleanup after all tests


class TestHealth:
    def test_health_ok(self):
        client = _get_client()
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert isinstance(data["llm_available"], bool)


class TestDemoEndpoint:
    def test_demo_inline_brief(self):
        client = _get_client()
        r = client.post("/demo", json={
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
        client = _get_client()
        r = client.post("/demo", json={"brief_file": "eval_01_coffee.json"})
        assert r.status_code == 200
        data = r.json()
        assert data["brief"]["title"] == "Умная кофеварка"
        assert data["directions_count"] >= 1

    def test_demo_missing_fields(self):
        client = _get_client()
        r = client.post("/demo", json={"title": "Only title"})
        assert r.status_code == 400

    def test_demo_invalid_brief_file(self):
        client = _get_client()
        r = client.post("/demo", json={"brief_file": "nonexistent.json"})
        assert r.status_code == 404

    def test_verdicts_sorted_descending(self):
        client = _get_client()
        r = client.post("/demo", json={
            "title": "Sort test brief",
            "description": "Testing sort order",
        })
        assert r.status_code == 200
        totals = [v["total"] for v in r.json()["verdicts"]]
        assert totals == sorted(totals, reverse=True)

    def test_trace_recording(self):
        client = _get_client()
        r = client.post("/demo", json={
            "title": "Trace test brief",
            "description": "For tracing API tests",
        })
        assert r.status_code == 200
        data = r.json()
        trace_file = _get_trace_dir() / f"{data['run_identifier']}.jsonl"
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
        # First create a run
        client = _get_client()
        client.post("/demo", json={
            "title": "Trace test brief",
            "description": "For tracing API tests",
        })

        traces = list(_get_trace_dir().glob("run_*.jsonl"))
        assert len(traces) >= 1
        latest = sorted(traces, key=lambda x: x.stat().st_mtime, reverse=True)[0]
        identifier = latest.stem

        client = _get_client()
        r = client.get(f"/traces/run/{identifier}")
        assert r.status_code == 200
        events = r.json()
        assert len(events) > 0
        types_found = {e["type"] for e in events}
        assert "agent_start" in types_found

    def test_get_trace_not_found(self):
        client = _get_client()
        r = client.get("/traces/run/nonexistent_run_xyz_12345")
        assert r.status_code == 404


class TestVetoFlow:
    def test_veto_records_event(self):
        reason = "Too risky for production deployment"

        client = _get_client()
        result = client.post("/demo", json={
            "title": "Veto test brief",
            "description": "Testing veto flow",
        })
        assert result.status_code == 200
        verdicts = result.json()["verdicts"]
        top_direction = verdicts[0]["direction_id"]

        client = _get_client()
        r = client.post("/veto", json={
            "direction_id": top_direction,
            "reason": reason,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "recorded"
        assert data["direction_id"] == top_direction
        assert data["reason"] == reason

        # Verify veto event type appears in the trace
        from creative_court.core.trace import read_traces
        found = False
        for p in _get_trace_dir().glob("*.jsonl"):
            evts = read_traces(str(p))
            if any(e.get("type") == "veto" for e in evts):
                found = True
                break
        assert found, "No 'veto' event type found in any trace"

    def test_veto_unknown_direction(self):
        client = _get_client()
        r = client.post("/veto", json={
            "direction_id": "ritual:GhostDirectionThatDoesNotExist999",
            "reason": "Should fail",
        })
        assert r.status_code == 404


class TestExportAndListRuns:
    def test_export_all_traces(self):
        # Run demos first to populate traces
        client = _get_client()
        client.post("/demo", json={"title": "Export test 1", "description": "First"})

        client = _get_client()
        r = client.get("/api/traces/export", params={"limit": 10})
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
        client = _get_client()
        client.post("/demo", json={"title": "Run list test", "description": "Test"})

        client = _get_client()
        r = client.get("/api/runs")
        assert r.status_code == 200
        data = r.json()
        assert "runs" in data
        assert len(data["runs"]) >= 1
