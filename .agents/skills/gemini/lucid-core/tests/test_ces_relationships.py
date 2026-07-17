import unittest
from pathlib import Path
from lucid_core.parse import compile_document, load_document
from lucid_ces.compile import compile_design
from lucid_ces.relationships import CesDesignQuery
from lucid_ces.models import ObservedTrace, Modality

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ces_mock_lucid.json"

class TestCesRelationships(unittest.TestCase):
    def setUp(self):
        raw = load_document(str(FIXTURE_PATH))
        compiled = compile_document(raw, document_id="doc_ces_test")
        self.ces_ir = compile_design(compiled)
        self.query = CesDesignQuery(self.ces_ir)

    def test_queries(self):
        self.assertIsNotNone(self.query.get_application())
        self.assertIsNotNone(self.query.get_agent("agent_root"))
        
        # Children
        children = self.query.get_children("agent_root")
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0].id, "agent_billing")
        
        # Tools
        tools = self.query.get_available_tools("agent_billing")
        self.assertTrue(len(tools) >= 1)
        
        # Handoffs
        handoffs = self.query.get_possible_handoffs("agent_root")
        self.assertTrue(len(handoffs) >= 1)

    def test_construct_possible_trajectory(self):
        trajectory = self.query.construct_possible_trajectory("agent_root", ["billing", "lookup"])
        self.assertTrue(len(trajectory) > 0)
        # Check ownership tracking
        self.assertEqual(trajectory[0]["owner"], "agent_root")
        # Find handoff step
        handoff_steps = [s for s in trajectory if "HANDOFF" in s["action"]]
        self.assertTrue(len(handoff_steps) >= 1)
        self.assertEqual(handoff_steps[0]["ownership"], "transfer")

    def test_validate_observed_trajectory_violations(self):
        # 1. Test confirmation violation
        trace1 = ObservedTrace(
            id="trace_1",
            displayName="Trace 1",
            orderedSpans=[
                {"step": 0, "action": "start"},
                {"step": 1, "action": "call payment update tool"}
            ],
            toolCalls=[
                {"toolName": "tool_payment_update"}
            ],
            agentTransfers=[]
        )
        val1 = self.query.validate_observed_trajectory(trace1)
        self.assertFalse(val1["valid"])
        self.assertTrue(any("confirmation" in v for v in val1["violations"]))

        # 2. Test forbidden transition violation
        trace2 = ObservedTrace(
            id="trace_2",
            displayName="Trace 2",
            orderedSpans=[],
            toolCalls=[],
            agentTransfers=[
                {"source": "agent_root", "target": "tool_payment_update"} # Forbidden transition in design
            ]
        )
        val2 = self.query.validate_observed_trajectory(trace2)
        self.assertFalse(val2["valid"])
        self.assertTrue(any("Forbidden transition" in v for v in val2["violations"]))

if __name__ == "__main__":
    unittest.main()
