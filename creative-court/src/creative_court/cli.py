"""Creative Court CLI — end-to-end demo: brief -> directions -> verdicts -> veto.

Usage:
    creative-court demo --brief "Умная кофеварка" --desc "для одиноких профессионалов" \
        --audience "urban workers 25-40"
    creative-court demo --brief-file demo_briefs/coffee.json
    creative-court traces --dir traces          # show trace metrics
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core.models import Brief
from .core.trace import TraceRecorder, export_trace_metrics
from .agents.creator import CreatorAgent
from .agents.judge import JudgeAgent

DEFAULT_BRIEF = Brief(
    title="Умная кофеварка",
    description="Кофеварка, которая сама выбирает рецепт по настроению и расписанию владельца.",
    audience="городские профессионалы 25-40",
    constraints=["должна работать без смартфона"],
    goal="превратить утренний кофе в ритуал",
)


def _load_brief(args) -> Brief:
    if args.brief_file:
        data = json.loads(Path(args.brief_file).read_text(encoding="utf-8"))
        return Brief(**data)
    return Brief(
        title=args.brief or DEFAULT_BRIEF.title,
        description=args.desc or DEFAULT_BRIEF.description,
        audience=args.audience or DEFAULT_BRIEF.audience,
    )


def cmd_demo(args) -> int:
    brief = _load_brief(args)
    trace_path = args.trace_path or f"traces/run_{args.run_name or 'demo'}.jsonl"
    with TraceRecorder(trace_path, meta={"brief": brief.title, "run": args.run_name or "demo"}) as rec:
        creator = CreatorAgent(rec)
        judge = JudgeAgent(rec)

        directions = creator.generate(brief)
        print(f"\n⚡ Creator: {len(directions)} направлений\n")
        for d in directions:
            print(f"  [{d.frame:12}] {d.name}: {d.concept}")

        verdicts = judge.judge(brief, directions)
        print(f"\n⚖️  Judge: топ-3\n")
        for v in verdicts[:3]:
            print(f"  {v.total:5.1f}  {v.direction_id}  ({v.summary})")

        # human override demo: veto the top-1 if user passes --veto
        if args.veto and verdicts:
            judge.veto(verdicts[0], args.veto)
            print(f"\n🚫 Вето человека: {verdicts[0].direction_id} — {args.veto}")

        metrics = export_trace_metrics(trace_path)
        print(f"\n📦 Траектория: {trace_path} ({metrics['total_events']} событий)")
        print(f"   {metrics['by_type']}")
    return 0


def cmd_traces(args) -> int:
    for p in sorted(Path(args.dir).glob("*.jsonl")):
        m = export_trace_metrics(str(p))
        print(f"{m['path']}: {m['total_events']} событий {m['by_type']}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="creative-court")
    sub = parser.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("demo")
    d.add_argument("--brief", default=None)
    d.add_argument("--desc", default=None)
    d.add_argument("--audience", default=None)
    d.add_argument("--brief-file", default=None)
    d.add_argument("--run-name", default="demo")
    d.add_argument("--trace-path", default=None)
    d.add_argument("--veto", default=None, help="veto the top-1 with this reason")
    d.set_defaults(fn=cmd_demo)

    t = sub.add_parser("traces")
    t.add_argument("--dir", default="traces")
    t.set_defaults(fn=cmd_traces)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
