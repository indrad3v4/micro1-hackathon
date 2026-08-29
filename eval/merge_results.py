"""Merge eval results: baseline (main run B04-B12 + rerun B01-B03 whose traces
survived) + advanced. Fill missing cost with token-based estimate using
CometAPI's own rates (extracted from a real cost_details response:
upstream_inference_prompt_cost 2.2896e-05 / 228 tok = $0.1004/1M in;
0.00202752 / 3072 tok = $0.66/1M out). Flags each record cost_estimated.
Output: eval/results/merged_baseline.json + merged_advanced.json (summary md
facts printed to stdout).
"""
import json
from pathlib import Path

R = Path("/root/.hermes/micro1-hackathon/eval/results")
RATE_IN, RATE_OUT = 0.1004, 0.66   # USD per 1M tokens (CometAPI deepseek lane)


def fill_cost(rec: dict) -> dict:
    rec = dict(rec)
    if not rec.get("cost_usd"):
        t = rec.get("tokens", {})
        pin = t.get("prompt_tokens", 0)
        pout = t.get("completion_tokens", 0)
        rec["cost_usd"] = round((pin * RATE_IN + pout * RATE_OUT) / 1e6, 6)
        rec["cost_estimated"] = True
    else:
        rec["cost_estimated"] = False
    return rec


def main():
    base_main = json.load(open(R / "baseline_results.json", encoding="utf-8"))
    base_123 = {d["brief_id"]: d for d in
                json.load(open(R / "baseline_results_B01_B02_B03.json", encoding="utf-8"))}
    baseline = []
    for d in base_main:
        if d["brief_id"] in base_123:
            # metrics must come from the SAME run whose trace survived (rerun B01-B03)
            d = base_123[d["brief_id"]]
        baseline.append(fill_cost(d))
    adv_main = {d["brief_id"]: d for d in
                json.load(open(R / "advanced_results_B01_B02_B03_B04_B05_B06_B07_B08_B09_B10_B11.json",
                               encoding="utf-8"))}
    adv_b12 = json.load(open(R / "advanced_results_B12.json", encoding="utf-8"))[0]
    advanced = [fill_cost(adv_main[d["brief_id"]]) for d in base_main
                if d["brief_id"] in adv_main] + [fill_cost(adv_b12)]

    (R / "merged_baseline.json").write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2))
    (R / "merged_advanced.json").write_text(
        json.dumps(advanced, ensure_ascii=False, indent=2))

    for name, rows in [("BASELINE", baseline), ("ADVANCED", advanced)]:
        tot_cost = sum(r["cost_usd"] for r in rows)
        tot_wall = sum(r["wall_s"] for r in rows)
        est = sum(1 for r in rows if r["cost_estimated"])
        print(f"{name}: {len(rows)} briefs | total cost ${tot_cost:.4f} "
              f"(est: {est}/12) | total wall {tot_wall:.0f}s "
              f"| avg wall {tot_wall/len(rows):.1f}s")
        for r in rows:
            dirs = r.get("direction_count", r.get("concept_count"))
            print(f"  {r['brief_id']}: dirs={dirs} wall={r['wall_s']}s "
                  f"cost=${r['cost_usd']:.6f} est={r['cost_estimated']} "
                  f"tok={r['tokens'].get('total_tokens')}")


if __name__ == "__main__":
    main()
