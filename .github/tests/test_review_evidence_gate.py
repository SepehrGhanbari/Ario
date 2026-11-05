"""Offline deterministic unit tests for the repository-only evidence gate."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from review_evidence_gate import (GateError, parse_record, protected_path,
                                  validate_candidate)

HEAD = "a" * 40


def record(**overrides):
    base = {
        "version": 1,
        "scope": "ROUTINE_LAB",
        "reviewed_head_sha": HEAD,
        "files": ["implementation/witness_provenance_experiment.py", "ENGINEERING_LOG.md"],
        "red_run_ids": [1201],
        "green_run_id": 1202,
        "red_failure": "Expected a specific synthetic custody regression and got false-positive separation.",
        "risk_disposition": "NO_KNOWN_BLOCKERS",
        "limitations": "LAB-only result; no live authentication, admission, signer, Genesis or production.",
    }
    base.update(overrides)
    return base


def candidate():
    pr = {
        "state": "open",
        "draft": False,
        "base": {"ref": "main"},
        "head": {"sha": HEAD, "ref": "fix/issue129-test",
                 "repo": {"full_name": "SepehrGhanbari/Ario"}},
        "user": {"login": "SepehrGhanbari"},
    }
    files = [{"filename": x, "status": "modified"} for x in record()["files"]]
    reviews = [{
        "user": {"login": "coderabbitai[bot]"},
        "state": "COMMENTED",
        "commit_id": HEAD,
        "body": "No blockers found in this synthetic fixture.",
        "submitted_at": "2026-11-03T14:00:00Z",
    }]
    runs = {
        1201: {"conclusion": "failure", "name": "Implementation Regression",
               "head_branch": "fix/issue129-test", "head_sha": "b" * 40,
               "head_repository": {"full_name": "SepehrGhanbari/Ario"}},
        1202: {"conclusion": "success", "name": "Implementation Regression",
               "head_sha": HEAD, "head_branch": "fix/issue129-test",
               "head_repository": {"full_name": "SepehrGhanbari/Ario"},
               "jobs": [{"name": "m0-regression", "conclusion": "success",
                         "steps": [{"name": "Run M0 and runtime regression suites",
                                    "conclusion": "success"}]}]},
    }
    return [pr, record(), files, reviews, [], runs]


class ReviewEvidenceGateTests(unittest.TestCase):
    def test_valid_record_and_fresh_review(self):
        payload = json.dumps(record())
        parsed = parse_record("About\n<!-- ARIO_REVIEW_EVIDENCE_V1\n" + payload + "\n-->")
        self.assertEqual(parsed, record())
        self.assertTrue(validate_candidate(*candidate()))

    def test_missing_or_duplicate_record_is_rejected(self):
        for body in ("", "ordinary PR description",
                     "<!-- ARIO_REVIEW_EVIDENCE_V1\n{}\n-->"):
            with self.subTest(body=body):
                with self.assertRaises(GateError):
                    parse_record(body)

    def test_wrong_sha_rejected(self):
        case = candidate()
        case[1]["reviewed_head_sha"] = "b" * 40
        with self.assertRaisesRegex(GateError, "STALE_REVIEW_RECORD_SHA"):
            validate_candidate(*case)

    def test_code_author_cannot_self_review(self):
        case = candidate()
        case[3][0]["user"]["login"] = "SepehrGhanbari"
        case[3][0]["state"] = "APPROVED"
        with self.assertRaisesRegex(GateError, "NO_FRESH_INDEPENDENT"):
            validate_candidate(*case)

    def test_stale_independent_review_rejected(self):
        case = candidate()
        case[3][0]["commit_id"] = "c" * 40
        with self.assertRaisesRegex(GateError, "NO_FRESH_INDEPENDENT"):
            validate_candidate(*case)

    def test_unresolved_review_thread_blocks(self):
        case = candidate()
        case[4] = [{"isResolved": False}]
        with self.assertRaisesRegex(GateError, "UNRESOLVED_REVIEW_THREAD"):
            validate_candidate(*case)

    def test_reported_major_finding_blocks(self):
        case = candidate()
        case[3][0]["body"] = "**Major** A high confidence source defect remains."
        with self.assertRaisesRegex(GateError, "INDEPENDENT_REVIEW_REPORTS_MAJOR"):
            validate_candidate(*case)

    def test_edited_older_exact_head_major_is_not_hidden_by_newer_clean_review(self):
        case = candidate()
        older = dict(case[3][0])
        older["body"] = "**Major** This remains a security blocker."
        older["submitted_at"] = "2026-11-03T13:00:00Z"
        newer = dict(case[3][0])
        newer["body"] = "No blocker in this later comment."
        newer["submitted_at"] = "2026-11-03T15:00:00Z"
        case[3] = [older, newer]
        with self.assertRaisesRegex(GateError, "INDEPENDENT_REVIEW_REPORTS_MAJOR"):
            validate_candidate(*case)


    def test_red_must_come_from_same_branch(self):
        case = candidate()
        case[5][1201]["head_branch"] = "other-branch"
        with self.assertRaisesRegex(GateError, "RED_RUN_FROM_OTHER_BRANCH"):
            validate_candidate(*case)

    def test_green_must_come_from_same_branch(self):
        case = candidate()
        case[5][1202]["head_branch"] = "other-branch"
        with self.assertRaisesRegex(GateError, "GREEN_RUN_FROM_OTHER_BRANCH"):
            validate_candidate(*case)

    def test_green_must_be_current_head(self):
        case = candidate()
        case[5][1202]["head_sha"] = "b" * 40
        with self.assertRaisesRegex(GateError, "GREEN_NOT_CURRENT_HEAD"):
            validate_candidate(*case)

    def test_red_must_really_fail(self):
        case = candidate()
        case[5][1201]["conclusion"] = "success"
        with self.assertRaisesRegex(GateError, "RED_RUN_NOT_FAILED"):
            validate_candidate(*case)

    def test_governance_and_authority_paths_block(self):
        paths = [
            "AGENTS.md", ".github/workflows/review-evidence-gate.yml",
            ".github/CODEOWNERS", "docs/REVIEW_AND_MERGE_POLICY_V1.md",
            "architecture/ARCHITECTURE.md",
            "implementation/owner_signer.py",
            "implementation/EVIDENCE_ADMISSION_CONTRACT_V0_1.md",
            "implementation/tests/test_authorization.py",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(protected_path(path))
        case = candidate()
        case[2][0]["filename"] = "implementation/owner_signer.py"
        case[1]["files"][0] = "implementation/owner_signer.py"
        with self.assertRaisesRegex(GateError, "PROTECTED_GOVERNANCE"):
            validate_candidate(*case)

    def test_typed_metadata_fails_closed(self):
        for override in [
            {"red_run_ids": ["1201"]},
            {"red_run_ids": []},
            {"green_run_id": True},
            {"reviewed_head_sha": HEAD[:-1]},
            {"risk_disposition": "UNKNOWN"},
            {"files": ["implementation/witness_provenance_experiment.py"]},
            {"limitations": ""},
        ]:
            with self.subTest(override=override):
                body = "<!-- ARIO_REVIEW_EVIDENCE_V1\n" + json.dumps(record(**override)) + "\n-->"
                with self.assertRaises(GateError):
                    parse_record(body)




# P0 RED specifications: these MUST fail on the original PR #133 baseline.
# Each assertion uses synthetic values only; GitHub API/installation not tested.
class GateP0NegativeFixtures(unittest.TestCase):
    def test_unknown_implementation_source_defaults_to_protected(self):
        self.assertTrue(protected_path("implementation/new_unreviewed_power.py"))

    def test_relative_git_path_is_not_normalized_into_routine(self):
        self.assertTrue(protected_path("implementation/../unreviewed.py"))

    def test_rename_from_protected_old_path_is_rejected(self):
        case = candidate()
        target = "implementation/tests/test_witness_provenance_experiment.py"
        case[1]["files"][0] = target
        case[2][0] = {"filename": target, "status": "renamed",
                      "previous_filename": "implementation/owner_signer.py"}
        with self.assertRaises(GateError):
            validate_candidate(*case)

    def test_unknown_change_operation_is_rejected(self):
        case = candidate()
        case[2][0]["status"] = "copied"
        with self.assertRaises(GateError):
            validate_candidate(*case)

    def test_log_historical_prefix_mutation_is_refused(self):
        from review_evidence_gate import validate_log_append_only
        with self.assertRaises(GateError):
            validate_log_append_only(b"historical truth\n", b"historical lie\nnew entry\n")

    def test_red_run_at_green_head_is_not_prefixed_regression(self):
        case = candidate()
        case[5][1201]["head_sha"] = HEAD
        with self.assertRaises(GateError):
            validate_candidate(*case)

    def test_red_run_fork_with_matching_branch_name_is_rejected(self):
        case = candidate()
        case[5][1201]["head_repository"] = {"full_name": "unrelated/Ario"}
        with self.assertRaises(GateError):
            validate_candidate(*case)

    def test_green_missing_regression_job_is_not_evidence(self):
        case = candidate()
        case[5][1202]["jobs"] = [{"name": "unrelated-smoke",
                                   "conclusion": "success"}]
        with self.assertRaises(GateError):
            validate_candidate(*case)



# Independent offline API-collector controls. No GitHub network or credentials.
class GateP0CollectorTests(unittest.TestCase):
    def test_log_readback_verifies_exact_git_blob(self):
        import base64
        import hashlib
        from unittest.mock import patch
        import review_evidence_gate as g
        payload = b"history preserved\n"
        gitsha = hashlib.sha1(
            b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()
        response = {"type": "file", "encoding": "base64",
                    "size": len(payload), "sha": gitsha,
                    "content": base64.b64encode(payload).decode("ascii") + "\n"}
        with patch.object(g, "api_request", return_value=response) as api:
            self.assertEqual(g.fetch_log_bytes("SepehrGhanbari/Ario", "a" * 40),
                             payload)
        self.assertEqual(api.call_count, 1)

    def test_log_readback_rejects_wrong_content_at_same_size(self):
        import base64
        import hashlib
        from unittest.mock import patch
        import review_evidence_gate as g
        original = b"original\n"
        tampered = b"changed!\n"
        digest = hashlib.sha1(
            b"blob " + str(len(original)).encode("ascii") + b"\0" + original).hexdigest()
        response = {"type": "file", "encoding": "base64", "sha": digest,
                    "size": len(tampered),
                    "content": base64.b64encode(tampered).decode("ascii")}
        with patch.object(g, "api_request", return_value=response):
            with self.assertRaisesRegex(GateError, "LOG_BLOB_IDENTITY_MISMATCH"):
                g.fetch_log_bytes("SepehrGhanbari/Ario", "a" * 40)

    def test_git_tree_truncation_refuses_mode_evidence(self):
        from unittest.mock import patch
        import review_evidence_gate as g
        commit = {"tree": {"sha": "b" * 40}}
        incomplete = {"truncated": True, "tree": []}
        with patch.object(g, "api_request", side_effect=[commit, incomplete]):
            with self.assertRaisesRegex(GateError, "TREE_TRUNCATED_OR_OVERSIZED"):
                g.regular_modes_at_commit("SepehrGhanbari/Ario", "a" * 40)

    def test_no_prefix_change_even_after_new_append(self):
        import review_evidence_gate as g
        g.validate_log_append_only(b"original\n", b"original\nnew\n")
        with self.assertRaisesRegex(GateError, "LOG_HISTORICAL_PREFIX_CHANGED"):
            g.validate_log_append_only(b"original\n", b"altered!\nnew\n")

if __name__ == "__main__":
    unittest.main()
