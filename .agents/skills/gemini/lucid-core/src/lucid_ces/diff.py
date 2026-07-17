"""Compare compiled design IR against a saved runtime export."""

from __future__ import annotations

from typing import Any, Dict, List
from .relationships import CesDesignQuery

def diff_design_and_runtime(
    design_ir: Dict[str, Any],
    runtime_export: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Compare compiled design IR and runtime export returning structured differences."""
    design = CesDesignQuery(design_ir)
    
    # Wrap runtime export in CesDesignQuery to ease access
    runtime = CesDesignQuery(runtime_export)
    
    diffs = []

    def add_diff(elem_type: str, elem_id: str, classification: str, desc: str, design_val: Any = None, runtime_val: Any = None):
        diffs.append({
            "element_type": elem_type,
            "element_id": elem_id,
            "classification": classification,
            "description": desc,
            "design_value": design_val,
            "runtime_value": runtime_val
        })

    # 1. Compare Application rootAgentId
    design_app = design.get_application()
    runtime_app = runtime.get_application()
    if design_app and runtime_app:
        if design_app.rootAgentId != runtime_app.rootAgentId:
            add_diff(
                "application",
                design_app.id,
                "configuration_mismatch",
                f"Application root agent mismatch: Design has '{design_app.rootAgentId}', Runtime has '{runtime_app.rootAgentId}'",
                design_app.rootAgentId,
                runtime_app.rootAgentId
            )

    # 2. Compare Agents
    design_agents = set(design.agents.keys())
    runtime_agents = set(runtime.agents.keys())
    
    # Missing in runtime
    for aid in design_agents - runtime_agents:
        add_diff("agent", aid, "missing_in_runtime", f"Agent '{aid}' defined in design but missing in runtime.")
        
    # Missing in design
    for aid in runtime_agents - design_agents:
        add_diff("agent", aid, "missing_in_design", f"Agent '{aid}' found in runtime but missing in design.")
        
    # In both - check config/instructions
    for aid in design_agents & runtime_agents:
        da = design.agents[aid]
        ra = runtime.agents[aid]
        if da.purpose.strip() != ra.purpose.strip():
            add_diff(
                "agent",
                aid,
                "instruction_mismatch",
                f"Agent '{aid}' instructions/purpose mismatch.",
                da.purpose,
                ra.purpose
            )
        if da.kind != ra.kind:
            add_diff(
                "agent",
                aid,
                "configuration_mismatch",
                f"Agent '{aid}' kind mismatch: Design is '{da.kind}', Runtime is '{ra.kind}'",
                da.kind,
                ra.kind
            )
            
    # 3. Compare Tools
    design_tools = set(design.tools.keys())
    runtime_tools = set(runtime.tools.keys())
    
    for tid in design_tools - runtime_tools:
        add_diff("tool", tid, "missing_in_runtime", f"Tool '{tid}' defined in design but missing in runtime.")
        
    for tid in runtime_tools - design_tools:
        add_diff("tool", tid, "missing_in_design", f"Tool '{tid}' found in runtime but missing in design.")
        
    for tid in design_tools & runtime_tools:
        dt = design.tools[tid]
        rt = runtime.tools[tid]
        if dt.confirmationRequirement != rt.confirmationRequirement:
            add_diff(
                "tool",
                tid,
                "configuration_mismatch",
                f"Tool '{tid}' confirmation requirement mismatch.",
                dt.confirmationRequirement,
                rt.confirmationRequirement
            )

    # 4. Compare Callbacks and Guardrails
    design_cbs = set(design.callbacks.keys())
    runtime_cbs = set(runtime.callbacks.keys())
    for cid in design_cbs - runtime_cbs:
        add_diff("callback", cid, "missing_in_runtime", f"Callback '{cid}' defined in design but missing in runtime.")
    for cid in runtime_cbs - design_cbs:
        add_diff("callback", cid, "missing_in_design", f"Callback '{cid}' found in runtime but missing in design.")

    design_grs = set(design.guardrails.keys())
    runtime_grs = set(runtime.guardrails.keys())
    for gid in design_grs - runtime_grs:
        add_diff("guardrail", gid, "missing_in_runtime", f"Guardrail '{gid}' defined in design but missing in runtime.")
    for gid in runtime_grs - design_grs:
        add_diff("guardrail", gid, "missing_in_design", f"Guardrail '{gid}' found in runtime but missing in design.")

    # 5. Compare Handoff relationships
    # We construct simplified sets of transitions (source -> target)
    design_transitions = {(ho.sourceAgentId, ho.targetAgentId) for ho in design.handoffs}
    runtime_transitions = {(ho.sourceAgentId, ho.targetAgentId) for ho in runtime.handoffs}
    
    for src, dst in design_transitions - runtime_transitions:
        add_diff(
            "relationship",
            f"{src}->{dst}",
            "relationship_mismatch",
            f"Handoff from '{src}' to '{dst}' exists in design but missing in runtime."
        )
        
    for src, dst in runtime_transitions - design_transitions:
        add_diff(
            "relationship",
            f"{src}->{dst}",
            "relationship_mismatch",
            f"Handoff from '{src}' to '{dst}' exists in runtime but missing in design."
        )

    return diffs

def render_diff_markdown(diffs: List[Dict[str, Any]]) -> str:
    """Render the structured difference list in Markdown."""
    lines = []
    lines.append("# CES Design vs Runtime Export Diff Report")
    lines.append("")
    
    if not diffs:
        lines.append("### No differences found! The design IR matches the runtime export exactly.")
        return "\n".join(lines)
        
    lines.append(f"Found {len(diffs)} differences between the design model and the active runtime configurations.")
    lines.append("")
    lines.append("| Component | Element ID | Classification | Description |")
    lines.append("|---|---|---|---|")
    
    for d in diffs:
        lines.append(f"| {d['element_type']} | {d['element_id']} | **{d['classification']}** | {d['description']} |")
        
    lines.append("")
    return "\n".join(lines)
