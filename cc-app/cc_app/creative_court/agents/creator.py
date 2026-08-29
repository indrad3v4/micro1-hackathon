"""Creator agent — brief -> fan of creative directions across ИКРА frames.

Every step is recorded to the trajectory. LLM-backed when a key is present,
heuristic fallback otherwise (keeps the pipeline runnable offline).
"""
from __future__ import annotations

import json
import os
import re

from ..core.models import Brief, Direction
from ..core.trace import TraceRecorder
from ..core.llm import LLMClient, FRAMES, heuristic_directions, load_prompt

# Load improved prompt from disk
# Resolve prompts: repo root has prompts/ (creative-court/prompts does not exist).
_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "prompts"),
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "prompts"),
    os.path.join(os.path.dirname(__file__), "..", "..", "prompts"),
]
_PROMPTS_DIR = next((p for p in _CANDIDATES
                     if os.path.isfile(os.path.join(p, "creator_prompt.txt"))),
                    _CANDIDATES[0])
_CREATOR_SYSTEM = load_prompt(os.path.join(_PROMPTS_DIR, "creator_prompt.txt"))


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
        if self.llm.available and _CREATOR_SYSTEM:
            try:
                raw = self._build_user_prompt(brief)
                response = self.llm.chat(system=_CREATOR_SYSTEM, user=raw, max_tokens=4096)
                self.recorder.tool_response(agent, "llm", response)
                payload = _parse_json(response)
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

    @staticmethod
    def _build_user_prompt(brief: Brief) -> str:
        parts = [f"Title: {brief.title}", f"Description: {brief.description}"]
        if brief.audience:
            parts.append(f"Audience: {brief.audience}")
        if brief.goal:
            parts.append(f"Goal: {brief.goal}")
        if brief.constraints:
            parts.append(f"Constraints:\n" + "\n".join(f"- {c}" for c in brief.constraints))
        return "\n".join(parts)


def _parse_json(raw: str) -> dict:
    """Extract JSON from LLM output, stripping markdown fences if present."""
    cleaned = raw.strip()
    m = re.search(r"```(?:json)?\s*\n(.*?)\n```\s*$", cleaned, re.DOTALL)
    if m:
        cleaned = m.group(1).strip()
    # Try full parse first, then bracket-fallback
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    m2 = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not m2:
        raise ValueError("no JSON object in LLM output")
    return json.loads(m2.group(0))
