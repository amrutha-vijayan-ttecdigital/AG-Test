#!/usr/bin/env python3
"""Create a Lucid Standard Import archive from Mermaid, with upload guarded by --apply."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests


def add_core_to_path() -> None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "lucid-core" / "src"
        if candidate.exists():
            sys.path.insert(0, str(candidate))
            return
    raise RuntimeError("Could not locate sibling lucid-core/src")


add_core_to_path()

from lucid_core.errors import LucidCoreError, MermaidParseError  # noqa: E402
from lucid_core.mermaid_import import parse_mermaid, write_standard_import_zip  # noqa: E402

MEDIA_TYPE = "x-application/vnd.lucid.standardImport"


def upload(zip_path: Path) -> None:
    token = os.getenv("LUCID_API_KEY") or os.getenv("LUCID_TOKEN")
    if not token:
        raise LucidCoreError("Set LUCID_API_KEY. LUCID_TOKEN is accepted as a deprecated alias.")
    headers = {"Authorization": f"Bearer {token}", "Lucid-Api-Version": "1", "Accept": "application/json"}
    with zip_path.open("rb") as fh:
        files = {"file": (zip_path.name, fh, MEDIA_TYPE)}
        data = {"product": "lucidchart"}
        resp = requests.post("https://api.lucid.co/v1/documents", headers=headers, files=files, data=data, timeout=(10, 60))
    if resp.status_code not in (200, 201):
        raise LucidCoreError(f"Lucid import failed with HTTP {resp.status_code}: {resp.text[:400]}")
    result = resp.json()
    print("Lucid document created.")
    print(f"Title: {result.get('title')}")
    print(f"View URL: {result.get('viewUrl')}")
    print(f"Edit URL: {result.get('editUrl')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert Mermaid (.mmd) to a Lucid Standard Import archive.")
    parser.add_argument("file", help="Path to the Mermaid .mmd file.")
    parser.add_argument("--out", help="Output .lucid zip path. Defaults beside input.")
    parser.add_argument("--apply", action="store_true", help="Upload to Lucid. Without this flag, the command is read-only/offline.")
    args = parser.parse_args()

    try:
        source = Path(args.file)
        if not source.exists():
            raise MermaidParseError(f"File not found: {source}")
        nodes, edges = parse_mermaid(source.read_text(encoding="utf-8"))
        out_zip = Path(args.out) if args.out else source.with_suffix(".lucid")
        write_standard_import_zip(out_zip, source.stem.replace("-", " ").title(), nodes, edges)
        print(f"Wrote Lucid Standard Import archive: {out_zip}")
        print(f"Parsed {len(nodes)} node(s), {len(edges)} edge(s).")
        if args.apply:
            upload(out_zip)
        else:
            print("Upload skipped. Re-run with --apply to create a Lucid document.")
        return 0
    except LucidCoreError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

