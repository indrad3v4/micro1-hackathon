"""Judge agent — scores directions on contextual rubrics, issues verdicts.

Rubrics mirror micro1's evaluation vocabulary: relevance to brief, novelty,
feasibility, risk (edge cases), engineering quality. Human veto is recorded
as a first-class trajectory event.
"""
from __future__ import annotations

from ..core.models import Brief, Direction, RubricScore, Verdict
from ..core.trace import TraceRecorder

RUBRICS = [
    ("relevance", 0.30, "how well it answers the brief"),
    ("novelty", 0.20, "how surprising / non-obvious it is"),
    ("feasibility", 0.20, "can it be built and reproduced"),
    ("risk", 0.15, "edge cases and failure modes handled"),
    ("quality", 0.15, "engineering / execution clarity"),
]


class JudgeAgent:
    def __init__(self, recorder: TraceRecorder):
        self.recorder = recorder

    def judge(self, brief: Brief, directions: list[Direction]) -> list[Verdict]:
        agent = "judge"
        self.recorder.event(
            agent=agent, type="agent_start",
            instruction=f"Score {len(directions)} directions against brief '{brief.title}'",
        )
        verdicts = []
        for d in directions:
            scores = [
                RubricScore(dim, _heuristic_score(dim, d, brief))
                for dim, _, _ in RUBRICS
            ]
            total = round(sum(s.score * w for (dim, w, _), s in zip(RUBRICS, scores)), 1)
            approved = total >= 60.0
            v = Verdict(
                direction_id=f"{d.frame}:{d.name}",
                total=total,
                scores=scores,
                summary=f"{d.name}: {total}/100 — {'approved' if approved else 'rejected'}",
                approved=approved,
            )
            verdicts.append(v)
            self.recorder.event(
                agent=agent, type="agent_step",
                action=f"verdict for {v.direction_id}",
                feedback=v.summary,
                verdict=json_dumps({s.dimension: s.score for s in scores}),
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


def _heuristic_score(dim: str, d: Direction, brief: Brief) -> float:
    """Deterministic scoring so the pipeline runs without an LLM key."""
    text = f"{d.frame} {d.name} {d.concept} {d.rationale}".lower()
    brief_text = f"{brief.title} {brief.description}".lower()
    if dim == "relevance":
        overlap = sum(1 for w in brief_text.split() if w in text and len(w) > 3)
        return min(95, 50 + overlap * 8)
    if dim == "novelty":
        return 70.0 if d.frame in ("ritual", "natural", "historical") else 60.0
    if dim == "feasibility":
        return 80.0 if not d.risks else 65.0
    if dim == "risk":
        return 85.0 if not d.risks else 55.0
    return 75.0


def json_dumps(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False)
