#!/usr/bin/env python3
"""Unit tests for run_roleplay.py.

Verifies the offline mock mode, the live path structure using unittest.mock,
utility helpers, and the exit codes based on evaluation outcomes.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Sibling path insertion
_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import run_roleplay as rr


class TestRunRoleplay(unittest.TestCase):

    def setUp(self):
        # Create temp files for customer context and design spec
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ctx_path = os.path.join(self.temp_dir.name, "customer_context.json")
        self.spec_path = os.path.join(self.temp_dir.name, "design_spec.md")
        self.out_path = os.path.join(self.temp_dir.name, "output.json")

        self.ctx_data = {
            "name": "Sarah Connor",
            "mood": "impatient",
            "goal": "cancel subscription and get a full refund",
            "constraint": "refuse discount offers, insist on speaking to a manager"
        }
        with open(self.ctx_path, "w", encoding="utf-8") as f:
            json.dump(self.ctx_data, f)

        self.spec_data = """# Billing Spec
        - Verify customer identity.
        - Set callType to billing_dispute before handoff.
        """
        with open(self.spec_path, "w", encoding="utf-8") as f:
            f.write(self.spec_data)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_clean_json_text(self):
        # Normal JSON
        self.assertEqual(rr.clean_json_text('{"a": 1}'), '{"a": 1}')
        # Wrapped in backticks
        self.assertEqual(rr.clean_json_text('```json\n{"a": 1}\n```'), '{"a": 1}')
        self.assertEqual(rr.clean_json_text('```\n{"a": 2}\n```'), '{"a": 2}')

    def test_mock_mode_success(self):
        # Configure arguments for mock run
        args = [
            "run_roleplay.py",
            "--customer-context", self.ctx_path,
            "--design-spec", self.spec_path,
            "--mock",
            "--output", self.out_path
        ]

        # Run main
        with patch.object(sys, "argv", args):
            exit_code = rr.main()
        self.assertEqual(exit_code, 0)

        # Verify output file
        self.assertTrue(os.path.exists(self.out_path))
        with open(self.out_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("transcript", data)
            self.assertIn("evaluation", data)
            self.assertTrue(data["evaluation"]["passed"])
            self.assertEqual(data["evaluation"]["agent_mood_handling_score"], 5)

    @patch("run_roleplay.call_gemini_mock_evaluator")
    def test_mock_mode_failure(self, mock_evaluator):
        # Configure evaluator to return failed evaluation
        mock_evaluator.return_value = json.dumps({
            "passed": False,
            "reasoning": "The agent failed to verify identity.",
            "violations": ["identity_verification_missing"],
            "goal_resolved": False,
            "agent_mood_handling_score": 1
        })

        args = [
            "run_roleplay.py",
            "--customer-context", self.ctx_path,
            "--design-spec", self.spec_path,
            "--mock"
        ]

        with patch.object(sys, "argv", args):
            exit_code = rr.main()
        self.assertEqual(exit_code, 1)

    @patch("run_roleplay.call_gemini")
    @patch("run_roleplay.CES")
    def test_live_path_structure_with_mocks(self, mock_ces_class, mock_call_gemini):
        # Set up mock CES instance
        mock_ces = MagicMock()
        mock_ces_class.return_value = mock_ces
        mock_ces.project = "test-project"
        mock_ces.location = "us"
        mock_ces._get_token.return_value = "fake-token"
        mock_ces.deployment_id = "test-deployment"

        # Mock run_session replies:
        # First for start session event, second for customer statement
        mock_ces.run_session.side_effect = [
            # Greeting
            {
                "outputs": [{
                    "text": "Hello! Welcome to support.",
                    "diagnosticInfo": {"messages": [{"role": "router"}]}
                }]
            },
            # Second turn response
            {
                "outputs": [{
                    "text": "I can help with that. Email?",
                    "diagnosticInfo": {"messages": [{"role": "billing"}]}
                }]
            }
        ]

        # Mock call_gemini responses:
        # First for Customer statement, second for Evaluator JSON
        mock_call_gemini.side_effect = [
            # Customer statement
            {
                "candidates": [{
                    "content": {
                        "parts": [{"text": "Hello, my name is Sarah Connor. I want a refund. <hangup>"}]
                    }
                }]
            },
            # Evaluator response
            {
                "candidates": [{
                    "content": {
                        "parts": [{"text": '{"passed": true, "reasoning": "Good", "violations": [], "goal_resolved": true}'}]
                    }
                }]
            }
        ]

        # Configure arguments without --mock
        args = [
            "run_roleplay.py",
            "--customer-context", self.ctx_path,
            "--design-spec", self.spec_path,
            "--max-turns", "1"
        ]

        # Run main to verify live execution logic matches mocks
        with patch.object(sys, "argv", args):
            exit_code = rr.main()
        self.assertEqual(exit_code, 0)

        # Verify interaction with mocked CES and Gemini functions
        self.assertEqual(mock_ces.run_session.call_count, 2)
        self.assertEqual(mock_call_gemini.call_count, 2)


if __name__ == "__main__":
    unittest.main()
