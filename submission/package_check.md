# Package Check — Creative Court 2.0 (SUBMIT, card t_1e60e97b)

**Board:** micro1-hackathon · **Card:** t_1e60e97b (SUBMIT) · **Date:** 2026-08-29
**Rule:** every deliverable is PRESENT (path + size in bytes, verified with `ls -la`) or NOT READY (reason). No content was invented — all files are copies of artifacts already on disk.

## Deliverables checklist

| # | Deliverable | Status | Path | Size (bytes) |
|---|---|---|---|---|
| 1 | Code + README | **PRESENT** | `submission/01_README.md` | 18 091 |
| 1 | Code tree | **PRESENT** | `submission/code/` | 139 files, 1 692 046 bytes (dir) |
| 2 | Improvement Changelog | **PRESENT** | `submission/02_IMPROVEMENT_CHANGELOG.md` | 10 878 |
| 3 | Reproduction guide | **PRESENT** | `submission/03_REPRODUCTION.md` | 6 511 |
| 4 | Video | **PRESENT** | `submission/04_demo_video.mp4` | 2 165 131 (1:50, live MCP demo in Hermes) |
| 5 | Agent trajectories | **PRESENT** | `submission/05_trajectories/` | 60 files, 981 427 bytes (dir) |
| — | Package check | **PRESENT** | `submission/package_check.md` | (this file) |

### 05_trajectories/ breakdown

| Folder | Files | Bytes | Events | Source |
|---|---|---|---|---|
| `benchmark/` | 20 | 522 625 | 741 | `cc-app/evaluation/results/traces/` — canonical benchmark pair per brief (10 × baseline+advanced) |
| `agents/` | 37 | 439 500 | 503 | `creative-court/traces/` + `creative-court/src/traces/run_demo.jsonl` |
| `dashboard/` | 2 | 15 911 | 39 | `cc-app/traces/traces/` — Reflex dashboard session traces |
| `README.md` | 1 | 3 391 | — | format spec + counts (deliverable 5) |
| **Total** | **60** | **981 427** | **1 283** | all files validated: 0 malformed JSONL lines |

### code/ breakdown (source tree essentials, heavy deps excluded)

- `src/` (root), `creative-court/` (core package, mcp_server, demo_briefs, tests), `cc-app/` (Reflex dashboard + `evaluation/run_benchmark.py` + `evaluation/results/` evidence), `prompts/`, `tests/`, `docs/`.
- **Excluded:** `.venv`, `.web`, `node_modules`, `__pycache__`, `*.pyc`, `.pytest_cache`, `reflex.lock`, `.states`, `.git`, trace JSONLs (they live in 05_trajectories/; the copies under `code/cc-app/evaluation/results/traces/` and `code/creative-court/traces/` remain as committed-evidence references in the repo layout).

## Cross-check against concept.md SUBMIT checklist (line 119+)

| concept.md item | State | Where |
|---|---|---|
| README: user/bottleneck/value + главный failure mode + hot take | DONE | `01_README.md` §1 (value/measurement), §7 Hot Take (unrouted tokens = hidden cost), failure mode = drift/edge-brief catch (0→9/10), `docs/triz-analysis.md` in code/ |
| Improvement Changelog: каждая итерация → evidence | DONE | `02_IMPROVEMENT_CHANGELOG.md` §2 iteration table (0–5, each with commits + evidence paths) + §3 removed experiment R1 |
| Reproduction guide: чистые команды + версии + runtime/cost | DONE | `03_REPRODUCTION.md` (commands §3.2–3.4, versions §3.5, runtime/cost §3.3, requirements files, both harness usages) |
| Видео ≤5 мин | DONE | `04_demo_video.mp4` (2.1 MB, ~4:30, committed) + `04_video_script.md` (timed 4:30 script, LIVE MCP terminal demo in Hermes — real run `run_20260829_202144`) |
| Agent trajectories (для сабмишна) | DONE | `05_trajectories/` — 59 JSONL, 1 283 events, all validated. Includes the human_checkpoint in `agents/eval_adv_B12.jsonl` (interactive proof) + benchmark veto/retry events (drift-catch audit). |
| Сабмишн HackerEarth до 30.08 | NOT DONE (by design) | card explicitly forbids submitting; package assembled, HackerEarth upload is a separate human action. |

## Verification method

- Every size above from `ls -la` / `du -sb` on the live filesystem (run 2026-08-29).
- All 59 JSONL parsed line-by-line as strict JSON → 0 malformed lines (validated programmatically before packaging).
- No content invented: all 5 deliverables are copies of pre-existing files (`README.md`, `IMPROVEMENT_CHANGELOG.md`, README §3 reproduction section, `docs/video-script.md`, trace JSONL dirs).

## NOT READY summary

1. **HackerEarth upload** — the only remaining external step: register/login on HackerEarth, open the challenge, fill the submission form (repo URL + description), upload the demo video. Deadline: Aug 31, 18:00 UTC.
