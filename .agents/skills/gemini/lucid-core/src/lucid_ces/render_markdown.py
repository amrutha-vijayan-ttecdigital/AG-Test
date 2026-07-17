"""Generate a structured Markdown report from the CES semantic IR."""

from __future__ import annotations

from typing import Any, Dict, List
from .relationships import CesDesignQuery
from .models import RelationshipType, Modality

def render_markdown_report(ir: Dict[str, Any]) -> str:
    """Render a comprehensive CES design specification report in Markdown."""
    query = CesDesignQuery(ir)
    app = query.get_application()

    lines = []
    lines.append(f"# CES Agent Studio Design Specification Report")
    lines.append(f"*(Version: {ir.get('schemaVersion', 'unknown')} | Document Title: {app.displayName})*")
    lines.append("")

    # 1. Application Overview
    lines.append("## 1. Application Overview")
    lines.append(f"- **Application ID:** {app.id}")
    lines.append(f"- **Display Name:** {app.displayName}")
    lines.append(f"- **Root Agent ID:** {app.rootAgentId or 'None'}")
    lines.append(f"- **Language/Locale:** {app.languageLocale or 'Not specified'}")
    lines.append(f"- **Tool Execution Mode:** {app.toolExecutionMode}")
    if app.channelProfiles:
        lines.append(f"- **Channel Profiles:** {', '.join(app.channelProfiles)}")
    lines.append("")

    # 2. Agent Hierarchy and Ownership
    lines.append("## 2. Agent Hierarchy and Delegation")
    lines.append("This section lists all LLM agents and human escalation targets designed in this application.")
    lines.append("")
    
    # Simple hierarchy tree helper
    def render_tree(agent_id: str, depth: int = 0):
        agent = query.get_agent(agent_id)
        if not agent:
            return
        indent = "  " * depth
        lines.append(f"{indent}- **{agent.id}** ({agent.displayName}) - *{agent.kind}*")
        for child_id in agent.childAgentIds:
            render_tree(child_id, depth + 1)

    if app.rootAgentId:
        render_tree(app.rootAgentId)
    else:
        for agent_id, agent in query.agents.items():
            if not agent.parentAgentId:
                render_tree(agent_id)
    lines.append("")

    # 3. Per-Agent Purpose and Scope
    lines.append("## 3. Per-Agent Purpose and Scope")
    for agent_id, agent in query.agents.items():
        lines.append(f"### Agent: {agent.id} ({agent.displayName})")
        lines.append(f"- **Purpose:** {agent.purpose or 'Not specified'}")
        if agent.inScopeGoals:
            lines.append("- **In-Scope Goals:**")
            for goal in agent.inScopeGoals:
                lines.append(f"  - {goal}")
        if agent.outOfScopeGoals:
            lines.append("- **Out-of-Scope Goals:**")
            for goal in agent.outOfScopeGoals:
                lines.append(f"  - {goal}")
        if agent.responsibilities:
            lines.append("- **Responsibilities:**")
            for resp in agent.responsibilities:
                lines.append(f"  - {resp}")
        if agent.completionCriteria:
            lines.append("- **Completion & Handoff Criteria:**")
            for comp in agent.completionCriteria:
                lines.append(f"  - {comp}")
        lines.append("")

    # 4. MUST/MAY/MUST NOT Behavioral Contracts
    lines.append("## 4. Behavioral Contracts & Rules")
    lines.append("The table below documents explicit behavioral claims and constraints derived from the design graph.")
    lines.append("")
    lines.append("| Subject ID | Modality | Behavioral Contract (Predicate) | Enforced By | Authority |")
    lines.append("|---|---|---|---|---|")
    
    # Extract behavioral claims from claims list or relationships
    has_claims = False
    for claim in query.claims:
        lines.append(f"| {claim.subjectId} | **{claim.modality}** | {claim.predicate} | {claim.enforcementResourceId or 'N/A'} | {claim.enforcementAuthority or 'Instruction'} |")
        has_claims = True

    # Also extract MUST/MUST_NOT from relationships
    for rel in query.relationships:
        if rel.modalGuarantee in (Modality.MUST, Modality.MUST_NOT):
            lines.append(f"| {rel.sourceId} -> {rel.targetId} | **{rel.modalGuarantee}** | {rel.triggerCondition or 'Transition'} | {rel.id} | {rel.controlAuthority} |")
            has_claims = True

    if not has_claims:
        lines.append("| N/A | N/A | No explicit MUST/MUST_NOT contracts found. | N/A | N/A |")
    lines.append("")

    # 5. Handoffs vs Agents-as-Tools
    lines.append("## 5. Handoffs and Agents-as-Tools")
    lines.append("Conversational flows partition conversation ownership transfers (Handoffs) from auxiliary capabilities (Agents-as-Tools).")
    lines.append("")
    lines.append("### Handoffs (Conversation Ownership Transfers)")
    if query.handoffs:
        for ho in query.handoffs:
            lines.append(f"- **{ho.sourceAgentId}** hands off to **{ho.targetAgentId}** via *{ho.mechanism}*.")
            if ho.condition:
                lines.append(f"  - *Condition:* {ho.condition}")
            if ho.returnCondition:
                lines.append(f"  - *Return Condition:* {ho.returnCondition}")
    else:
        lines.append("- No handoffs designed.")
    lines.append("")

    lines.append("### Agents-as-Tools (Auxiliary Capabilities)")
    if query.agents_as_tools:
        for aat in query.agents_as_tools:
            lines.append(f"- **{aat.callingAgentId}** invokes **{aat.targetAgentId}** as a tool ({aat.executionType or 'synchronous'}).")
            if aat.pendingResponseBehavior:
                lines.append(f"  - *Pending Behavior:* {aat.pendingResponseBehavior}")
    else:
        lines.append("- No agent-as-tool relationships designed.")
    lines.append("")

    # 6. Tools and Side-Effect Controls
    lines.append("## 6. Tools and Side-Effect Controls")
    if query.tools:
        for tool_id, tool in query.tools.items():
            lines.append(f"### Tool: {tool_id} ({tool.displayName})")
            lines.append(f"- **Kind:** {tool.toolKind}")
            lines.append(f"- **Execution Type:** {tool.executionType}")
            lines.append(f"- **Confirmation Required:** {tool.confirmationRequirement}")
            lines.append(f"- **Description:** {tool.description or 'No description'}")
            if tool.timeoutRetryPolicy:
                lines.append(f"- **Retry Policy:** {tool.timeoutRetryPolicy}")
            if tool.idempotencyStrategy:
                lines.append(f"- **Idempotency Strategy:** {tool.idempotencyStrategy}")
            lines.append("")
    else:
        lines.append("- No tools designed.")
    lines.append("")

    # 7. Callbacks and Guardrails
    lines.append("## 7. Callbacks and Guardrails")
    lines.append("### Callbacks")
    if query.callbacks:
        for cb_id, cb in query.callbacks.items():
            lines.append(f"- **{cb.id}** ({cb.callbackStage}): {cb.purpose}")
    else:
        lines.append("- No callbacks designed.")
    lines.append("")

    lines.append("### Guardrails")
    if query.guardrails:
        for gr_id, gr in query.guardrails.items():
            lines.append(f"- **{gr.id}** ({gr.scope}): {gr.triggerDefinition} -> Outcome: {gr.outcome}")
    else:
        lines.append("- No guardrails designed.")
    lines.append("")

    # 8. Variables and Data Contracts
    lines.append("## 8. Variables and Data Contracts")
    if query.variables:
        lines.append("| Variable Name | Type | Classification | Owner Agent | Sensitivity |")
        lines.append("|---|---|---|---|---|")
        for var_id, var in query.variables.items():
            lines.append(f"| {var.id} | {var.type} | {var.classification} | {var.ownerAgentId or 'Global'} | {var.sensitivity or 'Public'} |")
    else:
        lines.append("- No variables designed.")
    lines.append("")

    # 9. Remote Dialogflow Flows (Black Boxes)
    lines.append("## 9. Dialogflow CX Remote Agent Integration")
    if query.remotes:
        for r_id, r in query.remotes.items():
            lines.append(f"### Remote Agent Reference: {r_id}")
            lines.append(f"- **Target Resource:** {r.remoteAgentResource}")
            if r.inputVariables:
                lines.append(f"- **Input Variables:** {', '.join(r.inputVariables)}")
            if r.outputVariables:
                lines.append(f"- **Output Variables:** {', '.join(r.outputVariables)}")
            lines.append("")
    else:
        lines.append("- No remote DFCX agents designed.")
    lines.append("")

    # 10. Channel Behavior
    lines.append("## 10. Channel Behavior")
    lines.append("- Channel profiles and interactive options are configured at the application level.")
    lines.append("")

    # 11. Evaluation Coverage
    lines.append("## 11. Evaluation Coverage")
    if query.evaluations:
        for ev_id, ev in query.evaluations.items():
            lines.append(f"### Evaluation Spec: {ev_id}")
            lines.append(f"- **Goal:** {ev.userGoal}")
            lines.append(f"- **Must Assertions:** {', '.join(ev.must) or 'None'}")
            lines.append(f"- **Must Not Assertions:** {', '.join(ev.mustNot) or 'None'}")
            lines.append("")
    else:
        lines.append("- No evaluation specifications designed.")
    lines.append("")

    # 12. Ambiguities and Lint Findings
    lines.append("## 12. Linter Diagnostics & Ambiguities")
    diags = ir.get("diagnostics", [])
    if diags:
        lines.append("| Code | Severity | Message | Remediation |")
        lines.append("|---|---|---|---|")
        for diag in diags:
            lines.append(f"| {diag.get('code', 'N/A')} | {diag.get('severity', 'warning')} | {diag.get('message')} | {diag.get('remediation', '')} |")
    else:
        lines.append("- No lint diagnostics or ambiguities found.")
    lines.append("")

    # 13. Provenance Appendix
    lines.append("## 13. Provenance Appendix")
    lines.append("This appendix links semantic elements back to their source shapes/lines inside the Lucid chart document.")
    lines.append("")
    for agent_id, agent in query.agents.items():
        lines.append(f"- **Agent '{agent_id}':** Page ID: {agent.source.pageId}, Shape IDs: {', '.join(agent.source.shapeIds)}")
    for tool_id, tool in query.tools.items():
        lines.append(f"- **Tool '{tool_id}':** Page ID: {tool.source.pageId}, Shape IDs: {', '.join(tool.source.shapeIds)}")
    for rel in query.relationships:
        lines.append(f"- **Relationship '{rel.sourceId} -> {rel.targetId}':** Page ID: {rel.source.pageId}, Line IDs: {', '.join(rel.source.lineIds)}")
    lines.append("")

    return "\n".join(lines)
