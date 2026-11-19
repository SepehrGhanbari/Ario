"""Public, oracle-free invariants for the Ario A/B/C R0 research adapter.

The private fixture oracle, grader, positive/negative labels, and synthetic
truth must NOT be published here. These tests cannot establish real custody.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import provenance_blind_r0 as evaluator

OBSERVABLES = HERE / "provenance_blind_r0_observables.jsonl"


def public_cases():
    lines = OBSERVABLES.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


class PublicNoOracleContract(unittest.TestCase):
    def test_24_unique_public_cases(self):
        cases = public_cases()
        self.assertEqual(len(cases), 24)
        self.assertEqual(len({c["case_id"] for c in cases}), 24)
        self.assertEqual({d: sum(c["domain"] == d for c in cases) for d in "ABC"},
                         {"A": 8, "B": 8, "C": 8})

    def test_no_oracle_truth_in_public_fixture(self):
        raw = OBSERVABLES.read_text(encoding="utf-8")
        for forbidden in ('"oracle"', '"ground_truth"', '"hidden_truth"',
                          '"synthetic_truth"', '"expected"', '"secret"'):
            self.assertNotIn(forbidden, raw)
        for item in public_cases():
            self.assertEqual(set(item), {"case_id", "domain", "facts"})

    def test_each_public_case_remains_non_authoritative(self):
        for case in public_cases():
            with self.subTest(case=case["case_id"]):
                out = evaluator.evaluate(case)
                self.assertEqual(out["status"], "UNKNOWN")
                self.assertEqual(out["execution_attestation"], "NOT_ESTABLISHED")
                self.assertEqual(out["evidence_admission"], "NOT_EVALUATED")
                self.assertEqual(out["source_provenance"], "UNVERIFIED")
                self.assertEqual(out["case_id"], case["case_id"])
                self.assertEqual(out["domain"], case["domain"])
                self.assertNotIn("reason", out)  # valid observable shape

    def test_a_uses_lab_only_not_real_world_authentication(self):
        for case in public_cases():
            if case["domain"] != "A":
                continue
            out = evaluator.evaluate(case)
            self.assertEqual(out["custody_authenticity"], "NOT_ESTABLISHED")
            self.assertIn(out["independence"],
                          {"UNKNOWN", "LAB_DEPENDENCE_OBSERVED", "LAB_CONDITIONALLY_SEPARATE"})

    def test_b_artifact_signature_always_unverified(self):
        for case in public_cases():
            if case["domain"] != "B":
                continue
            out = evaluator.evaluate(case)
            self.assertEqual(out["artifact_authenticity"], "NOT_VERIFIED_SELF_CLAIM_ONLY")
            self.assertEqual(out["parser_final_status"], "UNKNOWN")
            self.assertEqual(out["parser_execution_attestation"], "NOT_ESTABLISHED")
            self.assertIn(out["claim_correspondence"], {"MATCH", "MISMATCH", "UNKNOWN"})

    def test_c_preserves_exact_supplied_receipt_identifiers(self):
        for case in public_cases():
            if case["domain"] != "C":
                continue
            out = evaluator.evaluate(case)
            self.assertEqual(out["historical_receipts"],
                             [x["id"] for x in case["facts"]["receipts"]])
            self.assertTrue(out["history_preserved"])
            self.assertIn(out["current_state"], {"UNRESOLVED", "LAB_CONDITIONALLY_CURRENT"})

    def test_conditional_currency_requires_witness_and_positive_attempts(self):
        original = next(case for case in public_cases() if case["case_id"] == "C-03")
        self.assertEqual(evaluator.evaluate(original)["current_state"], "LAB_CONDITIONALLY_CURRENT")
        for witness, current, issued in ((None, 1, 1), ("  ", 1, 1), ("W2", -1, -1),
                                         ("W2", 0, 1), ("W2", 1, 0)):
            with self.subTest(witness=witness, current=current, issued=issued):
                case = copy.deepcopy(original)
                facts = case["facts"]
                facts["current_attempt"] = current
                facts["receipts"][0].update(witness=witness, attempt=issued)
                out = evaluator.evaluate(case)
                self.assertEqual(out["status"], "UNKNOWN")
                self.assertEqual(out.get("reason"), "INVALID_OR_UNSUPPORTED_OBSERVATION")

    def test_injected_oracle_refused(self):
        case = copy.deepcopy(public_cases()[0])
        case["oracle"] = {"historical_truth": "hidden"}
        result = evaluator.evaluate(case)
        self.assertEqual(result["reason"], "INVALID_OR_UNSUPPORTED_OBSERVATION")
        self.assertEqual(result["status"], "UNKNOWN")

    def test_nested_hidden_field_refused(self):
        case = copy.deepcopy(public_cases()[0])
        case["facts"]["ground_truth"] = True
        result = evaluator.evaluate(case)
        self.assertEqual(result["reason"], "INVALID_OR_UNSUPPORTED_OBSERVATION")

    def test_mistyped_bool_fail_closed(self):
        case = copy.deepcopy(public_cases()[0])
        case["facts"]["complete_control"] = 1
        result = evaluator.evaluate(case)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason"], "INVALID_OR_UNSUPPORTED_OBSERVATION")

    def test_unknown_domain_fail_closed(self):
        case = copy.deepcopy(public_cases()[0])
        case["domain"] = "Z"
        result = evaluator.evaluate(case)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason"], "INVALID_OR_UNSUPPORTED_OBSERVATION")

    def test_subprocess_does_not_receive_oracle(self):
        case = public_cases()[0]
        p = subprocess.run([sys.executable, "-B", str(HERE / "provenance_blind_r0.py")],
                           input=json.dumps(case).encode(), capture_output=True, timeout=15)
        self.assertEqual(p.returncode, 0, p.stderr.decode()[:350])
        parsed = json.loads(p.stdout)
        self.assertEqual(parsed["status"], "UNKNOWN")
        self.assertNotIn('"oracle"', p.stdout.decode())

    def test_oversized_stream_rejected(self):
        p = subprocess.run([sys.executable, "-B", str(HERE / "provenance_blind_r0.py")],
                           input=b"Z" * 25000, capture_output=True, timeout=15)
        self.assertEqual(p.returncode, 0, p.stderr.decode()[:350])
        parsed = json.loads(p.stdout)
        self.assertEqual(parsed["status"], "UNKNOWN")
        self.assertEqual(parsed["reason"], "INVALID_OR_UNSUPPORTED_OBSERVATION")

    def test_duplicate_receipt_id_rejected_without_mutation(self):
        case = copy.deepcopy(next(x for x in public_cases()
                                  if x["domain"] == "C" and len(x["facts"]["receipts"]) > 1))
        orig = copy.deepcopy(case)
        case["facts"]["receipts"][1]["id"] = case["facts"]["receipts"][0]["id"]
        parsed = evaluator.evaluate(case)
        self.assertEqual(parsed["reason"], "INVALID_OR_UNSUPPORTED_OBSERVATION")
        self.assertEqual(evaluator.evaluate(orig)["status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
