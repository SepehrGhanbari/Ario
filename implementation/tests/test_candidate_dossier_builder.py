import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from candidate_dossier_builder import build_candidate_dossier, main
from ledger_observation_adapter import observe_ledger


class CandidateDossierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger = self.root / "events.jsonl"
        self.ledger.write_bytes(b''.join(json.dumps(event).encode() + b'\n' for event in (
            {"event": "TASK_STARTED", "task_id": "task-a", "timestamp": "2026-01-01T00:00:00Z"},
            {"event": "TASK_FINISHED", "task_id": "task-a", "status": "COMPLETED", "timestamp": "2026-01-01T00:00:01Z"},
        )))
        self.manifest = observe_ledger(self.ledger)
        self.kwargs = dict(line=2, claim_id="claim-1", claim_scope="ledger reports task status",
                           proposed_support_relation="Only supports that current ledger bytes report COMPLETED")

    def build(self, manifest=None, **changes):
        kwargs = dict(self.kwargs)
        kwargs.update(changes)
        return build_candidate_dossier(self.manifest if manifest is None else manifest, self.ledger, **kwargs)

    def test_valid_candidate_is_never_admitted_or_m0(self):
        original = self.ledger.read_bytes()
        result = self.build()
        self.assertEqual(result["status"], "CANDIDATE")
        self.assertEqual(result["admission_decision"], "NOT_EVALUATED")
        self.assertEqual(result["contract_version"], "EA-0.1")
        self.assertEqual(result["independence_declaration"], "UNKNOWN")
        self.assertEqual(result["observation_locator"]["reported_status"], "COMPLETED")
        self.assertEqual(result["bridge_verification"]["ledger_sha256"], hashlib.sha256(original).hexdigest())
        self.assertNotIn("evidence", result)
        self.assertNotIn("assessment", result)
        self.assertNotIn("verdict", result)
        self.assertEqual(self.ledger.read_bytes(), original)

    def test_mismatched_manifest_and_ledger_change_fail_closed(self):
        tampered = json.loads(json.dumps(self.manifest))
        tampered["observations"][1]["reported_status"] = "PASSED"
        self.assertEqual(self.build(tampered)["status"], "REJECTED")
        self.ledger.write_bytes(self.ledger.read_bytes() + b'{"event":"TASK_FINISHED","timestamp":"t"}\n')
        self.assertEqual(self.build()["status"], "REJECTED")

    def test_missing_locator_or_invalid_line_rejected(self):
        for line in (0, -1, 999, True, "2"):
            with self.subTest(line=line):
                self.assertEqual(self.build(line=line)["status"], "REJECTED")

    def test_unknown_upstream_is_not_promoted(self):
        self.assertEqual(self.build({"status": "UNKNOWN"})["status"], "UNKNOWN")

    def test_claim_fields_are_declared_and_bounded(self):
        for key, value in (("claim_id", ""), ("claim_scope", "  "),
                           ("proposed_support_relation", "x" * 601)):
            with self.subTest(key=key):
                self.assertEqual(self.build(**{key: value})["status"], "REJECTED")

    def test_bridge_not_an_independent_source(self):
        a = self.build()
        b = self.build()
        self.assertEqual(a["observation_locator"], b["observation_locator"])
        self.assertEqual(a["independence_declaration"], "UNKNOWN")
        self.assertEqual(b["independence_declaration"], "UNKNOWN")
        self.assertEqual(a["source_ledger"]["sha256"], b["source_ledger"]["sha256"])


if __name__ == "__main__":
    unittest.main()
