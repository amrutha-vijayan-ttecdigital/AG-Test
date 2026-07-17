"""Build normalized logical topology from physical Lucid items."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def build_logical_graph(physical: dict[str, Any]) -> dict[str, Any]:
    pages = []
    diagnostics = list(physical.get("diagnostics", []))
    for page in physical.get("pages", []):
        page_graph, page_diags = build_page_graph(page)
        pages.append(page_graph)
        diagnostics.extend(page_diags)
    return {
        "schemaVersion": physical.get("schemaVersion"),
        "documentId": physical.get("document", {}).get("id"),
        "pages": pages,
        "diagnostics": diagnostics,
    }


def build_page_graph(page: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    items = page.get("items", {})
    shapes = {s.get("id"): s for s in items.get("shapes", []) if s.get("id")}
    lines = {l.get("id"): l for l in items.get("lines", []) if l.get("id")}
    groups = {g.get("id"): g for g in items.get("groups", []) if g.get("id")}
    layers = {l.get("id"): l for l in items.get("layers", []) if l.get("id")}
    diagnostics: list[dict[str, Any]] = []

    nodes = []
    for sid, shape in shapes.items():
        nodes.append(
            {
                "id": sid,
                "kind": "shape",
                "class": shape.get("class"),
                "text": extract_text(shape),
                "textAreas": shape.get("textAreas", []),
                "customData": shape.get("customData", []),
                "linkedData": shape.get("linkedData", []),
                "contains": shape.get("contains", {}),
                "raw": shape,
            }
        )

    container_map: dict[str, list[str]] = defaultdict(list)
    for container in list(shapes.values()) + list(groups.values()) + list(layers.values()):
        cid = container.get("id")
        contains = container.get("contains", {})
        members = []
        if isinstance(contains, dict):
            members.extend(contains.get("shapes", []))
            members.extend(contains.get("lines", []))
            members.extend(contains.get("groups", []))
        members.extend(container.get("members", []) or [])
        for member in members:
            container_map[member].append(cid)

    edges = []
    for line_id, line in lines.items():
        srcs = resolve_endpoint(line_id, "endpoint1", shapes, lines)
        dsts = resolve_endpoint(line_id, "endpoint2", shapes, lines)
        diagnostics.extend(srcs["diagnostics"])
        diagnostics.extend(dsts["diagnostics"])
        if len(srcs["shapeIds"]) != 1 or len(dsts["shapeIds"]) != 1:
            diagnostics.append(
                {
                    "severity": "warning",
                    "code": "ambiguous_or_unresolved_line",
                    "pageId": page.get("id"),
                    "lineId": line_id,
                    "endpoint1ShapeIds": srcs["shapeIds"],
                    "endpoint2ShapeIds": dsts["shapeIds"],
                    "evidence": {
                        "endpoint1": line.get("endpoint1"),
                        "endpoint2": line.get("endpoint2"),
                    },
                }
            )
            continue
        edges.append(
            {
                "id": line_id,
                "from": srcs["shapeIds"][0],
                "to": dsts["shapeIds"][0],
                "label": extract_text(line),
                "textAreas": line.get("textAreas", []),
                "rawLine": line,
                "evidence": {
                    "direction": "endpoint1_to_endpoint2",
                    "endpoint1Path": srcs["path"],
                    "endpoint2Path": dsts["path"],
                    "endpoint1": line.get("endpoint1"),
                    "endpoint2": line.get("endpoint2"),
                },
            }
        )

    metadata = {
        "groups": list(groups.values()),
        "layers": list(layers.values()),
        "containerMembership": dict(container_map),
        "unrenderedLineCount": len(lines) - len(edges),
    }
    return (
        {
            "id": page.get("id"),
            "title": page.get("title"),
            "index": page.get("index"),
            "nodes": nodes,
            "edges": edges,
            "metadata": metadata,
        },
        diagnostics,
    )


def resolve_endpoint(
    line_id: str,
    endpoint_key: str,
    shapes: dict[str, dict[str, Any]],
    lines: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    line = lines[line_id]
    connected_to = (line.get(endpoint_key) or {}).get("connectedTo")
    diagnostics: list[dict[str, Any]] = []
    if not connected_to:
        return {
            "shapeIds": [],
            "path": [line_id, endpoint_key],
            "diagnostics": [{"severity": "warning", "code": "dangling_endpoint", "lineId": line_id, "endpoint": endpoint_key}],
        }
    shape_ids = sorted(_walk_to_shapes(connected_to, shapes, lines, visited_lines={line_id}, path=[line_id, connected_to], diagnostics=diagnostics))
    return {"shapeIds": shape_ids, "path": [line_id, connected_to], "diagnostics": diagnostics}


def _walk_to_shapes(
    item_id: str,
    shapes: dict[str, dict[str, Any]],
    lines: dict[str, dict[str, Any]],
    *,
    visited_lines: set[str],
    path: list[str],
    diagnostics: list[dict[str, Any]],
) -> set[str]:
    if item_id in shapes:
        return {item_id}
    if item_id not in lines:
        diagnostics.append({"severity": "warning", "code": "unknown_connection_target", "itemId": item_id, "path": path})
        return set()
    if item_id in visited_lines:
        diagnostics.append({"severity": "warning", "code": "line_connection_cycle", "lineId": item_id, "path": path})
        return set()
    visited_lines.add(item_id)
    found: set[str] = set()
    line = lines[item_id]
    for endpoint_name in ("endpoint1", "endpoint2"):
        next_id = (line.get(endpoint_name) or {}).get("connectedTo")
        if not next_id:
            continue
        found.update(_walk_to_shapes(next_id, shapes, lines, visited_lines=set(visited_lines), path=path + [next_id], diagnostics=diagnostics))
    if len(found) > 1:
        diagnostics.append({"severity": "warning", "code": "line_to_line_fanout", "lineId": item_id, "shapeIds": sorted(found), "path": path})
    return found


def extract_text(item: dict[str, Any]) -> str:
    texts = []
    for text_area in item.get("textAreas", []) or []:
        text = str(text_area.get("text", "")).strip()
        if text:
            texts.append(text)
    return " | ".join(texts)

