"""Creative Court — MCP Server (the product's main interface for AI IDEs).

The core function of Creative Court, per the born insight
(driver + barrier → tension → insight: "the more a human delegates to an agent,
the less of himself remains in the work — yet he signs for all of it"):

    return signable decisions to the human.

This MCP server is that function made callable by AI coding agents (Claude Code,
Cursor, Codex, Hermes, ...). The agent = Creator; the human = signatory; this
server = Judge + Trace between them. Reflex UI is a thin human-facing view over
the same core (creative-court/src/creative_court).

Exposed tools:
    court_run_brief        — run brief → directions → verdicts (LLM judge)
    court_veto             — human vetoes a direction with a real reason; rework
    court_sign_off         — human signs the approved decisions (binds to data)
    court_export_trace     — read a run's JSONL trajectory
    court_health           — LLM availability + trace count

Transport: stdio (default, for AI IDE config) and streamable HTTP (for remote).

Run:
    python mcp_server.py            # stdio
    python mcp_server.py --http     # streamable HTTP on 0.0.0.0:8765
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Make the core importable regardless of CWD.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from mcp.server.mcpserver import MCPServer  # mcp 2.x

from creative_court.core.models import Brief
from creative_court.core.trace import TraceRecorder, export_trace_metrics
from creative_court.core.llm import LLMClient
from creative_court.agents.creator import CreatorAgent
from creative_court.agents.judge import JudgeAgent

TRACE_DIR = Path(os.environ.get(
    "CC_TRACE_DIR", os.path.join(os.path.dirname(__file__), "traces")))
TRACE_DIR.mkdir(parents=True, exist_ok=True)

server = MCPServer(
    name="creative-court",
    title="Creative Court — Token Result Gate",
    version="0.2.0",
    instructions=(
        "The final signature stays human. Run a brief through the Court, review "
        "the verdicts, veto drift with a real reason, then sign only what you saw. "
        "Every step is recorded to a JSONL trajectory."
    ),
)


def _run_id() -> str:
    return datetime.now().strftime("run_%Y%m%d_%H%M%S")


def _brief_from(**kw) -> Brief:
    constraints = [c.strip() for c in str(kw.get("constraints", "")).splitlines()
                   if c.strip()]
    return Brief(
        title=str(kw.get("title", "")).strip(),
        description=str(kw.get("description", "")).strip(),
        audience=str(kw.get("audience", "")).strip(),
        constraints=constraints,
        goal=str(kw.get("goal", "")).strip(),
    )


def _verdicts_to_json(verdicts) -> list[dict]:
    out = []
    for v in verdicts:
        out.append({
            "direction_id": v.direction_id,
            "total": v.total,
            "approved": v.approved,
            "summary": v.summary,
            "scores": {s.dimension: s.score for s in v.scores},
        })
    return out


@server.tool()
def court_health() -> dict:
    """Check the Court: LLM judge availability and recorded trajectories."""
    return {
        "llm_available": LLMClient().available,
        "model": LLMClient().model,
        "trace_count": len(list(TRACE_DIR.glob("*.jsonl"))),
    }


@server.tool()
def court_run_brief(title: str, description: str, audience: str = "",
                    constraints: str = "", goal: str = "") -> dict:
    """Run a creative brief through the Court: Creator fans directions, Judge
    scores every one on the 5-dimension rubric and vetoes hard-constraint drift.
    Returns ranked verdicts; the human reviews and either signs or vetoes."""
    if not title.strip():
        return {"error": "title is required"}
    brief = _brief_from(title=title, description=description,
                        audience=audience, constraints=constraints, goal=goal)
    run_id = _run_id()
    trace_path = TRACE_DIR / f"{run_id}.jsonl"
    # Sidecar: persist the brief so veto/re-sign can reload the run's context.
    (TRACE_DIR / f"{run_id}.brief.json").write_text(
        json.dumps({"title": brief.title, "description": brief.description,
                    "audience": brief.audience, "constraints": brief.constraints,
                    "goal": brief.goal}, ensure_ascii=False), encoding="utf-8")
    rec = TraceRecorder(str(trace_path), meta={
        "title": brief.title, "run": run_id, "kind": "mcp"})
    try:
        creator = CreatorAgent(recorder=rec, llm=LLMClient())
        judge = JudgeAgent(recorder=rec, llm=LLMClient())
        directions = creator.generate(brief)
        verdicts = judge.judge(brief, directions)
        approved = [v for v in verdicts if v.approved]
        return {
            "run_id": run_id,
            "trace_path": str(trace_path),
            "directions_count": len(directions),
            "approved_count": len(approved),
            "verdicts": _verdicts_to_json(verdicts),
            "note": ("Judge is " + ("LLM-backed" if LLMClient().available
                                    else "heuristic fallback (no LLM key)")),
        }
    finally:
        rec.close()


@server.tool()
def court_veto(run_id: str, direction_id: str, reason: str) -> dict:
    """Human vetoes one direction with a real reason; the Creator reworks that
    direction to address the reason and the Judge re-scores it. This is the
    moment the human's signature re-enters the work — reason is not optional."""
    if not reason.strip():
        return {"error": "a veto needs a real reason — that is the point"}
    trace_path = TRACE_DIR / f"{run_id}.jsonl"
    brief_path = TRACE_DIR / f"{run_id}.brief.json"
    if not trace_path.exists():
        return {"error": f"run {run_id} not found"}
    # reload the run's brief from its sidecar (persisted at run time)
    if brief_path.exists():
        bd = json.loads(brief_path.read_text(encoding="utf-8"))
        brief = Brief(title=bd.get("title", ""),
                      description=bd.get("description", ""),
                      audience=bd.get("audience", ""),
                      constraints=bd.get("constraints", []),
                      goal=bd.get("goal", ""))
    else:
        brief = Brief(title=run_id, description="re-run from veto",
                      audience="", constraints=[], goal="")
    veto_id = datetime.now().strftime("veto_%Y%m%d_%H%M%S")
    rec = TraceRecorder(str(trace_path), meta={"veto": veto_id, "for": run_id})
    try:
        creator = CreatorAgent(recorder=rec, llm=LLMClient())
        judge = JudgeAgent(recorder=rec, llm=LLMClient())
        # The human's reason becomes a hard requirement: regenerate the set
        # with the concern added to the brief's constraints, then re-score.
        revised_brief = Brief(
            title=brief.title, description=brief.description,
            audience=brief.audience,
            constraints=list(brief.constraints) + [f"human requirement: {reason}"],
            goal=brief.goal)
        rec.event(agent="human", type="veto", action=direction_id, feedback=reason)
        directions = creator.generate(revised_brief)
        verdicts = judge.judge(revised_brief, directions)
        # the reworked slot = the direction that best answers the new constraint
        reworked = max(verdicts, key=lambda v: v.total)
        return {
            "veto_id": veto_id,
            "reworked_direction": reworked.direction_id,
            "reason": reason,
            "reworked_verdict": reworked.total,
            "all_verdicts": _verdicts_to_json(verdicts),
            "trace_path": str(trace_path),
        }
    finally:
        rec.close()


@server.tool()
def court_sign_off(run_id: str, decisions: list[dict]) -> dict:
    """Human signs the approved decisions. `decisions` must be the actual list
    of direction ids/names being approved (bound to the visible verdicts). The
    signature is recorded in the trajectory as data — proving WHAT was signed."""
    if not decisions:
        return {"error": "sign nothing or list the decisions — 'sign only what you saw'"}
    trace_path = TRACE_DIR / f"{run_id}.jsonl"
    rec = TraceRecorder(str(trace_path), meta={"sign_off": datetime.now().isoformat()})
    try:
        rec.event(agent="human", type="human_checkpoint",
                  human_checkpoint="human signed decisions",
                  data={"signed": decisions})
        return {
            "run_id": run_id,
            "signed": decisions,
            "recorded": True,
            "trace_path": str(trace_path),
        }
    finally:
        rec.close()


@server.tool()
def court_export_trace(run_id: str) -> dict:
    """Read a run's full JSONL trajectory (instruction → action → feedback →
    human checkpoints) plus event-type metrics."""
    trace_path = TRACE_DIR / f"{run_id}.jsonl"
    if not trace_path.exists():
        return {"error": f"run {run_id} not found"}
    events = []
    with open(trace_path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                events.append(__import__("json").loads(line))
    return {
        "run_id": run_id,
        "events": events,
        "metrics": export_trace_metrics(str(trace_path)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Creative Court MCP server")
    parser.add_argument("--http", action="store_true",
                        help="run over streamable HTTP (default: stdio)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    if args.http:
        import uvicorn
        app = server.streamable_http_app()
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    else:
        import asyncio
        asyncio.run(server.run_stdio_async())


if __name__ == "__main__":
    main()
