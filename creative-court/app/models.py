"""Pydantic request / response schemas for Creative Court FastAPI."""

from typing import Any

from pydantic import BaseModel, Field


class DemoRequest(BaseModel):
    """Run the full pipeline with a brief (inline or from file)."""

    title: str | None = Field(default=None, description="Brief title")
    description: str | None = Field(default=None, description="Brief description")
    audience: str | None = Field(default=None, description="Target audience")
    goal: str | None = Field(default=None, description="Goal of the project")
    constraints: list[str] = Field(
        default_factory=list, description="Constraints"
    )
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
