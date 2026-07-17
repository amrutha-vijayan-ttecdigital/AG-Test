import unittest
from pathlib import Path
from lucid_core.parse import compile_document, load_document
from lucid_ces.compile import compile_design
from lucid_ces.render_markdown import render_markdown_report
from lucid_ces.render_mermaid import render_mermaid_diagram

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ces_mock_lucid.json"

class TestCesRenderers(unittest.TestCase):
    def setUp(self):
        raw = load_document(str(FIXTURE_PATH))
        compiled = compile_document(raw, document_id="doc_ces_test")
        self.ces_ir = compile_design(compiled)

    def test_markdown_report_sections(self):
        report = render_markdown_report(self.ces_ir)
        self.assertIn("# CES Agent Studio Design Specification Report", report)
        self.assertIn("## 1. Application Overview", report)
        self.assertIn("## 4. Behavioral Contracts & Rules", report)
        self.assertIn("## 13. Provenance Appendix", report)

    def test_mermaid_renderer_outputs(self):
        # Test capability graph diagram
        diagram = render_mermaid_diagram(self.ces_ir, "capability")
        self.assertIn("flowchart TD", diagram)
        self.assertIn("agent_root", diagram)
        
        # Test hierarchy diagram
        diagram_h = render_mermaid_diagram(self.ces_ir, "hierarchy")
        self.assertIn("flowchart TD", diagram_h)

if __name__ == "__main__":
    unittest.main()
