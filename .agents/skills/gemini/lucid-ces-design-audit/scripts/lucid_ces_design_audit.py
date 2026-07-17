#!/usr/bin/env python3
"""Audit a compiled CES design IR, lint for ambiguities, and diff against runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

def add_core_to_path() -> None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "lucid-core" / "src"
        if candidate.exists():
            sys.path.insert(0, str(candidate))
            return
    raise RuntimeError("Could not locate sibling lucid-core/src")

add_core_to_path()

from lucid_core.serialization import write_text_atomic
from lucid_ces import (
    load_json,
    load_saved_runtime_export,
    diff_design_and_runtime,
    render_diff_markdown
)

def main() -> int:
    parser = argparse.ArgumentParser(description="Audit compiled CES IR, run lint, and compare against runtime export.")
    parser.add_argument("--ir", required=True, help="Path to compiled CES IR JSON file.")
    parser.add_argument("--report", help="Markdown lint report output path.")
    parser.add_argument("--fail-on", choices=["error", "warning", "never"], default="error",
                        help="Exit code behavior on diagnostics. Defaults to 'error'.")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Lint report format. Defaults to 'text'.")
    parser.add_argument("--ces-export", help="Saved CES app export/API snapshot JSON path.")
    parser.add_argument("--runtime-diff", help="Runtime diff markdown output path.")
    args = parser.parse_args()

    try:
        ir = load_json(args.ir)
        diagnostics = ir.get("diagnostics", [])

        # Formulate lint report content
        report_lines = ["# CES Design Audit & Linter Report", ""]
        if diagnostics:
            report_lines.append(f"Found {len(diagnostics)} diagnostic messages.")
            report_lines.append("")
            report_lines.append("| Code | Severity | Message | Remediation |")
            report_lines.append("|---|---|---|---|")
            for d in diagnostics:
                report_lines.append(f"| {d['code']} | {d['severity']} | {d['message']} | {d.get('remediation', '')} |")
        else:
            report_lines.append("No diagnostics or ambiguities found.")

        report_content = "\n".join(report_lines)

        # Print / Save lint report
        if args.report:
            write_text_atomic(args.report, report_content)
            print(f"Wrote audit report to {args.report}")
        else:
            if args.format == "json":
                print(json.dumps(diagnostics, indent=2))
            else:
                print(report_content)

        # Diff against runtime if provided
        if args.ces_export:
            runtime = load_saved_runtime_export(args.ces_export)
            diffs = diff_design_and_runtime(ir, runtime)
            diff_markdown = render_diff_markdown(diffs)
            
            if args.runtime-diff: # Note: arg is args.runtime_diff (argparse maps - to _)
                pass
            
            # Use argparse field
            out_diff_path = args.runtime_diff
            if out_diff_path:
                write_text_atomic(out_diff_path, diff_markdown)
                print(f"Wrote runtime diff report to {out_diff_path}")
            else:
                print("\n=== RUNTIME DIFF ===")
                print(diff_markdown)

        # Handle exit codes based on fail-on
        if args.fail_on != "never":
            has_error = any(d["severity"] == "error" for d in diagnostics)
            has_warning = any(d["severity"] in ("error", "warning") for d in diagnostics)
            
            if args.fail_on == "error" and has_error:
                print("Linter failed: errors were found.", file=sys.stderr)
                return 1
            if args.fail_on == "warning" and has_warning:
                print("Linter failed: warnings/errors were found.", file=sys.stderr)
                return 1

        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
