# Creative Court 2.0

> **A judgment layer between your agent and your signature — as an MCP server.**
>
> Delegate the generation. Keep the verdict. When you sign, you sign what you saw.

**Submission:** micro1 Agentic Workflows Hackathon — Frontier Engineering Challenge 2026 (HackerEarth)
**Repo:** `github.com/indrad3v4/micro1-hackathon` · branch `master` · English only (code, docs, UI)
**Form:** MCP server (main interface for AI IDEs) + Reflex dashboard (human view over the same core)

---

## The problem it solves

Most agentic tools sell **speed**: delegate more, ship faster. The hidden price is never shown: the more you delegate, the less of *you* is left in the work — yet you sign for all of it. Publicly you say "the agent handles it"; privately: "where am I in this?"

**The drama:** *"My agent already decided. I signed what I was shown, not what I saw."*

Creative Court solves this with one clean split: **delegate the generation, keep the verdict.** Your agent stays fast (the driver). Blind signatures disappear (the barrier). You can ask "why this?" without losing face — the judge asks it on every direction, by default. Your signature means something again.

**The form of the relationship:** a *court* — Creator, Judge, and you the signatory — expressed as an **MCP server**, so any AI IDE you already use becomes the court's chamber.

---

## What this is

Creative Court is a **human-judgment layer** in front of an AI coding agent — a `JudgeAgent` between the agent's output and the human's signature.

1. **`CreatorAgent`** fans a brief into 6+ creative directions across ИКРА frames (artistic / social / professional / historical / ritual / natural).
2. **`JudgeAgent`** scores every direction on a contextual rubric (relevance / novelty / feasibility / risk / quality) **plus a `goal_fit` signal** — how much the direction moves the work toward the human's stated goal, independent of constraint-relevance.
3. **Veto with a real reason** — the human's concern becomes a hard requirement; the Creator reworks *the same direction* to address it (not a random replacement).
4. **Sign-off bound to the canonical verdicts** — the exact list you signed is recorded (`data.signed`), and every step lands in an append-only JSONL trajectory.

> **Drift is measured against the human's stated goal.** A direction can respect every constraint yet still walk away from what the human actually wanted. That is why `court_run_brief` requires `goal` — without the goal there is nothing to drift from.

---

## Run it in your AI IDE

The product's main interface is an **MCP server** (`creative-court/mcp_server.py`). Any MCP-capable IDE or agent (Claude Code, Cursor, Cline, Antigravity, Codex, Hermes, …) connects to it the same way: point it at the Python file, provide an OpenAI-compatible API key, and the Court's tools appear.

**Prerequisite:** an OpenAI-compatible key (`COMETAPI_KEY`, `OPENROUTER_API_KEY`, or `LLM_API_KEY`). Without a key the server still runs — the judge degrades to a deterministic heuristic and says so honestly (`generated_by`/`score_source`).

```bash
cd micro1-hackathon
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
export COMETAPI_KEY=sk-...                            # or OPENROUTER_API_KEY / LLM_API_KEY
export LLM_MODEL=deepseek-v4-flash
```

### Claude Code

```bash
claude mcp add --transport stdio creative-court \
  --env COMETAPI_KEY=$COMETAPI_KEY \
  -- /path/to/micro1-hackathon/cc-app/.venv/bin/python \
     /path/to/micro1-hackathon/creative-court/mcp_server.py
```

Or project-scoped, committed for the team — add `.mcp.json` to the repo root:

```json
{
  "mcpServers": {
    "creative-court": {
      "type": "stdio",
      "command": "/path/to/micro1-hackathon/cc-app/.venv/bin/python",
      "args": ["/path/to/micro1-hackathon/creative-court/mcp_server.py"],
      "env": { "COMETAPI_KEY": "${COMETAPI_KEY}" }
    }
  }
}
```

### Cursor

Settings → MCP → **Add new MCP server** → type `stdio`:

```json
{
  "mcpServers": {
    "creative-court": {
      "command": "/path/to/micro1-hackathon/cc-app/.venv/bin/python",
      "args": ["/path/to/micro1-hackathon/creative-court/mcp_server.py"],
      "env": { "COMETAPI_KEY": "sk-..." }
    }
  }
}
```

### Cline (VS Code extension)

`.cline/mcp_settings.json` (or the MCP Servers panel → `Configure MCP Servers`):

```json
{
  "mcpServers": {
    "creative-court": {
      "command": "/path/to/micro1-hackathon/cc-app/.venv/bin/python",
      "args": ["/path/to/micro1-hackathon/creative-court/mcp_server.py"],
      "env": { "COMETAPI_KEY": "sk-..." }
    }
  }
}
```

### Antigravity / Codex / any MCP host

Antigravity and Codex read standard MCP config — use the same `mcpServers` JSON block in the host's MCP settings (`.mcp.json`, `~/.codex/config.toml` for Codex, etc.). Any client that speaks MCP stdio can consume the server.

### Hermes

```bash
hermes mcp add creative-court \
  --command /path/to/micro1-hackathon/cc-app/.venv/bin/python \
  --args /path/to/micro1-hackathon/creative-court/mcp_server.py \
  --env COMETAPI_KEY=$COMETAPI_KEY
hermes mcp test creative-court    # → Connected, tools discovered
```

> **Long-running tools need a longer timeout.** `court_run_brief`/`court_veto` run several LLM calls in sequence and can take 1–5 minutes. If your host drops the connection, raise its MCP tool timeout (e.g. Hermes: `hermes config set mcp_servers.creative_court.timeout 300`).

### Remote (streamable HTTP)

```bash
python creative-court/mcp_server.py --http   # streamable HTTP on 0.0.0.0:8765
```

Then connect any HTTP-capable MCP host to `http://<host>:8765/mcp`.

### Tools

| Tool | What it does |
|---|---|
| `court_run_brief` | brief + **required `goal`** → 6 directions → LLM verdicts (5-dimension rubric **+ `goal_fit` per direction**) |
| `court_veto` | human vetoes a direction with a real reason → the concern becomes a hard requirement → regenerate + re-score the SAME direction |
| `court_sign_off` | human signs the approved decisions; the exact list is bound into the trace as `data.signed` |
| `court_sign_off_all` | sign every currently-approved decision in ONE call, bound to canonical verdicts |
| `court_export_trace` | read a run's full JSONL trajectory + event metrics |
| `court_health` | LLM availability + trace count |

### Resources & Prompts

- **Resources** — the Court's record is native MCP: `traces://list` (all runs) and `trace://{run_id}` (full trajectory). An AI IDE reads the signable record directly.
- **Prompt** — `court_review` (run_id): guided "sign only what you saw" review — walk verdicts, find drift (constraint- or goal-drift), decide veto-or-sign.
- **Honesty built in**: every verdict carries `generated_by` (llm/heuristic) and `score_source`; responses include a `warnings` array when any fallback fired — heuristic work is never presented as LLM work.
- **Goal is a first-class citizen**: `court_run_brief` refuses to run without the human's stated `goal`, and every verdict carries a separate `goal_fit {score, note}`.

---

## Measured result (10 briefs, `cc-app/evaluation/results/final_report.json`)

| Metric | Baseline (heuristic judge, 0 LLM calls) | Advanced (Creative Court 2.0) | Delta |
|---|---|---|---|
| **Drift-catch rate** (primary outcome) | **0 / 10** (0 %) | **9 / 10** (90 %) | **+90 %** |
| Mean drift-probe score (lower = caught better) | 79.5 | 23.7 | −55.8 pts |
| Human review time per task (modelled proxy) | 33.1 min | 7.25 min | −25.85 min / task (−78 %) |
| LLM spend, 10 tasks (measured, incl. `usage.cost`) | $0.00 | **$0.09384** | **$0.00938 / task** |
| Tokens, 10 tasks (measured) | 0 | 348 877 | — |
| LLM calls, 10 tasks (measured) | 0 | 99 | — |
| Wall-clock, 10 tasks (measured) | ~0.04 s / task | 2 646 s (~44 min) | — |
| Vetoes / replacements | 0 | 9 / 9 | — |

Every brief received the **same hand-written drift probe** (a confident-sounding direction that violates a hard constraint but is lexically saturated with brief keywords) in both conditions. The baseline was fooled by every probe; the Court rejected 9 of 10 — including the deliberately contradictory `eval_10_edge_hotel`.

**Why the baseline's zero token spend is the hidden cost:** 0 LLM calls and $0.00 sounds free, but the heuristic judge is not a judge — it rubber-stamps constraint-violating directions (mean probe score 79.5), so the human pays 33 modelled minutes per task re-checking work that already missed the goal. The Court's ~1-cent-per-task verification spend buys certainty.

---

## Repository layout

```
micro1-hackathon/
├── creative-court/            # core agent package (stdlib-only runtime)
│   ├── pyproject.toml         # dependencies = [] — no runtime deps
│   ├── mcp_server.py          # ← MCP server (AI-IDE interface, see above)
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

## Reproduction guide

### Prerequisites

- **Python 3.12+** (report generated on 3.12.14; `requires-python >= 3.11`, verified on 3.13).
- **API key** for an OpenAI-compatible endpoint — the harness reads `COMETAPI_KEY` (primary) or `OPENROUTER_API_KEY` / `LLM_API_KEY`. Without a key, run the **baseline only** with `--no-llm`.
- The `creative-court` runtime is pure stdlib (`urllib`, `dataclasses`, `json`); the `cc-app/requirements.txt` install is only needed for the Reflex dashboard.

### One-command reproduction of the full benchmark

```bash
git clone https://github.com/indrad3v4/micro1-hackathon.git
cd micro1-hackathon
export COMETAPI_KEY=sk-...
export LLM_MODEL=deepseek-v4-flash
python cc-app/evaluation/run_benchmark.py --fresh
```

- `--fresh` re-runs all 10 briefs end-to-end (baseline + advanced per brief) and regenerates `final_report.json` / `.csv` / `traces/*.jsonl`.
- **Expected runtime & cost** (measured): ~2 646 s (~44 min) wall-clock; **$0.09384 total → $0.00938/task** (348 877 tokens, 99 LLM calls).
- Partial runs: `--limit 2` (smoke), `--only eval_10_edge_hotel` (single brief), `--no-llm` (offline/heuristic, CI-safe — run on a copy to keep real evidence).

### Verified dependency versions

| Component | Version (tested) | Notes |
|---|---|---|
| Python | 3.12.14 (report), ≥3.11 supported | verified on 3.13 too |
| `creative-court` package | 0.1.0 | `dependencies = []` — stdlib only |
| LLM model | `deepseek-v4-flash` | env `LLM_MODEL` |
| LLM endpoint | `https://api.cometapi.com/v1` | OpenAI-compatible |
| Judge reject threshold | 60.0 | const `REJECT_THRESHOLD` |
| `cc-app` (dashboard only) | reflex==0.9.9 · pydantic≥2.10 · openai≥1.0 | Node.js 20+ for the Reflex dev server |

---

## Improvement changelog & hot take

- **Full changelog:** `IMPROVEMENT_CHANGELOG.md` — Baseline → Iterations 1–6 → Final, each with evidence and decision, plus the removed experiment (R1).
- **Hot take — unrouted tokens are the hidden cost.** Most agentic designs treat *generation* as expensive and *checking* as cheap. This benchmark measures the opposite: the "free" baseline (0 LLM calls, $0.00) still fails the goal — it accepts 10 of 10 drift probes — and pushes the bill onto the most expensive interpreter in the loop, the human (33 modelled minutes per task). The Court inverts the curve: ~$0.01 of QA per task buys back ~25.85 minutes of human attention. **Token spend should be a gate on result, not a meter of activity** — and an LLM judge without a human veto quietly accepts edge cases as truth. The veto is not a courtesy; it is mandatory.

---

## Evidence paths (all committed on `master`)

- `cc-app/evaluation/results/final_report.json` — machine-readable evidence (source of truth)
- `cc-app/evaluation/results/final_report.csv` — one row per brief + totals
- `cc-app/evaluation/results/per_brief/*.json` — crash-safe per-brief results (10)
- `cc-app/evaluation/results/traces/bench_eval_*_{baseline,advanced}.jsonl` — benchmark trajectory pairs (20)
- `creative-court/traces/*.jsonl` — agent trajectories (deliverable 04)
- `cc-app/traces/traces/dashboard_*.jsonl` — live Reflex dashboard session trace
- `IMPROVEMENT_CHANGELOG.md` — baseline → Iterations 1–6 → Final, with the removed R1 experiment
