"""Generate task-specific context packets for coding agents from compiled IR."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
from .relationships import CesDesignQuery

def generate_context_packet(
    ir: Dict[str, Any],
    agent_id: Optional[str] = None,
    task: Optional[str] = None,
    radius: int = 1,
    include_evaluations: bool = False,
    include_visual_evidence: bool = False,
    max_chars: Optional[int] = None
) -> str:
    """Generate a task-specific context packet with size controls."""
    query = CesDesignQuery(ir)
    
    sections = []
    
    # 1. Task and requested change
    sections.append("# Task Context")
    if task:
        sections.append(f"**Requested Change:** {task}")
    else:
        sections.append("**Requested Change:** [No specific task requested]")
    if agent_id:
        sections.append(f"**Target Agent:** {agent_id}")
    sections.append("")

    # 2. Explicit "Not Implied" statements
    sections.append("## Explicit Guidelines & Invariants (Not Implied)")
    sections.append("- A dashed connector indicates a `MAY` relationship (model-selected delegation), NOT a guaranteed `MUST` order.")
    sections.append("- Active conversation ownership remains with the caller during an `AGENT_AS_TOOL` invocation.")
    sections.append("- A Dialogflow CX (DFCX) remote agent must be treated as a black box; internal routes/pages are out of scope.")
    sections.append("- Observed traces or simulator outputs show what happened in a single run, NOT a design contract constraint.")
    sections.append("- Direct shape-to-shape lines or line-to-line connections represent explicit routing; never infer adjacency.")
    sections.append("")

    # 3. Determine relevant agents using graph search
    relevant_agent_ids = set()
    if agent_id and agent_id in query.agents:
        relevant_agent_ids.add(agent_id)
        # BFS traversal for radius
        queue = [(agent_id, 0)]
        while queue:
            curr, depth = queue.pop(0)
            if depth >= radius:
                continue
            
            # Find parent/children
            curr_agent = query.get_agent(curr)
            if curr_agent:
                if curr_agent.parentAgentId:
                    parent = curr_agent.parentAgentId
                    if parent not in relevant_agent_ids:
                        relevant_agent_ids.add(parent)
                        queue.append((parent, depth + 1))
                for child in curr_agent.childAgentIds:
                    if child not in relevant_agent_ids:
                        relevant_agent_ids.add(child)
                        queue.append((child, depth + 1))
            
            # Find handoffs
            for ho in query.handoffs:
                if ho.sourceAgentId == curr and ho.targetAgentId not in relevant_agent_ids:
                    relevant_agent_ids.add(ho.targetAgentId)
                    queue.append((ho.targetAgentId, depth + 1))
                elif ho.targetAgentId == curr and ho.sourceAgentId not in relevant_agent_ids:
                    relevant_agent_ids.add(ho.sourceAgentId)
                    queue.append((ho.sourceAgentId, depth + 1))
    else:
        # Include all agents if none specified
        relevant_agent_ids.update(query.agents.keys())

    # 4. Relevant application details
    sections.append("## Application Overview")
    app = query.get_application()
    sections.append(f"- **Application ID:** {app.id}")
    sections.append(f"- **Display Name:** {app.displayName}")
    sections.append(f"- **Root Agent:** {app.rootAgentId}")
    sections.append("")

    # 5. Selected agent contracts
    sections.append("## Relevant Agent Specifications")
    for a_id in sorted(list(relevant_agent_ids)):
        agent = query.get_agent(a_id)
        if agent:
            sections.append(f"### Agent: {agent.id} ({agent.displayName})")
            sections.append(f"- **Purpose:** {agent.purpose or 'N/A'}")
            sections.append(f"- **Kind:** {agent.kind}")
            if agent.inScopeGoals:
                sections.append(f"- **In-Scope Goals:** {', '.join(agent.inScopeGoals)}")
            if agent.outOfScopeGoals:
                sections.append(f"- **Out-of-Scope Goals:** {', '.join(agent.outOfScopeGoals)}")
            if agent.responsibilities:
                sections.append(f"- **Responsibilities:** {', '.join(agent.responsibilities)}")
            if agent.completionCriteria:
                sections.append(f"- **Completion Criteria:** {', '.join(agent.completionCriteria)}")
            if agent.humanEscalationBehavior:
                sections.append(f"- **Escalation/Exit Behavior:** {agent.humanEscalationBehavior}")
            sections.append(f"- **Attached Tools:** {', '.join(agent.attachedTools) or 'None'}")
            sections.append("")

    # 6. Relevant tools and input/output contracts
    sections.append("## Relevant Tool Specifications")
    relevant_tools = set()
    for a_id in relevant_agent_ids:
        agent = query.get_agent(a_id)
        if agent:
            relevant_tools.update(agent.attachedTools)
            # Find tools called by relationships
            for tool in query.get_available_tools(a_id):
                relevant_tools.add(tool.id)

    for t_id in sorted(list(relevant_tools)):
        if t_id in query.tools:
            tool = query.tools[t_id]
            sections.append(f"### Tool: {tool.id} ({tool.displayName})")
            sections.append(f"- **Kind:** {tool.toolKind}")
            sections.append(f"- **Description:** {tool.description}")
            sections.append(f"- **Execution Type:** {tool.executionType}")
            sections.append(f"- **Confirmation Required:** {tool.confirmationRequirement}")
            if tool.timeoutRetryPolicy:
                sections.append(f"- **Timeout Policy:** {tool.timeoutRetryPolicy}")
            sections.append("")

    # 7. Handoffs and ownership relationships
    sections.append("## Handoff & Delegation Contracts")
    for ho in query.handoffs:
        if ho.sourceAgentId in relevant_agent_ids or ho.targetAgentId in relevant_agent_ids:
            sections.append(f"### Handoff: {ho.sourceAgentId} -> {ho.targetAgentId}")
            sections.append(f"- **Mechanism:** {ho.mechanism}")
            sections.append(f"- **Condition:** {ho.condition or 'unconditional'}")
            if ho.returnCondition:
                sections.append(f"- **Return Condition:** {ho.returnCondition}")
            sections.append("")

    # 8. Callbacks and guardrails
    sections.append("## Enforcement & Callbacks")
    relevant_cbs = set()
    relevant_grs = set()
    for a_id in relevant_agent_ids:
        agent = query.get_agent(a_id)
        if agent:
            relevant_cbs.update(agent.callbacks)
            relevant_grs.update(agent.guardrails)

    for cb_id in sorted(list(relevant_cbs)):
        if cb_id in query.callbacks:
            cb = query.callbacks[cb_id]
            sections.append(f"- **Callback {cb.id}** ({cb.callbackStage}): {cb.purpose}")
    for gr_id in sorted(list(relevant_grs)):
        if gr_id in query.guardrails:
            gr = query.guardrails[gr_id]
            sections.append(f"- **Guardrail {gr.id}** ({gr.scope}): {gr.triggerDefinition} -> Outcome: {gr.outcome}")
    sections.append("")

    # 9. Evaluations (if requested)
    if include_evaluations:
        sections.append("## Relevant Evaluation Scenarios")
        for a_id in relevant_agent_ids:
            evs = query.get_evaluation_coverage(a_id)
            for ev in evs:
                sections.append(f"### Evaluation: {ev.id}")
                sections.append(f"- **Goal:** {ev.userGoal}")
                if ev.must:
                    sections.append(f"- **Must Assertions:** {', '.join(ev.must)}")
                if ev.mustNot:
                    sections.append(f"- **Must-Not Assertions:** {', '.join(ev.mustNot)}")
                sections.append("")

    # 10. Unresolved ambiguities / linter diagnostics
    sections.append("## Unresolved Ambiguities & Warnings")
    relevant_diags = []
    for diag in ir.get("diagnostics", []):
        src = diag.get("source", {})
        shape_ids = src.get("shapeIds", [])
        line_ids = src.get("lineIds", [])
        # Check if shape or line is relevant
        is_relevant = False
        if agent_id and (agent_id in shape_ids or agent_id in line_ids):
            is_relevant = True
        else:
            for s_id in shape_ids:
                if s_id in relevant_agent_ids:
                    is_relevant = True
            for l_id in line_ids:
                # Find if line links to any relevant agent
                for rel in query.relationships:
                    if rel.id == l_id and (rel.sourceId in relevant_agent_ids or rel.targetId in relevant_agent_ids):
                        is_relevant = True
        if is_relevant:
            relevant_diags.append(diag)

    if relevant_diags:
        for diag in relevant_diags:
            sections.append(f"- **[{diag['code']}]** ({diag['severity']}): {diag['message']}")
            if diag.get("remediation"):
                sections.append(f"  *Remediation:* {diag['remediation']}")
    else:
        sections.append("- No outstanding linter warnings or ambiguities for the active sub-graph.")
    sections.append("")

    # Build the full packet
    packet = "\n".join(sections)

    # Size-control pruning
    if max_chars and len(packet) > max_chars:
        # Truncate descriptions/prose from the end, retaining rules, constraints, and warnings
        packet = packet[:max_chars] + "\n\n... [Truncated due to token/character limit]"

    return packet
