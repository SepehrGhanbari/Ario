"""Separated-role research verifier for governance merge evidence.

Roles:
  * candidate / evidence supplier: untrusted; may edit its own checker, policy,
    workflow, log and claim JSON;
  * trusted verifier: this pinned module tree, loaded independently of the
    candidate HEAD;
  * operator-supplied trust root: hashes of the exact verifier and policy bytes.

The verifier derives diffs, renames, blob identities and the engineering log
bytes from candidate Git objects, then evaluates them against the pinned policy.
It never authorizes a merge. Same-user process separation is NOT independent
custody; see the research note for the common-administrator boundary.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable

from .git_objects import DiffEntry, GitObjectError, GitRepo
from .trust import TrustError, load_policy, load_trust_root, verify_trust

SCHEMA = "ARIO-TRUSTED-MERGE-VERIFICATION-RESEARCH-0.1"
CLAIM_SCHEMA = "ARIO-MERGE-CLAIM-0.1"
AUTHORITY = "NON_AUTHORITATIVE_RESEARCH_ONLY"
SCOPE = "SYNTHETIC_TWO_ROLE_LAB_ONLY"
MAX_CLAIM_BYTES = 4 * 1024 * 1024
MAX_FILES = 5000
SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
MODES = frozenset({"PRE_MERGE", "POST_MERGE"})

CLAIM_FIELDS = frozenset({
    "schema", "repository", "pr", "reviews", "ci", "mode", "merge", "files", "log", "tree",
})
PR_FIELDS = frozenset({
    "id", "number", "state", "draft", "author_id", "author_login", "head_ref",
    "base_ref", "head_sha", "base_sha", "merge_method",
})
REVIEW_FIELDS = frozenset({"id", "author_id", "author_login", "state", "commit_id", "dismissed"})
CI_FIELDS = frozenset({
    "repository_id", "run_id", "run_attempt", "event", "status", "conclusion",
    "head_sha", "head_branch", "workflow_id", "workflow_path", "workflow_source_sha",
    "check_name", "app_id", "pr_association",
})
ASSOCIATION_FIELDS = frozenset({"method", "pr_id", "pr_number"})
MERGE_FIELDS = frozenset({"commit_sha", "method", "merged_by_id", "merged_by_login", "parents"})
FILE_FIELDS = frozenset({"status", "path", "old_path", "old_blob", "new_blob"})
LOG_FIELDS = frozenset({"path", "changed", "added_sha256", "added_bytes"})
CLAIM_MODES = frozenset({"PRE_MERGE", "POST_MERGE"})

GUARDS: list[tuple[str, Callable[[dict], list[str]]]] = []


def guard(name: str):
    def register(function):
        GUARDS.append((name, function))
        return function
    return register


class ClaimError(ValueError):
    """The candidate-supplied claim is structurally unusable."""


class VerifierError(RuntimeError):
    """The pinned verifier boundary cannot be established."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False, ensure_ascii=False).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hold(reason: str, detail: str, findings: list[str] | None = None,
          evidence: dict | None = None, mode: str | None = None) -> dict:
    return {
        "schema": SCHEMA,
        "disposition": "HOLD",
        "reason": reason,
        "detail": str(detail)[:600],
        "findings": list(findings or [reason]),
        "assessment_mode": mode,
        "scope": SCOPE,
        "authority": AUTHORITY,
        "merge_authorized": False,
        "trust_activated": False,
        "evidence": evidence or {},
        "epistemic_limit": (
            "Separated-role research verifier over caller-supplied evidence and local Git "
            "objects. Same-user process separation only; no independent custody, reviewer "
            "identity, GitHub authentication, trusted executor or merge authority."
        ),
    }


def _pass(evidence: dict, mode: str) -> dict:
    return {
        "schema": SCHEMA,
        "disposition": "PASS_PROCESS",
        "reason": "PINNED_POLICY_AND_GIT_OBJECTS_CONSISTENT",
        "detail": "Pinned policy, derived Git objects and supplied evidence agree.",
        "findings": [],
        "assessment_mode": mode,
        "scope": SCOPE,
        "authority": AUTHORITY,
        "merge_authorized": False,
        "trust_activated": False,
        "evidence": evidence,
        "epistemic_limit": (
            "Process consistency only. Same-user process separation does not prove "
            "independent custody, reviewer identity, GitHub authenticity or merge authority."
        ),
    }


def _positive(value: Any) -> bool:
    return type(value) is int and value > 0


def _sha(value: Any) -> bool:
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def _text(value: Any, cap: int = 300) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= cap


def _obj(value: Any, fields: frozenset[str], name: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise ClaimError(f"{name} must be an object with exact research fields")
    return value


def _files(value: Any) -> list[dict]:
    if not isinstance(value, list) or len(value) > MAX_FILES:
        raise ClaimError("files must be a bounded list")
    out = []
    for entry in value:
        entry = _obj(entry, FILE_FIELDS, "file entry")
        if entry["status"] not in {"A", "M", "D", "R", "T"}:
            raise ClaimError("file status is unsupported")
        if not _text(entry["path"], 512) or entry["path"].startswith("/") or "\\" in entry["path"]:
            raise ClaimError("file path is invalid")
        if entry["old_path"] is not None and not _text(entry["old_path"], 512):
            raise ClaimError("file old_path is invalid")
        for key in ("old_blob", "new_blob"):
            if entry[key] is not None and not _sha(entry[key]):
                raise ClaimError(f"file {key} is invalid")
        out.append(entry)
    return out


def validate_claim(claim: Any) -> dict:
    claim = _obj(claim, CLAIM_FIELDS, "claim")
    if claim["schema"] != CLAIM_SCHEMA:
        raise ClaimError("claim schema is unsupported")
    if claim["mode"] not in CLAIM_MODES:
        raise ClaimError("claim mode is unsupported")
    repo = claim["repository"]
    if not isinstance(repo, dict) or set(repo) != {"id", "full_name"} \
            or not _positive(repo["id"]) or not _text(repo["full_name"]):
        raise ClaimError("claim repository identity is invalid")
    pr = _obj(claim["pr"], PR_FIELDS, "pr")
    for key in ("id", "number", "author_id"):
        if not _positive(pr[key]):
            raise ClaimError(f"pr.{key} must be positive")
    if pr["state"] not in {"open", "closed"} or type(pr["draft"]) is not bool:
        raise ClaimError("pr state/draft is invalid")
    for key in ("head_ref", "base_ref", "author_login"):
        if not _text(pr[key], 256):
            raise ClaimError(f"pr.{key} is invalid")
    for key in ("head_sha", "base_sha"):
        if not _sha(pr[key]):
            raise ClaimError(f"pr.{key} is not a full SHA")
    if pr["merge_method"] not in {"merge", "squash", "rebase"}:
        raise ClaimError("pr merge_method is unsupported")
    reviews = claim["reviews"]
    if not isinstance(reviews, list) or len(reviews) > 500:
        raise ClaimError("reviews must be a bounded list")
    for review in reviews:
        review = _obj(review, REVIEW_FIELDS, "review")
        if not _positive(review["id"]) or not _positive(review["author_id"]):
            raise ClaimError("review identity is invalid")
        if not _text(review["author_login"], 100) or review["state"] not in {
                "APPROVED", "CHANGES_REQUESTED", "COMMENTED", "DISMISSED"}:
            raise ClaimError("review author/state is invalid")
        if review["commit_id"] is not None and not _sha(review["commit_id"]):
            raise ClaimError("review commit_id is invalid")
        if type(review["dismissed"]) is not bool:
            raise ClaimError("review dismissed is invalid")
    ci = _obj(claim["ci"], CI_FIELDS, "ci")
    for key in ("repository_id", "run_id", "run_attempt", "workflow_id", "app_id"):
        if not _positive(ci[key]):
            raise ClaimError(f"ci.{key} must be positive")
    if ci["event"] not in {"pull_request", "push", "merge_group"} \
            or ci["status"] not in {"queued", "in_progress", "completed"} \
            or ci["conclusion"] not in {"success", "failure", "neutral", "cancelled",
                                        "skipped", "timed_out", "action_required", None}:
        raise ClaimError("ci event/status/conclusion is invalid")
    for key in ("head_sha", "workflow_source_sha"):
        if not _sha(ci[key]):
            raise ClaimError(f"ci.{key} is not a full SHA")
    for key in ("head_branch", "workflow_path", "check_name"):
        if not _text(ci[key], 300):
            raise ClaimError(f"ci.{key} is invalid")
    association = _obj(ci["pr_association"], ASSOCIATION_FIELDS, "pr_association")
    if not _text(association["method"], 64) or not _positive(association["pr_id"]) \
            or not _positive(association["pr_number"]):
        raise ClaimError("pr association is invalid")
    merge = _obj(claim["merge"], MERGE_FIELDS, "merge")
    if merge["commit_sha"] is not None and not _sha(merge["commit_sha"]):
        raise ClaimError("merge commit_sha is invalid")
    if merge["method"] not in {"merge", "squash", "rebase"}:
        raise ClaimError("merge method is unsupported")
    if not _positive(merge["merged_by_id"]) or not _text(merge["merged_by_login"], 100):
        raise ClaimError("merge actor is invalid")
    if not isinstance(merge["parents"], list) or len(merge["parents"]) > 4 \
            or not all(_sha(parent) for parent in merge["parents"]):
        raise ClaimError("merge parents are invalid")
    log = _obj(claim["log"], LOG_FIELDS, "log")
    if not _text(log["path"], 300) or type(log["changed"]) is not bool:
        raise ClaimError("log path/changed is invalid")
    if log["changed"]:
        if not isinstance(log["added_sha256"], str) or DIGEST.fullmatch(log["added_sha256"]) is None:
            raise ClaimError("log added_sha256 is invalid")
        if type(log["added_bytes"]) is not int or log["added_bytes"] < 0:
            raise ClaimError("log added_bytes is invalid")
    else:
        if log["added_sha256"] is not None or log["added_bytes"] != 0:
            raise ClaimError("unchanged log must not declare an append")
    if not _sha(claim["tree"]):
        raise ClaimError("claim tree is invalid")
    return {"claim": claim, "files": _files(claim["files"])}


def _is_protected(path: str, policy: dict) -> bool:
    protected = policy["protected_paths"]
    base = path.rsplit("/", 1)[-1]
    if base in protected["basenames"]:
        return True
    if path.startswith(tuple(protected["prefixes"])):
        return True
    return re.search(protected["name_pattern"], path) is not None


def _read_snapshot(repo: GitRepo, claim: dict) -> dict:
    head = repo.resolve_ref(claim["pr"]["head_ref"])
    target = repo.resolve_ref(claim["pr"]["base_ref"])
    return {"head_sha": head, "target_sha": target}


def _derive(repo: GitRepo, claim: dict, policy: dict) -> dict:
    pr, merge = claim["pr"], claim["merge"]
    head = repo.commit(pr["head_sha"])
    base = repo.commit(pr["base_sha"])
    diff = repo.diff(base.sha, head.sha)
    log_path = policy["log_path"]
    base_log_id = repo.blob_id(base.sha, log_path)
    head_log_id = repo.blob_id(head.sha, log_path)
    log_base = repo.blob_bytes(base_log_id) if base_log_id else None
    log_head = repo.blob_bytes(head_log_id) if head_log_id else None
    log_paths = {entry.path for entry in diff}
    log_changed = log_path in log_paths
    delta = None
    prefix_ok = None
    if log_base is not None and log_head is not None:
        prefix_ok = log_head.startswith(log_base)
        if prefix_ok and len(log_head) > len(log_base):
            delta = log_head[len(log_base):]
    merge_commit = None
    if merge["commit_sha"] is not None:
        merge_commit = repo.commit(merge["commit_sha"])
    workflow_path = policy["required_check"]["workflow_path"]
    workflow_blob = repo.blob_id(head.sha, workflow_path)
    blobs = {}
    for entry in diff:
        if entry.status == "D" or entry.new_blob is None:
            continue
        try:
            digest, size = repo.blob_sha256(entry.new_blob)
        except GitObjectError:
            digest, size = None, None
        blobs[entry.new_blob] = {"sha256": digest, "bytes": size}
    return {
        "head": head, "base": base, "merge": merge_commit, "diff": diff,
        "log_base": log_base, "log_head": log_head, "log_changed": log_changed,
        "log_delta": delta, "log_prefix_ok": prefix_ok,
        "workflow_blob": workflow_blob, "blobs": blobs,
    }


def _declared(claim: dict) -> set:
    return {(entry["status"], entry["path"], entry["old_path"],
             entry["old_blob"], entry["new_blob"]) for entry in claim["files"]}


def _derived(entries: list[DiffEntry]) -> set:
    result = set()
    for entry in entries:
        status = "R" if entry.status == "C" else entry.status
        result.add((status, entry.path, entry.old_path if status == "R" else None,
                    entry.old_blob, entry.new_blob))
    return result


@guard("repository_identity")
def _g_repository(ctx: dict) -> list[str]:
    claim, policy = ctx["claim"], ctx["policy"]
    if (claim["repository"]["id"] != policy["repository"]["id"]
            or claim["repository"]["full_name"] != policy["repository"]["full_name"]):
        return ["REPOSITORY_IDENTITY_MISMATCH"]
    return []


@guard("refs_match_claim")
def _g_refs(ctx: dict) -> list[str]:
    claim, snap = ctx["claim"], ctx["snapshot1"]
    pr, merge = claim["pr"], claim["merge"]
    findings = []
    if snap["head_sha"] != pr["head_sha"]:
        findings.append("HEAD_REF_SHA_MISMATCH")
    if claim["mode"] == "PRE_MERGE" and snap["target_sha"] != pr["base_sha"]:
        findings.append("BASE_REF_SHA_MISMATCH")
    if claim["mode"] == "POST_MERGE" and snap["target_sha"] != merge["commit_sha"]:
        findings.append("BASE_REF_SHA_MISMATCH")
    return findings


@guard("head_tree")
def _g_tree(ctx: dict) -> list[str]:
    return [] if ctx["derived"]["head"].tree == ctx["claim"]["tree"] else ["HEAD_TREE_MISMATCH"]


@guard("base_ancestor")
def _g_ancestor(ctx: dict) -> list[str]:
    claim, repo = ctx["claim"], ctx["repo"]
    if not repo.is_ancestor(claim["pr"]["base_sha"], claim["pr"]["head_sha"]):
        return ["BASE_NOT_ANCESTOR"]
    return []


@guard("merge_base")
def _g_merge_base(ctx: dict) -> list[str]:
    claim, repo = ctx["claim"], ctx["repo"]
    base = repo.merge_base(claim["pr"]["head_sha"], claim["pr"]["base_sha"])
    if base != claim["pr"]["base_sha"]:
        return ["MERGE_BASE_MISMATCH"]
    return []


@guard("diff_declaration")
def _g_diff(ctx: dict) -> list[str]:
    if _declared(ctx["claim"]) != _derived(ctx["derived"]["diff"]):
        return ["DIFF_DECLARATION_MISMATCH"]
    return []


@guard("protected_paths")
def _g_protected(ctx: dict) -> list[str]:
    policy, diff = ctx["policy"], ctx["derived"]["diff"]
    findings = []
    workflow = policy["required_check"]["workflow_path"]
    for entry in diff:
        old, new = entry.old_path, entry.new_path
        if entry.status in {"R", "C"} and old and new and _is_protected(old, policy) \
                and not _is_protected(new, policy):
            findings.append("PROTECTED_PATH_RENAMED")
        if any(path and _is_protected(path, policy) for path in (old, new)):
            findings.append("PROTECTED_PATH_TOUCHED")
        if workflow in (old, new):
            findings.append("WORKFLOW_SOURCE_MODIFIED")
    return list(dict.fromkeys(findings))


@guard("log_prefix")
def _g_log_prefix(ctx: dict) -> list[str]:
    policy, derived = ctx["policy"], ctx["derived"]
    findings = []
    if derived["log_changed"] and (derived["log_base"] is None or derived["log_head"] is None):
        findings.append("LOG_MISSING")
    if policy["require_log_append"] and not derived["log_changed"]:
        findings.append("LOG_NOT_APPENDED")
    if derived["log_base"] is not None and derived["log_head"] is not None:
        if not derived["log_prefix_ok"]:
            findings.append("LOG_PREFIX_BROKEN")
        elif derived["log_delta"] is None or not derived["log_delta"]:
            findings.append("LOG_NOT_APPENDED")
    return findings


@guard("log_declaration")
def _g_log_declaration(ctx: dict) -> list[str]:
    policy, claim, derived = ctx["policy"], ctx["claim"], ctx["derived"]
    if claim["log"]["path"] != policy["log_path"]:
        return ["LOG_PATH_MISMATCH"]
    findings = []
    if claim["log"]["changed"] != derived["log_changed"]:
        findings.append("LOG_DECLARATION_MISMATCH")
    delta = derived["log_delta"]
    if derived["log_changed"] and delta is not None:
        if (claim["log"]["added_sha256"] != _sha256(delta)
                or claim["log"]["added_bytes"] != len(delta)):
            findings.append("LOG_APPEND_HASH_MISMATCH")
    return findings


@guard("reviewer_identity")
def _g_reviewers(ctx: dict) -> list[str]:
    claim = ctx["claim"]
    pr = claim["pr"]
    findings = []
    review_ids = []
    by_id: dict[int, set[str]] = {}
    by_login: dict[str, set[int]] = {}
    for review in claim["reviews"]:
        review_ids.append(review["id"])
        by_id.setdefault(review["author_id"], set()).add(review["author_login"])
        by_login.setdefault(review["author_login"], set()).add(review["author_id"])
        if review["state"] == "CHANGES_REQUESTED" and not review["dismissed"]:
            findings.append("CHANGES_REQUESTED_PRESENT")
        if review["author_login"] == pr["author_login"] and review["author_id"] != pr["author_id"]:
            findings.append("AUTHOR_LOGIN_COLLISION")
        if review["state"] == "APPROVED" and not review["dismissed"]:
            if review["author_id"] == pr["author_id"] or review["author_login"] == pr["author_login"]:
                findings.append("SELF_APPROVAL")
            if review["commit_id"] != pr["head_sha"]:
                findings.append("REVIEW_NOT_ON_HEAD")
    if len(review_ids) != len(set(review_ids)):
        findings.append("DUPLICATE_REVIEW_ID")
    if any(len(logins) > 1 for logins in by_id.values()):
        findings.append("DUPLICATE_REVIEWER_IDENTITY")
    if any(len(ids) > 1 for ids in by_login.values()):
        findings.append("AMBIGUOUS_REVIEWER_LOGIN")
    return list(dict.fromkeys(findings))


@guard("required_approvals")
def _g_approvals(ctx: dict) -> list[str]:
    claim, policy = ctx["claim"], ctx["policy"]
    pr = claim["pr"]
    approvers = {
        review["author_id"] for review in claim["reviews"]
        if review["state"] == "APPROVED" and not review["dismissed"]
        and review["commit_id"] == pr["head_sha"]
        and review["author_id"] != pr["author_id"]
        and review["author_login"] != pr["author_login"]
    }
    return [] if len(approvers) >= policy["required_approvals"] else ["INSUFFICIENT_APPROVALS"]


@guard("ci_identity")
def _g_ci(ctx: dict) -> list[str]:
    claim, policy = ctx["claim"], ctx["policy"]
    ci, pr, check = claim["ci"], claim["pr"], policy["required_check"]
    findings = []
    if ci["repository_id"] != policy["repository"]["id"]:
        findings.append("CI_REPOSITORY_MISMATCH")
    if ci["event"] != "pull_request":
        findings.append("CI_EVENT_NOT_PULL_REQUEST")
    if ci["status"] != "completed" or ci["conclusion"] != "success":
        findings.append("CI_NOT_GREEN")
    if ci["head_sha"] != pr["head_sha"]:
        findings.append("CI_HEAD_MISMATCH")
    if ci["head_branch"] != pr["head_ref"]:
        findings.append("CI_BRANCH_MISMATCH")
    if ci["workflow_id"] != check["workflow_id"] or ci["workflow_path"] != check["workflow_path"]:
        findings.append("CI_WORKFLOW_MISMATCH")
    if ci["app_id"] != check["app_id"] or ci["check_name"] != check["name"]:
        findings.append("CI_CHECK_IDENTITY_MISMATCH")
    return findings


@guard("ci_pr_association")
def _g_association(ctx: dict) -> list[str]:
    claim, policy = ctx["claim"], ctx["policy"]
    association = claim["ci"]["pr_association"]
    pr = claim["pr"]
    if policy["require_explicit_pr_association"]:
        if association["method"] != "explicit_link":
            return ["PR_ASSOCIATION_UNPROVEN"]
        if association["pr_id"] != pr["id"] or association["pr_number"] != pr["number"]:
            return ["PR_ASSOCIATION_UNPROVEN"]
    return []


@guard("workflow_binding")
def _g_workflow(ctx: dict) -> list[str]:
    claim, derived = ctx["claim"], ctx["derived"]
    actual = derived["workflow_blob"]
    if actual is None:
        return ["WORKFLOW_MISSING"]
    if claim["ci"]["workflow_source_sha"] != actual:
        return ["WORKFLOW_SOURCE_SHA_MISMATCH"]
    return []


@guard("merge_method")
def _g_method(ctx: dict) -> list[str]:
    claim, policy = ctx["claim"], ctx["policy"]
    findings = []
    if claim["pr"]["merge_method"] != claim["merge"]["method"]:
        findings.append("MERGE_METHOD_CONFLICT")
    if claim["merge"]["method"] not in policy["allowed_merge_methods"]:
        findings.append("MERGE_METHOD_UNSUPPORTED")
    return findings


@guard("premerge_shape")
def _g_premerge(ctx: dict) -> list[str]:
    claim = ctx["claim"]
    if claim["mode"] != "PRE_MERGE":
        return []
    pr, merge = claim["pr"], claim["merge"]
    findings = []
    if pr["state"] != "open":
        findings.append("PRE_MERGE_PR_NOT_OPEN")
    if pr["draft"]:
        findings.append("DRAFT_PR_NOT_MERGEABLE")
    if merge["commit_sha"] is not None or merge["parents"]:
        findings.append("PRE_MERGE_HAS_MERGE_METADATA")
    return findings


@guard("postmerge_shape")
def _g_postmerge(ctx: dict) -> list[str]:
    claim = ctx["claim"]
    if claim["mode"] != "POST_MERGE":
        return []
    pr, merge, derived = claim["pr"], claim["merge"], ctx["derived"]
    findings = []
    if pr["state"] != "closed" or pr["draft"]:
        findings.append("POST_MERGE_STATE_INVALID")
    commit = derived["merge"]
    if commit is None:
        return findings + ["MERGE_COMMIT_MISSING"]
    if len(commit.parents) != 2:
        findings.append("MERGE_COMMIT_NOT_TWO_PARENT")
    else:
        if commit.parents[0] != pr["base_sha"]:
            findings.append("MERGE_BASE_PARENT_MISMATCH")
        if commit.parents[1] != pr["head_sha"]:
            findings.append("MERGE_HEAD_PARENT_MISMATCH")
    if tuple(merge["parents"]) != commit.parents:
        findings.append("MERGE_PARENTS_DECLARATION_MISMATCH")
    return findings


@guard("bypass_actor")
def _g_bypass(ctx: dict) -> list[str]:
    claim, policy = ctx["claim"], ctx["policy"]
    if claim["mode"] != "POST_MERGE":
        return []
    if claim["merge"]["merged_by_id"] in policy["bypass_actor_ids"]:
        return ["BYPASS_ACTOR_MERGE"]
    return []


@guard("mode_consistency")
def _g_mode(ctx: dict) -> list[str]:
    requested = ctx["requested_mode"]
    return [] if requested is None or requested == ctx["claim"]["mode"] else ["MODE_CONFLICT"]


@guard("refs_stable")
def _g_stable(ctx: dict) -> list[str]:
    first, second = ctx["snapshot1"], ctx["snapshot2"]
    findings = []
    if first["head_sha"] != second["head_sha"] or first["target_sha"] != second["target_sha"]:
        findings.append("HEAD_OR_BASE_MOVED")
    claim = ctx["claim"]
    expected_target = claim["pr"]["base_sha"] if claim["mode"] == "PRE_MERGE" else claim["merge"]["commit_sha"]
    if second["head_sha"] != claim["pr"]["head_sha"] or second["target_sha"] != expected_target:
        findings.append("REF_MOVED_AFTER_VERIFICATION")
    return findings


def _separate(candidate: Path, verifier_dir: Path, trust_root: Path) -> None:
    if candidate == verifier_dir or verifier_dir.is_relative_to(candidate) or candidate.is_relative_to(verifier_dir):
        raise VerifierError("VERIFIER_INSIDE_CANDIDATE")
    if trust_root.is_relative_to(candidate):
        raise VerifierError("TRUST_ROOT_INSIDE_CANDIDATE")


def _evidence(ctx: dict) -> dict:
    claim, derived = ctx["claim"], ctx["derived"]
    pr = claim["pr"]
    ci = claim["ci"]
    changes = []
    for entry in derived["diff"]:
        changes.append({
            "status": entry.status, "old_path": entry.old_path, "new_path": entry.new_path,
            "old_blob": entry.old_blob, "new_blob": entry.new_blob,
        })
    delta = derived["log_delta"]
    return {
        "repository_id": claim["repository"]["id"],
        "pr_id": pr["id"],
        "pr_number": pr["number"],
        "head_sha": derived["head"].sha,
        "base_sha": derived["base"].sha,
        "head_tree": derived["head"].tree,
        "diff_sha256": _sha256(canonical(changes)),
        "changes": changes,
        "log_prefix_sha256": _sha256(derived["log_base"]) if derived["log_base"] is not None else None,
        "log_appended_sha256": _sha256(delta) if delta is not None else None,
        "log_appended_bytes": len(delta) if delta is not None else None,
        "workflow_source_sha": derived["workflow_blob"],
        "reviewer_ids": sorted({review["author_id"] for review in claim["reviews"]
                                if review["state"] == "APPROVED" and not review["dismissed"]
                                and review["commit_id"] == pr["head_sha"]
                                and review["author_id"] != pr["author_id"]
                                and review["author_login"] != pr["author_login"]}),
        "ci_binding_sha256": _sha256(canonical({
            "repository_id": ci["repository_id"], "run_id": ci["run_id"],
            "run_attempt": ci["run_attempt"], "head_sha": ci["head_sha"],
            "workflow_source_sha": ci["workflow_source_sha"],
            "check_name": ci["check_name"], "app_id": ci["app_id"],
            "pr_id": ci["pr_association"]["pr_id"],
            "pr_number": ci["pr_association"]["pr_number"],
        })),
        "run_id": ci["run_id"],
        "run_attempt": ci["run_attempt"],
        "merge_method": claim["merge"]["method"],
        "policy_sha256": ctx["trust"]["policy_sha256"],
        "verifier_sha256": ctx["trust"]["verifier_sha256"],
    }


def assess(candidate: str | Path, claim: Any, *, trust_root_path: str | Path,
           verifier_dir: str | Path | None = None, requested_mode: str | None = None,
           after_first_read: Callable[[], None] | None = None) -> dict:
    """Verify a candidate claim without authorizing any merge."""
    candidate_path = Path(candidate).resolve()
    verifier_path = Path(verifier_dir) if verifier_dir is not None else Path(__file__).resolve().parent
    trust_path = Path(trust_root_path).resolve()
    try:
        _separate(candidate_path, verifier_path.resolve(), trust_path)
        trust_root = load_trust_root(trust_path)
        trust = verify_trust(verifier_path, trust_root)
        policy = load_policy(verifier_path, trust_root)
    except (VerifierError, TrustError) as exc:
        code = str(exc) if isinstance(exc, VerifierError) else "TRUST_BOUNDARY_INVALID"
        return _hold(code, str(exc) or code, mode=requested_mode)
    except (OSError, ValueError, TypeError) as exc:
        return _hold("TRUST_BOUNDARY_INVALID", type(exc).__name__, mode=requested_mode)

    try:
        validated = validate_claim(claim)
    except (ClaimError, TypeError, ValueError) as exc:
        return _hold("CLAIM_INVALID", str(exc), mode=requested_mode)
    claim = validated["claim"]
    if requested_mode is not None and requested_mode not in MODES:
        return _hold("MODE_INVALID", "requested mode is unsupported", mode=requested_mode)

    try:
        repo = GitRepo(candidate_path)
    except (GitObjectError, OSError, ValueError) as exc:
        return _hold("GIT_OBJECT_ERROR", str(exc), mode=claim["mode"])
    try:
        snapshot1 = _read_snapshot(repo, claim)
        if snapshot1["head_sha"] is None or snapshot1["target_sha"] is None:
            return _hold("REF_MISSING_OR_INVALID", "candidate branch ref is missing", mode=claim["mode"])
        derived = _derive(repo, claim, policy)
    except (GitObjectError, OSError, ValueError, UnicodeError) as exc:
        return _hold("GIT_OBJECT_ERROR", str(exc), mode=claim["mode"])
    if after_first_read is not None:
        after_first_read()
    try:
        snapshot2 = _read_snapshot(repo, claim)
    except GitObjectError as exc:
        return _hold("GIT_OBJECT_ERROR", str(exc), mode=claim["mode"])

    ctx = {
        "claim": claim, "policy": policy, "repo": repo, "trust": trust,
        "snapshot1": snapshot1, "snapshot2": snapshot2, "derived": derived,
        "requested_mode": requested_mode,
    }
    findings: list[str] = []
    for _name, function in GUARDS:
        try:
            produced = function(ctx)
        except (GitObjectError, ValueError, TypeError, KeyError) as exc:
            return _hold("GUARD_INPUT_ERROR", type(exc).__name__, mode=claim["mode"])
        findings.extend(produced or [])
    unique = list(dict.fromkeys(findings))
    evidence = _evidence(ctx)
    if unique:
        return _hold(unique[0], "Pinned policy or Git objects reject the claim.", unique,
                     evidence, claim["mode"])
    return _pass(evidence, claim["mode"])
