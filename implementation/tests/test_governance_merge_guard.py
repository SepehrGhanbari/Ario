"""Synthetic regressions for the research-only governance merge guard.

No network, credentials, GitHub API, check publication or merge authority.
Run from ``implementation``: ``python -m unittest tests.test_governance_merge_guard``.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from research import governance_merge_guard as guard

HEAD = "a1" * 20
BASE = "b2" * 20
MERGE = "c3" * 20
PARENT = "d4" * 20
OTHER_HEAD = "e5" * 20
PR_ID = 2400000000
PR_NUMBER = 400
REPO_ID = 1401709791
ACTIONS_APP = 15368
WORKFLOW = ".github/workflows/implementation-regression.yml"
AUTHOR = ("agent-author", 111)
REVIEWER = ("reviewer-y", 222)
MERGE_ACTOR = ("maintainer", 999)


def case() -> dict:
    return {
        "repository": {"id": REPO_ID, "full_name": "SepehrGhanbari/Ario"},
        "pr": {
            "number": PR_NUMBER, "id": PR_ID, "state": "closed", "draft": False,
            "merged": True, "merge_commit_sha": MERGE, "merge_method": "merge",
            "head_sha": HEAD, "base_sha": BASE, "head_branch": "research/example",
            "author_login": AUTHOR[0], "author_id": AUTHOR[1],
            "changed_files": [
                "implementation/example.py",
                "implementation/tests/test_example.py",
                "ENGINEERING_LOG.md",
            ],
        },
        "pin": {"pr_number": PR_NUMBER, "pr_id": PR_ID, "head_sha": HEAD, "base_sha": BASE},
        "reviews": [{
            "id": 1, "state": "APPROVED", "author_login": REVIEWER[0],
            "author_id": REVIEWER[1], "commit_id": HEAD, "dismissed": False,
        }],
        "checks": {
            "total_count": 1, "hasNextPage": False, "check_runs": [{
                "id": 77, "name": "m0-regression", "head_sha": HEAD,
                "status": "completed", "conclusion": "success", "app_id": ACTIONS_APP,
                "workflow_path": WORKFLOW, "event": "pull_request",
                "head_branch": "research/example", "run_id": 45669049221,
                "pull_requests": [{"id": PR_ID, "number": PR_NUMBER}],
            }],
        },
        "required": {"check_name": "m0-regression", "workflow_path": WORKFLOW,
                     "app_id": ACTIONS_APP, "required_approvals": 1},
        "merge_commit": {"sha": MERGE, "parents": [PARENT, HEAD],
                         "merged_by_login": MERGE_ACTOR[0], "merged_by_id": MERGE_ACTOR[1],
                         "method": "merge"},
        "bypass_actors": [],
        "log": {"path": "ENGINEERING_LOG.md", "status": "modified",
                "added": ["## synthetic research entry"], "removed": []},
        "protected_paths_extra": [],
    }


def run(obj: dict) -> dict:
    out = guard.assess(obj)
    assert out["merge_authorized"] is False, out
    assert out["trust_activated"] is False, out
    assert out["authority"] == "NON_AUTHORITATIVE_RESEARCH_ONLY", out
    return out


def mutate(**changes) -> dict:
    obj = case()
    for key, value in changes.items():
        if key == "review":
            obj["reviews"] = [value]
        elif key == "check":
            obj["checks"]["check_runs"] = [value]
        elif key == "checks":
            obj["checks"] = value
        elif key == "pr":
            obj["pr"].update(value)
        elif key == "merge":
            obj["merge_commit"].update(value)
        elif key == "log":
            obj["log"].update(value)
        elif key == "required":
            obj["required"].update(value)
        elif key == "pin":
            obj["pin"].update(value)
        elif key == "files":
            obj["pr"]["changed_files"] = value
        elif key == "bypass":
            obj["bypass_actors"] = value
        else:
            obj[key] = value
    return obj


def findings(out: dict) -> list[str]:
    return out["findings"]


class CoherentBaselineTests(unittest.TestCase):
    def test_coherent_supplied_metadata_is_process_only(self):
        out = run(case())
        self.assertEqual(out["disposition"], "PASS_PROCESS")
        self.assertEqual(out["reason"], "ALL_SUPPLIED_CHECKS_CONSISTENT")
        self.assertEqual(out["protected_paths"], [])
        self.assertEqual(out["pr_link_basis"], "EXPLICIT_LINK")
        self.assertFalse(out["merge_authorized"])

    def test_merge_commit_must_match_pr_pin(self):
        out = run(mutate(pr={"merge_commit_sha": OTHER_HEAD}))
        self.assertEqual(out["disposition"], "HOLD")
        self.assertIn("MERGE_COMMIT_MISMATCH", findings(out))

    def test_pin_identity_mismatch_fails_closed(self):
        out = run(mutate(pin={"pr_id": PR_ID + 1}))
        self.assertIn("PIN_IDENTITY_MISMATCH", findings(out))

    def test_empty_changed_file_evidence_is_rejected(self):
        out = run(mutate(files=[]))
        self.assertIn("NO_FILE_EVIDENCE", findings(out))


class ReviewBindingTests(unittest.TestCase):
    def review(self, **changes):
        review = copy.deepcopy(case()["reviews"][0])
        review.update(changes)
        return review

    def test_stale_approval_at_older_head_is_rejected(self):
        out = run(mutate(review=self.review(commit_id=OTHER_HEAD)))
        self.assertIn("STALE_OR_UNBOUND_APPROVAL", findings(out))
        self.assertIn("INSUFFICIENT_APPROVALS", findings(out))

    def test_unbound_approval_without_commit_is_rejected(self):
        out = run(mutate(review=self.review(commit_id=None)))
        self.assertIn("STALE_OR_UNBOUND_APPROVAL", findings(out))

    def test_self_approval_is_rejected(self):
        out = run(mutate(review=self.review(author_login=AUTHOR[0], author_id=AUTHOR[1])))
        self.assertIn("SELF_APPROVAL", findings(out))
        self.assertIn("INSUFFICIENT_APPROVALS", findings(out))

    def test_changes_requested_blocks_even_with_approval(self):
        obj = case()
        obj["reviews"].append({
            "id": 2, "state": "CHANGES_REQUESTED", "author_login": "reviewer-z",
            "author_id": 333, "commit_id": HEAD, "dismissed": False,
        })
        out = run(obj)
        self.assertIn("CHANGES_REQUESTED_PRESENT", findings(out))

    def test_zero_approval_policy_is_rejected(self):
        out = run(mutate(required={"required_approvals": 0}))
        self.assertIn("ZERO_APPROVAL_POLICY", findings(out))

    def test_two_distinct_head_approvals_satisfy_two_required(self):
        obj = case()
        obj["reviews"].append({
            "id": 3, "state": "APPROVED", "author_login": "reviewer-q",
            "author_id": 444, "commit_id": HEAD, "dismissed": False,
        })
        obj["required"]["required_approvals"] = 2
        self.assertEqual(run(obj)["disposition"], "PASS_PROCESS")


class CiProvenanceTests(unittest.TestCase):
    def check(self, **changes):
        run_obj = copy.deepcopy(case()["checks"]["check_runs"][0])
        run_obj.update(changes)
        return run_obj

    def test_shared_sha_check_from_another_pr_is_rejected(self):
        out = run(mutate(check=self.check(pull_requests=[{"id": PR_ID + 1, "number": PR_NUMBER + 1}])))
        self.assertIn("CROSS_PR_CHECK_REUSE", findings(out))

    def test_check_without_pr_link_is_rejected_by_default(self):
        out = run(mutate(check=self.check(pull_requests=[])))
        self.assertIn("CROSS_PR_CHECK_REUSE", findings(out))

    def test_event_and_branch_association_is_explicit_partial_basis(self):
        # GitHub REST returned empty pull_requests for real runs 45460415487 /
        # 45460397514; event + branch is the strongest remaining API signal.
        obj = mutate(check=self.check(pull_requests=[], association="EVENT_AND_BRANCH"))
        out = run(obj)
        self.assertEqual(out["disposition"], "PASS_PROCESS")
        self.assertEqual(out["pr_link_basis"], "EVENT_AND_BRANCH_ONLY")

    def test_event_and_branch_mode_still_requires_pull_request_event(self):
        obj = mutate(check=self.check(pull_requests=[], association="EVENT_AND_BRANCH",
                                      event="push"))
        out = run(obj)
        self.assertIn("CHECK_NOT_FROM_PULL_REQUEST_EVENT", findings(out))

    def test_unknown_association_mode_is_rejected(self):
        out = run(mutate(check=self.check(association="TRUST_ME")))
        self.assertIn("INVALID_PR_ASSOCIATION_MODE", findings(out))

    def test_push_event_check_does_not_prove_pr_ci(self):
        out = run(mutate(check=self.check(event="push")))
        self.assertIn("CHECK_NOT_FROM_PULL_REQUEST_EVENT", findings(out))

    def test_workflow_source_identity_must_match(self):
        out = run(mutate(check=self.check(workflow_path=".github/workflows/attacker.yml")))
        self.assertIn("UNTRUSTED_CHECK_SOURCE", findings(out))

    def test_untrusted_app_identity_is_rejected(self):
        out = run(mutate(check=self.check(app_id=1)))
        self.assertIn("UNTRUSTED_CHECK_APP", findings(out))

    def test_stale_check_head_is_rejected(self):
        out = run(mutate(check=self.check(head_sha=OTHER_HEAD)))
        self.assertIn("STALE_CHECK_HEAD", findings(out))

    def test_incomplete_capture_is_rejected(self):
        checks = copy.deepcopy(case()["checks"])
        checks["total_count"] = 2
        out = run(mutate(checks=checks))
        self.assertIn("INCOMPLETE_CHECK_CAPTURE", findings(out))

    def test_missing_required_check_is_rejected(self):
        out = run(mutate(required={"check_name": "review-evidence-gate"}))
        self.assertIn("MISSING_REQUIRED_CHECK", findings(out))

    def test_duplicate_green_checks_with_same_name_are_ambiguous(self):
        second = self.check(id=78, run_id=78)
        checks = copy.deepcopy(case()["checks"])
        checks["check_runs"].append(second)
        checks["total_count"] = 2
        out = run(mutate(checks=checks))
        self.assertIn("AMBIGUOUS_REQUIRED_CHECK", findings(out))

    def test_real_merge_regression_workflow_modification_is_flagged(self):
        files = case()["pr"]["changed_files"] + [WORKFLOW]
        out = run(mutate(files=files))
        self.assertIn("WORKFLOW_SELF_MODIFIED", findings(out))
        self.assertIn(WORKFLOW, out["protected_paths"])


class ProtectedPolicyTests(unittest.TestCase):
    def test_nested_agents_file_is_protected(self):
        files = case()["pr"]["changed_files"] + ["implementation/AGENTS.md"]
        out = run(mutate(files=files))
        self.assertIn("PROTECTED_POLICY_CHANGE", findings(out))
        self.assertIn("implementation/AGENTS.md", out["protected_paths"])

    def test_root_agents_and_governance_files_are_protected(self):
        for path in ("AGENTS.md", "GOVERNANCE.md", "REVIEWER_INSTRUCTIONS.md",
                     ".github/CODEOWNERS", "GOVERNANCE/OWNER_DELEGATION_2026-11-25.md"):
            with self.subTest(path=path):
                out = run(mutate(files=case()["pr"]["changed_files"] + [path]))
                self.assertIn(path, out["protected_paths"])
                self.assertIn("PROTECTED_POLICY_CHANGE", findings(out))

    def test_policy_and_contract_documents_are_protected(self):
        for path in ("implementation/ADMISSION_REVIEW_POLICY_V0_1.md",
                     "implementation/REVIEWER_AUTHORIZATION_CONTRACT_V0_1.md",
                     "docs/REVIEW_AND_MERGE_POLICY_V1.md"):
            with self.subTest(path=path):
                out = run(mutate(files=case()["pr"]["changed_files"] + [path]))
                self.assertIn(path, out["protected_paths"])

    def test_caller_supplied_protected_prefix_is_honoured(self):
        out = mutate(files=case()["pr"]["changed_files"] + ["custom/owned-dir/file.txt"])
        out["protected_paths_extra"] = ["custom/owned-dir"]
        result = run(out)
        self.assertIn("custom/owned-dir/file.txt", result["protected_paths"])


class AppendOnlyEvidenceTests(unittest.TestCase):
    def test_log_truncation_is_rejected(self):
        out = run(mutate(log={"removed": ["- previous entry"]}))
        self.assertIn("EVIDENCE_LOG_NOT_APPEND_ONLY", findings(out))

    def test_log_deletion_is_rejected(self):
        out = run(mutate(log={"status": "deleted"}))
        self.assertIn("EVIDENCE_LOG_DELETED", findings(out))

    def test_empty_append_is_rejected(self):
        out = run(mutate(log={"added": []}))
        self.assertIn("EVIDENCE_LOG_EMPTY_APPEND", findings(out))

    def test_log_edit_must_appear_in_changed_files(self):
        out = run(mutate(files=["implementation/example.py"]))
        self.assertIn("EVIDENCE_LOG_EVIDENCE_MISMATCH", findings(out))

    def test_unchanged_log_listed_as_changed_is_inconsistent(self):
        out = run(mutate(log={"status": "unchanged"}))
        self.assertIn("EVIDENCE_LOG_EVIDENCE_MISMATCH", findings(out))


class MergeBindingTests(unittest.TestCase):
    def test_squash_merge_losing_reviewed_head_is_rejected(self):
        out = run(mutate(pr={"merge_method": "squash"},
                         merge={"method": "squash", "parents": [PARENT]}))
        self.assertIn("REVIEWED_HEAD_NOT_PRESERVED", findings(out))

    def test_rebase_merge_losing_reviewed_head_is_rejected(self):
        out = run(mutate(pr={"merge_method": "rebase"},
                         merge={"method": "rebase", "parents": [PARENT]}))
        self.assertIn("REVIEWED_HEAD_NOT_PRESERVED", findings(out))

    def test_two_parent_merge_preserving_reviewed_head_passes(self):
        self.assertEqual(run(case())["disposition"], "PASS_PROCESS")

    def test_bypass_actor_merge_is_rejected(self):
        bypass = [{"id": 104393545, "login": "SepehrGhanbari"}]
        out = run(mutate(bypass=bypass,
                         merge={"merged_by_login": "SepehrGhanbari",
                                "merged_by_id": 104393545}))
        self.assertIn("BYPASS_ACTOR_MERGE", findings(out))


class FailClosedInputTests(unittest.TestCase):
    def test_unknown_top_level_field_is_rejected(self):
        obj = case()
        obj["extra"] = True
        self.assertEqual(run(obj)["reason"], "INVALID_OR_INCOMPLETE_EVIDENCE")

    def test_missing_section_is_rejected(self):
        obj = case()
        del obj["checks"]
        self.assertEqual(run(obj)["reason"], "INVALID_OR_INCOMPLETE_EVIDENCE")

    def test_non_boolean_draft_is_rejected(self):
        out = run(mutate(pr={"draft": 1}))
        self.assertEqual(out["disposition"], "HOLD")

    def test_cli_never_returns_zero_even_for_process_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.json"
            path.write_text(json.dumps(case()), encoding="utf-8")
            self.assertEqual(guard.main([str(path)]), 1)

    def test_cli_unreadable_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"
            self.assertEqual(guard.main([str(path)]), 1)


if __name__ == "__main__":
    unittest.main()
