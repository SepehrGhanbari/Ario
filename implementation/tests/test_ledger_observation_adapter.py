import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from ledger_observation_adapter import observe_ledger, MAX_LINE_BYTES


class LedgerObservationTests(unittest.TestCase):
    def test_read_only_manifest_and_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "events.jsonl"
            first = {"event": "TASK_STARTED", "task_id": "t1", "timestamp": "2026-01-01T00:00:00Z"}
            second = {"event": "TASK_FINISHED", "task_id": "t1", "status": "COMPLETED", "timestamp": "2026-01-01T00:00:01Z"}
            original = b"".join((json.dumps(item).encode() + b"\n") for item in (first, second))
            ledger.write_bytes(original)
            manifest = observe_ledger(ledger)
            self.assertEqual(manifest["status"], "OBSERVED")
            self.assertEqual(manifest["event_count"], 2)
            self.assertEqual(manifest["sha256"], hashlib.sha256(original).hexdigest())
            self.assertEqual(manifest["observations"][1]["reported_status"], "COMPLETED")
            self.assertNotIn("evidence", manifest)
            self.assertEqual(ledger.read_bytes(), original)

    def test_invalid_and_incomplete_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "events.jsonl"
            for raw in (b"\xff\n", b"not json\n", b'{"event":"TASK_STARTED"}', b"x" * (MAX_LINE_BYTES + 1) + b"\n"):
                with self.subTest(raw_start=raw[:16]):
                    ledger.write_bytes(raw)
                    result = observe_ledger(ledger)
                    self.assertEqual(result["status"], "UNKNOWN")
                    self.assertEqual(result["observations"], [])
                    self.assertEqual(ledger.read_bytes(), raw)

    def test_empty_and_unknown_event(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "events.jsonl"
            for raw in (b"", b'{"event":"INVENTED","timestamp":"t"}\n'):
                ledger.write_bytes(raw)
                self.assertEqual(observe_ledger(ledger)["status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
