# Orchestration PRD — Self-Proof Chain for CRAFT Card 5 (micro1)

## 1. Problem
The current orchestrator was a monolithic recurring cron (every 3h) with the judge
as an internal step. It did not honor the required sequence:
**one WBS step → fresh-eyes judge roast → only if pass → next step.**

## 2. Ideal Ending (ИКР, TRIZ)
The chain advances itself: each completed step triggers an independent judge, and
the judge's pass decision is the only thing that starts the next step. The system
uses only what exists: cron scheduler, delegate_task (fresh subagent = judge), git,
and a JSON step-state file. No new infra.

## 3. Architecture

### 3.1 Step-state file (single source of truth)
`/root/.hermes/micro1-hackathon/orchestration/state.json`
```json
{
  "current_step": "5.2",
  "steps": {
    "5.1": {"title": "Benchmark evidence", "status": "done"},
    "5.2": {"title": "Improvement changelog", "status": "in_progress"},
    "5.3": {"title": "Reproduction guide + README", "status": "pending"},
    "5.4": {"title": "Trajectories + submission packet", "status": "pending"},
    "5.5": {"title": "Full-package judge roast + fixes", "status": "pending"}
  },
  "last_judge_verdict": null
}
```

### 3.2 The chain (per tick)
1. **Execute current step** (agent does the WBS task).
2. **Judge gate** — spawn a FRESH judge subagent (`delegate_task`) with the exact
   micro1 rubric (Problem&UserValue 15 / AgentSolution&Engineering 30 /
   End-to-End 20 / MeasuredImprovement 15 / Reproducibility 15 / HotTake 5).
   Judge returns `{pass: bool, scores: {...}, fixes: [...]}`.
3. **If pass (or scores ≥ threshold, e.g. total ≥ 80):**
   - commit + push atomic (conventional commit, English)
   - advance `state.json` to the next step
   - report `PASS` with evidence paths
4. **If fail:**
   - apply judge's fixes to the current step, re-verify, re-commit
   - do NOT advance the step
   - report `BLOCKED` with the judge's exact complaints

### 3.3 Chaining — two supported modes
- **Mode A (recommended, robust):** single recurring orchestrator cron
  (every 45m) with `continuity: true` + step-state file. Idempotent, resumable,
  survives crashes. The judge gate is the transition rule between steps.
- **Mode B (explicit cron-chaining):** one one-shot cron per step; on judge PASS
  the cron fires the next via `cronjob(action='run', job_id=<next>)`. More
  visible, but fragile (a missed fire dead-ends the chain).

Selected: **Mode A** (proven on this box — arkkona orchestrator pattern).

## 4. Judge subagent contract (the roast)
- ROLE: "Senior judge at the micro1 Agentic Workflows Hackathon, grading a
  submission package."
- TASK: read the package (repo files at fixed paths), score each criterion 0-N,
  give ONE concrete fix per criterion below ~90%.
- AC: must read actual files (never judge from the prompt alone); must return
  structured JSON `{pass, scores, fixes}`.
- Non-goal: no code changes by the judge; fixes are recommendations only.

## 5. Acceptance criteria (this PRD is done when)
- AC1: `orchestration/state.json` exists and advances only after a judge PASS.
- AC2: every step commit is atomic + pushed, message in English conventional format.
- AC3: judge subagent runs on a fresh session (delegate_task) per gate.
- AC4: a FAIL never advances the state; fixes are applied and re-verified first.
- AC5: final report to user is a yes/no triage checklist with evidence paths.
