---
name: grab-latest-skills
description: Clones the starter kit repository and copies the latest custom rules and skills into the global or local Antigravity config directory. Use when the user asks to get the latest skills, update conversational AI skills, or grab skill updates from origin.
---

# grab-latest-skills

This skill pulls the latest skills and rules from the official Dialogflow CX and CX Agent Studio starter kit repository and installs/updates them in the local workspace `.agents` directory or your global `~/.gemini/config/` directory.

## Triggering the Skill
This skill is triggered when the user requests an update, for example:
* "grab the latest skills"
* "update our skills from the starter kit repo"
* "install latest kit customizations"

## How to Execute the Update
To sync and install the latest updates, execute the Python script:
```bash
python3 .agents/skills/gemini/grab-latest-skills/scripts/sync_skills.py [options]
```

### Script Arguments:
* `--target` (default: `global`): Where to copy the skills. Options:
  * `global`: Installs/updates rules in `~/.gemini/config/skills/`.
  * `workspace`: Installs/updates rules in the active workspace's `.agents/skills/` directory.
  * `<custom_path>`: Installs to a specified directory.
* `--repo` (default: `https://github.com/Dig-Voice-AI/Antigravity.git`): The remote git repository URL.
* `--branch` (default: `main`): The branch to pull updates from.
* `--dry-run`: Performs a diff comparison and lists files that will be added/updated/removed without making actual writes.
