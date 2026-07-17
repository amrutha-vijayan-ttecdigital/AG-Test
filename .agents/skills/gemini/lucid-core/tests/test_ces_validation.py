import unittest
from lucid_ces.validate import CesValidator
from lucid_ces.models import ApplicationSpec, AgentSpec, ToolSpec, VariableSpec

class TestCesValidation(unittest.TestCase):
    def test_missing_root_agent_diagnostic_ces001(self):
        # Application with empty rootAgentId
        ir = {
            "application": ApplicationSpec(id="app_1", displayName="Test App", rootAgentId=""),
            "agents": [],
            "tools": [],
            "callbacks": [],
            "guardrails": [],
            "variables": [],
            "relationships": [],
            "handoffs": [],
            "agentsAsTools": [],
            "diagnostics": []
        }
        validator = CesValidator()
        diags = validator.validate(ir)
        codes = {d["code"] for d in diags}
        self.assertIn("CES001", codes)

    def test_agent_missing_purpose_scope_ces002(self):
        agent = AgentSpec(id="agent_1", displayName="Agent 1", purpose="", inScopeGoals=[], outOfScopeGoals=[])
        ir = {
            "application": ApplicationSpec(id="app_1", displayName="Test App", rootAgentId="agent_1"),
            "agents": [agent],
            "tools": [],
            "callbacks": [],
            "guardrails": [],
            "variables": [],
            "relationships": [],
            "handoffs": [],
            "agentsAsTools": [],
            "diagnostics": []
        }
        validator = CesValidator()
        diags = validator.validate(ir)
        codes = {d["code"] for d in diags}
        self.assertIn("CES002", codes)

    def test_side_effect_tool_missing_confirmation_ces012(self):
        # Tool description contains 'write' but confirmationRequirement is False
        tool = ToolSpec(id="tool_write", displayName="Write Tool", description="Writes to database.", confirmationRequirement=False)
        ir = {
            "application": ApplicationSpec(id="app_1", displayName="Test App", rootAgentId="agent_root"),
            "agents": [AgentSpec(id="agent_root", displayName="Root Agent", purpose="Test", inScopeGoals=["test"])],
            "tools": [tool],
            "callbacks": [],
            "guardrails": [],
            "variables": [],
            "relationships": [],
            "handoffs": [],
            "agentsAsTools": [],
            "diagnostics": []
        }
        validator = CesValidator()
        diags = validator.validate(ir)
        codes = {d["code"] for d in diags}
        self.assertIn("CES012", codes)

    def test_undeclared_variable_referenced_ces020(self):
        agent = AgentSpec(
            id="agent_root",
            displayName="Root Agent",
            purpose="Test",
            inScopeGoals=["test"],
            variablesRead=["undeclared_var"]
        )
        ir = {
            "application": ApplicationSpec(id="app_1", displayName="Test App", rootAgentId="agent_root"),
            "agents": [agent],
            "tools": [],
            "callbacks": [],
            "guardrails": [],
            "variables": [], # empty variables
            "relationships": [],
            "handoffs": [],
            "agentsAsTools": [],
            "diagnostics": []
        }
        validator = CesValidator()
        diags = validator.validate(ir)
        codes = {d["code"] for d in diags}
        self.assertIn("CES020", codes)

if __name__ == "__main__":
    unittest.main()
