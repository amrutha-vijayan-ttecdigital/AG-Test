#!/usr/bin/env python3
"""
validate_callback.py — Audit custom Python callback code for signature matching, sandbox compatibility, and voice safety.
"""

import argparse
import ast
import sys
from pathlib import Path

# Platform-required exact signatures
REQUIRED_PARAMS = {
    "before_agent_callback": ["callback_context"],
    "after_agent_callback": ["callback_context"],
    "before_model_callback": ["callback_context", "llm_request"],
    "after_model_callback": ["callback_context", "llm_response"],
    "before_tool_callback": ["tool", "input", "callback_context"],
    "after_tool_callback": ["tool", "input", "callback_context", "tool_response"]
}

class CallbackAuditor(ast.NodeVisitor):
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.found_any = False

    def visit_Import(self, node):
        forbidden_imports = ["requests", "urllib", "http.client", "socket"]
        for name in node.names:
            base_module = name.name.split('.')[0]
            if base_module in forbidden_imports:
                self.warnings.append(
                    f"SANDBOX WARNING: Raw socket connection library '{base_module}' imported. "
                    f"Raw outbound network sockets are disabled in the sandbox. Use the 'ces_requests' library instead."
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        forbidden_imports = ["requests", "urllib", "http.client", "socket"]
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module in forbidden_imports:
                self.warnings.append(
                    f"SANDBOX WARNING: Raw socket connection library '{base_module}' imported. "
                    f"Raw outbound network sockets are disabled in the sandbox. Use the 'ces_requests' library instead."
                )
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        func_name = node.name
        if func_name in REQUIRED_PARAMS:
            self.found_any = True
            expected = REQUIRED_PARAMS[func_name]
            
            # Parse arguments
            args = [arg.arg for arg in node.args.args]
            
            # Check length matching
            if len(args) != len(expected):
                self.errors.append(
                    f"SIGNATURE ERROR: Function '{func_name}' expects exactly {len(expected)} parameters, "
                    f"got {len(args)}: ({', '.join(args)})"
                )
            else:
                # Check exact parameter names
                for act, exp in zip(args, expected):
                    if act != exp:
                        self.errors.append(
                            f"PARAMETER NAME ERROR: Parameter '{act}' in function '{func_name}' must match "
                            f"the specification '{exp}' exactly (renaming causes runtime TypeError)."
                        )

            # Check for error safety: Try block inside function body
            has_try = any(isinstance(child, ast.Try) for child in ast.walk(node))
            if not has_try:
                self.warnings.append(
                    f"SAFETY WARNING: No 'try/except' block found in '{func_name}'. "
                    f"Uncaught exceptions will crash the entire conversational turn."
                )

            # Voice safety checks if "model" or "agent" is in function name
            if "model" in func_name or "agent" in func_name:
                has_text = False
                has_transcript = False
                has_ssml_strip = False

                for child in ast.walk(node):
                    # Check for attribute accesses
                    if isinstance(child, ast.Attribute):
                        if child.attr == "text":
                            has_text = True
                        elif child.attr == "transcript":
                            has_transcript = True
                    
                    # Check for re.sub or replace calls with HTML/SSML-like strings
                    if isinstance(child, ast.Call):
                        # Call to re.sub
                        if (isinstance(child.func, ast.Attribute) and 
                            isinstance(child.func.value, ast.Name) and 
                            child.func.value.id == "re" and 
                            child.func.attr == "sub"):
                            # Check arguments
                            if child.args and isinstance(child.args[0], ast.Constant):
                                val = child.args[0].value
                                if isinstance(val, str) and ("<" in val or ">" in val or "[^>]*" in val):
                                    has_ssml_strip = True
                        
                        # Call to .replace() or .sub()
                        elif isinstance(child.func, ast.Attribute) and child.func.attr in ("replace", "sub"):
                            if child.args and isinstance(child.args[0], ast.Constant):
                                val = child.args[0].value
                                if isinstance(val, str) and ("<" in val or ">" in val):
                                    has_ssml_strip = True

                # Check text vs transcript
                if has_text and not has_transcript:
                    self.warnings.append(
                        f"VOICE WARNING: Callback '{func_name}' references '.text' but does not check '.transcript'. "
                        f"On telephony voice trunks, user speech inputs arrive in the transcript property."
                    )
                
                # Check SSML stripping
                if not has_ssml_strip:
                    self.warnings.append(
                        f"VOICE WARNING: Callback '{func_name}' modifies text output but does not seem to strip "
                        f"SSML tags (e.g. '<speak>', '<break>'). Chirp 3 HD voices will crash if SSML is present."
                    )
                    
        self.generic_visit(node)

def analyze_code(content: str) -> tuple[list[str], list[str]]:
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        return [f"SYNTAX ERROR: Code fails to compile: {e}"], []

    auditor = CallbackAuditor()
    auditor.visit(tree)
    
    if not auditor.found_any:
        auditor.warnings.append("No standard platform callback functions (e.g. before_model_callback) were found in the file.")
        
    return auditor.errors, auditor.warnings

def main():
    parser = argparse.ArgumentParser(description="Audit custom callback code for safety.")
    parser.add_argument("path", help="Path to the python callback file to validate")
    args = parser.parse_args()

    cb_path = Path(args.path)
    if not cb_path.is_file():
        print(f"FAIL: File does not exist: {cb_path}", file=sys.stderr)
        return 1

    try:
        content = cb_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"FAIL: Cannot read file: {e}", file=sys.stderr)
        return 1

    errors, warnings = analyze_code(content)

    print(f"Auditing callback file: {cb_path.name}")
    print("-" * 50)
    
    if errors:
        print(f"VERDICT: FAIL ({len(errors)} error(s), {len(warnings)} warning(s))")
        for err in errors:
            print(f"  [ERROR] {err}", file=sys.stderr)
        for warn in warnings:
            print(f"  [WARN]  {warn}")
        return 1
        
    if warnings:
        print(f"VERDICT: PASS WITH WARNINGS ({len(warnings)} warning(s))")
        for warn in warnings:
            print(f"  [WARN]  {warn}")
        return 0

    print("VERDICT: PASS (Clean, compliant, and voice-safe!)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
