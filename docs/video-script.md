# Creative Court 2.0 — Demo Video Script (≤5 min, MCP demo in Hermes)

**Submission:** micro1 Agentic Workflows Hackathon — Frontier Engineering Challenge 2026 (TRACK 1).
**Target length:** 3:30–4:00 (hard cap 5:00). **Language:** EN.
**Source-of-truth rule:** every number quoted verbatim from `cc-app/evaluation/results/final_report.csv`, `IMPROVEMENT_CHANGELOG.md`, `README.md`. Modelled/unmeasured figures labeled on screen.

**Structure = solution-first, demo-first.** The drama is the *problem context* (15 seconds), the *product* is the MCP working live inside Hermes. Judges see the Court as a real tool, not as a story.

---

## PART 1 — Narrative script (voice-over, timed)

### Scene 1 — Problem in one breath (0:00–0:20)
**Visual:** terminal, dark. A line of text types in:
> "Your agent decides faster than you can understand. You sign what it shows you — not what you saw."

**VO (calm, fast):**
"Agentic tools give you speed. The hidden cost: the more you delegate, the less of you is left in the work — yet you sign for all of it. This is a court that fixes exactly that: a judgment layer between your agent and your signature, built as an MCP server."

**On-screen:** "Creative Court — MCP server · judgment layer · the signature stays human"

### Scene 2 — The form of the relationship (0:20–0:40)
**Visual:** minimal diagram, drawn live: `Brief → CreatorAgent → 6 directions → JudgeAgent → verdicts → YOU (veto / sign)`, with `JSONL trace` under it.

**VO:**
"Three roles. A Creator fans your brief into six directions. A Judge scores each against a real rubric — and against the goal *you* stated. You are the signatory: you see every verdict, you can veto with a real reason, and the exact list you approve is bound into the record. The whole court is one MCP server, so it drops into any AI IDE that speaks MCP."

### Scene 3 — LIVE DEMO in Hermes (0:40–2:20) — the heart of the video
**Visual:** real Hermes terminal. `hermes mcp test creative_court` → the 6 tools appear. Then a real agent cycle.

**VO:**
"Here it is live — inside Hermes itself. First, the server is connected: six tools, discovered over MCP. Now we give the Court a real brief — a poetry zine for teens, with a goal: give teens a real place to be published without adult gatekeeping."

**Action (live terminal):**
```
hermes mcp test creative_court
# → court_health, court_run_brief, court_veto, court_sign_off, court_sign_off_all, court_export_trace
```

**VO:**
"We call `court_run_brief`. The Creator fans six directions; the Judge scores them — rubric, plus goal_fit for each. Look at this one: 'Poet-to-Poet Signal'. It respects the constraints on paper, but it drifts from the goal — it's phone-first, and our brief says no smartphone. The human sees it and vetoes — with a real reason."

**Action (live terminal):**
```
court_veto(run_id, "social:Poet-to-Poet Signal",
           "teens must access without a smartphone; this is phone-first")
```

**VO:**
"The veto is not a delete. It becomes a hard requirement. The Creator reworks *the same direction* to answer the reason — and the Judge re-scores it."

**Action (live terminal):**
```
→ reworked: social:Pen-Poem Exchange  → verdict 84.8   (was 38.5)
court_sign_off_all(run_id)   → signed_count, recorded: true
court_export_trace(run_id)   → events, veto=yes, human_checkpoint=yes
```

**VO:**
"Same direction, reworked to answer you. Sign-off binds the exact list into the trace. Every step — veto, retry, human checkpoint — is in the record. That is the whole product: **delegate the generation, keep the verdict.**"

### Scene 4 — Proof: the measured difference (2:20–3:00)
**Visual:** on-screen table (from `final_report.csv`), rows highlight as spoken:

| Metric | Baseline | Court | Delta |
|---|---|---|---|
| Drift-catch rate | 0/10 (0%) | 10/10 (100%) | +100% |
| Mean drift-probe score | 79.5 | 18.6 | −60.9 pts |
| Human time/task (modelled proxy) | 33 min | 7.5 min | −77% |
| Cost/task (measured) | $0.00 | $0.01037 | — |

**VO:**
"Measured, apples-to-apples: same ten briefs, same injected drift probes, two systems. The simple baseline catches none and pushes 33 minutes of re-reading onto you. The Court catches all ten — including the deliberately contradictory hotel brief — for about one US cent per task. Verification tokens, not warm air."

### Scene 5 — Hot take (3:00–3:25)
**Visual:** one line, big: "An LLM judge without a human veto accepts edge cases as truth."

**VO:**
"What we learned: on our own contradictory brief, the LLM judge scored a generic angle 81 — the top score of the run — while ignoring the brief's core contradiction. Only a human veto caught it. Verification without a human veto is theater. The veto is not a courtesy — it is mandatory."

### Scene 6 — Close (3:25–3:45)
**Visual:** end card.
> **Creative Court** — judgment layer as an MCP server.
> Delegate the generation. Keep the verdict.
> "Pay for tokens that work toward your goal — not for tokens that warm the air."

**VO (resolved):**
"Creative Court: the signature stays human. Connect it to any MCP host — Claude Code, Cursor, Cline, Antigravity, Hermes — and start signing what you saw."

---

## PART 2 — Recording script (shots, timings, exact commands)

Recording setup: 1920×1080, dark theme, font ≥20pt, cursor enlarged. OBS; one take per scene, cut on timestamps. Every on-screen number matches `final_report.csv` exactly. **The demo in Scene 3 is a real live run in Hermes — record it in one take.**

| # | Time | Shot / View | Action & exact commands | On-screen text |
|---|---|---|---|---|
| 1 | 0:00–0:20 | Terminal, line types in | Black → text | "Your agent decides faster than you can understand." |
| 2 | 0:20–0:40 | Diagram Creator→Judge→You | Pre-made diagram (or draw live) | "three roles · one MCP server" |
| 3a | 0:40–1:05 | Hermes terminal: mcp test | `hermes mcp test creative_court` (live) | "6 tools discovered over MCP" |
| 3b | 1:05–1:40 | Hermes terminal: run brief | `court_run_brief(title, description, audience, constraints, goal)` (live; if too slow, replay from trace) | "6 directions · rubric · goal_fit" |
| 3c | 1:40–2:00 | Hermes terminal: veto | `court_veto(run, "social:Poet-to-Poet Signal", "teens must access without a smartphone; this is phone-first")` | "veto = hard requirement" |
| 3d | 2:00–2:20 | Hermes terminal: sign + trace | `court_sign_off_all(run)` → `court_export_trace(run)` | "same frame, reworked · sign bound to record" |
| 4 | 2:20–3:00 | Terminal: metrics table | `column -s, -t < cc-app/evaluation/results/final_report.csv` | Table from Scene 4; label "human time = modelled proxy" |
| 5 | 3:00–3:25 | Big line | Text card | "Veto is mandatory" |
| 6 | 3:25–3:45 | End card | Text card + repo link | "The signature stays human." |

**Recording checklist:**
- [ ] Every number matches `final_report.csv` / Changelog §1 (no rounding beyond shown).
- [ ] "Modelled proxy" label visible whenever human-time appears.
- [ ] Drift probes described as "identical hand-written probes in both conditions".
- [ ] Scene 3 veto reason is REAL (the no-smartphone constraint) — the demo shows a genuine veto.
- [ ] Scene 5 claim (81.0 top score on the contradictory brief) cites `IMPROVEMENT_CHANGELOG.md` on screen.
- [ ] Total runtime ≤4:00 (target), hard cap 5:00.
- [ ] No claims about subjective creative quality (not measured).
- [ ] **Scene 3 recorded as ONE live take in Hermes** — the MCP tools must be seen discovering and running, not simulated.

**Fact ledger (source → scene):**
- Drift-catch 0/10 → 10/10; probe 79.5→18.6; 33→7.5 min (modelled); $0.10369; 10 vetoes/10 replacements — `final_report.csv` + Changelog §1.
- Veto rework example (LIVE in Hermes, verified 2026-08-29, `creative-court/traces/run_20260829_195251.jsonl`): `natural:Poetry from the Wild` (78.2) vetoed for budget-constraint breach (its own risks admit "may exceed the 50 EUR budget") → reworked to `natural:Natural angle` 29.0 (rejected) → `artistic:Artistic angle` 71.5 survived → signed. 42 trace events, veto=yes, human_checkpoint=yes.
- Alternative earlier demo (same day, creative-court traces): `social:Poet-to-Poet Signal` → `social:Pen-Poem Exchange` 38.5 → 84.8 — use whichever live run you record; do NOT mix numbers.
- 81.0 "Historical angle" top score on contradictory brief + B12 veto — `IMPROVEMENT_CHANGELOG.md` (comparison, conclusion 2–3).
- Judge rubric dimensions (relevance/novelty/feasibility/risk/quality) + `goal_fit` — README §What this is.
- TRACK 1 rubric weights (Problem 15 / Engineering 30 / E2E 20 / Measured 15 / Repro 15 / Hot take 5) — for editor's self-check, not shown in video.
