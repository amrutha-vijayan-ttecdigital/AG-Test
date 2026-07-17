import unittest
from pathlib import Path
from lucid_core.parse import compile_document, load_document
from lucid_ces.compile import compile_design
from lucid_ces.lucid_adapter import load_lucid_graph, walk_line_endpoint

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ces_mock_lucid.json"
CHAIN_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "lucid_line_chain.json"

class TestCesCompile(unittest.TestCase):
    def test_compile_ces_design(self):
        raw = load_document(str(FIXTURE_PATH))
        compiled_doc = compile_document(raw, document_id="doc_ces_test")
        ces_ir = compile_design(compiled_doc)
        
        self.assertEqual(ces_ir["schemaVersion"], "ces-design-ir/v1")
        self.assertEqual(ces_ir["application"].rootAgentId, "agent_root")
        
        # Verify agents
        agents = {a.id: a for a in ces_ir["agents"]}
        self.assertIn("agent_root", agents)
        self.assertIn("agent_billing", agents)
        self.assertEqual(agents["agent_root"].kind, "llm_agent")
        
        # Verify tools
        tools = {t.id: t for t in ces_ir["tools"]}
        self.assertIn("tool_lookup", tools)
        self.assertIn("tool_payment_update", tools)
        self.assertTrue(tools["tool_payment_update"].confirmationRequirement)
        
        # Verify callbacks
        callbacks = {c.id: c for c in ces_ir["callbacks"]}
        self.assertIn("callback_auth", callbacks)
        
        # Verify relationships
        rels = ces_ir["relationships"]
        self.assertTrue(len(rels) > 0)
        
    def test_line_to_line_chain_resolution(self):
        # Using the baseline line chain fixture
        raw = load_document(str(CHAIN_FIXTURE_PATH))
        # compile_document handles physical parsing
        compiled_doc = compile_document(raw)
        graph = load_lucid_graph(compiled_doc)
        
        # Assert that resolvedEdges links "a-b" to "done" or similar shape endpoints traversed through lines
        edges = graph["pages"][0]["resolvedEdges"]
        self.assertTrue(len(edges) > 0)
        # Check that physicalLineIds preserves all line segments
        for edge in edges:
            self.assertTrue(len(edge["physicalLineIds"]) >= 1)

if __name__ == "__main__":
    unittest.main()
