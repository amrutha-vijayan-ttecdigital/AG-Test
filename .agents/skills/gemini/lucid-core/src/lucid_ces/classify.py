"""Classify Lucid shapes and lines into semantic CES kinds."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from .metadata import get_ces_custom_data

def classify_shape(shape: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]], str]:
    """Resolve a shape's semantic kind based on custom metadata and visual clues."""
    custom_data = get_ces_custom_data(shape)
    
    text = ""
    for ta in shape.get("textAreas", []) or []:
        t = str(ta.get("text", "")).strip()
        if t:
            text += " " + t
    text = text.strip()

    # 1. Explicit Custom Data
    if "ces.kind" in custom_data:
        kind = custom_data["ces.kind"]
        evidence = [{"kind": "custom_data", "value": f"ces.kind = {kind}", "confidence": 1.0}]
        return kind, evidence, "explicit"

    # 2. Structured Text tags
    evidence = []
    text_lower = text.lower()
    
    if "agent_as_tool" in text_lower or "agent-as-tool" in text_lower or "agent as tool" in text_lower:
        evidence.append({"kind": "shape_text", "value": "Contains 'agent as tool' phrase", "confidence": 0.95})
        return "agent_as_tool", evidence, "inferred"

    if "callback" in text_lower:
        evidence.append({"kind": "shape_text", "value": "Contains 'callback' word", "confidence": 0.9})
        return "callback", evidence, "inferred"

    if "guardrail" in text_lower:
        evidence.append({"kind": "shape_text", "value": "Contains 'guardrail' word", "confidence": 0.9})
        return "guardrail", evidence, "inferred"

    if "variable" in text_lower:
        evidence.append({"kind": "shape_text", "value": "Contains 'variable' word", "confidence": 0.9})
        return "variable", evidence, "inferred"

    if "evaluation" in text_lower:
        evidence.append({"kind": "shape_text", "value": "Contains 'evaluation' word", "confidence": 0.9})
        return "evaluation", evidence, "inferred"

    if "dfcx" in text_lower or "dialogflow" in text_lower:
        evidence.append({"kind": "shape_text", "value": "Contains DFCX reference", "confidence": 0.9})
        return "remote_dialogflow_agent", evidence, "inferred"

    # 3. Class-based inferences
    shape_class = shape.get("class", "") or ""
    if "Diamond" in shape_class:
        evidence.append({"kind": "shape_class", "value": "Diamond shape class", "confidence": 0.8})
        return "handoff_rule", evidence, "inferred"

    if "Database" in shape_class:
        evidence.append({"kind": "shape_class", "value": "Database shape class", "confidence": 0.8})
        return "tool", evidence, "inferred"

    if "Stickie" in shape_class or "StickyNote" in shape_class:
        evidence.append({"kind": "shape_class", "value": "Sticky Note shape class", "confidence": 0.8})
        return "note", evidence, "inferred"

    if "Terminator" in shape_class:
        if "human" in text_lower or "escalate" in text_lower or "transfer" in text_lower:
            evidence.append({"kind": "shape_class_and_text", "value": "Terminator shape with transfer text", "confidence": 0.9})
            return "human_handoff", evidence, "inferred"
        evidence.append({"kind": "shape_class", "value": "Terminator shape class", "confidence": 0.7})
        return "human_handoff", evidence, "inferred"

    if "Rectangle" in shape_class or "Card" in shape_class:
        evidence.append({"kind": "shape_class", "value": "Rectangle/Card shape class", "confidence": 0.6})
        return "agent", evidence, "inferred"

    evidence.append({"kind": "fallback", "value": "Unclassified shape defaults to note", "confidence": 0.3})
    return "note", evidence, "inferred"
