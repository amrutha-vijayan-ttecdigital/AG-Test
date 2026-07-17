"""Render specialized Mermaid.js diagrams from the CES semantic IR."""

from __future__ import annotations

import re
from typing import Any, Dict, List
from .relationships import CesDesignQuery
from .models import RelationshipType, Modality

def mermaid_id(name: str) -> str:
    """Generate a stable, collision-free Mermaid node ID from a string."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if not clean or clean[0].isdigit():
        clean = "id_" + clean
    return clean

def render_mermaid_diagram(ir: Dict[str, Any], diagram_type: str = "capability") -> str:
    """
    Render a Mermaid.js diagram of the specified type.
    Supported types: 'hierarchy', 'capability', 'enforcement', 'variables', 'evaluations'
    """
    query = CesDesignQuery(ir)
    lines = ["flowchart TD"]
    
    # Store link index to apply custom styling at the end
    link_styles = []
    link_counter = 0

    def add_edge(src: str, dst: str, label: str, modality: Modality, status: str = "explicit"):
        nonlocal link_counter
        src_id = mermaid_id(src)
        dst_id = mermaid_id(dst)
        
        # Determine connector style
        if status == "observed":
            # Dotted gray line
            lines.append(f'    {src_id} -. "OBSERVED: {label}" .-> {dst_id}')
            link_styles.append(f"    linkStyle {link_counter} stroke:#888888,stroke-dasharray: 5 5;")
        elif modality == Modality.MUST_NOT or "must not" in label.lower():
            # Red barred line
            lines.append(f'    {src_id} -- "MUST NOT: {label}" --x {dst_id}')
            link_styles.append(f"    linkStyle {link_counter} stroke:#ff3333,stroke-width:2px;")
        elif modality == Modality.MUST:
            # Solid line
            lines.append(f'    {src_id} -- "{label}" --> {dst_id}')
            link_styles.append(f"    linkStyle {link_counter} stroke:#3333ff,stroke-width:2px;")
        else:
            # Dashed line (MAY)
            lines.append(f'    {src_id} -. "{label}" .-> {dst_id}')
            
        link_counter += 1

    if diagram_type == "hierarchy":
        # Nodes are agents and parents
        lines.append("    %% Agent Hierarchy")
        for agent_id, agent in query.agents.items():
            lines.append(f'    {mermaid_id(agent_id)}["{agent.displayName} ({agent_id})"]')
        
        for rel in query.relationships:
            if rel.relationType == RelationshipType.PARENT_OF:
                add_edge(rel.sourceId, rel.targetId, "Parent of", rel.modalGuarantee, rel.status)

    elif diagram_type == "capability":
        lines.append("    %% Capability Graph")
        for agent_id, agent in query.agents.items():
            lines.append(f'    {mermaid_id(agent_id)}["{agent.displayName} ({agent_id})"]')
        for tool_id, tool in query.tools.items():
            lines.append(f'    {mermaid_id(tool_id)}[("Tool: {tool_id}")]')
        for r_id, r in query.remotes.items():
            lines.append(f'    {mermaid_id(r_id)}[["Remote: {r_id}"]]')

        for rel in query.relationships:
            if rel.relationType in (
                RelationshipType.MAY_HANDOFF_TO,
                RelationshipType.MUST_HANDOFF_TO,
                RelationshipType.CALLS_TOOL,
                RelationshipType.USES_AGENT_AS_TOOL,
                RelationshipType.INVOKES_REMOTE_FLOW_AGENT,
                RelationshipType.FORBIDDEN_TRANSITION
            ):
                label = rel.displayName
                if rel.relationType == RelationshipType.USES_AGENT_AS_TOOL:
                    label += " (Agent as Tool)"
                add_edge(rel.sourceId, rel.targetId, label, rel.modalGuarantee, rel.status)

    elif diagram_type == "enforcement":
        lines.append("    %% Enforcement Graph")
        # Include agents, tools, callbacks, and guardrails
        for agent_id in query.agents:
            lines.append(f'    {mermaid_id(agent_id)}["{agent_id}"]')
        for tool_id in query.tools:
            lines.append(f'    {mermaid_id(tool_id)}[("{tool_id}")]')
        for cb_id, cb in query.callbacks.items():
            lines.append(f'    {mermaid_id(cb_id)}["Callback: {cb_id}"]')
        for gr_id, gr in query.guardrails.items():
            lines.append(f'    {mermaid_id(gr_id)}["Guardrail: {gr_id}"]')

        for rel in query.relationships:
            if rel.relationType in (RelationshipType.ENFORCED_BY, RelationshipType.GUARDED_BY):
                add_edge(rel.sourceId, rel.targetId, rel.relationType.value, rel.modalGuarantee, rel.status)

    elif diagram_type == "variables":
        lines.append("    %% Variable / Data Contract Graph")
        for agent_id in query.agents:
            lines.append(f'    {mermaid_id(agent_id)}["{agent_id}"]')
        for var_id, var in query.variables.items():
            lines.append(f'    {mermaid_id(var_id)}["Variable: {var_id} ({var.type})"]')

        for rel in query.relationships:
            if rel.relationType in (RelationshipType.READS_VARIABLE, RelationshipType.WRITES_VARIABLE):
                add_edge(rel.sourceId, rel.targetId, rel.relationType.value, rel.modalGuarantee, rel.status)

    elif diagram_type == "evaluations":
        lines.append("    %% Evaluation Coverage Graph")
        for agent_id in query.agents:
            lines.append(f'    {mermaid_id(agent_id)}["{agent_id}"]')
        for tool_id in query.tools:
            lines.append(f'    {mermaid_id(tool_id)}[("{tool_id}")]')
        for ev_id, ev in query.evaluations.items():
            lines.append(f'    {mermaid_id(ev_id)}["Evaluation: {ev_id}"]')
            
            # Draw edges from evaluation to resources it asserts/starts
            if ev.startingAgentId:
                add_edge(ev_id, ev.startingAgentId, "starts_at", Modality.MAY)
            
            # Simple substring matching to cover other nodes
            for target_id in list(query.agents.keys()) + list(query.tools.keys()):
                if target_id != ev.startingAgentId and (target_id in ev.description or any(target_id in m for m in ev.must + ev.may + ev.mustNot)):
                    add_edge(ev_id, target_id, "asserts", Modality.MAY)

    lines.extend(link_styles)
    return "\n".join(lines)
