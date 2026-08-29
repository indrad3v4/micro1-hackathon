# Improvement Changelog — Creative Court 2.0

**Submission:** micro1 Agentic Workflows Hackathon — Frontier Engineering Challenge 2026 (HackerEarth)
**Project:** Creative Court 2.0 — an agentic system where a Creator agent generates a fan of creative directions from a product brief and a Judge agent scores them on a contextual rubric, vetoes constraint-violating drift, and leaves the human as the final authority (trace-logged override).
**Benchmark:** `creator-court-measured-improvement-v1` — 10 demo briefs, one deliberately contradictory "edge" brief, one hand-written constraint-violating **drift probe** per brief (identical text in both conditions).
**Harness:** `cc-app/evaluation/run_benchmark.py` · **Model:** `deepseek-v4-flash-vision-exp` · **Python:** 3.12.14 · **Generated (UTC):** 2026-08-29T06:47:11Z

> **Honesty notes (from the report's `interpretation_notes`):** mean verdict scores are **not** cross-condition comparable as a quality scale (baseline = lenient lexical heuristic, advanced = strict LLM rubric); `human_time_min` is a **modelled proxy** (constants in `run_benchmark.py`), not measured; wall-clock, tokens and cost **are measured** (real API usage incl. `usage.cost`).

---

## 1. Headline result (measured)

| Metric | Baseline | Advanced (Creative Court 2.0) | Delta |
|---|---|---|---|
| **Drift-catch rate** (primary outcome) | **0 / 10** (0%) | **10 / 10** (100%) | **+100%** |
| Mean drift-probe score (lower = caught better) | 79.5 | 18.6 | −60.9 pts |
| Human time per task (modelled proxy) | 33 min | 7.5 min | −77% (255 min saved across 10 tasks) |
| LLM calls (advanced) | 0 | 109 | — |
| Wall-clock, 10 tasks (advanced, measured) | — | 2 900 s (~48 min) | — |
| Tokens, 10 tasks (advanced, measured) | 0 | 378 866 | — |
| **Cost, 10 tasks (advanced, measured)** | $0.00 | **$0.10369** | **$0.01037 / task** |
| Vetoes / replacements (advanced) | 0 | 10 / 10 | — |

The baseline catches **none** of the 10 injected constraint violations; Creative Court 2.0 catches **all 10** — including on `eval_10_edge_hotel`, a deliberately contradictory brief — at **~1 US cent per task** of LLM spend, with a ~77 % modelled reduction in human review time.

---

## 2. Iteration table (Baseline → Iteration 1..3 → Final)

| # | Stage | What changed | Evidence | Decision |
|---|---|---|---|---|
| 0 | **Baseline** — "one-shot heuristic judge" | Deterministic `JudgeAgent._heuristic_score` path (word-overlap / frame-table scoring). Zero reasoning, zero LLM calls, $0.00, ~0.034–0.085 s/task measured wall-clock (mean ~0.041 s). Same 10 briefs + same drift probes as advanced. | `cc-app/evaluation/results/final_report.json` (`meta`, baseline blocks) · `final_report.csv` (baseline cols) · `results/traces/bench_eval_XX_baseline.jsonl` | **Keep as the honest simple baseline.** It is fooled by keyword-saturated probes (mean probe score 79.5 → 0/10 caught): a lexical judge is not a judge. |
| 1 | **Iteration 1** — Creator agent + deterministic judge | `8133f19`: initial `creative-court` codebase — CreatorAgent generates 6 ИКРА-frame directions (artistic/social/professional/historical/ritual/natural); JudgeAgent scores deterministically; TraceRecorder writes JSONL trajectories; 10 demo briefs + first eval results. | commit `8133f19` · `creative-court/src/creative_court/agents/` · `creative-court/traces/*.jsonl` · `eval/comparison.md` (assumption 3: judge was deterministic scoring over LLM content) | **Adopt frame-fan + tracing, but the judge is still too weak.** Deterministic scoring shows almost no discrimination (baseline-style spread ~0–10 pts) — cannot separate strong from weak creative directions. |
| 2 | **Iteration 2** — LLM-powered contextual Judge | `ce3610c` + `2dbabe4`: JudgeAgent now scores every direction with an **LLM rubric prompt** (relevance / novelty / feasibility / risk / quality) and improved Creator prompts. Real discrimination appears (final-run verdict spread 9.8–65.0 pts; Iteration-1's heuristic spread of ~0–10 pts is inferred from the harness interpretation note — no separate Iteration-1 artifact exists). | commit `ce3610c` · commit `2dbabe4` · `prompts/judge_prompt.txt`, `prompts/creator_prompt.txt` · per-brief verdicts in `final_report.json` (e.g. `eval_01_coffee`: scores 28.0–65.4, spread 34.6) | **Adopt.** LLM judge produces a genuinely critical, reason-backed verdict. New pitfall surfaced: `deepseek-v4-flash-vision-exp` is a reasoning model that can finish with *empty content* when `max_tokens` is exhausted → retry handling needed (recorded as `retry` trace events). |
| 3 | **Iteration 3** — drift probe + veto + replacement loop | Drift **veto** becomes first-class (Court veto event on explicit hard-constraint violation) with a **replacement retry loop**; FastAPI demo (`91b2f3d`), Reflex dashboard `143fcba`, trajectory tracking `f3b6dc9`. Harness injects identical drift probes into both conditions for an apples-to-apples primary metric. | commits `2dbabe4`, `91b2f3d`, `143fcba`, `f3b6dc9` · `cc-app/evaluation/run_benchmark.py` (probe + veto + retry sections) · `cc-app/evaluation/results/traces/bench_eval_*_advanced.jsonl` (veto + retry events, 10 files) · `creative-court/traces/eval_adv_B12.jsonl` (old-harness veto prototype) | **Adopt.** This is the capability that makes the primary metric measurable: rejected drift directions are vetoed (10 vetoes) and replaced (10 replacements), each landing in the trace. |
| 4 | **Final** — full 10-brief benchmark | Full harness run on all 10 briefs (incl. contradictory `eval_10_edge_hotel`). Drift catch **0/10 → 10/10**; 10 vetoes + 10 replacements; $0.10369 total LLM cost; 109 calls; 378 866 tokens; modelled human time 330 → 75 min. | `ceebbb4` + `67d969a` · `cc-app/evaluation/results/final_report.json` + `.csv` + `results/per_brief/*.json` + `results/traces/*.jsonl` | **Freeze as submission evidence.** No further capability changes; remaining work is packaging (README reproduction guide, trajectory bundle, video). |

---

## 3. Removed experiment (R1) — "LLM-as-baseline" one-shot free-text condition

**What was tried.** The first evaluation harness (`eval/run_eval.py`, 28.08, 12 briefs `B01–B12`) defined the baseline as **one single LLM prompt** producing one free-form concept text ("Ты креативный консультант… придумай концепцию одним связным текстом"), with the advanced condition built on the same LLM.

**Evidence it existed.** `eval/baseline_run.md` (definition + per-case table) · `eval/comparison.md` (comparison) · `eval/results/baseline_results.json`, `eval/results/merged_baseline.json` (measured runs: avg **56.8 s/task**, avg **$0.00268/task**, 72 875 tokens over 12 cases, 2 reasoning-empty retry blowups of 178–192 s) · traces `creative-court/traces/eval_base_B01..B12.jsonl`.

**Why it was removed.**
1. **Not apples-to-apples.** Both conditions used the same LLM, so the comparison measured *generator* quality, not the agentic *judge* layer this project is about — and free text cannot be rubric-scored, so there was no machine-readable primary outcome.
2. **Slow and paid for zero measurable signal.** ~57 s and ~$0.003 per task to produce text that then had to be read by a human.
3. **Unreproducible.** Results depended on live paid API calls with nondeterministic reasoning-mode blowups (empty-content retries).

**Replacement decision.** Baseline was redefined as a **deterministic, zero-cost, zero-LLM heuristic judge** (measured wall-clock 0.034–0.085 s/task, $0.00) with **identical hand-written drift probes** injected into both conditions. Drift-catch then becomes a clean, apples-to-apples, fully reproducible primary metric — the baseline is cheap precisely because it is simple, which is the point of a baseline.

**What was kept from the removed experiment.** The 12-brief case set, the contradictory-brief pattern (B12 → `eval_10_edge_hotel`), and the empty-content retry mitigation all carried over into the final harness. The old harness files remain in the repo under `eval/` as historical evidence (git-ignored result JSONs are force-tracked).

---

## 4. What is NOT claimed

- Subjective creative "quality" (which idea is *better*) is **not** measured — rubric scores measure the structure of selection, not truth. A live human review is the honest next step.
- `human_time_min` is a **modelled proxy** (documented constants in `run_benchmark.py`), not a stopwatch measurement.
- N = 10 briefs, 1 model, 1 run per brief — a small sample; run-to-run variance is **unmeasured** (a single contaminated run could in principle move the primary metric), so figures are submission evidence, not a general benchmark.

## 5. Evidence paths (all committed, branch `master`)

- `cc-app/evaluation/results/final_report.json` — full machine-readable evidence
- `cc-app/evaluation/results/final_report.csv` — one row per brief + totals
- `cc-app/evaluation/results/per_brief/*.json` — crash-safe per-brief results (10 files)
- `cc-app/evaluation/results/traces/*.jsonl` — benchmark trajectory pair per brief (baseline + advanced)
- `eval/baseline_run.md`, `eval/comparison.md`, `eval/results/*.json` — removed-experiment (R1) evidence
- `creative-court/traces/*.jsonl` — agent trajectories (submission deliverable 04)
