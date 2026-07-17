import unittest
from lucid_ces.models import (
    ApplicationSpec, AgentSpec, Modality, ControlAuthority, SourceProvenance
)
from lucid_ces.serialization import from_dict, to_dict

class TestCesModels(unittest.TestCase):
    def test_serialization_roundtrip_preserves_unknown_fields(self):
        data = {
            "id": "agent_test",
            "displayName": "Test Agent",
            "kind": "llm_agent",
            "future_field_abc": "xyz", # unknown field
            "source": {
                "documentId": "doc_123",
                "pageId": "page_1"
            }
        }
        
        # Deserialize
        agent = from_dict(AgentSpec, data)
        self.assertEqual(agent.id, "agent_test")
        self.assertEqual(agent.displayName, "Test Agent")
        self.assertEqual(agent.unknown_fields.get("future_field_abc"), "xyz")
        
        # Serialize
        serialized = to_dict(agent)
        self.assertEqual(serialized["id"], "agent_test")
        self.assertEqual(serialized["future_field_abc"], "xyz")
        self.assertNotIn("unknown_fields", serialized)

    def test_enums_mapping(self):
        self.assertEqual(Modality.MUST.value, "MUST")
        self.assertEqual(ControlAuthority.MODEL_INSTRUCTION.value, "MODEL_INSTRUCTION")

if __name__ == "__main__":
    unittest.main()
