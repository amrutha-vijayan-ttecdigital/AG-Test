import unittest
from pathlib import Path
from lucid_core.parse import compile_document, load_document
from lucid_ces.compile import compile_design
from lucid_ces.context_packet import generate_context_packet

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ces_mock_lucid.json"

class TestCesContextPacket(unittest.TestCase):
    def setUp(self):
        raw = load_document(str(FIXTURE_PATH))
        compiled = compile_document(raw, document_id="doc_ces_test")
        self.ces_ir = compile_design(compiled)

    def test_generate_context_packet_agent_filtering(self):
        packet = generate_context_packet(
            self.ces_ir,
            agent_id="agent_billing",
            task="Update confirmation messages",
            radius=1
        )
        self.assertIn("Billing Agent", packet)
        self.assertIn("Update confirmation messages", packet)
        # Verify it includes the "not implied" section
        self.assertIn("Explicit Guidelines & Invariants (Not Implied)", packet)

    def test_context_packet_size_pruning(self):
        packet = generate_context_packet(
            self.ces_ir,
            agent_id="agent_billing",
            max_chars=100
        )
        self.assertTrue(len(packet) <= 150) # Allow small overhead for truncation notice
        self.assertIn("Truncated", packet)

if __name__ == "__main__":
    unittest.main()
