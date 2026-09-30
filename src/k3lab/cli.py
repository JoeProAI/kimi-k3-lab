from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import load_suite
from .runner import compare_receipts, planned_ceiling, run_benchmark


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUITE = ROOT / "suites" / "k3-core-v1.jsonl"
DEFAULT_FIXTURES = ROOT / "fixtures" / "offline-responses.json"
DEFAULT_OUTPUT = ROOT / "runs"
DEFAULT_MODEL = "moonshotai/kimi-k3"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="k3lab", description="Receipt-first agent model evaluation")
    commands = parser.add_subparsers(dest="command", required=True)

    list_parser = commands.add_parser("list", help="List tasks without spending")
    list_parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)

    plan_parser = commands.add_parser("plan", help="Show the declared run ceiling")
    plan_parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    plan_parser.add_argument("--model", default=DEFAULT_MODEL)

    run_parser = commands.add_parser("run", help="Run offline fixtures or an explicitly capped live evaluation")
    run_parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    run_parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    run_parser.add_argument("--model", default=DEFAULT_MODEL)
    run_parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    run_parser.add_argument("--live", action="store_true")
    run_parser.add_argument("--max-usd", type=float, default=0.0)

    compare_parser = commands.add_parser("compare", help="Compare one or more JSON receipts")
    compare_parser.add_argument("receipts", nargs="+", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "list":
        for task in load_suite(args.suite):
            print(f"{task.id}\t{task.category}\t{task.title}")
        return 0
    if args.command == "plan":
        tasks = load_suite(args.suite)
        print(json.dumps({
            "model": args.model,
            "suite": str(args.suite),
            "tasks": len(tasks),
            "declared_cost_ceiling_usd": planned_ceiling(tasks),
            "live": False,
        }, indent=2))
        return 0
    if args.command == "run":
        path = run_benchmark(args.suite, args.model, args.output, args.live, args.max_usd, args.fixtures)
        receipt = json.loads(path.read_text(encoding="utf-8"))
        print(f"receipt={path}")
        print(f"score={receipt['score']:.2f} cost_usd={receipt['actual_cost_usd']:.6f}")
        return 0
    for row in compare_receipts(args.receipts):
        print(f"{row['model']}\tscore={row['score']:.2f}\tcost=${row['cost_usd']:.6f}\tpassed={row['passed']}\t{row['receipt']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
