#!/usr/bin/env python3
"""
create_handoff.py — Generate a structured transition report for another agent or human.
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

def run_cmd(cmd, cwd=None):
    try:
        result = subprocess.run(cmd, shell=True, text=True, capture_output=True, cwd=cwd)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""

def redact_secrets(text: str) -> str:
    # Basic regex patterns to mask sensitive tokens/passwords/keys
    patterns = [
        (r'(?i)(api_key|password|token|secret|auth|pwd)\s*[:=]\s*["\']?[a-zA-Z0-9_\-+=]{8,}["\']?', r'\1: [REDACTED]'),
        (r'Bearer\s+[a-zA-Z0-9_\-\.\+]{15,}', 'Bearer [REDACTED]')
    ]
    for pattern, repl in patterns:
        text = re.sub(pattern, repl, text)
    return text

def main():
    parser = argparse.ArgumentParser(description="Generate a handoff document.")
    parser.add_argument("--recipient", default="human", choices=["human", "agent"],
                        help="Handoff recipient type: human or agent (default: human)")
    parser.add_argument("--focus", default="", help="Description of what the next session will focus on")
    parser.add_argument("--out", help="Output file path (defaults to OS temporary directory)")
    args = parser.parse_args()

    # Gather Git info
    branch = run_cmd("git branch --show-current") or "unknown"
    git_status = run_cmd("git status --porcelain")
    recent_commits = run_cmd("git log -n 5 --oneline")
    
    modified_files = []
    if git_status:
        for line in git_status.split("\n"):
            line = line.strip()
            if line:
                parts = line.split(None, 1)
                if len(parts) == 2:
                    modified_files.append(parts[1])

    # Determine default suggested skills based on files changed
    suggested_skills = ["grab-latest-skills", "create-ag-skill"]
    has_dfcx_changes = any("dfcx-starter-kit" in f for f in modified_files)
    has_ces_changes = any("ces-agent-studio-starter-kit" in f for f in modified_files)
    
    if has_dfcx_changes:
        suggested_skills.extend(["dfcx_detect_intent.py", "dfcx_validate.py"])
    if has_ces_changes:
        suggested_skills.extend(["ces-sync", "ces-voice-test", "ces-deploy"])

    # Build Markdown Content
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = f"Antigravity Handoff Report - {timestamp}"
    
    content_parts = [
        f"# {title}",
        "",
        "## Transition Metadata",
        f"* **Recipient Type**: {args.recipient.upper()}",
        f"* **Source Git Branch**: `{branch}`",
        f"* **Transition Timestamp**: {timestamp}",
        ""
    ]

    if args.focus:
        content_parts.extend([
            "## Next Session Focus",
            redact_secrets(args.focus),
            ""
        ])

    content_parts.extend([
        "## Current Status",
        "The following workspace changes are currently staged or modified:",
        ""
    ])

    if modified_files:
        for f in modified_files:
            content_parts.append(f"* `{f}`")
    else:
        content_parts.append("* No local changes modified or unstaged in the repository.")
    content_parts.append("")

    if recent_commits:
        content_parts.extend([
            "## Recent Commits",
            "```",
            recent_commits,
            "```",
            ""
        ])

    content_parts.extend([
        "## Suggested Skills to Run Next",
        "The incoming developer or agent should consider using the following skills or tools next:",
    ])
    for skill in suggested_skills:
        content_parts.append(f"* `{skill}`")
    content_parts.append("")

    content_parts.extend([
        "## References",
        "* Refer to [implementation_plan.md](implementation_plan.md) or [walkthrough.md](walkthrough.md) for detailed blueprints.",
        "* Refer to [AGENTS.md](AGENTS.md) for workspace-level rules and conventions.",
        ""
    ])

    full_markdown = "\n".join(content_parts)

    # Determine Output File
    if args.out:
        out_path = Path(args.out)
    else:
        ts_slug = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_path = Path(tempfile.gettempdir()) / f"antigravity-handoff-{ts_slug}.md"

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(full_markdown, encoding="utf-8")
        print(f"Handoff document successfully generated and saved to:")
        print(f"  {out_path.resolve()}")
    except Exception as e:
        print(f"Error writing handoff document: {e}", file=sys.stderr)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
