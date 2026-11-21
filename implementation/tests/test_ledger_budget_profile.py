"""Research-only ledger budget profiler: privacy, limits and real call-chain."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ario_agent import run_task
from ledger_budget_profile import profile_ledger


class LedgerProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger = self.root / "events.jsonl"

    def test_empty_file(self):
        self.ledger.write_bytes(b"")
        original = self.ledger.read_bytes()
        result = profile_ledger(self.ledger)
        self.assertEqual(result["status"], "OBSERVED")
        self.assertEqual(result["events_seen"], 0)
        self.assertEqual(result["unique_task_ids"], 0)
        self.assertEqual(result["max_matching_task_events"], 0)
        self.assertEqual(self.ledger.read_bytes(), original)

    def test_task_counts_without_exposing_identifiers(self):
        ids = ["PRIVATE-SENSITIVE-ONE"] * 3 + ["PRIVATE-SENSITIVE-TWO"] * 129
        self.ledger.write_bytes(
            b"".join(
                (json.dumps({"event": "NOTE", "task_id": item}) + "\n").encode()
                for item in ids
            )
        )
        original = self.ledger.read_bytes()
        result = profile_ledger(self.ledger)
        self.assertEqual(result["status"], "OBSERVED")
        self.assertEqual(result["events_seen"], 132)
        self.assertEqual(result["unique_task_ids"], 2)
        self.assertEqual(result["max_matching_task_events"], 129)
        self.assertEqual(result["tasks_over_18_events"], 1)
        self.assertEqual(result["tasks_over_128_events"], 1)
        self.assertNotIn("PRIVATE-", json.dumps(result))
        self.assertEqual(self.ledger.read_bytes(), original)

    def test_malformed_json_is_unknown_not_counted_as_complete(self):
        self.ledger.write_bytes(b'{"event":"NOTE","task_id":"P"}\nmalformed\n')
        original = self.ledger.read_bytes()
        result = profile_ledger(self.ledger)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["error_class"], "DECODING_OR_JSON_REJECTED")
        self.assertIsNone(result["max_matching_task_events"])
        self.assertEqual(self.ledger.read_bytes(), original)

    def test_missing_and_symlink_source_fail_closed(self):
        self.assertEqual(profile_ledger(self.ledger)["status"], "UNKNOWN")
        self.ledger.write_text("{}\n", encoding="utf-8")
        link = self.root / "link.jsonl"
        try:
            link.symlink_to(self.ledger)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable")
        r = profile_ledger(link)
        self.assertEqual(r["status"], "UNKNOWN")
        self.assertEqual(r["error_class"], "NOT_REGULAR_FILE")

    def test_maximum_8_action_8_diagnostic_real_task_emits_18_events(self):
        (self.root / "proof.txt").write_text("ok", encoding="utf-8")
        payload = {
            "task_id": "MEASURE-18",
            "goal": "Synthetic worst-case diagnostics path",
            "actions": [
                {"step_id": f"ok-{i}", "tool": "read_text", "path": "proof.txt"}
                for i in range(7)
            ] + [{"step_id": "last", "tool": "read_text", "path": "missing.txt"}],
            "failure_diagnostics": [
                {"step_id": f"diag-{i}", "tool": "inspect_directory", "path": "."}
                for i in range(8)
            ],
        }
        output = run_task(payload, self.root, self.ledger)
        self.assertEqual(output["status"], "STOPPED")
        original = self.ledger.read_bytes()
        report = profile_ledger(self.ledger)
        self.assertEqual(report["status"], "OBSERVED")
        self.assertEqual(report["events_seen"], 18)
        self.assertEqual(report["max_matching_task_events"], 18)
        self.assertEqual(report["tasks_over_18_events"], 0)
        self.assertLess(report["max_logical_line_chars"], report["candidate_line_limit_chars"])
        self.assertGreater(report["max_physical_line_bytes"], 0)
        self.assertEqual(self.ledger.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
