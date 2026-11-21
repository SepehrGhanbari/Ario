"""Independent v0 review follow-up: no side-effect JSONL streaming call-chain checks.

All ledgers and workspace files are synthetic and stored in TemporaryDirectory.
This suite intentionally DOES NOT change historical semantics or resource caps.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ario_agent
import ario_workflow
from ario_agent import AgentRequestError, inspect_task_history
from ledger_streaming import iter_bounded_ledger_lines


def task(task_id: str) -> dict:
    return {
        "task_id": task_id,
        "goal": "Verify a synthetic workspace safely",
        "actions": [{"step_id": "inspect", "tool": "read_text", "path": "evidence.txt"}],
    }


def workflow(workflow_id: str, task_id: str) -> dict:
    return {
        "workflow_id": workflow_id,
        "goal": "Verify a synthetic workflow safely",
        "stages": [{"stage_id": "first", "task": task(task_id)}],
    }


class V0StreamingFollowUp(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.ledger = self.root / "historical.jsonl"
        (self.root / "evidence.txt").write_text("preserve", encoding="utf-8")

    def write_records(self, records, *, final_newline=True):
        raw = b"\n".join(json.dumps(record).encode("utf-8") for record in records)
        if final_newline:
            raw += b"\n"
        self.ledger.write_bytes(raw)
        return raw

    def assert_unchanged(self, original):
        self.assertEqual(self.ledger.read_bytes(), original)
        self.assertEqual((self.root / "evidence.txt").read_text(encoding="utf-8"), "preserve")
        self.assertFalse(Path(str(self.ledger) + ".lock").exists())
        self.assertFalse(Path(str(self.ledger) + ".workflow.lock").exists())

    def test_legacy_line_boundary_differential(self):
        cases = {
            "LF": b"a\nb\n",
            "CRLF": b"a\r\nb\r\n",
            "CR": b"a\rb\r",
            "BOM": b"\xef\xbb\xbf" + b'{"event":"NOTE"}\n',
            "empty": b"",
            "blank": b"\n\r\n",
            "unterminated": b'{"event":"NOTE"}',
            "Unicode LS": "a\u2028b\n".encode("utf-8"),
            "Unicode PS": "a\u2029b\n".encode("utf-8"),
            "Unicode NEL": "a\u0085b\n".encode("utf-8"),
            "escaped newline": b'{"value":"a\\nb"}\n',
            "malformed": b"{oops\n",
            "invalid UTF8": b"{\xff}\n",
        }
        for label, raw in cases.items():
            with self.subTest(label=label):
                self.ledger.write_bytes(raw)
                if label == "invalid UTF8":
                    with self.assertRaises(UnicodeDecodeError):
                        self.ledger.read_text(encoding="utf-8-sig").splitlines()
                    with self.assertRaises(UnicodeDecodeError):
                        list(iter_bounded_ledger_lines(self.ledger))
                    continue
                old = self.ledger.read_text(encoding="utf-8-sig").splitlines()
                new = [line for _, line in iter_bounded_ledger_lines(self.ledger)]
                self.assertEqual(old, new)
                self.assertEqual(self.ledger.read_bytes(), raw)

    def test_duplicate_task_at_first_middle_last_blocks_real_entrypoint(self):
        for position in range(3):
            with self.subTest(position=position):
                records = [
                    {"event": "NOTE", "task_id": "other-0"},
                    {"event": "NOTE", "task_id": "other-1"},
                    {"event": "NOTE", "task_id": "other-2"},
                ]
                records[position]["task_id"] = "TASK-USED"
                original = self.write_records(records, final_newline=position != 2)
                with patch.object(ario_agent, "execute_action") as execute, patch.object(
                    ario_agent, "_append_event"
                ) as append:
                    with self.assertRaisesRegex(AgentRequestError, "duplicate execution"):
                        ario_agent.run_task(task("TASK-USED"), self.root, self.ledger)
                execute.assert_not_called()
                append.assert_not_called()
                self.assert_unchanged(original)

    def test_duplicate_workflow_at_first_middle_last_blocks_real_entrypoint(self):
        for position in range(3):
            with self.subTest(position=position):
                records = [
                    {"event": "NOTE", "workflow_id": "other-0"},
                    {"event": "NOTE", "workflow_id": "other-1"},
                    {"event": "NOTE", "workflow_id": "other-2"},
                ]
                records[position]["workflow_id"] = "WF-USED"
                original = self.write_records(records, final_newline=position != 2)
                with patch.object(ario_workflow, "run_task") as execute, patch.object(
                    ario_workflow, "_append_event"
                ) as append:
                    with self.assertRaisesRegex(AgentRequestError, "duplicate execution"):
                        ario_workflow.run_workflow(workflow("WF-USED", "TASK-NEW"), self.root, self.ledger)
                execute.assert_not_called()
                append.assert_not_called()
                self.assert_unchanged(original)

    def test_workflow_preflights_later_task_id_before_first_stage(self):
        records = [{"event": "NOTE", "task_id": "other"}] * 3 + [
            {"event": "TASK_FINISHED", "task_id": "TASK-USED", "status": "COMPLETED"}
        ]
        original = self.write_records(records, final_newline=False)
        payload = workflow("WF-NEW", "TASK-USED")
        with patch.object(ario_workflow, "run_task") as execute, patch.object(
            ario_workflow, "_append_event"
        ) as append:
            with self.assertRaisesRegex(AgentRequestError, "duplicate execution"):
                ario_workflow.run_workflow(payload, self.root, self.ledger)
        execute.assert_not_called()
        append.assert_not_called()
        self.assert_unchanged(original)

    def test_malformed_late_record_blocks_both_entrypoints(self):
        original = b'{"event":"NOTE","task_id":"other"}\n{"event":"NOTE"}\nnot-json\n'
        self.ledger.write_bytes(original)
        with patch.object(ario_agent, "execute_action") as agent_action, patch.object(
            ario_agent, "_append_event"
        ) as agent_append, patch.object(
            ario_workflow, "run_task"
        ) as wf_action, patch.object(
            ario_workflow, "_append_event"
        ) as wf_append:
            with self.assertRaisesRegex(AgentRequestError, "malformed"):
                ario_agent.run_task(task("TASK-NEW"), self.root, self.ledger)
            with self.assertRaisesRegex(AgentRequestError, "malformed"):
                ario_workflow.run_workflow(workflow("WF-NEW", "TASK-NEW"), self.root, self.ledger)
        agent_action.assert_not_called()
        agent_append.assert_not_called()
        wf_action.assert_not_called()
        wf_append.assert_not_called()
        self.assertEqual(inspect_task_history("TASK-NEW", self.ledger)["status"], "UNKNOWN")
        self.assert_unchanged(original)

    def test_crash_history_never_promotes_incomplete_to_completed(self):
        original = self.write_records([
            {"event": "TASK_STARTED", "task_id": "TASK-CRASH", "goal": "unfinished", "step_ids": ["s1"]},
            {"event": "STEP_OBSERVED", "task_id": "TASK-CRASH", "step_id": "s1", "status": "SUCCEEDED"},
        ], final_newline=False)
        assessment = inspect_task_history("TASK-CRASH", self.ledger)
        self.assertEqual(assessment["status"], "INCOMPLETE")
        self.assertFalse(assessment["automatic_resume"])
        self.assertFalse(assessment["write_performed"])
        self.assert_unchanged(original)

    def test_actual_maximum_failure_diagnostics_task_is_safe_to_inspect(self):
        actions = [
            {"step_id": f"step-{i}", "tool": "read_text", "path": "evidence.txt"}
            for i in range(7)
        ] + [{"step_id": "step-fail", "tool": "read_text", "path": "missing.txt"}]
        diagnostics = [
            {"step_id": f"diag-{i}", "tool": "inspect_directory", "path": "."}
            for i in range(8)
        ]
        payload = {
            "task_id": "TASK-DIAG-8",
            "goal": "Exercise maximum failure diagnostics",
            "actions": actions,
            "failure_diagnostics": diagnostics,
        }
        result = ario_agent.run_task(payload, self.root, self.ledger)
        self.assertEqual(result["status"], "STOPPED")
        original = self.ledger.read_bytes()
        assessment = inspect_task_history("TASK-DIAG-8", self.ledger)
        self.assertEqual(assessment["status"], "STOPPED")
        self.assertEqual(assessment["event_count"], 18)
        self.assertFalse(assessment["automatic_resume"])
        self.assertFalse(assessment["write_performed"])
        self.assert_unchanged(original)

    def test_too_many_matching_events_do_not_produce_positive_recovery(self):
        records = [
            {"event": "TASK_STARTED", "task_id": "TASK-CAP", "goal": "g", "step_ids": []}
        ] + [
            {"event": "STEP_OBSERVED", "task_id": "TASK-CAP", "status": "SUCCEEDED", "step_id": str(i)}
            for i in range(4)
        ] + [
            {"event": "TASK_FINISHED", "task_id": "TASK-CAP", "status": "COMPLETED"}
        ]
        original = self.write_records(records)
        with patch.object(ario_agent, "MAX_TASK_HISTORY_EVENTS", 5):
            assessment = inspect_task_history("TASK-CAP", self.ledger)
        self.assertEqual(assessment["status"], "UNKNOWN")
        self.assertIn("event-count", assessment["error"])
        self.assertFalse(assessment["automatic_resume"])
        self.assert_unchanged(original)


if __name__ == "__main__":
    unittest.main()
