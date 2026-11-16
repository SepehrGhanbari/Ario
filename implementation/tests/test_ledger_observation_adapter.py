import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from ledger_observation_adapter import (
    MAX_JSON_DEPTH,
    MAX_LINE_BYTES,
    json_nesting_exceeds,
    observe_ledger,
)


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


    def test_unhashable_event_values_fail_closed_and_preserve_input(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "events.jsonl"
            for raw in (b'{"event":[],"timestamp":"t"}\n',
                        b'{"event":{},"timestamp":"t"}\n'):
                with self.subTest(raw=raw):
                    ledger.write_bytes(raw)
                    result = observe_ledger(ledger)
                    self.assertEqual(result["status"], "UNKNOWN")
                    self.assertEqual(result["observations"], [])
                    self.assertIn("invalid event envelope", result["error"])
                    self.assertEqual(ledger.read_bytes(), raw)


    def test_deeply_nested_json_fails_closed_and_preserves_bytes(self):
        """A valid bounded JSONL line must not escape as RecursionError."""
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "events.jsonl"
            deeply_nested = b"[" * 12000 + b"0" + b"]" * 12000
            raw = b'{"event":' + deeply_nested + b',"timestamp":"t"}\n'
            self.assertLess(len(raw), MAX_LINE_BYTES)
            ledger.write_bytes(raw)
            result = observe_ledger(ledger)
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertEqual(result["observations"], [])
            self.assertIn("JSON nesting-depth limit exceeded", result["error"])
            self.assertEqual(ledger.read_bytes(), raw)

    def _observe_bytes(self, raw):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "events.jsonl"
            ledger.write_bytes(raw)
            result = observe_ledger(ledger)
            self.assertEqual(ledger.read_bytes(), raw)
            return result

    def test_deep_nesting_in_unrelated_field_is_interpreter_independent(self):
        """Valid envelope plus deep payload must be UNKNOWN on every CPython.

        Before the explicit bound, CPython 3.12/3.13 returned UNKNOWN via
        RecursionError while 3.14 returned OBSERVED for the same bytes.
        """
        deep = b"[" * 12000 + b"0" + b"]" * 12000
        raw = b'{"event":"TASK_STARTED","timestamp":"t","payload":' + deep + b"}\n"
        self.assertLess(len(raw), MAX_LINE_BYTES)
        result = self._observe_bytes(raw)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["observations"], [])
        self.assertIn("JSON nesting-depth limit exceeded", result["error"])

    def test_nesting_at_limit_is_observed_and_one_over_is_unknown(self):
        def line(levels):
            inner = b"[" * (levels - 1) + b"0" + b"]" * (levels - 1)
            return b'{"event":"TASK_STARTED","timestamp":"t","payload":' + inner + b"}\n"

        at_limit = self._observe_bytes(line(MAX_JSON_DEPTH))
        self.assertEqual(at_limit["status"], "OBSERVED")
        over_limit = self._observe_bytes(line(MAX_JSON_DEPTH + 1))
        self.assertEqual(over_limit["status"], "UNKNOWN")
        self.assertIn("JSON nesting-depth limit exceeded", over_limit["error"])

    def test_brackets_inside_strings_do_not_count_toward_depth(self):
        noisy = "[{" * 200 + '\\"' + "}]" * 200
        raw = json.dumps(
            {"event": "TASK_STARTED", "timestamp": "t", "note": noisy}
        ).encode("utf-8") + b"\n"
        result = self._observe_bytes(raw)
        self.assertEqual(result["status"], "OBSERVED")
        self.assertEqual(result["event_count"], 1)

    def test_depth_scanner_unit_cases(self):
        self.assertFalse(json_nesting_exceeds('{"a": [1, 2]}', limit=2))
        self.assertTrue(json_nesting_exceeds('{"a": [[1]]}', limit=2))
        self.assertFalse(json_nesting_exceeds('{"a": "[[[[[["}', limit=1))
        self.assertFalse(json_nesting_exceeds('{"a": "\\"[[["}', limit=1))


if __name__ == "__main__":
    unittest.main()
