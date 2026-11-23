"""PR #298: streaming inspect CLI preserves exact wire format and status.

All records are synthetic; no real history or production files are accessed.
"""
from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import ario_agent


class StreamingInspectionOutputTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.ledger = Path(temporary.name) / "scratch.jsonl"

    def write_events(self, events):
        original = b"".join(
            (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8")
            for event in events
        )
        self.ledger.write_bytes(original)
        return original

    def test_real_cli_returns_exact_legacy_json_for_complete_history(self):
        raw = self.write_events([
            {"event": "TASK_STARTED", "task_id": "T", "goal": "معاینه",
             "step_ids": ["one"], "success_criteria_ids": []},
            {"event": "STEP_OBSERVED", "task_id": "T", "step_id": "one",
             "tool": "read_text", "timestamp": "t", "status": "SUCCEEDED"},
            {"event": "TASK_FINISHED", "task_id": "T", "status": "COMPLETED"},
        ])
        expected_report = ario_agent.inspect_task_history("T", self.ledger)
        expected_line = json.dumps(
            expected_report, ensure_ascii=False, sort_keys=True
        ) + "\n"
        out = io.StringIO()
        with redirect_stdout(out):
            exit_code = ario_agent.main([
                "--inspect-task-id", "T", "--ledger", str(self.ledger)
            ])
        self.assertEqual(exit_code, 0)
        self.assertEqual(out.getvalue(), expected_line)
        self.assertEqual(self.ledger.read_bytes(), raw)

    def test_real_cli_preserves_inherited_workflow_unknown(self):
        raw = self.write_events([
            {"event": "TASK_STARTED", "task_id": "T", "goal": "x",
             "step_ids": [], "success_criteria_ids": []},
            {"event": "TASK_FINISHED", "task_id": "T", "status": "STOPPED"},
            {"event": "WORKFLOW_STAGE_OBSERVED", "task_id": "T",
             "workflow_id": "W", "status": "STOPPED"},
        ])
        expected_report = ario_agent.inspect_task_history("T", self.ledger)
        self.assertEqual(expected_report["status"], "UNKNOWN")
        out = io.StringIO()
        with redirect_stdout(out):
            exit_code = ario_agent.main([
                "--inspect-task-id", "T", "--ledger", str(self.ledger)
            ])
        self.assertEqual(exit_code, 2)
        self.assertEqual(
            out.getvalue(), json.dumps(expected_report, ensure_ascii=False, sort_keys=True) + "\n"
        )
        self.assertEqual(self.ledger.read_bytes(), raw)

    def test_streaming_cli_never_calls_monolithic_json_dumps(self):
        report = {
            "task_id": "A", "status": "STOPPED", "automatic_resume": False,
            "write_performed": False, "observed_steps": [
                {"step_id": str(i), "tool": "\U0001f642" * 50_000,
                 "status": "SUCCEEDED"} for i in range(16)
            ],
        }
        expected = json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n"

        class CountingOutput:
            def __init__(self):
                self.count = 0
                self.digest = hashlib.sha256()
                self.fragments = 0

            def write(self, text):
                if len(text) > 500_000:
                    raise AssertionError("CLI emitted one unbounded JSON fragment")
                self.fragments += 1
                self.count += len(text)
                self.digest.update(text.encode("utf-8"))

        sink = CountingOutput()
        with patch.object(ario_agent, "inspect_task_history", return_value=report), patch.object(
            ario_agent.json, "dumps", side_effect=AssertionError(
                "CLI inspect must not use monolithic json.dumps"
            )
        ), patch.object(ario_agent.sys, "stdout", sink):
            exit_code = ario_agent.main([
                "--inspect-task-id", "A", "--ledger", str(self.ledger)
            ])
        self.assertEqual(exit_code, 0)
        self.assertGreater(sink.fragments, 16)
        self.assertEqual(sink.count, len(expected))
        self.assertEqual(sink.digest.hexdigest(), hashlib.sha256(
            expected.encode("utf-8")
        ).hexdigest())

    def test_nonterminal_inspection_still_exit_two_without_rewriting(self):
        raw = self.write_events([
            {"event": "TASK_STARTED", "task_id": "T", "goal": "x",
             "step_ids": ["s"], "success_criteria_ids": []},
            {"event": "STEP_OBSERVED", "task_id": "T", "step_id": "s",
             "tool": "read_text", "status": "SUCCEEDED"},
        ])
        out = io.StringIO()
        with redirect_stdout(out):
            exit_code = ario_agent.main([
                "--inspect-task-id", "T", "--ledger", str(self.ledger)
            ])
        self.assertEqual(exit_code, 2)
        self.assertEqual(json.loads(out.getvalue())["status"], "INCOMPLETE")
        self.assertEqual(self.ledger.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
