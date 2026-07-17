---
name: callback-planner
description: Generate production-ready Python callback code for Google Cloud CX Agent Studio agents using an interactive multi-agent design and verification loop. Trigger whenever the user wants to write, create, or validate callbacks (e.g. before_model_callback, after_tool_callback, custom payloads, and webhook routing).
---

# callback-planner

Generate production-ready Python callback code for CX Agent Studio agents using a lightweight multi-agent review loop and static verification checks.

## Workflow

When triggered, the parent agent **MUST** spin up a design-and-review loop using subagents:

### Step 1: Define Subagents
Define the following two subagents:

1. **`callback_designer`**:
   * **Role**: Generates the callback logic based on the user's requirements.
   * **Instruction**: Must strictly enforce parameter name gotchas (keyword matching), sandbox network constraints (must use `ces_requests` instead of `requests` or `urllib`), and include regex SSML tag-stripping helpers for voice synthesis safety.

2. **`callback_reviewer`**:
   * **Role**: Acts as a forensic auditor validating the generated callback against strict workspace guidelines.
   * **Instruction**: Audits the code and runs the verification tool `validate_callback.py` to ensure it passes all checks.

### Step 2: Orchestrated Loop
1. The `callback_designer` generates the first draft of the code.
2. The `callback_reviewer` checks the code and outputs feedback.
3. The `callback_designer` updates the code to resolve any warnings or failures.
4. Loop continues until the `callback_reviewer` yields a **`VERDICT: PASS`** report.

### Step 3: Run the Verification Script
Run the linter script locally to verify compliance before finalizing the code:

```bash
python3 .agents/skills/gemini/callback-planner/scripts/validate_callback.py <path-to-callback-file>
```

### Step 4: Simulate Callback Execution Locally
Run the callback simulator locally to verify that the code compiles, executes without exceptions, and modifies context state variables correctly:

```bash
python3 tools/ces_mock_runner.py <path-to-callback-file> --function <function_name> --variables '<initial-state-json>' --transcript '<user-utterance>'
```

---

## Static Lint Checks (`validate_callback.py`)

The script validates:
1. **Parameter signatures**: Must match exact platform spec names (e.g. `callback_context`, `llm_request`, `llm_response`, `tool`, `input`, `tool_response`).
2. **Sandbox sockets**: Flags warnings if standard `requests` or `urllib` is imported (requires `ces_requests`).
3. **Voice safety**: Warns if the callback uses user inputs without reading `.transcript`, or modifies output text without adding an SSML stripping regex pattern.
4. **Error safety**: Warns if operations aren't wrapped in `try/except` blocks.
