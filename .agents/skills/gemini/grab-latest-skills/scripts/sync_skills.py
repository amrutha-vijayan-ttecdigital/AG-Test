#!/usr/bin/env python3
"""
sync_skills.py — Grab the latest skills and rules from the starter kit repository.
"""

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

DEFAULT_REPO = "https://github.com/Dig-Voice-AI/Antigravity.git"
DEFAULT_BRANCH = "main"

def run_cmd(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\nError: {result.stderr.strip()}")
    return result.stdout.strip()

def main():
    parser = argparse.ArgumentParser(description="Pull and install/update skills from starter kit repo.")
    parser.add_argument("--target", default="global", choices=["global", "workspace"],
                        help="Where to install/sync the skills (default: global)")
    parser.add_argument("--repo", default=DEFAULT_REPO, help=f"Git repository to pull from (default: {DEFAULT_REPO})")
    parser.add_argument("--branch", default=DEFAULT_BRANCH, help=f"Git branch to pull (default: {DEFAULT_BRANCH})")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying files")
    args = parser.parse_args()

    # Resolve target directory
    if args.target == "global":
        target_dir = Path.home() / ".gemini" / "config" / "skills" / "gemini"
    else:
        # Detect active workspace root (either current directory or walk up to find .git/.agents)
        curr = Path.cwd()
        workspace_root = None
        for p in [curr] + list(curr.parents):
            if (p / ".agents").is_dir() or (p / ".git").is_dir():
                workspace_root = p
                break
        if not workspace_root:
            workspace_root = curr
        target_dir = workspace_root / ".agents" / "skills" / "gemini"

    print(f"Target Directory: {target_dir}")
    if not args.dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"Cloning {args.repo} (branch: {args.branch}) into temporary workspace...")
        try:
            run_cmd(f"git clone --depth 1 --branch {args.branch} {args.repo} .", cwd=temp_dir)
        except Exception as e:
            print(f"Error during repository clone: {e}")
            return 1

        # Search for gemini skill directories inside cloned repo
        source_dirs = []
        for starter_path in [
            "dfcx-starter-kit/.agents/skills/gemini", 
            "ces-agent-studio-starter-kit/.agents/skills/gemini",
            "qa-tools-starter-kit/.agents/skills/gemini"
        ]:
            full_source = temp_path / starter_path
            if full_source.is_dir():
                source_dirs.append(full_source)

        if not source_dirs:
            print("No skills folders found in starter kit repository structures.")
            return 1

        copied_count = 0
        skipped_count = 0

        for src_dir in source_dirs:
            for item in src_dir.iterdir():
                if item.is_dir():
                    skill_name = item.name
                    dest_skill_dir = target_dir / skill_name
                    
                    # Skip copying itself if it matches the current running script directory structure
                    if skill_name == "grab-latest-skills" and args.target == "workspace":
                        continue

                    print(f"[{'DRY-RUN' if args.dry_run else 'SYNCING'}] Skill: {skill_name}")
                    
                    if not args.dry_run:
                        # Copying/updating the skill folder
                        if dest_skill_dir.exists():
                            shutil.rmtree(dest_skill_dir)
                        shutil.copytree(item, dest_skill_dir)
                    copied_count += 1

        print(f"\nCompleted! Sync summary:")
        print(f"  Total Skills Checked/Synchronized: {copied_count}")
        print(f"  Target: {target_dir}")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
