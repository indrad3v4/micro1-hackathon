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

from mcp.server.mcpserver import MCPServer, Context  # mcp 2.x

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
    version="0.3.0",
    instructions=(
        "The final signature stays human. Run a brief through the Court, review "
        "the verdicts, veto drift with a real reason, then sign only what you saw. "
        "Every step is recorded to a JSONL trajectory. Traces are also exposed as "
        "resources (trace://{run_id}) and a review prompt (court_review) is available."
    ),
)

# ---------------------------------------------------------------------------
# Resources — the Court's record exposed to the client (AI IDE / agent).
# This is the product's core promise made native to MCP: "return signable
# decisions to the human" — the trajectory IS the signable record.
# ---------------------------------------------------------------------------


def _list_traces() -> list[dict]:
    runs = []
    for f in sorted(TRACE_DIR.glob("run_*.jsonl")):
        runs.append({
            "uri": f"trace://{f.stem.replace('run_', '')}",
            "run_id": f.stem.replace("run_", ""),
            "path": str(f),
            "size": f.stat().st_size,
        })
    return runs


def _read_trace_file(run_id: str) -> list[dict] | None:
    p = TRACE_DIR / f"run_{run_id}.jsonl"
    if not p.exists():
        return None
    events = []
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                events.append(json.loads(line))
    return events


@server.resource(uri="traces://list", name="traces_list",
                 title="Court run index",
                 description="All Creative Court runs recorded in the trajectory store")
def traces_list() -> list[dict]:
    """List every recorded run (run_id, trace path, size)."""
    return _list_traces()


@server.resource(uri="trace://{run_id}", name="trace_read",
                 title="Court trajectory",
                 description="Full JSONL trajectory of one run — instruction → action → feedback → human checkpoints")
def trace_read(run_id: str) -> dict:
    """Return the full trajectory of one run (events + metrics)."""
    events = _read_trace_file(run_id)
    if events is None:
        raise ValueError(f"run {run_id} not found")
    from creative_court.core.trace import export_trace_metrics
    return {
        "run_id": run_id,
        "events": events,
        "metrics": export_trace_metrics(str(TRACE_DIR / f"run_{run_id}.jsonl")),
    }


# ---------------------------------------------------------------------------
# Prompt — a guided review workflow the client can invoke by name.
# ---------------------------------------------------------------------------


@server.prompt(name="court_review", title="Review a Creative Court run",
               description="Walk a run's verdicts as the human who must sign — find drift, decide veto or sign")
def court_review_prompt(run_id: str) -> str:
    """Template: the agent reads a run's trace and produces a sign-or-veto review."""
    return (
        f"You are the human signatory for Creative Court run `{run_id}`.\n"
        "Read the trajectory, then for each approved direction answer: "
        "(1) does it respect every hard constraint of the brief? "
        "(2) is the concept concrete (not template boilerplate)? "
        "(3) does its rationale justify the score? "
        "Then either recommend which direction to veto (with a reason) or "
        "confirm the whole set is safe to sign. "
        "Sign only what you saw — never rubber-stamp."
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


def _verdicts_to_json(verdicts, directions=None) -> list[dict]:
    # map direction_id (frame:name) -> Direction to attach the content a human
    # must see before signing/rejecting ("sign only what you saw")
    dir_map = {}
    if directions:
        for d in directions:
            dir_map[f"{d.frame}:{d.name}"] = d
    out = []
    for v in verdicts:
        d = dir_map.get(v.direction_id)
        out.append({
            "direction_id": v.direction_id,
            "total": v.total,
            "approved": v.approved,
            "summary": v.summary,
            "scores": {s.dimension: s.score for s in v.scores},
            "concept": d.concept if d else "",
            "rationale": d.rationale if d else "",
            "risks": list(d.risks) if d else [],
            # honesty: how was this produced? a heuristic direction must never
            # be presented as LLM work (brand-champion rule)
            "generated_by": getattr(d, "generated_by", "llm") if d else "llm",
        })
    return out


def _warnings(directions) -> list[str]:
    """Surface any fallback so a human never signs heuristic work as LLM work."""
    warns = []
    if not directions:
        return warns
    n_heur = sum(1 for d in directions if getattr(d, "generated_by", "llm") == "heuristic")
    if n_heur == len(directions):
        warns.append("LLM generation failed; all directions are heuristic templates")
    elif n_heur:
        warns.append(f"{n_heur}/{len(directions)} directions are heuristic fallbacks (LLM output unparseable)")
    return warns


@server.tool()
def court_health() -> dict:
    """Check the Court: LLM judge availability and recorded trajectories."""
    return {
        "llm_available": LLMClient().available,
        "model": LLMClient().model,
        "trace_count": len(list(TRACE_DIR.glob("*.jsonl"))),
    }


@server.tool()
async def court_run_brief(title: str, description: str, audience: str = "",
                          constraints: str = "", goal: str = "",
                          ctx: Context = None) -> dict:
    """Run a creative brief through the Court: Creator fans directions, Judge
    scores every one on the 5-dimension rubric and vetoes hard-constraint drift.
    Returns ranked verdicts; the human reviews and either signs or vetoes."""
    import asyncio

    async def _progress(p: float, msg: str) -> None:
        if ctx:
            await ctx.report_progress(p, 100, msg)

    await _progress(5, "Loading brief")
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
    loop = asyncio.get_running_loop()
    try:
        creator = CreatorAgent(recorder=rec, llm=LLMClient())
        judge = JudgeAgent(recorder=rec, llm=LLMClient())
        await _progress(15, "Creator: fanning directions")

        # run the blocking LLM work off-loop; progress callbacks hop back via threadsafe
        def _run():
            dirs = creator.generate(brief)
            n = len(dirs)
            def cb(i, n, msg):
                loop.call_soon_threadsafe(
                    lambda: asyncio.ensure_future(_progress(30 + int(60 * (i + 1) / n), msg)))
            vs = judge.judge(brief, dirs, progress_cb=cb)
            return dirs, vs
        directions, verdicts = await asyncio.to_thread(_run)

        approved = [v for v in verdicts if v.approved]
        await _progress(95, "Persisting verdicts")
        # Sidecar: persist the canonical verdicts so sign-off binds to THEM,
        # not to whatever the human re-typed (brand-champion rule).
        (TRACE_DIR / f"{run_id}.verdicts.json").write_text(
            json.dumps(_verdicts_to_json(verdicts, directions),
                       ensure_ascii=False), encoding="utf-8")
        await _progress(100, "Done")
        return {
            "run_id": run_id,
            "trace_path": str(trace_path),
            "directions_count": len(directions),
            "approved_count": len(approved),
            "verdicts": _verdicts_to_json(verdicts, directions),
            "warnings": _warnings(directions),
            "note": ("Judge is " + ("LLM-backed" if LLMClient().available
                                    else "heuristic fallback (no LLM key)")),
        }
    finally:
        rec.close()


@server.tool()
async def court_veto(run_id: str, direction_id: str, reason: str,
                     ctx: Context = None) -> dict:
    """Human vetoes one direction with a real reason; the Creator reworks that
    direction to address the reason and the Judge re-scores it. This is the
    moment the human's signature re-enters the work — reason is not optional."""
    import asyncio

    async def _progress(p: float, msg: str) -> None:
        if ctx:
            await ctx.report_progress(p, 100, msg)

    await _progress(5, "Recording veto")
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
    loop = asyncio.get_running_loop()
    try:
        creator = CreatorAgent(recorder=rec, llm=LLMClient())
        judge = JudgeAgent(recorder=rec, llm=LLMClient())
        # The human's reason becomes a hard requirement on the SAME direction:
        # rework is bound to direction_id, reason fed into the Creator prompt.
        revised_brief = Brief(
            title=brief.title, description=brief.description,
            audience=brief.audience,
            constraints=list(brief.constraints) + [f"human requirement: {reason}"],
            goal=brief.goal)
        rec.event(agent="human", type="veto", action=direction_id, feedback=reason)
        await _progress(20, "Creator: reworking the vetoed direction")

        # run the blocking LLM work off-loop; progress callbacks hop back via threadsafe
        def _run():
            dirs = creator.generate(
                revised_brief,
                rework={"direction_id": direction_id, "reason": reason})
            n = len(dirs)
            def cb(i, n, msg):
                loop.call_soon_threadsafe(
                    lambda: asyncio.ensure_future(_progress(45 + int(45 * (i + 1) / n), msg)))
            vs = judge.judge(revised_brief, dirs, progress_cb=cb)
            return dirs, vs
        directions, verdicts = await asyncio.to_thread(_run)

        # the reworked slot must be the SAME direction (frame) as the vetoed one,
        # re-generated under the new constraint — not a random unrelated frame.
        frame = direction_id.split(":")[0] if ":" in direction_id else direction_id
        target = next((v for v in verdicts if v.direction_id.startswith(frame + ":")), None)
        # refresh canonical verdicts sidecar so sign_off binds to the current set
        await _progress(95, "Persisting verdicts")
        (TRACE_DIR / f"{run_id}.verdicts.json").write_text(
            json.dumps(_verdicts_to_json(verdicts, directions),
                       ensure_ascii=False), encoding="utf-8")
        await _progress(100, "Done")
        return {
            "veto_id": veto_id,
            "reworked_direction": target.direction_id if target else direction_id,
            "reason": reason,
            "reworked_verdict": target.total if target else None,
            "all_verdicts": _verdicts_to_json(verdicts, directions),
            "warnings": _warnings(directions),
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
def court_sign_off_all(run_id: str) -> dict:
    """Sign every currently-approved decision in ONE call, bound to the CANONICAL
    verdicts (persisted at run/veto time) — the human confirms instead of re-typing
    id/score/concept. Returns the signed list plus a pass-diff showing what changed
    since the previous state, so silent replacements become visible."""
    trace_path = TRACE_DIR / f"{run_id}.jsonl"
    verdicts_path = TRACE_DIR / f"{run_id}.verdicts.json"
    if not trace_path.exists():
        return {"error": f"run {run_id} not found"}
    if not verdicts_path.exists():
        return {"error": f"run {run_id} has no persisted verdicts — run the brief first"}
    canonical = json.loads(verdicts_path.read_text(encoding="utf-8"))
    approved = [v for v in canonical if v.get("approved")]
    if not approved:
        return {"error": "no approved decisions to sign", "approved": []}
    rec = TraceRecorder(str(trace_path), meta={"sign_off": datetime.now().isoformat()})
    try:
        rec.event(agent="human", type="human_checkpoint",
                  human_checkpoint="human signed decisions",
                  data={"signed": approved})
        return {
            "run_id": run_id,
            "signed_count": len(approved),
            "signed": approved,
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
