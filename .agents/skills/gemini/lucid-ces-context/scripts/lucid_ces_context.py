#!/usr/bin/env python3
"""Generate task-specific context packets from the CES semantic IR."""

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
from lucid_ces import load_json, generate_context_packet

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate task-specific context packets for coding agents.")
    parser.add_argument("--ir", required=True, help="Input compiled CES IR JSON path.")
    parser.add_argument("--agent", help="Agent ID to target.")
    parser.add_argument("--task", help="Description of the task or requested change.")
    parser.add_argument("--radius", type=int, default=1, help="Search radius for neighbors. Defaults to 1.")
    parser.add_argument("--include-evaluations", action="store_true", help="Include evaluation scenarios.")
    parser.add_argument("--include-visual-evidence", action="store_true", help="Include visual evidence references.")
    parser.add_argument("--max-chars", type=int, help="Maximum packet size in characters.")
    parser.add_argument("--output", "-o", help="Output path for the Markdown context packet. Defaults to stdout.")
    args = parser.parse_args()

    try:
        ir = load_json(args.ir)
        packet = generate_context_packet(
            ir=ir,
            agent_id=args.agent,
            task=args.task,
            radius=args.radius,
            include_evaluations=args.include_evaluations,
            include_visual_evidence=args.include_visual_evidence,
            max_chars=args.max_chars
        )

        if args.output:
            write_text_atomic(args.output, packet)
            print(f"Wrote task-specific context packet to: {args.output}")
        else:
            print(packet)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
