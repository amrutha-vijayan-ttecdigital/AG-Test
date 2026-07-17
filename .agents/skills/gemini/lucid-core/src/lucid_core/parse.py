"""Lucid REST snapshot parsing and graph compilation."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from .analysis import analyze_logical_graph
from .semantic import build_semantic_ir
from .serialization import normalized_json_bytes, read_json
from .topology import build_logical_graph

SCHEMA_VERSION = "lucid-core.v1"
UUID_RE = re.compile(r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", re.I)


def get_document_id(url_or_id: str) -> str:
    match = UUID_RE.search(url_or_id)
    return match.group(0) if match else url_or_id


def load_document(path: str) -> dict[str, Any]:
    return read_json(path)


def compile_document(raw: dict[str, Any], *, document_id: str | None = None, fetched_at: str | None = None) -> dict[str, Any]:
    physical = build_physical_ir(raw, document_id=document_id, fetched_at=fetched_at)
    logical = build_logical_graph(physical)
    analysis = analyze_logical_graph(logical)
    semantic = build_semantic_ir(logical)
    return {
        "schemaVersion": SCHEMA_VERSION,
        "physical": physical,
        "logical": logical,
        "analysis": analysis,
        "semantic": semantic,
    }


def build_physical_ir(raw: dict[str, Any], *, document_id: str | None = None, fetched_at: str | None = None) -> dict[str, Any]:
    raw_bytes = normalized_json_bytes(raw)
    doc_id = document_id or raw.get("id")
    pages = []
    diagnostics = []
    for page in raw.get("pages", []):
        items = page.get("items", {}) or {}
        shapes = [preserve_item(s) for s in items.get("shapes", [])]
        lines = [preserve_item(l) for l in items.get("lines", [])]
        groups = [preserve_item(g) for g in items.get("groups", [])]
        layers = [preserve_item(l) for l in items.get("layers", [])]
        seen: dict[str, str] = {}
        for kind, values in (("shape", shapes), ("line", lines), ("group", groups), ("layer", layers)):
            for item in values:
                item_id = item.get("id")
                if not item_id:
                    diagnostics.append({"severity": "warning", "code": "item_missing_id", "pageId": page.get("id"), "kind": kind})
                    continue
                if item_id in seen:
                    diagnostics.append(
                        {
                            "severity": "error",
                            "code": "duplicate_item_id",
                            "pageId": page.get("id"),
                            "itemId": item_id,
                            "kinds": [seen[item_id], kind],
                        }
                    )
                seen[item_id] = kind
        pages.append(
            {
                "id": page.get("id"),
                "title": page.get("title", "Untitled Page"),
                "index": page.get("index"),
                "customData": page.get("customData", []),
                "linkedData": page.get("linkedData", []),
                "items": {
                    "shapes": shapes,
                    "lines": lines,
                    "groups": groups,
                    "layers": layers,
                },
                "raw": page,
            }
        )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "document": {
            "id": doc_id,
            "title": raw.get("title"),
            "product": raw.get("product"),
            "accountId": raw.get("accountId"),
            "data": raw.get("data", {}),
        },
        "snapshot": {
            "fetchedAt": fetched_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "apiVersion": "1",
            "toolSchemaVersion": SCHEMA_VERSION,
            "sha256": hashlib.sha256(raw_bytes).hexdigest(),
        },
        "pages": pages,
        "diagnostics": diagnostics,
        "raw": raw,
    }


def preserve_item(item: dict[str, Any]) -> dict[str, Any]:
    return dict(item)

