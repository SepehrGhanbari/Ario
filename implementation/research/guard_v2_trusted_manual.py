"""Manual, protected-main-only GitHub PR review observer (research, read-only).

Do not execute with a token in a pull_request / PR-checkout workflow.
The *workflow* must provide trusted source provenance; this module cannot
prove that its own bytes or runtime environment are protected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from typing import Any

import ario_repo_self_audit as rest
from research import guard_v2_pr_scope as guard
from research import guard_v2_review_graph as graph

SCHEMA = "ARIO-GUARD-V2-TRUSTED-MANUAL-READ-LAB-0.1"
REPO_URL = "https://api.github.com/repos/SepehrGhanbari/Ario"
SHA = re.compile(r"[a-f0-9]{40}\Z")


def _hold(reason: str, **fields: Any) -> dict[str, Any]:
    return {"schema": SCHEMA, "disposition": "HOLD", "status": "UNKNOWN",
            "reason": reason, "merge_authorized": False,
            "check_publish_authorized": False, "trust_activated": False,
            "execution_attestation": "NOT_ESTABLISHED",
            "independent_custody": "NOT_ESTABLISHED",
            "atomic_merge_attestation": "NOT_ESTABLISHED",
            "source_provenance": "PROVIDED_BY_CALLER_NOT_INDEPENDENTLY_VERIFIED",
            **fields}


def _pr_identity(repo: Any, pr: Any, number: int, head_sha: str) -> dict:
    if not isinstance(repo, dict) or not isinstance(pr, dict):
        raise graph.ReviewGraphUnknown("MALFORMED_REST_REPOSITORY_OR_PR")
    base = pr.get("base")
    base_repo = base.get("repo") if isinstance(base, dict) else None
    sha = pr.get("head")
    if (not guard.positive(repo.get("id")) or not guard.positive(pr.get("id"))
            or type(pr.get("number")) is not int or pr["number"] != number
            or not isinstance(base, dict) or
            not isinstance(base_repo, dict) or
            base_repo.get("id") != repo["id"]
            or not isinstance(sha, dict)
            or sha.get("sha") != head_sha):
        raise graph.ReviewGraphUnknown("REST_PR_IDENTITY_OR_HEAD_MISMATCH")
    base_sha = base.get("sha")
    if (not isinstance(base_sha, str) or SHA.fullmatch(base_sha) is None
            or base.get("ref") != "main"
            or pr.get("state") != "open"
            or type(pr.get("draft")) is not bool):
        raise graph.ReviewGraphUnknown("REST_PR_BASE_OR_STATE_UNEXPECTED")
    updated = pr.get("updated_at")
    body = pr.get("body")
    if not isinstance(updated, str) or not isinstance(body, (str, type(None))):
        raise graph.ReviewGraphUnknown("REST_PR_METADATA_MISSING")
    return {"repository_id": repo["id"], "pr_id": pr["id"],
            "pr_number": pr["number"], "head_sha": sha["sha"],
            "base_sha": base_sha, "draft": pr["draft"],
            "updated_at": updated, "body_hash": hashlib.sha256(
                (body or "").encode("utf-8")).hexdigest()}


def observe(number: int, head_sha: str, *, rest_reader: Any, graph_reader: Any,
            source_sha: str) -> dict:
    out = _hold("UNASSESSED")
    try:
        if (not guard.positive(number) or not isinstance(head_sha, str)
                or SHA.fullmatch(head_sha) is None or
                not isinstance(source_sha, str) or SHA.fullmatch(source_sha) is None):
            raise graph.ReviewGraphUnknown("INVALID_FIXED_TARGET_OR_SOURCE_SHA")
        out["source_commit_sha"] = source_sha  # recorded; not authority
        repository = rest_reader.get_json(REPO_URL)
        pr_url = rest.API + "/pulls/" + str(number)
        before = _pr_identity(repository, rest_reader.get_json(pr_url),
                              number, head_sha)
        pin = {"repository_id": before["repository_id"],
               "pr_id": before["pr_id"], "pr_number": number,
               "head_sha": head_sha, "base_sha": before["base_sha"]}
        comparison = graph.compare_twice(pin, graph_reader)
        out["review_graph_sample"] = comparison.get("sample_status", "UNKNOWN")
        out["review_graph_reason"] = comparison.get("reason", "UNKNOWN")
        out["first_digest"] = comparison.get("first_digest")
        out["second_digest"] = comparison.get("second_digest")
        if comparison.get("sample_status") != "SAMPLED_STABLE_UNATTESTED":
            raise graph.ReviewGraphUnknown("GRAPH_" + str(comparison.get("reason", "UNKNOWN")))
        after = _pr_identity(repository, rest_reader.get_json(pr_url),
                             number, head_sha)
        if before != after:
            raise graph.ReviewGraphUnknown("REST_PR_CHANGED_DURING_GRAPH_READ")
        out["live_identity"] = {"repository_id": before["repository_id"],
                                "pr_id": before["pr_id"],
                                "pr_number": number, "head_sha": head_sha,
                                "base_sha": before["base_sha"]}
        out["review_freshness"] = "TWO_SAMPLED_GRAPHS_MATCH_NON_ATOMIC"
        out["reason"] = ("PR_DRAFT_READ_ONLY_HOLD" if before["draft"]
                         else "LIVE_READ_ONLY_NON_ATOMIC_HOLD")
    except (graph.ReviewGraphUnknown, guard.EvidenceError, rest.ReadUnknown,
            KeyError, TypeError, ValueError, OSError, OverflowError,
            RecursionError) as exc:
        out["reason"] = (str(exc) if isinstance(
            exc, (graph.ReviewGraphUnknown, rest.ReadUnknown))
            else "READER_OR_METADATA_UNAVAILABLE")
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args(argv)
    token = os.environ.get("ARIO_TRUSTED_READ_TOKEN")
    if not token:
        result = _hold("MISSING_READ_ONLY_TOKEN")
    else:
        try:
            result = observe(args.pr, args.expected_head,
                             rest_reader=rest.GitHubReadOnly(token),
                             graph_reader=graph.ReadOnlyGraphQL(token),
                             source_sha=args.source_sha)
        except (graph.ReviewGraphUnknown, rest.ReadUnknown, ValueError,
                OSError, TypeError) as exc:
            result = _hold("TRUSTED_OBSERVER_INITIALIZATION_FAILED",
                           error_type=type(exc).__name__)
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    # Advisory manual run, never an authoritative status check.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
