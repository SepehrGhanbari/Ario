"""Hallaaj review-derived NEGATIVE probes: GitHub log != pytest attestation."""
from __future__ import annotations

import copy
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest import mock

import pr_claim_audit_github_v0_3 as v03
import pr_claim_audit_log_boundary_v0_4 as v04
from test_pr_claim_audit_github_v0_3 import FakeGitHub, LOG, claim_body

OWNER, REPO, PR = "SepehrGhanbari", "Ario", 249


class MutableFakeGitHub(FakeGitHub):
    def __init__(self):
        super().__init__()
        self.run_reads = 0
        self.jobs_reads = 0
        self.next_run = None
        self.next_job = None

    def get_json(self, url):
        if url.endswith("/actions/runs/43949946093"):
            self.run_reads += 1
            if self.next_run and self.run_reads > 1:
                self.calls.append(url)
                return copy.deepcopy(self.next_run)
        if "/attempts/1/jobs?" in url:
            self.jobs_reads += 1
            if self.next_job and self.jobs_reads > 1:
                self.calls.append(url)
                return {"total_count": 1, "jobs": [copy.deepcopy(self.next_job)]}
        return super().get_json(url)


class ExecutionAttestationBoundary(unittest.TestCase):
    def setUp(self):
        self.fake = MutableFakeGitHub()
        self.fake.run["conclusion"] = "failure"

    def audit(self):
        return v04.assess_github_pr(OWNER, REPO, PR, reader=self.fake)

    def test_hallaaj_forged_runner_log_v03_internal_mock_match_v04_unknown(self):
        self.fake.log = "\n".join((
            "2026-11-16T20:27:42Z ##[group]Run echo 'fake pytest invocation'",
            "2026-11-16T20:27:42Z Python 3.14.10 (synthetic, NOT actually pytest)",
            "2026-11-16T20:27:43Z ##[group]Run python -m pytest -q tests",
            "2026-11-16T20:27:49Z 9999 passed, 121 subtests passed in 0.12s",
        ))
        self.fake.pr["body"] = claim_body(passed=9999, failed=0, job_conclusion="success")
        self.fake.job["conclusion"] = "success"
        self.fake.run["conclusion"] = "success"
        # This is an OFFLINE mock of a workflow-controlled GitHub log, not a real CI run.
        reader = v03.PublicGitHubReader()
        with mock.patch.object(v03, "PublicGitHubReader", return_value=reader), \
             mock.patch.object(reader, "get_json", side_effect=self.fake.get_json), \
             mock.patch.object(reader, "get_job_log", side_effect=self.fake.get_job_log):
            unsafe = v03.assess_github_pr(OWNER, REPO, PR)
        self.assertEqual(unsafe["status"], "MATCH")
        result = self.audit()
        self.assertEqual(result["correspondence_status"], "MATCH")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["log_execution_attestation"], "NOT_ESTABLISHED")
        self.assertEqual(result["workflow_overall_conclusion"], "success")

    def test_honest_match_still_only_diagnostic(self):
        result = self.audit()
        self.assertEqual(result["correspondence_status"], "MATCH")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["source_transport_status"], "UNVERIFIED")
        self.assertEqual(result["workflow_overall_conclusion"], "failure")
        self.assertEqual(result["scope"], "ONE_JOB_ONLY")

    def test_mismatch_remains_diagnostic_when_log_unattested(self):
        self.fake.pr["body"] = claim_body(passed=1141)
        result = self.audit()
        self.assertEqual(result["correspondence_status"], "MISMATCH")
        self.assertEqual(result["differences"], ["passed"])
        self.assertEqual(result["status"], "UNKNOWN")

    def test_missing_source_stays_unknown(self):
        self.fake.fail_log = True
        result = self.audit()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["correspondence_status"], "UNKNOWN")

    def test_author_controlled_fields_cannot_upgrade_final(self):
        self.fake.pr["origin_verified"] = True
        self.fake.run["log_execution_attestation"] = "VERIFIED"
        self.fake.job["attested"] = True
        result = self.audit()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["log_execution_attestation"], "NOT_ESTABLISHED")

    def test_job_success_does_not_hide_workflow_failure(self):
        self.fake.job["conclusion"] = "success"
        self.fake.pr["body"] = claim_body(job_conclusion="success")
        self.fake.run["conclusion"] = "failure"
        result = self.audit()
        self.assertEqual(result["correspondence_status"], "MATCH")
        self.assertEqual(result["observed"]["job_conclusion"], "success")
        self.assertEqual(result["workflow_overall_conclusion"], "failure")
        self.assertEqual(result["status"], "UNKNOWN")

    def test_run_attempt_changed_during_readback_unknown(self):
        self.fake.next_run = copy.deepcopy(self.fake.run)
        self.fake.next_run["run_attempt"] = 2
        result = self.audit()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["correspondence_status"], "UNKNOWN")
        self.assertEqual(result["reason"], "RUN_CHANGED_OR_UNAVAILABLE_ON_RECHECK")

    def test_run_conclusion_changed_without_attempt_change_visible_not_attested(self):
        self.fake.next_run = copy.deepcopy(self.fake.run)
        self.fake.next_run["conclusion"] = "success"
        result = self.audit()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["workflow_overall_conclusion"], "success")

    def test_job_result_changed_during_readback_unknown(self):
        self.fake.next_job = copy.deepcopy(self.fake.job)
        self.fake.next_job["conclusion"] = "success"
        result = self.audit()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["correspondence_status"], "UNKNOWN")
        self.assertEqual(result["reason"], "JOB_CHANGED_OR_MISSING_ON_RECHECK")

    def test_job_id_changed_during_readback_unknown(self):
        self.fake.next_job = copy.deepcopy(self.fake.job)
        self.fake.next_job["id"] = 777
        result = self.audit()
        self.assertEqual(result["correspondence_status"], "UNKNOWN")

    def test_unexpected_job_collection_unknown(self):
        self.fake.job_total = 501
        self.assertEqual(self.audit()["status"], "UNKNOWN")

    def test_non_attesting_result_contains_limitations(self):
        result = self.audit()
        self.assertTrue(any("workflow" in s.lower() for s in result["limitations"]))
        self.assertEqual(result["reason"], "LOG_EXECUTION_NOT_ATTESTED")

    def test_cli_one_json_and_0_never_implies_success(self):
        out = io.StringIO()
        with mock.patch.object(v04, "assess_github_pr", return_value=self.audit()), redirect_stdout(out):
            exit_code = v04.main(["--owner", OWNER, "--repo", REPO, "--pr", str(PR)])
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(out.getvalue())["status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
