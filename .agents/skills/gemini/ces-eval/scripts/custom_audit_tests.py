#!/usr/bin/env python3
"""Custom independent integration tests for run_roleplay.py victory audit.
Verifies the CLI, transcript generation, mock execution flow, and exit codes.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

# Insert script path
_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import run_roleplay as rr


class TestVictoryAuditIntegration(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ctx_file = os.path.join(self.temp_dir.name, "ctx.json")
        self.spec_file = os.path.join(self.temp_dir.name, "spec.md")
        self.out_file = os.path.join(self.temp_dir.name, "out.json")

        self.ctx_data = {
            "name": "Audit Customer",
            "mood": "frustrated",
            "goal": "check bill details",
            "constraint": "do not agree to upgrade"
        }
        with open(self.ctx_file, "w", encoding="utf-8") as f:
            json.dump(self.ctx_data, f)

        self.spec_data = "Billing spec checklist: check verification."
        with open(self.spec_file, "w", encoding="utf-8") as f:
            f.write(self.spec_data)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_mock_flow_and_transcript_assembly(self):
        """Test that running with --mock collects turns into a properly structured transcript."""
        args = [
            "run_roleplay.py",
            "--customer-context", self.ctx_file,
            "--design-spec", self.spec_file,
            "--mock",
            "--output", self.out_file,
            "--max-turns", "4"
        ]

        with patch.object(sys, "argv", args):
            exit_code = rr.main()

        self.assertEqual(exit_code, 0, "Mock mode execution failed")
        self.assertTrue(os.path.exists(self.out_file), "Output file was not written")

        with open(self.out_file, "r", encoding="utf-8") as f:
            output = json.load(f)

        self.assertIn("transcript", output)
        self.assertIn("evaluation", output)

        transcript = output["transcript"]
        self.assertIn("Audit Customer", transcript)
        self.assertIn("check bill details", transcript)
        self.assertIn("Agent:", transcript)
        self.assertIn("Customer:", transcript)

        # Check dialogue sequence
        lines = transcript.splitlines()
        self.assertTrue(any(line.startswith("Agent:") for line in lines))
        self.assertTrue(any(line.startswith("Customer:") for line in lines))

        evaluation = output["evaluation"]
        self.assertIn("passed", evaluation)
        self.assertTrue(evaluation["passed"])
        self.assertEqual(evaluation["agent_mood_handling_score"], 5)

    def test_mock_mode_bypass_token_requirement(self):
        """Test that --mock bypasses actual Google token fetch/authorization."""
        # We will mock CES._get_token to raise an exception.
        # Since it is mock mode, CES._get_token should NEVER be called!
        # If it is called, the test will fail.
        with patch("ces_client.CES._get_token", side_effect=AssertionError("Token should not be fetched in mock mode")):
            args = [
                "run_roleplay.py",
                "--customer-context", self.ctx_file,
                "--design-spec", self.spec_file,
                "--mock"
            ]
            with patch.object(sys, "argv", args):
                exit_code = rr.main()
            self.assertEqual(exit_code, 0)

    def test_failed_evaluation_returns_exit_code_1(self):
        """Test that when evaluation fails, exit code 1 is correctly returned."""
        # Mock the evaluator to return passed: False
        with patch("run_roleplay.call_gemini_mock_evaluator") as mock_eval:
            mock_eval.return_value = json.dumps({
                "passed": False,
                "reasoning": "Audit failed: goal not resolved",
                "violations": ["goal_not_resolved"],
                "goal_resolved": False,
                "agent_mood_handling_score": 2
            })

            args = [
                "run_roleplay.py",
                "--customer-context", self.ctx_file,
                "--design-spec", self.spec_file,
                "--mock"
            ]
            with patch.object(sys, "argv", args):
                exit_code = rr.main()

            self.assertEqual(exit_code, 1, "Expected exit code 1 when evaluation fails")


if __name__ == "__main__":
    unittest.main()
