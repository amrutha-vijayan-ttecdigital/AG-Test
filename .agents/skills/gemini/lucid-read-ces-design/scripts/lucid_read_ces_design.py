#!/usr/bin/env python3
"""Read a compiled CES IR JSON and render a Markdown report."""

from __future__ import annotations

import argparse
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
from lucid_ces import load_json, render_markdown_report

def main() -> int:
    parser = argparse.ArgumentParser(description="Render a compiled CES IR JSON as Markdown report.")
    parser.add_argument("--ir", required=True, help="Input compiled CES IR JSON path.")
    parser.add_argument("--output", "-o", help="Markdown output path. Defaults to stdout.")
    args = parser.parse_args()

    try:
        ir = load_json(args.ir)
        markdown = render_markdown_report(ir)

        if args.output:
            write_text_atomic(args.output, markdown)
            print(f"Wrote Markdown report to: {args.output}")
        else:
            print(markdown)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
