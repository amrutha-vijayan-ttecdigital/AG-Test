# CES Agent Studio Design Specification Report
*(Version: ces-design-ir/v1 | Document Title: CES Test Document)*

## 1. Application Overview
- **Application ID:** doc_ces_test
- **Display Name:** CES Test Document
- **Root Agent ID:** agent_root
- **Language/Locale:** Not specified
- **Tool Execution Mode:** unspecified

## 2. Agent Hierarchy and Delegation
This section lists all LLM agents and human escalation targets designed in this application.

- **agent_root** (Root Agent) - *llm_agent*
  - **agent_billing** (Billing Agent) - *llm_agent*

## 3. Per-Agent Purpose and Scope
### Agent: agent_root (Root Agent)
- **Purpose:** Not specified

### Agent: agent_billing (Billing Agent)
- **Purpose:** Not specified

## 4. Behavioral Contracts & Rules
The table below documents explicit behavioral claims and constraints derived from the design graph.

| Subject ID | Modality | Behavioral Contract (Predicate) | Enforced By | Authority |
|---|---|---|---|---|
| agent_billing -> tool_payment_update | **Modality.MUST** | calls tool | line_calls_write | ControlAuthority.DETERMINISTIC_HANDOFF_RULE |
| agent_root -> tool_payment_update | **Modality.MUST_NOT** | call update_payment before confirmation | line_forbidden | ControlAuthority.UNKNOWN |

## 5. Handoffs and Agents-as-Tools
Conversational flows partition conversation ownership transfers (Handoffs) from auxiliary capabilities (Agents-as-Tools).

### Handoffs (Conversation Ownership Transfers)
- **agent_root** hands off to **agent_billing** via *model_instruction*.
  - *Condition:* hand off when billing goal; returns when resolved
  - *Return Condition:* resolved
- **agent_root** hands off to **agent_billing** via *model_instruction*.
  - *Condition:* simulator trace

### Agents-as-Tools (Auxiliary Capabilities)
- No agent-as-tool relationships designed.

## 6. Tools and Side-Effect Controls
### Tool: tool_lookup ()
- **Kind:** openapi
- **Execution Type:** unknown
- **Confirmation Required:** False
- **Description:** No description

### Tool: tool_payment_update ()
- **Kind:** openapi
- **Execution Type:** unknown
- **Confirmation Required:** True
- **Description:** No description


## 7. Callbacks and Guardrails
### Callbacks
- **callback_auth** (CallbackStage.BEFORE_TOOL): 

### Guardrails
- **guardrail_safety** ():  -> Outcome: GuardrailOutcome.BLOCK

## 8. Variables and Data Contracts
| Variable Name | Type | Classification | Owner Agent | Sensitivity |
|---|---|---|---|---|
| variable_token | string | dynamic | Global | Public |

## 9. Dialogflow CX Remote Agent Integration
### Remote Agent Reference: dfcx_agent
- **Target Resource:** 


## 10. Channel Behavior
- Channel profiles and interactive options are configured at the application level.

## 11. Evaluation Coverage
- No evaluation specifications designed.

## 12. Linter Diagnostics & Ambiguities
| Code | Severity | Message | Remediation |
|---|---|---|---|
| CES002 | warning | Agent 'agent_root' is missing purpose or scope goals. | Populate the agent shape text with 'Purpose:' and 'In Scope:' / 'Out of Scope:' lists. |
| CES002 | warning | Agent 'agent_billing' is missing purpose or scope goals. | Populate the agent shape text with 'Purpose:' and 'In Scope:' / 'Out of Scope:' lists. |
| CES003 | warning | Agent 'agent_billing' has no completion, return, or escalation behavior. | Specify 'Completion:', 'Handoff:', or 'Exit:' behavior on the agent shape text. |
| CES019 | warning | MUST/MUST_NOT claim on connector from 'agent_root' lacks deterministic enforcement. | Specify rule, callback, or guardrail authority (e.g. '[MUST][RULE]') to enforce the contract. |
| CES024 | warning | Observed trace connector from 'agent_root' to 'agent_billing' is represented as design guarantee. | Mark trace connectors explicitly as [OBSERVED] or move them to a separate page/layer. |
| CES007 | warning | Handoff from 'agent_root' to 'agent_billing' lacks return behavior. | Clarify return behavior in label (e.g., 'returns when resolved'). |
| CES011 | error | Tool 'tool_lookup' description is missing. | Provide a description within the tool shape text. |
| CES015 | warning | Tool 'tool_lookup' is missing timeout retry or error handling details. | Specify 'Timeout:' or 'Error Handling:' inside the tool shape text. |
| CES011 | error | Tool 'tool_payment_update' description is missing. | Provide a description within the tool shape text. |
| CES015 | warning | Tool 'tool_payment_update' is missing timeout retry or error handling details. | Specify 'Timeout:' or 'Error Handling:' inside the tool shape text. |
| CES022 | warning | Sensitive variable 'variable_token' lacks redaction or logging guidance. | Specify log redaction expectations for the sensitive variable. |
| CES023 | error | Remote DFCX flow agent 'dfcx_agent' lacks input/output mapping. | Define the inputs/outputs mapped to the black-box Dialogflow agent. |

## 13. Provenance Appendix
This appendix links semantic elements back to their source shapes/lines inside the Lucid chart document.

- **Agent 'agent_root':** Page ID: page_1, Shape IDs: agent_root
- **Agent 'agent_billing':** Page ID: page_1, Shape IDs: agent_billing
- **Tool 'tool_lookup':** Page ID: page_1, Shape IDs: tool_lookup
- **Tool 'tool_payment_update':** Page ID: page_1, Shape IDs: tool_payment_update
- **Relationship 'agent_root -> agent_billing':** Page ID: page_1, Line IDs: line_parent
- **Relationship 'agent_root -> agent_billing':** Page ID: page_1, Line IDs: line_handoff_billing
- **Relationship 'agent_billing -> tool_lookup':** Page ID: page_1, Line IDs: line_calls_lookup
- **Relationship 'agent_billing -> tool_payment_update':** Page ID: page_1, Line IDs: line_calls_write
- **Relationship 'agent_root -> tool_payment_update':** Page ID: page_1, Line IDs: line_forbidden
- **Relationship 'agent_root -> agent_billing':** Page ID: page_1, Line IDs: line_observed
