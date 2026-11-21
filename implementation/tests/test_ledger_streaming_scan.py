"""Read-only bounded streaming of historic Agent/Workflow JSONL records."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ario_agent
import ario_workflow
import ledger_streaming
from ario_agent import AgentRequestError, _ensure_task_id_unused, inspect_task_history
from ario_workflow import _ensure_workflow_id_unused
from ledger_streaming import LedgerLineLimitExceeded, iter_bounded_ledger_lines


class StreamedLedgerReaderTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.ledger = self.root / "historical.jsonl"

    def write_events(self, events, newline="\n"):
        raw = newline.join(json.dumps(event, ensure_ascii=False) for event in events) + newline
        self.ledger.write_bytes(raw.encode("utf-8"))
        return self.ledger.read_bytes()

    def test_utf8_bom_crlf_blank_and_legacy_line_numbers(self):
        self.ledger.write_bytes(
            b"\xef\xbb\xbf" + b'{"event":"NOTE"}\r\n\r\n{"event":"TASK_STARTED"}\n'
        )
        self.assertEqual(list(iter_bounded_ledger_lines(self.ledger)), [
            (1, '{"event":"NOTE"}'), (2, ""), (3, '{"event":"TASK_STARTED"}'),
        ])

    def test_unicode_splitline_inside_json_fails_closed_like_historical_splitlines(self):
        payload = '{"event":"TASK_STARTED","task_id":"TASK-X","goal":"a\u2028b"}\n'
        self.ledger.write_bytes(payload.encode("utf-8"))
        before = self.ledger.read_bytes()
        with self.assertRaisesRegex(AgentRequestError, "malformed at line 1"):
            _ensure_task_id_unused(self.ledger, "NEW")
        self.assertEqual(inspect_task_history("TASK-X", self.ledger)["status"], "UNKNOWN")
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_no_total_file_ceiling_for_many_unrelated_entries(self):
        events = [{"event": "NOTE", "task_id": f"other-{i}", "workflow_id": f"wf-{i}"} for i in range(2000)]
        original = self.write_events(events)
        with patch.object(Path, "read_text", side_effect=AssertionError("whole-file read forbidden")):
            _ensure_task_id_unused(self.ledger, "unused")
            _ensure_workflow_id_unused(self.ledger, "unused")
            result = inspect_task_history("unused", self.ledger)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["event_count"], 0)
        self.assertEqual(self.ledger.read_bytes(), original)

    def test_duplicate_checks_stop_before_any_append(self):
        original = self.write_events([
            {"event": "NOTE", "task_id": "used-task", "workflow_id": "used-workflow"},
            {"event": "NOTE", "task_id": "other", "workflow_id": "other"},
        ])
        with self.assertRaisesRegex(AgentRequestError, "refusing duplicate execution"):
            _ensure_task_id_unused(self.ledger, "used-task")
        with self.assertRaisesRegex(AgentRequestError, "refusing duplicate execution"):
            _ensure_workflow_id_unused(self.ledger, "used-workflow")
        self.assertEqual(self.ledger.read_bytes(), original)

    def test_long_line_is_not_parsed_partially(self):
        self.ledger.write_bytes(json.dumps({"event": "NOTE", "task_id": "NEW", "pad": "x" * 128}).encode() + b"\n")
        before = self.ledger.read_bytes()
        with patch.object(ledger_streaming, "MAX_LEDGER_LINE_CHARS", 64):
            with self.assertRaisesRegex(AgentRequestError, "exceeds 64 characters"):
                _ensure_task_id_unused(self.ledger, "unused")
            with self.assertRaisesRegex(AgentRequestError, "exceeds 64 characters"):
                _ensure_workflow_id_unused(self.ledger, "unused")
            inspected = inspect_task_history("NEW", self.ledger)
        self.assertEqual(inspected["status"], "UNKNOWN")
        self.assertFalse(inspected["write_performed"])
        self.assertFalse(inspected["automatic_resume"])
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_limit_exact_and_one_more_fails_closed(self):
        self.ledger.write_bytes(b"x" * 32)
        with patch.object(ledger_streaming, "MAX_LEDGER_LINE_CHARS", 32):
            self.assertEqual(list(iter_bounded_ledger_lines(self.ledger)), [(1, "x" * 32)])
            self.ledger.write_bytes(b"x" * 33)
            with self.assertRaises(LedgerLineLimitExceeded):
                list(iter_bounded_ledger_lines(self.ledger))

    def test_malformed_unicode_has_explicit_unknown_or_rejection(self):
        self.ledger.write_bytes(b'{"event":"NOTE"}\n' + b'{"event":"BAD","task_id":"NEW","raw":"\xff"}\n')
        original = self.ledger.read_bytes()
        with self.assertRaisesRegex(AgentRequestError, "invalid UTF-8"):
            _ensure_task_id_unused(self.ledger, "NEW")
        with self.assertRaisesRegex(AgentRequestError, "invalid UTF-8"):
            _ensure_workflow_id_unused(self.ledger, "NEW")
        history = inspect_task_history("NEW", self.ledger)
        self.assertEqual(history["status"], "UNKNOWN")
        self.assertEqual(history["write_performed"], False)
        self.assertEqual(self.ledger.read_bytes(), original)

    def test_completed_history_projects_only_required_fields(self):
        events = [
            {"event": "TASK_STARTED", "task_id": "DONE", "goal": "ok", "step_ids": ["s1"], "success_criteria_ids": []},
            {"event": "STEP_OBSERVED", "task_id": "DONE", "step_id": "s1", "tool": "read_text", "status": "SUCCEEDED", "timestamp": "t", "observation": {"content": "x" * 10000}},
            {"event": "TASK_FINISHED", "task_id": "DONE", "status": "COMPLETED"},
        ]
        original = self.write_events(events)
        result = inspect_task_history("DONE", self.ledger)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["event_count"], 3)
        self.assertEqual(result["observed_steps"], [{"step_id": "s1", "tool": "read_text", "status": "SUCCEEDED", "timestamp": "t"}])
        self.assertEqual(result["goal"], "ok")
        self.assertFalse(result["automatic_resume"])
        self.assertEqual(self.ledger.read_bytes(), original)

    def test_truncated_and_malformed_records_are_not_ignored(self):
        self.ledger.write_bytes(b'{"event":"TASK_STARTED","task_id":"X"}\nnot-json\n')
        original = self.ledger.read_bytes()
        with self.assertRaisesRegex(AgentRequestError, "malformed at line 2"):
            _ensure_task_id_unused(self.ledger, "NEW")
        result = inspect_task_history("X", self.ledger)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("line 2", result["error"])
        self.assertEqual(self.ledger.read_bytes(), original)

    def test_excess_matching_task_events_return_unknown_without_truncation(self):
        original = self.write_events(
            [{"event": "TASK_STARTED", "task_id": "X", "goal": "g"}] +
            [{"event": "STEP_OBSERVED", "task_id": "X", "step_id": str(i), "status": "SUCCEEDED"} for i in range(8)]
        )
        with patch.object(ario_agent, "MAX_TASK_HISTORY_EVENTS", 4):
            result = inspect_task_history("X", self.ledger)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("event-count limit", result["error"])
        self.assertFalse(result["automatic_resume"])
        self.assertEqual(self.ledger.read_bytes(), original)

    def test_missing_ledger_is_unknown_or_empty_for_duplicate_scans(self):
        _ensure_task_id_unused(self.ledger, "A")
        _ensure_workflow_id_unused(self.ledger, "B")
        result = inspect_task_history("X", self.ledger)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertFalse(result["write_performed"])


if __name__ == "__main__":
    unittest.main()
