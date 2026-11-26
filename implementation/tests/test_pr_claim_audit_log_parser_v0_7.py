"""Hallaaj 2026-11-17 real-log incompatibility: additive RED/GREEN controls."""
from __future__ import annotations

import copy
import hashlib
import json
import unittest

import pr_claim_audit as v01
import pr_claim_audit_log_parser_v0_7 as v07

HEAD = "a67c63934a4a0a993fc14032ad29920cc970807f"
CMD = "2026-11-17T16:14:51.1730758Z ##[group]Run python -m pytest -q tests"
SETUP = "2026-11-17T16:14:44.0507715Z Successfully set up CPython (3.13.18)"
SUMMARY = "2026-11-17T16:14:58.5347756Z 1253 passed, 2 skipped, 2 warnings, 124 subtests passed in 6.36s"


def make_log(summary: str = SUMMARY, setup: str = SETUP, command: str = CMD) -> str:
    return "\n".join([setup, command, summary])


def claim_text(*, passed: int = 1253, python_version: str = "3.13.18") -> str:
    claim = {
        "schema": "ARIO-PR-CI-0.1", "head_sha": HEAD,
        "run_id": 44123481398, "run_attempt": 1, "job_id": 134180830525,
        "python_version": python_version, "pytest_command": "python -m pytest -q tests",
        "passed": passed, "failed": 0, "skipped": 2, "subtests_passed": 124,
        "job_conclusion": "success",
    }
    return "<!-- ARIO-CI-CLAIM-V0.1\n"+json.dumps(claim)+"\nARIO-CI-CLAIM-V0.1 -->"


def evidence(log: str | None = None) -> dict:
    if log is None:
        log = make_log()
    return {
        "run": {"id":44123481398,"run_attempt":1,"head_sha":HEAD,"status":"completed",
                "event":"pull_request","conclusion":"success"},
        "job": {"id":134180830525,"run_id":44123481398,"run_attempt":1,
                "head_sha":HEAD,"status":"completed","name":"m0-regression","conclusion":"success"},
        "job_log_complete":True,
        "job_log":log,
        "job_log_sha256":hashlib.sha256(log.encode("utf-8")).hexdigest(),
    }


class RealLogReproduction(unittest.TestCase):
    def test_v01_real_git_log_excerpt_is_red(self):
        with self.assertRaisesRegex(v01.Invalid, "no test outcome count"):
            v01._extract_log(make_log())

    def test_v01_version_remains_red_without_warnings(self):
        no_warn=SUMMARY.replace("2 warnings, ", "")
        with self.assertRaisesRegex(v01.Invalid, "missing or conflicting python version"):
            v01._extract_log(make_log(no_warn))

    def test_v07_real_git_log_excerpt_green(self):
        r=v07.extract_log(make_log())
        self.assertEqual(r,{"passed":1253,"failed":0,"skipped":2,"subtests_passed":124,
                             "python_version":"3.13.18","pytest_command":"python -m pytest -q tests"})

    def test_v07_snapshot_diagnostic_match_but_final_unknown(self):
        r=v07.assess(claim_text(),evidence())
        self.assertEqual(r["claim_correspondence"],"MATCH")
        self.assertEqual(r["status"],"UNKNOWN")
        self.assertEqual(r["execution_attestation"],"NOT_ESTABLISHED")
        self.assertEqual(r["source_delivery"],"UNVERIFIED")
        self.assertEqual(r["binding"]["job_log_sha256"], evidence()["job_log_sha256"])

    def test_without_warning(self):
        self.assertEqual(v07.extract_log(make_log(SUMMARY.replace("2 warnings, ", "")))["passed"],1253)

    def test_reordered_warning_and_subtest(self):
        reord=SUMMARY.replace("2 skipped, 2 warnings, 124 subtests passed", "124 subtests passed, 2 warnings, 2 skipped")
        self.assertEqual(v07.extract_log(make_log(reord))["subtests_passed"],124)

    def test_singular_warning(self):
        one=SUMMARY.replace("2 warnings", "1 warning")
        self.assertEqual(v07.extract_log(make_log(one))["skipped"],2)

    def test_original_python_line_recognized(self):
        old="2026-11-17T16:14:44.0Z Python 3.13.18"
        self.assertEqual(v07.extract_log(make_log(setup=old))["python_version"],"3.13.18")

    def test_conflicting_python_versions_rejected(self):
        with self.assertRaisesRegex(v01.Invalid,"conflicting python version"):
            v07.extract_log(make_log()+"\nPython 3.12.0")

    def test_arbitrary_other_version_not_accepted(self):
        with self.assertRaisesRegex(v01.Invalid,"python version"):
            v07.extract_log(make_log(setup="Installed package CPython (3.13.18)"))

    def test_future_unsupported_warning_like_field_does_not_silent_tail_match(self):
        new=SUMMARY.replace("2 warnings", "2 flaky")
        with self.assertRaisesRegex(v01.Invalid,"unsupported pytest summary component"):
            v07.extract_log(make_log(new))

    def test_warning_only_is_not_success(self):
        with self.assertRaisesRegex(v01.Invalid,"no test outcome count"):
            v07.extract_log(make_log("2 warnings in 6.36s"))

    def test_duplicate_warning_field_rejected(self):
        line=SUMMARY.replace("2 warnings", "2 warnings, 1 warning")
        with self.assertRaisesRegex(v01.Invalid,"duplicate pytest summary field"):
            v07.extract_log(make_log(line))

    def test_duplicate_passed_field_rejected(self):
        line=SUMMARY.replace("2 skipped", "5 passed, 2 skipped")
        with self.assertRaisesRegex(v01.Invalid,"duplicate pytest summary field"):
            v07.extract_log(make_log(line))

    def test_multiple_complete_summaries_rejected(self):
        with self.assertRaisesRegex(v01.Invalid,"ambiguous pytest summary"):
            v07.extract_log(make_log()+"\n"+SUMMARY)

    def test_incorrect_claim_remains_diagnostic_mismatch(self):
        r=v07.assess(claim_text(passed=9999),evidence())
        self.assertEqual(r["claim_correspondence"],"MISMATCH")
        self.assertEqual(r["differences"],["passed"])
        self.assertEqual(r["status"],"UNKNOWN")

    def test_log_checksum_tamper_downgrades(self):
        e=evidence();e["job_log"]+="\nmodified"
        r=v07.assess(claim_text(),e)
        self.assertEqual(r["claim_correspondence"],"UNKNOWN")
        self.assertEqual(r["reason"],"log digest mismatch")

    def test_head_mismatch_downgrades(self):
        e=evidence();e["run"]["head_sha"]="f"*40
        r=v07.assess(claim_text(),e)
        self.assertEqual(r["claim_correspondence"],"UNKNOWN")
        self.assertEqual(r["status"],"UNKNOWN")

    def test_job_attempt_mismatch_downgrades(self):
        e=evidence();e["job"]["run_attempt"]=2
        r=v07.assess(claim_text(),e)
        self.assertEqual(r["claim_correspondence"],"UNKNOWN")

    def test_missing_command_downgrades(self):
        r=v07.assess(claim_text(),evidence(make_log(command="some other command")))
        self.assertEqual(r["claim_correspondence"],"UNKNOWN")

    def test_duplicate_command_downgrades(self):
        with self.assertRaisesRegex(v01.Invalid,"exactly one"):
            v07.extract_log(make_log()+"\n"+CMD)

    def test_fake_pytest_log_never_attests(self):
        # This log was invented by a user, not GitHub. Correspondence only.
        r=v07.assess(claim_text(),evidence())
        self.assertEqual(r["claim_correspondence"],"MATCH")
        self.assertEqual(r["execution_attestation"],"NOT_ESTABLISHED")
        self.assertEqual(r["status"],"UNKNOWN")


if __name__=="__main__":
    unittest.main()
