"""Eval runner — baseline (один простой промпт) vs Creative Court (advanced)
on the same 12 briefs. micro1 hackathon, Measured Improvement (15 pts).

Both paths call the SAME model via the same OpenAI-compatible endpoint
(deepseek-v4-flash-vision-exp via CometAPI) — difference is only the HARNESS:
  baseline = one naive prompt, no agents, no judge;
  advanced = Creator agent (6 ИКРА frames) + Judge agent (contextual rubrics,
             deterministic scoring) + human veto event + TraceRecorder JSONL.

Real token usage captured on BOTH sides (MeteredLLM wraps LLMClient for the
advanced Creator; baseline counts its own single call). Costs from the
agentic-coding model-pool table: deepseek lane $0.064/$0.129 per 1M in/out.

Traces: BOTH modes write TraceRecorder JSONL into creative-court/traces/
(eval_base_BXX.jsonl / eval_adv_BXX.jsonl).

Usage:
  eval/.venv... python run_eval.py baseline
  eval/.venv... python run_eval.py advanced
Outputs: eval/results/<mode>_results.json
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # micro1-hackathon/
CC = ROOT / "creative-court"
sys.path.insert(0, str(CC / "src"))

from creative_court.core.models import Brief           # noqa: E402
from creative_court.core.trace import TraceRecorder    # noqa: E402
from creative_court.core.llm import LLMClient          # noqa: E402
from creative_court.agents.creator import CreatorAgent # noqa: E402
from creative_court.agents.judge import JudgeAgent     # noqa: E402

# pricing (USD per 1M tokens) — agentic-coding model pool table, deepseek lane
PRICE_IN, PRICE_OUT = 0.064, 0.129
MODEL = os.environ.get("LLM_MODEL", "deepseek-v4-flash-vision-exp")

BASELINE_SYSTEM = (
    "Ты креативный консультант. Придумай креативную концепцию для брифа. "
    "Ответь одним связным текстом: идея, почему сработает, риски."
)

BRIEFS = json.loads((Path(__file__).parent / "briefs.json").read_text())["briefs"]
RESULTS_DIR = Path(__file__).parent / "results"
TRACES_DIR = CC / "traces"


def llm_chat(system: str, user: str, max_tokens: int = 8192) -> tuple[str, dict, float]:
    """One raw OpenAI-compatible call; returns (content, usage, cost_usd).

    - max_tokens high: deepseek-v4-flash-vision-exp is a reasoning model and
      burns 2-3k tokens on reasoning before writing the answer (finish=length
      with empty content at 3072).
    - cost: CometAPI returns usage.cost (authoritative); we SUM it across
      attempts so failed retries are counted too (honest accounting).
    - retries on empty content.
    """
    key = os.environ["COMETAPI_KEY"]
    base = os.environ.get("LLM_BASE_URL", "https://api.cometapi.com/v1")
    last_err = None
    total_cost = 0.0
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for attempt in range(3):
        body = json.dumps({
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
        }).encode()
        req = urllib.request.Request(f"{base}/chat/completions", data=body, headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {key}"})
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode())
            usage = data.get("usage", {})
            total_cost += float(usage.get("cost") or 0.0)
            for k in total_usage:
                total_usage[k] += usage.get(k, 0)
            msg = data["choices"][0]["message"]
            content = (msg.get("content") or "").strip()
            if content:
                return content, total_usage, round(total_cost, 6)
            last_err = RuntimeError(
                f"empty content (attempt {attempt+1}): keys={list(msg.keys())}, "
                f"finish={data['choices'][0].get('finish_reason')}")
            print(f"  retry: {last_err}", file=sys.stderr)
        except Exception as exc:  # network/HTTP error — retry
            last_err = exc
            print(f"  retry: {exc}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"llm_chat failed after 3 attempts: {last_err}")


def usage_cost(usage: dict) -> float:
    pin = usage.get("prompt_tokens", 0)
    pout = usage.get("completion_tokens", 0)
    return round((pin * PRICE_IN + pout * PRICE_OUT) / 1_000_000, 6)


def brief_to_model(b: dict) -> Brief:
    return Brief(
        title=b["title"], description=b["description"],
        audience=b.get("audience", ""),
        constraints=b.get("constraints", []), goal=b.get("goal", ""),
    )


class MeteredLLM(LLMClient):
    """LLMClient subclass that records per-call usage (wrap, not monkeypatch —
    monkeypatching chat.completions is unreliable per agentic-coding skill)."""

    def __init__(self):
        super().__init__()
        self.calls: list[dict] = []

    def chat(self, system: str, user: str, max_tokens: int = 8192) -> str:
        content, usage, cost = llm_chat(system, user, max_tokens)
        self.calls.append({"usage": usage, "cost_usd": cost})
        return content


def run_baseline() -> list[dict]:
    out = []
    for b in BRIEFS:
        trace_path = TRACES_DIR / f"eval_base_{b['id']}.jsonl"
        prompt = (
            f"БРИФ: {b['title']}\n{b['description']}\n"
            f"Аудитория: {b.get('audience', '-')}\n"
            f"Ограничения: {'; '.join(b.get('constraints', [])) or '-'}\n"
            f"Цель: {b.get('goal', '-')}\n"
            "Создай креативную концепцию для этого брифа."
        )
        t0 = time.monotonic()
        with TraceRecorder(str(trace_path), meta={
            "brief": b["title"], "run": f"eval_baseline_{b['id']}",
            "mode": "baseline", "model": MODEL,
        }) as rec:
            rec.tool_call("baseline_single_prompt", "llm_chat_completions", prompt)
            content, usage, cost = llm_chat(BASELINE_SYSTEM, prompt)
            rec.tool_response("baseline_single_prompt", "llm", content)
            rec.event(agent="baseline_single_prompt", type="agent_end",
                      action="returned 1 free-text concept",
                      data={"usage": usage, "cost_usd": cost})
        wall = round(time.monotonic() - t0, 2)
        out.append({
            "brief_id": b["id"], "brief_title": b["title"], "complex": b.get("complex", False),
            "output_preview": content[:400], "output_full_chars": len(content),
            "wall_s": wall, "llm_calls": 1,
            "tokens": usage, "cost_usd": cost,
            "concept_count": 1, "frames_used": 0,
            "rubric_scores": False, "verdicts": False, "veto": False,
            "trace": str(trace_path.relative_to(ROOT)),
        })
        print(f"baseline {b['id']}: {wall}s ${out[-1]['cost_usd']:.6f}")
    return out


def run_advanced() -> list[dict]:
    out = []
    for b in BRIEFS:
        trace_path = TRACES_DIR / f"eval_adv_{b['id']}.jsonl"
        t0 = time.monotonic()
        metered = MeteredLLM()
        with TraceRecorder(str(trace_path), meta={
            "brief": b["title"], "run": f"eval_advanced_{b['id']}",
            "mode": "advanced", "model": MODEL,
        }) as rec:
            creator = CreatorAgent(rec, llm=metered)
            judge = JudgeAgent(rec)
            directions = creator.generate(brief_to_model(b))
            verdicts = judge.judge(brief_to_model(b), directions)
            # complex case: human checkpoint + veto of the top-1 — B12 is the
            # multi-stakeholder conflict case; recorded as first-class trace event
            veto_note = None
            if b.get("complex") and verdicts:
                rec.human_checkpoint("judge", "ASSESSMENT: человек проверяет топ-3 перед запуском")
                judge.veto(verdicts[0], "ASSESSMENT: топ-1 игнорирует конфликт с арендодателем — ручное вето")
                veto_note = verdicts[0].direction_id
        wall = round(time.monotonic() - t0, 2)
        tot = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for c in metered.calls:
            for k in tot:
                tot[k] += c["usage"].get(k, 0)
        cost = round(sum(c["cost_usd"] for c in metered.calls), 6)
        scores = {v.direction_id: round(v.total, 1) for v in verdicts}
        approved = [v.direction_id for v in verdicts if v.approved and not v.vetoed]
        out.append({
            "brief_id": b["id"], "brief_title": b["title"], "complex": b.get("complex", False),
            "output_preview": f"{len(directions)} направлений; топ-1: "
                              f"{verdicts[0].direction_id if verdicts else '-'} "
                              f"({verdicts[0].total if verdicts else '-'})",
            "direction_count": len(directions),
            "frames_used": sorted({d.frame for d in directions}),
            "wall_s": wall, "llm_calls": len(metered.calls),
            "tokens": tot, "cost_usd": cost,
            "rubric_scores": True, "verdicts": True, "veto": veto_note,
            "trace": str(trace_path.relative_to(ROOT)),
            "approved": approved, "top_scores": scores,
        })
        print(f"advanced {b['id']}: {wall}s {len(directions)} dir ${cost:.6f}")
    return out


def main():
    args = sys.argv[1:]
    mode = args[0] if args else "baseline"
    only = args[1].split(",") if len(args) > 1 else None   # e.g. "B01,B02,B03"
    RESULTS_DIR.mkdir(exist_ok=True)
    global BRIEFS
    if only:
        BRIEFS = [b for b in BRIEFS if b["id"] in only]
    if mode == "baseline":
        results = run_baseline()
    elif mode == "advanced":
        results = run_advanced()
    else:
        raise SystemExit("mode must be baseline|advanced [B01,B02,...]")
    suffix = ("_" + "_".join(only)) if only else ""
    out = RESULTS_DIR / f"{mode}_results{suffix}.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"saved {out}")


if __name__ == "__main__":
    main()
