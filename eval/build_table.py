"""Build the comparison table data (facts only from merged results).
Prints a markdown table fragment used by both run reports.
"""
import json

B = "/root/.hermes/micro1-hackathon"
base = json.load(open(f"{B}/eval/results/merged_baseline.json", encoding="utf-8"))
adv = json.load(open(f"{B}/eval/results/merged_advanced.json", encoding="utf-8"))

titles = {b["id"]: b["title"] for b in
          json.load(open(f"{B}/eval/briefs.json", encoding="utf-8"))["briefs"]}
complex_id = [b["id"] for b in json.load(open(f"{B}/eval/briefs.json"))["briefs"]
              if b.get("complex")][0]

rows = []
for b, a in zip(base, adv):
    assert b["brief_id"] == a["brief_id"]
    bid = b["brief_id"]
    rows.append({
        "id": bid,
        "title": titles[bid],
        "complex": bid == complex_id,
        "base_wall": b["wall_s"], "adv_wall": a["wall_s"],
        "base_cost": b["cost_usd"], "adv_cost": a["cost_usd"],
        "base_tok": b["tokens"].get("total_tokens", 0),
        "adv_tok": a["tokens"].get("total_tokens", 0),
        "base_out": b.get("output_full_chars", 0),
        "adv_dirs": a.get("direction_count", 0),
        "adv_approved": len(a.get("approved", [])),
        "adv_top1": (sorted(a.get("top_scores", {}).items(), key=lambda kv: -kv[1]) or [("-", 0)])[0],
        "veto": a.get("veto"),
    })

print("| Брыф | Baseline: час, с | Adv: час, с | Baseline: $ | Adv: $ | Baseline: токены | Adv: токены | Adv: направл./approved | Adv: топ-1 |")
print("|---|---|---|---|---|---|---|---|---|")
for r in rows:
    mark = " ⚠️" if r["complex"] else ""
    veto = " (veto)" if r["veto"] else ""
    print(f"| {r['id']}{mark} | {r['base_wall']} | {r['adv_wall']} | "
          f"{r['base_cost']:.6f} | {r['adv_cost']:.6f} | {r['base_tok']} | {r['adv_tok']} | "
          f"{r['adv_dirs']}/{r['adv_approved']}{veto} | {r['adv_top1'][0]} ({r['adv_top1'][1]}) |")

tb = sum(r["base_wall"] for r in rows); ta = sum(r["adv_wall"] for r in rows)
cb = sum(r["base_cost"] for r in rows); ca = sum(r["adv_cost"] for r in rows)
tkb = sum(r["base_tok"] for r in rows); tka = sum(r["adv_tok"] for r in rows)
print(f"| **Разам (12)** | **{tb:.0f}** | **{ta:.0f}** | **{cb:.6f}** | **{ca:.6f}** | "
      f"**{tkb}** | **{tka}** | — | — |")
print()
print(f"avg wall: baseline {tb/12:.1f}s vs advanced {ta/12:.1f}s")
print(f"total cost: baseline ${cb:.4f} vs advanced ${ca:.4f}")
print(f"cost per brief avg: baseline ${cb/12:.5f} vs advanced ${ca/12:.5f}")
