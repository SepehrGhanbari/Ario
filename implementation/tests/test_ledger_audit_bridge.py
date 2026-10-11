import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from ledger_observation_adapter import observe_ledger
from ledger_audit_bridge import verify_observation_manifest, verify_manifest_file


class LedgerAuditBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = Path(self.tmp.name) / "events.jsonl"
        self.ledger.write_bytes(b''.join(
            (json.dumps(row).encode('utf-8') + b'\n') for row in (
                {"event": "TASK_STARTED", "task_id": "t1", "timestamp": "2026-01-01T00:00:00Z"},
                {"event": "TASK_FINISHED", "task_id": "t1", "status": "COMPLETED", "timestamp": "2026-01-01T00:00:01Z"},
            )
        ))
        self.original = self.ledger.read_bytes()
        self.manifest = observe_ledger(self.ledger)

    def test_good_manifest_is_only_observed_and_read_only(self):
        r = verify_observation_manifest(self.manifest, self.ledger)
        self.assertEqual(r["status"], "OBSERVED")
        self.assertEqual(r["event_count"], 2)
        self.assertEqual(r["ledger_sha256"], hashlib.sha256(self.original).hexdigest())
        self.assertNotIn("verdict", r)
        self.assertNotIn("evidence", r)
        self.assertNotIn("assessment", r)
        self.assertEqual(self.ledger.read_bytes(), self.original)

    def test_tampered_observation_or_duplicate_rejected(self):
        for change in ("status", "duplicate", "hash", "source", "limit", "extra"):
            with self.subTest(change=change):
                m = copy.deepcopy(self.manifest)
                if change == "status": m["observations"][1]["reported_status"] = "STOPPED"
                if change == "duplicate": m["observations"].append(m["observations"][0])
                if change == "hash": m["sha256"] = "0" * 64
                if change == "source": m["source"] = "other-file"
                if change == "limit": m["epistemic_limit"] = "truth is confirmed"
                if change == "extra": m["Evidence"] = "manufactured"
                self.assertEqual(verify_observation_manifest(m, self.ledger)["status"], "REJECTED")
        self.assertEqual(self.ledger.read_bytes(), self.original)

    def test_unknown_manifest_and_unavailable_ledger_fail_closed(self):
        self.assertEqual(verify_observation_manifest({"status": "UNKNOWN"}, self.ledger)["status"], "UNKNOWN")
        self.ledger.unlink()
        self.assertEqual(verify_observation_manifest(self.manifest, self.ledger)["status"], "UNKNOWN")

    def test_changed_ledger_cannot_validate_old_manifest(self):
        with self.ledger.open('ab') as stream:
            stream.write(b'{"event":"TASK_STARTED","timestamp":"2026-01-01T00:00:02Z"}\n')
        self.assertEqual(verify_observation_manifest(self.manifest, self.ledger)["status"], "REJECTED")

    def test_manifest_file_cli_inputs(self):
        p = Path(self.tmp.name) / 'manifest.json'
        p.write_text(json.dumps(self.manifest), encoding='utf-8')
        self.assertEqual(verify_manifest_file(p, self.ledger)['status'], 'OBSERVED')
        p.write_bytes(b'not-json')
        self.assertEqual(verify_manifest_file(p, self.ledger)['status'], 'REJECTED')
        self.assertEqual(self.ledger.read_bytes(), self.original)


if __name__ == '__main__':
    unittest.main()
