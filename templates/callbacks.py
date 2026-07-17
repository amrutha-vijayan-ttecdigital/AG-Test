"""
Google Cloud CX Agent Studio: Custom Callback Templates
This file contains canonical skeletons for all 6 primary callback hooks.
Use these to run custom reasoning, input validation, tool pre/post-processing,
and telephony handoffs.

CRITICAL GOTCHA:
Primary callback function parameters must match the specified names EXACTLY (e.g.
'callback_context', 'llm_request', etc.). Renaming them will result in TypeErrors at runtime.
"""

from typing import Any, Optional

# =====================================================================
# Typings / Stubs (For local IDE support)
# =====================================================================
class CallbackContext:
    """Pre-injected context containing session variables."""
    variables: dict[str, Any]
    state: dict[str, Any]

class Content:
    """Represents a conversational message containing parts (text, json, functions)."""
    @classmethod
    def from_text(cls, text: str) -> "Content": ...
    @classmethod
    def from_parts(cls, parts: list[Any]) -> "Content": ...

class Part:
    """Represents a piece of a content payload."""
    @classmethod
    def from_text(cls, text: str) -> "Part": ...
    @classmethod
    def from_json(cls, data: str) -> "Part": ...
    @classmethod
    def from_function_call(cls, name: str, args: dict[str, Any]) -> "Part": ...

class LlmRequest:
    """Raw request to the Gemini model."""
    prompt: str
    temperature: float

class LlmResponse:
    """Raw response returned from the Gemini model."""
    content: Content
    @classmethod
    def from_parts(cls, parts: list[Any]) -> "LlmResponse": ...

class Tool:
    """Definition of the current tool being executed."""
    name: str
    description: str

# Pre-injected environment tools (Available in runtime without imports):
# - ces_requests: Sandbox safe HTTP library (e.g., ces_requests.get(url))
# - tools: Sync tool executor (e.g., tools.my_tool(args))
# - async_tools: Async tool executor (e.g., async_tools.my_tool(args))
# - get_variable(key, default)
# - set_variable(key, value)
# - remove_variable(key)


# =====================================================================
# Callback Lifecycle Hooks
# =====================================================================

def before_agent_callback(callback_context: CallbackContext) -> Optional[Content]:
    """
    Fires before the agent is invoked.
    
    Return:
        None: Continue normal execution.
        Content: Skip agent reasoning and return this content immediately.
    """
    # Example: Check if session is already flagged for termination
    if callback_context.variables.get("force_escalation") is True:
        # Construct and return an immediate handoff command
        handoff_part = Part.from_function_call(
            name="end_session",
            args={
                "reason": "force_escalation",
                "session_escalated": True,
                "params": {
                    "ESCALATION_MESSAGE": "We are transferring you immediately.",
                    "PHONE_GATEWAY_TRANSFER": {
                        "phone_number": "+18005550199"
                    }
                }
            }
        )
        return Content.from_parts([handoff_part])
        
    return None


def after_agent_callback(callback_context: CallbackContext) -> Optional[Content]:
    """
    Fires after the agent completes reasoning but before response is sent.
    
    Return:
        None: Keep agent's generated response as-is.
        Content: Overwrite the agent's response entirely.
    """
    # Example: Append a system disclaimer variable if set
    disclaimer = callback_context.variables.get("dynamic_disclaimer")
    if disclaimer:
        # Get existing conversation parts or construct a new content object
        # ...
        pass
    return None


def before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    """
    Fires immediately before the prompt is sent to the LLM (Gemini).
    
    Return:
        None: Proceed with LLM call.
        LlmResponse: Skip LLM call and return this response (mocking).
    """
    # Example: Detect escalation intent without sending to LLM
    # if has_escalate_intent(llm_request):
    #     handoff_part = Part.from_function_call(
    #         name="end_session",
    #         args={
    #             "reason": "user_requested_escalation",
    #             "session_escalated": True,
    #             "params": {
    #                 "ESCALATION_MESSAGE": "Sure, let me connect you to an agent.",
    #                 "PHONE_GATEWAY_TRANSFER": {
    #                     "phone_number": "+19496855555"
    #                 },
    #                 "LIVE_AGENT_HANDOFF": {
    #                     "sip-refer": True
    #                 }
    #             }
    #         }
    #     )
    #     return LlmResponse.from_parts([handoff_part])
    return None


def after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
    """
    Fires after LLM returns a response but before the agent processes it.
    Useful for redacting PII, checking safety guardrails, or injecting custom payloads.
    
    Return:
        None: Proceed with LLM response as-is.
        LlmResponse: Replace the model response.
    """
    # Example: Inject a custom chat-messenger widget payload if the agent mentions "tracker"
    # import json
    # text_part = llm_response.content.parts[0].text
    # if text_part and "tracker" in text_part.lower():
    #     payload = {
    #         "display_widget": "order_tracker",
    #         "data": {"order_id": callback_context.variables.get("order_id")}
    #     }
    #     new_parts = [
    #         Part.from_text(text_part),
    #         Part.from_json(json.dumps(payload))
    #     ]
    #     return LlmResponse.from_parts(new_parts)
    return None


def before_tool_callback(tool: Tool, input: dict[str, Any], callback_context: CallbackContext) -> Optional[dict[str, Any]]:
    """
    Fires before a tool (action/webhook) executes.
    
    Return:
        None: Execute the tool normally.
        dict: Skip tool execution and return this dictionary as the mock tool result.
    """
    # Example: Inject a mocked API payload during testing or local development
    # if tool.name == "fetch_account_balance" and callback_context.variables.get("test_mode") == "mock":
    #     return {"status": "success", "balance": 150.00, "due_date": "2026-07-01"}
    return None


def after_tool_callback(tool: Tool, input: dict[str, Any], callback_context: CallbackContext, tool_response: dict) -> Optional[dict]:
    """
    Fires after a tool completes execution.
    Useful for formatting raw API JSON, filtering sensitive data, or setting session variables.
    
    Return:
        None: Proceed with original tool response.
        dict: Replace the tool response sent to the LLM.
    """
    # Example: Store retrieved data in session context variables for prompt reference
    if tool.name == "get_customer_profile" and tool_response.get("status") == "success":
        data = tool_response.get("data", {})
        # Save to context variables
        callback_context.variables["customer_name"] = data.get("first_name", "Valued Customer")
        callback_context.variables["account_status"] = data.get("status", "Active")
        
    return None
