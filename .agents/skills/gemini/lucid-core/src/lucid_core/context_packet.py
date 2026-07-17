"""Compact model-context packet rendering."""

from __future__ import annotations

from typing import Any


def build_context_packet(compiled: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": compiled.get("schemaVersion"),
        "document": compiled.get("physical", {}).get("document", {}),
        "snapshot": compiled.get("physical", {}).get("snapshot", {}),
        "pages": [
            {
                "id": page.get("id"),
                "title": page.get("title"),
                "nodes": [{"id": n.get("id"), "class": n.get("class"), "text": n.get("text")} for n in page.get("nodes", [])],
                "edges": [
                    {"id": e.get("id"), "from": e.get("from"), "to": e.get("to"), "label": e.get("label")} for e in page.get("edges", [])
                ],
            }
            for page in compiled.get("logical", {}).get("pages", [])
        ],
        "diagnostics": compiled.get("logical", {}).get("diagnostics", []) + compiled.get("semantic", {}).get("diagnostics", []),
    }

