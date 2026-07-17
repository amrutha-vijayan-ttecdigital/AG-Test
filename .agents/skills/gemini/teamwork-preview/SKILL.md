---
name: teamwork-preview
description: Execute complex tasks using an advanced multi-agent teamwork coordination team.
---

# Multi-Agent Teamwork Orchestration Skill

Use this skill when the user requests to solve a task using "teamwork", "multi-agent orchestration", or "the teamwork preview feature".

## Action Plan

When this skill is triggered, you must perform the following actions:

1. **Read the Sentinel Prompt**: Locate the current workspace directory and read the contents of the Sentinel system prompt from:
   `<workspace_root>/.agents/skills/gemini/teamwork-preview/references/sentinel.txt`
   *(If the workspace root is the parent multi-project root, look under `ces-agent-studio-starter-kit/.agents/skills/gemini/teamwork-preview/references/sentinel.txt`)*

2. **Define the Sentinel Subagent**:
   Call `define_subagent` with:
   - `name`: `teamwork_preview_sentinel`
   - `description`: `Project Sentinel managing multi-agent dispatch, monitoring, and final victory audit verification.`
   - `system_prompt`: [The contents of sentinel.txt]
   - `enable_subagent_tools`: `true`
   - `enable_write_tools`: `true`
   - `enable_mcp_tools`: `true`

3. **Invoke the Sentinel**:
   Call `invoke_subagent` with:
   - `TypeName`: `teamwork_preview_sentinel`
   - `Role`: `user_liaison`
   - `Prompt`: The user's original task request.

4. **Notify the User**:
   Provide a concise confirmation to the user that the Multi-Agent Teamwork Orchestration team has been initialized and the Sentinel is coordinating the task. Highlight that the Sentinel will spawn the Orchestrator, which in turn spawns workers, reviewers, and auditors to verify correctness.
