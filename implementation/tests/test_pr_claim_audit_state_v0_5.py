"""Hallaaj v0.5 review: separate diagnosis, delivery, consistency and attestation."""
from __future__ import annotations

import copy
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest import mock

import pr_claim_audit_state_v0_5 as v05
import pr_claim_audit_log_boundary_v0_4 as v04
from test_pr_claim_audit_log_boundary_v0_4 import MutableFakeGitHub
from test_pr_claim_audit_github_v0_3 import claim_body, LOG

OWNER, REPO, PR = "SepehrGhanbari", "Ario", 249


class ThirdReadChange(MutableFakeGitHub):
    def __init__(self):
        super().__init__()
        self.changed_pr = None
        self.fail_final_pr = False

    def get_json(self, url):
        if url.endswith("/pulls/249") and self.call_count_pr == 2:
            self.call_count_pr += 1
            self.calls.append(url)
            if self.fail_final_pr:
                raise v05.OriginUnknown("simulated API error")
            return copy.deepcopy(self.changed_pr or self.pr)
        return super().get_json(url)


class FourAxisTests(unittest.TestCase):
    def setUp(self):
        self.fake = ThirdReadChange()

    def audit(self):
        return v05.assess_github_pr(OWNER, REPO, PR, reader=self.fake)

    def test_honest_snapshot_only_reports_diagnostic_match(self):
        r = self.audit()
        self.assertEqual(r["schema"], "ARIO-PR-CI-0.5")
        self.assertEqual(r["claim_correspondence"], "MATCH")
        self.assertEqual(r["status"], "UNKNOWN")
        self.assertEqual(r["source_delivery"], "UNVERIFIED")
        self.assertEqual(r["state_consistency"], "STABLE_AT_SAMPLED_READS")
        self.assertEqual(r["execution_attestation"], "NOT_ESTABLISHED")
        self.assertFalse(r["workflow_state_changed_during_recheck"])
        self.assertEqual(self.fake.call_count_pr, 3)

    def test_hallaaj_change_workflow_conclusion_flag_without_false_unknown(self):
        self.fake.next_run = copy.deepcopy(self.fake.run)
        self.fake.next_run["conclusion"] = "success"
        r = self.audit()
        self.assertEqual(r["claim_correspondence"], "MATCH")
        self.assertEqual(r["state_consistency"], "WORKFLOW_CONCLUSION_CHANGED")
        self.assertTrue(r["workflow_state_changed_during_recheck"])
        self.assertEqual(r["workflow_conclusion_initial"], "failure")
        self.assertEqual(r["workflow_conclusion_final"], "success")
        self.assertEqual(r["status"], "UNKNOWN")

    def test_reverse_workflow_conclusion_change(self):
        self.fake.run["conclusion"] = "success"
        self.fake.next_run = copy.deepcopy(self.fake.run)
        self.fake.next_run["conclusion"] = "failure"
        r = self.audit()
        self.assertTrue(r["workflow_state_changed_during_recheck"])
        self.assertEqual(r["claim_correspondence"], "MATCH")

    def test_final_pr_head_move_after_v03_recheck_detected(self):
        self.fake.changed_pr = copy.deepcopy(self.fake.pr)
        self.fake.changed_pr["head"]["sha"] = "f" * 40
        # v0.4 only reads PR twice; this case really is missed by v0.4.
        before = v04.assess_github_pr(OWNER, REPO, PR, reader=self.fake)
        self.assertEqual(before["correspondence_status"], "MATCH")
        self.fake.call_count_pr = 0
        self.fake.calls.clear()
        after = self.audit()
        self.assertEqual(after["claim_correspondence"], "UNKNOWN")
        self.assertEqual(after["correspondence_status"], "UNKNOWN")
        self.assertEqual(after["state_consistency"], "PR_CHANGED")
        self.assertEqual(after["reason"], "PR_CHANGED_AFTER_V04_READBACK")
        self.assertIsNone(after["binding"])
        self.assertEqual(after["status"], "UNKNOWN")

    def test_final_pr_body_changed_after_v03_recheck(self):
        self.fake.changed_pr = copy.deepcopy(self.fake.pr)
        self.fake.changed_pr["body"] += "\nnew claim text"  # only the last GET sees this
        r = self.audit()
        self.assertEqual(r["state_consistency"], "PR_CHANGED")
        self.assertEqual(r["claim_correspondence"], "UNKNOWN")

    def test_final_pr_identity_changed(self):
        self.fake.changed_pr = copy.deepcopy(self.fake.pr)
        self.fake.changed_pr["id"] += 1
        self.assertEqual(self.audit()["state_consistency"], "PR_CHANGED")

    def test_final_pr_unavailable(self):
        self.fake.fail_final_pr = True
        r = self.audit()
        self.assertEqual(r["status"], "UNKNOWN")
        self.assertEqual(r["claim_correspondence"], "UNKNOWN")
        self.assertEqual(r["source_delivery"], "UNVERIFIED")

    def test_mismatching_claim_diagnostic_stays_mismatch(self):
        self.fake.pr["body"] = claim_body(passed=1141)
        r = self.audit()
        self.assertEqual(r["claim_correspondence"], "MISMATCH")
        self.assertEqual(r["state_consistency"], "STABLE_AT_SAMPLED_READS")
        self.assertEqual(r["status"], "UNKNOWN")

    def test_fake_runner_summary_cannot_attest_execution(self):
        self.fake.log = LOG.replace("1140 passed", "9999 passed")
        self.fake.pr["body"] = claim_body(passed=9999)
        r = self.audit()
        self.assertEqual(r["claim_correspondence"], "MATCH")
        self.assertEqual(r["execution_attestation"], "NOT_ESTABLISHED")
        self.assertEqual(r["status"], "UNKNOWN")

    def test_missing_log_stays_unknown(self):
        self.fake.fail_log = True
        r = self.audit()
        self.assertEqual(r["claim_correspondence"], "UNKNOWN")
        self.assertEqual(r["status"], "UNKNOWN")
        self.assertEqual(r["state_consistency"], "UNKNOWN")

    def test_changed_job_downgrades_diagnostic(self):
        self.fake.next_job = copy.deepcopy(self.fake.job)
        self.fake.next_job["conclusion"] = "success"
        r = self.audit()
        self.assertEqual(r["claim_correspondence"], "UNKNOWN")
        self.assertEqual(r["status"], "UNKNOWN")

    def test_injected_reader_fake_credentials_do_not_promote(self):
        self.fake.pr["source_delivery"] = "GITHUB_API_TLS_ROUTE"
        self.fake.pr["execution_attestation"] = "VERIFIED"
        r = self.audit()
        self.assertEqual(r["source_delivery"], "UNVERIFIED")
        self.assertEqual(r["execution_attestation"], "NOT_ESTABLISHED")
        self.assertEqual(r["status"], "UNKNOWN")

    def test_internal_reader_constructor_mock_only_tests_route(self):
        # Do NOT label this as an actual TLS network test: it mocks the ctor.
        with mock.patch.object(v05, "PublicGitHubReader", return_value=self.fake):
            r = v05.assess_github_pr(OWNER, REPO, PR)
        self.assertEqual(r["claim_correspondence"], "MATCH")
        self.assertEqual(r["source_delivery"], "GITHUB_API_TLS_ROUTE")
        self.assertEqual(r["status"], "UNKNOWN")
        self.assertEqual(r["execution_attestation"], "NOT_ESTABLISHED")

    def test_invalid_repo_fails_closed(self):
        r = v05.assess_github_pr("../escape", "Ario", PR, reader=self.fake)
        self.assertEqual(r["status"], "UNKNOWN")
        self.assertEqual(r["claim_correspondence"], "UNKNOWN")

    def test_cli_outputs_one_json_unknown(self):
        out = io.StringIO()
        with mock.patch.object(v05, "assess_github_pr", return_value=self.audit()), redirect_stdout(out):
            code = v05.main(["--owner", OWNER, "--repo", REPO, "--pr", "249"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())["status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
