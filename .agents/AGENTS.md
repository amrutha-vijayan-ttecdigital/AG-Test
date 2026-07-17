# AGENTS.md - Greenfield CX Agent Studio Workspace Rules

## Objective
This workspace is a clean, greenfield environment for planning, designing, and building conversational agents on Google Cloud's Customer Experience (CX) Agent Studio.

---

## 1. Research & Document Integrity

### CRITICAL: Setup Must Pass First
Before live Google Cloud, Lucid, Jira, or deployment workflows, you **MUST** ensure the local `.env` and connection variables are configured. As an agent, you should automatically invoke the `profile-generator` skill to build this file dynamically. Alternatively, run the setup manually:
```bash
./setup.sh
```
or, for an existing `.env`:
```bash
./setup.sh --verify
```
Do not proceed if setup reports missing ADC, a mismatched active gcloud account,
an inaccessible project, missing required `.env` values, or partial Jira
credentials.

### CRITICAL: Git Branch & Write Access Verification (Onboarding Gate)
Before making any repository changes or syncing local assets to the live draft, verify the current active local branch, remote tracking status (e.g., via `git status`), and that the local git identity (`user.name` and `user.email`) is configured. Additionally, verify write permissions to the remote organization (e.g., via `git push --dry-run`) before modifying source code. Once per session during the initial research/onboarding phase, output the active branch name and confirm with the user that this is the expected branch to prevent clobbering the workspace or remote environments with incorrect agent versions.

### CRITICAL: Private Repository Access & GitHub CLI
- **Rule**: Direct HTTP requests (such as `read_url_content`) or browser subagents (`browser_subagent`) to private GitHub repositories (e.g., under the `Dig-Voice-AI` organization) are unauthorized and will fail with a 404. To retrieve files, list issues/PRs, or fetch repository/issue metadata, you **MUST** use the local GitHub CLI (`gh`) or standard git command tools rather than web scraping or direct URL fetches. If you need to verify or configure this, run `gh auth status` or suggest installing/authenticating `gh` if missing.


### CRITICAL: Always Perform Live Research
Do **NOT** rely solely on the local markdown files, research summaries, or code templates in this workspace as the absolute, static source of truth. CX Agent Studio, the Agent Development Kit (ADK), and Google Cloud APIs are subject to updates, quota changes, and feature enhancements.
- **Rule**: Whenever you plan a new integration, callback pattern, or tool schema, you **MUST** run active queries against the `google-developer-knowledge` MCP server to verify the latest platform capabilities and constraints.
- **MCP Server Name**: `google-developer-knowledge`
- **Exposed Tools**: `search_documents(query)`, `answer_query(query)`, `get_documents(parent)`.
- **Target Terms**: Use specific API/resource terms when querying, such as `"ces.googleapis.com"`, `"llmAgent"`, `"audioProcessingConfig"`, or `"modelSettings"`.

---

## 2. Workspace Directory Convention

This workspace uses a standard directory layout. Place artifacts in the correct
locations to keep the repository navigable across sprints and team members.

| Directory | Purpose |
|---|---|
| `docs/designs/` | Core design specifications — Lucid compiled IRs, markdown design specs, review docs. Output target for `lucid-read-design`, `lucid-compile-graph`, and `lucid-to-ces-ir` scripts. |
| `docs/designs/supplemental/` | Business rules, edge case documentation, client-provided reference material, and supporting design context that is not a primary flow spec. |
| `docs/diagrams/` | Mermaid `.mmd` flowcharts and architecture diagrams. Output target for `lucid-to-mermaid` scripts. |
| `docs/qa/` | QA checklists, UAT handoff documents, human test scripts, and governance reports. |
| `docs/reports/` | Generated reports — latency dashboards, status summaries, deployment reports, smoke test HTML. |
| `docs/testdata/` | Test fixtures (JSON, CSV, XLSX), golden data sets, test scenario definitions, and test environment credentials references. |
| `exports/` | All state snapshots — version exports, draft captures, and pre-change rollback snapshots. Use filename prefixes to distinguish purpose: `version-` for deployment versions, `draft-` for draft snapshots, `pre-change-` for rollback safety snapshots, `uat-` for UAT captures. Output target for `ces-deploy export.py`. |
| `testcases/` | Test case specifications and execution results for `ces-eval` and `ces-voice-test` runs. |

When scaffolding a new project from this starter kit, create these directories if
they do not already exist. The `.gitkeep` files ensure empty directories are
tracked in Git.

---

## 3. Core Architecture & Primitives
- **ADK Runtime Model**: This platform is driven by system instructions, custom Python callbacks, and tool definitions. It is **not** playbook-based. Avoid using Dialogflow CX primitives (pages, flows, transition routes, detectIntent) as implementation structures.
- **XML-Structured Instructions**: Prompting works best when structured in standard XML tags (e.g., `<role>`, `<persona>`, `<taskflow>`, `<subtask>`).
- **Chips & References**: Reference sub-agents with `{@AGENT: Agent Name}`, tools with `{@TOOL: tool_name}`, and variables with `{variable_name}` inside prompts.
- **Variables**: Use `{{static_var}}` for static configuration (invalidates prompt cache on update) and `{dynamic_var}` for session state fetched via tools (preserves prompt cache).

---

## 4. Developer Callback Guidelines
- **Multi-Agent Review Loop**: When writing, generating, or modifying custom callbacks, agents **MUST** trigger the `callback-planner` skill. It spins up a multi-agent review loop (Designer + Reviewer/Auditor) and uses `validate_callback.py` to ensure sandbox, parameter, and voice safety.
- **Parameter Name Gotchas**: Parameter names for the primary callback functions **must match the platform specifications exactly** due to keyword argument passing in the ADK:
  - `before_agent_callback(callback_context)`
  - `after_agent_callback(callback_context)`
  - `before_model_callback(callback_context, llm_request)`
  - `after_model_callback(callback_context, llm_response)`
  - `before_tool_callback(tool, input, callback_context)`
  - `after_tool_callback(tool, input, callback_context, tool_response)`
  *Renaming parameters (e.g., `callback_context` -> `ctx`) will cause immediate `TypeError` failures at runtime.*
- **Outbound Network Calls**: Custom callback code runs in a sandbox where raw network sockets are disabled. Outbound HTTP requests must use the `ces_requests` library wrapper.
- **Tool Chaining**: Callbacks should be used for orchestration, state validation, and routing. Implement backend logic as declared OpenAPI tools and invoke them inside callbacks using `tools.<name>(args)` or `async_tools.<name>(args)`.

---

## 5. Live Agent Handoff & Escalation
- Escalation must invoke the system tool `end_session`.
- Telephony routing details must be structured inside the `params` object of `end_session` under the `PHONE_GATEWAY_TRANSFER` and `LIVE_AGENT_HANDOFF` blocks:
  - Use `phone_number` and `use_originating_trunk` (boolean) inside `PHONE_GATEWAY_TRANSFER`.
  - Use `sip-refer` (boolean) and `uui-headers` (list of strings) inside `LIVE_AGENT_HANDOFF`.

---

## 6. Console/API Change-Control Process
Keep the live Agent Studio console configuration and the local workspace repository synchronized:
1. **Change Tracking**: If you mutate the agent configuration in the Google Cloud Console or via the API, record the modification in a changelog or operational note in the workspace.
2. **Snapshotting**: Export and save small JSON snapshots of tool schemas, instructions, or callback code in the repository to maintain traceability.
3. **Blueprints First**: Do not commit ad-hoc or temporary debug callback code or prompts to the main branch without documenting them as finalized blueprints.

> The `ces-*` skills (Section 8) implement this process: `ces-sync` pushes local
> source to the draft, `ces-deploy` cuts versions + captures the live state to
> git, and `ces-api`/`ces-eval`/`ces-voice-test` verify behavior. Prefer them
> over manual console edits for anything that should be reproducible.

---

## 7. Visual Design Verification & The Crop Tool
When reviewing conversational flows designed in large flowcharts (exported as `.png` files, e.g., 6000x6000px), edge labels, prompts, and intent connectors can be difficult for LLMs and humans to inspect globally.

To resolve this, use the Pillow-based image crop tool to extract and save readable regions of interest.

### Using the Crop Tool
Run the crop utility from the command line:
```bash
python3 .agents/scripts/crop_image.py --input <path_to_large_png> --coords <left> <top> <right> <bottom> --output /tmp/crop.png [--resize <width> <height>]
```

- **Coordinates**: Left, Top, Right, Bottom pixels representing the bounding box.
- **Resize**: Optional parameters (e.g. `--resize 2025 1350`) to scale the cropped region for visual models to inspect.

---

## 8. CES Operations: edit → sync → deploy → test → capture

Five skills under `.agents/skills/gemini/` operate a live CES app reproducibly.
They share one client (`.agents/scripts/ces_client.py`) and read connection
details from `.env` — run `./setup.sh --verify` before using them.

| Skill | What it does |
|---|---|
| `ces-api` | REST CRUD over agents/tools/toolsets/etc.; one-turn `sessions run` smoke test; full-app `inventory.py`. The foundation the others import. |
| `ces-sync` | Push local source (instructions, toolsets, standalone tools, childAgents, callbacks, app config) into the **draft**. |
| `ces-deploy` | Cut an immutable **version** from the draft, repoint the deployment(s), roll back, and `export.py` the live state to a diffable tree. |
| `ces-eval` | Text/routing regression packs over `runSession` — assert route, tools, keywords, params, latency. |
| `ces-voice-test` | Voice packs over WebSocket BidiRunSession — real STT, agent audio, applied callbacks. |

### The loop

```bash
S=.agents/skills/gemini
# 1. edit local source (agents/<slug>/instruction.md + agent.json, callbacks/*.py, toolsets/*.yaml)
SYNC_ONLY=<slug> python $S/ces-sync/scripts/sync.py --src ./my-app          # 2. push to DRAFT (scoped)
python $S/ces-api/scripts/ces.py sessions run --input "..."                 # 3. smoke the draft
python $S/ces-eval/scripts/run_eval.py --test-file routing.json             # 3. routing regression (draft + fakes)
python $S/ces-deploy/scripts/deploy.py --label "<change>" --deployment test # 4. cut a version, repoint a TEST deployment
python $S/ces-voice-test/scripts/run_voice.py --test-file voice.json        # 5. voice/callback behavior on the deployment
python $S/ces-deploy/scripts/export.py && git add env-snapshot && git commit # 6. capture the receipt
```

### Non-negotiables

- **Draft ≠ deployment.** A sync only updates the draft. **Callback return values
  and the real telephony path only apply on a deployment** — validate those with
  `ces-voice-test`/`--deployed`, never against the draft.
- **Default to scoped sync** (`SYNC_ONLY=<slug>` / `--only`). A bare full sync
  patches every managed resource and will clobber a teammate's in-flight console
  draft. Always pull/export the draft and run a diff before syncing.
- **Claim a shared deployment before iterating**, and **always record the rollback version** that
  `deploy.py` prints. 
  1. Record the current live version number of the target deployment.
  2. Run `export.py` to snapshot the running config to the tracked `env-snapshot/` directory.
  3. If testing (e.g. `ces-voice-test` or `ces-eval`) fails on the newly deployed version, immediately roll back the deployment to the last known-good Version ID using `deploy.py --version <previous_version_id> --deployment <deployment_name>`.
- **Capture after deploying.** `export.py` + commit is the record of what is live.
- **Voice callbacks read `.transcript`, not just `.text`.** On a phone call the
  caller's words arrive in a part's `.transcript`; a callback that only reads
  `.text` is blind to spoken input. Test by voice, not just text, to catch it.
- **OS-specific TTS locking & Gemini Audio (Mac vs API costs)**: To minimize Google Cloud API costs, voice testing (`ces-voice-test`) should use local synthesis or native multimodal audio output:
  - **macOS users**: Must lock `CES_VOICE_TTS=say` in `.env` to use the built-in macOS speech synthesizer.
  - **Windows/Linux/Other users**: Use `CES_VOICE_TTS=gemini-audio` to leverage Vertex AI Gemini's native multimodal audio output (which is billed per token and is significantly cheaper than the premium Google Cloud TTS API Chirp/Studio voice rates).

- **Jira & PractiTest Integrations**:
  - Use the `/jira` and `/jira-stories` skills to manage tickets and generate story breakdowns from design files.
  - Use the `/practitest` skill and `.agents/scripts/practitest_client.py` to list/search tests or push results. Ensure `PRACTITEST_PROJECT_ID`, `PRACTITEST_FILTER_ID`, and basic auth parameters are correctly populated in `.env` (avoid hardcoding values in code).

---

## 9. Governance Log (`agent.changes.log`)
Every side-effecting change (files, resources, tool runs) must be appended to `agent.changes.log` at the project root. This log is **append-only**; never edit, delete, or truncate existing entries.
- **Initialization**: Create the log as your first action if it does not exist.
- **Entry Format**: `YYYY-MM-DD HH:MM:SS GMT | <author> | <action> | <path/scope> | <summary>`
  - Indent detail blocks (2 spaces) for: failures, retries, multi-file changes, `GRANT`/`REVOKE` context, or non-routine `RUN` outcomes.
- **Author**: `<agent>:<version>` (e.g., `antigravity:gemini-3.5-flash`) or human username.
- **Actions**: `CREATE`, `EDIT`, `DELETE`, `MOVE`, `RENAME`, `RESTORE`, `GRANT`, `REVOKE`, `RUN`.
- **Scope**: Log all state-changing actions (file edits, tool side-effects). **Do NOT** log every conversation turn, reading, or scratch work. Skip failures that leave no trace.
