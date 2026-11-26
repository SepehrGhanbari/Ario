"""Research-only governance/merge-protection auditor (non-authoritative).

This module evaluates *supplied* synthetic or read-only GitHub metadata. It does
not fetch live data, execute PR code, publish a Check Run, hold credentials, or
merge anything. Even a coherent positive returns ``PASS_PROCESS``; it never
authorizes a merge or establishes trust. The CLI always exits nonzero so the
module cannot be wired in as a GREEN required status check.

Scope of the checks (research hypotheses, not production policy):
  * reviewed-HEAD binding, stale/self approvals and separation of duties;
  * PR-scoped CI provenance (check-run -> PR association, trusted workflow);
  * workflow self-modification and protected-policy path changes;
  * append-only engineering evidence handling;
  * squash/rebase loss of the reviewed HEAD and bypass-actor merges.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "ARIO-GOVERNANCE-MERGE-GUARD-RESEARCH-0.1"
AUTHORITY = "NON_AUTHORITATIVE_RESEARCH_ONLY"
MAX_BYTES = 1_048_576
MAX_FILES = 5000
SHA = re.compile(r"[0-9a-f]{40}\Z")

# Paths whose modification is treated as a governance/policy change by the
# research guard. This is deliberately broader than the merged gate heuristic:
# nested AGENTS.md files, policy/contract docs and the GOVERNANCE/ tree count.
PROTECTED_BASENAMES = frozenset({
    "AGENTS.md", "CODEOWNERS", "SECURITY.md", "CONTRIBUTING.md",
    "REVIEWER_INSTRUCTIONS.md",
})
PROTECTED_PREFIXES = (".github/", "GOVERNANCE/")
PROTECTED_NAME = re.compile(
    r"(^|/)[A-Z0-9_]*(POLICY|CONTRACT|GOVERNANCE|AUTHORIZATION|DELEGATION)[A-Z0-9_]*"
    r"(\.[A-Za-z0-9]+)?\Z"
)
LOG_PATH = "ENGINEERING_LOG.md"
MERGE_METHODS = frozenset({"merge", "squash", "rebase"})
REVIEW_APPROVED = "APPROVED"
REVIEW_CHANGES_REQUESTED = "CHANGES_REQUESTED"

CASE_FIELDS = frozenset({
    "repository", "pr", "pin", "reviews", "checks", "required", "merge_commit",
    "bypass_actors", "log", "protected_paths_extra",
})
PR_FIELDS = frozenset({
    "number", "id", "state", "draft", "merged", "merge_commit_sha", "merge_method",
    "head_sha", "base_sha", "head_branch", "author_login", "author_id",
    "changed_files",
})
PIN_FIELDS = frozenset({"pr_number", "pr_id", "head_sha", "base_sha"})
REQUIRED_FIELDS = frozenset({"check_name", "workflow_path", "app_id", "required_approvals"})
MERGE_FIELDS = frozenset({"sha", "parents", "merged_by_login", "merged_by_id", "method"})
LOG_FIELDS = frozenset({"path", "status", "added", "removed"})


class GuardInputError(ValueError):
    """Supplied evidence cannot be interpreted fail-closed."""


def _hold(reason: str, detail: str, findings: list[str] | None = None,
          protected: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "disposition": "HOLD",
        "reason": reason,
        "detail": detail[:600],
        "findings": list(findings or [reason]),
        "protected_paths": list(protected or []),
        "pr_link_basis": "NOT_ESTABLISHED",
        "merge_authorized": False,
        "trust_activated": False,
        "authority": AUTHORITY,
        "epistemic_limit": (
            "Caller-supplied metadata only. No live GitHub verification, no "
            "reviewer identity, no trusted CI executor and no merge authority."
        ),
    }


def _pass(pr_link_basis: str = "EXPLICIT_LINK") -> dict[str, Any]:
    limit = (
        "Process consistency only. No live GitHub verification, no reviewer "
        "identity, no trusted CI executor and no merge authority."
    )
    if pr_link_basis == "EVENT_AND_BRANCH":
        pr_link_basis = "EVENT_AND_BRANCH_ONLY"
    if pr_link_basis == "EVENT_AND_BRANCH_ONLY":
        limit += (
            " Check-run PR association relied on the pull_request event and head "
            "branch because the GitHub check-run pull_requests field was empty."
        )
    return {
        "schema": SCHEMA,
        "disposition": "PASS_PROCESS",
        "reason": "ALL_SUPPLIED_CHECKS_CONSISTENT",
        "detail": "Supplied metadata passed every research check; this is not authority.",
        "findings": [],
        "protected_paths": [],
        "pr_link_basis": pr_link_basis,
        "merge_authorized": False,
        "trust_activated": False,
        "authority": AUTHORITY,
        "epistemic_limit": limit,
    }


def _positive(value: Any) -> bool:
    return type(value) is int and value > 0


def _sha(value: Any) -> bool:
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def _text(value: Any, cap: int = 300) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= cap


def _obj(value: Any, fields: frozenset[str], name: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise GuardInputError(f"{name} must be an object with exact research fields")
    return value


def _paths(value: Any) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_FILES:
        raise GuardInputError("changed_files must be a bounded list")
    out = []
    for item in value:
        if not _text(item, 512) or "\\" in item or item.startswith("/") or ".." in item.split("/"):
            raise GuardInputError("changed_files entries must be normalized repository paths")
        out.append(item)
    if len(set(out)) != len(out):
        raise GuardInputError("changed_files contains duplicates")
    return out


def protected_paths(paths: list[str], extra: list[str]) -> list[str]:
    """Return the subset of paths this research guard treats as protected policy."""
    protected = []
    for path in paths:
        base = path.rsplit("/", 1)[-1]
        if (base in PROTECTED_BASENAMES
                or path.startswith(PROTECTED_PREFIXES)
                or PROTECTED_NAME.search(path) is not None
                or any(path == item or path.startswith(item.rstrip("/") + "/") for item in extra)):
            protected.append(path)
    return protected


def _validate(case: Any) -> dict:
    case = _obj(case, CASE_FIELDS, "case")
    repo = case["repository"]
    if not isinstance(repo, dict) or not _positive(repo.get("id")) or not _text(repo.get("full_name")):
        raise GuardInputError("repository must carry a positive id and full_name")
    pr = _obj(case["pr"], PR_FIELDS, "pr")
    pin = _obj(case["pin"], PIN_FIELDS, "pin")
    required = _obj(case["required"], REQUIRED_FIELDS, "required")
    for key in ("number", "id", "author_id"):
        if not _positive(pr[key]):
            raise GuardInputError(f"pr.{key} must be a positive integer")
    for key in ("head_sha", "base_sha"):
        if not _sha(pr[key]):
            raise GuardInputError(f"pr.{key} must be a full lowercase SHA")
    if pr["state"] not in {"open", "closed"} or type(pr["draft"]) is not bool or type(pr["merged"]) is not bool:
        raise GuardInputError("pr.state/draft/merged are invalid")
    if not _text(pr["head_branch"], 256) or not _text(pr["author_login"], 100):
        raise GuardInputError("pr head_branch/author_login are invalid")
    if pr["merge_method"] is not None and pr["merge_method"] not in MERGE_METHODS:
        raise GuardInputError("pr.merge_method is not a GitHub merge method")
    if pr["merge_commit_sha"] is not None and not _sha(pr["merge_commit_sha"]):
        raise GuardInputError("pr.merge_commit_sha is invalid")
    changed = _paths(pr["changed_files"])

    for key in ("pr_number", "pr_id"):
        if not _positive(pin[key]):
            raise GuardInputError(f"pin.{key} must be a positive integer")
    for key in ("head_sha", "base_sha"):
        if not _sha(pin[key]):
            raise GuardInputError(f"pin.{key} must be a full lowercase SHA")

    reviews = case["reviews"]
    if not isinstance(reviews, list) or len(reviews) > 500:
        raise GuardInputError("reviews must be a bounded list")
    for review in reviews:
        if not isinstance(review, dict):
            raise GuardInputError("review entries must be objects")
        if not _positive(review.get("id")) or not _text(review.get("state"), 40):
            raise GuardInputError("review id/state are invalid")
        if not _text(review.get("author_login"), 100) or not _positive(review.get("author_id")):
            raise GuardInputError("review author identity is invalid")
        commit = review.get("commit_id")
        if commit is not None and not _sha(commit):
            raise GuardInputError("review commit_id is not a full SHA or null")
        if type(review.get("dismissed")) is not bool:
            raise GuardInputError("review dismissed must be boolean")

    checks = case["checks"]
    if not isinstance(checks, dict) or set(checks) != {"total_count", "hasNextPage", "check_runs"}:
        raise GuardInputError("checks capture must have total_count/hasNextPage/check_runs")
    if type(checks["total_count"]) is not int or checks["total_count"] < 0 or checks["total_count"] > 1000:
        raise GuardInputError("checks.total_count is invalid")
    if type(checks["hasNextPage"]) is not bool:
        raise GuardInputError("checks.hasNextPage must be boolean")
    if not isinstance(checks["check_runs"], list):
        raise GuardInputError("checks.check_runs must be a list")
    for run in checks["check_runs"]:
        if not isinstance(run, dict) or not _positive(run.get("id")) or not _text(run.get("name"), 200):
            raise GuardInputError("check run identity is invalid")
        if not _sha(run.get("head_sha")):
            raise GuardInputError("check run head_sha is invalid")
        if not _positive(run.get("app_id")):
            raise GuardInputError("check run app_id is invalid")
        if not _text(run.get("workflow_path"), 300) or not _positive(run.get("run_id")):
            raise GuardInputError("check run workflow/run identity is invalid")
        if run.get("event") not in {"pull_request", "push", "merge_group"}:
            raise GuardInputError("check run event is invalid")
        if not isinstance(run.get("pull_requests"), list):
            raise GuardInputError("check run pull_requests must be a list")
        for link in run["pull_requests"]:
            if not isinstance(link, dict) or not _positive(link.get("id")) or not _positive(link.get("number")):
                raise GuardInputError("check run PR link is invalid")
        if type(run.get("conclusion")) is not str and run.get("conclusion") is not None:
            raise GuardInputError("check run conclusion is invalid")

    if not _text(required["check_name"], 200) or not _text(required["workflow_path"], 300):
        raise GuardInputError("required check name/workflow are invalid")
    if not _positive(required["app_id"]):
        raise GuardInputError("required.app_id is invalid")
    if type(required["required_approvals"]) is not int or not 0 <= required["required_approvals"] <= 20:
        raise GuardInputError("required.required_approvals is invalid")

    merge = case["merge_commit"]
    if not isinstance(merge, dict) or set(merge) != MERGE_FIELDS:
        raise GuardInputError("merge_commit must have exact research fields")
    if not _sha(merge["sha"]) or not isinstance(merge["parents"], list):
        raise GuardInputError("merge_commit sha/parents are invalid")
    if len(merge["parents"]) > 2 or not all(_sha(parent) for parent in merge["parents"]):
        raise GuardInputError("merge_commit parents must be at most two full SHAs")
    if merge["method"] is not None and merge["method"] not in MERGE_METHODS:
        raise GuardInputError("merge_commit.method is invalid")
    if not _text(merge["merged_by_login"], 100) or not _positive(merge["merged_by_id"]):
        raise GuardInputError("merge_commit merged_by identity is invalid")

    bypass = case["bypass_actors"]
    if not isinstance(bypass, list) or len(bypass) > 100:
        raise GuardInputError("bypass_actors must be a bounded list")
    for actor in bypass:
        if not isinstance(actor, dict) or set(actor) != {"id", "login"}:
            raise GuardInputError("bypass actors must have id/login")
        if not _positive(actor["id"]) or not _text(actor["login"], 100):
            raise GuardInputError("bypass actor identity is invalid")

    log = _obj(case["log"], LOG_FIELDS, "log")
    if log["path"] != LOG_PATH or log["status"] not in {"modified", "deleted", "unchanged"}:
        raise GuardInputError("log must describe ENGINEERING_LOG.md status")
    for key in ("added", "removed"):
        if not isinstance(log[key], list) or len(log[key]) > 20000 or not all(_text(x, 4000) for x in log[key]):
            raise GuardInputError(f"log.{key} must be a bounded list of text lines")
    if case["protected_paths_extra"] is not None:
        _paths(case["protected_paths_extra"])
    return {"case": case, "repo": repo, "pr": pr, "pin": pin, "required": required,
            "reviews": reviews, "checks": checks, "merge": merge, "bypass": bypass,
            "log": log, "changed": changed}


def assess(case: Any) -> dict[str, Any]:
    """Audit supplied merge metadata. Never authorize a merge."""
    try:
        data = _validate(case)
    except GuardInputError as exc:
        return _hold("INVALID_OR_INCOMPLETE_EVIDENCE", str(exc))
    except (KeyError, TypeError, ValueError, RecursionError, OverflowError) as exc:
        return _hold("MALFORMED_EVIDENCE", type(exc).__name__)

    pr, pin, required = data["pr"], data["pin"], data["required"]
    repo, merge, log, changed = data["repo"], data["merge"], data["log"], data["changed"]
    failures: list[str] = []

    if (pin["pr_number"] != pr["number"] or pin["pr_id"] != pr["id"]
            or pin["head_sha"] != pr["head_sha"] or pin["base_sha"] != pr["base_sha"]):
        failures.append("PIN_IDENTITY_MISMATCH")
    if pr["merged"] and pr["merge_commit_sha"] != merge["sha"]:
        failures.append("MERGE_COMMIT_MISMATCH")
    if not pr["merged"] and pr["merge_commit_sha"] is not None:
        failures.append("UNMERGED_PR_WITH_MERGE_COMMIT")

    if required["required_approvals"] < 1:
        failures.append("ZERO_APPROVAL_POLICY")

    approvals = [r for r in data["reviews"]
                 if r["state"] == REVIEW_APPROVED and not r["dismissed"]]
    if any(r["state"] == REVIEW_CHANGES_REQUESTED for r in data["reviews"]):
        failures.append("CHANGES_REQUESTED_PRESENT")
    if any(r["commit_id"] != pr["head_sha"] for r in approvals):
        failures.append("STALE_OR_UNBOUND_APPROVAL")
    if any(r["author_login"] == pr["author_login"] or r["author_id"] == pr["author_id"]
           for r in approvals):
        failures.append("SELF_APPROVAL")
    independent = {(r["author_login"], r["author_id"]) for r in approvals
                   if r["commit_id"] == pr["head_sha"]
                   and r["author_login"] != pr["author_login"]
                   and r["author_id"] != pr["author_id"]}
    if len(independent) < required["required_approvals"]:
        failures.append("INSUFFICIENT_APPROVALS")

    checks = data["checks"]
    if checks["hasNextPage"] or checks["total_count"] != len(checks["check_runs"]):
        failures.append("INCOMPLETE_CHECK_CAPTURE")
    same_name = [run for run in checks["check_runs"] if run["name"] == required["check_name"]]
    if not same_name:
        failures.append("MISSING_REQUIRED_CHECK")
    trusted = []
    for run in same_name:
        problems = []
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            problems.append("REQUIRED_CHECK_NOT_GREEN")
        if run["head_sha"] != pr["head_sha"]:
            problems.append("STALE_CHECK_HEAD")
        if run["app_id"] != required["app_id"]:
            problems.append("UNTRUSTED_CHECK_APP")
        if run["workflow_path"] != required["workflow_path"]:
            problems.append("UNTRUSTED_CHECK_SOURCE")
        if run["event"] != "pull_request":
            problems.append("CHECK_NOT_FROM_PULL_REQUEST_EVENT")
        if run.get("head_branch") != pr["head_branch"]:
            problems.append("CHECK_BRANCH_MISMATCH")
        links = run["pull_requests"]
        association = run.get("association", "EXPLICIT_LINK")
        if association not in {"EXPLICIT_LINK", "EVENT_AND_BRANCH"}:
            problems.append("INVALID_PR_ASSOCIATION_MODE")
        elif links:
            if (len(links) != 1 or links[0]["id"] != pr["id"]
                    or links[0]["number"] != pr["number"]):
                problems.append("CROSS_PR_CHECK_REUSE")
        elif association == "EXPLICIT_LINK":
            problems.append("CROSS_PR_CHECK_REUSE")
        if problems:
            failures.extend(problems)
        else:
            trusted.append((run, association))
    if same_name and len(same_name) > 1 and len(trusted) != 1:
        failures.append("AMBIGUOUS_REQUIRED_CHECK")

    if any(path == required["workflow_path"] or path.startswith(".github/workflows/")
           for path in changed):
        failures.append("WORKFLOW_SELF_MODIFIED")

    protected = protected_paths(changed, data["case"]["protected_paths_extra"] or [])
    if protected:
        failures.append("PROTECTED_POLICY_CHANGE")

    if log["status"] == "deleted":
        failures.append("EVIDENCE_LOG_DELETED")
    elif log["status"] == "modified":
        if log["path"] not in changed:
            failures.append("EVIDENCE_LOG_EVIDENCE_MISMATCH")
        elif log["removed"]:
            failures.append("EVIDENCE_LOG_NOT_APPEND_ONLY")
        elif not log["added"]:
            failures.append("EVIDENCE_LOG_EMPTY_APPEND")
    elif log["path"] in changed:
        failures.append("EVIDENCE_LOG_EVIDENCE_MISMATCH")
    if not changed:
        failures.append("NO_FILE_EVIDENCE")

    if pr["merged"]:
        if merge["method"] not in MERGE_METHODS:
            failures.append("MERGE_METHOD_UNKNOWN")
        elif pr["head_sha"] not in merge["parents"]:
            failures.append("REVIEWED_HEAD_NOT_PRESERVED")
        if any(actor["id"] == merge["merged_by_id"]
               or actor["login"] == merge["merged_by_login"] for actor in data["bypass"]):
            failures.append("BYPASS_ACTOR_MERGE")

    unique = []
    for failure in failures:
        if failure not in unique:
            unique.append(failure)
    if unique:
        result = _hold(unique[0], "One or more research checks failed.", unique, protected)
        return result
    out = _pass(trusted[0][1] if len(trusted) == 1 else "EXPLICIT_LINK")
    out["protected_paths"] = []
    return out


def _read_bounded(path: Path) -> Any:
    if path.is_symlink():
        raise GuardInputError("symlink input refused")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise GuardInputError("input byte limit exceeded")

    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise GuardInputError("duplicate JSON member")
            obj[key] = value
        return obj

    def bad_constant(_):
        raise GuardInputError("nonstandard JSON constant")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                          parse_constant=bad_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, GuardInputError):
            raise
        raise GuardInputError("malformed JSON") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path, help="Caller-supplied merge metadata JSON")
    args = parser.parse_args(argv)
    try:
        result = assess(_read_bounded(args.case))
    except (GuardInputError, OSError, ValueError, TypeError, OverflowError):
        result = _hold("UNREADABLE_OR_INVALID_INPUT", "Bounded JSON input could not be read.")
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 1  # Never a GREEN required gate; research signal only.


if __name__ == "__main__":
    raise SystemExit(main())
