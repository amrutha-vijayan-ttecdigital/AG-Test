import unittest
from pathlib import Path
from lucid_core.parse import compile_document, load_document
from lucid_ces.compile import compile_design
from lucid_ces.evaluations import generate_eval_specs_from_design, render_evals_mapping_guide

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ces_mock_lucid.json"

class TestCesEvaluations(unittest.TestCase):
    def setUp(self):
        raw = load_document(str(FIXTURE_PATH))
        compiled = compile_document(raw, document_id="doc_ces_test")
        self.ces_ir = compile_design(compiled)

    def test_evaluations_generation(self):
        evals = generate_eval_specs_from_design(self.ces_ir)
        self.assertTrue(len(evals) > 0)
        
        # Check confirmation enforcement check is generated
        confirm_evals = [e for e in evals if "confirm" in e.id]
        self.assertTrue(len(confirm_evals) >= 1)
        self.assertEqual(confirm_evals[0].mustNot, ["call tool_payment_update without confirmation"])

        # Check forbidden transition check is generated
        forbidden_evals = [e for e in evals if "forbidden" in e.id]
        self.assertTrue(len(forbidden_evals) >= 1)
        self.assertIn("handoff to tool_payment_update", forbidden_evals[0].mustNot)

        # Check mapping guide
        guide = render_evals_mapping_guide(evals)
        self.assertIn("# CES Evaluation Specification & Mapping Guide", guide)

if __name__ == "__main__":
    unittest.main()
