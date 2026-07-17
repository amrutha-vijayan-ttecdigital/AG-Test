# CX Agent Studio Escalation and Handoff Reference

This document outlines the configurations, architectural patterns, and guidelines for call escalation and handoff in Google Cloud CX Agent Studio. 

---

## 1. Handoff & Escalation Types

Conversational agents deployed on CX Agent Studio generally utilize one of two primary handoff types:

### A. GTP (Google Telephony Provider) Native Path
* **Description**: Direct telephony integration using CX Agent Studio's native Google Telephony Provider gateway.
* **Mechanism**: Handled via the built-in `end_session` system tool, with routing parameters passed directly in the prompt instructions or injected dynamically.
* **Parameters**:
  - `ESCALATION_MESSAGE` (String): The text the agent says before escalating.
  - `PHONE_GATEWAY_TRANSFER` (Object): Contains `phone_number` and optional `use_originating_trunk` (boolean).
  - `LIVE_AGENT_HANDOFF` (Object): Contains `sip-refer` (boolean) and optional `uui-headers` (list of strings).

---

### B. Dialogflow CX (DFCX) Flow Sub-agent Path
* **Description**: Integration model used in hybrid deployments (such as **MGM Resorts / Avaya** and **C Spire / Cisco WxCC**). 
* **Mechanism**: Rather than executing a native `end_session` telephony transfer from the generative agent, CX Agent Studio delegates the escalation to a **Dialogflow CX Flow child agent** (e.g., `{@AGENT: Send to Avaya}` or `{@AGENT: Send to WxCC}`).
* **Why it is used**: Allows reusing legacy Dialogflow CX page-based routing logic, custom payloads, UJet/Avaya webhooks, or existing CCaaS integration flows without rewriting the telephony deflection and screen-pop infrastructure in Agent Studio.
* **Best Practice**: Treat the DFCX Flow sub-agent as a black box. Pass parameters explicitly into the flow on entry, and extract parameters explicitly on flow exit.

---

## 2. Platform-Specific Escalation Architectures

When building for contact center integrations (CCaaS), follow the specific contracts below:

### Cisco WxCC V2 (DFCX Flow / Native Integration)
* **Contract**: Cisco WxCC Virtual Agent V2 expects a specific nested JSON payload (`Execute_Request`) to trigger the screen-pop desktop and route to the correct queue.
* **telephony handoff**: Uses `sip-refer` or SIP Refer with `endSession: false` in `LIVE_AGENT_HANDOFF` to delegate control to the WxCC gateway.
* **Payload Structure**:
  ```json
  "LIVE_AGENT_HANDOFF": {
    "endSession": false,
    "sip-refer": true,
    "custom_metadata": {
      "Execute_Request": {
        "Data": {
          "Params": {
            "IVA_Customer_Account_Type": "{account_type}",
            "IVA_Customer_Name": "{first_name}",
            "IVA_Customer_Transfer_Type": "{transfer_reason}",
            "IVA_Customer_Phone": "{phone_number}",
            "IVA_Customer_Account": "{account_number}",
            "IVA_Customer_Email": "{customer_email}"
          }
        }
      }
    }
  }
  ```

---

### Avaya / UJet Handoff (MGM Resorts Project)
* **Contract**: MGM Resorts utilizes a hybrid DFCX Flow connection. The agent calls a custom `avaya-transfer` OpenAPI tool or webhook to generate a `transferKey` (ANI-based 11-digit lookup key) and write session state to Firestore. The call is then routed to a DFCX "Send to Avaya" flow which triggers the SIP REFER with the `UUI` header set to the `transferKey`.
* **telephony handoff**: Uses the parameters:
  ```json
  "PHONE_GATEWAY_TRANSFER": {
    "phone_number": "{transferDestination}"
  },
  "LIVE_AGENT_HANDOFF": {
    "sip-refer": true
  }
  ```

---

## 3. Why Custom Callbacks are Required in Production Handoffs

While it is theoretically possible to instruct an LLM to generate parameters for the `end_session` tool directly inside system instructions (e.g., using variable templates), **relying on the LLM to write complex telephony transfer parameters is a high risk and not recommended for production deployments.**

Enterprise integrations (like Cisco WxCC and MGM/Avaya) require custom Python callbacks for the following reasons:

### 1. Model JSON Instability & Gateway Rigidness
Telephony gateways (such as Avaya and WxCC V2) are extremely rigid about the exact schema of transfer parameters (like `PHONE_GATEWAY_TRANSFER` and `LIVE_AGENT_HANDOFF`). If the LLM generates a tool call with minor JSON syntax errors, missing keys, or incorrect casing (e.g., camelCase instead of snake_case), the telephony gateway will fail to transfer, resulting in dropped calls or `Deflection (no_deflection)` errors.

### 2. Programmatic Variable Binding
A custom Python callback (specifically `before_tool_callback` on the `end_session` tool) programmatically intercepts the handoff intent. It reads verified variables directly from the session context (e.g., `callback_context.variables.get("transferDestination")`) and formats them cleanly (e.g., stripping spaces or formatting to E.164) before constructing the payload. This removes the dependency on the LLM's capability to format and write the digits.

### 3. Session Bookkeeping and State Cleaning
Telephony handoffs often require database state updates immediately before the call is transferred (such as writing a `transferKey` to Firestore for desktop screen-pops or clearing cardholder data from memory). Doing this inside a callback ensures these steps execute deterministically, whereas an LLM might skip them or execute them out of order.

---


## 4. Instruction Templates (Prompting)

### 1. Route to a DFCX Flow Sub-agent (WxCC & Avaya)
When using the DFCX Flow integration pattern, instruct the steering agent to route execution to the child agent representing the flow:
```text
If the user wants to speak to a Billing agent, hand off the session to the WxCC Billing flow: {@AGENT: Send to WxCC Billing}.

If the user wants to speak to a Front Desk representative, hand off the session to the Avaya operator flow: {@AGENT: Send to Avaya Operator}.
```

### 2. Route via Native GTP PSTN
```text
If the user wants to speak to an agent, escalate the call to the agent by executing the end_session tool with session_escalated=true and params={"ESCALATION_MESSAGE": "Transferring call via PSTN", "PHONE_GATEWAY_TRANSFER": {"phone_number": "+19496855555"}}.
```

### 3. Route via Native GTP SIP Trunk
```text
If the user wants to speak to an agent over a SIP TRUNK, escalate the call to the agent by executing the end_session tool with session_escalated=true and params={"ESCALATION_MESSAGE": "Transferring call via SIP TRUNK", "PHONE_GATEWAY_TRANSFER": {"phone_number": "+19496855555", "use_originating_trunk": true}}.
```
