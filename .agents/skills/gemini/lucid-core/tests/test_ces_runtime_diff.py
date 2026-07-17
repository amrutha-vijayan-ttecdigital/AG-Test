import unittest
from pathlib import Path
from lucid_core.parse import compile_document, load_document
from lucid_ces.compile import compile_design
from lucid_ces.diff import diff_design_and_runtime, render_diff_markdown

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ces_mock_lucid.json"

class TestCesRuntimeDiff(unittest.TestCase):
    def setUp(self):
        raw = load_document(str(FIXTURE_PATH))
        compiled = compile_document(raw, document_id="doc_ces_test")
        self.ces_ir = compile_design(compiled)

    def test_diff_identifies_missing_and_mismatch(self):
        # Construct a synthetic runtime export that differs from design
        runtime_export = {
            "application": {
                "id": "doc_ces_test",
                "displayName": "CES Application",
                "rootAgentId": "agent_billing" # mismatch rootAgentId
            },
            "agents": [
                # agent_root is missing
                {
                    "id": "agent_billing",
                    "displayName": "Billing Agent",
                    "purpose": "Different purpose text", # mismatch purpose
                    "kind": "llm_agent"
                }
            ],
            "tools": [],
            "callbacks": [],
            "guardrails": [],
            "variables": [],
            "relationships": [],
            "handoffs": [],
            "agentsAsTools": []
        }
        
        diffs = diff_design_and_runtime(self.ces_ir, runtime_export)
        self.assertTrue(len(diffs) > 0)
        
        classifications = {d["classification"] for d in diffs}
        self.assertIn("missing_in_runtime", classifications) # agent_root is missing
        self.assertIn("configuration_mismatch", classifications) # root agent is different
        self.assertIn("instruction_mismatch", classifications) # purpose differs
        
        # Test markdown rendering
        report = render_diff_markdown(diffs)
        self.assertIn("# CES Design vs Runtime Export Diff Report", report)
        self.assertIn("missing_in_runtime", report)

if __name__ == "__main__":
    unittest.main()
