"""Core domain models for Creative Court."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# --- Trace event types (micro1-compatible) ---
EVENT_AGENT_START = "agent_start"
EVENT_AGENT_STEP = "agent_step"          # an action taken by the agent
EVENT_TOOL_CALL = "tool_call"            # agent invoked a tool
EVENT_TOOL_RESPONSE = "tool_response"    # tool output came back
EVENT_RETRY = "retry"                    # agent retried after a failure
EVENT_HUMAN_CHECKPOINT = "human_checkpoint"  # human approval gate
EVENT_VETO = "veto"                      # human overrode an agent decision
EVENT_AGENT_END = "agent_end"


@dataclass
class TraceEvent:
    """One recorded step in an agent trajectory."""
    ts: str                    # ISO-8601 UTC
    agent: str                 # agent id/name, e.g. "creator", "judge", "codex"
    type: str                  # one of EVENT_*
    instruction: Optional[str] = None    # the prompt/instruction given
    action: Optional[str] = None         # what the agent did
    tool: Optional[str] = None           # tool name for tool_call/response
    tool_response: Optional[str] = None  # tool output (truncated for storage)
    feedback: Optional[str] = None       # feedback that shaped the next step
    retry_of: Optional[str] = None       # reference to the failed step
    human_checkpoint: Optional[str] = None  # what the human approved
    verdict: Optional[str] = None        # for judge events
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Brief:
    """The creative brief the Creator agent works from."""
    title: str
    description: str
    audience: str = ""
    constraints: list[str] = field(default_factory=list)
    goal: str = ""


@dataclass
class Direction:
    """One creative direction produced by the Creator agent."""
    frame: str                 # ИКРА frame: artistic/social/professional/historical/ritual/natural
    name: str
    concept: str               # what it is
    rationale: str             # why it fits the brief
    risks: list[str] = field(default_factory=list)
    generated_by: str = "llm"  # provenance: "llm" or "heuristic" (honesty for the signer)


@dataclass
class RubricScore:
    """A single rubric dimension scored by the Judge."""
    dimension: str
    score: float               # 0-100
    comment: str = ""


@dataclass
class Verdict:
    """Judge verdict for one direction."""
    direction_id: str          # frame + name
    total: float               # weighted total 0-100
    scores: list[RubricScore] = field(default_factory=list)
    summary: str = ""
    approved: bool = True
    vetoed: bool = False
    veto_reason: str = ""
    score_source: str = "llm"  # provenance: "llm" or "heuristic" (honesty for the signer)
    goal_fit: dict = field(default_factory=dict)  # {"score": 0-100, "note": str} — the human's stated higher goal
