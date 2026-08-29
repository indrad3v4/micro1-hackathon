"""Creator agent — brief -> fan of creative directions across ИКРА frames.

Every step is recorded to the trajectory. LLM-backed when a key is present,
heuristic fallback otherwise (keeps the pipeline runnable offline).
"""
from __future__ import annotations

from ..core.models import Brief, Direction
from ..core.trace import TraceRecorder
from ..core.llm import LLMClient, heuristic_directions

CREATOR_SYSTEM = (
    "You are the Creator agent in a creative court. Given a brief, produce "
    "creative directions across SIX frames: artistic, social, professional, "
    "historical, ritual, natural. For each direction give: frame, name, "
    "concept (what it is), rationale (why it fits the brief), risks. "
    "Return STRICT JSON: {\"directions\": [{\"frame\": ..., \"name\": ..., "
    "\"concept\": ..., \"rationale\": ..., \"risks\": [...]}]}"
)


class CreatorAgent:
    def __init__(self, recorder: TraceRecorder, llm: LLMClient | None = None):
        self.recorder = recorder
        self.llm = llm or LLMClient()

    def generate(self, brief: Brief) -> list[Direction]:
        agent = "creator"
        self.recorder.event(
            agent=agent, type="agent_start",
            instruction=f"Generate creative directions for brief: {brief.title}",
        )
        if self.llm.available:
            try:
                raw = self.llm.chat(CREATOR_SYSTEM, f"BRIEF:\n{brief.title}\n{brief.description}")
                self.recorder.tool_response(agent, "llm", raw)
                payload = _parse_json(raw)
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


def _parse_json(raw: str) -> dict:
    import re
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        raise ValueError("no JSON object in LLM output")
    return __import__("json").loads(m.group(0))
