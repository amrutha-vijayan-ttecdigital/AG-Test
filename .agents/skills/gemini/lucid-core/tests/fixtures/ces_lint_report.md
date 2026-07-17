# CES Design Audit & Linter Report

Found 12 diagnostic messages.

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