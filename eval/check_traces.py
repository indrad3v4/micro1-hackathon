"""Verify trace files: count events per file, check meta, check completeness."""
import json, glob, sys

pats = sys.argv[1:] or ["eval_base_*.jsonl"]
for pat in pats:
    files = sorted(glob.glob(f"/root/.hermes/micro1-hackathon/creative-court/traces/{pat}"))
    print(f"pattern {pat}: {len(files)} files")
    for p in files:
        lines = [json.loads(l) for l in open(p, encoding="utf-8")]
        meta = lines[0].get("data", {}).get("meta", {})
        types = {}
        for e in lines:
            types[e["type"]] = types.get(e["type"], 0) + 1
        print(f"  {p.split('/')[-1]}: {len(lines)} events, run={meta.get('run')}, mode={meta.get('mode')}, types={types}")
