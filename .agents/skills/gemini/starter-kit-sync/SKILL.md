---
name: starter-kit-sync
description: Surgically syncs a project with the latest Antigravity Starter Kit guidance and skills without clobbering existing rules.
---

# Starter Kit Sync Skill

This skill is used to surgically update an existing project with the latest **Governance Log** rules, **Jira skills**, and **Lucidchart** architectural guidelines from the master Antigravity Starter Kit.

## Safety-First Policy (CRITICAL)
Before executing the sync script, agents **MUST** ensure the workspace has a clean revert point:
1. `git add . && git commit -m "pre-sync savepoint"`
2. `git checkout -b starter-kit-sync` (or a similar descriptive branch)

## Usage
When a workspace needs to adopt the latest starter kit features:
1. Run the Python `starter_kit_sync.py` script. 
2. The script will automatically detect the project type (Agent Studio or DFCX).
3. It will merge missing `AGENTS.md` sections (preserving custom rules) and import missing skills.
4. It will initialize the `agent.changes.log`.

## Command
```bash
# Usage: python3 starter_kit_sync.py <kit_root_path> [project_root_path]
python3 starter_kit_sync.py /path/to/cloned/starter-kit .
```
