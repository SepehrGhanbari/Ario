"""Small synthetic regressions for the ledger budget evidence on PR #298."""
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import ario_agent
import ario_workflow
import ledger_budget_profile
import ledger_streaming


class StreamingBudgetEvidence(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.ledger = self.root / "events.jsonl"

    def test_maximum_criteria_path_and_workflow_matching_count(self):
        (self.root / "proof.txt").write_text("ok", encoding="utf-8")
        task = {
            "task_id": "example", "goal": "inspect",
            "actions": [{"tool": "read_text", "step_id": str(i), "path": "proof.txt"} for i in range(8)],
            "success_criteria": [
                {"criterion_id": str(i), "path": "proof.txt", "expected_text": "ok"} for i in range(8)
            ],
        }
        result = ario_agent.run_task(task, self.root, self.ledger)
        self.assertEqual(result["status"], "COMPLETED")
        history = ario_agent.inspect_task_history("example", self.ledger)
        self.assertEqual((history["status"], history["event_count"]), ("COMPLETED", 18))

        task["task_id"] = "stage-task"
        task["success_criteria"][0]["expected_text"] = "missing"
        workflow = {"workflow_id": "workflow", "goal": "inspect",
                    "stages": [{"stage_id": "stage", "task": task}]}
        result = ario_workflow.run_workflow(workflow, self.root, self.ledger)
        self.assertEqual(result["status"], "STOPPED")
        profile = ledger_budget_profile.profile_ledger(self.ledger)
        self.assertEqual(profile["status"], "OBSERVED")
        self.assertEqual(profile["max_matching_task_events"], 19)
        self.assertEqual(profile["tasks_over_18_events"], 1)

    def test_exact_matching_event_ceiling(self):
        records = [{"event": "TASK_STARTED", "task_id": "example"}]
        records.extend({"event": "NOTE", "task_id": "example"} for _ in range(126))
        records.append({"event": "TASK_FINISHED", "task_id": "example", "status": "STOPPED"})
        self.ledger.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        history = ario_agent.inspect_task_history("example", self.ledger)
        self.assertEqual((history["status"], history["event_count"]), ("STOPPED", 128))
        with self.ledger.open("ab") as stream:
            stream.write(b'{"event":"NOTE","task_id":"example"}\n')
        history = ario_agent.inspect_task_history("example", self.ledger)
        self.assertEqual(history["status"], "UNKNOWN")
        self.assertIn("event-count limit", history["error"])

    def test_four_byte_text_and_crlf_at_boundary(self):
        line = json.dumps({"event": "NOTE", "text": "\U0001f642" * 128}, ensure_ascii=False)
        self.ledger.write_bytes((line + "\r\n").encode("utf-8"))
        with patch.object(ledger_streaming, "MAX_LEDGER_LINE_CHARS", len(line) + 1):
            self.assertEqual(list(ledger_streaming.iter_bounded_ledger_lines(self.ledger)), [(1, line)])
        with patch.object(ledger_streaming, "MAX_LEDGER_LINE_CHARS", len(line)):
            with self.assertRaises(ledger_streaming.LedgerLineLimitExceeded):
                list(ledger_streaming.iter_bounded_ledger_lines(self.ledger))

    def test_inspector_during_append_of_unfinished_final_record(self):
        initial = b'{"event":"TASK_STARTED","task_id":"t","step_ids":[]}\n'
        partial = b'{"event":"TASK_FINISHED","task_id":"t",'
        remainder = b'"status":"STOPPED"}\n'
        self.ledger.write_bytes(initial)
        reader_started = threading.Event()
        partial_written = threading.Event()
        iterator = ledger_streaming.iter_bounded_ledger_lines

        def read_during_append(path):
            for number, line in iterator(path):
                yield number, line
                if number == 1:
                    reader_started.set()
                    self.assertTrue(partial_written.wait(10))

        with ThreadPoolExecutor(max_workers=1) as pool, patch.object(
            ario_agent, "iter_bounded_ledger_lines", read_during_append
        ):
            result = pool.submit(ario_agent.inspect_task_history, "t", self.ledger)
            try:
                self.assertTrue(reader_started.wait(10))
                with self.ledger.open("ab") as writer:
                    writer.write(partial)
            finally:
                partial_written.set()
            assessment = result.result(timeout=10)
        self.assertEqual(assessment["status"], "UNKNOWN")
        self.assertFalse(assessment["automatic_resume"])
        self.assertFalse(assessment["write_performed"])
        self.assertEqual(self.ledger.read_bytes(), initial + partial)
        with self.ledger.open("ab") as writer:
            writer.write(remainder)
        self.assertEqual(ario_agent.inspect_task_history("t", self.ledger)["status"], "STOPPED")

    def test_profiler_append_between_passes_yields_unknown(self):
        record = b'{"event":"NOTE"}\n'
        self.ledger.write_bytes(record)
        raw_metrics = ledger_budget_profile._raw_line_metrics

        def append_then_measure(path):
            with path.open("ab") as stream:
                stream.write(record)
            return raw_metrics(path)

        with patch.object(ledger_budget_profile, "_raw_line_metrics", append_then_measure):
            profile = ledger_budget_profile.profile_ledger(self.ledger)
        self.assertEqual(profile["status"], "UNKNOWN")
        self.assertEqual(profile["error_class"], "SOURCE_CHANGED_DURING_SCAN")
        self.assertEqual(self.ledger.read_bytes(), record * 2)
