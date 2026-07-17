"""Markdown rendering from compiled Lucid graph IR."""

from __future__ import annotations

from typing import Any


def render_markdown(compiled: dict[str, Any]) -> str:
    physical = compiled["physical"]
    logical = compiled["logical"]
    analysis_by_page = {p["pageId"]: p for p in compiled.get("analysis", {}).get("pages", [])}
    lines = [
        f"# {physical.get('document', {}).get('title') or 'Lucid Design'}",
        "",
        f"- Document ID: `{physical.get('document', {}).get('id')}`",
        f"- Snapshot SHA-256: `{physical.get('snapshot', {}).get('sha256')}`",
        f"- Generated from schema: `{compiled.get('schemaVersion')}`",
        "",
        "> This is a derived view. Raw snapshot, physical IR, logical graph, and semantic IR are the source of truth.",
        "",
    ]
    for page in logical.get("pages", []):
        analysis = analysis_by_page.get(page.get("id"), {})
        lines.extend(render_page(page, analysis))
    diagnostics = logical.get("diagnostics", []) + compiled.get("semantic", {}).get("diagnostics", [])
    if diagnostics:
        lines.extend(["## Diagnostics", ""])
        for diag in diagnostics:
            lines.append(f"- `{diag.get('code')}` ({diag.get('severity', 'info')}): {diag}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_page(page: dict[str, Any], analysis: dict[str, Any]) -> list[str]:
    lines = [
        f"## {page.get('title') or page.get('id')}",
        "",
        f"- Nodes: {len(page.get('nodes', []))}",
        f"- Edges: {len(page.get('edges', []))}",
        f"- Entrypoints: {', '.join(f'`{x}`' for x in analysis.get('entrypoints', [])) or '(none)'}",
        f"- Branches: {', '.join(f'`{x}`' for x in analysis.get('branches', [])) or '(none)'}",
        f"- Joins: {', '.join(f'`{x}`' for x in analysis.get('joins', [])) or '(none)'}",
        "",
        "### Nodes",
        "",
    ]
    for node in page.get("nodes", []):
        text = one_line(node.get("text") or "")
        lines.append(f"- `{node.get('id')}` `{node.get('class')}`: {text or '(no text)'}")
    lines.extend(["", "### Connections", ""])
    if page.get("edges"):
        lines.extend(["| From | Label | To |", "|---|---|---|"])
        for edge in page.get("edges", []):
            lines.append(f"| `{edge.get('from')}` | {escape_cell(one_line(edge.get('label') or ''))} | `{edge.get('to')}` |")
    else:
        lines.append("(No resolved connections.)")
    lines.append("")
    if analysis.get("cycles"):
        lines.append("### Cycles")
        lines.append("")
        for cycle in analysis["cycles"]:
            lines.append("- " + " -> ".join(f"`{x}`" for x in cycle))
        lines.append("")
    return lines


def one_line(text: str) -> str:
    return " ".join(text.replace("|", "/").split())


def escape_cell(text: str) -> str:
    return text.replace("|", "/") or ""

