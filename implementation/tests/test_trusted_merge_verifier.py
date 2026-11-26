"""Adversarial regressions for the separated-role trusted merge verifier.

Each test builds a *disposable synthetic Git repository* (the untrusted
candidate) plus a *separately pinned verifier copy* (the trusted side). The
candidate may edit its own checker, policy, workflow, log and claim JSON; the
pinned verifier must reject the claim anyway.

Run from ``implementation``::

    python -m pytest -q tests/test_trusted_merge_verifier.py
    python -m unittest tests.test_trusted_merge_verifier

No network, credential, GitHub API, ruleset, merge or trust activation is used.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from research.trusted_merge_verifier import verifier as module
from research.trusted_merge_verifier.git_objects import GitRepo
from research.trusted_merge_verifier.pin import build as build_trust_root
from research.trusted_merge_verifier.verifier import assess

PACKAGE = Path(__file__).resolve().parents[1] / "research" / "trusted_merge_verifier"
REPO_ID = 990001
REPO_NAME = "synthetic/ario-candidate"
PR_ID = 2400000001
PR_NUMBER = 401
WORKFLOW = ".github/workflows/implementation-regression.yml"
WORKFLOW_ID = 379498305
APP_ID = 15368
CHECK_NAME = "m0-regression"
BYPASS_ACTOR = 104393545
AUTHOR_ID, AUTHOR_LOGIN = 111, "agent-author"
LOG_PATH = "ENGINEERING_LOG.md"
BASE_LOG = b"# Engineering log\n\n- earlier entry\n"
APPENDED_LOG = b"- candidate entry\n"
BASE_FILES = {
    "impl/example.py": b"value = 1\n",
    WORKFLOW: b"name: regression\non: pull_request\n",
    "GOVERNANCE.md": b"# Governance\n",
}


class Lab:
    """A disposable synthetic candidate repository and a pinned verifier copy."""

    def __init__(self, test: unittest.TestCase, *, required_approvals: int = 2,
                 base_files: dict | None = None, head_files: dict | None = None,
                 head_moves: list[tuple[str, str]] | None = None,
                 append_log: bool = True, base_log: bytes = BASE_LOG,
                 checkout_main: bool = True) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="ario-trust-lab-"))
        test.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

        self.verifier = self.root / "verifier"
        self.verifier.mkdir()
        for source in PACKAGE.iterdir():
            if source.is_file() and (source.suffix == ".py" or source.name == "policy.json"):
                shutil.copyfile(source, self.verifier / source.name)
        if required_approvals != 2:
            policy_path = self.verifier / "policy.json"
            policy = json.loads(policy_path.read_text("utf-8"))
            policy["required_approvals"] = required_approvals
            policy_path.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", "utf-8")

        self.candidate = self.root / "candidate"
        self.candidate.mkdir()
        self._git("init", "-q", "--initial-branch=main")
        self._git("config", "user.name", "Synthetic Author")
        self._git("config", "user.email", "synthetic@example.invalid")
        self._git("config", "commit.gpgsign", "false")

        self.base_log = base_log
        files = dict(BASE_FILES)
        files.update(base_files or {})
        for path, data in files.items():
            self.write_file(path, data)
        self.write_file(LOG_PATH, base_log)
        self.base_sha = self.commit("base evidence")

        self._git("checkout", "-q", "-b", "research/example")
        self.write_file("impl/example.py", b"value = 2\n")
        self.write_file("impl/extra.py", b"new = True\n")
        for path, data in (head_files or {}).items():
            self.write_file(path, data)
        for old, new in (head_moves or []):
            (self.candidate / new).parent.mkdir(parents=True, exist_ok=True)
            self._git("mv", old, new)
        if append_log and (head_files is None or LOG_PATH not in head_files):
            self.write_file(LOG_PATH, base_log + APPENDED_LOG)
        self.head_sha = self.commit("candidate research change")
        self.head_tree = self.rev(f"{self.head_sha}^{{tree}}")
        self.base_tree = self.rev(f"{self.base_sha}^{{tree}}")
        if checkout_main:
            self._git("checkout", "-q", "main")
        self.merge_sha: str | None = None
        self.trust = self.pin()

    # -- git plumbing -----------------------------------------------------
    def _git(self, *args: str) -> bytes:
        result = subprocess.run(
            ["git", "-C", str(self.candidate), *args],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=clean_env(), timeout=60,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"git {' '.join(args)} failed: {result.stderr.decode('utf-8', 'replace')}"
            )
        return result.stdout

    def write_file(self, path: str, data: bytes | None) -> None:
        target = self.candidate / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if data is None:
            if target.exists():
                target.unlink()
            return
        target.write_bytes(data)

    def commit(self, message: str) -> str:
        self._git("add", "-A")
        self._git("commit", "-q", "-m", message)
        return self.rev("HEAD")

    def rev(self, expression: str) -> str:
        return self._git("rev-parse", expression).decode("ascii").strip()

    def blob(self, path: str, commit: str | None = None) -> str | None:
        return GitRepo(self.candidate).blob_id(commit or self.head_sha, path)

    def read(self, path: str, commit: str | None = None) -> bytes | None:
        blob = self.blob(path, commit)
        return None if blob is None else GitRepo(self.candidate).blob_bytes(blob)

    def rewrite_head(self, files: dict, moves: list[tuple[str, str]] | None = None,
                     message: str = "candidate rewrites head") -> str:
        self._git("checkout", "-q", "research/example")
        for path, data in files.items():
            self.write_file(path, data)
        for old, new in (moves or []):
            (self.candidate / new).parent.mkdir(parents=True, exist_ok=True)
            self._git("mv", old, new)
        self._git("add", "-A")
        self._git("commit", "-q", "-m", message)
        self.head_sha = self.rev("HEAD")
        self.head_tree = self.rev(f"{self.head_sha}^{{tree}}")
        self._git("checkout", "-q", "main")
        return self.head_sha

    def merge(self, *, squash: bool = False, reverse: bool = False) -> str:
        self._git("checkout", "-q", "main")
        if squash:
            self._git("merge", "--squash", "-q", "research/example")
            self.merge_sha = self.commit("squash candidate research change")
            return self.merge_sha
        if reverse:
            tree = self.rev(f"{self.head_sha}^{{tree}}")
            sha = self._git(
                "commit-tree", tree, "-p", self.head_sha, "-p", self.base_sha,
                "-m", "reversed parent merge",
            ).decode("ascii").strip()
            self._git("update-ref", "refs/heads/main", sha)
            self.merge_sha = sha
            return sha
        self._git("merge", "--no-ff", "-q", "-m", "merge research/example", "research/example")
        self.merge_sha = self.rev("HEAD")
        return self.merge_sha

    def orphan(self) -> str:
        return self._git("commit-tree", self.base_tree, "-m", "unrelated root").decode("ascii").strip()

    # -- pinned trust -----------------------------------------------------
    def pin(self, name: str = "trust_root.json") -> Path:
        path = self.root / name
        path.write_text(
            json.dumps(build_trust_root(self.verifier, "2026-11-25T12:00:00Z"),
                       indent=2, sort_keys=True) + "\n",
            "utf-8",
        )
        return path

    # -- claim helpers ----------------------------------------------------
    def review(self, review_id: int, author_id: int, login: str, *,
               state: str = "APPROVED", head: str | None = None,
               dismissed: bool = False) -> dict:
        return {
            "id": review_id, "author_id": author_id, "author_login": login,
            "state": state,
            "commit_id": self.head_sha if head is None else head,
            "dismissed": dismissed,
        }

    def diff_files(self, base: str | None = None, head: str | None = None) -> list[dict]:
        entries = GitRepo(self.candidate).diff(base or self.base_sha, head or self.head_sha)
        out = []
        for entry in entries:
            out.append({
                "status": entry.status,
                "path": entry.path,
                "old_path": entry.old_path if entry.status == "R" else None,
                "old_blob": entry.old_blob,
                "new_blob": entry.new_blob,
            })
        return out

    def claim(self, *, mode: str = "PRE_MERGE", repository: dict | None = None,
              pr: dict | None = None, reviews: list[dict] | None = None,
              ci: dict | None = None, merge: dict | None = None,
              files: list[dict] | None = None, log: dict | None = None,
              tree: str | None = None) -> dict:
        head, base = self.head_sha, self.base_sha
        workflow_blob = self.blob(WORKFLOW) or "0" * 40
        claim = {
            "schema": "ARIO-MERGE-CLAIM-0.1",
            "repository": {"id": REPO_ID, "full_name": REPO_NAME},
            "pr": {
                "id": PR_ID, "number": PR_NUMBER, "state": "open", "draft": False,
                "author_id": AUTHOR_ID, "author_login": AUTHOR_LOGIN,
                "head_ref": "research/example", "base_ref": "main",
                "head_sha": head, "base_sha": base, "merge_method": "merge",
            },
            "reviews": [
                self.review(9001, 222, "reviewer-y"),
                self.review(9002, 333, "reviewer-z"),
            ] if reviews is None else reviews,
            "ci": {
                "repository_id": REPO_ID, "run_id": 5550001, "run_attempt": 1,
                "event": "pull_request", "status": "completed", "conclusion": "success",
                "head_sha": head, "head_branch": "research/example",
                "workflow_id": WORKFLOW_ID, "workflow_path": WORKFLOW,
                "workflow_source_sha": workflow_blob,
                "check_name": CHECK_NAME, "app_id": APP_ID,
                "pr_association": {
                    "method": "explicit_link", "pr_id": PR_ID, "pr_number": PR_NUMBER,
                },
            },
            "mode": mode,
            "merge": {
                "commit_sha": None, "method": "merge", "merged_by_id": 999,
                "merged_by_login": "maintainer", "parents": [],
            },
            "files": self.diff_files() if files is None else files,
            "log": self.log_declaration() if log is None else log,
            "tree": self.head_tree if tree is None else tree,
        }
        if mode == "POST_MERGE":
            claim["pr"]["state"] = "closed"
            claim["merge"] = {
                "commit_sha": self.merge_sha, "method": "merge", "merged_by_id": 999,
                "merged_by_login": "maintainer",
                "parents": [base, head] if self.merge_sha else [],
            }
        for section, override in (("repository", repository), ("pr", pr), ("ci", ci),
                                  ("merge", merge)):
            if override:
                claim[section].update(override)
        return claim

    def log_declaration(self) -> dict:
        head_log = self.read(LOG_PATH)
        base_log = self.read(LOG_PATH, self.base_sha)
        if head_log is not None and base_log is not None and head_log.startswith(base_log):
            delta = head_log[len(base_log):]
        else:
            delta = None
        changed = bool(delta)
        return {
            "path": LOG_PATH, "changed": changed,
            "added_sha256": hashlib.sha256(delta).hexdigest() if changed else None,
            "added_bytes": len(delta) if changed else 0,
        }

    def assess(self, claim, **kwargs):
        return assess(self.candidate, claim, trust_root_path=self.trust,
                      verifier_dir=self.verifier, **kwargs)


def clean_env() -> dict:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "Synthetic Author",
        "GIT_AUTHOR_EMAIL": "synthetic@example.invalid",
        "GIT_COMMITTER_NAME": "Synthetic Author",
        "GIT_COMMITTER_EMAIL": "synthetic@example.invalid",
        "GIT_AUTHOR_DATE": "2026-11-25T00:00:00+0000",
        "GIT_COMMITTER_DATE": "2026-11-25T00:00:00+0000",
        "GIT_TERMINAL_PROMPT": "0",
        "LC_ALL": "C",
    })
    return env


@contextlib.contextmanager
def guard_removed(*names: str):
    saved = list(module.GUARDS)
    module.GUARDS[:] = [item for item in saved if item[0] not in names]
    try:
        yield
    finally:
        module.GUARDS[:] = saved


class TrustTestCase(unittest.TestCase):
    def assertFinding(self, result: dict, code: str) -> None:
        self.assertEqual(result["disposition"], "HOLD", result.get("findings"))
        self.assertIn(code, result["findings"])

    def assertNoAuthority(self, result: dict) -> None:
        self.assertIs(result["merge_authorized"], False)
        self.assertIs(result["trust_activated"], False)
        self.assertEqual(result["authority"], "NON_AUTHORITATIVE_RESEARCH_ONLY")
        self.assertEqual(result["scope"], "SYNTHETIC_TWO_ROLE_LAB_ONLY")


class BaselineTests(TrustTestCase):
    def test_pre_merge_consistent_evidence_is_process_pass(self):
        lab = Lab(self)
        result = lab.assess(lab.claim())
        self.assertEqual(result["disposition"], "PASS_PROCESS", result["findings"])
        self.assertEqual(result["findings"], [])
        self.assertNoAuthority(result)
        self.assertEqual(result["assessment_mode"], "PRE_MERGE")
        self.assertEqual(result["evidence"]["head_sha"], lab.head_sha)
        self.assertEqual(result["evidence"]["base_sha"], lab.base_sha)
        self.assertEqual(result["evidence"]["head_tree"], lab.head_tree)
        self.assertEqual(result["evidence"]["log_appended_sha256"],
                         hashlib.sha256(APPENDED_LOG).hexdigest())
        self.assertEqual(result["evidence"]["reviewer_ids"], [222, 333])
        self.assertEqual(result["evidence"]["merge_method"], "merge")

    def test_post_merge_consistent_evidence_is_audit_pass(self):
        lab = Lab(self)
        lab.merge()
        result = lab.assess(lab.claim(mode="POST_MERGE"))
        self.assertEqual(result["disposition"], "PASS_PROCESS", result["findings"])
        self.assertEqual(result["assessment_mode"], "POST_MERGE")
        self.assertNoAuthority(result)

    def test_pre_merge_and_post_merge_are_distinct_assessments(self):
        lab = Lab(self)
        lab.merge()
        # The merge commit exists, but a PRE_MERGE claim may not carry it.
        self.assertFinding(lab.assess(lab.claim()), "BASE_REF_SHA_MISMATCH")

    def test_cli_always_exits_nonzero_even_on_process_pass(self):
        lab = Lab(self)
        claim_path = lab.root / "claim.json"
        claim_path.write_text(json.dumps(lab.claim()), "utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "research.trusted_merge_verifier.cli",
             "--candidate", str(lab.candidate), "--claim", str(claim_path),
             "--trust-root", str(lab.trust), "--verifier-dir", str(lab.verifier)],
            cwd=str(PACKAGE.parents[1]), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=120,
        )
        self.assertEqual(result.returncode, 1, result.stderr.decode("utf-8", "replace"))
        payload = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(payload["disposition"], "PASS_PROCESS", payload["findings"])
        self.assertIs(payload["merge_authorized"], False)


class TrustBoundaryTests(TrustTestCase):
    def test_changed_verifier_bytes_are_rejected(self):
        lab = Lab(self)
        with open(lab.verifier / "verifier.py", "ab") as handle:
            handle.write(b"\n# candidate-side edit\n")
        result = lab.assess(lab.claim())
        self.assertFinding(result, "TRUST_BOUNDARY_INVALID")

    def test_changed_policy_bytes_are_rejected(self):
        lab = Lab(self)
        policy_path = lab.verifier / "policy.json"
        policy = json.loads(policy_path.read_text("utf-8"))
        policy["required_approvals"] = 0
        policy_path.write_text(json.dumps(policy), "utf-8")
        result = lab.assess(lab.claim())
        self.assertFinding(result, "TRUST_BOUNDARY_INVALID")

    def test_extra_verifier_source_breaks_pinned_file_set(self):
        lab = Lab(self)
        (lab.verifier / "override.py").write_text("MERGE = True\n", "utf-8")
        result = lab.assess(lab.claim())
        self.assertFinding(result, "TRUST_BOUNDARY_INVALID")

    def test_trust_root_inside_candidate_is_rejected(self):
        lab = Lab(self)
        inside = lab.candidate / "trust_root.json"
        shutil.copyfile(lab.trust, inside)
        result = assess(lab.candidate, lab.claim(), trust_root_path=inside,
                        verifier_dir=lab.verifier)
        self.assertFinding(result, "TRUST_ROOT_INSIDE_CANDIDATE")

    def test_verifier_directory_inside_candidate_is_rejected(self):
        lab = Lab(self)
        inside = lab.candidate / "verifier"
        inside.mkdir()
        shutil.copyfile(lab.verifier / "policy.json", inside / "policy.json")
        result = assess(lab.candidate, lab.claim(), trust_root_path=lab.trust,
                        verifier_dir=inside)
        self.assertFinding(result, "VERIFIER_INSIDE_CANDIDATE")

    def test_missing_trust_root_holds(self):
        lab = Lab(self)
        result = assess(lab.candidate, lab.claim(),
                        trust_root_path=lab.root / "absent.json",
                        verifier_dir=lab.verifier)
        self.assertFinding(result, "TRUST_BOUNDARY_INVALID")


class CandidateSelfModificationTests(TrustTestCase):
    def test_candidate_policy_copy_cannot_lower_requirements(self):
        lab = Lab(self)
        forged = json.loads((PACKAGE / "policy.json").read_text("utf-8"))
        forged["required_approvals"] = 0
        forged["require_explicit_pr_association"] = False
        lab.rewrite_head({
            "implementation/research/trusted_merge_verifier/policy.json":
                (json.dumps(forged, indent=2) + "\n").encode("utf-8"),
            "implementation/research/trusted_merge_verifier/verifier.py":
                b"def assess(*args, **kwargs):\n    return {'disposition': 'PASS'}\n",
            "implementation/trust_root.json": b'{"schema": "candidate-owned"}\n',
        })
        result = lab.assess(lab.claim(reviews=[]))
        self.assertFinding(result, "INSUFFICIENT_APPROVALS")
        self.assertEqual(result["evidence"]["policy_sha256"],
                         hashlib.sha256((lab.verifier / "policy.json").read_bytes()).hexdigest())

    def test_candidate_supplied_trust_root_is_ignored(self):
        lab = Lab(self)
        forged = {
            "schema": "ARIO-TRUST-ROOT-RESEARCH-0.1",
            "policy_file": "policy.json",
            "policy_sha256": "0" * 64,
            "verifier_sha256": {"verifier.py": "0" * 64},
            "pinned_at": "2026-11-25T12:00:00Z",
        }
        lab.rewrite_head({"implementation/trust_root.json":
                          (json.dumps(forged, indent=2) + "\n").encode("utf-8")})
        result = lab.assess(lab.claim())
        self.assertEqual(result["disposition"], "PASS_PROCESS", result["findings"])
        self.assertNoAuthority(result)

    def test_candidate_workflow_self_modification_is_rejected(self):
        lab = Lab(self, head_files={
            WORKFLOW: b"name: regression\non: pull_request\njobs:\n  skip:\n"
                      b"    if: github.event.pull_request.number == 298\n",
        })
        result = lab.assess(lab.claim())
        self.assertFinding(result, "WORKFLOW_SOURCE_MODIFIED")
        self.assertFinding(result, "PROTECTED_PATH_TOUCHED")


class EvidenceLogTests(TrustTestCase):
    def test_rewritten_log_history_is_rejected(self):
        lab = Lab(self)
        rewritten = b"# Engineering log\n\n- rewritten history\n"
        lab.rewrite_head({LOG_PATH: rewritten})
        claim = lab.claim(log={
            "path": LOG_PATH, "changed": True,
            "added_sha256": hashlib.sha256(rewritten).hexdigest(),
            "added_bytes": len(rewritten),
        })
        self.assertFinding(lab.assess(claim), "LOG_PREFIX_BROKEN")

    def test_truncated_log_is_rejected(self):
        lab = Lab(self)
        lab.rewrite_head({LOG_PATH: lab.base_log[:9]})
        result = lab.assess(lab.claim())
        self.assertFinding(result, "LOG_PREFIX_BROKEN")
        self.assertFinding(result, "LOG_DECLARATION_MISMATCH")

    def test_deleted_log_is_rejected(self):
        lab = Lab(self, head_files={LOG_PATH: None}, append_log=False)
        result = lab.assess(lab.claim())
        self.assertFinding(result, "LOG_MISSING")
        self.assertFinding(result, "LOG_DECLARATION_MISMATCH")

    def test_unappended_log_is_rejected(self):
        lab = Lab(self, append_log=False)
        result = lab.assess(lab.claim())
        self.assertFinding(result, "LOG_NOT_APPENDED")

    def test_log_append_hash_must_match_git_bytes(self):
        lab = Lab(self)
        self.assertFinding(lab.assess(lab.claim(log={
            "path": LOG_PATH, "changed": True,
            "added_sha256": "0" * 64, "added_bytes": len(APPENDED_LOG),
        })), "LOG_APPEND_HASH_MISMATCH")

    def test_log_declaration_path_must_be_pinned_path(self):
        lab = Lab(self)
        self.assertFinding(lab.assess(lab.claim(log={
            "path": "docs/OTHER_LOG.md", "changed": True,
            "added_sha256": hashlib.sha256(APPENDED_LOG).hexdigest(),
            "added_bytes": len(APPENDED_LOG),
        })), "LOG_PATH_MISMATCH")

    def test_unchanged_log_cannot_claim_an_append(self):
        lab = Lab(self, append_log=False)
        self.assertFinding(lab.assess(lab.claim(log={
            "path": LOG_PATH, "changed": True,
            "added_sha256": hashlib.sha256(b"").hexdigest(), "added_bytes": 0,
        })), "LOG_NOT_APPENDED")


class ProtectedPathTests(TrustTestCase):
    def test_protected_document_rename_is_rejected(self):
        lab = Lab(self, head_moves=[("GOVERNANCE.md", "docs/governance-archive.md")])
        result = lab.assess(lab.claim())
        self.assertFinding(result, "PROTECTED_PATH_RENAMED")
        self.assertFinding(result, "PROTECTED_PATH_TOUCHED")

    def test_nested_agents_md_is_protected(self):
        lab = Lab(self, base_files={"implementation/AGENTS.md": b"# Agents\n"},
                  head_files={"implementation/AGENTS.md": b"# Agents\n- new rule\n"})
        self.assertFinding(lab.assess(lab.claim()), "PROTECTED_PATH_TOUCHED")

    def test_named_policy_document_is_protected(self):
        lab = Lab(self, base_files={"docs/REVIEW_AND_MERGE_POLICY_V1.md": b"# Policy\n"},
                  head_files={"docs/REVIEW_AND_MERGE_POLICY_V1.md": b"# Policy\n- edit\n"})
        self.assertFinding(lab.assess(lab.claim()), "PROTECTED_PATH_TOUCHED")

    def test_workflow_deletion_is_rejected(self):
        lab = Lab(self, head_files={WORKFLOW: None})
        result = lab.assess(lab.claim())
        self.assertFinding(result, "WORKFLOW_MISSING")
        self.assertFinding(result, "WORKFLOW_SOURCE_MODIFIED")


class ReviewerIdentityTests(TrustTestCase):
    def test_self_approval_by_numeric_identity_is_rejected(self):
        lab = Lab(self)
        reviews = [lab.review(1, AUTHOR_ID, "renamed-agent"), lab.review(2, 333, "reviewer-z")]
        self.assertFinding(lab.assess(lab.claim(reviews=reviews)), "SELF_APPROVAL")

    def test_self_approval_by_login_collision_is_rejected(self):
        lab = Lab(self)
        reviews = [lab.review(1, 777, AUTHOR_LOGIN), lab.review(2, 333, "reviewer-z")]
        result = lab.assess(lab.claim(reviews=reviews))
        self.assertFinding(result, "SELF_APPROVAL")
        self.assertFinding(result, "AUTHOR_LOGIN_COLLISION")

    def test_same_numeric_reviewer_does_not_count_twice(self):
        lab = Lab(self)
        reviews = [lab.review(1, 222, "reviewer-y"), lab.review(2, 222, "reviewer-z")]
        result = lab.assess(lab.claim(reviews=reviews))
        self.assertFinding(result, "DUPLICATE_REVIEWER_IDENTITY")
        self.assertFinding(result, "INSUFFICIENT_APPROVALS")

    def test_approval_on_old_head_is_stale(self):
        lab = Lab(self)
        reviews = [lab.review(1, 222, "reviewer-y", head=lab.base_sha),
                   lab.review(2, 333, "reviewer-z")]
        result = lab.assess(lab.claim(reviews=reviews))
        self.assertFinding(result, "REVIEW_NOT_ON_HEAD")
        self.assertFinding(result, "INSUFFICIENT_APPROVALS")

    def test_dismissed_approval_does_not_count(self):
        lab = Lab(self)
        reviews = [lab.review(1, 222, "reviewer-y", dismissed=True),
                   lab.review(2, 333, "reviewer-z")]
        self.assertFinding(lab.assess(lab.claim(reviews=reviews)), "INSUFFICIENT_APPROVALS")

    def test_changes_requested_blocks(self):
        lab = Lab(self)
        reviews = [lab.review(1, 222, "reviewer-y"), lab.review(2, 333, "reviewer-z"),
                   lab.review(3, 444, "reviewer-w", state="CHANGES_REQUESTED")]
        self.assertFinding(lab.assess(lab.claim(reviews=reviews)), "CHANGES_REQUESTED_PRESENT")

    def test_duplicate_review_identifier_is_rejected(self):
        lab = Lab(self)
        reviews = [lab.review(1, 222, "reviewer-y"), lab.review(1, 333, "reviewer-z")]
        self.assertFinding(lab.assess(lab.claim(reviews=reviews)), "DUPLICATE_REVIEW_ID")


class CiBindingTests(TrustTestCase):
    def test_push_event_cannot_supply_pr_ci(self):
        lab = Lab(self)
        self.assertFinding(lab.assess(lab.claim(ci={"event": "push"})),
                           "CI_EVENT_NOT_PULL_REQUEST")

    def test_non_green_ci_is_rejected(self):
        lab = Lab(self)
        self.assertFinding(lab.assess(lab.claim(ci={"conclusion": "failure"})), "CI_NOT_GREEN")

    def test_ci_head_must_equal_pr_head(self):
        lab = Lab(self)
        self.assertFinding(lab.assess(lab.claim(ci={"head_sha": lab.base_sha})),
                           "CI_HEAD_MISMATCH")

    def test_ci_branch_must_equal_pr_branch(self):
        lab = Lab(self)
        self.assertFinding(lab.assess(lab.claim(ci={"head_branch": "main"})),
                           "CI_BRANCH_MISMATCH")

    def test_ci_workflow_path_must_equal_pinned_path(self):
        lab = Lab(self)
        self.assertFinding(lab.assess(lab.claim(ci={"workflow_path": ".github/workflows/other.yml"})),
                           "CI_WORKFLOW_MISMATCH")

    def test_ci_github_actions_app_identity_is_required(self):
        lab = Lab(self)
        self.assertFinding(lab.assess(lab.claim(ci={"app_id": 1})),
                           "CI_CHECK_IDENTITY_MISMATCH")

    def test_ci_repository_must_equal_pinned_repository(self):
        lab = Lab(self)
        self.assertFinding(lab.assess(lab.claim(ci={"repository_id": 1})),
                           "CI_REPOSITORY_MISMATCH")

    def test_ci_pr_association_must_be_explicit(self):
        lab = Lab(self)
        self.assertFinding(lab.assess(lab.claim(ci={"pr_association": {
            "method": "name_and_sha", "pr_id": PR_ID, "pr_number": PR_NUMBER,
        }})), "PR_ASSOCIATION_UNPROVEN")

    def test_ci_pr_association_must_match_pr_identity(self):
        lab = Lab(self)
        self.assertFinding(lab.assess(lab.claim(ci={"pr_association": {
            "method": "explicit_link", "pr_id": PR_ID, "pr_number": 999,
        }})), "PR_ASSOCIATION_UNPROVEN")

    def test_ci_workflow_source_revision_must_equal_head_blob(self):
        lab = Lab(self)
        other = lab.blob("impl/example.py")
        self.assertFinding(lab.assess(lab.claim(ci={"workflow_source_sha": other})),
                           "WORKFLOW_SOURCE_SHA_MISMATCH")


class GitObjectDeclarationTests(TrustTestCase):
    def test_phantom_file_is_rejected(self):
        lab = Lab(self)
        files = lab.diff_files() + [{
            "status": "A", "path": "impl/phantom.py", "old_path": None,
            "old_blob": None, "new_blob": lab.blob("impl/extra.py"),
        }]
        self.assertFinding(lab.assess(lab.claim(files=files)), "DIFF_DECLARATION_MISMATCH")

    def test_missing_file_is_rejected(self):
        lab = Lab(self)
        files = [entry for entry in lab.diff_files() if entry["path"] != "impl/extra.py"]
        self.assertFinding(lab.assess(lab.claim(files=files)), "DIFF_DECLARATION_MISMATCH")

    def test_wrong_blob_identity_is_rejected(self):
        lab = Lab(self)
        files = lab.diff_files()
        for entry in files:
            if entry["path"] == "impl/example.py":
                entry["new_blob"] = lab.blob("impl/example.py", lab.base_sha)
        self.assertFinding(lab.assess(lab.claim(files=files)), "DIFF_DECLARATION_MISMATCH")

    def test_rename_cannot_be_declared_as_add(self):
        lab = Lab(self, head_files={"impl/example.py": b"value = 1\n"},
                  head_moves=[("impl/example.py", "impl/renamed.py")])
        files = lab.diff_files()
        for entry in files:
            if entry["status"] == "R":
                entry["status"] = "A"
                entry["old_path"] = None
                entry["old_blob"] = None
        self.assertFinding(lab.assess(lab.claim(files=files)), "DIFF_DECLARATION_MISMATCH")

    def test_declared_tree_must_equal_head_tree(self):
        lab = Lab(self)
        self.assertFinding(lab.assess(lab.claim(tree=lab.base_tree)), "HEAD_TREE_MISMATCH")

    def test_repository_identity_is_pinned(self):
        lab = Lab(self)
        self.assertFinding(lab.assess(lab.claim(repository={"id": 1})),
                           "REPOSITORY_IDENTITY_MISMATCH")

    def test_unrelated_base_is_rejected(self):
        lab = Lab(self)
        orphan = lab.orphan()
        result = lab.assess(lab.claim(pr={"base_sha": orphan}))
        self.assertFinding(result, "BASE_NOT_ANCESTOR")

    def test_head_moved_before_verification_is_rejected(self):
        lab = Lab(self)
        claim = lab.claim()
        lab.rewrite_head({"impl/extra.py": b"new = False\n"})
        self.assertFinding(lab.assess(claim), "HEAD_REF_SHA_MISMATCH")

    def test_base_moved_before_verification_is_rejected(self):
        lab = Lab(self)
        claim = lab.claim()
        lab._git("checkout", "-q", "main")
        lab.write_file("impl/other.py", b"base = 2\n")
        lab.commit("base moved")
        lab._git("checkout", "-q", "research/example")
        self.assertFinding(lab.assess(claim), "BASE_REF_SHA_MISMATCH")

    def test_head_or_base_moved_during_verification_is_rejected(self):
        lab = Lab(self)
        claim = lab.claim()

        def move() -> None:
            lab.rewrite_head({"impl/extra.py": b"new = 'after verification'\n"})

        result = lab.assess(claim, after_first_read=move)
        self.assertFinding(result, "HEAD_OR_BASE_MOVED")
        self.assertFinding(result, "REF_MOVED_AFTER_VERIFICATION")


class MergeShapeTests(TrustTestCase):
    def test_squash_merge_loses_the_reviewed_head(self):
        lab = Lab(self)
        lab.merge(squash=True)
        result = lab.assess(lab.claim(mode="POST_MERGE"))
        self.assertFinding(result, "MERGE_COMMIT_NOT_TWO_PARENT")
        self.assertFinding(result, "MERGE_PARENTS_DECLARATION_MISMATCH")

    def test_reversed_merge_parent_order_is_rejected(self):
        lab = Lab(self)
        lab.merge(reverse=True)
        self.assertFinding(lab.assess(lab.claim(mode="POST_MERGE")),
                           "MERGE_BASE_PARENT_MISMATCH")

    def test_bypass_actor_merge_is_rejected(self):
        lab = Lab(self)
        lab.merge()
        result = lab.assess(lab.claim(mode="POST_MERGE", merge={
            "merged_by_id": BYPASS_ACTOR, "merged_by_login": "bypass-actor",
        }))
        self.assertFinding(result, "BYPASS_ACTOR_MERGE")

    def test_bypass_actor_does_not_apply_to_pre_merge(self):
        lab = Lab(self)
        result = lab.assess(lab.claim(merge={
            "merged_by_id": BYPASS_ACTOR, "merged_by_login": "bypass-actor",
        }))
        self.assertEqual(result["disposition"], "PASS_PROCESS", result["findings"])

    def test_pre_merge_claim_may_not_carry_merge_metadata(self):
        lab = Lab(self)
        self.assertFinding(lab.assess(lab.claim(merge={"commit_sha": lab.head_sha})),
                           "PRE_MERGE_HAS_MERGE_METADATA")

    def test_draft_pr_is_not_mergeable(self):
        lab = Lab(self)
        self.assertFinding(lab.assess(lab.claim(pr={"draft": True})),
                           "DRAFT_PR_NOT_MERGEABLE")

    def test_requested_mode_must_match_claim_mode(self):
        lab = Lab(self)
        self.assertFinding(lab.assess(lab.claim(), requested_mode="POST_MERGE"),
                           "MODE_CONFLICT")

    def test_post_merge_claim_requires_closed_pr(self):
        lab = Lab(self)
        lab.merge()
        self.assertFinding(lab.assess(lab.claim(mode="POST_MERGE", pr={"state": "open"})),
                           "POST_MERGE_STATE_INVALID")


class ClaimValidationTests(TrustTestCase):
    def test_missing_claim_field_holds(self):
        lab = Lab(self)
        claim = lab.claim()
        del claim["tree"]
        self.assertFinding(lab.assess(claim), "CLAIM_INVALID")

    def test_extra_claim_field_holds(self):
        lab = Lab(self)
        claim = lab.claim()
        claim["policy"] = {"required_approvals": 0}
        self.assertFinding(lab.assess(claim), "CLAIM_INVALID")

    def test_wrong_claim_schema_holds(self):
        lab = Lab(self)
        self.assertFinding(lab.assess(lab.claim(ci={"conclusion": "success"}) | {
            "schema": "ARIO-MERGE-CLAIM-9999",
        }), "CLAIM_INVALID")

    def test_non_git_candidate_holds(self):
        lab = Lab(self)
        other = lab.root / "not-a-repo"
        other.mkdir()
        result = assess(other, lab.claim(), trust_root_path=lab.trust,
                        verifier_dir=lab.verifier)
        self.assertFinding(result, "GIT_OBJECT_ERROR")

    def test_duplicate_json_member_is_rejected_by_cli(self):
        lab = Lab(self)
        claim_path = lab.root / "duplicate.json"
        claim_path.write_bytes(b'{"schema": "a", "schema": "b"}')
        result = subprocess.run(
            [sys.executable, "-m", "research.trusted_merge_verifier.cli",
             "--candidate", str(lab.candidate), "--claim", str(claim_path),
             "--trust-root", str(lab.trust), "--verifier-dir", str(lab.verifier)],
            cwd=str(PACKAGE.parents[1]), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=120,
        )
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(payload["disposition"], "HOLD")
        self.assertEqual(payload["reason"], "UNREADABLE_CLAIM")

    def test_nonstandard_json_constant_is_rejected_by_cli(self):
        lab = Lab(self)
        claim_path = lab.root / "nan.json"
        claim_path.write_text('{"schema": NaN}', "utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "research.trusted_merge_verifier.cli",
             "--candidate", str(lab.candidate), "--claim", str(claim_path),
             "--trust-root", str(lab.trust), "--verifier-dir", str(lab.verifier)],
            cwd=str(PACKAGE.parents[1]), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=120,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout.decode("utf-8"))["reason"],
                         "UNREADABLE_CLAIM")


class GuardMutationTests(TrustTestCase):
    """Remove one guard at a time and prove the corresponding attack then passes.

    This is mutation testing of the verifier itself: if a guard is not
    load-bearing, its adversarial regression is not testing anything.
    """

    def assertLoadBearing(self, lab: Lab, claim: dict, guard: str, finding: str, **kwargs):
        self.assertIn(guard, {name for name, _ in module.GUARDS})
        before = lab.assess(claim, **kwargs)
        self.assertEqual(before["disposition"], "HOLD", (guard, before["findings"]))
        self.assertIn(finding, before["findings"])
        self.assertNoAuthority(before)
        with guard_removed(guard):
            after = lab.assess(claim, **kwargs)
        self.assertEqual(after["disposition"], "PASS_PROCESS", (guard, after["findings"]))
        self.assertNoAuthority(after)
        return after

    def test_log_prefix_guard_is_load_bearing(self):
        lab = Lab(self)
        rewritten = b"# Engineering log\n\n- rewritten history\n"
        lab.rewrite_head({LOG_PATH: rewritten})
        claim = lab.claim(log={
            "path": LOG_PATH, "changed": True,
            "added_sha256": hashlib.sha256(rewritten).hexdigest(),
            "added_bytes": len(rewritten),
        })
        self.assertLoadBearing(lab, claim, "log_prefix", "LOG_PREFIX_BROKEN")

    def test_protected_paths_guard_is_load_bearing(self):
        lab = Lab(self, head_moves=[("GOVERNANCE.md", "docs/governance-archive.md")])
        self.assertLoadBearing(lab, lab.claim(), "protected_paths", "PROTECTED_PATH_RENAMED")

    def test_workflow_protection_is_load_bearing(self):
        lab = Lab(self, head_files={
            WORKFLOW: b"name: regression\non: pull_request\njobs:\n  skip:\n"
                      b"    if: github.event.pull_request.number == 298\n",
        })
        self.assertLoadBearing(lab, lab.claim(), "protected_paths", "WORKFLOW_SOURCE_MODIFIED")

    def test_reviewer_identity_guard_is_load_bearing(self):
        lab = Lab(self, required_approvals=1)
        claim = lab.claim(reviews=[
            lab.review(1, 222, "reviewer-y"),
            lab.review(2, 222, "reviewer-z"),
        ])
        self.assertLoadBearing(lab, claim, "reviewer_identity", "DUPLICATE_REVIEWER_IDENTITY")

    def test_required_approvals_guard_is_load_bearing(self):
        lab = Lab(self)
        self.assertLoadBearing(lab, lab.claim(reviews=[]), "required_approvals",
                               "INSUFFICIENT_APPROVALS")

    def test_ci_event_guard_is_load_bearing(self):
        lab = Lab(self)
        self.assertLoadBearing(lab, lab.claim(ci={"event": "push"}),
                               "ci_identity", "CI_EVENT_NOT_PULL_REQUEST")

    def test_pr_association_guard_is_load_bearing(self):
        lab = Lab(self)
        claim = lab.claim(ci={"pr_association": {
            "method": "name_and_sha", "pr_id": PR_ID, "pr_number": PR_NUMBER,
        }})
        self.assertLoadBearing(lab, claim, "ci_pr_association", "PR_ASSOCIATION_UNPROVEN")

    def test_workflow_binding_guard_is_load_bearing(self):
        lab = Lab(self)
        claim = lab.claim(ci={"workflow_source_sha": lab.blob("impl/example.py")})
        self.assertLoadBearing(lab, claim, "workflow_binding", "WORKFLOW_SOURCE_SHA_MISMATCH")

    def test_diff_declaration_guard_is_load_bearing(self):
        lab = Lab(self)
        files = lab.diff_files() + [{
            "status": "A", "path": "impl/phantom.py", "old_path": None,
            "old_blob": None, "new_blob": lab.blob("impl/extra.py"),
        }]
        self.assertLoadBearing(lab, lab.claim(files=files), "diff_declaration",
                               "DIFF_DECLARATION_MISMATCH")

    def test_head_tree_guard_is_load_bearing(self):
        lab = Lab(self)
        self.assertLoadBearing(lab, lab.claim(tree=lab.base_tree), "head_tree",
                               "HEAD_TREE_MISMATCH")

    def test_mode_consistency_guard_is_load_bearing(self):
        lab = Lab(self)
        self.assertLoadBearing(lab, lab.claim(), "mode_consistency", "MODE_CONFLICT",
                               requested_mode="POST_MERGE")

    def test_repository_identity_guard_is_load_bearing(self):
        lab = Lab(self)
        self.assertLoadBearing(lab, lab.claim(repository={"id": 1}),
                               "repository_identity", "REPOSITORY_IDENTITY_MISMATCH")

    def test_bypass_actor_guard_is_load_bearing(self):
        lab = Lab(self)
        lab.merge()
        claim = lab.claim(mode="POST_MERGE", merge={
            "merged_by_id": BYPASS_ACTOR, "merged_by_login": "bypass-actor",
        })
        self.assertLoadBearing(lab, claim, "bypass_actor", "BYPASS_ACTOR_MERGE")

    def test_merge_shape_guard_is_load_bearing(self):
        lab = Lab(self)
        lab.merge(squash=True)
        self.assertLoadBearing(lab, lab.claim(mode="POST_MERGE"), "postmerge_shape",
                               "MERGE_COMMIT_NOT_TWO_PARENT")

    def test_ref_stability_guard_is_load_bearing(self):
        first = Lab(self)
        moved = first.assess(
            first.claim(),
            after_first_read=lambda: first.rewrite_head({"impl/extra.py": b"new = 'moved'\n"}),
        )
        self.assertFinding(moved, "HEAD_OR_BASE_MOVED")
        self.assertFinding(moved, "REF_MOVED_AFTER_VERIFICATION")

        second = Lab(self)
        claim = second.claim()
        self.assertIn("refs_stable", {name for name, _ in module.GUARDS})
        with guard_removed("refs_stable"):
            after = second.assess(
                claim,
                after_first_read=lambda: second.rewrite_head({"impl/extra.py": b"new = 'moved'\n"}),
            )
        self.assertEqual(after["disposition"], "PASS_PROCESS", after["findings"])
        self.assertNoAuthority(after)


if __name__ == "__main__":
    unittest.main()
