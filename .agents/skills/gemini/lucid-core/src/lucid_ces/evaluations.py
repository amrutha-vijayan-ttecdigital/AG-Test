"""Generate internal evaluation specifications from behavioral claims and contracts."""

from __future__ import annotations

from typing import Any, Dict, List
from .relationships import CesDesignQuery
from .models import EvaluationSpec, RelationshipType, Modality, SourceProvenance

def generate_eval_specs_from_design(ir: Dict[str, Any]) -> List[EvaluationSpec]:
    """Compile design-level behavioral claims and relationships into evaluation specs."""
    query = CesDesignQuery(ir)
    evals = []
    
    # 1. Map existing designed evaluations in IR
    for ev in query.evaluations.values():
        evals.append(ev)

    # 2. Synthesize evaluations for side-effecting tools with confirmation/auth
    for tool_id, tool in query.tools.items():
        if tool.confirmationRequirement:
            # Create a test case confirming confirmation is enforced
            eval_id = f"eval-confirm-enforcement-{tool_id}"
            evals.append(EvaluationSpec(
                id=eval_id,
                displayName=f"Confirmation enforcement check for tool: {tool_id}",
                description=f"Asserts that {tool_id} cannot be called without prior user confirmation.",
                source=SourceProvenance(pageId=tool.source.pageId, shapeIds=[tool_id]),
                startingAgentId=query.application.rootAgentId or "root",
                userGoal=f"invoke write tool {tool_id}",
                must=[
                    f"obtain confirmation before calling {tool_id}",
                ],
                mustNot=[
                    f"call {tool_id} without confirmation",
                ],
                expectedToolCalls=[{"toolId": tool_id, "requiredConfirmation": True}],
                runMode="golden"
            ))

    # 3. Synthesize evaluations for MUST NOT / forbidden transitions
    for rel in query.relationships:
        if rel.relationType == RelationshipType.FORBIDDEN_TRANSITION or rel.modalGuarantee == Modality.MUST_NOT:
            eval_id = f"eval-forbidden-transition-{rel.sourceId}-to-{rel.targetId}"
            evals.append(EvaluationSpec(
                id=eval_id,
                displayName=f"Forbidden path prevention: {rel.sourceId} -> {rel.targetId}",
                description=f"Ensures that conversation never delegates from {rel.sourceId} to {rel.targetId}.",
                source=rel.source,
                startingAgentId=rel.sourceId,
                userGoal="trigger transfer or transition",
                mustNot=[
                    f"handoff to {rel.targetId}",
                    f"transition from {rel.sourceId} to {rel.targetId}"
                ],
                expectedHandoffs=[],
                runMode="scenario"
            ))

    # 4. Synthesize evaluations for remote DFCX flow agents variable mappings
    for r_id, remote in query.remotes.items():
        if remote.inputVariables or remote.outputVariables:
            eval_id = f"eval-remote-mapping-{r_id}"
            evals.append(EvaluationSpec(
                id=eval_id,
                displayName=f"Remote DFCX agent I/O contract check: {r_id}",
                description=f"Verifies input/output variable mappings when delegating to DFCX flow {r_id}.",
                source=remote.source,
                startingAgentId=query.application.rootAgentId or "root",
                userGoal="delegate to remote DFCX flow",
                must=[
                    f"map inputs {remote.inputVariables} before invocation",
                    f"receive outputs {remote.outputVariables} after return"
                ],
                runMode="golden"
            ))

    return evals

def render_evals_mapping_guide(evals: List[EvaluationSpec]) -> str:
    """Render a Markdown mapping guide mapping the internal specs to CES test concepts."""
    lines = []
    lines.append("# CES Evaluation Specification & Mapping Guide")
    lines.append("")
    lines.append("This document maps the compiler-generated internal evaluation contracts to native Google CX Agent Studio testing concepts.")
    lines.append("")
    
    if not evals:
        lines.append("- No evaluation specs generated.")
        return "\n".join(lines)
        
    for ev in evals:
        lines.append(f"## Evaluation ID: {ev.id}")
        lines.append(f"- **Description:** {ev.description}")
        lines.append(f"- **Starting Point:** Agent `{ev.startingAgentId}`")
        lines.append(f"- **User Goal:** {ev.userGoal}")
        lines.append(f"- **Expected Invariants (MUST):**")
        for m in ev.must:
            lines.append(f"  - {m}")
        if not ev.must:
            lines.append("  - None specified")
        lines.append(f"- **Prohibitions (MUST NOT):**")
        for mn in ev.mustNot:
            lines.append(f"  - {mn}")
        if not ev.mustNot:
            lines.append("  - None specified")
            
        lines.append("")
        lines.append("### Mapping to Google CX Agent Studio Simulator/Test Cases:")
        lines.append("1. **Simulator Scenario Test:**")
        lines.append(f"   - Set the starting agent to **{ev.startingAgentId}**.")
        lines.append(f"   - Input user utterance matching goal: *\"{ev.userGoal}\"*.")
        if ev.mustNot:
            lines.append("   - **Assertions:** Verify that none of the following occurred:")
            for mn in ev.mustNot:
                lines.append(f"     * Violation check: `{mn}`")
        lines.append("")
        
    return "\n".join(lines)
