"""Inspect B12 advanced trace + both results files; print key facts."""
import json

base = "/root/.hermes/micro1-hackathon"

# B12 advanced trace: find retry + veto events, and whether directions are heuristic
p = f"{base}/creative-court/traces/eval_adv_B12.jsonl"
for line in open(p, encoding="utf-8"):
    e = json.loads(line)
    if e["type"] in ("retry", "veto", "human_checkpoint"):
        print("B12", e["type"], "|", (e.get("retry_of") or "")[:60], "|", (e.get("feedback") or "")[:90])
    if e["type"] == "tool_response" and e.get("tool") == "llm":
        print("B12 llm raw head:", e["tool_response"][:150].replace("\n", " "))

for mode, f in [("baseline", "baseline_results.json"),
                ("base_123", "baseline_results_B01_B02_B03.json"),
                ("advanced", "advanced_results.json")]:
    data = json.load(open(f"{base}/eval/results/{f}", encoding="utf-8"))
    tot_cost = sum(d["cost_usd"] or 0 for d in data)
    tot_wall = sum(d["wall_s"] for d in data)
    print(f"\n{mode}: {len(data)} briefs, cost=${tot_cost:.4f}, wall={tot_wall:.0f}s")
    for d in data:
        dirs = d.get("direction_count", d.get("concept_count"))
        print(f"  {d['brief_id']}: dirs={dirs} wall={d['wall_s']}s cost=${d['cost_usd']:.6f} "
              f"tokens={d['tokens'].get('total_tokens')} veto={bool(d.get('veto'))}")
