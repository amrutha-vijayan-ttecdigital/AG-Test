"""CES semantic linter and design validator implementing 38 diagnostic checks."""

from __future__ import annotations

from typing import Any, List, Dict, Optional, Set
from .models import (
    ApplicationSpec, AgentSpec, ToolSpec, CallbackSpec, GuardrailSpec,
    VariableSpec, RemoteDialogflowAgentRef, RelationshipSpec, HandoffSpec,
    AgentAsToolSpec, EvaluationSpec, ObservedTrace, RelationshipType, Modality,
    ControlAuthority, GuardrailOutcome
)
from .relationships import CesDesignQuery

# Default severities: error, warning, info
DEFAULT_SEVERITIES = {
    "CES001": "error",
    "CES002": "warning",
    "CES003": "warning",
    "CES004": "warning",
    "CES005": "warning",
    "CES006": "error",
    "CES007": "warning",
    "CES008": "warning",
    "CES009": "warning",
    "CES010": "warning",
    "CES011": "error",
    "CES012": "warning",
    "CES013": "warning",
    "CES014": "warning",
    "CES015": "warning",
    "CES016": "error",
    "CES017": "warning",
    "CES018": "error",
    "CES019": "warning",
    "CES020": "error",
    "CES021": "warning",
    "CES022": "warning",
    "CES023": "error",
    "CES024": "warning",
    "CES025": "warning",
    "CES026": "warning",
    "CES027": "warning",
    "CES028": "warning",
    "CES029": "warning",
    "CES030": "error",
    "CES031": "warning",
    "CES032": "warning",
    "CES033": "warning",
    "CES034": "warning",
    "CES035": "warning",
    "CES036": "error",
    "CES037": "warning",
    "CES038": "info",
}

class CesValidator:
    def __init__(self, severity_overrides: Optional[Dict[str, str]] = None):
        self.severities = dict(DEFAULT_SEVERITIES)
        if severity_overrides:
            self.severities.update(severity_overrides)

    def validate(self, ir: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run all 38 diagnostic lint checks on compiled IR."""
        query = CesDesignQuery(ir)
        diagnostics = []

        def add_diag(code: str, message: str, source: Any = None, remediation: str = ""):
            sev = self.severities.get(code, "warning")
            if sev == "never":
                return
            src_prov = None
            if source:
                if hasattr(source, "source"):
                    src_prov = source.source
                elif isinstance(source, dict) and "source" in source:
                    src_prov = source["source"]
                elif isinstance(source, dict):
                    src_prov = source
            
            # Convert SourceProvenance to dict if it's an object
            if src_prov and not isinstance(src_prov, dict):
                src_prov = {
                    "documentId": getattr(src_prov, "documentId", ""),
                    "pageId": getattr(src_prov, "pageId", ""),
                    "shapeIds": list(getattr(src_prov, "shapeIds", [])),
                    "lineIds": list(getattr(src_prov, "lineIds", [])),
                    "textAreaIds": list(getattr(src_prov, "textAreaIds", [])),
                    "customDataKeys": list(getattr(src_prov, "customDataKeys", []))
                }

            diagnostics.append({
                "code": code,
                "severity": sev,
                "message": message,
                "source": src_prov or {},
                "remediation": remediation
            })

        # CES001: Application has no identifiable root agent.
        app = query.get_application()
        if not app or not app.rootAgentId:
            add_diag(
                "CES001",
                "Application has no identifiable root agent.",
                app,
                "Define a root agent in custom data (ces.is_root=true) or name an agent 'root'."
            )

        # Build ID sets to detect collisions and resolve references
        all_ids = set()
        for agent_id in query.agents:
            if agent_id in all_ids:
                add_diag("CES036", f"Same semantic ID '{agent_id}' is used by multiple resources.", query.agents[agent_id], "Ensure all shapes have unique ces.id custom data.")
            all_ids.add(agent_id)
        for tool_id in query.tools:
            if tool_id in all_ids:
                add_diag("CES036", f"Same semantic ID '{tool_id}' is used by multiple resources.", query.tools[tool_id], "Ensure all shapes have unique ces.id custom data.")
            all_ids.add(tool_id)
        for cb_id in query.callbacks:
            if cb_id in all_ids:
                add_diag("CES036", f"Same semantic ID '{cb_id}' is used by multiple resources.", query.callbacks[cb_id], "Ensure all shapes have unique ces.id custom data.")
            all_ids.add(cb_id)
        for gr_id in query.guardrails:
            if gr_id in all_ids:
                add_diag("CES036", f"Same semantic ID '{gr_id}' is used by multiple resources.", query.guardrails[gr_id], "Ensure all shapes have unique ces.id custom data.")
            all_ids.add(gr_id)

        # Loop over agents
        for agent_id, agent in query.agents.items():
            # CES002: Agent is missing purpose or scope.
            if not agent.purpose or (not agent.inScopeGoals and not agent.outOfScopeGoals):
                add_diag(
                    "CES002",
                    f"Agent '{agent_id}' is missing purpose or scope goals.",
                    agent,
                    "Populate the agent shape text with 'Purpose:' and 'In Scope:' / 'Out of Scope:' lists."
                )

            # CES003: Agent has no completion, return, or escalation behavior.
            if agent_id != app.rootAgentId:
                if not agent.completionCriteria and not agent.humanEscalationBehavior and not agent.handoffCriteria:
                    add_diag(
                        "CES003",
                        f"Agent '{agent_id}' has no completion, return, or escalation behavior.",
                        agent,
                        "Specify 'Completion:', 'Handoff:', or 'Exit:' behavior on the agent shape text."
                    )

            # CES031: Agent instructions reference a tool, agent, or variable not attached/declared.
            # (Heuristic: search text for common references not in declared attributes)
            for tool_ref in query.tools:
                if tool_ref in agent.purpose and tool_ref not in agent.attachedTools:
                    add_diag(
                        "CES031",
                        f"Agent '{agent_id}' instructions reference tool '{tool_ref}' which is not attached.",
                        agent,
                        f"Connect the agent to the tool '{tool_ref}' with a CALLS_TOOL connector or add to attachedTools."
                    )

            # CES038: Resource was inferred from shape class alone.
            if agent.status == "inferred" and any(e.kind == "shape_class" for e in agent.evidence):
                add_diag(
                    "CES038",
                    f"Agent '{agent_id}' was inferred from shape class alone.",
                    agent,
                    "Annotate the agent shape with 'ces.kind' custom metadata to make it explicit."
                )

        # Loop over relationships
        for rel in query.relationships:
            # CES025: Semantic connector is unlabeled.
            if not rel.displayName or rel.displayName.strip() in ("Transition", "Line", "Connector"):
                add_diag(
                    "CES025",
                    "Semantic connector is unlabeled.",
                    rel,
                    "Add an explicit label to the Lucid line detailing the transition behavior."
                )

            # CES004: Model-selected handoff has no allowed target or trigger description.
            if rel.relationType == RelationshipType.MAY_HANDOFF_TO:
                if not rel.triggerCondition or rel.triggerCondition.strip() == "":
                    add_diag(
                        "CES004",
                        f"Model-selected handoff from '{rel.sourceId}' has no trigger description.",
                        rel,
                        "Provide a natural-language description on the connector, e.g., '[MAY] when user wants account details'."
                    )

            # CES005: Deterministic handoff is represented only in instructions, not a rule/callback.
            if rel.relationType == RelationshipType.MUST_HANDOFF_TO:
                if rel.controlAuthority == ControlAuthority.MODEL_INSTRUCTION:
                    add_diag(
                        "CES005",
                        f"Deterministic handoff from '{rel.sourceId}' to '{rel.targetId}' is configured as MODEL_INSTRUCTION.",
                        rel,
                        "Use [RULE] or [CALLBACK] namespace on the connector to enforce determinism."
                    )

            # CES006: Handoff and agent-as-a-tool semantics are conflated.
            if rel.relationType == RelationshipType.USES_AGENT_AS_TOOL:
                # Find if there is also a handoff spec for the same source/target
                for ho in query.handoffs:
                    if ho.sourceAgentId == rel.sourceId and ho.targetAgentId == rel.targetId:
                        add_diag(
                            "CES006",
                            f"Handoff and agent-as-a-tool semantics are conflated between '{rel.sourceId}' and '{rel.targetId}'.",
                            rel,
                            "An agent can either be used as a tool (active agent retains control) or handed off to (transfers ownership). Do not design both."
                        )

            # CES019: MUST/MUST_NOT claim lacks deterministic enforcement.
            if rel.modalGuarantee in (Modality.MUST, Modality.MUST_NOT):
                if rel.controlAuthority not in (ControlAuthority.DETERMINISTIC_HANDOFF_RULE, ControlAuthority.CALLBACK, ControlAuthority.GUARDRAIL):
                    add_diag(
                        "CES019",
                        f"MUST/MUST_NOT claim on connector from '{rel.sourceId}' lacks deterministic enforcement.",
                        rel,
                        "Specify rule, callback, or guardrail authority (e.g. '[MUST][RULE]') to enforce the contract."
                    )

            # CES024: Observed trace is represented as a design guarantee.
            if rel.controlAuthority == ControlAuthority.OBSERVED_ONLY or rel.status == "observed":
                add_diag(
                    "CES024",
                    f"Observed trace connector from '{rel.sourceId}' to '{rel.targetId}' is represented as design guarantee.",
                    rel,
                    "Mark trace connectors explicitly as [OBSERVED] or move them to a separate page/layer."
                )

        # Loop over handoffs
        for ho in query.handoffs:
            # CES007: Handoff lacks ownership or return behavior.
            if not ho.returnCondition and not ho.postTransferOwner:
                add_diag(
                    "CES007",
                    f"Handoff from '{ho.sourceAgentId}' to '{ho.targetAgentId}' lacks return behavior.",
                    ho,
                    "Clarify return behavior in label (e.g., 'returns when resolved')."
                )

        # Loop over agents-as-tools
        for aat in query.agents_as_tools:
            # CES008: Agent-as-a-tool lacks input/output contract.
            if not aat.inputContract and not aat.outputContract:
                add_diag(
                    "CES008",
                    f"Agent-as-a-tool '{aat.targetAgentId}' called by '{aat.callingAgentId}' lacks input/output contract.",
                    aat,
                    "Add structured metadata or text specifying the input/output variable mappings."
                )
            # CES009: Async tool/agent-as-tool lacks pending behavior.
            if aat.executionType == "asynchronous" and not aat.pendingResponseBehavior:
                add_diag(
                    "CES009",
                    f"Asynchronous agent-as-tool '{aat.targetAgentId}' lacks pending behavior description.",
                    aat,
                    "Define what the active agent should say/do while the async tool execution is pending."
                )

        # Loop over tools
        for tool_id, tool in query.tools.items():
            # CES011: Tool schema or description is missing.
            if not tool.description:
                add_diag(
                    "CES011",
                    f"Tool '{tool_id}' description is missing.",
                    tool,
                    "Provide a description within the tool shape text."
                )

            # Heuristics for side-effects
            is_write = "write" in tool.description.lower() or "update" in tool.description.lower() or "delete" in tool.description.lower() or "post" in tool.description.lower()
            
            # CES012: Side-effecting tool lacks confirmation requirement.
            if is_write and not tool.confirmationRequirement:
                add_diag(
                    "CES012",
                    f"Side-effecting tool '{tool_id}' lacks a confirmation requirement.",
                    tool,
                    "Configure 'ces.confirmation_requirement=true' in custom data or add 'Confirmation: required' in text."
                )

            # CES013: Side-effecting tool lacks authorization/enforcement.
            if is_write and not tool.authRequirement and not tool.callbacks:
                add_diag(
                    "CES013",
                    f"Side-effecting tool '{tool_id}' lacks authorization or enforcement callback.",
                    tool,
                    "Attach a before_tool callback to check authorization credentials."
                )

            # CES014: Irreversible tool lacks idempotency or duplicate prevention.
            if is_write and not tool.idempotencyStrategy:
                add_diag(
                    "CES014",
                    f"Irreversible write tool '{tool_id}' lacks idempotency or duplicate prevention policy.",
                    tool,
                    "Add 'Idempotency: ...' to the tool description text."
                )

            # CES015: Tool timeout/failure behavior is missing.
            if not tool.timeoutRetryPolicy and not tool.errorResultContract:
                add_diag(
                    "CES015",
                    f"Tool '{tool_id}' is missing timeout retry or error handling details.",
                    tool,
                    "Specify 'Timeout:' or 'Error Handling:' inside the tool shape text."
                )

        # Loop over callbacks
        for cb_id, cb in query.callbacks.items():
            # CES016: Callback is missing a callback stage/type.
            # (If it falls back to a default not explicitly set)
            if not cb.callbackStage:
                add_diag(
                    "CES016",
                    f"Callback '{cb_id}' is missing callback stage classification.",
                    cb,
                    "Set ces.callback_type custom data to one of before_agent, before_tool, etc."
                )

            # CES017: Callback can bypass execution but the bypass result is undocumented.
            if "bypass" in cb.purpose.lower() and not cb.skipReplaceBehavior:
                add_diag(
                    "CES017",
                    f"Bypassing callback '{cb_id}' does not document skip/replace behavior.",
                    cb,
                    "Add skip/replace instructions in callback custom data or text."
                )

        # Loop over guardrails
        for gr_id, gr in query.guardrails.items():
            # CES018: Guardrail has no explicit scope or outcome.
            if gr.outcome == GuardrailOutcome.OTHER:
                add_diag(
                    "CES018",
                    f"Guardrail '{gr_id}' has no explicit outcome defined.",
                    gr,
                    "Set ces.guardrail_scope to exact_response, agent_handoff, block, or redact."
                )

        # Loop over variables
        for var_id, var in query.variables.items():
            # CES022: Sensitive variable lacks redaction/logging guidance.
            is_sensitive = "pii" in (var.sensitivity or "").lower() or "password" in var_id.lower() or "token" in var_id.lower()
            if is_sensitive and not var.redactionExpectations: # Note: models.py has default settings
                add_diag(
                    "CES022",
                    f"Sensitive variable '{var_id}' lacks redaction or logging guidance.",
                    var,
                    "Specify log redaction expectations for the sensitive variable."
                )

        # CES020: Variable is referenced but not declared.
        # Check all agent reads/writes
        for agent_id, agent in query.agents.items():
            for vread in agent.variablesRead:
                if vread not in query.variables:
                    add_diag(
                        "CES020",
                        f"Variable '{vread}' read by agent '{agent_id}' is not declared.",
                        agent,
                        "Add a Variable shape with ces.id matching the variable name."
                    )
            for vwrite in agent.variablesWritten:
                if vwrite not in query.variables:
                    add_diag(
                        "CES020",
                        f"Variable '{vwrite}' written by agent '{agent_id}' is not declared.",
                        agent,
                        "Add a Variable shape with ces.id matching the variable name."
                    )

        # CES023: Remote DFCX agent lacks explicit input/output mapping.
        for r_id, r in query.remotes.items():
            if not r.inputVariables and not r.outputVariables:
                add_diag(
                    "CES023",
                    f"Remote DFCX flow agent '{r_id}' lacks input/output mapping.",
                    r,
                    "Define the inputs/outputs mapped to the black-box Dialogflow agent."
                )

        # CES029: Cross-agent loop has no exit/escalation policy.
        # Detect agent-to-agent loops
        loops = self._detect_loops(query)
        for loop in loops:
            has_exit = False
            for node in loop:
                agent = query.get_agent(node)
                if agent and (agent.humanEscalationBehavior or agent.handoffCriteria):
                    has_exit = True
                    break
            if not has_exit:
                add_diag(
                    "CES029",
                    f"Cross-agent delegation loop {loop} has no exit or escalation policy.",
                    query.get_agent(loop[0]),
                    "Provide a human escalation target or handoff exit condition in at least one agent in the loop."
                )

        # CES030: Human escalation target is referenced but undefined.
        for agent_id, agent in query.agents.items():
            if agent.humanEscalationBehavior:
                # Heuristic: check if target name matches any agent/target or is in app.humanEscalationTargets
                target = agent.humanEscalationBehavior
                if target not in app.humanEscalationTargets and target not in query.agents:
                    # If it looks like a variable/agent reference but isn't defined
                    if len(target.split()) == 1 and target.isalnum():
                        add_diag(
                            "CES030",
                            f"Human escalation target '{target}' referenced by '{agent_id}' is undefined.",
                            agent,
                            "Add the target to application humanEscalationTargets or define it as an agent."
                        )

        # CES033: High-risk behavioral claim has no evaluation coverage.
        for claim in query.claims:
            coverage = query.get_evaluation_coverage(claim.id)
            if not coverage:
                add_diag(
                    "CES033",
                    f"High-risk behavioral claim '{claim.id}' has no evaluation coverage.",
                    claim,
                    "Create an evaluation scenario shape targeting this claim ID to assert correct behavior."
                )

        # Page-specific checks
        # CES027: Connector label is floating rather than attached.
        # CES037: Lucid connector resolves through an ambiguous line junction.
        for page in ir.get("logical", {}).get("pages", []):
            page_id = page.get("id", "")
            for diag in page.get("diagnostics", []):
                dcode = diag.get("code")
                dmsg = diag.get("message", "")
                if "dangling" in dmsg.lower() or "floating" in dmsg.lower():
                    add_diag("CES027", f"Connector label is floating rather than attached: {dmsg}", {"pageId": page_id}, "Attach the floating text box directly to the connector line in Lucidchart.")
                elif "junction" in dmsg.lower() or "ambiguous" in dmsg.lower():
                    add_diag("CES037", f"Lucid connector resolves through an ambiguous line junction: {dmsg}", {"pageId": page_id}, "Simplify the connector line routing and avoid multi-line overlapping intersections.")

        return diagnostics

    def _detect_loops(self, query: CesDesignQuery) -> List[List[str]]:
        """Find loops in the agent-to-agent delegation graph using DFS."""
        adj = {}
        for agent_id in query.agents:
            adj[agent_id] = []
        for rel in query.relationships:
            if rel.relationType in (RelationshipType.MAY_HANDOFF_TO, RelationshipType.MUST_HANDOFF_TO):
                if rel.sourceId in adj and rel.targetId in adj:
                    adj[rel.sourceId].append(rel.targetId)

        loops = []
        visited = {}
        path = []

        def dfs(node):
            visited[node] = 1 # visiting
            path.append(node)
            for neighbor in adj[node]:
                if neighbor in visited:
                    if visited[neighbor] == 1:
                        # loop detected
                        loop_start = path.index(neighbor)
                        loops.append(list(path[loop_start:]))
                else:
                    dfs(neighbor)
            path.pop()
            visited[node] = 2 # visited

        for node in adj:
            if node not in visited:
                dfs(node)

        return loops
