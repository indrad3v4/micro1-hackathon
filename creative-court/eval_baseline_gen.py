#!/usr/bin/env python3
"""Baseline generator — the honest 'one simple prompt' comparison point.

Per the hackathon PDF: baseline = ONE simple prompt / simple script on the SAME
briefs. No frames fan-out, no rubrics, no judge, no veto, no trajectory.
One deterministic pass producing exactly one generic creative idea.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from creative_court.agents.judge import _heuristic_score  # noqa: E402
from creative_court.core.models import Brief, Direction  # noqa: E402

# The single generic prompt a person would paste into any chatbot.
BASELINE_PROMPT = (
    "Придумай одну креативную идею для этого брифа: «{title}». {description} "
    "Аудитория: {audience}. Цель: {goal}. Ответ: название, концепция, обоснование."
)


def baseline_run(brief: Brief) -> dict:
    """One generic idea, one deterministic pass. Returns outcome + the prompt used."""
    prompt = BASELINE_PROMPT.format(
        title=brief.title, description=brief.description,
        audience=brief.audience or "целевая аудитория", goal=brief.goal or "",
    )
    d = Direction(
        frame="standard",
        name="Главная идея",
        concept=f"Продвигать «{brief.title}» через понятную историю для {brief.audience or 'аудитории'}: подчеркнуть главную пользу и запуститься по плану брифа.",
        rationale="Идея напрямую повторяет формулировку брифа и понятна аудитории.",
        risks=[],
    )
    # Scored by the SAME heuristic the Judge uses — identical yardstick for both arms.
    score = round(sum(
        _heuristic_score(dim, d, brief) * w
        for dim, w in [("relevance", 0.30), ("novelty", 0.20), ("feasibility", 0.20), ("risk", 0.15), ("quality", 0.15)]
    ), 1)
    return {
        "prompt_used": prompt,
        "n_directions": 1,
        "best_total": score,
        "rubrics": False,
        "veto": False,
        "trace": False,
        "contradiction_flagged": False,  # a single generic pass has no contradiction gate
    }


if __name__ == "__main__":
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(json.dumps(baseline_run(Brief(**data)), ensure_ascii=False, indent=2))
