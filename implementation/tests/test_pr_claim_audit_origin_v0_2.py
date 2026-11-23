"""RED/GREEN provenance boundary tests — no real GitHub access or secrets."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from pr_claim_audit import OPEN, CLOSE, assess as legacy_assess
from pr_claim_audit_origin_v0_2 import assess, main

CLAIM = {
    "schema": "ARIO-PR-CI-0.1",
    "head_sha": "c800b45c2c06d1bbeacaa063cca4573f0ec1d879",
    "run_id": 43949946093,
    "run_attempt": 1,
    "job_id": 133589448819,
    "python_version": "3.14.10",
    "pytest_command": "python -m pytest -q tests",
    "passed": 1140,
    "failed": 1,
    "skipped": 0,
    "subtests_passed": 121,
    "job_conclusion": "failure",
}
FAKE_LOG = (
    "2026-11-16T20:27:42.3105798Z Python 3.14.10 (synthetic; NOT real GitHub)\n"
    "2026-11-16T20:27:42.4802125Z ##[group]Run python -m pytest -q tests\n"
    "2026-11-16T20:27:49.2372855Z 1 failed, 1140 passed, 121 subtests passed in 6.08s"
)


def make_body(claim=None):
    return OPEN + "\n" + json.dumps(CLAIM if claim is None else claim) + "\n" + CLOSE


def make_evidence(log=FAKE_LOG):
    return {
        "run": {
            "id": CLAIM["run_id"], "head_sha": CLAIM["head_sha"], "run_attempt": 1,
            "status": "completed", "event": "pull_request", "conclusion": "failure",
        },
        "job": {
            "id": CLAIM["job_id"], "run_id": CLAIM["run_id"], "name": "python-314-differential-advisory",
            "status": "completed", "conclusion": "failure",
        },
        "job_log_complete": True,
        "job_log": log,
        "job_log_sha256": hashlib.sha256(log.encode()).hexdigest(),
    }


class StrictOriginTests(unittest.TestCase):
    def test_forged_consistent_evidence_matches_v01_but_final_v02_unknown(self):
        evidence = make_evidence()
        self.assertEqual(legacy_assess(make_body(), evidence)["status"], "MATCH")
        result = assess(make_body(), evidence)
        self.assertEqual(result["correspondence_status"], "MATCH")
        self.assertEqual(result["origin_status"], "UNVERIFIED")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason"], "EVIDENCE_ORIGIN_UNVERIFIED")

    def test_self_rehashed_forgery_remains_unknown(self):
        source = make_evidence(FAKE_LOG + "\nforged footer")
        self.assertEqual(legacy_assess(make_body(), source)["status"], "MATCH")
        self.assertEqual(assess(make_body(), source)["status"], "UNKNOWN")

    def test_caller_claims_verified_origin_cannot_promote_match(self):
        e = make_evidence()
        e["origin_verified"] = True
        e["origin_status"] = "VERIFIED_BY_GITHUB"
        e["fetcher_signature"] = "fake"
        result = assess(make_body(), e)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["origin_status"], "UNVERIFIED")

    def test_correspondence_mismatch_with_unverified_source_is_unknown_final(self):
        body = make_body(dict(CLAIM, passed=1141))
        result = assess(body, make_evidence())
        self.assertEqual(result["correspondence_status"], "MISMATCH")
        self.assertEqual(result["differences"], ["passed"])
        self.assertEqual(result["status"], "UNKNOWN")

    def test_missing_evidence_is_unknown_in_both(self):
        result = assess(make_body(), {})
        self.assertEqual(result["correspondence_status"], "UNKNOWN")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason"], "SNAPSHOT_NOT_ASSESSABLE")

    def test_wrong_run_and_job_binding_remain_unknown(self):
        for field in ("id", "run_attempt", "head_sha"):
            with self.subTest(field=field):
                e = make_evidence()
                e["run"][field] = "f" * 40 if field == "head_sha" else 999
                self.assertEqual(assess(make_body(), e)["correspondence_status"], "UNKNOWN")
        e = make_evidence()
        e["job"]["run_id"] = 123
        self.assertEqual(assess(make_body(), e)["correspondence_status"], "UNKNOWN")

    def test_inconsistent_log_hash_fails_closed(self):
        e = make_evidence()
        e["job_log"] += "tampering not accompanied by rehash"
        self.assertEqual(assess(make_body(), e)["status"], "UNKNOWN")
        self.assertEqual(assess(make_body(), e)["correspondence_status"], "UNKNOWN")

    def test_report_never_asserts_merge_or_authorization(self):
        r = assess(make_body(), make_evidence())
        self.assertNotIn("APPROVED", json.dumps(r))
        self.assertNotIn("ADMITTED", json.dumps(r))
        self.assertEqual(set((r["status"], r["correspondence_status"])), {"UNKNOWN", "MATCH"})

    def test_cli_no_writes_one_json_and_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d, "claim.md"), Path(d, "evidence.json")
            a.write_text(make_body(), encoding="utf-8")
            b.write_text(json.dumps(make_evidence()), encoding="utf-8")
            before = (a.read_bytes(), b.read_bytes())
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--pr-body", str(a), "--evidence", str(b)]), 0)
            data = json.loads(output.getvalue())
            self.assertEqual(data["status"], "UNKNOWN")
            self.assertEqual(data["correspondence_status"], "MATCH")
            self.assertEqual(before, (a.read_bytes(), b.read_bytes()))

    def test_cli_invalid_evidence_returns_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d,"claim.md"),Path(d,"evidence.json")
            a.write_text(make_body(),encoding="utf-8")
            b.write_text("{invalid-json",encoding="utf-8")
            out=io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(["--pr-body",str(a),"--evidence",str(b)]),0)
            self.assertEqual(json.loads(out.getvalue())["status"],"UNKNOWN")


if __name__ == "__main__":
    unittest.main()
