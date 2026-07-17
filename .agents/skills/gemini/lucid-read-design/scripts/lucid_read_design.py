#!/usr/bin/env python3
"""Read a Lucid design through the shared graph compiler and render Markdown."""

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

from lucid_core.api import LucidClient  # noqa: E402
from lucid_core.errors import LucidCoreError  # noqa: E402
from lucid_core.parse import compile_document, get_document_id, load_document  # noqa: E402
from lucid_core.render_markdown import render_markdown  # noqa: E402
from lucid_core.serialization import write_json_atomic, write_text_atomic  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a Lucid REST snapshot as graph-derived Markdown.")
    parser.add_argument("url_or_id", nargs="?", help="Lucid document URL or ID. Not needed with --input-json.")
    parser.add_argument("--input-json", help="Use an offline Lucid REST contents JSON file.")
    parser.add_argument("--output", "-o", help="Markdown output path. Defaults to stdout.")
    parser.add_argument("--save-raw", help="Optional path for the exact raw JSON snapshot.")
    parser.add_argument("--save-ir", help="Optional path for the compiled graph IR JSON.")
    args = parser.parse_args()

    try:
        if args.input_json:
            raw = load_document(args.input_json)
            doc_id = raw.get("id")
        else:
            if not args.url_or_id:
                parser.error("url_or_id is required unless --input-json is provided")
            doc_id = get_document_id(args.url_or_id)
            raw = LucidClient().fetch_document_contents(doc_id)

        compiled = compile_document(raw, document_id=doc_id)
        markdown = render_markdown(compiled)

        if args.output:
            write_text_atomic(args.output, markdown)
            print(f"Wrote Markdown: {args.output}")
        else:
            print(markdown, end="")
        if args.save_raw:
            write_json_atomic(args.save_raw, raw)
        if args.save_ir:
            write_json_atomic(args.save_ir, compiled)
        return 0
    except LucidCoreError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

