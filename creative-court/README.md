# Creative Court

Agent harness with **trajectory recording** for the micro1 Frontier
Engineering Challenge 2026 (28–30.08, HackerEarth).

Two agents — **Creator** (brief → fan of creative directions across ИКРА
frames) and **Judge** (contextual rubrics → verdicts, human veto) — with every
step recorded to an append-only JSONL trajectory.

## Why trajectories matter (micro1)

- The submission package **requires** agent trajectories: "Representative
  trajectories for every agent you used, easy to follow from the agent
  instructions through to the final result."
- micro1 may **buy back** qualifying agent-use traces at **$2–15/trace**
  (cap $100–200/participant) — separate from the $5,000 prize pool.
- `TraceRecorder` writes every event atomically (fsync per line), so a crash
  never loses a trajectory. Tool outputs >4KB are truncated in the trace
  (full evidence kept separately).

## Quick start

```bash
uv run creative-court demo --brief "Умная кофеварка" \
    --desc "сама выбирает рецепт по настроению и расписанию" \
    --audience "городские профессионалы 25-40" \
    --veto "слишком тёмная драма"
uv run creative-court traces --dir traces
```

Without `COMETAPI_KEY`/`LLM_API_KEY` the pipeline runs on a deterministic
heuristic fallback (6 frames, rule-based scoring) — always runnable offline.
With a key it uses `deepseek-v4-flash-vision-exp` via CometAPI by default
(override with `LLM_MODEL` / `LLM_BASE_URL`).

## Trajectory format

`traces/run_<name>.jsonl` — one JSON object per line:

| type | meaning |
|---|---|
| `agent_start` | agent began, instruction recorded |
| `agent_step` | action taken + feedback that shaped the next step |
| `tool_call` / `tool_response` | tool invocation and its output |
| `retry` | agent retried after a failure (with reason) |
| `human_checkpoint` | human approval gate |
| `veto` | human overrode an agent decision |
| `agent_end` | agent finished, summary |

## Using the recorder with your own agents

```python
from creative_court.core.trace import TraceRecorder
with TraceRecorder("traces/run_codex.jsonl") as rec:
    rec.tool_call("codex", "bash", "run tests")
    rec.tool_response("codex", "bash", output)
    rec.human_checkpoint("codex", "approved deploy")
    rec.retry("codex", "failed step", "flaky test — retrying")
```

## Layout

```
src/creative_court/
  core/models.py    Brief, Direction, RubricScore, Verdict, TraceEvent
  core/trace.py     TraceRecorder (JSONL, atomic, thread-safe)
  core/llm.py       LLMClient + heuristic fallback + ИКРА frames
  agents/creator.py Creator agent
  agents/judge.py   Judge agent (rubrics, veto)
  cli.py            demo + traces commands
tests/test_pipeline.py  smoke tests (run offline)
```

## Next steps before kickoff (28.08)

- [ ] Adapt Creator/Judge to the actual problem PDF once released
- [ ] Wire real coding-agent traces (Codex/Claude Code) into TraceRecorder
- [ ] Demo video script (≤5 min): problem → baseline → run → comparison → changelog
