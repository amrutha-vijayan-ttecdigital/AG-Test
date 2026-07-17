#!/usr/bin/env python3
"""Export Lucid document pages as PNG images with a manifest."""

from __future__ import annotations

import argparse
import re
import sys
import time
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
from lucid_core.parse import get_document_id  # noqa: E402
from lucid_core.serialization import write_bytes_atomic, write_json_atomic  # noqa: E402
from lucid_core.visuals import image_manifest_entry  # noqa: E402


def sanitize_filename(title: str, page_id: str | None, index: int | None) -> str:
    base = re.sub(r"[^A-Za-z0-9]+", "_", title.strip().lower()).strip("_") or "untitled"
    suffix = page_id or f"page_{index or 0}"
    return f"{base}_{suffix}.png"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Lucidchart pages as PNG")
    parser.add_argument("doc_id", help="Lucidchart document URL or ID")
    parser.add_argument("--output", "-o", default=".", help="Output directory")
    parser.add_argument("--page", "-p", type=int, help="Export one page by 1-based index")
    parser.add_argument("--page-id", help="Export one page by page ID")
    parser.add_argument("--list", "-l", action="store_true", help="List pages without exporting")
    parser.add_argument("--manifest", default="manifest.json", help="Manifest filename inside output directory")
    args = parser.parse_args()

    try:
        doc_id = get_document_id(args.doc_id)
        client = LucidClient()
        doc = client.fetch_document_contents(doc_id)
        pages = doc.get("pages", [])
        if not pages:
            pages = [{"id": None, "title": "page_1", "index": 0}]

        print(f"Found {len(pages)} page(s):")
        print(f"{'#':<4} {'Page ID':<32} {'Title'}")
        print("-" * 72)
        for i, page in enumerate(pages, 1):
            print(f"{i:<4} {str(page.get('id') or 'N/A'):<32} {page.get('title', 'Untitled')}")

        if args.list:
            return 0

        if args.page_id:
            targets = [p for p in pages if p.get("id") == args.page_id]
            if not targets:
                raise LucidCoreError(f"Page ID not found: {args.page_id}")
        elif args.page:
            if args.page < 1 or args.page > len(pages):
                raise LucidCoreError(f"Page {args.page} out of range (1-{len(pages)})")
            targets = [pages[args.page - 1]]
        else:
            targets = pages

        out_dir = Path(args.output)
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest = []
        for page in targets:
            index = int(page.get("index", pages.index(page))) + 1
            page_id = page.get("id")
            title = page.get("title", f"page_{index}")
            filename = sanitize_filename(title, page_id, index)
            out_path = out_dir / filename
            data = client.export_page_png(doc_id, page_id=page_id, page_index=index)
            write_bytes_atomic(out_path, data)
            manifest.append(image_manifest_entry(out_path, document_id=doc_id, page_id=page_id, page_index=index, title=title))
            print(f"Wrote: {out_path}")
            if len(targets) > 1:
                time.sleep(0.5)

        write_json_atomic(out_dir / args.manifest, {"documentId": doc_id, "pages": manifest})
        print(f"Wrote manifest: {out_dir / args.manifest}")
        return 0
    except LucidCoreError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

