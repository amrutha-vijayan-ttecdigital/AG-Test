"""Lucid graph adapter for parsing and resolving graph topology and metadata."""

from __future__ import annotations

from typing import Any, List, Dict, Tuple, Set
from .errors import LucidCesParseError


def load_lucid_graph(compiled_doc: dict[str, Any]) -> dict[str, Any]:
    """Exposes pages, shapes, lines, groups, layers, and resolved line-to-line connections."""
    pages = []
    
    for page in compiled_doc.get("physical", {}).get("pages", []):
        page_id = page.get("id")
        title = page.get("title", "Untitled Page")
        
        items = page.get("items", {}) or {}
        shapes_dict = {s.get("id"): s for s in items.get("shapes", []) if s.get("id")}
        lines_dict = {l.get("id"): l for l in items.get("lines", []) if l.get("id")}
        
        # Build logical connections resolving line-to-line chains
        resolved_edges = []
        for line_id, line in lines_dict.items():
            src_shapes, src_lines = walk_line_endpoint(line_id, "endpoint1", shapes_dict, lines_dict)
            dst_shapes, dst_lines = walk_line_endpoint(line_id, "endpoint2", shapes_dict, lines_dict)
            
            if len(src_shapes) == 1 and len(dst_shapes) == 1:
                all_lines = sorted(list(set([line_id] + src_lines + dst_lines)))
                resolved_edges.append({
                    "id": line_id,
                    "source": src_shapes[0],
                    "target": dst_shapes[0],
                    "physicalLineIds": all_lines,
                    "label": extract_line_text(line),
                    "raw": line
                })
        
        pages.append({
            "id": page_id,
            "title": title,
            "shapes": list(shapes_dict.values()),
            "lines": list(lines_dict.values()),
            "groups": items.get("groups", []),
            "layers": items.get("layers", []),
            "resolvedEdges": resolved_edges,
            "customData": page.get("customData", []),
            "linkedData": page.get("linkedData", [])
        })
        
    return {
        "document": compiled_doc.get("physical", {}).get("document", {}),
        "pages": pages,
        "diagnostics": compiled_doc.get("logical", {}).get("diagnostics", [])
    }

def walk_line_endpoint(
    line_id: str,
    endpoint_key: str,
    shapes: dict[str, dict[str, Any]],
    lines: dict[str, dict[str, Any]]
) -> tuple[list[str], list[str]]:
    """Walk an endpoint to resolve the target shape ID and all traversed lines."""
    line = lines[line_id]
    connected_to = (line.get(endpoint_key) or {}).get("connectedTo")
    if not connected_to:
        return [], []
    
    visited_lines = {line_id}
    return _walk_recursive(connected_to, shapes, lines, visited_lines)

def _walk_recursive(
    item_id: str,
    shapes: dict[str, dict[str, Any]],
    lines: dict[str, dict[str, Any]],
    visited_lines: set[str]
) -> tuple[list[str], list[str]]:
    if item_id in shapes:
        return [item_id], []
    if item_id not in lines:
        return [], []
    if item_id in visited_lines:
        return [], []
        
    visited_lines.add(item_id)
    resolved_shapes = set()
    traversed_lines = {item_id}
    
    line = lines[item_id]
    for endpoint in ("endpoint1", "endpoint2"):
        next_id = (line.get(endpoint) or {}).get("connectedTo")
        if next_id:
            s_ids, l_ids = _walk_recursive(next_id, shapes, lines, set(visited_lines))
            resolved_shapes.update(s_ids)
            traversed_lines.update(l_ids)
            
    return sorted(list(resolved_shapes)), sorted(list(traversed_lines))

def extract_line_text(line: dict[str, Any]) -> str:
    texts = []
    for ta in line.get("textAreas", []) or []:
        text = str(ta.get("text", "")).strip()
        if text:
            texts.append(text)
    return " | ".join(texts)
