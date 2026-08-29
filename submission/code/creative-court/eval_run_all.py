#!/usr/bin/env python3
"""Eval runner — baseline vs advanced (Creative Court) on the same 10 briefs.

Measures per case: primary outcome metrics, human wall-time per task, cost.
Writes eval/results.json. $0 budget: everything runs offline deterministically.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent  # creative-court/

# HARD $0 guarantee: strip any LLM keys so both this process and the spawned
# `uv run creative-court` subprocess run the deterministic heuristic fallback.
for _k in ("COMETAPI_KEY", "LLM_API_KEY"):
    os.environ.pop(_k, None)
assert not os.environ.get("COMETAPI_KEY") and not os.environ.get("LLM_API_KEY")
sys.path.insert(0, str(ROOT / "src"))
from creative_court.core.models import Brief  # noqa: E402
from eval_baseline_gen import baseline_run  # noqa: E402

BRIEFS_DIR = ROOT / "demo_briefs"
OUT = ROOT / "eval" / "results.json"

# Contradiction markers an effective judge should catch (edge-case brief).
CONTRA_RULES = [
    ("no screens / internet", r"экран|интернет|офлайн|offline"),
    ("push notifications", r"push|пуш|уведомлен"),
    ("livestream", r"трансляц|livestream|стрим"),
    ("voice assistant in rooms", r"голосов|ассистент"),
    ("work email & calls", r"почт|созвон"),
]


def detect_contradiction(brief: Brief) -> dict:
    """Detect root requirement vs add-on requirements that conflict with it."""
    text = f"{brief.description} {' '.join(brief.constraints)} {brief.goal}".lower()
    if not any(re.search(p, text) for _, p in CONTRA_RULES[:1]):
        return {"is_contradictory": False, "conflicts": []}
    conflicts = []
    for name, pat in CONTRA_RULES[1:]:
        if re.search(pat, text):
            conflicts.append(name)
    return {
        "is_contradictory": bool(conflicts),
        "conflicts": conflicts,
        "root_requirement": "full digital detox (no screens/internet)",
    }


def run_advanced(brief_path: Path, trace_path: Path) -> dict:
    """Run the full Creative Court pipeline, parse verdicts from stdout."""
    t0 = time.perf_counter()
    proc = subprocess.run(
        ["uv", "run", "creative-court", "demo", "--brief-file", str(brief_path),
         "--trace-path", str(trace_path)],
        capture_output=True, text=True, cwd=str(ROOT), timeout=300,
    )
    wall = time.perf_counter() - t0
    if proc.returncode != 0:
        return {"error": proc.stderr[-500:], "wall_s": round(wall, 3)}
    # parse judge verdicts: lines like "  78.5  ritual:Name  (Name: 78.5/100 — approved)"
    nums = [float(m) for m in re.findall(r"^\s+(\d+\.\d)\s+\S+", proc.stdout, re.M)]
    best = max(nums) if nums else 0.0
    n_dirs = (len(re.findall(r"^\s+\[\w+\s*\]", proc.stdout, re.M))
              or len(re.findall(r"направлений", proc.stdout)))
    m = re.search(r"Creator: (\d+) направлений", proc.stdout)
    if m:
        n_dirs = int(m.group(1))
    return {
        "best_total": best,
        "n_directions": n_dirs,
        "rubrics": True,
        "veto": False,
        "trace": trace_path.exists(),
        "wall_s": round(wall, 3),
        "returncode": proc.returncode,
    }


def main() -> None:
    brief_paths = sorted(BRIEFS_DIR.glob("eval_*.json"))
    results = []
    for bp in brief_paths:
        data = json.loads(bp.read_text(encoding="utf-8"))
        brief = Brief(**data)
        slug = bp.stem.replace("eval_", "")
        trace = ROOT / "traces" / f"eval_{slug}.jsonl"

        t0 = time.perf_counter()
        base = baseline_run(brief)
        base_wall = time.perf_counter() - t0
        base["wall_s"] = round(base_wall, 3)

        adv = run_advanced(bp, trace)
        contra = detect_contradiction(brief)

        results.append({
            "case": bp.name,
            "title": brief.title,
            "is_edge": contra["is_contradictory"],
            "edge_conflicts": contra["conflicts"],
            "baseline": base,
            "advanced": adv,
        })
        print(f"{bp.name}: base={base['best_total']} adv={adv.get('best_total')} "
              f"dirs={adv.get('n_directions')} edge={contra['is_contradictory']}")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({OUT.stat().st_size} bytes, {len(results)} cases)")


if __name__ == "__main__":
    main()
