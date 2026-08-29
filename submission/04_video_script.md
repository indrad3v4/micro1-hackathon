# Creative Court 2.0 — Demo Video Script (≤5 min) + Recording Script

**Submission:** micro1 Agentic Workflows Hackathon — Frontier Engineering Challenge 2026 (TRACK 1).
**Target length:** 4:30 (hard cap 5:00). **Language:** EN.
**Source-of-truth rule:** every number below is quoted verbatim from `eval/comparison.md`, `IMPROVEMENT_CHANGELOG.md`, `cc-app/evaluation/results/final_report.csv`, or `treasure.md` (TRACK 1 rubric). Nothing invented; modelled/unmeasured figures are labeled on screen.

**Asset inventory used (visuals/, all exist):**
`cc_dashboard_full.png`, `cc_dashboard_scrolled.png`, `demo_01_form_filled.png`, `demo_03_results.png`, `ui_v2_before_header.png`, `ui_v2_after_header.png`, `insight-landscape.png`, `insight-square.png` + live terminal / file views (listed per scene).

---

## PART 1 — Narrative script (voice-over, timed)

### Scene 1 — Problem (0:00–0:40)
**VO:**
"Generative agents produce a flood of plausible creative directions. But the real question — *is this good, for THIS brief, by THIS rubric?* — still burns expensive human time. And an LLM judge without oversight quietly accepts edge cases as truth. Trust, not generation, is the missing layer."
**On-screen text:** "Trust, not generation, is the missing layer."
**View:** terminal → `cat research.md` value block (or the intro slide built from `insight-landscape.png` as backdrop).

### Scene 2 — Baseline (0:40–1:20)
**VO:**
"Every valid submission needs a baseline. The first honest baseline here was one LLM prompt producing one free-text concept per brief. Measured on 12 briefs, same model both sides — `deepseek-v4-flash-vision-exp`: 56.8 seconds and $0.00268 per task on average, with zero structure — no rubric, no alternatives, no trace. One text, and everything is on the human."
**On-screen (labeled "Removed experiment R1"):** avg 56.8 s/task · avg $0.00268/task · 72,875 tokens over 12 cases · free text, no machine-readable outcome.
**View:** `eval/baseline_run.md` open in editor; then `eval/comparison.md` table rows.

### Scene 3 — Live run: Creative Court (1:20–2:20)
**VO:**
"Creative Court: a Creator agent fans one brief into six directions across ИКРА frames — artistic, social, professional, historical, ritual, natural. A Judge agent scores each against contextual rubrics — relevance, novelty, feasibility, risk, quality — vetoes constraint-violating drift, and a replacement loop fills the gap. Every decision lands in a JSONL trace."
**Action (live terminal):**
```
python cc-app/evaluation/run_benchmark.py --brief eval_01_coffee
```
**View:** `demo_01_form_filled.png` (form filled), then `demo_03_results.png` (six directions + scores + verdict), then `cc_dashboard_full.png` → scroll (`cc_dashboard_scrolled.png`).
**Callout:** "6 directions → rubric scores → verdict → veto → replacement → trace."

### Scene 4 — Metrics comparison (2:20–3:20)
**VO:**
"Now the measured improvement — final harness, 10 briefs, identical hand-written drift probes injected into both conditions.
Primary outcome, drift-catch rate: baseline heuristic judge catches 0 of 10 injected violations. Creative Court catches 10 of 10 — including the deliberately contradictory brief, `eval_10_edge_hotel`.
Mean drift-probe score drops from 79.5 to 18.6 — lower means the violation was caught.
Human review time: modelled proxy — 33 minutes down to 7.5 per task. That's a modelled constant, not a stopwatch.
And the real measured numbers: 2,900 seconds wall-clock for 10 tasks, 109 LLM calls, 378,866 tokens, total cost — 10.4 cents. About one US cent per task."
**On-screen table (from `final_report.csv` / Changelog §1):**

| Metric | Baseline | Advanced | Delta |
|---|---|---|---|
| Drift-catch rate | 0/10 (0%) | 10/10 (100%) | +100% |
| Mean drift-probe score | 79.5 | 18.6 | −60.9 pts |
| Human time (modelled proxy) | 33 min | 7.5 min | −77% |
| Wall-clock (10 tasks, measured) | — | 2,900 s | — |
| Tokens (measured) | 0 | 378,866 | — |
| Cost (measured) | $0.00 | $0.10369 | $0.01037/task |

**View:** `cc-app/evaluation/results/final_report.csv` in terminal (`column -s, -t < ...`), then Changelog §1 rendered.

### Scene 5 — Improvement Changelog (3:20–4:10)
**VO:**
"The Improvement Changelog documents every iteration with evidence — and one removed experiment.
Iteration 1: frame-fan + tracing adopted, but the deterministic judge couldn't discriminate — spread of roughly 0–10 points.
Iteration 2: the LLM rubric judge — real discrimination appears, verdict spread 9.8 to 65.0. Pitfall found: the reasoning model can finish with empty content when max_tokens runs out — retry handling added.
Iteration 3: drift veto as a first-class trace event, with a replacement loop.
And the removed experiment: the first harness compared one LLM prompt against the same LLM with structure — not apples-to-apples, unreproducible, paid ~3 cents a task for zero machine-readable signal. Baseline was redefined as a deterministic zero-cost heuristic judge with identical drift probes in both conditions."
**On-screen:** iteration table (Changelog §2) + "Removed: R1 — LLM-as-baseline (§3)".
**View:** `IMPROVEMENT_CHANGELOG.md` scrolled in editor.

### Scene 6 — Hot take (4:10–4:40)
**VO:**
"Hot take. On the contradictory hotel brief, our own earlier advanced run's Judge scored a generic 'Historical angle' 81.0 — the top score of the whole run — while ignoring the brief's core contradiction. On case B12, the top-1 direction ignored a conflict with the landlord; only a human veto caught it. An LLM judge without human veto accepts edge cases as truth — the veto is not a courtesy, it's mandatory. That's why human veto is a first-class event in the trace."
**On-screen:** "LLM judge + no veto = edge case becomes truth. Veto is mandatory."
**View:** `eval/comparison.md` B12 row highlighted; trace file `cc-app/evaluation/results/traces/bench_eval_10_edge_hotel_advanced.jsonl` showing the veto event (B12's own trace predates the final harness naming — the final-harness edge case is `eval_10_edge_hotel`).

### Scene 7 — Close + reproducibility (4:40–4:50)
**VO:**
"Full evidence is committed: final report JSON and CSV, per-brief results, 20 JSONL traces, and a reproduction guide with exact commands, versions, runtime and cost. Creative Court — pay for tokens that work toward your goal."
**View:** `cc-app/evaluation/results/` listing; README reproduction section.

---

## PART 2 — Recording script (shots, timings, exact commands)

Recording setup: 1920×1080, dark terminal theme, font ≥20pt, cursor enlarged. Record with OBS; one take per scene, cut on the timestamps.

| # | Time | Shot / View | Action & exact commands | On-screen text |
|---|---|---|---|---|
| 1 | 0:00–0:40 | Terminal full-screen; then title card over `insight-landscape.png` | Value block source is `treasure.md` (lines ~152–175): `sed -n '152,175p' treasure.md` — or paste the 3 VO sentences as a title slide | "Trust, not generation, is the missing layer." |
| 2 | 0:40–1:20 | Editor: `eval/baseline_run.md`, then `eval/comparison.md` | Open `eval/baseline_run.md`; scroll to per-case table; then `sed -n '5,17p' eval/comparison.md` | "Removed experiment R1 · 56.8 s · $0.00268/task · no structure" |
| 3a | 1:20–1:50 | Show `visuals/demo_01_form_filled.png` full-screen | Static image, slow zoom-in | "Brief: eval_01_coffee — smart coffee machine" |
| 3b | 1:50–2:20 | Terminal live run → `visuals/demo_03_results.png` | `python cc-app/evaluation/run_benchmark.py --brief eval_01_coffee` (real run; if too slow for the take, replay from trace — verified format: events agent_start/agent_step/veto/retry): `grep '"type"' cc-app/evaluation/results/traces/bench_eval_01_coffee_advanced.jsonl | head -20`) → cut to `demo_03_results.png` → pan `cc_dashboard_full.png` → scroll to `cc_dashboard_scrolled.png` framing | "6 directions · rubric · verdict · veto · trace" |
| 4 | 2:20–3:20 | Terminal: metrics table | `column -s, -t < cc-app/evaluation/results/final_report.csv` ; then open `IMPROVEMENT_CHANGELOG.md` §1 headline table. Highlight rows: 0/10 vs 10/10; 79.5→18.6; $0.10369 total | Table from Scene 4; label "human time = modelled proxy, not stopwatch" |
| 5 | 3:20–4:10 | Editor: `IMPROVEMENT_CHANGELOG.md` | Scroll §2 iteration table (rows 0→4); pause on Iteration 2 empty-content pitfall; then jump to §3 "Removed experiment R1"; highlight the three removal reasons | "Every iteration → evidence · one removed experiment" |
| 6 | 4:10–4:40 | Editor: `eval/comparison.md` + terminal: trace | `grep -n "B12\|81.0" eval/comparison.md`; highlight the 81.0 "Historical angle" cell and the B12 veto cell; then show the veto event (verified present): `grep '"type": "veto"' cc-app/evaluation/results/traces/bench_eval_10_edge_hotel_advanced.jsonl` | "Judge scored the generic angle 81.0 — top of the run" · "Veto is mandatory" |
| 7 | 4:40–4:50 | Terminal: evidence tree → end card over `insight-square.png` | `ls cc-app/evaluation/results cc-app/evaluation/results/traces | head -30`; end card: one-liner | "You pay for tokens that work toward your goal — not for tokens that warm the air." |

**Recording checklist:**
- [ ] Every on-screen number matches `final_report.csv` / Changelog §1 exactly (no rounding beyond shown).
- [ ] "Modelled proxy" label visible whenever human-time appears (honesty note, Changelog header).
- [ ] Drift probes described as "identical hand-written probes in both conditions".
- [ ] Scene 6 B12/81.0 claims cite `eval/comparison.md` on screen (it is the source).
- [ ] Total runtime ≤5:00 (target 4:50 with end card).
- [ ] Commands typed live in Scene 3b only; all other terminal shots are pre-verified pastes (no typo risk).
- [ ] No claims about subjective creative quality (Changelog §4: not measured).

**Fact ledger (source → scene):**
- Drift-catch 0/10 → 10/10; probe 79.5→18.6; 33→7.5 min (modelled); 2,900 s; 109 calls; 378,866 tokens; $0.10369; 10 vetoes/10 replacements — Changelog §1 + `final_report.csv`.
- 56.8 s / $0.00268 / 72,875 tokens / 12 briefs (R1) — Changelog §3 + `eval/comparison.md`.
- Verdict spread 9.8–65.0; heuristic spread ~0–10; empty-content pitfall — Changelog §2 (Iterations 1–2).
- B12 veto + 81.0 "Historical angle" — `eval/comparison.md` (rows B09/B12, conclusion 2–3).
- Judge rubric dimensions (relevance/novelty/feasibility/risk/quality), ИКРА frame names, value/bottleneck copy — `treasure.md` + Changelog header.
- TRACK 1 rubric weights (Problem 15 / Engineering 30 / E2E 20 / Measured 15 / Repro 15 / Hot take 5) — `treasure.md` ТРЭК 1 (for editor's self-check, not shown in video).
