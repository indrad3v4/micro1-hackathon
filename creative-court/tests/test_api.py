"""Integration tests for Creative Court FastAPI demo."""

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

# Ensure the creative_court package is importable
_COURT_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_COURT_SRC) not in sys.path:
    sys.path.insert(0, str(_COURT_SRC))

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

BASE_URL = os.environ.get("APP_BASE_URL", "http://127.0.0.1:8000")

# Force heuristic mode (no LLM calls)
os.environ.pop("COMETAPI_KEY", None)
os.environ.pop("LLM_API_KEY", None)


@pytest.fixture(scope="session", autouse=True)
def clean_traces_dir():
    """Wipe traces/ before tests so we start fresh."""
    traces_dir = _PROJECT_ROOT / "traces"
    if traces_dir.exists():
        for f in traces_dir.glob("*.jsonl"):
            f.unlink()


@pytest.fixture(scope="session")
def client():
    """Create an httpx TestClient pointing at the running server."""
    from app.main import app
    with httpx.Client(app=app, base_url="http://test") as c:
        yield c


@pytest.mark.integration
class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert isinstance(data["llm_available"], bool)


@pytest.mark.integration
class TestDemoEndpoint:
    def test_demo_inline_brief(self, client):
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
        assert len(data["verdicts"]) > 0
        # Each verdict has all rubric scores
        for v in data["verdicts"]:
            assert "total" in v
            assert "scores" in v
            assert len(v["scores"]) > 0
            assert v["approved"] is not None
            assert "summary" in v
        # Check events structure
        assert isinstance(data["events"], dict)
        assert "agent_start" in data["events"] or "agent_end" in data["events"]

    def test_demo_from_file(self, client):
        r = client.post("/demo", json={
            "brief_file": "eval_01_coffee.json",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["brief"]["title"] == "Умная кофеварка"
        assert data["directions_count"] >= 1

    def test_demo_missing_fields(self, client):
        r = client.post("/demo", json={"title": "Only title"})
        assert r.status_code == 400

    def test_demo_invalid_brief_file(self, client):
        r = client.post("/demo", json={"brief_file": "nonexistent.json"})
        assert r.status_code == 404

    def test_verdicts_sorted_descending(self, client):
        r = client.post("/demo", json={
            "title": "Sort test",
            "description": "Testing sort order",
        })
        assert r.status_code == 200
        total_scores = [v["total"] for v in r.json()["verdicts"]]
        assert total_scores == sorted(total_scores, reverse=True)

    def test_rubric_dimensions_present(self, client):
        r = client.post("/demo", json={
            "title": "Dimension check",
            "description": "Verify rubric dimensions",
        })
        assert r.status_code == 200
        dim_sets = {tuple(s["dimension"] for s in v["scores"]) for v in r.json()["verdicts"]}
        expected = {"relevance", "novelty", "feasibility", "risk", "quality"}
        # All verdicts should have the same set of dimensions
        for dims in dim_sets:
            assert set(dims) == expected


@pytest.mark.integration
class TestTracesEndpoint:
    def setup_method(self):
        """Run a demo first so there's something to query."""
        from app.main import app
        with httpx.Client(app=app, base_url="http://test") as c:
            c.post("/demo", json={
                "title": "Trace test brief",
                "description": "For tracing API tests",
            })

    def test_get_trace_by_identifier(self, client):
        r = client.get("/traces/run/run_")
        assert r.status_code == 200
        events = r.json()
        assert len(events) > 0
        types_found = {e["type"] for e in events}
        assert "agent_start" in types_found

    def test_get_trace_not_found(self, client):
        r = client.get("/traces/run/nonexistent_run_xyz")
        assert r.status_code == 404


@pytest.mark.integration
class TestVetoFlow:
    def test_veto_records_event(self, client):
        # First run a pipeline
        from app.main import app
        with httpx.Client(app=app, base_url="http://test") as c:
            result = c.post("/demo", json={
                "title": "Veto test brief",
                "description": "Testing veto flow",
            })
            verdicts = result.json()["verdicts"]
            top_direction = verdicts[0]["direction_id"]

        # Now veto it via the API
        r = client.post("/veto", json={
            "direction_id": top_direction,
            "reason": "Too risky for production deployment",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "recorded"
        assert data["direction_id"] == top_direction
        assert data["reason"] == "Too risky for production deployment"
        # Recent events should include veto-related ones
        recent = data.get("recent_events", [])
        actions_and_feedbacks = [str(e.get("action", "")) + str(e.get("feedback", "")) for e in recent]
        found_veto = any("Too risky" in s for s in actions_and_feedbacks)
        assert found_veto, f"No veto reason found in recent events: {recent}"

    def test_veto_unknown_direction(self, client):
        r = client.post("/veto", json={
            "direction_id": "ritual:GhostDirectionThatDoesNotExist",
            "reason": "Should fail",
        })
        assert r.status_code == 404


@pytest.mark.integration
class TestExportAndListRuns:
    def test_export_all_traces(self, client):
        # Run a couple demos first
        from app.main import app
        with httpx.Client(app=app, base_url="http://test") as c:
            c.post("/demo", json={"title": "Export test 1", "description": "First"})
            c.post("/demo", json={"title": "Export test 2", "description": "Second"})

        r = client.get("/api/traces/export", params={"limit": 10})
        assert r.status_code == 200
        # Content type should be JSONL
        assert "application/x-jsonlines" in r.headers.get("content-type", "")
        assert "Content-Disposition" in r.headers
        lines = [l for l in r.text.strip().split("\n") if l.strip()]
        assert len(lines) >= 1
        # Each line should be valid JSON
        for line in lines:
            json.loads(line)

    def test_list_runs(self, client):
        r = client.get("/api/runs")
        assert r.status_code == 200
        data = r.json()
        assert "runs" in data
        runs = data["runs"]
        assert len(runs) > 0
        # At least one run should exist from other tests
        found = any(len(run["events"].values()) > 0 for run in runs)
        assert found
