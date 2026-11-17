"""Read-only GitHub evidence bridge: offline, mock REST responses; never network."""
from __future__ import annotations
import copy
import json
import unittest
from unittest import mock
from urllib.error import HTTPError
from io import BytesIO

from pr_claim_audit import OPEN, CLOSE
from pr_claim_audit_github_v0_3 import (
    PublicGitHubReader, assess_github_pr, OriginUnknown, _NoRedirect, _valid_repo
)

SHA = "c800b45c2c06d1bbeacaa063cca4573f0ec1d879"
LOG = ("2026-11-16T20:27:42.3105798Z Python 3.14.10 (main, Oct 26 2026) [GCC]\n"
       "2026-11-16T20:27:42.4802125Z ##[group]Run python -m pytest -q tests\n"
       "2026-11-16T20:27:49.2372855Z 1 failed, 1140 passed, 121 subtests passed in 6.08s")
CLAIM = {
    "schema": "ARIO-PR-CI-0.1", "head_sha": SHA, "run_id": 43949946093,
    "run_attempt": 1, "job_id": 133589448819, "python_version": "3.14.10",
    "pytest_command": "python -m pytest -q tests", "passed": 1140,
    "failed": 1, "skipped": 0, "subtests_passed": 121,
    "job_conclusion": "failure",
}


def claim_body(**updates):
    return OPEN + "\n" + json.dumps({**CLAIM, **updates}) + "\n" + CLOSE


class FakeGitHub:
    """Synthetic transport; cannot grant positive final verdict."""
    def __init__(self):
        self.pr = {"number": 249, "id": 5344518184, "head": {"sha": SHA}, "body": claim_body()}
        self.run = {"id": 43949946093, "run_attempt": 1, "head_sha": SHA,
                    "event": "pull_request", "status": "completed", "conclusion": "failure",
                    "pull_requests": [{"number": 249, "id": 5344518184, "head": {"sha": SHA}}]}
        self.job = {"id": 133589448819, "run_id": 43949946093, "run_attempt": 1,
                    "head_sha": SHA, "status": "completed", "conclusion": "failure",
                    "name": "python-314-differential-advisory"}
        self.log = LOG
        self.job_total = 1
        self.next_pr = None
        self.call_count_pr = 0
        self.fail_log = False
        self.calls = []

    def get_json(self, url):
        self.calls.append(url)
        if url.endswith("/pulls/249"):
            self.call_count_pr += 1
            return copy.deepcopy(self.next_pr if self.next_pr and self.call_count_pr > 1 else self.pr)
        if url.endswith("/actions/runs/43949946093"):
            return copy.deepcopy(self.run)
        if "/attempts/1/jobs?" in url:
            return {"total_count": self.job_total, "jobs": [copy.deepcopy(self.job)]}
        raise AssertionError("unexpected GitHub API GET " + url)

    def get_job_log(self, url):
        self.calls.append(url)
        if self.fail_log:
            raise OriginUnknown("GitHub log unavailable")
        if url != "https://api.github.com/repos/SepehrGhanbari/Ario/actions/jobs/133589448819/logs":
            raise AssertionError("invalid log endpoint")
        return self.log


class GitHubBridgeTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeGitHub()

    def call(self):
        return assess_github_pr("SepehrGhanbari", "Ario", 249, reader=self.fake)

    def test_mock_source_yields_correspondence_match_but_final_unknown(self):
        result = self.call()
        self.assertEqual(result["correspondence_status"], "MATCH")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["origin_status"], "UNVERIFIED")
        self.assertEqual(len(self.fake.calls), 5)
        self.assertTrue(self.fake.calls[3].endswith("/logs"))

    def test_mutated_count_reports_diagnostic_mismatch_but_stays_unknown(self):
        self.fake.pr["body"] = claim_body(passed=1141)
        result = self.call()
        self.assertEqual(result["correspondence_status"], "MISMATCH")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("passed", result["differences"])

    def test_forged_log_plus_matching_forged_count_still_unknown(self):
        self.fake.log = LOG.replace("1140 passed", "9999 passed")
        self.fake.pr["body"] = claim_body(passed=9999)
        result = self.call()
        self.assertEqual(result["correspondence_status"], "MATCH")
        self.assertEqual(result["status"], "UNKNOWN")

    def test_pr_head_different_from_claim_unknown(self):
        self.fake.pr["head"]["sha"] = "f"*40
        self.assertEqual(self.call()["status"], "UNKNOWN")
        self.assertEqual(len(self.fake.calls), 1)

    def test_run_head_different_from_pr_unknown(self):
        self.fake.run["head_sha"] = "f"*40
        self.assertEqual(self.call()["status"], "UNKNOWN")

    def test_run_not_linked_to_actual_pr_unknown(self):
        self.fake.run["pull_requests"] = []
        self.assertIn("not linked", self.call()["reason"])

    def test_same_number_and_sha_but_wrong_pr_global_id_unknown(self):
        self.fake.run["pull_requests"][0]["id"] = 999999999
        self.assertIn("not linked", self.call()["reason"])

    def test_wrong_run_attempt_unknown(self):
        self.fake.run["run_attempt"] = 2
        self.assertEqual(self.call()["status"], "UNKNOWN")

    def test_wrong_job_attempt_unknown(self):
        self.fake.job["run_attempt"] = 2
        self.assertEqual(self.call()["status"], "UNKNOWN")

    def test_wrong_job_run_unknown(self):
        self.fake.job["run_id"] = 111
        self.assertEqual(self.call()["status"], "UNKNOWN")

    def test_wrong_job_sha_unknown(self):
        self.fake.job["head_sha"] = "f" * 40
        self.assertEqual(self.call()["status"], "UNKNOWN")

    def test_missing_job_fails_closed(self):
        self.fake.job["id"] = 999
        self.assertEqual(self.call()["status"], "UNKNOWN")

    def test_oversized_job_page_count_unknown(self):
        self.fake.job_total = 999
        self.assertEqual(self.call()["status"], "UNKNOWN")

    def test_missing_claim_returns_unknown(self):
        self.fake.pr["body"] = "No structured CI claim"
        self.assertEqual(self.call()["status"], "UNKNOWN")

    def test_log_not_available_unknown(self):
        self.fake.fail_log = True
        self.assertEqual(self.call()["status"], "UNKNOWN")

    def test_pr_head_moved_between_fetches_unknown(self):
        self.fake.next_pr = copy.deepcopy(self.fake.pr)
        self.fake.next_pr["head"]["sha"] = "f"*40
        self.assertIn("moved", self.call()["reason"])

    def test_pr_body_edited_between_fetches_unknown(self):
        self.fake.next_pr = copy.deepcopy(self.fake.pr)
        self.fake.next_pr["body"] += "edited"
        self.assertIn("moved", self.call()["reason"])

    def test_pretend_origin_verified_cannot_be_supplied(self):
        self.fake.pr["origin_verified"] = True
        self.fake.run["origin_status"] = "VERIFIED"
        self.assertEqual(self.call()["status"], "UNKNOWN")

    def test_bad_owner_repository_rejected_no_network(self):
        self.assertEqual(assess_github_pr("../etc", "Ario", 249, reader=self.fake)["status"], "UNKNOWN")
        self.assertEqual(assess_github_pr("Sepehr", "../../etc", 249, reader=self.fake)["status"], "UNKNOWN")
        self.assertEqual(self.fake.calls, [])

    def test_job_log_hosts_only_known_https_actions(self):
        good = ["https://results-receiver.actions.githubusercontent.com/foo?key=abc",
                "https://productionresultssa20.blob.core.windows.net/a/b?sig=abc"]
        bad = ["http://results-receiver.actions.githubusercontent.com/a",
               "https://localhost/a", "https://example.com/a", "https://productionresultssa20.blob.core.windows.net.evil.test/a",
               "https://user:pw@results-receiver.actions.githubusercontent.com/a", "file:///etc/passwd"]
        for u in good:
            self.assertTrue(PublicGitHubReader._is_actions_log_host(u), u)
        for u in bad:
            self.assertFalse(PublicGitHubReader._is_actions_log_host(u), u)

    def test_api_redirect_is_not_followed(self):
        reader = PublicGitHubReader()
        with mock.patch.object(reader, "_fetch", return_value=(302,b"", "https://example.org")):
            with self.assertRaises(OriginUnknown):
                reader.get_json("https://api.github.com/repos/x/y/pulls/1")

    def test_job_log_redirect_to_unexpected_host_rejected(self):
        reader = PublicGitHubReader()
        with mock.patch.object(reader, "_fetch", return_value=(302,b"", "https://evil.invalid")):
            with self.assertRaises(OriginUnknown):
                reader.get_job_log("https://api.github.com/repos/x/y/actions/jobs/1/logs")

    def test_allowed_log_redirect_is_followed_once(self):
        reader = PublicGitHubReader()
        redirect = "https://results-receiver.actions.githubusercontent.com/job.txt?sig=notreal"
        with mock.patch.object(reader, "_fetch", side_effect=[
            (302, b"", redirect), (200, LOG.encode("utf-8"), None)
        ]) as getter:
            text = reader.get_job_log("https://api.github.com/repos/x/y/actions/jobs/1/logs")
        self.assertEqual(text, LOG)
        self.assertEqual(getter.call_count, 2)
        self.assertEqual(getter.call_args_list[1].args[0], redirect)

    def test_fake_job_pagination_must_be_complete(self):
        self.fake.job_total = 2
        self.assertEqual(self.call()["status"], "UNKNOWN")

    def test_injected_real_reader_still_cannot_promote_status(self):
        # Even an actual-class object whose get_json/get_job_log are monkeypatched
        # is treated as injected, not externally authenticated.
        reader = PublicGitHubReader()
        with mock.patch.object(reader, "get_json", side_effect=self.fake.get_json), \
             mock.patch.object(reader, "get_job_log", side_effect=self.fake.get_job_log):
            result = assess_github_pr("SepehrGhanbari", "Ario", 249, reader=reader)
        self.assertEqual(result["correspondence_status"], "MATCH")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["origin_status"], "UNVERIFIED")

    def test_mocked_internal_reader_checks_positive_branch_only(self):
        # Patch only the constructor for an *offline branch-coverage test*.
        # This is NOT a live GitHub network origin observation.
        fake = self.fake
        reader = PublicGitHubReader()
        with mock.patch("pr_claim_audit_github_v0_3.PublicGitHubReader", return_value=reader), \
             mock.patch.object(reader, "get_json", side_effect=fake.get_json), \
             mock.patch.object(reader, "get_job_log", side_effect=fake.get_job_log):
            result = assess_github_pr("SepehrGhanbari", "Ario", 249)
        self.assertEqual(result["correspondence_status"], "MATCH")
        self.assertEqual(result["status"], "MATCH")
        self.assertEqual(result["origin_status"], "GITHUB_API_TLS_FETCHED")


if __name__ == "__main__":
    unittest.main()
