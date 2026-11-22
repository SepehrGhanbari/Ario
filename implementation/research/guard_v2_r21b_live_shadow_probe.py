"""R21B live shadow probe: V1 and V2 from SAME bounded GraphQL pages.

Runs only in a fixed research-branch push GitHub Actions workflow with an
ephemeral GITHUB_TOKEN set to READ permissions. No mutation, no historical
ledger write, no publication of identity/author/body or token. Output always
reports HOLD; job exits nonzero for incomplete observations.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import ario_repo_self_audit as rest
from research import guard_v2_r21b_shadow_reader as shadow

REPO = "SepehrGhanbari/Ario"
SCHEMA = "ARIO-GUARD-V2-R21B-LIVE-SHADOW-READ-LAB-0.1"
TARGETS = (183, 295)


def summarize(number: int, result: dict) -> dict:
    v1 = result.get("v1")
    v2 = result.get("v2")
    v1 = v1 if type(v1) is dict else {}
    v2 = v2 if type(v2) is dict else {}
    return {
        "pr": number,
        "status": "UNKNOWN", "disposition": "HOLD",
        "merge_authorized": False, "trust_activated": False,
        "source_provenance": "EPHEMERAL_ACTIONS_SELF_REPORTED_NOT_INDEPENDENT",
        "shadow_reason": result.get("reason"),
        "v1_status": v1.get("sample_status", "UNKNOWN"),
        "v1_reason": v1.get("reason", "NOT_ESTABLISHED"),
        "v1_first_digest": v1.get("first_digest"),
        "v1_second_digest": v1.get("second_digest"),
        "v2_reason": v2.get("reason", "NOT_ESTABLISHED"),
        "v2_first_digest": v2.get("first_attribution_digest"),
        "v2_second_digest": v2.get("second_attribution_digest"),
        "network_page_count": result.get("recorded_page_count", 0),
        "historical_truth": "NOT_ESTABLISHED",
        "independent_custody": "NOT_ESTABLISHED",
    }


def live_pin(number: int, reader: Any) -> dict:
    repo = reader.get_json(rest.API)
    pr = reader.get_json(rest.API + "/pulls/" + str(number))
    # No fallback or caller-invented head/base. Strict type checks here;
    # the graph reader binds all subsequent pages to these identities.
    rid, pid = repo.get("id"), pr.get("id")
    head = pr.get("head")
    base = pr.get("base")
    if not (type(rid) is int and rid > 0 and type(pid) is int and pid > 0
            and type(pr.get("number")) is int and pr["number"] == number
            and type(head) is dict and type(base) is dict):
        raise ValueError("MALFORMED_REST_TARGET")
    if type(head.get("sha")) is not str or type(base.get("sha")) is not str:
        raise ValueError("MALFORMED_REST_REVISION")
    return {
        "repository_id": rid, "pr_id": pid, "pr_number": number,
        "head_sha": head["sha"], "base_sha": base["sha"],
    }


def main() -> int:
    if (os.getenv("GITHUB_REPOSITORY") != REPO or
        os.getenv("GITHUB_REF") !=
            "refs/heads/research/r21b-shadow-reader-v1-v2-20261122"):
        print("ARIO_R21B_LIVE_SHADOW " + json.dumps({
            "schema": SCHEMA, "status": "INVALID_RUN_CONTEXT_HOLD",
            "disposition": "HOLD", "merge_authorized": False,
        }))
        return 2
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("ARIO_R21B_LIVE_SHADOW " + json.dumps({
            "schema": SCHEMA, "status": "NO_EPHEMERAL_TOKEN_HOLD",
            "disposition": "HOLD", "merge_authorized": False,
        }))
        return 2
    results = []
    # Each target uses separate read-only transports, never publishes raw
    # review data. Errors are reduced to a fixed diagnostic label.
    for number in TARGETS:
        try:
            rest_reader = rest.GitHubReadOnly(token)
            pin = live_pin(number, rest_reader)
            graphql_reader = shadow.ReadOnlyGraphQLB(token)
            result = shadow.compare_shadow(pin, graphql_reader)
            results.append(summarize(number, result))
        except (ValueError, TypeError, KeyError, OSError, OverflowError,
                RecursionError):
            results.append({
                "pr": number, "status": "UNKNOWN", "disposition": "HOLD",
                "merge_authorized": False,
                "reason": "READ_OR_REVISION_UNAVAILABLE",
            })
    completed = all(
        r.get("v1_status") == "SAMPLED_STABLE_UNATTESTED" and
        r.get("v2_reason") == "B_SAMPLES_EQUAL_NONATTESTED"
        for r in results
    )
    out = {
        "schema": SCHEMA,
        "disposition": "HOLD", "status": "UNKNOWN",
        "merge_authorized": False, "check_publish_authorized": False,
        "trust_activated": False, "execution_attestation": "NOT_ESTABLISHED",
        "independent_custody": "NOT_ESTABLISHED",
        "historical_truth": "NOT_ESTABLISHED",
        "research_observation": "TWO_COMPLETE_NONATTESTED" if completed
                                else "INCOMPLETE_OR_CHANGED_HOLD",
        "results": results,
    }
    # Output includes only statuses, reasons, counts, and hashes; never names,
    # Node IDs, review contents or token material.
    print("ARIO_R21B_LIVE_SHADOW " + json.dumps(out, sort_keys=True))
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fp:
            fp.write("### R21B V1/V2 read-only shadow experiment\n\n")
            fp.write("HOLD — " + out["research_observation"] + "\n\n")
            fp.write(json.dumps(out, sort_keys=True, indent=2) + "\n")
    return 0 if completed else 2


if __name__ == "__main__":
    sys.exit(main())
