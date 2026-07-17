"""before_model callback: stamp the current date into session state.

Parameter names MUST match the ADK spec exactly (callback_context, llm_request) or
the platform raises TypeError via its keyword-argument passing. Outbound network
calls from callbacks must use the ces_requests wrapper, not raw sockets.
"""

from datetime import date


def before_model_callback(callback_context, llm_request):
    # Only set it once per session.
    if not callback_context.state.get("currentDate"):
        callback_context.state["currentDate"] = date.today().isoformat()
    # Return None to let the model response proceed unmodified.
    return None
