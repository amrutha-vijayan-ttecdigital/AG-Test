"""Offline-first adapter to load and normalize saved CES runtime exports."""

from __future__ import annotations

import json
from typing import Any, Dict
from .errors import LucidCesParseError

def load_saved_runtime_export(path: str) -> Dict[str, Any]:
    """Load a saved CX Agent Studio app export or API snapshot from disk."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise LucidCesParseError(f"Failed to read runtime export file: {e}")
        
    if not isinstance(data, dict):
        raise LucidCesParseError("Runtime export data must be a JSON object.")
        
    # Normalize keys if needed (e.g., handles different CES API formats or CLI exports)
    normalized = {
        "application": data.get("application", {}) or {},
        "agents": data.get("agents", []) or [],
        "tools": data.get("tools", []) or [],
        "callbacks": data.get("callbacks", []) or [],
        "guardrails": data.get("guardrails", []) or [],
        "variables": data.get("variables", []) or [],
        "relationships": data.get("relationships", []) or [],
        "handoffs": data.get("handoffs", []) or [],
        "agentsAsTools": data.get("agentsAsTools", []) or [],
        "remotes": data.get("remotes", []) or [],
        "evaluations": data.get("evaluations", []) or [],
        "traces": data.get("traces", []) or []
    }
    
    return normalized
