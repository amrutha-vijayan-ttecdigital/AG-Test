"""Mermaid rendering from logical graph IR."""

from __future__ import annotations

import hashlib
import re
from typing import Any


def render_page_mermaid(compiled: dict[str, Any], page: dict[str, Any]) -> str:
    id_map = {node["id"]: mermaid_id(node["id"]) for node in page.get("nodes", [])}
    lines = [
        f"%% {page.get('title') or page.get('id')}",
        f"%% Derived from Lucid document {compiled.get('physical', {}).get('document', {}).get('id')}",
        "flowchart TD",
    ]
    for node in page.get("nodes", []):
        lines.append(f"    {id_map[node['id']]}{shape_syntax(node)}")
    if page.get("edges"):
        lines.append("")
    for edge in page.get("edges", []):
        src = id_map.get(edge.get("from"), mermaid_id(str(edge.get("from"))))
        dst = id_map.get(edge.get("to"), mermaid_id(str(edge.get("to"))))
        label = edge.get("label") or ""
        if label:
            lines.append(f"    {src} -->|\"{escape_mermaid(label)}\"| {dst}")
        else:
            lines.append(f"    {src} --> {dst}")
    diagnostics = [d for d in compiled.get("logical", {}).get("diagnostics", []) if d.get("pageId") == page.get("id")]
    if diagnostics:
        lines.append("")
        lines.append("%% Diagnostics")
        for diag in diagnostics:
            lines.append(f"%% {diag.get('code')}: {diag}")
    return "\n".join(lines) + "\n"


def mermaid_id(raw_id: str) -> str:
    base = re.sub(r"[^A-Za-z0-9_]", "_", raw_id)
    if not base or base[0].isdigit():
        base = "n_" + base
    digest = hashlib.sha1(raw_id.encode("utf-8")).hexdigest()[:8]
    return f"{base}_{digest}"


def shape_syntax(node: dict[str, Any]) -> str:
    label = escape_mermaid(node.get("text") or node.get("id") or "")
    cls = node.get("class") or ""
    if "Diamond" in cls:
        return f'{{{{"{label}"}}}}'
    if "Terminator" in cls:
        return f'(["{label}"])'
    if "Merge" in cls:
        return f'(("{label}"))'
    if "Database" in cls:
        return f'[("{label}")]'
    if "Predefined" in cls or "Subprocess" in cls:
        return f'[["{label}"]]'
    return f'["{label}"]'


def escape_mermaid(text: str) -> str:
    return " ".join(text.replace('"', "'").split())

