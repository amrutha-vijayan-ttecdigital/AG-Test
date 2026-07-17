#!/usr/bin/env python3
"""Text/routing eval runner for a CES Agent Studio app.

Runs a JSON pack of test cases through runSession and asserts on the agent route,
tools invoked, response keywords, session params, and latency.

    python .agents/skills/gemini/ces-eval/scripts/run_eval.py --test-file pack.json
    python .agents/skills/gemini/ces-eval/scripts/run_eval.py --test-file pack.json --output results.json
    python .agents/skills/gemini/ces-eval/scripts/run_eval.py --test-file pack.json --no-fakes --entry-agent billing
    python .agents/skills/gemini/ces-eval/scripts/run_eval.py --test-file pack.json --deployed

Targeting:
  default      draft / current settings, useToolFakes=ON  (routing without real backends)
  --no-fakes   draft, real backends (tools actually call out)
  --deployed   the deployment in CES_DEPLOYMENT_ID (real backends), to test a cut version
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

# Make sibling modules (loader/assertions/engine) and the shared client importable.
_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
for parent in _HERE.parents:
    cand = parent / ".agents" / "scripts"
    if cand.is_dir():
        sys.path.insert(0, str(cand))
        break

from ces_client import CES        # type: ignore  # noqa: E402
from loader import load_test_cases  # noqa: E402
from engine import run_all          # noqa: E402


def print_result(r: dict) -> None:
    icon = "+" if r["passed"] else "x"
    print(f"  [{icon}] {r['test_name']}: {'PASS' if r['passed'] else 'FAIL'} ({r['total_latency_ms']:.0f}ms)")
    for t in r["turns"]:
        for a in t["assertions"]:
            if not a["passed"]:
                print(f"      FAIL [{a['type']}] {a['message']}")
    if r["error"]:
        print(f"      ERROR: {r['error']}")


def main() -> int:
    ap = argparse.ArgumentParser(description="CES text/routing eval runner")
    ap.add_argument("--test-file", required=True)
    ap.add_argument("--output", help="write JSON results here")
    ap.add_argument("--no-fakes", action="store_true", help="disable useToolFakes (real backends)")
    ap.add_argument("--deployed", action="store_true", help="target CES_DEPLOYMENT_ID instead of the draft")
    ap.add_argument("--entry-agent", default=None, help="start sessions at this agent id (default: root)")
    args = ap.parse_args()

    c = CES()
    test_cases = load_test_cases(args.test_file)
    deployment_id = c.deployment_id if args.deployed else None
    use_fakes = not (args.no_fakes or args.deployed)

    print(f"App:        {c.app_path}")
    print(f"Target:     {'deployment ' + deployment_id if deployment_id else 'draft / current settings'}")
    print(f"Tool fakes: {'ON' if use_fakes else 'OFF (real backends)'}")
    print(f"Tests:      {len(test_cases)} from {args.test_file}")
    print("-" * 60)

    results = run_all(test_cases, c, on_result=print_result,
                      deployment_id=deployment_id, use_tool_fakes=use_fakes,
                      entry_agent=args.entry_agent)

    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    total_ms = sum(r["total_latency_ms"] for r in results)
    print("-" * 60)
    print(f"Results: {passed} passed, {failed} failed, {len(results)} total ({total_ms:.0f}ms)")

    if args.output:
        pathlib.Path(args.output).write_text(json.dumps(
            {"summary": {"total": len(results), "passed": passed, "failed": failed},
             "results": results}, indent=2))
        print(f"Results -> {args.output}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
