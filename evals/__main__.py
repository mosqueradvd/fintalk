"""CLI: ``python -m evals [--min-pass 0.8] [--only NAME] [--json PATH]``

Exit code is 0 when pass_rate >= --min-pass, 1 otherwise — so this can gate a
deploy in CI. Exits 0 with a notice (not a failure) when the prerequisites
aren't there (no API key, DB down), so it can sit in a pipeline that doesn't
always have secrets.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from chat.config import ANTHROPIC_API_KEY
from core.db import close_pool, query

from .harness import load_cases, run_suite, to_dict


def _prereqs_ok() -> str | None:
    if not ANTHROPIC_API_KEY:
        return "ANTHROPIC_API_KEY not set — skipping behavioural evals."
    try:
        query("SELECT 1")
    except Exception as exc:  # noqa: BLE001
        return f"Postgres not reachable ({exc}) — skipping behavioural evals."
    return None


def _print_report(suite_dict: dict) -> None:
    print()
    print(f"{'case':<32} {'result':<7} {'tools':<7} {'lat':>6} {'cost':>10}")
    print("-" * 66)
    for c in suite_dict["cases"]:
        mark = "PASS" if c["passed"] else "FAIL"
        failed = [k for k, v in c["checks"].items() if not v]
        detail = "" if c["passed"] else "  ✗ " + ", ".join(failed or [c["error"] or "?"])
        print(
            f"{c['name']:<32} {mark:<7} {len(c['tools_called']):<7} "
            f"{c['latency_s']:>5}s ${c['cost_usd']:>8.5f}{detail}"
        )
    print("-" * 66)
    print(
        f"pass_rate={suite_dict['pass_rate']:.0%}  "
        f"tool_precision={suite_dict['tool_precision']:.0%}  "
        f"cost=${suite_dict['total_cost_usd']:.4f}  "
        f"wall={suite_dict['wall_s']}s"
    )
    print()


def main() -> int:
    ap = argparse.ArgumentParser(prog="python -m evals")
    ap.add_argument("--min-pass", type=float, default=1.0,
                    help="fail (exit 1) if pass_rate is below this (default 1.0)")
    ap.add_argument("--only", help="run only the case with this name")
    ap.add_argument("--json", type=Path, help="also write the full report here")
    args = ap.parse_args()

    skip = _prereqs_ok()
    if skip:
        print(skip)
        return 0

    cases = load_cases()
    if args.only:
        cases = [c for c in cases if c["name"] == args.only]
        if not cases:
            print(f"no case named {args.only!r}")
            return 1

    try:
        suite = asyncio.run(run_suite(cases))
    finally:
        close_pool()

    report = to_dict(suite)
    _print_report(report)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2))
        print(f"wrote {args.json}")

    ok = report["pass_rate"] >= args.min_pass
    if not ok:
        print(f"FAIL: pass_rate {report['pass_rate']:.0%} < required {args.min_pass:.0%}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
