"""RAC-0.1 adversarial, non-authorizing preflight tests."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reviewer_authorization_preflight import FIELDS, preflight_authorization


def grant():
    return {
        "authorization_contract_version": "RAC-0.1",
        "grant_id": "GRANT-A",
        "issuer_id": "ISSUER-DECLARED",
        "issuer_trust_basis": "claimed-local-issuer",
        "principal_id": "HUMAN-A",
        "identity_binding_method": "claimed-signature",
        "permitted_action": "REVIEW_CANDIDATE",
        "policy_version": "ARP-0.1",
        "claim_scope": "Ledger reports event",
        "candidate_binding": "claimed-digest",
        "validity_start": "2026-01-01",
        "validity_end": "2027-01-01",
        "verification_time_basis": "claimed-local-clock",
        "revocation_reference": "claimed-list",
        "revocation_check": "ACTIVE",
        "separation_of_duties": "CLAIMED_INDEPENDENT",
        "signature_or_attestation": "claimed-signature-by-issuer",
        "verification_result": "VERIFIED_FOR_REVIEW_ONLY",
        "grant_limitations": "review-only",
        "rule_version": "RAC-0.1",
    }


class PreflightTests(unittest.TestCase):
    def test_nominal_is_unknown_not_granted(self):
        result = preflight_authorization(grant())
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["authorization_decision"], "NOT_CHECKED")
        self.assertEqual(result["admission_decision"], "NOT_EVALUATED")

    def test_all_fields_match(self):
        self.assertEqual(set(grant()), FIELDS)

    def test_self_attestation_never_authorizes(self):
        g = grant()
        g["signature_or_attestation"] = "self-signed"
        g["verification_result"] = "VERIFIED_FOR_REVIEW_ONLY"
        self.assertEqual(preflight_authorization(g)["status"], "UNKNOWN")

    def test_null_trust_claims_never_authorize(self):
        g = grant()
        for k in ("issuer_trust_basis", "identity_binding_method", "candidate_binding", "revocation_check"):
            g[k] = None
        self.assertEqual(preflight_authorization(g)["status"], "UNKNOWN")

    def test_reject_forbidden_actions(self):
        for action in ("ADMIT_EVIDENCE", "ADMITTED", "M0_PASS", "ASSERT_TRUTH", "DELETE_LEDGER", ""):
            with self.subTest(action=action):
                g = grant(); g["permitted_action"] = action
                self.assertEqual(preflight_authorization(g)["status"], "REJECTED")

    def test_reject_self_review(self):
        for relation in ("SELF_REVIEW", "SAME_PROPOSER_AND_REVIEWER"):
            with self.subTest(relation=relation):
                g = grant(); g["separation_of_duties"] = relation
                self.assertEqual(preflight_authorization(g)["status"], "REJECTED")

    def test_reject_declared_revoked(self):
        g = grant(); g["revocation_check"] = "REVOKED"
        self.assertEqual(preflight_authorization(g)["status"], "REJECTED")

    def test_reject_wrong_versions(self):
        for key, value in (("authorization_contract_version", "RAC-2"), ("rule_version", "RAC-2"), ("policy_version", "ARP-9")):
            with self.subTest(key=key):
                g = grant(); g[key] = value
                self.assertEqual(preflight_authorization(g)["status"], "REJECTED")

    def test_reject_missing_extra_unbounded_and_wrong_types(self):
        g = grant(); del g["claim_scope"]
        self.assertEqual(preflight_authorization(g)["status"], "REJECTED")
        g = grant(); g["unexpected"] = "x"
        self.assertEqual(preflight_authorization(g)["status"], "REJECTED")
        g = grant(); g["grant_id"] = "x" * 1000
        self.assertEqual(preflight_authorization(g)["status"], "REJECTED")
        g = grant(); g["claim_scope"] = []
        self.assertEqual(preflight_authorization(g)["status"], "REJECTED")

    def test_never_returns_authorized_on_hostile_field_variations(self):
        for key in grant():
            with self.subTest(key=key):
                g = grant(); g[key] = "VERIFIED_FOR_REVIEW_ONLY"
                self.assertNotEqual(preflight_authorization(g)["status"], "VERIFIED_FOR_REVIEW_ONLY")
                self.assertNotEqual(preflight_authorization(g)["authorization_decision"], "VERIFIED_FOR_REVIEW_ONLY")

    def test_input_not_mutated(self):
        original = grant(); snapshot = copy.deepcopy(original)
        preflight_authorization(original)
        self.assertEqual(original, snapshot)

    def test_cli_json_readonly(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "grant.json"
            path.write_text(json.dumps(grant()), encoding="utf-8")
            before = path.read_bytes()
            module = Path(__file__).resolve().parents[1] / "reviewer_authorization_preflight.py"
            done = subprocess.run([sys.executable, "-B", str(module), str(path)], capture_output=True, text=True)
            self.assertEqual(done.returncode, 0)
            self.assertEqual(json.loads(done.stdout)["status"], "UNKNOWN")
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
