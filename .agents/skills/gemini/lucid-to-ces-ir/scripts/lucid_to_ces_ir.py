#!/usr/bin/env python3
"""Compile a Lucid REST snapshot into the CES semantic IR."""

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

from lucid_core.api import LucidClient
from lucid_core.parse import compile_document, get_document_id, load_document
from lucid_ces import compile_design, to_dict, write_json_atomic

def main() -> int:
    parser = argparse.ArgumentParser(description="Compile a Lucid snapshot into the CES semantic IR.")
    parser.add_argument("url_or_id", nargs="?", help="Lucid document URL or ID. Not needed with --input-json.")
    parser.add_argument("--input-json", help="Use an offline Lucid REST contents JSON file.")
    parser.add_argument("--output", "-o", required=True, help="CES IR JSON output path.")
    parser.add_argument("--save-raw", help="Optional path for the exact raw JSON snapshot.")
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

        compiled_doc = compile_document(raw, document_id=doc_id)
        ces_ir = compile_design(compiled_doc)
        
        # Serialize to dict and write to file
        serialized_ir = to_dict(ces_ir)
        write_json_atomic(args.output, serialized_ir)
        print(f"Successfully compiled CES IR to {args.output}")

        if args.save_raw:
            write_json_atomic(args.save_raw, raw)
            print(f"Saved raw snapshot to {args.save_raw}")
            
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
