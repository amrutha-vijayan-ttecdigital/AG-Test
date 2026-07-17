# Task Context
**Requested Change:** Implement confirmation before payment update
**Target Agent:** agent_billing

## Explicit Guidelines & Invariants (Not Implied)
- A dashed connector indicates a `MAY` relationship (model-selected delegation), NOT a guaranteed `MUST` order.
- Active conversation ownership remains with the caller during an `AGENT_AS_TOOL` invocation.
- A Dialogflow CX (DFCX) remote agent must be treated as a black box; internal routes/pages are out of scope.
- Observed traces or simulator outputs show what happened in a single run, NOT a design contract constraint.
- Direct shape-to-shape lines or line-to-line connections represent explicit routing; never infer adjacency.

## Application Overview
- **Application ID:** doc_ces_test
- **Display Name:** CES Test Document
- **Root Agent:** agent_root

## Relevant Agent Specifications
### Agent: agent_billing (Billing Agent)
- **Purpose:** N/A
- **Kind:** llm_agent
- **Attached Tools:** None

### Agent: agent_root (Root Agent)
- **Purpose:** N/A
- **Kind:** llm_agent
- **Attached Tools:** None

## Relevant Tool Specifications
### Tool: tool_lookup ()
- **Kind:** openapi
- **Description:** 
- **Execution Type:** unknown
- **Confirmation Required:** False

### Tool: tool_payment_update ()
- **Kind:** openapi
- **Description:** 
- **Execution Type:** unknown
- **Confirmation Required:** True

## Handoff & Delegation Contracts
### Handoff: agent_root -> agent_billing
- **Mechanism:** model_instruction
- **Condition:** hand off when billing goal; returns when resolved
- **Return Condition:** resolved

### Handoff: agent_root -> agent_billing
- **Mechanism:** model_instruction
- **Condition:** simulator trace

## Enforcement & Callbacks

## Unresolved Ambiguities & Warnings
- **[CES002]** (warning): Agent 'agent_root' is missing purpose or scope goals.
  *Remediation:* Populate the agent shape text with 'Purpose:' and 'In Scope:' / 'Out of Scope:' lists.
- **[CES002]** (warning): Agent 'agent_billing' is missing purpose or scope goals.
  *Remediation:* Populate the agent shape text with 'Purpose:' and 'In Scope:' / 'Out of Scope:' lists.
- **[CES003]** (warning): Agent 'agent_billing' has no completion, return, or escalation behavior.
  *Remediation:* Specify 'Completion:', 'Handoff:', or 'Exit:' behavior on the agent shape text.
- **[CES019]** (warning): MUST/MUST_NOT claim on connector from 'agent_root' lacks deterministic enforcement.
  *Remediation:* Specify rule, callback, or guardrail authority (e.g. '[MUST][RULE]') to enforce the contract.
- **[CES024]** (warning): Observed trace connector from 'agent_root' to 'agent_billing' is represented as design guarantee.
  *Remediation:* Mark trace connectors explicitly as [OBSERVED] or move them to a separate page/layer.
- **[CES007]** (warning): Handoff from 'agent_root' to 'agent_billing' lacks return behavior.
  *Remediation:* Clarify return behavior in label (e.g., 'returns when resolved').
