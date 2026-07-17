# Google Cloud CX Agent Studio (CES): Advanced Technical Reference

This document serves as the canonical technical reference for building conversational designs in Customer Experience (CX) Agent Studio (formerly Conversational Agents). It outlines the runtime architecture, custom code callback interfaces, execution constraints, and integration boundaries.

---

## 1. Custom Callback Architecture
Callbacks in CX Agent Studio allow you to execute custom Python code at specific stages of a conversational turn. They are built on Google’s **Agent Development Kit (ADK)** runtime.

### Exact Parameter Naming Gotcha
> [!IMPORTANT]
> Because the ADK framework passes callback arguments by keyword, your primary callback function parameters **must match the documented names exactly**. Renaming parameters to common developer aliases (like `ctx` instead of `callback_context`) will cause a runtime `TypeError` and crash the conversation.

### Callback Lifecycle & Signatures

#### A. Before Agent Starts
* **Function Name**: `before_agent_callback`
* **Signature**: 
  ```python
  def before_agent_callback(callback_context: CallbackContext) -> Optional[Content]:
  ```
* **Execution**: Fires before the agent is invoked.
* **Return Behavior**:
  * `None`: Continue normal agent execution.
  * `Content` object: Intercepts execution. The agent's LLM call is **skipped**, and the returned `Content` is used immediately as the final agent output for the turn.

#### B. After Agent Finishes
* **Function Name**: `after_agent_callback`
* **Signature**:
  ```python
  def after_agent_callback(callback_context: CallbackContext) -> Optional[Content]:
  ```
* **Execution**: Fires after the agent completes reasoning.
* **Return Behavior**:
  * `None`: Keep the agent's generated response as-is.
  * `Content` object: Replaces the agent's output.

#### C. Before LLM Call
* **Function Name**: `before_model_callback`
* **Signature**:
  ```python
  def before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
  ```
* **Execution**: Fires immediately before a request is sent to the Gemini model.
* **Return Behavior**:
  * `None`: Proceed with the LLM call.
  * `LlmResponse` object: Skips the LLM call entirely. The framework uses the provided `LlmResponse` as if it came from the model. (Used for prompt validation, input caching, or guardrails).

#### D. After LLM Call
* **Function Name**: `after_model_callback`
* **Signature**:
  ```python
  def after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
  ```
* **Execution**: Fires after a response is returned from the LLM but before the agent processes it.
* **Return Behavior**:
  * `None`: Proceed with the LLM's response.
  * `LlmResponse` object: Replaces the model's response (used for output sanitization, redacting PII, or injecting disclaimers).

#### E. Before Tool Call
* **Function Name**: `before_tool_callback`
* **Signature**:
  ```python
  def before_tool_callback(tool: Tool, input: dict[str, Any], callback_context: CallbackContext) -> Optional[dict[str, Any]]:
  ```
* **Execution**: Fires before a tool (action/webhook) is executed by the agent.
* **Return Behavior**:
  * `None`: Execute the tool normally.
  * `dict`: Skips tool execution and immediately returns the dictionary as the mock result of the tool call back to the LLM.

#### F. After Tool Call
* **Function Name**: `after_tool_callback`
* **Signature**:
  ```python
  def after_tool_callback(tool: Tool, input: dict[str, Any], callback_context: CallbackContext, tool_response: dict) -> Optional[dict]:
  ```
* **Execution**: Fires after a tool completes execution.
* **Return Behavior**:
  * `None`: Proceed with the original tool response.
  * `dict`: Replaces the tool response sent to the LLM (used for formatting or filtering API outputs).

---

## 2. Python Sandbox & Runtime Environment
Callbacks and custom code tools run in an isolated, secure sandbox.

### Global Variables & Helper Functions
The following variables and shortcuts are pre-injected into the Python environment:
* **`context`**: The ADK Context object. `context.variables` (or `context.state`) houses session variables. (Use of `context.variables` is preferred over `context.state` for new code).
* **`get_variable(key: str, default: Any = None) -> Any`**: Shortcut for `context.variables.get(key, default)`.
* **`set_variable(key: str, value: Any) -> None`**: Shortcut for `context.variables[key] = value`.
* **`remove_variable(key: str) -> None`**: Shortcut for `del context.variables[key]`.
* **`ces_requests`**: A wrapper around the standard `requests` library. **Note**: Raw network sockets are disabled in the sandbox; all outbound HTTP calls must go through the `ces_requests` object.
* **`tools`**: Synchronous tool executor (e.g., `response = tools.my_tool(args)`).
* **`async_tools`**: Asynchronous tool executor (e.g., `future = async_tools.my_tool(args)`).

### Runtime Constraints & Safety
* **No Raw System Calls**: Importing `os` or `subprocess` to run commands or interact with the underlying container will result in a deployment/execution failure.
* **Payload Limits**: Inbound and outbound files/payloads are capped at **100MB**.
* **Timeout Constraints**: Code execution times out after **300 seconds** for standard reasoning engines, though conversational turn callbacks are optimized for sub-second latency and should be kept under **10 seconds** to avoid speech barge-in/endpointing issues.

---

## 3. Dynamic vs. Static Variables

| Attribute | Static Variables (`{{my_var}}`) | Dynamic Variables (`{my_var}`) |
|---|---|---|
| **Compilation** | Compiled directly into the system prompt text prior to model call. | Appended dynamically to the conversation history. |
| **Syntax** | Referenced in instructions via double braces: `{{my_var}}`. | Referenced in instructions via single braces: `{my_var}`. |
| **Best For** | Rigid business rules, global configs, static URLs. | Session data (names, accounts, auth tokens) fetched via tools. |
| **Caching Impact** | **Yes**. Updating a static variable invalidates prompt caching, increasing latency/cost. | **No**. Prompt caching is preserved. |
| **History Risk** | **None**. Prompt context remains constant. | **Yes**. If conversation exceeds context limits, old variables in history are pruned. |

---

## 4. Custom Payloads & Client-Side Action
Custom payloads allow the agent to return non-textual, structured JSON to the client (such as UI widgets, carousels, or routing commands). The LLM is completely blind to these payloads.

### How to Inject a Custom Payload
You must use `before_model_callback` or `after_model_callback` to insert a JSON-based `Part` (mime-type: `application/json`) into the response:

```python
import json

def after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
    # Check if the model response has text
    if llm_response.content.parts[0].text is not None:
        # Define the custom payload dictionary
        payload = {
            "display_widget": "order_tracker",
            "data": {
                "order_id": callback_context.variables.get("order_id"),
                "status": "in_transit"
            }
        }
        
        # Build the new response payload parts
        new_parts = [
            Part.from_text(llm_response.content.parts[0].text),
            Part.from_json(data=json.dumps(payload))
        ]
        return LlmResponse.from_parts(parts=new_parts)
    return None
```

---

## 5. Live Agent Handoff & Escalation
Escalation and transfer in CX Agent Studio are managed via the built-in system tool `end_session`.

### Telephony Handoff
Telephony transfers (SIP INVITE or SIP REFER) are configured using the `PHONE_GATEWAY_TRANSFER` and `LIVE_AGENT_HANDOFF` parameters inside `end_session`.

Depending on your CCaaS gateway platform, you will structure the escalation payload in one of two ways:

#### A. WxCC Escalation Path (Cisco WxCC V2)
If your target contact center is Cisco WxCC V2, you must pass customer profile context parameters wrapped inside the `custom_metadata` object, and set `endSession` to `False` to prevent the gateway from dropping the call.

##### Python Callback Implementation Example:
```python
def before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    # Check if the model is trying to escalate
    if not has_escalate_intent(llm_request):
        return None

    # Construct the six-field Cisco WxCC V2 metadata payload
    transfer_payload = {
        "Execute_Request": {
            "Data": {
                "Params": {
                    "IVA_Customer_Account_Type": callback_context.variables.get("account_type", "unknown"),
                    "IVA_Customer_Name": callback_context.variables.get("first_name", "unknown"),
                    "IVA_Customer_Transfer_Type": callback_context.variables.get("transfer_reason", "general"),
                    "IVA_Customer_Phone": callback_context.variables.get("phone_number", "unknown"),
                    "IVA_Customer_Account": callback_context.variables.get("account_number", "unknown"),
                    "IVA_Customer_Email": callback_context.variables.get("customer_email", "unknown")
                }
            }
        }
    }

    # Intercept LLM and force the end_session tool execution
    handoff_part = Part.from_function_call(
        name="end_session",
        args={
            "reason": "human_escalation",
            "session_escalated": True,
            "params": {
                "ESCALATION_MESSAGE": "Please hold while I connect you to a representative.",
                "PHONE_GATEWAY_TRANSFER": {
                    "phone_number": "+18005550199",
                    "use_originating_trunk": True
                },
                "LIVE_AGENT_HANDOFF": {
                    "endSession": False,  # Keeps telephony gateway control active
                    "sip-refer": True,
                    "custom_metadata": transfer_payload 
                }
            }
        }
    )

    return LlmResponse.from_parts(parts=[handoff_part])
```

#### B. MGM CES Escalation Path (MGM Resorts / Avaya / UJet)
For integrations that rely on dynamic routing to destination numbers resolved during the call flow, use a custom callback on the `before_tool_callback` hook for the `end_session` tool. This callback intercepts the agent's transfer intent and dynamically maps the destination phone number from a session variable.

##### Python Callback Implementation Example:
```python
def before_tool_callback(tool: Tool, input: dict[str, Any], callback_context: CallbackContext) -> Optional[dict[str, Any]]:
    # Only intercept end_session tool calls
    if tool.name.replace("-", "_").lower() != "end_session":
        return None

    # Dynamically extract and normalize destination number resolved in the flow
    dest = callback_context.variables.get("transferDestination")
    phone_gateway_transfer = {}
    if dest:
        phone_gateway_transfer["phone_number"] = normalize_destination_digits(dest)

    # Re-structure the input parameters for the end_session tool call
    input["reason"] = str(input.get("reason") or "transfer")
    input["session_escalated"] = True
    input["params"] = {
        "PHONE_GATEWAY_TRANSFER": phone_gateway_transfer,
        "LIVE_AGENT_HANDOFF": {}  # Empty handoff payload
    }
    
    return None  # Continue normal execution with updated input parameters
```


---

## 6. System Limits & Quotas

### Static Structural Limits
* **Maximum Agents per App**: 100
* **Maximum Tools per App**: 200
* **Maximum Tools per Agent**: 100
* **Maximum Variables per App**: 100
* **Maximum Callbacks per Agent**: 50
* **Maximum App Versions**: 200

### API Rate Quotas (Default)
* **App Mutation Operations**: 200 requests / minute
* **App Read Operations**: 600 requests / minute
* **App Generative Operations**: 100 requests / minute
* **Tool Executions (`ExecuteTool`)**: 240 requests / minute
* **Session LLM Tokens**: 120,000 tokens / minute

---

## 7. Development Best Practices
1. **Flows as Black Boxes**: Dialogflow CX relies on global session parameter propagation, which causes drift. Treat Dialogflow CX Flows as black boxes in CX Agent Studio. Pass parameters explicitly on flow entry, and extract parameters explicitly on flow exit.
2. **No Reconnect**: Unlike Dialogflow CX, CX Agent Studio session contexts **cannot be resumed or reconnected** once `end_session` is called and executed. Ensure all post-call database writes or wrap-ups are chained *before* the final `end_session` call.
3. **Proactive Execution Warning**: In the callback configuration, `proactiveExecutionEnabled` should remain `False` for `after_model_callback` unless necessary. Turning it on runs the callback on intermediate LLM stream chunks, drastically increasing execution costs and latency.
4. **Chirp 3 HD Voice & SSML Limitation**: Chirp 3 HD voices are fully supported in CX Agent Studio. However, **SSML tags are not supported** for these models and must be removed from prompt text to prevent speech synthesis errors.

---

## 8. Rich Response Widgets & Web Messenger Integration
CX Agent Studio includes native support for deploying conversational agents via a built-in web messenger widget (`chat-messenger` web component).

### Widget Tools & Types
You can configure widget tools that output structured data schemas. When invoked, the agent generates a visual widget on the client side:
* `PRODUCT_CAROUSEL`: scrollable catalog of product cards.
* `PRODUCT_DETAILS`: detail page for a single item.
* `QUICK_ACTIONS`: customized quick-reply choices.
* `PRODUCT_COMPARISON`: side-by-side comparison tables.
* `ORDER_SUMMARY`: structured transactional checkout receipt.

### Using Widgets in Agent Instructions
Add the widget to the agent configuration and invoke it using the widget reference chip format:
* Reference: `{@Widget: widget_name}` or `{@TOOL: widget_name}`.
* *Example instruction*: `When the user asks to see options or a catalog, use the {@Widget: product_catalog_widget} to render the product options.`

### JavaScript Events & Methods
For custom website integrations, you can bind listeners directly to the `<chat-messenger>` HTML element:
* **Events**:
  * `chat-messenger-loaded`: triggered when the widget finishes initialization.
  * `chat-messenger-error`: returns details on backend API or connectivity errors.
  * `df-update-cart-count`: fires when the user triggers transactional selections inside product carousels/details.
* **Methods**:
  * `renderCustomText(text: str)`: programmatically injects a text message into the chat UI as if it came from the agent.
  * `renderCustomCard(payload: list)`: programmatically renders a structured custom card (uses standard Dialogflow Messenger rich payloads).

---

## 9. Official GitHub Repositories & Resources
To reference real-world implementations, deployment blueprints, or SDK source code, check the following official Google and GCP GitHub repositories:

* **[google/adk-python](https://github.com/google/adk-python)**: The core Python SDK repository for the Agent Development Kit. Houses the callback runner, context state tracker, and local execution frameworks.
* **[google/adk-samples](https://github.com/google/adk-samples)**: Official multi-agent design examples, including code execution tools and callback boilerplates.
* **[google/adk-docs](https://github.com/google/adk-docs)**: Master source documentation for building, evaluating, and testing ADK-based agents.
* **[GoogleCloudPlatform/cxas-scrapi](https://github.com/GoogleCloudPlatform/cxas-scrapi)**: Command-line interface and Python library for programmatically interacting with and refactoring Conversational Agents (CX Agent Studio).
* **[GoogleCloudPlatform/ces-messenger](https://github.com/GoogleCloudPlatform/ces-messenger)**: Setup files and examples for integrating the `chat-messenger` widget, including a Cloud Function Cloud Run boilerplate for Token Broker authentication.
