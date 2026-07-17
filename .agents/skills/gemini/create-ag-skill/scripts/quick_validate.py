#!/usr/bin/env python3
"""
quick_validate.py — Validate that a skill directory has the correct structure and metadata.
"""

import argparse
import re
import sys
from pathlib import Path

def parse_frontmatter(content: str) -> dict:
    # Match YAML frontmatter between --- markers at start of file
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}
    
    yaml_text = match.group(1)
    metadata = {}
    for line in yaml_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            metadata[k.strip().lower()] = v.strip().strip('"').strip("'")
            
    return metadata

def main():
    parser = argparse.ArgumentParser(description="Validate an Antigravity skill.")
    parser.add_argument("path", help="Path to the skill directory (e.g. '.agents/skills/gemini/my-skill')")
    args = parser.parse_args()

    skill_dir = Path(args.path)
    if not skill_dir.is_dir():
        print(f"FAIL: Directory does not exist: {skill_dir}", file=sys.stderr)
        return 1

    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        print(f"FAIL: SKILL.md not found in {skill_dir}", file=sys.stderr)
        return 1

    try:
        content = skill_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"FAIL: Cannot read SKILL.md: {e}", file=sys.stderr)
        return 1

    metadata = parse_frontmatter(content)
    if not metadata:
        print("FAIL: SKILL.md does not start with valid YAML frontmatter surrounded by '---' separators.", file=sys.stderr)
        return 1

    errors = []
    
    # 1. Check name existence
    if "name" not in metadata:
        errors.append("Missing required frontmatter key: 'name'")
    else:
        # 2. Check name matches folder name
        expected_folder = metadata["name"]
        actual_folder = skill_dir.name
        if expected_folder != actual_folder:
            errors.append(f"Frontmatter 'name' ('{expected_folder}') does not match directory name ('{actual_folder}')")

    # 3. Check description existence
    if "description" not in metadata:
        errors.append("Missing required frontmatter key: 'description'")
    elif not metadata["description"].strip() or "<enter" in metadata["description"].lower():
        errors.append("Description is empty or contains placeholder text.")

    if errors:
        print(f"FAIL: Validation failed for skill at {skill_dir}:")
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"PASS: Skill at '{skill_dir}' is valid.")
    print(f"  - Name: {metadata.get('name')}")
    print(f"  - Description: {metadata.get('description')}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
