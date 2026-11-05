"""Offline deterministic unit tests for the repository-only evidence gate."""
import copy
import io
import json
import os
import sys
import unittest
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

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
        "number": 151,
        "state": "open",
        "draft": False,
        "base": {"ref": "main", "sha": "c" * 40,
                 "repo": {"id": 55, "full_name": "SepehrGhanbari/Ario"}},
        "head": {"sha": HEAD, "ref": "fix/issue129-test",
                 "repo": {"id": 55, "full_name": "SepehrGhanbari/Ario"}},
        "user": {"id": 1001, "login": "SepehrGhanbari", "type": "User"},
    }
    files = [{"filename": x, "status": "modified"} for x in record()["files"]]
    reviews = [{
        "id": 700,
        "user": {"id": 136622811, "login": "coderabbitai[bot]", "type": "Bot"},
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
    for run_id, run in runs.items():
        run.update({
            "id": run_id, "event": "pull_request", "status": "completed",
            "workflow_id": 77, "path": ".github/workflows/implementation-regression.yml",
            "repository": {"id": 55, "full_name": "SepehrGhanbari/Ario"},
            "run_attempt": 1,
            "pull_requests": [{
                "number": 151,
                "head": {"sha": run["head_sha"], "ref": pr["head"]["ref"],
                         "repo": copy.deepcopy(pr["head"]["repo"])},
                "base": copy.deepcopy(pr["base"]),
            }],
        })
        run["head_repository"]["id"] = 55
        outcome = run["conclusion"]
        run["jobs"] = [{
            "id": run_id + 10000, "name": "m0-regression", "status": "completed",
            "head_sha": run["head_sha"], "conclusion": outcome,
            "steps": [{"name": "Run M0 and runtime regression suites",
                       "status": "completed", "conclusion": outcome}],
        }]
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


class MutableEvidenceHarness:
    """Fake GitHub state; every read returns a detached API snapshot.

    Mutations occur between the first and later reads without changing SHAs.
    No network, token, temporary event file, or filesystem fixture is used.
    """

    def __init__(self):
        import review_evidence_gate as g
        self.g = g
        self.pr, self.record, self.files, self.reviews, self.threads, self.runs = candidate()
        self.pr["body"] = "<!-- ARIO_REVIEW_EVIDENCE_V1\n" + json.dumps(self.record) + "\n-->"
        self.comments = []
        self.later_pr = None
        self.later_reviews = None
        self.later_threads = None
        self.later_comments = None
        self.later_runs = {}
        self.workflow_by_sha = {}
        self.workflow_bytes = (Path(__file__).resolve().parents[1] / "workflows" /
                               "implementation-regression.yml").read_bytes()
        self.checkout_commits = {}
        self.job_logs = {}
        self.comparisons = {}
        for run_id, run in self.runs.items():
            checkout_sha = ("d" if run_id == 1201 else "e") * 40
            self.checkout_commits[checkout_sha] = {
                "sha": checkout_sha,
                "parents": [{"sha": self.pr["base"]["sha"]},
                            {"sha": run["head_sha"]}],
            }
            job = run["jobs"][0]
            job["run_id"] = run_id
            job["run_attempt"] = run["run_attempt"]
            summary = "1 failed" if run_id == 1201 else "12 passed"
            self.job_logs[job["id"]] = (
                "2026-11-05T12:00:00.0000000Z [command]/usr/bin/git log -1 --format=%H\n"
                "2026-11-05T12:00:00.0000000Z " + checkout_sha + "\n"
                "2026-11-05T12:00:01.0000000Z ##[group]Run python -m pytest -q tests\n"
                "2026-11-05T12:00:01.0000000Z python -m pytest -q tests\n"
                "2026-11-05T12:00:02.0000000Z " + summary + " in 1.0s\n"
            )
        self.reads = {}
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()

    def snapshot(self, label, first, later=None):
        self.reads[label] = self.reads.get(label, 0) + 1
        return copy.deepcopy(first if self.reads[label] == 1 or later is None else later)

    def api(self, path, **kwargs):
        base = "/repos/SepehrGhanbari/Ario"
        if path == base + "/pulls/151":
            return self.snapshot("pr", self.pr, self.later_pr)
        if path == base + "/pulls/151/files?per_page=100":
            return copy.deepcopy(self.files)
        if path == base + "/pulls/151/reviews?per_page=100":
            return self.snapshot("reviews", self.reviews, self.later_reviews)
        if path == base + "/pulls/151/comments?per_page=100":
            return self.snapshot("comments", self.comments, self.later_comments)
        if path == base + "/actions/workflows/implementation-regression.yml":
            return {"id": 77, "path": ".github/workflows/implementation-regression.yml"}
        if path.startswith(base + "/compare/"):
            left, right = path.split("/compare/")[1].split("...")
            return copy.deepcopy(self.comparisons.get((left, right), {
                "status": "identical" if left == right else "ahead",
                "merge_base_commit": {"sha": left},
            }))
        if path.startswith(base + "/git/commits/"):
            return copy.deepcopy(self.checkout_commits[path.rsplit("/", 1)[1]])
        if path.startswith(base + "/actions/jobs/") and path.endswith("/logs"):
            job_id = int(path.split("/actions/jobs/")[1].split("/")[0])
            if job_id not in self.job_logs:
                raise self.g.GateError("GITHUB_API_UNAVAILABLE_OR_INVALID_RESPONSE")
            return self.job_logs[job_id]
        if path.startswith(base + "/actions/runs/"):
            run_id = int(path.split("/actions/runs/")[1].split("/")[0])
            run = self.runs[run_id]
            if "/jobs?" in path or "/jobs?" in path.replace("/attempts/1", ""):
                return {"total_count": len(run["jobs"]), "jobs": copy.deepcopy(run["jobs"])}
            return self.snapshot("run:" + str(run_id), run, self.later_runs.get(run_id))
        if "/contents/.github/workflows/implementation-regression.yml?ref=" in path:
            import base64
            import hashlib
            sha = path.split("?ref=", 1)[1]
            payload = self.workflow_by_sha.get(sha, self.workflow_bytes)
            digest = hashlib.sha1(b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()
            return {"type": "file", "encoding": "base64", "size": len(payload),
                    "sha": digest, "content": base64.b64encode(payload).decode("ascii"),
                    "path": ".github/workflows/implementation-regression.yml"}
        raise AssertionError("Unexpected API request: " + path)

    def run(self, action="edited"):
        g = self.g
        event = {"action": action, "pull_request": {"number": 151}}
        with patch.dict(os.environ, {
                "GITHUB_REPOSITORY": "SepehrGhanbari/Ario", "GITHUB_EVENT_PATH": "in-memory-event",
                "GITHUB_EVENT_NAME": "pull_request_review_comment"}), \
                patch("builtins.open", return_value=io.StringIO(json.dumps(event))), \
                patch.object(g, "api_request", side_effect=self.api), \
                patch.object(g, "graphql_threads", side_effect=lambda *args: self.snapshot(
                    "threads", self.threads, self.later_threads)), \
                patch.object(g, "fetch_log_bytes", side_effect=[b"history\n", b"history\nnew\n"]), \
                patch.object(g, "regular_modes_at_commit", return_value={
                    f["filename"]: "100644" for f in self.files}), \
                redirect_stdout(self.stdout), redirect_stderr(self.stderr):
            return g.main()


def inline_comment(**overrides):
    value = {
        "id": 900, "pull_request_review_id": 700,
        "body": "A nonblocking clarification from the independent reviewer.",
        "commit_id": HEAD, "original_commit_id": HEAD,
        "user": {"id": 136622811, "login": "coderabbitai[bot]", "type": "Bot"},
        "created_at": "2026-11-03T14:00:00Z", "updated_at": "2026-11-03T14:00:00Z",
        "path": "implementation/witness_provenance_experiment.py",
    }
    value.update(overrides)
    return value


class GateMutableEvidenceTests(unittest.TestCase):
    def assert_hold(self, harness, action="edited"):
        self.assertEqual(harness.run(action), 1, harness.stdout.getvalue())
        self.assertIn("GATE_RESULT=HOLD", harness.stderr.getvalue())
        self.assertNotIn("GATE_RESULT=PASS", harness.stdout.getvalue())

    def test_unchanged_api_snapshots_pass_process_check(self):
        h = MutableEvidenceHarness()
        self.assertEqual(h.run(), 0, h.stderr.getvalue())
        self.assertIn("GATE_RESULT=PASS_PROCESS_EVIDENCE_ONLY_NO_MERGE_AUTHORITY", h.stdout.getvalue())

    def test_same_sha_pr_body_removed_at_boundary_blocks(self):
        h = MutableEvidenceHarness()
        h.later_pr = copy.deepcopy(h.pr)
        h.later_pr["body"] = "The machine-readable evidence was removed."
        self.assert_hold(h)

    def test_same_sha_review_body_edited_to_major_at_boundary_blocks(self):
        h = MutableEvidenceHarness()
        h.later_reviews = copy.deepcopy(h.reviews)
        h.later_reviews[0]["body"] = "**Major** Newly reported reproducible blocker."
        self.assert_hold(h)

    def test_inline_comment_creation_invalidates_same_sha_snapshot(self):
        h = MutableEvidenceHarness()
        h.later_comments = [inline_comment(body="**Major** A newly created blocker.")]
        self.assert_hold(h, "created")

    def test_inline_comment_body_edit_invalidates_same_sha_snapshot(self):
        h = MutableEvidenceHarness()
        h.comments = [inline_comment()]
        h.later_comments = [inline_comment(body="**Major** Edited to report a blocker.")]
        self.assert_hold(h)

    def test_inline_comment_deletion_invalidates_same_sha_snapshot(self):
        h = MutableEvidenceHarness()
        h.comments = [inline_comment()]
        h.later_comments = []
        self.assert_hold(h, "deleted")

    def test_new_unresolved_thread_at_boundary_blocks(self):
        h = MutableEvidenceHarness()
        h.later_threads = [{"id": "thread-1", "isResolved": False}]
        self.assert_hold(h, "created")

    def test_reopened_thread_at_boundary_blocks(self):
        h = MutableEvidenceHarness()
        h.threads = [{"id": "thread-1", "isResolved": True}]
        h.later_threads = [{"id": "thread-1", "isResolved": False}]
        self.assert_hold(h)

    def test_resolved_outdated_thread_is_not_automatically_a_blocker(self):
        case = candidate()
        case[4] = [{"id": "thread-1", "isResolved": True, "isOutdated": True}]
        self.assertTrue(validate_candidate(*case))

    def test_initial_inline_major_is_not_hidden_by_clean_review_body(self):
        h = MutableEvidenceHarness()
        h.comments = [inline_comment(body="**Major** A reproducible inline blocker remains.")]
        self.assert_hold(h)

    def test_inline_comment_missing_commit_identity_fails_closed(self):
        h = MutableEvidenceHarness()
        comment = inline_comment()
        comment.pop("commit_id")
        h.comments = [comment]
        self.assert_hold(h)

    def test_picture_wrapped_major_review_label_blocks(self):
        h = MutableEvidenceHarness()
        # CodeRabbit can place severity artwork between ** and the label.
        # alt="major" would already match the old regex and is not a RED.
        h.reviews[0]["body"] = (
            '**<picture><source media="(prefers-color-scheme: dark)" srcset="major-dark.svg">'
            '<img src="major-light.svg" alt=""></picture> Major** A reproducible blocker.'
        )
        self.assert_hold(h)

    def test_workflow_rechecks_inline_comment_created_edited_deleted(self):
        import re
        workflow = (Path(__file__).resolve().parents[1] / "workflows" /
                    "review-evidence-gate.yml").read_text(encoding="utf-8")
        trigger = re.search(r"(?m)^  pull_request_review_comment:\s*\n    types: \[([^]]+)\]", workflow)
        self.assertIsNotNone(trigger, "Inline comment changes must trigger a fresh process check")
        self.assertEqual({part.strip() for part in trigger.group(1).split(",")},
                         {"created", "edited", "deleted"})


class GateRunProvenanceTests(unittest.TestCase):
    """Collector controls for authentic PR/attempt/source/test evidence."""

    def assert_hold(self, harness):
        self.assertEqual(harness.run(), 1, harness.stdout.getvalue())
        self.assertIn("GATE_RESULT=HOLD", harness.stderr.getvalue())
        self.assertNotIn("GATE_RESULT=PASS", harness.stdout.getvalue())

    def test_unassociated_push_run_is_not_pr_regression_evidence(self):
        h = MutableEvidenceHarness()
        h.runs[1201]["event"] = "push"
        h.runs[1201]["pull_requests"] = []
        self.assert_hold(h)

    def test_green_non_pr_event_is_rejected_even_with_claimed_association(self):
        h = MutableEvidenceHarness()
        h.runs[1202]["event"] = "push"
        self.assert_hold(h)

    def test_red_without_pr_association_is_rejected(self):
        h = MutableEvidenceHarness()
        h.runs[1201]["pull_requests"] = []
        self.assert_hold(h)

    def test_green_run_for_other_pr_at_same_sha_is_rejected(self):
        h = MutableEvidenceHarness()
        h.runs[1202]["pull_requests"][0]["number"] = 999
        self.assert_hold(h)

    def test_red_run_association_to_wrong_head_repository_is_rejected(self):
        h = MutableEvidenceHarness()
        h.runs[1201]["pull_requests"][0]["head"]["repo"]["id"] = 999
        self.assert_hold(h)

    def test_green_run_association_to_wrong_base_branch_is_rejected(self):
        h = MutableEvidenceHarness()
        h.runs[1202]["pull_requests"][0]["base"]["ref"] = "other-target"
        self.assert_hold(h)

    def test_red_association_live_head_sha_need_not_equal_historical_red(self):
        h = MutableEvidenceHarness()
        # GitHub's run association can report the live PR HEAD after a push.
        h.runs[1201]["pull_requests"][0]["head"]["sha"] = HEAD
        self.assertEqual(h.run(), 0, h.stderr.getvalue())

    def test_red_workflow_temporarily_changed_then_reverted_is_rejected(self):
        h = MutableEvidenceHarness()
        changed = h.workflow_bytes.replace(b"python -m pytest -q tests", b"exit 1")
        self.assertNotEqual(changed, h.workflow_bytes)
        h.workflow_by_sha["b" * 40] = changed
        self.assert_hold(h)

    def test_checkout_merge_workflow_must_match_trusted_source(self):
        h = MutableEvidenceHarness()
        h.workflow_by_sha["e" * 40] = h.workflow_bytes.replace(
            b"python -m pytest -q tests", b"echo fake-green")
        self.assert_hold(h)

    def test_missing_job_logs_are_not_verified_test_execution(self):
        h = MutableEvidenceHarness()
        h.job_logs.pop(11201)
        self.assert_hold(h)

    def test_named_failed_step_without_pytest_command_is_not_red(self):
        h = MutableEvidenceHarness()
        h.job_logs[11201] = h.job_logs[11201].replace(
            "python -m pytest -q tests", "exit 1")
        self.assert_hold(h)

    def test_named_successful_step_without_pytest_command_is_not_green(self):
        h = MutableEvidenceHarness()
        h.job_logs[11202] = h.job_logs[11202].replace(
            "python -m pytest -q tests", "echo fake-green")
        self.assert_hold(h)

    def test_no_tests_collected_is_not_red_regression(self):
        h = MutableEvidenceHarness()
        h.job_logs[11201] = h.job_logs[11201].replace("1 failed in 1.0s", "no tests ran in 1.0s")
        self.assert_hold(h)

    def test_collection_error_without_failed_test_is_not_red_regression(self):
        h = MutableEvidenceHarness()
        h.job_logs[11201] = h.job_logs[11201].replace("1 failed in 1.0s", "1 error in 1.0s")
        self.assert_hold(h)

    def test_green_without_executed_test_summary_fails_closed(self):
        h = MutableEvidenceHarness()
        h.job_logs[11202] = h.job_logs[11202].replace("12 passed in 1.0s", "output was truncated")
        self.assert_hold(h)

    def test_checkout_commit_must_contain_claimed_run_head(self):
        h = MutableEvidenceHarness()
        h.checkout_commits["d" * 40]["parents"][1]["sha"] = "f" * 40
        self.assert_hold(h)

    def test_checkout_base_must_be_current_base_or_verified_ancestor(self):
        h = MutableEvidenceHarness()
        h.checkout_commits["d" * 40]["parents"][0]["sha"] = "f" * 40
        h.comparisons[("f" * 40, "c" * 40)] = {
            "status": "diverged", "merge_base_commit": {"sha": "9" * 40}}
        self.assert_hold(h)

    def test_run_rerun_during_audit_invalidates_attempt_evidence(self):
        h = MutableEvidenceHarness()
        h.later_runs[1202] = copy.deepcopy(h.runs[1202])
        h.later_runs[1202]["run_attempt"] = 2
        self.assert_hold(h)

    def test_skipped_regression_step_still_fails_closed(self):
        h = MutableEvidenceHarness()
        h.runs[1201]["jobs"][0]["steps"][0]["conclusion"] = "skipped"
        self.assert_hold(h)


class GateReviewIdentityShapeTests(unittest.TestCase):
    """API identity tuple checks; these fixtures do not forge GitHub identities."""

    def assert_no_fresh_review(self, case):
        with self.assertRaisesRegex(GateError, "NO_FRESH_INDEPENDENT"):
            validate_candidate(*case)

    def test_bot_login_alone_without_immutable_id_is_not_authenticated(self):
        case = candidate()
        case[3][0]["user"].pop("id")
        self.assert_no_fresh_review(case)

    def test_bot_login_with_different_immutable_id_is_rejected(self):
        case = candidate()
        case[3][0]["user"]["id"] = 1002
        self.assert_no_fresh_review(case)

    def test_bot_id_and_login_with_user_account_type_are_rejected(self):
        case = candidate()
        case[3][0]["user"]["type"] = "User"
        self.assert_no_fresh_review(case)

    def test_bot_id_alone_with_other_login_is_not_authenticated(self):
        case = candidate()
        case[3][0]["user"]["login"] = "some-other-account"
        self.assert_no_fresh_review(case)

    def test_review_same_immutable_id_as_author_is_not_independent(self):
        case = candidate()
        case[0]["user"]["id"] = case[3][0]["user"]["id"]
        self.assert_no_fresh_review(case)

    def test_verified_bot_id_login_and_type_tuple_passes_fixture(self):
        self.assertTrue(validate_candidate(*candidate()))


class GateExecutionBoundaryTests(unittest.TestCase):
    def test_green_checkout_on_older_base_is_not_current_base_evidence(self):
        h = MutableEvidenceHarness()
        h.checkout_commits["e" * 40]["parents"][0]["sha"] = "f" * 40
        self.assertEqual(h.run(), 1, h.stdout.getvalue())
        self.assertIn("GATE_RESULT=HOLD", h.stderr.getvalue())

    def test_raw_log_redirect_does_not_forward_github_bearer(self):
        import review_evidence_gate as g
        from urllib.request import HTTPRedirectHandler

        def download(request, **kwargs):
            self.assertEqual(request.get_header("Authorization"), "Bearer fixture-token")
            redirected = HTTPRedirectHandler().redirect_request(
                request, None, 302, "Found", {}, "https://logs.example.invalid/signed")
            self.assertIsNone(redirected.get_header("Authorization"))
            return io.BytesIO(b"downloaded job log")

        with patch.dict(os.environ, {"GITHUB_TOKEN": "fixture-token"}), \
                patch.object(g, "urlopen", side_effect=download):
            self.assertEqual(g.api_request("/repos/example/repo/actions/jobs/1/logs", raw=True),
                             "downloaded job log")

    def test_crlf_job_logs_preserve_real_execution_control(self):
        h = MutableEvidenceHarness()
        h.job_logs = {job: text.replace("\n", "\r\n") for job, text in h.job_logs.items()}
        self.assertEqual(h.run(), 0, h.stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
