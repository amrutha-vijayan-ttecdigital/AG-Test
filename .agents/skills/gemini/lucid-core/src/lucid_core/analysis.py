"""Graph analysis helpers that avoid inventing a single execution order."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


def analyze_logical_graph(logical: dict[str, Any]) -> dict[str, Any]:
    pages = []
    for page in logical.get("pages", []):
        pages.append(analyze_page(page))
    return {"pages": pages}


def analyze_page(page: dict[str, Any]) -> dict[str, Any]:
    node_ids = [n["id"] for n in page.get("nodes", [])]
    outgoing: dict[str, list[str]] = defaultdict(list)
    incoming: dict[str, list[str]] = defaultdict(list)
    for edge in page.get("edges", []):
        outgoing[edge["from"]].append(edge["to"])
        incoming[edge["to"]].append(edge["from"])
    entrypoints = [nid for nid in node_ids if not incoming[nid]]
    exits = [nid for nid in node_ids if not outgoing[nid]]
    joins = [nid for nid in node_ids if len(incoming[nid]) > 1]
    branches = [nid for nid in node_ids if len(outgoing[nid]) > 1]
    reachable = sorted(_reachable(entrypoints, outgoing))
    unreachable = [nid for nid in node_ids if nid not in reachable]
    return {
        "pageId": page.get("id"),
        "entrypoints": entrypoints,
        "exits": exits,
        "joins": joins,
        "branches": branches,
        "cycles": _cycles(node_ids, outgoing),
        "unreachable": unreachable,
    }


def _reachable(entrypoints: list[str], outgoing: dict[str, list[str]]) -> set[str]:
    seen = set(entrypoints)
    queue = deque(entrypoints)
    while queue:
        node_id = queue.popleft()
        for nxt in outgoing.get(node_id, []):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def _cycles(node_ids: list[str], outgoing: dict[str, list[str]]) -> list[list[str]]:
    cycles: list[list[str]] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node_id: str, path: list[str]) -> None:
        if node_id in visiting:
            if node_id in path:
                cycles.append(path[path.index(node_id) :] + [node_id])
            return
        if node_id in visited:
            return
        visiting.add(node_id)
        for nxt in outgoing.get(node_id, []):
            dfs(nxt, path + [nxt])
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in node_ids:
        dfs(node_id, [node_id])
    deduped = []
    seen = set()
    for cycle in cycles:
        key = tuple(cycle)
        if key not in seen:
            seen.add(key)
            deduped.append(cycle)
    return deduped

