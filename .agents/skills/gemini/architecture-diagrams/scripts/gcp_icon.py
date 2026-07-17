#!/usr/bin/env python3
"""Embed official GCP icons into an SVG diagram — safely.

Never type or paste icon base64 by hand: the data URIs are 2–6 KB long and
do not survive manual transcription (truncation/splicing corrupts the XML
and the whole diagram fails to render). Instead, write short placeholder
comments in the SVG and let this script expand them:

    <!-- gcp-icon: vertex-ai 987 214 36 -->        (name x y [size])

then run:

    python gcp_icon.py --inject diagram.svg

which replaces every placeholder with a correct <image> element, verifies
every icon data URI in the file decodes cleanly, and confirms the file is
well-formed XML. Run it (again) whenever placeholders change; it is
idempotent on already-expanded files.

Other modes:
    python gcp_icon.py --list                      # available icon names
    python gcp_icon.py --check diagram.svg         # validate only, no writes
    python gcp_icon.py bigquery -x 480 -y 236      # print one <image> element
"""
import argparse
import base64
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ICON_DIR = Path(__file__).resolve().parent.parent / "assets" / "gcp-icons"
PLACEHOLDER = re.compile(
    r'<!--\s*gcp-icon:\s*([\w-]+)\s+([\d.]+)\s+([\d.]+)(?:\s+([\d.]+))?\s*-->')


def element(name: str, x: float, y: float, size: float) -> str:
    path = ICON_DIR / f"{name}.svg"
    if not path.exists():
        close = [p.stem for p in ICON_DIR.glob("*.svg") if name.split("-")[0] in p.stem]
        sys.exit(f"No icon '{name}'. Close matches: {close or 'none'}. "
                 f"Use --list, or the product's category icon (cat-*).")
    b64 = base64.b64encode(path.read_bytes()).decode()
    return (f'<image x="{x:g}" y="{y:g}" width="{size:g}" height="{size:g}" '
            f'href="data:image/svg+xml;base64,{b64}"/>')


def check(text: str, label: str) -> int:
    """Validate XML well-formedness and every icon data URI. Returns #errors."""
    errors = 0
    try:
        ET.fromstring(text)
    except ET.ParseError as e:
        print(f"ERROR: {label} is not well-formed XML: {e}", file=sys.stderr)
        errors += 1
    for i, m in enumerate(re.finditer(r'base64,([A-Za-z0-9+/=]*)', text), 1):
        try:
            base64.b64decode(m.group(1), validate=True).decode()
        except Exception as e:
            print(f"ERROR: embedded image #{i} has a corrupt data URI ({e}). "
                  f"Do not hand-edit base64 — restore a placeholder comment and "
                  f"re-run --inject.", file=sys.stderr)
            errors += 1
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("icon", nargs="?", help="icon name, e.g. 'bigquery' or 'cat-networking'")
    ap.add_argument("--list", action="store_true", help="list available icons")
    ap.add_argument("--inject", metavar="SVG", help="expand gcp-icon placeholders in file")
    ap.add_argument("--check", metavar="SVG", help="validate file's icon embeds, no writes")
    ap.add_argument("-x", type=float, default=0)
    ap.add_argument("-y", type=float, default=0)
    ap.add_argument("-s", "--size", type=float, default=36, help="width=height px (default 36)")
    args = ap.parse_args()

    if args.list:
        for p in sorted(ICON_DIR.glob("*.svg")):
            print(p.stem)
        return 0

    if args.check:
        n = check(Path(args.check).read_text(), args.check)
        print("OK: XML well-formed, all icon embeds valid." if n == 0 else f"{n} problem(s).")
        return 1 if n else 0

    if args.inject:
        p = Path(args.inject)
        text = p.read_text()
        expanded = 0

        def sub(m: re.Match) -> str:
            nonlocal expanded
            expanded += 1
            return element(m.group(1), float(m.group(2)), float(m.group(3)),
                           float(m.group(4) or 36))

        text = PLACEHOLDER.sub(sub, text)
        if check(text, str(p)):
            print("Aborted: result failed validation; file not modified.", file=sys.stderr)
            return 1
        p.write_text(text)
        print(f"Expanded {expanded} placeholder(s); file validates clean.")
        return 0

    if not args.icon:
        for p in sorted(ICON_DIR.glob("*.svg")):
            print(p.stem)
        return 0
    print(element(args.icon, args.x, args.y, args.size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
