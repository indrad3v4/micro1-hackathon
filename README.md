# Creative Court 2.0 — Token Result Gate

**Submission:** micro1 Agentic Workflows Hackathon — Frontier Engineering Challenge 2026 (HackerEarth)
**Repo:** `github.com/indrad3v4/micro1-hackathon` · branch `master` · English only (code, docs, UI)
**Harness:** `cc-app/evaluation/run_benchmark.py` · **Model:** `deepseek-v4-flash-vision-exp` · **Python:** 3.12.14 (≥3.11 supported)

> **One-liner.** *You pay for tokens that work toward your goal — not for tokens that warm the air.*

---

## 1. What this is

Creative Court 2.0 is a **routing layer for meaning** in front of a creative-generation LLM. A `CreatorAgent` fans a product brief out into 6+ creative directions (ИКРА frames: artistic / social / professional / historical / ritual / natural); a `JudgeAgent` scores **every** direction on a contextual rubric (relevance / novelty / feasibility / risk / quality); directions that violate an explicit hard constraint of the brief are **vetoed and replaced** in a retry loop; and the human stays the final authority, with every decision written to an append-only JSONL trajectory (instruction → action → feedback → human checkpoints — submission deliverable 04).

**The problem it solves is token economics, not creativity.** A one-shot generator that is told "here is the brief, go" burns the whole generation budget and hands the human a wall of confident-sounding text that may violate the brief's hard constraints. The user then pays twice: once in tokens for text that missed the goal, once in minutes reading it. The Court inverts the flow — *more* tokens are spent per task, but every one is a **verification** token: judge calls, veto decisions, replacement checks. Token spend becomes a **gate on result**, not a meter of activity.

**Form = token-result gate** (направляющий контур: it directs model parameters at the user's goal and vetoes drift before tokens are burned on the wrong path).

### Measured result (10 briefs, `cc-app/evaluation/results/final_report.json`)

| Metric | Baseline (heuristic judge, 0 LLM calls) | Advanced (Creative Court 2.0) | Delta |
|---|---|---|---|
| **Drift-catch rate** (primary outcome) | **0 / 10** (0 %) | **10 / 10** (100 %) | **+100 %** |
| Mean drift-probe score (lower = caught better) | 79.5 | 18.6 | −60.9 pts |
| Human review time per task (modelled proxy) | 33.0 min | 7.5 min | −25.5 min / task (−77 %) |
| LLM spend, 10 tasks (measured, incl. `usage.cost`) | $0.00 | **$0.10369** | **$0.01037 / task** |
| Tokens, 10 tasks (measured) | 0 | 378 866 | — |
| LLM calls, 10 tasks (measured) | 0 | 109 | — |
| Wall-clock, 10 tasks (measured) | ~0.04 s / task | 2 900 s (~48 min) | — |
| Vetoes / replacements | 0 | 10 / 10 | — |

Every brief received the **same hand-written drift probe** (a confident-sounding direction that violates a hard constraint but is lexically saturated with brief keywords) in both conditions. The baseline was fooled by every probe; the Court rejected all 10 — including the deliberately contradictory `eval_10_edge_hotel`.

**Why the baseline's zero token spend is the hidden cost:** 0 LLM calls and $0.00 sounds free, but the heuristic judge is not a judge — it rubber-stamps constraint-violating directions (mean probe score 79.5), so the human pays 33 modelled minutes per task re-checking work that already missed the goal. The Court's ~1-cent-per-task verification spend buys certainty that every parameter activated served the brief.

---

## 2. Repository layout

```
micro1-hackathon/
├── creative-court/            # core agent package (stdlib-only runtime)
│   ├── pyproject.toml         # dependencies = [] — no runtime deps
│   ├── src/creative_court/
│   │   ├── agents/{creator,judge}.py
│   │   └── core/{llm,models,trace}.py
│   ├── demo_briefs/eval_01..10.json
│   └── traces/*.jsonl         # agent trajectories (deliverable 04)
├── cc-app/                    # Reflex.dev dashboard + benchmark harness
│   ├── requirements.txt       # reflex==0.9.9, pydantic>=2.10, openai>=1, ...
│   ├── cc_app/                # dashboard (reflex run)
│   └── evaluation/run_benchmark.py   # ← the benchmark (single file)
├── prompts/{creator,judge}_prompt.txt
├── docs/orchestration-prd.md
├── orchestration/state.json   # self-proof gate state (hackathon QA)
├── IMPROVEMENT_CHANGELOG.md   # baseline → iterations → final + removed experiment
└── README.md                  # you are here
```

---

## 3. Reproduction guide

### 3.1 Prerequisites

- **Python 3.12+** recommended (report generated on 3.12.14; `requires-python >= 3.11`, verified working on 3.13).
- **API key** for an OpenAI-compatible endpoint — the harness reads `COMETAPI_KEY` (primary) or `OPENROUTER_API_KEY` / `LLM_API_KEY`. Without a key, run the **baseline only** with `--no-llm` (see 3.4).
- No pip install is required for the **benchmark harness** itself (the `creative-court` runtime is pure stdlib: `urllib`, `dataclasses`, `json`). The `cc-app/requirements.txt` install is only needed if you also want the Reflex dashboard.

### 3.2 Clean-environment setup

```bash
git clone https://github.com/indrad3v4/micro1-hackathon.git
cd micro1-hackathon

# optional but recommended: isolated venv
python3 -m venv .venv && source .venv/bin/activate

# benchmark harness needs NO packages — stdlib only.
# dashboard only (if you want the UI):
# pip install -r cc-app/requirements.txt && cd cc-app && reflex run

# credentials + model wiring (OpenAI-compatible)
export COMETAPI_KEY=sk-...            # or OPENROUTER_API_KEY / LLM_API_KEY
export LLM_MODEL=deepseek-v4-flash-vision-exp
export LLM_BASE_URL=https://api.cometapi.com/v1
```

### 3.3 One-command reproduction of the full benchmark

```bash
python cc-app/evaluation/run_benchmark.py --fresh
```

`--fresh` wipes only the per-brief caches of the briefs being run, then re-runs **all 10 briefs end-to-end** (baseline + advanced per brief) and regenerates `final_report.json` / `final_report.csv` / `results/traces/*.jsonl`. No `--fresh` = resume: cached per-brief results are reused and missing briefs are computed, then merged into one report.

**Expected outputs** (created under `cc-app/evaluation/results/`):

| File | Contents |
|---|---|
| `final_report.json` | full machine-readable evidence (meta + summary + per-brief baseline/advanced blocks) |
| `final_report.csv` | one row per brief + totals |
| `per_brief/<id>.json` | crash-safe incremental per-brief results |
| `traces/bench_eval_<id>_{baseline,advanced}.jsonl` | one trajectory pair per brief (TraceRecorder format) |

**Expected runtime & cost** (measured, from `final_report.json`):

- **Wall-clock:** ~2 900 s (~48 min) for the full 10-brief advanced run; dominated by LLM latency. The deterministic baseline is ~0.034–0.085 s per task.
- **Cost:** **$0.10369 total → $0.01037 per task** (10 tasks; 378 866 tokens; 109 LLM calls). Verified from `usage.cost` when the API reports it, else a chars/4-token estimate (flagged `usage_estimated`).
- Cost math is linear and auditable: `per_task = total / n_briefs = 0.10369 / 10 = 0.01037`. A single smoke brief (`--limit 1`) costs ≈ **$0.01** (measured per-brief range across the 10 tasks: $0.0061–$0.0165).

### 3.4 Partial / offline runs

```bash
# smoke test — first 2 briefs only
python cc-app/evaluation/run_benchmark.py --limit 2

# single brief
python cc-app/evaluation/run_benchmark.py --only eval_10_edge_hotel

# offline / no API key — forces heuristic mode in BOTH conditions (CI-safe)
python cc-app/evaluation/run_benchmark.py --no-llm
```

`--fresh`, `--limit` and `--only` compose: `--fresh --limit 2` wipes and re-runs only the first two briefs' caches, leaving the rest untouched.

> ⚠️ `--no-llm` overwrites per-brief caches with heuristic-only results. Run it on a **copy** of the repo if you want to keep real LLM evidence.

### 3.5 Verified dependency versions

| Component | Version (tested) | Notes |
|---|---|---|
| Python | 3.12.14 (report), ≥3.11 supported | verified on 3.13 too |
| `creative-court` package | 0.1.0 | `dependencies = []` — stdlib only; build backend `uv_build>=0.12.5,<0.13.0` |
| LLM model | `deepseek-v4-flash-vision-exp` | env `LLM_MODEL` |
| LLM endpoint | `https://api.cometapi.com/v1` | OpenAI-compatible, env `LLM_BASE_URL` |
| Judge reject threshold | 60.0 | const `REJECT_THRESHOLD` in `run_benchmark.py` |
| `cc-app` (dashboard only) | reflex==0.9.9 · pydantic≥2.10 (2.13.4) · openai≥1.0 (2.24.0) · fastapi≥0.115 · uvicorn[standard]≥0.34 | Node.js 20+ for the Reflex dev server |

---

## 4. Evaluation honesty notes

From `final_report.json` → `meta.interpretation_notes`:

- **Primary metric is apples-to-apples:** the *identical* drift probe text is judged by both systems on every brief; catch = probe rejected (total < 60) or vetoed.
- **Mean verdict scores are NOT cross-condition comparable** as a quality scale: baseline scores come from a lenient lexical heuristic, advanced from a strict LLM rubric. The within-condition signal is *discrimination* (`score_spread` = max−min verdict total, measured from per-brief data): the heuristic cluster is a constant ~9.5 pts on every brief, while the LLM judge spreads verdicts 9.8–65.0 pts — widest (65.0) exactly on the deliberately contradictory edge brief, where the heuristic was at its most fooled.
- `human_time_min` is a **modelled proxy** (documented constants in `run_benchmark.py`), not a stopwatch measurement. Wall-clock, tokens and cost **are measured** (real API usage).
- **N = 10 briefs, 1 model, 1 run per brief.** A small sample; run-to-run variance is unmeasured — these figures are submission evidence, not a general benchmark.
- Advanced LLM call counts include retries of the reasoning model's empty-content answers (a known `deepseek-v4-flash-vision-exp` pitfall, clamped `max_tokens` + bigger retry budget).

## 5. Evidence paths (all committed on `master`)

- `cc-app/evaluation/results/final_report.json` — machine-readable evidence (source of truth for all numbers above)
- `cc-app/evaluation/results/final_report.csv` — one row per brief + totals
- `cc-app/evaluation/results/per_brief/*.json` — crash-safe per-brief results (10)
- `cc-app/evaluation/results/traces/bench_eval_*_{baseline,advanced}.jsonl` — benchmark trajectory pairs (20; 10 baseline + 10 advanced)
- `creative-court/traces/*.jsonl` — agent trajectories (deliverable 04)
- `cc-app/traces/traces/dashboard_*.jsonl` — live Reflex dashboard session trace (interactive human-in-the-loop run; heuristic fallback — no API key at demo time)
- `visuals/demo_*.png` — dashboard demo screenshots (form filled + results)
- `IMPROVEMENT_CHANGELOG.md` — baseline → Iterations 1–3 → Final, with the removed R1 experiment

## 6. Trajectory format (submission requirement 04)

Every trace is **append-only JSONL** written by `TraceRecorder` (`creative-court/src/creative_court/core/trace.py`) with atomic per-line `fsync`. Each line is one flat event with 12 keys:

```jsonc
{"ts": "…ISO-8601 UTC…", "agent": "creator|judge|harness|…",
 "type": "agent_start|agent_step|agent_end|tool_call|tool_response|veto|retry|human_checkpoint",
 "instruction": "…", "action": "…", "tool": "…", "tool_response": "…",
 "feedback": "…", "retry_of": "…", "human_checkpoint": "…", "verdict": "…", "data": {…}}
```

The four submission-required aspects map directly onto schema fields — **instruction → action → feedback → human checkpoints**:

| Requirement | Schema field(s) | Example (from `creative-court/traces/eval_adv_B12.jsonl`) |
|---|---|---|
| instruction | `instruction` | the brief + direction prompt passed to the agent |
| action | `action` / `tool` / `tool_response` | `"action": "verdict for artistic:Artistic angle"` + `tool: "llm"` |
| feedback | `feedback` | `"feedback": "Artistic angle: 64.3/100 — approved"` |
| human checkpoints | `type: "human_checkpoint"` + `human_checkpoint` | `"human_checkpoint": "ASSESSMENT: человек проверяет топ-3 перед запуском"` |

Veto and retry events additionally record the court's drift-catch mechanics (`veto`, `retry_of`), so the 10/10 drift-catch result is auditable event-by-event, not just as a summary number. All 56 committed trace files validate against this schema (checked programmatically: 0 malformed lines).

**Trace coverage honesty.** Benchmark traces (`results/traces/bench_eval_*`) contain **zero `human_checkpoint` events by design**: `run_benchmark.py` is a *headless* harness — no human reviews during an automated run, so nothing is checkpointed. Human-checkpoint capability lives in the interactive path: the schema field, the single `human_checkpoint` event in `creative-court/traces/eval_adv_B12.jsonl` (`ASSESSMENT: человек проверяет топ-3 перед запуском`), and the Reflex dashboard session trace (`cc-app/traces/traces/dashboard_*.jsonl`). Likewise, baseline bench traces carry **no `tool_call`/`tool_response` events because the baseline makes 0 LLM calls** — the heuristic judge does no tool use; the absence *is* the measured zero, not a recording gap. Advanced bench traces carry `tool_response` (LLM verdicts), `veto` (17) and `retry` (25) events.

---

## 7. Hot Take — unrouted tokens are the hidden cost

Most agentic designs treat **generation** as the expensive part and **checking** as the cheap part. This benchmark measures the opposite.

The baseline "spends nothing" — 0 LLM calls, $0.00, ~0.04 s/task (measured) — and still fails the goal: it accepts all 10 constraint-violating drift probes (mean probe score 79.5/100) because its check is a rubber-stamp. The bill does not disappear; it is deferred to the most expensive interpreter in the loop, the human: 33 modelled minutes per task re-reading directions that already missed the brief.

The Court inverts the cost curve. It spends **~1 US cent per task** (measured: `$0.01037/task`, 10.9 LLM calls, ~37 900 tokens) — but every token is a *verification* token: rubric-judge calls, veto decisions, replacement checks. Result: 10/10 drift probes caught, probe mean 79.5 → 18.6, human time 33 → 7.5 min per task (**25.5 min saved**).

The arithmetic: **$0.01 of QA buys back 25.5 minutes of human attention** (~2 500 minutes per dollar). The most expensive model call in an agentic workflow is the one you never vetoed, because its output still has to be read. Token spend should be a **gate on result**, not a meter of activity: route tokens through a veto gate and the marginal cent pays for certainty — not for tokens that warm the air.
