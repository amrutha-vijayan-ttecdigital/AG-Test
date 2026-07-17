"""Custom metadata and visible label grammar parsers for CES designs."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

# Regex matching: [MODALITY][AUTHORITY_OR_SYNC] label
LABEL_GRAMMAR = re.compile(
    r"^\[(MUST\s+NOT|MUST|MAY|SHOULD\s+NOT|SHOULD|OBSERVED)\]"
    r"(?:\[([A-Z0-9_]+)\])?"
    r"\s*(.*)$",
    re.IGNORECASE
)

def parse_visible_label(label: str) -> Dict[str, Any]:
    """Parse visible edge labels using the CES visible connector label grammar."""
    match = LABEL_GRAMMAR.match(label.strip())
    if not match:
        return {
            "modality": None,
            "authority": "UNKNOWN",
            "syncBehavior": "synchronous",
            "text": label,
            "status": "explicit",
            "is_parsed": False
        }

    mod_str = match.group(1).upper().replace(" ", "_")
    auth_str = match.group(2).upper() if match.group(2) else None
    rest = match.group(3).strip()

    modality = None
    status = "explicit"
    if mod_str == "MUST":
        modality = "MUST"
    elif mod_str == "MAY":
        modality = "MAY"
    elif mod_str == "MUST_NOT":
        modality = "MUST_NOT"
    elif mod_str == "SHOULD":
        modality = "SHOULD"
    elif mod_str == "SHOULD_NOT":
        modality = "SHOULD_NOT"
    elif mod_str == "OBSERVED":
        modality = "MAY"
        status = "observed"

    authority = "UNKNOWN"
    sync_behavior = "synchronous"

    if auth_str:
        if auth_str in ("ASYNC", "ASYNCHRONOUS"):
            sync_behavior = "asynchronous"
            authority = "MODEL_INSTRUCTION"
        elif auth_str in ("SYNC", "SYNCHRONOUS"):
            sync_behavior = "synchronous"
            authority = "MODEL_INSTRUCTION"
        elif auth_str == "MODEL":
            authority = "MODEL_INSTRUCTION"
        elif auth_str == "RULE":
            authority = "DETERMINISTIC_HANDOFF_RULE"
        elif auth_str == "CALLBACK":
            authority = "CALLBACK"
        elif auth_str == "GUARDRAIL":
            authority = "GUARDRAIL"
        elif auth_str == "TOOL":
            authority = "TOOL_IMPLEMENTATION"
        elif auth_str == "FLOW":
            authority = "REMOTE_DIALOGFLOW_AGENT"
        elif auth_str == "CLIENT":
            authority = "CLIENT_APPLICATION"
        elif auth_str == "HUMAN":
            authority = "HUMAN_PROCESS"
        elif auth_str == "PLATFORM":
            authority = "PLATFORM_RUNTIME"

    return {
        "modality": modality,
        "authority": authority,
        "syncBehavior": sync_behavior,
        "text": rest,
        "status": status,
        "is_parsed": True
    }

def get_ces_custom_data(item: Dict[str, Any]) -> Dict[str, Any]:
    """Extract all keys matching 'ces.*' custom data namespace."""
    metadata = {}
    custom_data = item.get("customData", []) or []
    for entry in custom_data:
        key = entry.get("key", "")
        if key.startswith("ces."):
            metadata[key] = entry.get("value")
    return metadata
