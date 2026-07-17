import unittest
from pathlib import Path

from lucid_core.mermaid_import import parse_mermaid, standard_import_document
from lucid_core.parse import compile_document, load_document
from lucid_core.render_markdown import render_markdown
from lucid_core.render_mermaid import mermaid_id, render_page_mermaid


FIXTURE = Path(__file__).parent / "fixtures" / "lucid_line_chain.json"


class LucidCoreTests(unittest.TestCase):
    def compiled(self):
        return compile_document(load_document(str(FIXTURE)), fetched_at="2026-01-01T00:00:00Z")

    def test_line_to_line_chain_is_resolved_and_dangling_is_diagnosed(self):
        compiled = self.compiled()
        page = compiled["logical"]["pages"][0]
        edges = {(e["from"], e["to"]) for e in page["edges"]}
        self.assertIn(("a-b", "a_b"), edges)
        self.assertIn(("a_b", "done"), edges)
        codes = {d["code"] for d in compiled["logical"]["diagnostics"]}
        self.assertIn("dangling_endpoint", codes)
        self.assertIn("ambiguous_or_unresolved_line", codes)

    def test_physical_ir_preserves_notes_data_groups_layers(self):
        compiled = self.compiled()
        items = compiled["physical"]["pages"][0]["items"]
        self.assertTrue(any(s["id"] == "note1" for s in items["shapes"]))
        self.assertTrue(any(s["id"] == "data1" for s in items["shapes"]))
        self.assertEqual(items["groups"][0]["id"], "group1")
        self.assertEqual(items["layers"][0]["id"], "layer1")

    def test_markdown_does_not_claim_api_order_is_process_steps(self):
        markdown = render_markdown(self.compiled())
        self.assertNotIn("Process Steps", markdown)
        self.assertIn("Entrypoints", markdown)
        self.assertIn("Expected Response?", markdown)

    def test_mermaid_ids_do_not_collide_and_labels_are_not_truncated(self):
        compiled = self.compiled()
        page = compiled["logical"]["pages"][0]
        self.assertNotEqual(mermaid_id("a-b"), mermaid_id("a_b"))
        output = render_page_mermaid(compiled, page)
        self.assertIn("Collect account number and call webhook get_account without truncating this long label", output)

    def test_diamond_is_not_automatically_mapped_to_dfcx_page(self):
        compiled = self.compiled()
        codes = {d["code"] for d in compiled["semantic"]["diagnostics"]}
        self.assertIn("decision_not_assumed_page", codes)

    def test_mermaid_standard_import_uses_text_not_textareas(self):
        nodes, edges = parse_mermaid('flowchart TD\n    A["Start"]\n    B{{"Decision"}}\n    A -->|"yes"| B\n')
        doc = standard_import_document("Sample", nodes, edges)
        shape = doc["pages"][0]["shapes"][0]
        line = doc["pages"][0]["lines"][0]
        self.assertIn("text", shape)
        self.assertNotIn("textAreas", shape)
        self.assertIn("text", line)


if __name__ == "__main__":
    unittest.main()

