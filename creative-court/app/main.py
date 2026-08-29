"""FastAPI application for Creative Court — agent harness with trajectory recording."""

import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Make sure creative_court package is importable — works both locally and in Docker
_LOCAL_ROOT = Path("/root/.hermes/micro1-hackathon/creative-court")
_DOCKER_ROOT = Path("/app")

if _LOCAL_ROOT.is_dir() and (_LOCAL_ROOT / "src" / "creative_court").is_dir():
    _ROOT = _LOCAL_ROOT
elif _DOCKER_ROOT.is_dir() and (_DOCKER_ROOT / "src" / "creative_court").is_dir():
    _ROOT = _DOCKER_ROOT
else:
    _ROOT = _LOCAL_ROOT  # fallback

_COURT_SRC = _ROOT / "src"
if str(_COURT_SRC) not in sys.path:
    sys.path.insert(0, str(_COURT_SRC))

_PROJECT_ROOT = _ROOT
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from creative_court.core.models import Brief, Verdict
from creative_court.core.trace import TraceRecorder, read_traces, export_trace_metrics
from creative_court.agents.creator import CreatorAgent
from creative_court.agents.judge import JudgeAgent

# ---------------------------------------------------------------------------
# Pydantic models (request / response schemas)
# ---------------------------------------------------------------------------

class DemoRequest(BaseModel):
    """Run the full pipeline with a brief (inline or from file)."""
    title: str | None = Field(default=None, description="Brief title")
    description: str | None = Field(default=None, description="Brief description")
    audience: str | None = Field(default=None, description="Target audience")
    goal: str | None = Field(default=None, description="Goal of the project")
    constraints: list[str] = Field(default_factory=list, description="Constraints")
    brief_file: str | None = Field(default=None, description="Path to a demo_briefs JSON file")


class VerdictResponse(BaseModel):
    direction_id: str
    total: float
    scores: list[dict[str, Any]]
    summary: str
    approved: bool
    vetoed: bool = False
    veto_reason: str = ""


class VetoRequest(BaseModel):
    direction_id: str = Field(description="Direction ID in format 'frame:name'")
    reason: str = Field(description="Reason for veto")


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    llm_available: bool = False


class RunInfo(BaseModel):
    identifier: str
    trace_path: str
    total_events: int
    event_types: dict[str, int]


class ListRunsResponse(BaseModel):
    runs: list[RunInfo]


class TraceExportResponse(BaseModel):
    path: str | None = None
    lines: int = 0


class PipelineResult(BaseModel):
    run_identifier: str
    brief: dict[str, Any]
    directions_count: int
    verdicts: list[VerdictResponse]
    trace_path: str
    events: dict[str, int]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TRACE_DIR = Path("traces")
BRIEFS_DIR = _PROJECT_ROOT / "demo_briefs"

def _check_llm() -> bool:
    """Return True if an LLM key is configured."""
    return bool(os.environ.get("COMETAPI_KEY") or os.environ.get("LLM_API_KEY"))


def _make_run_identifier() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"run_{ts}"


def _load_brief(req: DemoRequest) -> Brief:
    if req.brief_file:
        path = Path(req.brief_file)
        if not path.is_absolute():
            # Try demo_briefs/ relative to project root
            path = BRIEFS_DIR / path
        if not path.is_file():
            raise HTTPException(status_code=404, detail=f"Brief file not found: {req.brief_file}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return Brief(**data)
    if not req.title or not req.description:
        raise HTTPException(status_code=400, detail="Either provide title+description or brief_file")
    return Brief(
        title=req.title,
        description=req.description,
        audience=req.audience or "",
        constraints=req.constraints or [],
        goal=req.goal or "",
    )


def _verdict_to_dict(v: Verdict) -> dict[str, Any]:
    return {
        "direction_id": v.direction_id,
        "total": v.total,
        "scores": [{"dimension": s.dimension, "score": s.score, "comment": s.comment} for s in v.scores],
        "summary": v.summary,
        "approved": v.approved,
        "vetoed": v.vetoed,
        "veto_reason": v.veto_reason,
    }


def _list_runs() -> list[RunInfo]:
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for p in sorted(TRACE_DIR.glob("*.jsonl"), key=lambda x: x.name, reverse=True):
        try:
            metrics = export_trace_metrics(str(p))
        except Exception:
            continue
        results.append(RunInfo(
            identifier=p.stem,
            trace_path=str(p),
            total_events=metrics["total_events"],
            event_types=metrics["by_type"],
        ))
    return results


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    yield


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Creative Court API",
    description=(
        "FastAPI wrapper around Creative Court's agent harness.\n\n"
        "Pipeline: **brief → Creator → Directions → Judge → Verdicts → Veto**\n"
        "Every step is recorded as an append-only JSONL trajectory."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health():
    """Simple health check."""
    return HealthResponse(
        status="ok",
        llm_available=_check_llm(),
    )


@app.post("/demo", response_model=PipelineResult)
async def run_demo(req: DemoRequest):
    """
    Run the full creative-pipeline: load brief → creator generates directions → judge scores them → returns verdicts.

    All steps are recorded to a JSONL trajectory file under `traces/`.
    """
    brief = _load_brief(req)
    run_id = _make_run_identifier()
    trace_path = TRACE_DIR / f"{run_id}.jsonl"

    # Force heuristic mode unless LLM key present
    os.environ.pop("COMETAPI_KEY", None) if os.environ.get("COMETAPI_KEY") else None
    os.environ.pop("LLM_API_KEY", None) if os.environ.get("LLM_API_KEY") else None

    with TraceRecorder(str(trace_path), meta={"brief": brief.title, "run": run_id}) as rec:
        creator = CreatorAgent(rec)
        judge = JudgeAgent(rec)

        directions = creator.generate(brief)
        verdicts = judge.judge(brief, directions)

    metrics = export_trace_metrics(str(trace_path))
    return PipelineResult(
        run_identifier=run_id,
        brief={
            "title": brief.title,
            "description": brief.description,
            "audience": brief.audience,
            "goal": brief.goal,
            "constraints": brief.constraints,
        },
        directions_count=len(directions),
        verdicts=[VerdictResponse(**_verdict_to_dict(v)) for v in verdicts],
        trace_path=str(trace_path),
        events=metrics["by_type"],
    )


@app.get("/traces/run/{identifier}", response_model=list[dict])
async def get_trace(identifier: str):
    """
    Return the full trajectory content for a given run identifier.

    The identifier is the filename stem (e.g. `run_20260101-120000` — without `.jsonl`).
    If no exact match is found, tries to find a partial match among recent traces.
    """
    candidates = [f for f in TRACE_DIR.glob("*.jsonl") if identifier in f.stem]
    if not candidates:
        available = ", ".join(f.stem for f in sorted(TRACE_DIR.glob("*.jsonl"), reverse=True)[:5])
        raise HTTPException(
            status_code=404,
            detail=f"No trace found for '{identifier}'. Available recent runs: {available}",
        )
    path = sorted(candidates, key=lambda x: x.stat().st_mtime, reverse=True)[0]
    return read_traces(str(path))


@app.get("/api/traces/export", response_class=JSONResponse)
async def export_all_traces(limit: int = Query(default=100, ge=1, le=1000)):
    """
    Download all recorded trajectories as a single JSONL attachment.
    Returns at most *limit* lines (most recent first).
    """
    all_lines = []
    for p in sorted(TRACE_DIR.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            content = p.read_text(encoding="utf-8").strip()
            if content:
                all_lines.append(content)
        except Exception:
            continue
        if len(all_lines) >= limit:
            break

    if not all_lines:
        raise HTTPException(status_code=404, detail="No trace files found in traces/")

    jsonl_content = "\n".join(all_lines) + "\n"
    run_id = _make_run_identifier()
    export_name = f"creative-court-traces-{run_id}.jsonl"

    return JSONResponse(
        content=jsonl_content,
        media_type="application/x-jsonlines",
        headers={
            "Content-Disposition": f'attachment; filename="{export_name}"',
        },
    )


@app.post("/veto")
async def submit_veto(req: VetoRequest):
    """
    Record a human veto for a direction.

    Finds the latest trace that references the given direction_id,
    appends a veto event, and returns confirmation.
    """
    direction_id = req.direction_id
    reason = req.reason

    # Find traces that contain this direction (check action, feedback, data, verdict)
    matching = []
    for p in TRACE_DIR.glob("*.jsonl"):
        events = read_traces(str(p))
        for ev in events:
            ev_text = str(ev.get("action", "")) + str(ev.get("feedback", ""))
            ev_text += str(ev.get("data", {})) + str(ev.get("verdict", ""))
            if direction_id in ev_text:
                matching.append((p, events))
                break

    if not matching:
        available = ", ".join(f.stem for f in sorted(TRACE_DIR.glob("*.jsonl"), reverse=True)[:5])
        raise HTTPException(
            status_code=404,
            detail=f"No trace contains direction '{direction_id}'. Recent runs: {available}",
        )

    # Append veto event to the most recent matching trace
    best_path, _events = sorted(matching, key=lambda x: x[0].stat().st_mtime, reverse=True)[0]
    rec = TraceRecorder(str(best_path))
    rec.veto("user", direction_id, reason)
    rec.close()

    # Read back the last few events to confirm
    new_events = read_traces(str(best_path))[-3:]
    return JSONResponse({
        "status": "recorded",
        "trace_path": str(best_path),
        "direction_id": direction_id,
        "reason": reason,
        "recent_events": new_events,
    })


@app.get("/api/runs", response_model=ListRunsResponse)
async def list_runs():
    """List all recorded runs with metadata."""
    return ListRunsResponse(runs=_list_runs())


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
