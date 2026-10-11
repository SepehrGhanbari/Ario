import copy
import json
import tempfile
import unittest
from pathlib import Path

from admission_review_evaluator import evaluate_review_request, main
from candidate_dossier_builder import build_candidate_dossier
from ledger_observation_adapter import observe_ledger


class AdmissionReviewEvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger = Path(self.temp.name) / "events.jsonl"
        self.ledger.write_bytes((json.dumps({"event": "TASK_FINISHED", "timestamp": "2026-10-11T00:00:00Z", "status": "COMPLETED"}) + "\n").encode())
        self.manifest = observe_ledger(self.ledger)
        self.candidate = build_candidate_dossier(self.manifest, self.ledger, line=1, claim_id="c1", claim_scope="Ledger reports completion", proposed_support_relation="Only reported status")
        assert self.candidate["status"] == "CANDIDATE"
        self.req = {
            "policy_version": "ARP-0.1", "candidate": self.candidate, "candidate_digest": "UNKNOWN",
            "reviewer_id": "r1", "reviewer_role": "human", "authorization_reference": "declared-auth",
            "requested_claim_id": "c1", "requested_claim_scope": "Ledger reports completion",
            "requested_support_relation": "Only reported status", "corroboration_refs": [],
            "review_rule_ids": ["ARP-0.1"], "limitations": "No external authentication",
            "recorded_at": "reported-time", "decision": "NOT_EVALUATED",
        }

    def evaluate(self, change=None):
        r = copy.deepcopy(self.req)
        if change:
            change(r)
        return evaluate_review_request(r, self.manifest, self.ledger)

    def test_declared_authorization_is_not_authenticated(self):
        outcome = self.evaluate()
        self.assertEqual(outcome["status"], "UNKNOWN")
        self.assertEqual(outcome["admission_decision"], "NOT_EVALUATED")

    def test_forbidden_outcomes(self):
        for value in ("ADMITTED", "ACCEPTED_AS_EVIDENCE", "M0_PASS", "TRUTH"):
            with self.subTest(value=value):
                self.assertEqual(self.evaluate(lambda r: r.update(decision=value))["status"], "REJECTED")

    def test_forged_evidence_admission(self):
        self.assertEqual(self.evaluate(lambda r: r["candidate"].update(admission_decision="ADMITTED"))["status"], "REJECTED")

    def test_claim_scope_expansion(self):
        self.assertEqual(self.evaluate(lambda r: r.update(requested_claim_scope="External engineering goal achieved"))["status"], "REJECTED")

    def test_changed_ledger_rejected(self):
        self.ledger.write_bytes(self.ledger.read_bytes().replace(b"COMPLETED", b"FAILED"))
        self.assertEqual(self.evaluate()["status"], "REJECTED")

    def test_dossier_tamper_rejected(self):
        self.assertEqual(self.evaluate(lambda r: r["candidate"]["observation_locator"].update(record_sha256="0" * 64))["status"], "REJECTED")

    def test_missing_authority_yields_unknown(self):
        self.assertEqual(self.evaluate(lambda r: r.update(authorization_reference=None))["status"], "UNKNOWN")

    def test_multiple_echoes_not_independent(self):
        def edit(r):
            r["corroboration_refs"] = [{"type": "adapter"}, {"type": "bridge"}, {"type": "builder"}]
        self.assertEqual(self.evaluate(edit)["status"], "UNKNOWN")

    def test_dossier_digest_must_not_be_guessed(self):
        self.assertEqual(self.evaluate(lambda r: r.update(candidate_digest="sha256:pretend"))["status"], "UNKNOWN")

    def test_invalid_request_envelope(self):
        self.assertEqual(self.evaluate(lambda r: r.pop("recorded_at"))["status"], "REJECTED")

    def test_no_ledger_mutation(self):
        before = self.ledger.read_bytes()
        self.evaluate()
        self.assertEqual(before, self.ledger.read_bytes())

    def test_cli_no_admission(self):
        request = Path(self.temp.name) / "req.json"
        manifest = Path(self.temp.name) / "manifest.json"
        request.write_text(json.dumps(self.req), encoding="utf-8")
        manifest.write_text(json.dumps(self.manifest), encoding="utf-8")
        self.assertEqual(main([str(request), str(manifest), str(self.ledger)]), 0)


if __name__ == "__main__":
    unittest.main()
