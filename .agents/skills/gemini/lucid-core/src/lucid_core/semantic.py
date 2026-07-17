"""Conservative CX semantic projection from logical graph evidence."""

from __future__ import annotations

import re
from typing import Any


def build_semantic_ir(logical: dict[str, Any]) -> dict[str, Any]:
    pages = []
    diagnostics = []
    for page in logical.get("pages", []):
        semantic_nodes = []
        for node in page.get("nodes", []):
            sem, sem_diags = classify_node(node, page.get("id"))
            semantic_nodes.append(sem)
            diagnostics.extend(sem_diags)
        semantic_edges = [classify_edge(edge) for edge in page.get("edges", [])]
        pages.append({"pageId": page.get("id"), "title": page.get("title"), "nodes": semantic_nodes, "edges": semantic_edges})
    return {"pages": pages, "diagnostics": diagnostics}


def classify_node(node: dict[str, Any], page_id: str | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cls = node.get("class") or ""
    text = node.get("text") or ""
    diagnostics = []
    category = "process"
    if "Diamond" in cls:
        category = "decision"
        diagnostics.append(
            {
                "severity": "info",
                "code": "decision_not_assumed_page",
                "pageId": page_id,
                "nodeId": node.get("id"),
                "message": "Diamond shape preserved as decision evidence; it is not automatically mapped to a DFCX page.",
            }
        )
    elif "Terminator" in cls:
        category = "entry_or_exit"
    elif "Stickie" in cls or "StickyNote" in cls:
        category = "note"
    elif "MinimalTextBlock" in cls:
        category = "label"
    elif "PaperTape" in cls:
        category = "data"
    elif "Database" in cls:
        category = "webhook_or_data"
    inferred = []
    lower = text.lower()
    if "webhook" in lower or re.search(r"\bdb\b|database", lower):
        inferred.append({"type": "dfcx.webhook_or_data_call", "basis": "text"})
    if "transfer" in lower or "queue" in lower:
        inferred.append({"type": "dfcx.live_agent_handoff", "basis": "text"})
    if "playbook" in lower:
        inferred.append({"type": "dfcx.playbook", "basis": "text"})
    if "agent" in lower or "sub-agent" in lower or "subagent" in lower:
        inferred.append({"type": "cx_agent_studio.agent_or_delegation", "basis": "text"})
    return (
        {
            "id": node.get("id"),
            "text": text,
            "shapeClass": cls,
            "category": category,
            "inferredSemantics": inferred,
            "evidence": {"textAreas": node.get("textAreas", []), "customData": node.get("customData", [])},
        },
        diagnostics,
    )


def classify_edge(edge: dict[str, Any]) -> dict[str, Any]:
    label = edge.get("label") or ""
    edge_type = "transition"
    if "$session.params" in label or "==" in label or "!=" in label:
        edge_type = "condition_route"
    elif label.lower().startswith("event:") or "no-match" in label.lower() or "no-input" in label.lower():
        edge_type = "event_handler"
    return {
        "id": edge.get("id"),
        "from": edge.get("from"),
        "to": edge.get("to"),
        "label": label,
        "type": edge_type,
        "evidence": edge.get("evidence", {}),
    }

