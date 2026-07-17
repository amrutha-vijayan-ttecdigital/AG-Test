"""Semantic relationship and ownership tracking queries for CES designs."""

from __future__ import annotations

from typing import Any, List, Dict, Optional, Set
from .models import (
    ApplicationSpec, AgentSpec, ToolSpec, CallbackSpec, GuardrailSpec,
    VariableSpec, RemoteDialogflowAgentRef, RelationshipSpec, HandoffSpec,
    AgentAsToolSpec, EvaluationSpec, ObservedTrace, RelationshipType, Modality,
    ControlAuthority, AsyncState
)

class CesDesignQuery:
    def __init__(self, ir: Dict[str, Any]):
        self.ir = ir
        from .serialization import from_dict
        
        self.application = ir.get("application")
        if isinstance(self.application, dict):
            self.application = from_dict(ApplicationSpec, self.application)
            
        self.agents = {}
        for a in ir.get("agents", []) or []:
            if isinstance(a, dict):
                a = from_dict(AgentSpec, a)
            self.agents[a.id] = a

        self.tools = {}
        for t in ir.get("tools", []) or []:
            if isinstance(t, dict):
                t = from_dict(ToolSpec, t)
            self.tools[t.id] = t

        self.callbacks = {}
        for c in ir.get("callbacks", []) or []:
            if isinstance(c, dict):
                c = from_dict(CallbackSpec, c)
            self.callbacks[c.id] = c

        self.guardrails = {}
        for g in ir.get("guardrails", []) or []:
            if isinstance(g, dict):
                g = from_dict(GuardrailSpec, g)
            self.guardrails[g.id] = g

        self.variables = {}
        for v in ir.get("variables", []) or []:
            if isinstance(v, dict):
                v = from_dict(VariableSpec, v)
            self.variables[v.id] = v

        self.remotes = {}
        for r in ir.get("remotes", []) or []:
            if isinstance(r, dict):
                r = from_dict(RemoteDialogflowAgentRef, r)
            self.remotes[r.id] = r

        self.evaluations = {}
        for e in ir.get("evaluations", []) or []:
            if isinstance(e, dict):
                e = from_dict(EvaluationSpec, e)
            self.evaluations[e.id] = e

        self.traces = {}
        for t in ir.get("traces", []) or []:
            if isinstance(t, dict):
                t = from_dict(ObservedTrace, t)
            self.traces[t.id] = t

        self.relationships = []
        for rel in ir.get("relationships", []) or []:
            if isinstance(rel, dict):
                rel = from_dict(RelationshipSpec, rel)
            self.relationships.append(rel)

        self.handoffs = []
        for ho in ir.get("handoffs", []) or []:
            if isinstance(ho, dict):
                ho = from_dict(HandoffSpec, ho)
            self.handoffs.append(ho)

        self.agents_as_tools = []
        for aat in ir.get("agentsAsTools", []) or []:
            if isinstance(aat, dict):
                aat = from_dict(AgentAsToolSpec, aat)
            self.agents_as_tools.append(aat)

        raw_claims = ir.get("behavioralClaims", []) or ir.get("claims", []) or []
        self.claims = []
        for claim in raw_claims:
            if isinstance(claim, dict):
                from .models import BehavioralClaim
                claim = from_dict(BehavioralClaim, claim)
            self.claims.append(claim)

    def get_application(self) -> ApplicationSpec:
        return self.application

    def get_agent(self, agent_id: str) -> Optional[AgentSpec]:
        return self.agents.get(agent_id)

    def get_children(self, agent_id: str) -> List[AgentSpec]:
        agent = self.get_agent(agent_id)
        if not agent:
            return []
        return [self.agents[cid] for cid in agent.childAgentIds if cid in self.agents]

    def get_possible_handoffs(self, agent_id: str) -> List[HandoffSpec]:
        """Returns handoffs where agent_id is the source and modality is MAY or MUST."""
        return [h for h in self.handoffs if h.sourceAgentId == agent_id]

    def get_required_handoffs(self, agent_id: str) -> List[HandoffSpec]:
        """Returns handoffs where agent_id is the source and modality/direction is MUST/forced."""
        req = []
        for h in self.handoffs:
            if h.sourceAgentId == agent_id:
                # Find corresponding relationship to check modality
                rel = self._find_relationship(h.sourceAgentId, h.targetAgentId)
                if (rel and rel.modalGuarantee == Modality.MUST) or h.direction == "must" or h.mechanism == "deterministic_handoff_rule":
                    req.append(h)
        return req

    def get_forbidden_handoffs(self, agent_id: str) -> List[RelationshipSpec]:
        """Returns relationships representing forbidden transitions from agent_id."""
        return [
            rel for rel in self.relationships
            if rel.sourceId == agent_id and (
                rel.relationType == RelationshipType.FORBIDDEN_TRANSITION or
                rel.modalGuarantee == Modality.MUST_NOT
            )
        ]

    def get_available_tools(self, agent_id: str) -> List[ToolSpec]:
        """Get tools attached to agent or connected via CALLS_TOOL relationship."""
        tool_ids = set()
        agent = self.get_agent(agent_id)
        if agent:
            tool_ids.update(agent.attachedTools)
        for rel in self.relationships:
            if rel.sourceId == agent_id and rel.relationType == RelationshipType.CALLS_TOOL:
                tool_ids.add(rel.targetId)
        return [self.tools[tid] for tid in tool_ids if tid in self.tools]

    def get_agents_as_tools(self, agent_id: str) -> List[AgentAsToolSpec]:
        return [a for a in self.agents_as_tools if a.callingAgentId == agent_id]

    def get_required_controls(self, resource_id: str) -> List[BaseResource]:
        """Find callbacks, guardrails, or handoff rules that guard/enforce/control a resource."""
        controls = []
        for rel in self.relationships:
            if rel.targetId == resource_id:
                if rel.relationType in (RelationshipType.ENFORCED_BY, RelationshipType.GUARDED_BY):
                    ctrl_id = rel.sourceId
                    if ctrl_id in self.callbacks:
                        controls.append(self.callbacks[ctrl_id])
                    elif ctrl_id in self.guardrails:
                        controls.append(self.guardrails[ctrl_id])
        return controls

    def get_behavioral_claims(self, resource_id: str) -> List[Any]:
        return [c for c in self.claims if c.subjectId == resource_id]

    def get_variable_contract(self, name: str) -> Optional[VariableSpec]:
        return self.variables.get(name)

    def get_evaluation_coverage(self, resource_id: str) -> List[EvaluationSpec]:
        coverage = []
        for ev in self.evaluations.values():
            # If the description references the ID, or startingAgentId matches
            if (resource_id in ev.id or
                resource_id in ev.description or
                ev.startingAgentId == resource_id or
                any(resource_id in m for m in ev.must) or
                any(resource_id in m for m in ev.may) or
                any(resource_id in mn for mn in ev.mustNot)):
                coverage.append(ev)
        return coverage

    def get_policy_subgraph(self, agent_id: str, depth: int = 2) -> Dict[str, Any]:
        """Find sub-graph of agents and connections starting from agent_id up to a depth."""
        visited_nodes = {agent_id}
        queue = [(agent_id, 0)]
        edges = []

        while queue:
            curr, curr_depth = queue.pop(0)
            if curr_depth >= depth:
                continue
            for rel in self.relationships:
                if rel.sourceId == curr:
                    edges.append(rel)
                    target = rel.targetId
                    if target not in visited_nodes:
                        visited_nodes.add(target)
                        queue.append((target, curr_depth + 1))

        return {
            "nodes": list(visited_nodes),
            "edges": edges
        }

    def get_unresolved_ambiguities(self, page_id: str) -> List[Dict[str, Any]]:
        """Return diagnostic messages that indicate ambiguities for the given page."""
        ambiguities = []
        for diag in self.ir.get("diagnostics", []):
            prov = diag.get("source", {})
            if prov.get("pageId") == page_id or page_id in prov.get("pageId", ""):
                if diag.get("severity") in ("warning", "error"):
                    ambiguities.append(diag)
        return ambiguities

    def _find_relationship(self, src: str, dst: str) -> Optional[RelationshipSpec]:
        for rel in self.relationships:
            if rel.sourceId == src and rel.targetId == dst:
                return rel
        return None

    def construct_possible_trajectory(self, start_agent_id: str, goals: List[str]) -> List[Dict[str, Any]]:
        """
        Synthesize a potential nondeterministic conversation/task trajectory trace.
        Tracks conversation ownership, capabilities used, and returns steps.
        """
        steps = []
        current_owner = start_agent_id
        visited = set()
        
        steps.append({
            "step": 0,
            "owner": current_owner,
            "action": "ACTIVATE",
            "ownership": "retain",
            "description": f"Root agent {current_owner} starts conversation."
        })
        
        # Simple simulation based on goals and connections
        step_count = 1
        for goal in goals:
            # Look for handoffs matching this goal
            transferred = False
            for handoff in self.get_possible_handoffs(current_owner):
                if goal.lower() in handoff.condition.lower() or not handoff.condition:
                    target = handoff.targetAgentId
                    # It's a handoff -> ownership transfers
                    steps.append({
                        "step": step_count,
                        "owner": target,
                        "action": f"HANDOFF TO {target}",
                        "ownership": "transfer",
                        "description": f"Conversation ownership transfers from {current_owner} to {target} on condition: {handoff.condition or 'none'}."
                    })
                    step_count += 1
                    current_owner = target
                    transferred = True
                    break
            
            if not transferred:
                # Look for agent_as_tool matching the goal
                for tool_as_agent in self.get_agents_as_tools(current_owner):
                    if goal.lower() in tool_as_agent.displayName.lower():
                        target = tool_as_agent.targetAgentId
                        # agent_as_tool -> ownership is retained by current_owner
                        steps.append({
                            "step": step_count,
                            "owner": current_owner,
                            "action": f"USE AGENT AS TOOL: {target}",
                            "ownership": "retain",
                            "description": f"Agent {current_owner} uses agent {target} as tool. Active agent retains conversation ownership."
                        })
                        step_count += 1
                        transferred = True
                        break
                        
            # Call tools if any are available for the goal
            for tool in self.get_available_tools(current_owner):
                if goal.lower() in tool.displayName.lower() or goal.lower() in tool.description.lower():
                    sync = "synchronous" if tool.executionType != "asynchronous" else "asynchronous"
                    steps.append({
                        "step": step_count,
                        "owner": current_owner,
                        "action": f"CALL TOOL {tool.id}",
                        "ownership": "wait" if sync == "synchronous" else "idle/pending",
                        "description": f"Agent {current_owner} calls tool {tool.id} ({sync})."
                    })
                    step_count += 1
                    
        return steps

    def validate_observed_trajectory(self, trace: ObservedTrace) -> Dict[str, Any]:
        """
        Validate an observed trace/trajectory against MUST, MAY, MUST_NOT claims
        and relationship specifications.
        """
        violations = []
        warnings = []
        checked_claims = 0

        # Build list of transitions from trace
        observed_transitions = []
        for transfer in trace.agentTransfers:
            src = transfer.get("source") or transfer.get("from")
            dst = transfer.get("target") or transfer.get("to")
            if src and dst:
                observed_transitions.append((src, dst))

        # Check for forbidden transitions (MUST_NOT claims)
        for src, dst in observed_transitions:
            forbidden = [
                rel for rel in self.relationships
                if rel.sourceId == src and rel.targetId == dst and (
                    rel.relationType == RelationshipType.FORBIDDEN_TRANSITION or
                    rel.modalGuarantee == Modality.MUST_NOT
                )
            ]
            if forbidden:
                violations.append(
                    f"Forbidden transition observed: from '{src}' to '{dst}' violates MUST_NOT claim/forbidden relationship."
                )
            
            # Check if transition is defined at all
            exists = False
            for rel in self.relationships:
                if rel.sourceId == src and rel.targetId == dst:
                    exists = True
                    break
            if not exists:
                warnings.append(
                    f"Undocumented transition observed: from '{src}' to '{dst}' is not specified in the capability/handoff design."
                )

        # Check MUST claims
        # e.g., if a write tool is called, was confirmation obtained first?
        tool_calls_observed = []
        for call in trace.toolCalls:
            name = call.get("toolName") or call.get("id")
            if name:
                tool_calls_observed.append(name)

        # Check confirmation requirement on side-effecting write tools
        for tool_id, tool in self.tools.items():
            if tool.confirmationRequirement and tool_id in tool_calls_observed:
                # Find if confirmation happened before the tool call in orderedSpans
                confirmed = False
                for span in trace.orderedSpans:
                    action = span.get("action", "").lower()
                    if "confirm" in action or "user confirmed" in action or span.get("confirmed") is True:
                        # Verify it was before the tool call
                        # In orderedSpans, check indices
                        confirmed = True
                if not confirmed:
                    violations.append(
                        f"MUST claim violated: Tool '{tool_id}' has confirmationRequirement=True but was called without observed confirmation."
                    )
                    checked_claims += 1

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "checkedClaimsCount": checked_claims
        }
