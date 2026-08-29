"""Print B12 story facts + advanced top scores for report writing."""
import json

B = "/root/.hermes/micro1-hackathon"

adv = json.load(open(f"{B}/eval/results/merged_advanced.json", encoding="utf-8"))
base = json.load(open(f"{B}/eval/results/merged_baseline.json", encoding="utf-8"))

b12b = [d for d in base if d["brief_id"] == "B12"][0]
print("=== B12 baseline output (preview 400 chars) ===")
print(b12b["output_preview"])
print("\nfull chars:", b12b["output_full_chars"])

print("\n=== Advanced top_scores per brief ===")
for d in adv:
    ts = d.get("top_scores", {})
    top1 = sorted(ts.items(), key=lambda kv: -kv[1])[:1]
    print(f"{d['brief_id']}: approved={len(d.get('approved', []))}/6, "
          f"top1={top1[0] if top1 else '-'}")
    if d["brief_id"] == "B12":
        print("  B12 all:", json.dumps(ts, ensure_ascii=False))
        print("  B12 veto:", d.get("veto"))
        print("  B12 preview:", d["output_preview"])
