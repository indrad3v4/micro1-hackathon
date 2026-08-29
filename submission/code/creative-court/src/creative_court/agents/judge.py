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

# Resolve prompts: repo root has prompts/ (creative-court/prompts does not exist).
_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "prompts"),
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "prompts"),
    os.path.join(os.path.dirname(__file__), "..", "..", "prompts"),
]
_PROMPTS_DIR = next((p for p in _CANDIDATES
                     if os.path.isfile(os.path.join(p, "judge_prompt.txt"))),
                    _CANDIDATES[0])

# The prompt contains literal JSON braces (its OUTPUT FORMAT section) which
# would break str.format() in _llm_score. Double every brace that is not a
# known placeholder, so .format() works everywhere (MCP, CLI, Reflex, bench).
_PLACEHOLDER_KEYS = (
    "brief_title", "brief_description", "brief_audience", "brief_constraints",
    "direction_frame", "direction_name", "direction_concept",
    "direction_rationale", "direction_risks",
)


def _format_safe(prompt: str) -> str:
    out = prompt.replace("{", "{{").replace("}", "}}")
    for k in _PLACEHOLDER_KEYS:
        out = out.replace("{{" + k + "}}", "{" + k + "}")
    return out


class JudgeAgent:
    def __init__(self, recorder: TraceRecorder, llm: LLMClient | None = None):
        self.recorder = recorder
        self.llm = llm or LLMClient()
        self._prompt_text = _format_safe(
            load_prompt(os.path.join(_PROMPTS_DIR, "judge_prompt.txt")))

    def judge(self, brief: Brief, directions: list[Direction],
              progress_cb=None) -> list[Verdict]:
        agent = "judge"
        self.recorder.event(
            agent=agent, type="agent_start",
            instruction=f"Score {len(directions)} directions against brief '{brief.title}'",
        )
        verdicts = []
        n = len(directions)
        for i, d in enumerate(directions):
            if progress_cb:
                progress_cb(i, n, f"judging {i + 1}/{n}: {d.name}")
            if self.llm.available and self._prompt_text:
                score, source = self._llm_score(d, brief)
            else:
                score, source = self._heuristic_score(d, brief), "heuristic"
            total = round(sum(s.score * w for (dim, w, _), s in zip(RUBRICS, score)), 1)
            approved = total >= 60.0
            v = Verdict(
                direction_id=f"{d.frame}:{d.name}",
                total=total,
                scores=score,
                summary=f"{d.name}: {total}/100 — {'approved' if approved else 'rejected'}",
                approved=approved,
                score_source=source,
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

    def _llm_score(self, direction: Direction, brief: Brief) -> tuple[list[RubricScore], str]:
        """Ask the LLM to score a single direction using the rubric prompt.
        Falls back to heuristic scoring on any LLM/parse failure so the Court
        never dies mid-run. On parse failure, retries once with a strict-JSON
        hint BEFORE the heuristic — a heuristic number must never be
        indistinguishable from an LLM one. Returns (scores, source)."""
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
        try:
            raw = self.llm.chat(system="", user=user, max_tokens=2048)
            return self._parse_llm_scores(raw), "llm"
        except Exception as exc:
            # one strict-JSON retry before giving up to heuristic
            try:
                strict = user + "\n\nIMPORTANT: Reply with ONLY valid JSON, no prose."
                raw2 = self.llm.chat(system="", user=strict, max_tokens=2048)
                return self._parse_llm_scores(raw2), "llm"
            except Exception as exc2:
                self.recorder.retry("judge", direction.name,
                                    f"LLM score failed twice ({exc} | {exc2}); heuristic fallback")
                return self._heuristic_score(direction, brief), "heuristic"

    @staticmethod
    def _parse_llm_scores(raw: str) -> list[RubricScore]:
        """Extract JSON scores from LLM output, handling markdown fences and
        stray reasoning/prose. Falls back to finding the first {...} block."""
        import re
        cleaned = (raw or "").strip()
        # drop any reasoning_content prefix (some models emit it)
        cleaned = re.sub(r"<reasoning>.*?</reasoning>", "", cleaned, flags=re.DOTALL)
        # Strip optional markdown code fence
        m = re.search(r"```(?:json)?\s*\n(.*?)\n```\s*$", cleaned, re.DOTALL)
        if m:
            cleaned = m.group(1).strip()
        try:
            obj = json.loads(cleaned)
        except json.JSONDecodeError:
            m2 = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if not m2:
                raise ValueError(f"no JSON object in judge output: {cleaned[:120]!r}")
            obj = json.loads(m2.group(0))
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
