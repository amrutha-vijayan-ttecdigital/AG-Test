#!/usr/bin/env python3
import json
import os
import pathlib
import sys
import tempfile
import unittest
import subprocess
from unittest.mock import patch, MagicMock

# Sibling path insertion
_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import run_roleplay as rr
from ces_client import CES, load_env

class TestChallengeRoleplay(unittest.TestCase):

    def setUp(self):
        # Create temp files for customer context and design spec
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ctx_path = os.path.join(self.temp_dir.name, "customer_context.json")
        self.spec_path = os.path.join(self.temp_dir.name, "design_spec.md")
        self.out_path = os.path.join(self.temp_dir.name, "output.json")

        # Create valid context & spec to use as defaults
        self.valid_ctx = {
            "name": "John Doe",
            "mood": "happy",
            "goal": "inquire about plans",
            "constraint": "none"
        }
        with open(self.ctx_path, "w", encoding="utf-8") as f:
            json.dump(self.valid_ctx, f)

        self.valid_spec = "# Hello Spec"
        with open(self.spec_path, "w", encoding="utf-8") as f:
            f.write(self.valid_spec)

    def tearDown(self):
        self.temp_dir.cleanup()

    # --- 1. Customer Context Tests ---

    def test_malformed_customer_context_json(self):
        """Malformed JSON should handle the exception, write to stderr, and exit 1."""
        with open(self.ctx_path, "w", encoding="utf-8") as f:
            f.write("{invalid_json: 123}")

        args = [
            "run_roleplay.py",
            "--customer-context", self.ctx_path,
            "--design-spec", self.spec_path,
            "--mock"
        ]
        with patch.object(sys, "argv", args), patch("sys.stderr.write") as mock_stderr:
            exit_code = rr.main()
            self.assertEqual(exit_code, 1)
            mock_stderr.assert_called()
            self.assertIn("Error loading customer context", mock_stderr.call_args[0][0])

    def test_empty_customer_context_json(self):
        """Empty JSON object should use defaults and run successfully (exit 0)."""
        with open(self.ctx_path, "w", encoding="utf-8") as f:
            f.write("{}")

        args = [
            "run_roleplay.py",
            "--customer-context", self.ctx_path,
            "--design-spec", self.spec_path,
            "--mock"
        ]
        with patch.object(sys, "argv", args):
            exit_code = rr.main()
            self.assertEqual(exit_code, 0)

    def test_empty_file_customer_context(self):
        """Empty file (size 0) should fail with JSON decode error and exit 1."""
        with open(self.ctx_path, "w", encoding="utf-8") as f:
            f.write("")

        args = [
            "run_roleplay.py",
            "--customer-context", self.ctx_path,
            "--design-spec", self.spec_path,
            "--mock"
        ]
        with patch.object(sys, "argv", args), patch("sys.stderr.write") as mock_stderr:
            exit_code = rr.main()
            self.assertEqual(exit_code, 1)
            mock_stderr.assert_called()
            self.assertIn("Error loading customer context", mock_stderr.call_args[0][0])

    # --- 2. Design Spec Tests ---

    def test_empty_design_spec(self):
        """Empty design spec should run successfully (exit 0) in mock mode."""
        with open(self.spec_path, "w", encoding="utf-8") as f:
            f.write("")

        args = [
            "run_roleplay.py",
            "--customer-context", self.ctx_path,
            "--design-spec", self.spec_path,
            "--mock"
        ]
        with patch.object(sys, "argv", args):
            exit_code = rr.main()
            self.assertEqual(exit_code, 0)

    # --- 3. Evaluator response validation ---

    @patch("run_roleplay.call_gemini_mock_evaluator")
    def test_evaluator_malformed_json_response(self, mock_evaluator):
        """If the LLM returns invalid JSON, the script should catch it and exit 1."""
        mock_evaluator.return_value = "{malformed_json"

        args = [
            "run_roleplay.py",
            "--customer-context", self.ctx_path,
            "--design-spec", self.spec_path,
            "--mock"
        ]
        with patch.object(sys, "argv", args), patch("sys.stderr.write") as mock_stderr:
            exit_code = rr.main()
            self.assertEqual(exit_code, 1)
            mock_stderr.assert_called()
            self.assertIn("Error parsing evaluator JSON output", mock_stderr.call_args[0][0])

    @patch("run_roleplay.call_gemini_mock_evaluator")
    def test_evaluator_invalid_schema_list(self, mock_evaluator):
        """If the LLM returns a JSON list instead of an object, it should be caught and exit with code 1."""
        mock_evaluator.return_value = "[true, false]"

        args = [
            "run_roleplay.py",
            "--customer-context", self.ctx_path,
            "--design-spec", self.spec_path,
            "--mock"
        ]
        with patch.object(sys, "argv", args), patch("sys.stderr.write") as mock_stderr:
            exit_code = rr.main()
            self.assertEqual(exit_code, 1)
            mock_stderr.assert_called()

    @patch("run_roleplay.call_gemini_mock_evaluator")
    def test_evaluator_violations_null(self, mock_evaluator):
        """If 'violations' key is null, the script should not crash and should exit based on passed."""
        mock_evaluator.return_value = json.dumps({
            "passed": True,
            "reasoning": "Fine",
            "violations": None,
            "goal_resolved": True,
            "agent_mood_handling_score": 5
        })

        args = [
            "run_roleplay.py",
            "--customer-context", self.ctx_path,
            "--design-spec", self.spec_path,
            "--mock"
        ]
        with patch.object(sys, "argv", args):
            exit_code = rr.main()
            self.assertEqual(exit_code, 0)

    @patch("run_roleplay.call_gemini_mock_evaluator")
    def test_evaluator_violations_invalid_type_string(self, mock_evaluator):
        """If 'violations' is a string, it should be wrapped in a list and printed as a whole string."""
        mock_evaluator.return_value = json.dumps({
            "passed": True,
            "reasoning": "Fine",
            "violations": "none",
            "goal_resolved": True,
            "agent_mood_handling_score": 5
        })

        args = [
            "run_roleplay.py",
            "--customer-context", self.ctx_path,
            "--design-spec", self.spec_path,
            "--mock"
        ]
        with patch.object(sys, "argv", args), patch("sys.stdout.write") as mock_stdout:
            exit_code = rr.main()
            self.assertEqual(exit_code, 0)
            # Find the print output of violations
            printed = "".join([call[0][0] for call in mock_stdout.call_args_list])
            self.assertIn("Violations:         none", printed)

    @patch("run_roleplay.call_gemini_mock_evaluator")
    def test_evaluator_violations_invalid_list_types(self, mock_evaluator):
        """If 'violations' list contains non-string items, they should be converted to string safely."""
        mock_evaluator.return_value = json.dumps({
            "passed": True,
            "reasoning": "Fine",
            "violations": [123, 456],
            "goal_resolved": True,
            "agent_mood_handling_score": 5
        })

        args = [
            "run_roleplay.py",
            "--customer-context", self.ctx_path,
            "--design-spec", self.spec_path,
            "--mock"
        ]
        with patch.object(sys, "argv", args), patch("sys.stdout.write") as mock_stdout:
            exit_code = rr.main()
            self.assertEqual(exit_code, 0)
            printed = "".join([call[0][0] for call in mock_stdout.call_args_list])
            self.assertIn("Violations:         123, 456", printed)

    # --- 4. Missing Environment Variables Tests ---

    @patch.dict(os.environ, {}, clear=True)
    @patch("ces_client.find_kit_root")
    def test_missing_environment_variables_live(self, mock_find_kit_root):
        """In live mode, missing environment variables should cause main to catch SystemExit and return 1."""
        # Ensure load_env doesn't find .env file
        mock_find_kit_root.return_value = pathlib.Path(self.temp_dir.name)

        args = [
            "run_roleplay.py",
            "--customer-context", self.ctx_path,
            "--design-spec", self.spec_path
        ]
        
        with patch.object(sys, "argv", args), patch("sys.stderr.write") as mock_stderr:
            exit_code = rr.main()
            self.assertEqual(exit_code, 1)
            mock_stderr.assert_called()

    # --- 5. Token Refresh Failures & Invalid Credentials ---

    @patch("subprocess.check_output")
    def test_token_refresh_failures(self, mock_check_output):
        """If token fetching fails entirely, it raises RuntimeError."""
        # Mock both check_output to fail
        mock_check_output.side_effect = subprocess.CalledProcessError(1, "gcloud")

        c = CES(env={
            "GCP_PROJECT_ID": "test-project",
            "CES_APP_ID": "test-app",
            "GCP_REGION": "us",
        })
        with self.assertRaises(RuntimeError):
            c._get_token()

    # --- 6. Max Turns Tests ---

    @patch("run_roleplay.call_gemini_mock_evaluator")
    def test_max_turns_exceeded_passed(self, mock_evaluator):
        """If max turns is reached and evaluator passes, the exit code should be 0."""
        mock_evaluator.return_value = json.dumps({
            "passed": True,
            "reasoning": "Still passed somehow",
            "violations": [],
            "goal_resolved": False,
            "agent_mood_handling_score": 3
        })

        args = [
            "run_roleplay.py",
            "--customer-context", self.ctx_path,
            "--design-spec", self.spec_path,
            "--mock",
            "--max-turns", "1"
        ]
        with patch.object(sys, "argv", args):
            exit_code = rr.main()
            self.assertEqual(exit_code, 0)

    @patch("run_roleplay.call_gemini_mock_evaluator")
    def test_max_turns_exceeded_failed(self, mock_evaluator):
        """If max turns is reached and evaluator fails, the exit code should be 1."""
        mock_evaluator.return_value = json.dumps({
            "passed": False,
            "reasoning": "Failed to resolve goal in time",
            "violations": ["max_turns_exceeded"],
            "goal_resolved": False,
            "agent_mood_handling_score": 3
        })

        args = [
            "run_roleplay.py",
            "--customer-context", self.ctx_path,
            "--design-spec", self.spec_path,
            "--mock",
            "--max-turns", "1"
        ]
        with patch.object(sys, "argv", args):
            exit_code = rr.main()
            self.assertEqual(exit_code, 1)

if __name__ == "__main__":
    unittest.main()
