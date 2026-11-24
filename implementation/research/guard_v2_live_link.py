"""Research-only junction: Ario's live CI observer and the PR-scoped Guard V2 lab.

This cannot post Checks, authorize or perform merges, or establish review freshness.
Caller-supplied review captures may be compared but are NOT GitHub-attested.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any

import ario_repo_self_audit as observer
from research import guard_v2_pr_scope as guard
from research import guard_v2_review_graph as review_graph

SCHEMA = "ARIO-GUARD-V2-LIVE-LINK-LAB-0.1"


def _hold(reason: str, **details: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "UNKNOWN",
        "disposition": "HOLD",
        "reason": reason,
        "merge_authorized": False,
        "check_publish_authorized": False,
        "trust_activated": False,
        "execution_attestation": "NOT_ESTABLISHED",
        "review_freshness": "NOT_ATTESTED_BY_LIVE_GITHUB_READ",
        "ci_sample_freshness": "NOT_CONFIRMED",
        "ci_source_freshness": "NOT_ESTABLISHED",
        "ci_history_continuity": "NOT_ESTABLISHED",
        "source": "LIVE_GITHUB_READ_PLUS_OPTIONAL_CALLER_SUPPLIED_LAB_FIXTURE",
        **details,
    }


def _live_identity(raw: Any, pin: dict) -> dict:
    """Read exact GitHub PR identity, distinguishing numeric IDs from bool/float."""
    if not isinstance(raw, dict):
        raise guard.EvidenceError("INVALID_LIVE_PR")
    identity = observer._identity(raw, pin["pr_number"])
    base = raw.get("base")
    base_repo = base.get("repo") if isinstance(base, dict) else None
    if not isinstance(base_repo, dict) or not guard.positive(base_repo.get("id")):
        raise guard.EvidenceError("INVALID_LIVE_REPOSITORY_ID")
    if (base_repo["id"] != pin["repository_id"]
            or identity["id"] != pin["pr_id"]
            or identity["number"] != pin["pr_number"]):
        raise guard.EvidenceError("LIVE_PR_IDENTITY_MISMATCH")
    if identity["head"] != pin["head_sha"] or identity["base"] != pin["base_sha"]:
        raise guard.EvidenceError("LIVE_PR_REVISION_MISMATCH")
    updated = raw.get("updated_at")
    if not isinstance(updated, str) or not updated:
        raise guard.EvidenceError("LIVE_PR_UPDATED_AT_UNAVAILABLE")
    return {**identity, "repository_id": base_repo["id"], "updated_at": updated}


def examine(pin: dict, *, reader: Any = None, first: dict | None = None,
            last: dict | None = None, checks: dict | None = None,
            review_graph_reader: Any = None) -> dict:
    """Run real read-only observation and one final PR reread; never act on a verdict.

    The before/after Guard review and Check captures are optional lab fixtures,
    NOT obtained by the live observer. Without them, HOLD is mandatory.
    """
    result = _hold("UNASSESSED")
    try:
        guard._validate_pin(pin)
        if not guard.positive(pin["pr_number"]):
            raise guard.EvidenceError("INVALID_PR_NUMBER")
        source = reader if reader is not None else observer.GitHubReadOnly(
            os.environ.get("ARIO_GITHUB_READ_TOKEN"))
        url = observer.API + "/pulls/" + str(pin["pr_number"])
        before = _live_identity(source.get_json(url), pin)
        result["live_pr_id"] = before["id"]
        result["live_pr_head"] = before["head"]
        audit = observer.observe(pin["pr_number"], pin["head_sha"], reader=source)
        if (not isinstance(audit, dict) or audit.get("status") != "UNKNOWN"
                or audit.get("merge_authorized") is not False):
            raise guard.EvidenceError("INVALID_SELF_AUDIT_AUTHORITY")
        result["ci_observation"] = audit.get("required_check_observation", "NOT_CONFIRMED")
        result["self_audit_reason"] = audit.get("reason", "UNKNOWN")
        result["self_audit_pr_sample"] = audit.get("pr_sample_consistency", "UNKNOWN")
        # Preserve the weaker sample-level statement, never infer source freshness
        # or continuity from a successful linked check or caller-supplied data.
        if (audit.get("workflow_freshness") == "SAMPLED_NOT_ATOMIC"
                and audit.get("required_check_observation") == "REPORTED_SUCCESS_BY_LINKED_PR_RUN"):
            result["ci_sample_freshness"] = "SAMPLED_NOT_ATOMIC"
        if review_graph_reader is not None:
            # Complete separately sampled GraphQL review graph. This check
            # detects edits/deletions between two reads even if PR.updated_at
            # never changed. It is NOT an independent or atomic attestation.
            sampled = review_graph.compare_twice(pin, review_graph_reader)
            result["review_graph_reason"] = sampled.get("reason", "UNKNOWN")
            result["review_graph_status"] = sampled.get("sample_status", "UNKNOWN")
            if sampled.get("sample_status") != "SAMPLED_STABLE_UNATTESTED":
                raise guard.EvidenceError("GRAPH_FRESHNESS_" + str(sampled.get("reason", "UNKNOWN")))
            result["review_graph_digest"] = sampled["first_digest"]
            result["review_freshness"] = "SAMPLED_STABLE_UNATTESTED"
        after = _live_identity(source.get_json(url), pin)
        if before != after:
            raise guard.EvidenceError("LIVE_PR_CHANGED_BEFORE_DECISION")
        result["live_pr_consistency"] = "SAME_AT_PRE_AND_POST_READ"
        if before["state"] != "open" or before["draft"] is not False:
            raise guard.EvidenceError("LIVE_PR_NOT_READY")
        if audit.get("pr_sample_consistency") != "SAME_AT_TWO_SAMPLED_READS":
            raise guard.EvidenceError("SELF_AUDIT_SAMPLES_UNCONFIRMED")
        if audit.get("required_check_observation") != "REPORTED_SUCCESS_BY_LINKED_PR_RUN":
            raise guard.EvidenceError("LINKED_PR_CI_NOT_CONFIRMED")
        if first is None or last is None or checks is None:
            raise guard.EvidenceError("REVIEW_AND_APP_EVIDENCE_NOT_CAPTURED")
        verdict = guard.assess(pin, first, last, checks, self_audit=audit)
        result["guard_reason"] = verdict.get("reason", "UNKNOWN")
        if verdict.get("disposition") != "REVIEWABLE_ONLY":
            raise guard.EvidenceError("GUARD_" + str(verdict.get("reason", "HOLD")))
        # A positive here is *not* a live review-evidence attestation: captures
        # remain caller-supplied and a later mutation can still occur.
        result.update(disposition="REVIEWABLE_ONLY",
                      reason="LIVE_PR_AND_SUPPLIED_LAB_METADATA_CORRESPOND")
    except (guard.EvidenceError, observer.ReadUnknown, KeyError, TypeError,
            ValueError, OSError, IndexError, OverflowError, RecursionError) as exc:
        result["disposition"] = "HOLD"
        result["reason"] = (str(exc) if isinstance(exc, (guard.EvidenceError, observer.ReadUnknown))
                            else "LIVE_READER_OR_EVIDENCE_INVALID")
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", type=int, required=True)
    parser.add_argument("--pr-id", type=int, required=True)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-base", required=True)
    args = parser.parse_args(argv)
    # There is no trusted review digest in the GitHub event; a deliberately
    # unmatchable digest ensures that even a live coherent PR cannot be green.
    pin = {"repository_id": args.repo_id, "pr_id": args.pr_id,
           "pr_number": args.pr, "head_sha": args.expected_head,
           "base_sha": args.expected_base, "review_digest": "0" * 64}
    print(json.dumps(examine(pin), sort_keys=True, ensure_ascii=True))
    return 0  # Advisory output only; NEVER a successful security gate.


if __name__ == "__main__":
    raise SystemExit(main())
