#!/usr/bin/env python3
"""Generate human-readable QA test scripts and governance reports.

Three modes:
  from-design  Read a CES Design IR, generate both a human test script
               and a runnable JSON spec from the design's EvaluationSpecs.
  human        Render an existing JSON spec into a human-readable
               step-by-step test script.
  results      Read automated run_eval / run_roleplay output and generate
               a QA governance report with design affirmation, issues, and
               sign-off.

All output is Markdown – no external dependencies beyond the sibling
lucid_ces library (for from-design mode only).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_HERE = pathlib.Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Lucid-core import helper (only needed for from-design mode)
# ---------------------------------------------------------------------------
_LUCID_CORE = None

def _ensure_lucid_core():
    """Lazy-import lucid_ces from the sibling lucid-core package."""
    global _LUCID_CORE
    if _LUCID_CORE is not None:
        return _LUCID_CORE
    # Walk up to find .agents/skills/gemini/lucid-core/src
    for parent in _HERE.parents:
        cand = parent / ".agents" / "skills" / "gemini" / "lucid-core" / "src"
        if cand.is_dir():
            sys.path.insert(0, str(cand))
            break
    try:
        import lucid_ces  # noqa: F811
        _LUCID_CORE = lucid_ces
        return lucid_ces
    except ImportError:
        sys.stderr.write(
            "Error: lucid_ces library not found. "
            "The from-design mode requires the lucid-core package.\n"
        )
        sys.exit(1)


# ===================================================================
# Helpers
# ===================================================================

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _safe_id(name: str) -> str:
    """Turn a display name into a short test-case ID."""
    cleaned = name.lower().replace(" ", "_").replace("-", "_")
    cleaned = "".join(c for c in cleaned if c.isalnum() or c == "_")
    return cleaned[:40]


def _severity_from_type(assertion_type: str) -> str:
    """Map assertion failure types to a default severity."""
    mapping = {
        "routing": "Major",
        "tool": "Major",
        "param": "Minor",
        "keywords": "Minor",
        "latency": "Minor",
        "response": "Minor",
    }
    return mapping.get(assertion_type.lower(), "Minor")


def _describe_expect(expect: dict) -> str:
    """Turn an expect dict into plain-English expected result text."""
    parts = []

    # Routing
    for key in ("Agent route path", "agent_route", "playbook", "flow", "page"):
        val = expect.get(key)
        if val:
            parts.append(f"Routes to **{val}**")
            break

    # Tool
    for key in ("expected_tool_invocation", "expected_tool", "tool"):
        val = expect.get(key)
        if val:
            parts.append(f"invokes tool **{val}**")
            break

    # Response content
    for key in ("contains", "keywords", "responseContains"):
        val = expect.get(key)
        if val:
            if isinstance(val, list):
                parts.append(f'response contains: {", ".join(f"*{v}*" for v in val)}')
            else:
                parts.append(f"response contains: *{val}*")
            break

    # Params
    params = expect.get("params", {})
    if params:
        param_items = [f"`{k}`=`{v}`" for k, v in params.items()]
        parts.append(f'sets parameters: {", ".join(param_items)}')

    return "; ".join(parts) if parts else "Agent responds appropriately"


def _describe_input(turn: dict) -> str:
    """Describe the user action for a turn."""
    if turn.get("user"):
        return f'Say/type: "{turn["user"]}"'
    if turn.get("event"):
        return f"System event: `{turn['event']}`"
    if turn.get("dtmf"):
        return f"Press DTMF: `{turn['dtmf']}`"
    if turn.get("intent"):
        return f"Trigger intent: `{turn['intent']}`"
    return "N/A"


# ===================================================================
# Mode: human — JSON spec -> human-readable test script
# ===================================================================

def render_human_test_script(
    spec: dict,
    agent_name: str = "Agent Under Test",
    agent_version: str = "",
    design_ref: str = "",
) -> str:
    """Render a JSON test spec into a human-readable Markdown test script."""
    lines = []
    lines.append(f"# QA Test Script: {agent_name}")
    lines.append("")
    lines.append(f"**Version**: {agent_version or 'Draft'}")
    lines.append(f"**Environment**: Draft")
    lines.append(f"**Date**: {_now_date()}")
    lines.append(f"**Tester**: ____________________")
    if design_ref:
        lines.append(f"**Design Reference**: {design_ref}")
    lines.append("")
    lines.append("---")
    lines.append("")

    test_cases = spec.get("testCases", [])
    for idx, tc in enumerate(test_cases, 1):
        tc_id = f"TC-{idx:03d}"
        display_name = tc.get("displayName", f"Test Case {idx}")
        tags = tc.get("tags", [])

        # Derive category from tags
        category = "General"
        for tag in tags:
            tag_lower = tag.lower().replace("-", " ")
            if "happy" in tag_lower:
                category = "Happy Path"
            elif "sad" in tag_lower:
                category = "Sad Path"
            elif "neutral" in tag_lower:
                category = "Neutral Path"
            elif "escalation" in tag_lower or "telephony" in tag_lower:
                category = "Escalation"

        lines.append(f"## Test Case: {tc_id} \u2014 {display_name}")
        lines.append("")
        lines.append(f"**Category**: {category}  ")

        priority = "P1-High" if category in ("Happy Path", "Escalation") else "P2-Medium"
        lines.append(f"**Priority**: {priority}")
        lines.append("")

        # Preconditions
        seed_vars = tc.get("seedVariables", tc.get("sessionParams", {}))
        if seed_vars:
            lines.append("### Preconditions")
            lines.append("| Condition | Value |")
            lines.append("|---|---|")
            for k, v in seed_vars.items():
                lines.append(f"| {k} | {v} |")
            start_agent = tc.get("startPage", "")
            if start_agent:
                lines.append(f"| Starting Agent/Page | {start_agent} |")
            lines.append("")

        # Steps
        turns = tc.get("turns", [])
        lines.append("### Test Steps")
        lines.append("| Step | Action | Expected Result | Pass/Fail | Notes |")
        lines.append("|------|--------|-----------------|-----------|-------|")
        for step_idx, turn in enumerate(turns, 1):
            action = _describe_input(turn)
            expect = turn.get("expect", {})
            expected = _describe_expect(expect)
            lines.append(
                f"| {step_idx} | {action} | {expected} | \u2610 Pass \u2610 Fail | |"
            )
        lines.append("")

        # CX Quality
        lines.append("### CX Quality Assessment")
        lines.append("| Dimension | Rating (1-5) | Notes |")
        lines.append("|-----------|-------------|-------|")
        lines.append("| Response Accuracy vs Design | | |")
        lines.append("| Tone & Empathy | | |")
        lines.append("| Natural Language Quality | | |")
        lines.append("| Error Recovery | | |")
        lines.append("| Pacing & Flow | | |")
        lines.append("")

        # Issues
        lines.append("### Issues Found")
        lines.append("| Issue ID | Step | Severity | Description | Status |")
        lines.append("|----------|------|----------|-------------|--------|")
        lines.append("| | | | | |")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Test Cases | {len(test_cases)} |")
    lines.append("| Passed | |")
    lines.append("| Failed | |")
    lines.append("| Issues Found | |")
    lines.append("| Critical Issues | |")
    lines.append("")

    return "\n".join(lines)


# ===================================================================
# Mode: results — run_eval/run_roleplay output -> governance report
# ===================================================================

def render_governance_report(
    spec: Optional[dict],
    results: dict,
    agent_name: str = "Agent Under Test",
    agent_version: str = "",
    design_ref: str = "",
    ir: Optional[dict] = None,
) -> str:
    """Render automated test results into a QA governance report."""
    lines = []
    lines.append(f"# QA Governance Report: {agent_name}")
    lines.append("")
    lines.append("> This report was auto-generated by `generate_qa_report.py`.")
    lines.append("> CX Quality scores require human review.")
    lines.append("")

    # --- Section 1: Agent Overview ---
    lines.append("## 1. Agent Overview")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| **Agent Name** | {agent_name} |")
    lines.append(f"| **Version** | {agent_version or 'Draft'} |")
    lines.append(f"| **Report Date** | {_now_date()} |")
    lines.append(f"| **Report Generated** | {_now_iso()} |")
    if design_ref:
        lines.append(f"| **Design Reference** | {design_ref} |")
    run_meta = results.get("metadata", {})
    if run_meta.get("run_id"):
        lines.append(f"| **Run ID** | `{run_meta['run_id']}` |")
    if run_meta.get("project"):
        lines.append(f"| **GCP Project** | `{run_meta['project']}` |")
    lines.append("")

    # --- Section 2: Test Coverage Summary ---
    lines.append("## 2. Test Coverage Summary")
    lines.append("")

    case_results = results.get("cases", results.get("testCases", []))

    # If results is from run_roleplay (single transcript), wrap it
    if not case_results and results.get("transcript"):
        case_results = [{
            "displayName": "Roleplay Simulation",
            "passed": results.get("evaluation", {}).get("passed", False),
            "evaluation": results.get("evaluation", {}),
            "transcript": results.get("transcript", ""),
        }]

    total = len(case_results)
    passed = sum(1 for c in case_results if c.get("passed", False))
    failed = total - passed

    lines.append("| Metric | Count | Percentage |")
    lines.append("|---|---|---|")
    lines.append(f"| **Total Test Cases** | {total} | 100% |")
    pct_pass = f"{(passed / total * 100):.0f}%" if total > 0 else "N/A"
    pct_fail = f"{(failed / total * 100):.0f}%" if total > 0 else "N/A"
    lines.append(f"| **Passed** | {passed} | {pct_pass} |")
    lines.append(f"| **Failed** | {failed} | {pct_fail} |")
    overall = "\u2705 PASSED" if failed == 0 else "\u274c FAILED"
    lines.append(f"| **Overall Status** | **{overall}** | |")
    lines.append("")

    # --- Section 3: Design Affirmation Matrix ---
    lines.append("## 3. Design Affirmation Matrix")
    lines.append("")

    if ir:
        lc = _ensure_lucid_core()
        query = lc.CesDesignQuery(ir)

        lines.append("| Design Element | Type | Test Coverage | Matches Design? | Notes |")
        lines.append("|---|---|---|---|---|")

        # Agents
        for a_id, agent in query.agents.items():
            covered = "\u2014"
            affirmed = "\u2014"
            for cr in case_results:
                turns = cr.get("turns", [])
                for t in turns:
                    actual_route = t.get("actual", {}).get("route", "")
                    if a_id.lower() in actual_route.lower():
                        covered = f"TC: {cr.get('displayName', '?')}"
                        affirmed = "\u2705 Yes" if cr.get("passed") else "\u26a0\ufe0f Failed"
                        break
            lines.append(
                f"| {agent.displayName or a_id} | Agent | {covered} | {affirmed} | |"
            )

        # Tools
        for t_id, tool in query.tools.items():
            covered = "\u2014"
            affirmed = "\u2014"
            for cr in case_results:
                turns = cr.get("turns", [])
                for t in turns:
                    actual_tools = t.get("actual", {}).get("tools", [])
                    if isinstance(actual_tools, list) and any(
                        t_id.lower() in at.lower() for at in actual_tools
                    ):
                        covered = f"TC: {cr.get('displayName', '?')}"
                        affirmed = "\u2705 Yes" if cr.get("passed") else "\u26a0\ufe0f Failed"
                        break
            lines.append(
                f"| {tool.displayName or t_id} | Tool | {covered} | {affirmed} | |"
            )

        # Behavioral Claims
        for claim in query.claims:
            claim_text = ""
            if isinstance(claim, dict):
                claim_text = claim.get("claim", claim.get("displayName", ""))
            else:
                claim_text = str(claim)
            if claim_text:
                lines.append(
                    f"| {claim_text[:60]} | Behavioral Claim | \u2014 | \u2610 Review | |"
                )
        lines.append("")
    else:
        lines.append("*Design IR not provided. Run with `--ir` to enable design affirmation.*")
        lines.append("")

    # --- Section 4: Test Case Details ---
    lines.append("## 4. Test Case Results")
    lines.append("")

    issue_register: List[dict] = []
    issue_counter = 1

    for idx, cr in enumerate(case_results, 1):
        tc_id = f"TC-{idx:03d}"
        name = cr.get("displayName", f"Test Case {idx}")
        tc_passed = cr.get("passed", False)
        status_icon = "\u2705" if tc_passed else "\u274c"

        lines.append(f"### {tc_id}: {name} \u2014 {status_icon} {'PASSED' if tc_passed else 'FAILED'}")
        lines.append("")

        # Turn-by-turn results if available
        turns = cr.get("turns", [])
        if turns:
            lines.append("| Step | Input | Expected | Actual | Status |")
            lines.append("|------|-------|----------|--------|--------|")
            for step_idx, turn in enumerate(turns, 1):
                user_input = turn.get("user", turn.get("input", "\u2014"))
                expected = turn.get("expected", "\u2014")
                if isinstance(expected, dict):
                    expected = _describe_expect(expected)
                actual = turn.get("actual", "\u2014")
                if isinstance(actual, dict):
                    actual_parts = []
                    if actual.get("route"):
                        actual_parts.append(f"Route: {actual['route']}")
                    if actual.get("tools"):
                        actual_parts.append(f"Tools: {', '.join(actual['tools'])}")
                    if actual.get("text"):
                        text_preview = actual["text"][:80]
                        actual_parts.append(f'"{text_preview}"')
                    actual = "; ".join(actual_parts) if actual_parts else str(actual)

                turn_passed = turn.get("passed", True)
                step_status = "\u2705" if turn_passed else "\u274c"
                lines.append(
                    f"| {step_idx} | {user_input} | {expected} | {actual} | {step_status} |"
                )

                # Auto-generate issues for failures
                if not turn_passed:
                    failures = turn.get("failures", [])
                    for fail in failures:
                        issue_id = f"ISS-{issue_counter:03d}"
                        f_type = fail.get("type", "assertion") if isinstance(fail, dict) else "assertion"
                        f_msg = fail.get("message", str(fail)) if isinstance(fail, dict) else str(fail)
                        severity = _severity_from_type(f_type)
                        issue_register.append({
                            "id": issue_id,
                            "description": f_msg,
                            "severity": severity,
                            "test_case": f"{tc_id} \u2014 {name}",
                            "step": step_idx,
                            "status": "Open",
                        })
                        issue_counter += 1
            lines.append("")
        else:
            # Roleplay-style result
            evaluation = cr.get("evaluation", {})
            if evaluation:
                lines.append(f"- **Passed**: {evaluation.get('passed', '\u2014')}")
                lines.append(f"- **Goal Resolved**: {evaluation.get('goal_resolved', '\u2014')}")
                lines.append(f"- **Mood Handling Score**: {evaluation.get('agent_mood_handling_score', '\u2014')}/5")
                lines.append(f"- **Reasoning**: {evaluation.get('reasoning', '\u2014')}")
                violations = evaluation.get("violations", [])
                if violations:
                    lines.append(f"- **Violations**: {', '.join(str(v) for v in violations)}")
                    for v in violations:
                        issue_id = f"ISS-{issue_counter:03d}"
                        issue_register.append({
                            "id": issue_id,
                            "description": str(v),
                            "severity": "Major",
                            "test_case": f"{tc_id} \u2014 {name}",
                            "step": "\u2014",
                            "status": "Open",
                        })
                        issue_counter += 1
                lines.append("")

            transcript = cr.get("transcript", "")
            if transcript:
                lines.append("<details><summary>Full Transcript</summary>")
                lines.append("")
                lines.append("```")
                lines.append(transcript)
                lines.append("```")
                lines.append("</details>")
                lines.append("")

        lines.append("---")
        lines.append("")

    # --- Section 5: CX Quality Scorecard ---
    lines.append("## 5. CX Quality Scorecard")
    lines.append("")
    lines.append("*Requires human review. Fill in scores after reviewing test results and transcripts.*")
    lines.append("")
    lines.append("| Dimension | Rating (1-5) | Notes |")
    lines.append("|-----------|-------------|-------|")
    lines.append("| Response Accuracy vs Design | | |")
    lines.append("| Tone & Empathy | | |")
    lines.append("| Natural Language Quality | | |")
    lines.append("| Error Recovery | | |")
    lines.append("| Guardrail Compliance | | |")
    lines.append("| Pacing & Flow | | |")
    lines.append(f"| **Overall CX Score** | | |")
    lines.append("")

    # --- Section 6: Issue Register ---
    lines.append("## 6. Issue Register")
    lines.append("")
    if issue_register:
        lines.append("| Issue ID | Description | Severity | Test Case | Step | Status | Owner | Target Date |")
        lines.append("|----------|-------------|----------|-----------|------|--------|-------|-------------|")
        for iss in issue_register:
            lines.append(
                f"| {iss['id']} | {iss['description'][:80]} | {iss['severity']} "
                f"| {iss['test_case']} | {iss['step']} | {iss['status']} | | |"
            )
    else:
        lines.append("No issues found. All test cases passed. \u2705")
    lines.append("")

    # --- Section 7: Go-Live Readiness ---
    lines.append("## 7. Go-Live Readiness Assessment")
    lines.append("")
    critical_issues = [i for i in issue_register if i["severity"] == "Critical"]
    major_issues = [i for i in issue_register if i["severity"] == "Major"]

    if critical_issues:
        verdict = "\u274c **Not Ready**"
        reason = f"{len(critical_issues)} critical issue(s) must be resolved."
    elif major_issues:
        verdict = "\u26a0\ufe0f **Ready with Conditions**"
        reason = f"{len(major_issues)} major issue(s) require review and resolution or risk acceptance."
    elif failed > 0:
        verdict = "\u26a0\ufe0f **Ready with Conditions**"
        reason = f"{failed} test case(s) failed. Review and accept risk or fix."
    else:
        verdict = "\u2705 **Ready**"
        reason = "All test cases passed with no open issues."

    lines.append(f"**Verdict**: {verdict}")
    lines.append(f"**Rationale**: {reason}")
    lines.append("")

    if critical_issues or major_issues:
        lines.append("### Blocking Issues")
        for iss in critical_issues + major_issues:
            lines.append(f"- **{iss['id']}** ({iss['severity']}): {iss['description'][:80]}")
        lines.append("")

    # --- Section 8: Sign-off ---
    lines.append("## 8. Sign-off")
    lines.append("")
    lines.append("| Role | Name | Date | Approval |")
    lines.append("|------|------|------|----------|")
    lines.append("| Client Lead | | | \u2610 Approved |")
    lines.append("| Project Manager | | | \u2610 Approved |")
    lines.append("| QA Lead | | | \u2610 Approved |")
    lines.append("| Engineering Lead | | | \u2610 Approved |")
    lines.append("| Design Lead | | | \u2610 Approved |")
    lines.append("")

    return "\n".join(lines)


# ===================================================================
# Mode: from-design — CES IR -> human test script + runnable JSON spec
# ===================================================================

def _eval_spec_to_test_case(eval_spec, query) -> dict:
    """Convert an EvaluationSpec into a JSON test case dict."""
    tc = {
        "displayName": eval_spec.displayName or eval_spec.id,
        "tags": [],
        "turns": [],
    }

    # Seed variables from the eval spec
    if eval_spec.initialVariables:
        tc["sessionParams"] = dict(eval_spec.initialVariables)

    # Determine tags
    if eval_spec.mustNot:
        tc["tags"].append("sad-path")
    if eval_spec.expectedToolCalls:
        tc["tags"].append("tool-verification")
    if not tc["tags"]:
        tc["tags"].append("happy-path")

    # Build the primary turn from the user goal
    turn = {"user": eval_spec.userGoal or "Perform the intended action"}
    expect: Dict[str, Any] = {}

    # Routing expectation from startingAgentId
    if eval_spec.startingAgentId:
        expect["Agent route path"] = eval_spec.startingAgentId

    # Tool expectations
    if eval_spec.expectedToolCalls:
        first_tool = eval_spec.expectedToolCalls[0]
        tool_id = first_tool.get("toolId", "") if isinstance(first_tool, dict) else str(first_tool)
        if tool_id:
            expect["expected_tool_invocation"] = tool_id

    # Keywords from must assertions
    if eval_spec.must:
        expect["contains"] = eval_spec.must

    # Params from expected outcome
    if eval_spec.expectedOutcome:
        expect["params"] = dict(eval_spec.expectedOutcome)

    if expect:
        turn["expect"] = expect
    tc["turns"].append(turn)

    return tc


def generate_from_design(ir: dict, agent_name: str) -> tuple:
    """Generate both a human test script and a runnable JSON spec from a CES IR.

    Returns (human_script_md: str, spec_json: dict).
    """
    lc = _ensure_lucid_core()
    query = lc.CesDesignQuery(ir)

    # Get eval specs from the design
    eval_specs = lc.generate_eval_specs_from_design(ir)

    # Convert each EvaluationSpec to a TestCase
    test_cases = []
    for es in eval_specs:
        tc = _eval_spec_to_test_case(es, query)
        test_cases.append(tc)

    # Generate additional test cases from forbidden transitions
    for rel in query.relationships:
        rel_type = rel.relationType
        modal = rel.modalGuarantee
        rel_type_val = rel_type.value if hasattr(rel_type, "value") else str(rel_type)
        modal_val = modal.value if hasattr(modal, "value") else str(modal)

        if rel_type_val == "FORBIDDEN_TRANSITION" or modal_val == "MUST_NOT":
            already_covered = any(
                "forbidden" in tc["displayName"].lower()
                and rel.sourceId in tc["displayName"]
                for tc in test_cases
            )
            if not already_covered:
                tc = {
                    "displayName": f"Forbidden: {rel.sourceId} must not reach {rel.targetId}",
                    "tags": ["sad-path", "forbidden-transition"],
                    "turns": [{
                        "user": f"Attempt to route from {rel.sourceId} to {rel.targetId}",
                        "expect": {
                            "Agent route path": rel.sourceId,
                        }
                    }]
                }
                test_cases.append(tc)

    # Generate test cases from behavioral claims
    for claim in query.claims:
        claim_text = ""
        claim_must = []
        if isinstance(claim, dict):
            claim_text = claim.get("claim", claim.get("displayName", ""))
            claim_must = [claim_text] if claim_text else []
        elif hasattr(claim, "claim"):
            claim_text = claim.claim or getattr(claim, "displayName", "")
            claim_must = [claim_text] if claim_text else []
        else:
            claim_text = str(claim)
            claim_must = [claim_text]

        if claim_text:
            tc = {
                "displayName": f"Behavioral: {claim_text[:60]}",
                "tags": ["behavioral-claim"],
                "turns": [{
                    "user": "Trigger scenario related to behavioral claim",
                    "expect": {
                        "contains": claim_must[:3],
                    }
                }]
            }
            test_cases.append(tc)

    spec = {
        "description": f"Auto-generated test spec from CES Design IR for {agent_name}",
        "startUtterance": "<event>session start</event>",
        "testCases": test_cases,
    }

    # Design reference from IR application
    design_ref = ""
    app = query.application
    if app and hasattr(app, "displayName"):
        design_ref = app.displayName or ""

    # Generate human-readable script from the spec
    human_script = render_human_test_script(
        spec, agent_name=agent_name, design_ref=design_ref
    )

    return human_script, spec


# ===================================================================
# CLI
# ===================================================================

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate human-readable QA test scripts and governance reports."
    )
    ap.add_argument(
        "--mode",
        required=True,
        choices=["from-design", "human", "results", "roleplay"],
        help="Generation mode",
    )
    ap.add_argument("--spec", help="Path to JSON test spec file")
    ap.add_argument("--ir", help="Path to CES Design IR JSON file (for from-design and design affirmation)")
    ap.add_argument("--results", help="Path to results JSON from run_eval or run_roleplay")
    ap.add_argument("--design-spec", help="Path to design spec Markdown file (for reference)")
    ap.add_argument("--agent-name", default="Agent Under Test", help="Agent name for the report")
    ap.add_argument("--agent-version", default="", help="Agent version string")
    ap.add_argument("--output-dir", default=".", help="Output directory for generated files")

    args = ap.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    safe_name = _safe_id(args.agent_name)

    # ---- from-design mode ----
    if args.mode == "from-design":
        if not args.ir:
            sys.stderr.write("Error: --ir is required for from-design mode.\n")
            return 1
        with open(args.ir, "r", encoding="utf-8") as f:
            ir = json.load(f)

        human_script, spec = generate_from_design(ir, args.agent_name)

        # Write human test script
        script_path = os.path.join(args.output_dir, f"{safe_name}_test_script.md")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(human_script)
        print(f"Human test script written to: {script_path}")

        # Write runnable JSON spec
        spec_path = os.path.join(args.output_dir, f"{safe_name}_spec.json")
        with open(spec_path, "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2)
        print(f"Runnable JSON spec written to: {spec_path}")

        return 0

    # ---- human mode ----
    elif args.mode == "human":
        if not args.spec:
            sys.stderr.write("Error: --spec is required for human mode.\n")
            return 1
        with open(args.spec, "r", encoding="utf-8") as f:
            spec = json.load(f)

        design_ref = args.design_spec or ""
        human_script = render_human_test_script(
            spec, agent_name=args.agent_name, agent_version=args.agent_version,
            design_ref=design_ref,
        )

        script_path = os.path.join(args.output_dir, f"{safe_name}_test_script.md")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(human_script)
        print(f"Human test script written to: {script_path}")

        return 0

    # ---- results / roleplay mode ----
    elif args.mode in ("results", "roleplay"):
        if not args.results:
            sys.stderr.write("Error: --results is required for results/roleplay mode.\n")
            return 1
        with open(args.results, "r", encoding="utf-8") as f:
            results = json.load(f)

        spec = None
        if args.spec:
            with open(args.spec, "r", encoding="utf-8") as f:
                spec = json.load(f)

        ir = None
        if args.ir:
            with open(args.ir, "r", encoding="utf-8") as f:
                ir = json.load(f)

        design_ref = args.design_spec or ""
        report = render_governance_report(
            spec, results, agent_name=args.agent_name,
            agent_version=args.agent_version, design_ref=design_ref, ir=ir,
        )

        report_path = os.path.join(
            args.output_dir, f"{safe_name}_governance_report.md"
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"QA governance report written to: {report_path}")

        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
