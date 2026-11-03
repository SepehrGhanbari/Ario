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
        "head": {"sha": HEAD},
        "user": {"login": "SepehrGhanbari"},
    }
    files = [{"filename": x} for x in record()["files"]]
    reviews = [{
        "user": {"login": "coderabbitai[bot]"},
        "state": "COMMENTED",
        "commit_id": HEAD,
    }]
    runs = {
        1201: {"conclusion": "failure", "name": "Implementation Regression"},
        1202: {"conclusion": "success", "name": "Implementation Regression",
               "head_sha": HEAD},
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


if __name__ == "__main__":
    unittest.main()
