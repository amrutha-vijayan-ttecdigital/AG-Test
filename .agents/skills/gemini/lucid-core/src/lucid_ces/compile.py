"""Compile the Lucid Logical Graph into the CES Design IR Spec."""

from __future__ import annotations

import re
from typing import Any, List, Dict, Tuple
from .errors import LucidCesCompileError
from .lucid_adapter import load_lucid_graph
from .classify import classify_shape
from .metadata import parse_visible_label, get_ces_custom_data
from .models import (
    ApplicationSpec,
    AgentSpec,
    ToolSpec,
    CallbackSpec,
    GuardrailSpec,
    VariableSpec,
    RemoteDialogflowAgentRef,
    RelationshipSpec,
    HandoffSpec,
    AgentAsToolSpec,
    EvaluationSpec,
    ObservedTrace,
    SourceProvenance,
    EvidenceSpec,
    RelationshipType,
    Modality,
    ControlAuthority,
    CallbackStage,
    GuardrailOutcome,
    SCHEMA_VERSION
)

def parse_text_sections(text: str) -> Dict[str, str]:
    """Parse text into sections separated by headers like Purpose:, Goals:, etc."""
    sections = {}
    current_key = "description"
    current_lines = []
    for line in text.split("\n"):
        clean_line = line.strip()
        if not clean_line:
            continue
        if ":" in clean_line and not clean_line.startswith("http"):
            parts = clean_line.split(":", 1)
            candidate = parts[0].strip().lower().replace(" ", "_")
            if candidate in (
                "purpose", "scope", "in_scope", "out_of_scope", "goals",
                "responsibilities", "entry", "exit", "completion", "inputs",
                "outputs", "handoff", "timeout", "retry", "confirmation",
                "authorization"
            ):
                sections[current_key] = "\n".join(current_lines).strip()
                current_key = candidate
                current_lines = [parts[1].strip()]
                continue
        current_lines.append(line)
    sections[current_key] = "\n".join(current_lines).strip()
    return sections

def compile_design(compiled_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Compile the logical graph from a Lucid snapshot into a CES semantic IR."""
    graph = load_lucid_graph(compiled_doc)
    
    agents: Dict[str, AgentSpec] = {}
    tools: Dict[str, ToolSpec] = {}
    callbacks: Dict[str, CallbackSpec] = {}
    guardrails: Dict[str, GuardrailSpec] = {}
    variables: Dict[str, VariableSpec] = {}
    remotes: Dict[str, RemoteDialogflowAgentRef] = {}
    evaluations: Dict[str, EvaluationSpec] = {}
    traces: Dict[str, ObservedTrace] = {}
    
    relationships: List[RelationshipSpec] = []
    handoffs: List[HandoffSpec] = []
    agents_as_tools: List[AgentAsToolSpec] = []
    
    diagnostics = list(graph.get("diagnostics", []))
    
    # Compile shapes
    for page in graph.get("pages", []):
        page_id = page["id"]
        for shape in page["shapes"]:
            sid = shape["id"]
            custom_data = get_ces_custom_data(shape)
            ces_id = custom_data.get("ces.id") or sid
            
            kind, evidence_list, status = classify_shape(shape)
            evidence = [EvidenceSpec(**e) for e in evidence_list]
            
            text = shape.get("text", "")
            sections = parse_text_sections(text)
            
            source = SourceProvenance(
                documentId=graph.get("document", {}).get("id", ""),
                pageId=page_id,
                shapeIds=[sid],
                customDataKeys=list(custom_data.keys())
            )
            
            if kind == "agent" or kind == "human_handoff":
                agent_kind = "llm_agent"
                if kind == "human_handoff":
                    agent_kind = "human_handoff_target"
                
                # Check isRoot
                is_root = custom_data.get("ces.is_root") == "true" or "root" in ces_id.lower()
                
                # Extract goals/responsibilities
                in_scope = [g.strip() for g in sections.get("in_scope", "").split(",") if g.strip()]
                out_scope = [g.strip() for g in sections.get("out_of_scope", "").split(",") if g.strip()]
                resp = [r.strip() for r in sections.get("responsibilities", "").split(",") if r.strip()]
                inputs = [i.strip() for i in sections.get("inputs", "").split(",") if i.strip()]
                outputs = [o.strip() for o in sections.get("outputs", "").split(",") if o.strip()]
                entry = [e.strip() for e in sections.get("entry", "").split(",") if e.strip()]
                completion = [c.strip() for c in sections.get("completion", "").split(",") if c.strip()]
                handoff_criteria = [h.strip() for h in sections.get("handoff", "").split(",") if h.strip()]
                
                agents[ces_id] = AgentSpec(
                    id=ces_id,
                    displayName=shape.get("displayName") or sections.get("description", ces_id),
                    source=source,
                    evidence=evidence,
                    status=status,
                    kind=agent_kind,
                    isRoot=is_root,
                    purpose=sections.get("purpose", ""),
                    inScopeGoals=in_scope,
                    outOfScopeGoals=out_scope,
                    responsibilities=resp,
                    inputs=inputs,
                    outputs=outputs,
                    entryAssumptions=entry,
                    completionCriteria=completion,
                    handoffCriteria=handoff_criteria,
                    humanEscalationBehavior=sections.get("exit", "")
                )
                
            elif kind == "tool":
                confirm = custom_data.get("ces.confirmation_requirement") == "true" or "confirm" in text.lower()
                tools[ces_id] = ToolSpec(
                    id=ces_id,
                    displayName=sections.get("description", ces_id),
                    source=source,
                    evidence=evidence,
                    status=status,
                    toolKind=custom_data.get("ces.tool_kind", "openapi"),
                    description=text,
                    confirmationRequirement=confirm,
                    timeoutRetryPolicy=sections.get("timeout", "")
                )
                
            elif kind == "callback":
                stage_str = custom_data.get("ces.callback_type") or "before_model_callback"
                try:
                    stage = CallbackStage(stage_str)
                except ValueError:
                    stage = CallbackStage.BEFORE_MODEL
                callbacks[ces_id] = CallbackSpec(
                    id=ces_id,
                    displayName=sections.get("description", ces_id),
                    source=source,
                    evidence=evidence,
                    status=status,
                    callbackStage=stage,
                    purpose=text
                )
                
            elif kind == "guardrail":
                outcome_str = custom_data.get("ces.guardrail_scope") or "other"
                try:
                    outcome = GuardrailOutcome(outcome_str)
                except ValueError:
                    outcome = GuardrailOutcome.OTHER
                guardrails[ces_id] = GuardrailSpec(
                    id=ces_id,
                    displayName=sections.get("description", ces_id),
                    source=source,
                    evidence=evidence,
                    status=status,
                    outcome=outcome,
                    triggerDefinition=text
                )
                
            elif kind == "variable":
                variables[ces_id] = VariableSpec(
                    id=ces_id,
                    displayName=ces_id,
                    source=source,
                    evidence=evidence,
                    status=status,
                    type=custom_data.get("ces.variable_owner", "string")
                )
                
            elif kind == "remote_dialogflow_agent":
                remotes[ces_id] = RemoteDialogflowAgentRef(
                    id=ces_id,
                    displayName=sections.get("description", ces_id),
                    source=source,
                    evidence=evidence,
                    status=status,
                    remoteAgentResource=sections.get("purpose", "")
                )
                
            elif kind == "evaluation":
                evaluations[ces_id] = EvaluationSpec(
                    id=ces_id,
                    displayName=ces_id,
                    source=source,
                    evidence=evidence,
                    status=status,
                    description=text
                )
                
            elif kind == "observed_trace":
                traces[ces_id] = ObservedTrace(
                    id=ces_id,
                    displayName=ces_id,
                    source=source,
                    evidence=evidence,
                    status=status
                )
                
    # Compile relationships and handoffs
    for page in graph.get("pages", []):
        page_id = page["id"]
        for edge in page["resolvedEdges"]:
            edge_id = edge["id"]
            label = edge["label"]
            parsed_label = parse_visible_label(label)
            src_id = edge["source"]
            dst_id = edge["target"]
            
            # Map default relation types
            relation_type = RelationshipType.MAY_HANDOFF_TO
            
            if "parent" in label.lower() or "child" in label.lower():
                relation_type = RelationshipType.PARENT_OF
            elif "tool" in label.lower() and "agent" not in label.lower():
                relation_type = RelationshipType.CALLS_TOOL
            elif "agent as tool" in label.lower() or "agent_as_tool" in label.lower():
                relation_type = RelationshipType.USES_AGENT_AS_TOOL
            elif "must" in label.lower() and "not" not in label.lower():
                relation_type = RelationshipType.MUST_HANDOFF_TO
            elif "must not" in label.lower() or "forbidden" in label.lower():
                relation_type = RelationshipType.FORBIDDEN_TRANSITION
            
            source_provenance = SourceProvenance(
                documentId=graph.get("document", {}).get("id", ""),
                pageId=page_id,
                lineIds=[edge_id]
            )
            
            modality = parsed_label["modality"] or Modality.MAY
            authority = parsed_label["authority"] or ControlAuthority.UNKNOWN
            status = parsed_label["status"]
            
            relationships.append(RelationshipSpec(
                id=edge_id,
                displayName=label or "Transition",
                source=source_provenance,
                evidence=[EvidenceSpec(kind="line_label", value=label, confidence=0.9)],
                status=status,
                sourceId=src_id,
                targetId=dst_id,
                relationType=relation_type,
                modalGuarantee=modality,
                controlAuthority=authority,
                triggerCondition=parsed_label["text"],
                syncBehavior=parsed_label["syncBehavior"]
            ))

            # Populate Handoff Specs
            if relation_type in (RelationshipType.MAY_HANDOFF_TO, RelationshipType.MUST_HANDOFF_TO):
                # parse return condition if present in label
                return_cond = ""
                ret_match = re.search(r"returns?\s+when\s+(.*)$", label, re.IGNORECASE)
                if ret_match:
                    return_cond = ret_match.group(1).strip()
                handoffs.append(HandoffSpec(
                    id=edge_id + "-handoff",
                    displayName=label or "Handoff",
                    source=source_provenance,
                    status=status,
                    sourceAgentId=src_id,
                    targetAgentId=dst_id,
                    direction="forward" if relation_type == RelationshipType.MAY_HANDOFF_TO else "must",
                    mechanism="deterministic_handoff_rule" if authority == ControlAuthority.DETERMINISTIC_HANDOFF_RULE else "model_instruction",
                    condition=parsed_label["text"],
                    returnCondition=return_cond
                ))
                
            # Populate AgentAsTool Specs
            elif relation_type == RelationshipType.USES_AGENT_AS_TOOL:
                # check for pending behavior in label
                pending_beh = ""
                if "pending" in label.lower():
                    pending_beh = label
                agents_as_tools.append(AgentAsToolSpec(
                    id=edge_id + "-agent-tool",
                    displayName=label or "Agent as Tool",
                    source=source_provenance,
                    status=status,
                    callingAgentId=src_id,
                    targetAgentId=dst_id,
                    executionType=parsed_label["syncBehavior"],
                    pendingResponseBehavior=pending_beh
                ))
                
    # Build Parent/Child relations in Agent Specs
    for rel in relationships:
        if rel.relationType == RelationshipType.PARENT_OF:
            parent = agents.get(rel.sourceId)
            child = agents.get(rel.targetId)
            if parent and child:
                child.parentAgentId = parent.id
                if child.id not in parent.childAgentIds:
                    parent.childAgentIds.append(child.id)
                    
    # Find Root Agent ID
    root_agent_id = ""
    for agent in agents.values():
        if agent.isRoot:
            root_agent_id = agent.id
            break
    if not root_agent_id and agents:
        # Fallback: find agent with no parent
        for agent in agents.values():
            if not agent.parentAgentId:
                root_agent_id = agent.id
                agent.isRoot = True
                break
                
    # Build ApplicationSpec
    app_spec = ApplicationSpec(
        id=graph.get("document", {}).get("id", "ces_app"),
        displayName=graph.get("document", {}).get("title") or "CES Application",
        rootAgentId=root_agent_id
    )
    
    res = {
        "schemaVersion": SCHEMA_VERSION,
        "application": app_spec,
        "agents": list(agents.values()),
        "tools": list(tools.values()),
        "callbacks": list(callbacks.values()),
        "guardrails": list(guardrails.values()),
        "variables": list(variables.values()),
        "remotes": list(remotes.values()),
        "evaluations": list(evaluations.values()),
        "traces": list(traces.values()),
        "relationships": relationships,
        "handoffs": handoffs,
        "agentsAsTools": agents_as_tools,
        "diagnostics": diagnostics
    }

    # Run semantic linter and append diagnostic codes
    from .validate import CesValidator
    validator = CesValidator()
    semantic_diags = validator.validate(res)
    res["diagnostics"].extend(semantic_diags)

    return res
