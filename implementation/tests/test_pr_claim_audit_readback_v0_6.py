"""v0.6 regression checks for explicit PR read sampling and safe source wording."""
from __future__ import annotations

import copy
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest import mock

import pr_claim_audit_readback_v0_6 as v06
from test_pr_claim_audit_state_v0_5 import ThirdReadChange, OWNER, REPO, PR


class PartialFinalRead(ThirdReadChange):
    def get_json(self, url):
        if url.endswith("/pulls/249") and self.call_count_pr == 2:
            self.call_count_pr += 1
            self.calls.append(url)
            return {"number": 249, "id": self.pr["id"], "head": {"sha": self.pr["head"]["sha"]}}
        return super().get_json(url)


class ReadbackReports(unittest.TestCase):
    def setUp(self):
        self.fake = ThirdReadChange()

    def audit(self, reader=None):
        return v06.assess_github_pr(OWNER, REPO, PR, reader=self.fake if reader is None else reader)

    def test_clean_pr_three_reads_safe_vocabulary(self):
        r = self.audit()
        self.assertEqual(r["pr_read_count"], 3)
        self.assertEqual(r["final_pr_readback_status"], "OK")
        self.assertEqual(r["last_pr_head_sha_observed"], self.fake.pr["head"]["sha"])
        self.assertEqual(r["claim_correspondence"], "MATCH")
        self.assertEqual(r["state_consistency"], "STABLE_AT_SAMPLED_READS")
        self.assertEqual(r["source_delivery"], "READER_RESPONSE_UNATTESTED")
        self.assertEqual(r["tls_route_verification"], "NOT_INDEPENDENTLY_VERIFIED")
        self.assertEqual(r["transport_configuration"], "CALLER_INJECTED_READER")
        self.assertEqual(r["status"], "UNKNOWN")
        self.assertNotIn("current_head_sha", r)
        self.assertFalse(any("identity" in x for x in r["pr_read_samples"]))

    def test_head_moves_at_third_read_report_last_observed_head_not_current(self):
        self.fake.changed_pr = copy.deepcopy(self.fake.pr)
        self.fake.changed_pr["head"]["sha"] = "f" * 40
        r = self.audit()
        self.assertEqual(r["final_pr_readback_status"], "CHANGED")
        self.assertEqual(r["last_pr_head_sha_observed"], "f" * 40)
        self.assertEqual(r["pinned_pr_head_sha"], self.fake.pr["head"]["sha"])
        self.assertEqual(r["claim_correspondence"], "UNKNOWN")
        self.assertEqual(r["state_consistency"], "PR_CHANGED")
        self.assertIsNone(r["binding"])
        self.assertEqual(r["status"], "UNKNOWN")

    def test_body_changes_without_sha_change_is_explicit_change(self):
        self.fake.changed_pr = copy.deepcopy(self.fake.pr)
        self.fake.changed_pr["body"] += "\nupdated"
        r = self.audit()
        self.assertEqual(r["final_pr_readback_status"], "CHANGED")
        self.assertEqual(r["last_pr_head_sha_observed"], self.fake.pr["head"]["sha"])
        self.assertEqual(r["claim_correspondence"], "UNKNOWN")

    def test_failed_last_get_sets_head_unresolved(self):
        self.fake.fail_final_pr = True
        r = self.audit()
        self.assertEqual(r["final_pr_readback_status"], "FAILED")
        self.assertIsNone(r["last_pr_head_sha_observed"])
        self.assertEqual(r["claim_correspondence"], "UNKNOWN")
        self.assertEqual(r["state_consistency"], "UNRESOLVED")
        self.assertEqual(r["pr_read_samples"][-1]["result"], "FAILED")
        self.assertNotIn("current_head_sha", r)

    def test_partial_final_get_not_validated_as_last_head(self):
        r = self.audit(reader=PartialFinalRead())
        self.assertEqual(r["final_pr_readback_status"], "PARTIAL")
        self.assertIsNone(r["last_pr_head_sha_observed"])
        self.assertEqual(r["state_consistency"], "UNRESOLVED")
        self.assertEqual(r["claim_correspondence"], "UNKNOWN")

    def test_workflow_conclusion_change_keeps_diagnostic_match(self):
        self.fake.next_run = copy.deepcopy(self.fake.run)
        self.fake.next_run["conclusion"] = "success"
        r = self.audit()
        self.assertEqual(r["claim_correspondence"], "MATCH")
        self.assertEqual(r["state_consistency"], "WORKFLOW_CONCLUSION_CHANGED")
        self.assertTrue(r["workflow_state_changed_during_recheck"])
        self.assertEqual(r["status"], "UNKNOWN")

    def test_missing_run_conclusion_does_not_report_stable(self):
        self.fake.run.pop("conclusion", None)
        r = self.audit()
        self.assertNotEqual(r["state_consistency"], "STABLE_AT_SAMPLED_READS")
        self.assertEqual(r["status"], "UNKNOWN")

    def test_missing_selected_job_results_in_no_final_pr_recheck(self):
        self.fake.job["id"] = 111
        r = self.audit()
        self.assertEqual(r["final_pr_readback_status"], "NOT_REACHED")
        self.assertIsNone(r["last_pr_head_sha_observed"])
        self.assertEqual(r["status"], "UNKNOWN")

    def test_fake_github_verified_claim_cannot_promote(self):
        self.fake.pr["origin_verified"] = True
        self.fake.run["test_execution_attested"] = True
        r = self.audit()
        self.assertEqual(r["source_delivery"], "READER_RESPONSE_UNATTESTED")
        self.assertEqual(r["execution_attestation"], "NOT_ESTABLISHED")
        self.assertEqual(r["status"], "UNKNOWN")

    def test_even_mocked_internal_reader_has_no_tls_verified_claim(self):
        with mock.patch.object(v06, "PublicGitHubReader", return_value=self.fake):
            r = v06.assess_github_pr(OWNER, REPO, PR)
        self.assertEqual(r["transport_configuration"], "PUBLIC_READER_CONFIGURED")
        self.assertEqual(r["source_delivery"], "READER_RESPONSE_UNATTESTED")
        self.assertEqual(r["tls_route_verification"], "NOT_INDEPENDENTLY_VERIFIED")
        self.assertEqual(r["status"], "UNKNOWN")

    def test_invalid_owner_returns_unknown_without_claiming_pr_head(self):
        r = v06.assess_github_pr("../bad", REPO, PR, reader=self.fake)
        self.assertEqual(r["final_pr_readback_status"], "NOT_REACHED")
        self.assertIsNone(r["last_pr_head_sha_observed"])
        self.assertEqual(r["status"], "UNKNOWN")

    def test_report_samples_have_ordered_local_time_not_server_attestation(self):
        r = self.audit()
        samples = r["pr_read_samples"]
        self.assertTrue(all("requested_utc" in s and "completed_utc" in s for s in samples))
        self.assertTrue(all(s["requested_utc"] <= s["completed_utc"] for s in samples))
        self.assertIn("T", samples[-1]["completed_utc"])
        self.assertFalse(any("server_time" in s for s in samples))

    def test_cli_one_json_unknown(self):
        out = io.StringIO()
        with mock.patch.object(v06, "assess_github_pr", return_value=self.audit()), redirect_stdout(out):
            self.assertEqual(v06.main(["--owner",OWNER,"--repo",REPO,"--pr","249"]),0)
        self.assertEqual(json.loads(out.getvalue())["status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
