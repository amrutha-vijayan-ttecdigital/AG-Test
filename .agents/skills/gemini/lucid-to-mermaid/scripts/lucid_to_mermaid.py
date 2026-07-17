#!/usr/bin/env python3
"""Render Lucid REST contents to Mermaid from shared graph IR."""

from __future__ import annotations

import argparse
import re
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
from lucid_core.render_mermaid import render_page_mermaid  # noqa: E402
from lucid_core.serialization import write_json_atomic, write_text_atomic  # noqa: E402


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "untitled"


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert Lucidchart/Lucidspark contents to Mermaid flowcharts.")
    parser.add_argument("url_or_id", nargs="?", help="Lucid document URL or ID. Not needed with --input-json.")
    parser.add_argument("--input-json", help="Use an offline Lucid REST contents JSON file.")
    parser.add_argument("--out-dir", default="docs/diagrams", help="Output directory for .mmd files.")
    parser.add_argument("--pages", nargs="+", help="Specific page titles to extract, case-insensitive.")
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
        target_pages = {p.lower() for p in args.pages or []}
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        extracted = 0
        for page in compiled["logical"].get("pages", []):
            title = page.get("title") or f"page-{page.get('index')}"
            if target_pages and title.lower() not in target_pages:
                continue
            path = out_dir / f"{safe_slug(title)}.mmd"
            write_text_atomic(path, render_page_mermaid(compiled, page))
            print(f"Wrote: {path}")
            extracted += 1

        if args.save_raw:
            write_json_atomic(args.save_raw, raw)
        if args.save_ir:
            write_json_atomic(args.save_ir, compiled)
        print(f"Extracted {extracted} page(s) to {out_dir}")
        return 0
    except LucidCoreError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

