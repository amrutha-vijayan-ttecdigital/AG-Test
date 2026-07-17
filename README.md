# Google Cloud CX Agent Studio: Greenfield Starter Kit

Welcome to the **Greenfield CX Agent Studio Starter Kit**. This repository is designed as a platform-neutral, clean starting point for building conversational agents on Google Cloud's Customer Experience (CX) Agent Studio (built on the Agent Development Kit runtime model).

This kit provides the core architectural guidelines, developer references, and code/configuration templates to jumpstart your implementation without any legacy Dialogflow CX topology or client-specific business logic.

---

## Directory Structure

```text
├── README.md                           # This onboarding guide
├── AGENTS.md                           # Root rules entrypoint for coding agents
├── .env.example                        # Template for connection details
├── setup.sh                            # Interactive setup and onboarding script
├── .agents/                            # Workspace rules and sharing folder
│   ├── AGENTS.md                       # Project-scoped agent rules and guidelines
│   └── skills/gemini/                  # Live CES operations (sync, deploy, eval, voice test) and Lucid automation
├── docs/
│   ├── designs/                        # Core design specs, Lucid exports, compiled IRs
│   │   └── supplemental/              # Business rules, edge case docs, reference material
│   ├── diagrams/                       # Mermaid .mmd files, architecture diagrams
│   ├── qa/                             # QA checklists, handoff docs, test scripts
│   ├── reports/                        # Generated reports (latency, status, governance)
│   ├── testdata/                       # Test fixtures, golden data, test scenarios
│   ├── ces-agent-studio-deep-dive.md   # Advanced technical reference on callbacks, variables, and sandbox limits
│   ├── ces-official-docs-research.md   # Synthesized findings on ADK runtime, steering patterns, and MCP tools
│   └── escalation-handoff-reference.md # Reference for call escalation & handoffs using Google Telephony Platform, WxCC, and Avaya
├── templates/
│   ├── callbacks.py                    # Python skeleton showing all 6 primary callback hook signatures
│   ├── openapi_tool_template.json      # OpenAPI 3.0 tool definition template with session-context injection
│   └── system_instructions_template.xml # Structured XML prompt template for steering/routing agents
├── exports/                            # Version exports, draft snapshots, pre-change rollback snapshots
└── testcases/                          # Test case definitions and execution results
```

---

## Core Architecture Primitives

When building on CX Agent Studio, align your implementation with the following design guidelines:

1. **ADK-Based Architecture (Not Playbooks)**:
   CX Agent Studio does not use Dialogflow CX pages, transition routes, or flow topology as implementation primitives. Instead, it runs on the **Agent Development Kit (ADK)** model, driven by system instructions, custom Python callbacks, and declared tools.

2. **Orchestration Pattern**:
   Use a **steering agent** (root agent) that acts as the entry point and router, delegating specific intents or tasks to specialized child sub-agents (`{@AGENT: Sub Agent Name}`).

3. **XML-Structured Instructions**:
   Prompts are highly effective when structured using clean XML tags:
   - `<role>`: Establishes persona and tone.
   - `<taskflow>`: Specifies step-by-step logic.
   - `<subtask>`: Handles modular pieces of user interaction.

4. **Chips & References**:
   Interact with resources using platform reference chips inside instructions:
   - `{@AGENT: Agent Name}`: Transfers execution to a child sub-agent.
   - `{@TOOL: tool_name}`: Invokes a tool (API action, webhook, or system tool).
   - `{variable_name}`: Dynamically references a session variable.

---

## Quick Start: Using the Templates

### 0. Onboarding & Setup
Run the onboarding script to configure your local workspace details and verify
Google Cloud access:
```bash
./setup.sh
```
The script writes a gitignored `.env`, then blocks until `gcloud`, the active
account, Application Default Credentials, and project access are usable. Re-run
verification at any time:
```bash
./setup.sh --verify
```

Optional Lucid and Jira credentials can be entered during setup or added later
to `.env`. Lucid/Jira-dependent skills will fail until those values are present.

### 1. Register Callback Hooks
Copy `templates/callbacks.py` into your serverless execution environment (e.g., Cloud Functions or Cloud Run) or paste the handlers directly into the CX Agent Studio code editor. These callbacks allow you to intercept messages, sanitize PII, validate models, and structure outputs.

### 2. Configure REST Integration
Customize `templates/openapi_tool_template.json` to define integration endpoints. The schema includes the header injection block to pass context dynamically via `x-ces-session-context`.

### 3. Write System Instructions
Use the structure in `templates/system_instructions_template.xml` to compose your agent's system prompt in the CX Agent Studio console.

---

## Platform Quotas and Constraints

Keep these platform boundaries in mind during design:
- **Execution Timeout**: Callback functions must complete within **10 seconds** to prevent speech barge-in issues (platform sandbox hard timeout is 300s).
- **Payload Limit**: Files and JSON payloads are capped at **100MB**.
- **Variables**: Session state variables are limited to **100** per App.
- **Model Prompts**: Keep prompt caching active by using dynamic variable references (`{dynamic_var}`) instead of static variables (`{{static_var}}`) in instructions wherever possible.

---

## Documentation and Support
- See [docs/ces-agent-studio-deep-dive.md](docs/ces-agent-studio-deep-dive.md) for callback parameters, sandbox limits, and live agent handoff.
- See [docs/ces-official-docs-research.md](docs/ces-official-docs-research.md) for Developer Knowledge MCP queries and official Google GitHub repositories.
- See [docs/escalation-handoff-reference.md](docs/escalation-handoff-reference.md) for configuration parameters, architectures, and templates for GTP, Cisco WxCC, and Avaya DFCX Flow escalation.

---

## Lucidchart Integration & Design Auditing

This starter kit includes a suite of automated agent skills (under `.agents/skills/gemini/`) to pull, parse, convert, and audit visual Lucidchart/Lucidspark flowcharts against your live CX Agent Studio configurations (System Instructions, OpenAPI tools, callbacks, and sub-agents).

### Core Workflow

All visual audit and representation tools consume a shared canonical **Graph Intermediate Representation (IR)** compiled from the Lucid API to guarantee consistency:

1. **Compile a Lucid Chart**:
   Fetch a live snapshot of a Lucid document and write the canonical graph IR:
   ```bash
   python3 .agents/skills/gemini/lucid-compile-graph/scripts/lucid_compile_graph.py <lucid-url-or-id> --out-dir docs/designs/lucid-compiled --save-raw
   ```
2. **Convert to Mermaid Flowcharts**:
   Project the IR into Mermaid `.mmd` flowcharts for local documentation:
   ```bash
   python3 .agents/skills/gemini/lucid-to-mermaid/scripts/lucid_to_mermaid.py <lucid-url-or-id> --out-dir docs/diagrams
   ```
3. **Generate Markdown Specifications**:
   Produce a comprehensive text-based design spec detailing shapes, text, and connections:
   ```bash
   python3 .agents/skills/gemini/lucid-read-design/scripts/lucid_read_design.py <lucid-url-or-id> --out-dir docs/designs
   ```
4. **Audit Deployed CES Logic**:
   - Reconcile Lucid shapes against CES playbooks and tools using `lucid-design-audit` (mapping Process boxes to System Instructions, Diamonds to conditional routing rules, Cylinders to OpenAPI Tools, and Terminators to sub-agent delegation or `end_session` handoffs).
   - Trace flow visual context and verify layout constraints using `visual-design-audit` (which enforces the System Instructions Consolidation Rule to avoid unnecessary sub-agents).

### CES Nondeterministic Agent Design Pipeline

For Google Customer Experience Agent Studio (CX Agent Studio) model-driven, nondeterministic agents, use the new dedicated compiler-style design pipeline:

1. **Compile Design to CES IR**:
   Compile a Lucid JSON document to the versioned `ces-design-ir/v1` representation:
   ```bash
   python3 .agents/skills/gemini/lucid-to-ces-ir/scripts/lucid_to_ces_ir.py \
     --input-json docs/designs/lucid_raw.json \
     --output docs/designs/ces/ces_ir.json
   ```

2. **Lint and Report Ambiguities**:
   Validate the design against 38 semantic validation rules (e.g. missing root agent, confirmation requirements, variables declarations, loops exit):
   ```bash
   python3 .agents/skills/gemini/lucid-ces-design-audit/scripts/lucid_ces_design_audit.py \
     --ir docs/designs/ces/ces_ir.json \
     --report docs/designs/ces/ces_lint.md \
     --fail-on error
   ```

3. **Compare Design to Offline Runtime Snapshot**:
   Diff the design IR with a saved CES app export or API snapshot:
   ```bash
   python3 .agents/skills/gemini/lucid-ces-design-audit/scripts/lucid_ces_design_audit.py \
     --ir docs/designs/ces/ces_ir.json \
     --ces-export fixtures/ces_app_export.json \
     --runtime-diff docs/designs/ces/runtime_diff.md
   ```

4. **Generate Markdown Specifications**:
   Produce a detailed specification report:
   ```bash
   python3 .agents/skills/gemini/lucid-read-ces-design/scripts/lucid_read_ces_design.py \
     --ir docs/designs/ces/ces_ir.json \
     --output docs/designs/ces/design.md
   ```

5. **Generate Task-Specific Context Packets**:
   Generate a focused packet for coding agents to execute changes without context window bloat:
   ```bash
   python3 .agents/skills/gemini/lucid-ces-context/scripts/lucid_ces_context.py \
     --ir docs/designs/ces/ces_ir.json \
     --agent agent.billing \
     --task "Implement confirmation before payment update" \
     --output docs/designs/ces/context/payment-update.md
   ```

---

## CES Operations: Sync, Deploy & Test

This starter kit includes a suite of operations tools under `.agents/skills/gemini/` to manage a live CES app safely and reproducibly:

*   **`ces-sync`**: Syncs local configurations into the live Draft (use `SYNC_ONLY` to avoid clobbering).
*   **`ces-deploy`**: Cuts version snapshots and moves deployment pointers (with rollback support).
*   **`ces-eval`**: Runs JSON multi-turn text/routing test cases against the draft or deployment.
*   **`ces-voice-test`**: Runs streaming voice/audio tests over a WebSocket connection.

See the project-level [AGENTS.md](file:///.agents/AGENTS.md) for detailed workflow instructions and example commands.

---

## Jira & PractiTest Integration

This starter kit includes automated agent skills (under `.agents/skills/gemini/`) for Jira issue tracking and PractiTest test run management:

1. **Jira Issue Management (`jira` skill)**:
   Query, comment on, assign, transition, and reconcile Jira tickets using the Jira REST API.
   - Run via: `/jira`

2. **Generate Jira Stories (`jira-stories` skill)**:
   Automatically parse design specifications (`agent_design.md`) and generate a structured set of Jira stories under an Epic.
   - Run via: `/jira-stories`

3. **PractiTest Test Run Management (`practitest` skill)**:
   Query and update PractiTest test cases, runs, and instances to sync automated test results to the cloud.
   - CLI Tool: `python3 .agents/scripts/practitest_client.py <command>`
   - Run via: `/practitest`

