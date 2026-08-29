# Reproduction Guide — Creative Court 2.0 (deliverable 03)

**Submission:** micro1 Agentic Workflows Hackathon — Frontier Engineering Challenge 2026 (HackerEarth)
**Harness:** `cc-app/evaluation/run_benchmark.py` · **Model:** `deepseek-v4-flash` · **Python:** 3.12.14 (≥3.11 supported, verified on 3.13)
**Source of truth:** this guide is the reproduction section of the project README (`01_README.md` §3), copied verbatim, with the requirements files and both harness usages appended. Nothing invented.

---

## 3.1 Prerequisites

- **Python 3.12+** recommended (report generated on 3.12.14; `requires-python >= 3.11`, verified working on 3.13).
- **API key** for an OpenAI-compatible endpoint — the harness reads `COMETAPI_KEY` (primary) or `OPENROUTER_API_KEY` / `LLM_API_KEY`. Without a key, run the **baseline only** with `--no-llm` (see 3.4).
- No pip install is required for the **benchmark harness** itself (the `creative-court` runtime is pure stdlib: `urllib`, `dataclasses`, `json`). The `cc-app/requirements.txt` install is only needed if you also want the Reflex dashboard.

## 3.2 Clean-environment setup

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
export LLM_MODEL=deepseek-v4-flash
export LLM_BASE_URL=https://api.cometapi.com/v1
```

## 3.3 One-command reproduction of the full benchmark

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

## 3.4 Partial / offline runs

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

## 3.5 Verified dependency versions

| Component | Version (tested) | Notes |
|---|---|---|
| Python | 3.12.14 (report), ≥3.11 supported | verified on 3.13 too |
| `creative-court` package | 0.1.0 | `dependencies = []` — stdlib only; build backend `uv_build>=0.12.5,<0.13.0` |
| LLM model | `deepseek-v4-flash` | env `LLM_MODEL` |
| LLM endpoint | `https://api.cometapi.com/v1` | OpenAI-compatible, env `LLM_BASE_URL` |
| Judge reject threshold | 60.0 | const `REJECT_THRESHOLD` in `run_benchmark.py` |
| `cc-app` (dashboard only) | reflex==0.9.9 · pydantic≥2.10 (2.13.4) · openai≥1.0 (2.24.0) · fastapi≥0.115 · uvicorn[standard]≥0.34 | Node.js 20+ for the Reflex dev server |

## Requirements files (contents, from `code/`)

`cc-app/requirements.txt` (dashboard only — benchmark harness needs no packages):
```
reflex==0.9.9
pydantic>=2.10.0
openai>=1.0.0
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
```

`creative-court/requirements.txt` (MCP server / API app):
```
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
pydantic>=2.10.0
```

`creative-court/pyproject.toml` — core package, `dependencies = []` (pure stdlib runtime), build backend `uv_build>=0.12.5,<0.13.0`.

## Harness usage (actual CLI)

`cc-app/evaluation/run_benchmark.py`:
```
usage: run_benchmark.py [-h] [--limit LIMIT] [--only ONLY] [--no-llm] [--fresh]

Creator Court measured-improvement benchmark

options:
  -h, --help     show this help message and exit
  --limit LIMIT  run only first N briefs (smoke)
  --only ONLY    comma-separated brief ids to run
  --no-llm       force heuristic mode everywhere (CI/offline)
  --fresh        wipe previous results before running
```

`eval/run_eval.py` — **historical harness of the removed R1 experiment** (12-brief `B01–B12` set, LLM-as-baseline one-shot condition). Kept in the repo as evidence only; **not** the submission harness. Usage: `mode must be baseline|advanced [B01,B02,...]`. Evidence of its measured run: `eval/results/` JSONs (avg 56.8 s/task, avg $0.00268/task, 72 875 tokens over 12 cases), traces in `05_trajectories/agents/eval_base_B*.jsonl` / `eval_adv_B*.jsonl`.

## Reproducibility notes (from README §4, evaluation honesty)

- Primary metric is apples-to-apples: the **identical** drift probe text is judged by both systems on every brief; catch = probe rejected (total < 60) or vetoed.
- `human_time_min` is a **modelled proxy** (documented constants in `run_benchmark.py`), not a stopwatch measurement. Wall-clock, tokens and cost **are measured** (real API usage).
- N = 10 briefs, 1 model, 1 run per brief — a small sample; run-to-run variance is unmeasured.
