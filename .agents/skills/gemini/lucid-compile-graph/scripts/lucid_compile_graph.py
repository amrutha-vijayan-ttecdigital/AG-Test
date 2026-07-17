#!/usr/bin/env python3
"""Compile a Lucid REST snapshot into canonical graph artifacts."""

from __future__ import annotations

import argparse
import json
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
from lucid_core.context_packet import build_context_packet  # noqa: E402
from lucid_core.errors import LucidCoreError  # noqa: E402
from lucid_core.parse import compile_document, get_document_id, load_document  # noqa: E402
from lucid_core.render_markdown import render_markdown  # noqa: E402
from lucid_core.render_mermaid import render_page_mermaid  # noqa: E402
from lucid_core.serialization import write_json_atomic, write_text_atomic  # noqa: E402


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "untitled"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile Lucid REST contents into graph IR artifacts.")
    parser.add_argument("url_or_id", nargs="?", help="Lucid document URL or ID. Not needed with --input-json.")
    parser.add_argument("--input-json", help="Use a saved Lucid REST contents JSON file instead of fetching.")
    parser.add_argument("--out-dir", default="docs/designs/lucid-compiled", help="Output directory.")
    parser.add_argument("--save-raw", action="store_true", help="Save exact raw JSON snapshot when fetching from Lucid.")
    parser.add_argument("--page", action="append", help="Page title to render. May be passed multiple times.")
    args = parser.parse_args()

    try:
        if args.input_json:
            raw = load_document(args.input_json)
            document_id = raw.get("id")
        else:
            if not args.url_or_id:
                parser.error("url_or_id is required unless --input-json is provided")
            document_id = get_document_id(args.url_or_id)
            raw = LucidClient().fetch_document_contents(document_id)

        compiled = compile_document(raw, document_id=document_id)
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        write_json_atomic(out_dir / "physical.json", compiled["physical"])
        write_json_atomic(out_dir / "logical.json", compiled["logical"])
        write_json_atomic(out_dir / "semantic.json", compiled["semantic"])
        write_json_atomic(out_dir / "analysis.json", compiled["analysis"])
        write_json_atomic(out_dir / "context-packet.json", build_context_packet(compiled))
        write_text_atomic(out_dir / "design.md", render_markdown(compiled))
        if args.save_raw or args.input_json:
            write_json_atomic(out_dir / "raw.json", raw)

        page_filter = {p.lower() for p in args.page or []}
        for page in compiled["logical"].get("pages", []):
            title = page.get("title") or page.get("id") or "page"
            if page_filter and title.lower() not in page_filter:
                continue
            write_text_atomic(out_dir / f"{safe_slug(title)}.mmd", render_page_mermaid(compiled, page))

        print(f"Compiled Lucid graph artifacts to {out_dir}")
        print(f"Diagnostics: {len(compiled['logical'].get('diagnostics', [])) + len(compiled['semantic'].get('diagnostics', []))}")
        return 0
    except LucidCoreError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

