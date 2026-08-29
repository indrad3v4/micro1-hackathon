"""Judge agent — scores directions on contextual rubrics, issues verdicts.

Rubrics mirror micro1's evaluation vocabulary: relevance to brief, novelty,
feasibility, risk (edge cases), engineering quality. Human veto is recorded
as a first-class trajectory event.

Uses LLM-based scoring when a key is configured, falls back to heuristics
when not.
"""
from __future__ import annotations

import json
import os

from ..core.models import Brief, Direction, RubricScore, Verdict
from ..core.trace import TraceRecorder
from ..core.llm import LLMClient, load_prompt

RUBRICS = [
    ("relevance", 0.30, "how well it answers the brief"),
    ("novelty", 0.20, "how surprising / non-obvious it is"),
    ("feasibility", 0.20, "can it be built and reproduced"),
    ("risk", 0.15, "edge cases and failure modes handled"),
    ("quality", 0.15, "engineering / execution clarity"),
]

# Resolve prompt path relative to this file's module directory
_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "prompts")


class JudgeAgent:
    def __init__(self, recorder: TraceRecorder, llm: LLMClient | None = None):
        self.recorder = recorder
        self.llm = llm or LLMClient()
        self._prompt_text = load_prompt(os.path.join(_PROMPTS_DIR, "judge_prompt.txt"))

    def judge(self, brief: Brief, directions: list[Direction]) -> list[Verdict]:
        agent = "judge"
        self.recorder.event(
            agent=agent, type="agent_start",
            instruction=f"Score {len(directions)} directions against brief '{brief.title}'",
        )
        verdicts = []
        for d in directions:
            if self.llm.available and self._prompt_text:
                score = self._llm_score(d, brief)
            else:
                score = self._heuristic_score(d, brief)
            total = round(sum(s.score * w for (dim, w, _), s in zip(RUBRICS, score)), 1)
            approved = total >= 60.0
            v = Verdict(
                direction_id=f"{d.frame}:{d.name}",
                total=total,
                scores=score,
                summary=f"{d.name}: {total}/100 — {'approved' if approved else 'rejected'}",
                approved=approved,
            )
            verdicts.append(v)
            self.recorder.event(
                agent=agent, type="agent_step",
                action=f"verdict for {v.direction_id}",
                feedback=v.summary,
                verdict=json_dumps({s.dimension: s.score for s in score}),
            )
        # rank
        verdicts.sort(key=lambda v: v.total, reverse=True)
        self.recorder.event(agent=agent, type="agent_end",
                            action=f"ranked {len(verdicts)} verdicts")
        return verdicts

    def veto(self, verdict: Verdict, reason: str) -> Verdict:
        verdict.vetoed = True
        verdict.veto_reason = reason
        self.recorder.veto("judge", verdict.direction_id, reason)
        return verdict

    # --- LLM scoring --------------------------------------------------------

    def _llm_score(self, direction: Direction, brief: Brief) -> list[RubricScore]:
        """Ask the LLM to score a single direction using the rubric prompt."""
        user = self._prompt_text.format(
            brief_title=brief.title,
            brief_description=brief.description,
            brief_audience=brief.audience or "",
            brief_constraints="\n".join(f"- {c}" for c in brief.constraints) if brief.constraints else "(none)",
            direction_frame=direction.frame,
            direction_name=direction.name,
            direction_concept=direction.concept,
            direction_rationale=direction.rationale,
            direction_risks=", ".join(direction.risks) if direction.risks else "(none)",
        )
        raw = self.llm.chat(system="", user=user, max_tokens=2048)
        return self._parse_llm_scores(raw)

    @staticmethod
    def _parse_llm_scores(raw: str) -> list[RubricScore]:
        """Extract JSON scores from LLM output, handling markdown fences."""
        import re
        cleaned = raw.strip()
        # Strip optional markdown code fence
        m = re.search(r"```(?:json)?\s*\n(.*?)\n```\s*$", cleaned, re.DOTALL)
        if m:
            cleaned = m.group(1).strip()
        obj = json.loads(cleaned)
        results = []
        for entry in obj.get("scores", []):
            dim = entry["dimension"]
            score_val = float(entry["score"])
            comment = entry.get("comment", "")
            results.append(RubricScore(dimension=dim, score=score_val, comment=comment))
        # Validate we have all 5 dimensions
        expected_dims = {r[0] for r in RUBRICS}
        got_dims = {r.dimension for r in results}
        missing = expected_dims - got_dims
        if missing:
            raise ValueError(f"LLM missed dimensions: {missing}")
        return results

    # --- Heuristic scoring (offline fallback) --------------------------------

    def _heuristic_score(self, direction: Direction, brief: Brief) -> list[RubricScore]:
        """Deterministic scoring so the pipeline runs without an LLM key."""
        text = f"{direction.frame} {direction.name} {direction.concept} {direction.rationale}".lower()
        brief_text = f"{brief.title} {brief.description}".lower()
        scores = []
        for dim, _, desc in RUBRICS:
            if dim == "relevance":
                overlap = sum(1 for w in brief_text.split() if w in text and len(w) > 3)
                s = min(95, 50 + overlap * 8)
            elif dim == "novelty":
                s = 70.0 if direction.frame in ("ritual", "natural", "historical") else 60.0
            elif dim == "feasibility":
                s = 80.0 if not direction.risks else 65.0
            elif dim == "risk":
                s = 85.0 if not direction.risks else 55.0
            else:
                s = 75.0
            scores.append(RubricScore(dimension=dim, score=s, comment=f"Heuristic: {desc}"))
        return scores


def json_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)
