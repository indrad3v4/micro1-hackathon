# TRIZ System Analysis — Creative Court 2.0 (Token Result Gate)

Grounded in Kukalev 2014 «Теория развития искусственных систем» (§6.2–6.12).
Every claim traces to `cc-app/evaluation/results/final_report.json` (10-brief benchmark).

## 1. Element (Component) Model (§6.2)

Artificial system «Creative Court» — designed to return signable agent decisions.

| # | Element | Role | Code |
|---|---------|------|------|
| 1 | CreatorAgent | generates direction fan from brief | `agents/creator.py` |
| 2 | JudgeAgent | rubric scoring, veto | `agents/judge.py` |
| 3 | TraceRecorder | append-only event log | `core/trace.py` |
| 4 | Reflex UI | presents the court, accepts sign-off | `cc-app/cc_app/` |
| А | Human signatory (supersystem) | final veto + signature | — |
| Б | Brief (environment) | material of the main flow | `demo_briefs/*.json` |

## 2. Flow Model of Interactions (ПМВ, §6.5)

```
P1 (flow of directions): Бриф → Creator [1] → Direction*6 → Judge [2] → Verdict → Human [А] → signature
P2 (flow of events):     every transition → TraceRecorder [3] → JSONL → UI [4] → human trust
P3 (flow of tokens):     paid tokens → either on-goal (verification) or burned (blind generation)
```

Chain-of-interactions rule (book: function rank grows along the flow): Judge's
tokens carry the highest rank — they convert all prior tokens into a signable verdict.

## 3. Functional Model (ФМ, §6.6)

Main system function: **возвращать человеку подписываемые решения его агента**
(verb + object, per book rules §1.2.7).

| Carrier | Function (verb+object) | Rank | Level: baseline | Level: Court |
|---|---|---|---|---|
| Creative Court (Гл.Ф) | Возвращать подписываемые решения | Гл. | fails | **works** |
| CreatorAgent [1] | Порождать веер направлений из брифа | 1 | works | works |
| JudgeAgent [2] | Отсекать дрейф-направления (veto) | 1 | **absent** | works 10/10 |
| JudgeAgent [2] | Обосновывать каждый вердикт (rubric) | 1 | absent | works |
| CreatorAgent [1] | Пересобирать vetoed направление | 2 | absent | works (10 replacements) |
| TraceRecorder [3] | Фиксировать каждое решение | 1 | absent | works (56 files, 12-key schema) |
| Reflex UI [4] | Предъявлять ход суда человеку | 1 | — | works |
| Reflex UI [4] | **Принимать подпись человека** | 1 | — | **partial → 5.6a** |

## 4. Parametric Model (§6.7) — required vs actual

| Parameter (event) | Required (for Гл.Ф) | Baseline | Court | Verdict |
|---|---|---|---|---|
| Drift detection | 100% | 0% (0/10) | **100% (10/10)** | baseline: deficiency |
| Human time / task | ≤10 min | 33 min | **7.5 min** | baseline: deficiency |
| Cost / task | ≤$0.05 | ~$0.002 (blind) | $0.0104 | both: acceptable |
| Signable output | human-grade verdict | AI draft wall | verdict + rubric + trace | baseline: deficiency |

## 5. Flow-Material Needs Model (ПМП, §6.8)

Material of flow = Direction; consumer = human signatory.

| МП | Consumer | Properties | Direction «wants» | Function serving it | Level |
|---|---|---|---|---|---|
| Direction | Signatory | text concept | be **compatible with all constraints** | Ф Judge: rubric scoring | base: Н / Court: ok |
| Direction | Signatory | chosen logic | carry **"why this way"** | Ф Judge: reasoned verdict | base: Н / Court: ok |
| Direction | Signatory | replaceability | **be replaced if vetoed** | Ф Creator: retry loop | base: Н / Court: ok (10/10) |
| Direction | Signatory | provability | **leave a trace of its path** | Ф Trace: JSONL event | ok both |

**Flow gap (the book's promised finding):** baseline Direction reaches the
signatory without a single check — 33 human minutes per task are the price of
uncoordinated flows.

## 6. Cause-Effect Model (ПСМ, §6.11)

```
Main deficiency: human cannot sign an agent decision without long manual re-checking
 ├─ CAUSE 1: Creator generates without constraint check (drift)
 │    └─ 1.1: one-shot prompt, no rubric gate → 10/10 drift
 ├─ CAUSE 2: manual verification = 33 min/task, does not scale
 │    └─ 2.1: no machine-readable verdict with reasoning
 └─ CAUSE 3: no decision trail → nothing to revisit or explain
      └─ 3.1: raw LLM calls leave no events

RESOLUTION: Judge rubric (root 1) + veto/retry loop (root 2) + TraceRecorder (root 3)
```

## 7. Function-Ideal Model (ФИМ, §6.12) — IFR collapse

IFR: Court performs the main function by itself, using only existing resources.

| Element | Function | Collapsed into | Status |
|---|---|---|---|
| Human checker (33 min) | assess directions | **JudgeAgent** (same LLM, different prompt) | ✅ collapsed — the main saving |
| Separate evaluator service | scoring | same model, rubric prompt | ✅ collapsed — zero new infra |
| Audit database | store events | append-only JSONL file | ✅ collapsed |
| Human signatory | final decision | **NOT collapsed** — veto + signature stay human (hackathon ground rules 04–05: human approval for consequential actions) | 🔒 kept by design |

**Resulting ideal contour:** Creator + Judge inside one model; the human only
signs and holds veto. Ideality achieved: all functions performed, zero new
resources, the one non-collapsible part is the human signature — by requirement,
not by weakness.

## 8. Hot Take (from ФИМ)

We collapsed into one model what the market sells as three products
(generation + evaluation + audit). **Signability is the one function we
deliberately left to the human.**
