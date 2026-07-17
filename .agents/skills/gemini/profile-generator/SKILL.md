---
name: profile-generator
description: Automated setup assistant for coding agents. Use when the agent needs to initialize dialogflowcx/profiles.json or .env, configure project connections, or onboard to the active workspace. This skill should be invoked automatically by the agent before running any live DFCX/CES APIs if profiles/credentials are missing.
---

# profile-generator

This is an agent-invoked onboarding skill that automatically configures connection profiles (`profiles.json`) and environment variables (`.env`) for Dialogflow CX and CX Agent Studio.

## Auto-Invocation Protocol (For Agents)

Coding agents **MUST** automatically trigger this skill during their initial research phase if they detect that:
1. `dialogflowcx/profiles.json` does not exist or contains template placeholders.
2. `.env` does not exist or contains placeholders.

Do not ask the user for manual profile setup commands; invoke this skill to configure it programmatically.

## Execution

The script can be run automatically by the agent or manually by the user:

```bash
python3 .agents/skills/gemini/profile-generator/scripts/generate_profile.py [options]
```

### Arguments:
* `--project` (optional): The target GCP Project ID.
* `--agent-id` (optional): The target Dialogflow CX or CES Agent UUID.
* `--location` (default: `us-central1`): GCP region/location.
* `--dry-run`: Preview the output profile files without writing them.
