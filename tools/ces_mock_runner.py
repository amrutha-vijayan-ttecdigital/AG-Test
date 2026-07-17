#!/usr/bin/env python3
"""
ces_mock_runner.py — A local runtime simulator for Customer Experience Agent Studio (CES) custom Python callbacks.
Loads callback code, injects mock context classes, mocks the google.cloud.ces ADK module, and prints output/state changes.
"""

import argparse
import json
import sys
import types
import importlib.util
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

# =====================================================================
# 1. Define Canonical Mock ADK Classes
# =====================================================================

class MockPart:
    """Mock implementation of the ADK Part class."""
    def __init__(self, text: Optional[str] = None, json_data: Optional[str] = None, function_call: Optional[Dict[str, Any]] = None):
        self.text = text
        self.json_data = json_data
        self.function_call = function_call

    @classmethod
    def from_text(cls, text: str):
        return cls(text=text)

    @classmethod
    def from_json(cls, data: str):
        return cls(json_data=data)

    @classmethod
    def from_function_call(cls, name: str, args: Dict[str, Any]):
        return cls(function_call={"name": name, "args": args})

    def to_dict(self) -> Dict[str, Any]:
        res = {}
        if self.text is not None:
            res["text"] = self.text
        if self.json_data is not None:
            res["json_data"] = self.json_data
        if self.function_call is not None:
            res["function_call"] = self.function_call
        return res

    def __repr__(self) -> str:
        if self.text is not None:
            return f"Part.from_text({self.text!r})"
        if self.json_data is not None:
            return f"Part.from_json({self.json_data!r})"
        if self.function_call is not None:
            return f"Part.from_function_call({self.function_call['name']!r}, {self.function_call['args']!r})"
        return "Part()"


class MockContent:
    """Mock implementation of the ADK Content class."""
    def __init__(self, parts: List[MockPart]):
        self.parts = parts

    @classmethod
    def from_text(cls, text: str):
        return cls([MockPart.from_text(text)])

    @classmethod
    def from_parts(cls, parts: List[MockPart]):
        return cls(parts)

    def to_dict(self) -> Dict[str, Any]:
        return {"parts": [p.to_dict() for p in self.parts]}

    def __repr__(self) -> str:
        return f"Content(parts={self.parts!r})"


class MockCallbackContext:
    """Mock implementation of the ADK CallbackContext class."""
    def __init__(self, variables: Optional[Dict[str, Any]] = None, transcript: str = ""):
        self.variables = variables if variables is not None else {}
        self.state = self.variables  # Alias context.state to context.variables
        self.transcript = transcript

    def __repr__(self) -> str:
        return f"CallbackContext(variables={self.variables!r}, transcript={self.transcript!r})"


class MockLlmRequest:
    """Mock implementation of the ADK LlmRequest class."""
    def __init__(self, prompt: str = "", temperature: float = 0.7, content: Optional[MockContent] = None):
        self.prompt = prompt
        self.temperature = temperature
        self.content = content if content is not None else MockContent([])

    def __repr__(self) -> str:
        return f"LlmRequest(prompt={self.prompt!r}, temperature={self.temperature!r}, content={self.content!r})"


class MockLlmResponse:
    """Mock implementation of the ADK LlmResponse class."""
    def __init__(self, content: MockContent):
        self.content = content

    @classmethod
    def from_parts(cls, parts: List[MockPart]):
        return cls(MockContent(parts))

    def to_dict(self) -> Dict[str, Any]:
        return {"content": self.content.to_dict()}

    def __repr__(self) -> str:
        return f"LlmResponse(content={self.content!r})"


class MockTool:
    """Mock implementation of the ADK Tool class."""
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description

    def __repr__(self) -> str:
        return f"Tool(name={self.name!r})"


# =====================================================================
# 2. Inject Mock Module into Python's sys.modules
# =====================================================================

mock_ces_module = types.ModuleType("google.cloud.ces")
mock_ces_module.Part = MockPart
mock_ces_module.Content = MockContent
mock_ces_module.CallbackContext = MockCallbackContext
mock_ces_module.LlmRequest = MockLlmRequest
mock_ces_module.LlmResponse = MockLlmResponse
mock_ces_module.Tool = MockTool

sys.modules["google.cloud.ces"] = mock_ces_module


# =====================================================================
# 3. Dynamic Execution Engine
# =====================================================================

def execute_callback(
    filepath: str,
    func_name: str,
    variables: Dict[str, Any],
    transcript: str,
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_response: Dict[str, Any]
) -> None:
    # Safely load the callback module
    spec = importlib.util.spec_from_file_location("simulated_callback", filepath)
    if spec is None or spec.loader is None:
        print(f"ERROR: Cannot create module spec for {filepath}", file=sys.stderr)
        sys.exit(1)
        
    module = importlib.util.module_from_spec(spec)
    
    # Pre-inject environment globals directly into the module dictionary
    # This emulates the Google Cloud CES pre-injected variables sandbox
    try:
        import requests
        module.__dict__["ces_requests"] = requests
    except ImportError:
        module.__dict__["ces_requests"] = MagicMock()
        
    module.__dict__["tools"] = MagicMock()
    module.__dict__["async_tools"] = MagicMock()
    
    # Pre-inject variable helper shortcuts
    def get_variable(key: str, default: Any = None) -> Any:
        return variables.get(key, default)
    def set_variable(key: str, value: Any) -> None:
        variables[key] = value
    def remove_variable(key: str) -> None:
        if key in variables:
            del variables[key]

    module.__dict__["get_variable"] = get_variable
    module.__dict__["set_variable"] = set_variable
    module.__dict__["remove_variable"] = remove_variable

    # Run module compilation/load
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"COMPILE ERROR: Callback script failed to compile/run module setup: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Check if target callback function exists
    if not hasattr(module, func_name):
        print(f"ERROR: Callback function '{func_name}' not found in {filepath}", file=sys.stderr)
        # Suggest available functions
        funcs = [name for name, val in module.__dict__.items() if isinstance(val, types.FunctionType) and not name.startswith("_")]
        print(f"Available functions: {', '.join(funcs)}")
        sys.exit(1)

    callback_func = getattr(module, func_name)

    # Instantiate parameters
    context = MockCallbackContext(variables=variables, transcript=transcript)
    llm_req = MockLlmRequest(prompt=transcript, content=MockContent.from_text(transcript))
    llm_resp_content = MockContent([MockPart.from_text("Model generated response text.")])
    llm_resp = MockLlmResponse(llm_resp_content)
    tool = MockTool(name=tool_name)

    # Prepare function arguments based on hook signature
    kwargs = {}
    if func_name in ("before_agent_callback", "after_agent_callback"):
        kwargs["callback_context"] = context
    elif func_name == "before_model_callback":
        kwargs["callback_context"] = context
        kwargs["llm_request"] = llm_req
    elif func_name == "after_model_callback":
        kwargs["callback_context"] = context
        kwargs["llm_response"] = llm_resp
    elif func_name == "before_tool_callback":
        kwargs["tool"] = tool
        kwargs["input"] = tool_input
        kwargs["callback_context"] = context
    elif func_name == "after_tool_callback":
        kwargs["tool"] = tool
        kwargs["input"] = tool_input
        kwargs["callback_context"] = context
        kwargs["tool_response"] = tool_response
    else:
        # Generic fallback
        print(f"WARNING: Unknown callback signature '{func_name}'. Attempting call with context.")
        kwargs["callback_context"] = context

    # Print run configuration
    print("=" * 60)
    print(f"RUNNING CALLBACK SIMULATION")
    print(f"File:      {filepath}")
    print(f"Function:  {func_name}")
    print(f"Arguments: {', '.join(f'{k}={v}' for k, v in kwargs.items())}")
    print("=" * 60)

    # Run the callback function
    try:
        res = callback_func(**kwargs)
    except Exception as e:
        print(f"\n[EXCEPTION IN CALLBACK]: Execution failed with error:\n", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Print results
    print("\nSIMULATION RESULTS")
    print("-" * 30)
    print(f"Return Value:  {res!r}")
    if hasattr(res, "to_dict"):
        print(f"Return JSON:   {json.dumps(res.to_dict(), indent=2)}")
    elif isinstance(res, dict):
        print(f"Return JSON:   {json.dumps(res, indent=2)}")
        
    print(f"Final State Variables: {json.dumps(context.variables, indent=2)}")
    print("-" * 30)


# =====================================================================
# 4. Command Line Entry Point
# =====================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Local runtime simulator for Google Cloud CX Agent Studio (CES) Python Callbacks."
    )
    parser.add_argument("path", help="Path to the custom callback python file")
    parser.add_argument(
        "--function", "-f",
        default="before_model_callback",
        help="Name of the callback function to run (default: before_model_callback)"
    )
    parser.add_argument(
        "--variables", "-v",
        default="{}",
        help="JSON string representing initial session variables"
    )
    parser.add_argument(
        "--transcript", "-t",
        default="Hello there",
        help="Mock user transcript for callback_context"
    )
    parser.add_argument(
        "--tool-name", "-n",
        default="mock_tool",
        help="Tool name for before_tool_callback or after_tool_callback"
    )
    parser.add_argument(
        "--tool-input", "-i",
        default="{}",
        help="JSON string for tool input dictionary"
    )
    parser.add_argument(
        "--tool-response", "-r",
        default="{}",
        help="JSON string for tool response dictionary"
    )

    args = parser.parse_args()

    # Parse JSON parameters
    try:
        variables = json.loads(args.variables)
    except json.JSONDecodeError as e:
        print(f"ERROR: --variables is invalid JSON: {e}", file=sys.stderr)
        return 1

    try:
        tool_input = json.loads(args.tool_input)
    except json.JSONDecodeError as e:
        print(f"ERROR: --tool-input is invalid JSON: {e}", file=sys.stderr)
        return 1

    try:
        tool_response = json.loads(args.tool_response)
    except json.JSONDecodeError as e:
        print(f"ERROR: --tool-response is invalid JSON: {e}", file=sys.stderr)
        return 1

    execute_callback(
        filepath=args.path,
        func_name=args.function,
        variables=variables,
        transcript=args.transcript,
        tool_name=args.tool_name,
        tool_input=tool_input,
        tool_response=tool_response
    )
    return 0

if __name__ == "__main__":
    sys.exit(main())
