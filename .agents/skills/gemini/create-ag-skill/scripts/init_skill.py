#!/usr/bin/env python3
"""
init_skill.py — Scaffold a new Antigravity skill in the workspace.
"""

import argparse
import re
import sys
from pathlib import Path

def normalize_name(name: str) -> str:
    # Convert to lowercase and replace spaces/underscores with hyphens
    s = name.strip().lower()
    s = re.sub(r'[\s_]+', '-', s)
    s = re.sub(r'[^a-z0-9\-]', '', s)
    return s

def main():
    parser = argparse.ArgumentParser(description="Scaffold a new Antigravity skill.")
    parser.add_argument("name", help="The name of the new skill (e.g. 'my-cool-skill')")
    parser.add_argument("--resources", default="scripts,references",
                        help="Comma-separated list of resource folders to create: scripts,references,assets")
    parser.add_argument("--dry-run", action="store_true", help="Preview the creation without writing files")
    args = parser.parse_args()

    skill_name = normalize_name(args.name)
    if not skill_name:
        print("Error: Invalid skill name.", file=sys.stderr)
        return 1

    # Detect active workspace root's skill folder
    curr = Path.cwd()
    skills_base = None
    for p in [curr] + list(curr.parents):
        if (p / ".agents").is_dir():
            skills_base = p / ".agents" / "skills" / "gemini"
            break

    if not skills_base:
        skills_base = curr / ".agents" / "skills" / "gemini"

    skill_dir = skills_base / skill_name
    print(f"Target Skill Directory: {skill_dir}")

    if skill_dir.exists():
        print(f"Error: Skill '{skill_name}' already exists at {skill_dir}", file=sys.stderr)
        return 1

    # Plan creation
    created_items = []
    skill_file = skill_dir / "SKILL.md"
    created_items.append((skill_file, "file"))

    resource_types = [r.strip().lower() for r in args.resources.split(",") if r.strip()]
    for res in resource_types:
        if res in ["scripts", "references", "assets"]:
            created_items.append((skill_dir / res, "dir"))

    if args.dry_run:
        print("\n[DRY-RUN] Would create the following structure:")
        for item, itype in created_items:
            print(f"  [{itype.upper()}] {item.relative_to(skills_base.parent.parent.parent) if skills_base.parent.parent.parent in item.parents else item}")
        return 0

    # Write files
    try:
        skill_dir.mkdir(parents=True, exist_ok=True)
        
        # Write SKILL.md template
        template_content = f"""---
name: {skill_name}
description: <Enter trigger description here - this helps Antigravity understand when to use this skill>
---

# {skill_name}

Provide instructions, guidelines, and workflows for this skill here. Keep it concise (under 500 lines).

## How to use
Describe when and how to execute this skill.
"""
        skill_file.write_text(template_content, encoding="utf-8")
        print(f"Created file: {skill_file}")

        # Create resource dirs
        for item, itype in created_items:
            if itype == "dir":
                item.mkdir(parents=True, exist_ok=True)
                print(f"Created directory: {item}")

        print(f"\nSuccess! Scaffolded new skill '{skill_name}' successfully.")
        print(f"Edit the triggers in: {skill_file}")

    except Exception as e:
        print(f"Error scaffolding skill: {e}", file=sys.stderr)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
