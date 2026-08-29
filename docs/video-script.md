# Creative Court 2.0 — Demo Video Script (≤5 min, drama-driven)

**Submission:** micro1 Agentic Workflows Hackathon — Frontier Engineering Challenge 2026 (TRACK 1).
**Target length:** 3:45–4:00 (hard cap 5:00). **Language:** EN.
**Source-of-truth rule:** every number quoted verbatim from `cc-app/evaluation/results/final_report.csv`, `IMPROVEMENT_CHANGELOG.md`, `README.md`. Modelled/unmeasured figures labeled on screen.

**Structure = the tension, escalated then resolved.** Open on the drama, not the logo. The metrics serve the story, not the other way around.

---

## PART 1 — Narrative script (voice-over, timed)

### Scene 1 — Hook: the drama (0:00–0:25)
**Visual:** black screen, white text types in:
> "I signed what I was shown — not what I saw."

**VO (slow, cold):**
"That sentence is the real cost of delegating to agents. Your agent decides faster than you can understand. You approve what it shows you. You sign for what you never saw. The speed feels like winning — until the bill arrives."

**On-screen (small, below):** "generation speed ↑  ·  your presence in the work ↓"

### Scene 2 — The tension (0:25–0:50)
**Visual:** two lines diverging on a dark graph — "what the agent does" climbs, "what you understand" falls. The gap widens.

**VO:**
"Here is the tension nobody prices. The more you delegate, the more gets done — and the less of you is left in the work. Yet you're the one who signs for all of it. Delegate faster, and you go blind faster. That is not a bug in your agent. It is the hidden tax on delegation itself."

**On-screen:** "Driver: delegate → speed. Barrier: delegate → blindness. One action, both grow."

### Scene 3 — The insight + the Court (0:50–1:15)
**Visual:** the gap closes as a third element appears — the Court between agent and human.

**VO:**
"So we built the missing layer: a judgment court between your agent and your signature. One agent — the Creator — fans your brief into six directions. Another — the Judge — scores each against a real rubric, and against your stated goal. And when something drifts, you — a human — can veto it with a real reason."

**On-screen:** "Creator → Judge → Human. The signature stays human."

### Scene 4 — Live demo: veto that changes the work (1:15–2:20)
**Visual:** live terminal → `court_run_brief` (poetry zine brief, goal: "give teens a real place to be published without adult gatekeeping") → 6 directions with verdicts → agent presents → human spots drift.

**VO (paced, matter-of-fact):**
"Live. We give the Court a brief — a poetry zine for teens, goal: a real place to be published. It fans six directions and the Judge scores them. But look at this one — 'Poet-to-Poet Signal'. It respects every constraint... except the goal we actually stated: no adult gatekeeping, and no smartphone-first dependency. So we veto it — with the real reason."

**Visual:** `court_veto(run, direction, "teens must access without a smartphone; this is phone-first")`.

**VO:**
"The veto is not a delete button. It is a hard requirement. The Creator reworks *the same direction* to answer the reason — and the Judge re-scores it."

**Visual:** side-by-side: `Poet-to-Poet Signal 38.5 → Pen-Poem Exchange 84.8` (same frame, reworked). Then `court_sign_off` → `data.signed` recorded → trace export.

**VO:**
"Same direction, reworked to answer you. And when you sign, the exact list you approved is bound into the record — provable, replayable."

### Scene 5 — Proof: the measured difference (2:20–3:00)
**Visual:** on-screen table (from `final_report.csv`), rows highlight as spoken:

| Metric | Baseline | Court | Delta |
|---|---|---|---|
| Drift-catch rate | 0/10 (0%) | 10/10 (100%) | +100% |
| Mean drift-probe score | 79.5 | 18.6 | −60.9 pts |
| Human time/task (modelled proxy) | 33 min | 7.5 min | −77% |
| Cost/task (measured) | $0.00 | $0.01037 | — |

**VO:**
"Measured, apples-to-apples: the same ten briefs, the same injected drift probes, two systems. The simple baseline catches none of them and pushes 33 minutes of re-reading onto you. The Court catches all ten — including the deliberately contradictory hotel brief — for about one US cent per task. That is not free. It is the opposite of free: it is the one cent that buys back your attention."

### Scene 6 — Hot take (3:00–3:30)
**Visual:** one line, big: "An LLM judge without a human veto accepts edge cases as truth."

**VO:**
"Here is what we learned building this. On our own contradictory brief, the LLM judge scored a generic angle 81 — the top score of the whole run — while ignoring the brief's core contradiction. Only a human veto caught it. Verification without a human veto is theater. The veto is not a courtesy. It is mandatory."

### Scene 7 — Close: the signature (3:30–3:55)
**Visual:** the opening sentence returns, now complete:

> "I signed what I was shown — not what I saw."
> *"Now I sign what I saw."*

**VO (warm, resolved):**
"Delegate the generation. Keep the verdict. Your signature means something again."

**End card:**
> **Creative Court** — *the signature stays human.*
> "Pay for tokens that work toward your goal — not for tokens that warm the air."

---

## PART 2 — Recording script (shots, timings, exact commands)

Recording setup: 1920×1080, dark theme, font ≥20pt, cursor enlarged. OBS; one take per scene, cut on timestamps. Every on-screen number matches `final_report.csv` exactly.

| # | Time | Shot / View | Action & exact commands | On-screen text |
|---|---|---|---|---|
| 1 | 0:00–0:25 | Black → white text types in | Title card: the hook sentence | "I signed what I was shown — not what I saw." |
| 2 | 0:25–0:50 | Animated divergence (two lines) | Pre-made animation (PowerPoint/After Effects) or `matplotlib` line chart | "One action, both grow" |
| 3 | 0:50–1:15 | Diagram: Creator → Judge → Human | Pre-made diagram (see `visuals/` if exists, else draw) | "The signature stays human" |
| 4a | 1:15–1:40 | Terminal: run brief | `python creative-court/mcp_server.py` + client call `court_run_brief` (or replay from trace) | "6 directions · rubric · goal" |
| 4b | 1:40–2:00 | Terminal: veto | `court_veto(run, "social:Poet-to-Poet Signal", "teens must access without a smartphone; this is phone-first")` | "veto = hard requirement" |
| 4c | 2:00–2:20 | Side-by-side scores + sign-off | Show `38.5 → 84.8` rework; then `court_sign_off` → `data.signed`; then `court_export_trace` | "same frame, reworked · sign bound to record" |
| 5 | 2:20–3:00 | Terminal: metrics table | `column -s, -t < cc-app/evaluation/results/final_report.csv` | Table from Scene 5; label "human time = modelled proxy" |
| 6 | 3:00–3:30 | Big line | Text card | "Veto is mandatory" |
| 7 | 3:30–3:55 | Opening sentence returns, complete | Text card + end card | "Now I sign what I saw." · "The signature stays human." |

**Recording checklist:**
- [ ] Every number matches `final_report.csv` / Changelog §1 (no rounding beyond shown).
- [ ] "Modelled proxy" label visible whenever human-time appears.
- [ ] Drift probes described as "identical hand-written probes in both conditions".
- [ ] Scene 4 veto reason is REAL (the no-smartphone constraint) — the demo must show a genuine veto, not a scripted one.
- [ ] Scene 6 claim (81.0 top score on the contradictory brief) cites `IMPROVEMENT_CHANGELOG.md` / comparison on screen.
- [ ] Total runtime ≤4:00 (target), hard cap 5:00.
- [ ] No claims about subjective creative quality (not measured).

**Fact ledger (source → scene):**
- Drift-catch 0/10 → 10/10; probe 79.5→18.6; 33→7.5 min (modelled); $0.10369; 10 vetoes/10 replacements — `final_report.csv` + Changelog §1.
- Veto rework example (`Poet-to-Poet Signal` → `Pen-Poem Exchange`, 38.5 → 84.8) — live MCP demo run (verified 2026-08-29, creative-court traces).
- 81.0 "Historical angle" top score on contradictory brief + B12 veto — `IMPROVEMENT_CHANGELOG.md` (comparison, conclusion 2–3).
- Judge rubric dimensions (relevance/novelty/feasibility/risk/quality) + `goal_fit` — README §What this is.
- TRACK 1 rubric weights (Problem 15 / Engineering 30 / E2E 20 / Measured 15 / Repro 15 / Hot take 5) — for editor's self-check, not shown in video.
