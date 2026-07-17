"""Mermaid parsing and Lucid Standard Import generation."""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

from .errors import MermaidParseError

EDGE_RE = re.compile(r"^\s*([A-Za-z][\w.-]*)\s*-->\s*(?:\|\"?(.+?)\"?\|\s*)?([A-Za-z][\w.-]*)\s*$")
NODE_RE = re.compile(r"^\s*([A-Za-z][\w.-]*)\s*(.+?)\s*$")


def parse_mermaid(text: str) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("%%") or line.startswith("flowchart") or line.startswith("graph"):
            continue
        edge = EDGE_RE.match(line)
        if edge:
            src, label, dst = edge.groups()
            edges.append({"src": src, "dst": dst, "label": label or ""})
            nodes.setdefault(src, {"label": src, "shape": "process"})
            nodes.setdefault(dst, {"label": dst, "shape": "process"})
            continue
        node = NODE_RE.match(line)
        if node:
            nid, syntax = node.groups()
            label = _extract_label(syntax)
            nodes[nid] = {"label": label or nid, "shape": _shape_from_syntax(syntax)}
            continue
        raise MermaidParseError(f"Unsupported Mermaid syntax: {raw_line}")
    return nodes, edges


def standard_import_document(title: str, nodes: dict[str, dict[str, Any]], edges: list[dict[str, str]]) -> dict[str, Any]:
    shapes = []
    lines = []
    for idx, (node_id, node) in enumerate(nodes.items()):
        rank = idx // 4
        col = idx % 4
        shapes.append(
            {
                "id": node_id,
                "class": _lucid_class(node.get("shape", "process")),
                "boundingBox": {"x": 120 + col * 260, "y": 120 + rank * 160, "w": 180, "h": 70},
                "text": [{"text": node.get("label", node_id)}],
            }
        )
    for idx, edge in enumerate(edges):
        line = {
            "id": f"line_{idx}",
            "endpoint1": {"style": "None", "connectedTo": edge["src"]},
            "endpoint2": {"style": "Arrow", "connectedTo": edge["dst"]},
        }
        if edge.get("label"):
            line["text"] = [{"text": edge["label"]}]
        lines.append(line)
    return {"version": 1, "title": title, "product": "lucidchart", "pages": [{"id": "page1", "title": title, "shapes": shapes, "lines": lines}]}


def write_standard_import_zip(path: str | Path, title: str, nodes: dict[str, dict[str, Any]], edges: list[dict[str, str]]) -> None:
    doc = standard_import_document(title, nodes, edges)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("document.json", json.dumps(doc, ensure_ascii=False, indent=2))


def _extract_label(syntax: str) -> str:
    match = re.search(r'"([^"]*)"', syntax)
    if match:
        return match.group(1)
    stripped = syntax.strip()
    return stripped.strip("[](){}")


def _shape_from_syntax(syntax: str) -> str:
    if "{{" in syntax:
        return "decision"
    if "([" in syntax:
        return "terminator"
    if "[(" in syntax:
        return "database"
    if "[[" in syntax:
        return "subprocess"
    return "process"


def _lucid_class(shape: str) -> str:
    return {
        "decision": "DecisionDiamond",
        "terminator": "Terminator",
        "database": "Database",
        "subprocess": "PredefinedProcess",
    }.get(shape, "ProcessBlock")

