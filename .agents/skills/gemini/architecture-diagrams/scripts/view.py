#!/usr/bin/env python3
"""Open an SVG diagram in the default system web browser for visual inspection.

Usage:
    python view.py diagram.svg
"""
import argparse
import sys
import webbrowser
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("svg", help="Path to the SVG file to view")
    args = ap.parse_args()

    svg_path = Path(args.svg).resolve()
    if not svg_path.exists():
        print(f"Error: {args.svg} not found.", file=sys.stderr)
        return 1

    # Convert the file path to a browser-compatible URL
    url = svg_path.as_uri()
    print(f"Opening {svg_path.name} in your default browser...")
    webbrowser.open(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
