#!/usr/bin/env python3
"""Fail-closed, read-only repository PR review evidence gate (not evidence admission).

This checks *process metadata*, not code correctness, consciousness, real-world
provenance or authorization to activate an Ario runtime.
"""
from __future__ import annotations

import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MARKER = "ARIO_REVIEW_EVIDENCE_V1"
BOT_NAMES = frozenset({"coderabbitai", "coderabbitai[bot]"})
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MAX_ITEMS = 100


class GateError(Exception):
    """A reason to block the PR rather than assume a positive decision."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise GateError(code)


def parse_record(body: str) -> dict:
    require(isinstance(body, str), "MISSING_PR_BODY")
    pattern = r"<!--[ \t]*" + MARKER + r"[ \t]*\n(.*?)\n-->"
    blocks = re.findall(pattern, body, flags=re.DOTALL)
    require(len(blocks) == 1, "REVIEW_RECORD_ABSENT_OR_AMBIGUOUS")
    try:
        data = json.loads(blocks[0])
    except (ValueError, RecursionError) as exc:
        raise GateError("MALFORMED_REVIEW_RECORD") from exc
    require(isinstance(data, dict), "REVIEW_RECORD_NOT_OBJECT")
    required = {
        "version", "reviewed_head_sha", "scope", "files",
        "red_run_ids", "green_run_id", "red_failure",
        "risk_disposition", "limitations",
    }
    require(set(data) == required, "REVIEW_RECORD_SCHEMA_MISMATCH")
    require(data["version"] == 1 and data["scope"] == "ROUTINE_LAB",
            "NOT_ELIGIBLE_FOR_ROUTINE_GATE")
    require(isinstance(data["reviewed_head_sha"], str) and
            bool(SHA_RE.fullmatch(data["reviewed_head_sha"])), "INVALID_REVIEWED_SHA")
    require(isinstance(data["files"], list) and len(data["files"]) in range(2, 21)
            and all(isinstance(f, str) and f and len(f) <= 256 for f in data["files"])
            and len(set(data["files"])) == len(data["files"]), "INVALID_FILES")
    require(isinstance(data["red_run_ids"], list) and
            1 <= len(data["red_run_ids"]) <= 12 and
            all(type(v) is int and v > 0 for v in data["red_run_ids"]) and
            len(set(data["red_run_ids"])) == len(data["red_run_ids"]), "INVALID_RED_RUNS")
    require(type(data["green_run_id"]) is int and data["green_run_id"] > 0,
            "INVALID_GREEN_RUN")
    require(data["green_run_id"] not in data["red_run_ids"], "RED_GREEN_RUN_COLLISION")
    for k in ("red_failure", "limitations"):
        require(isinstance(data[k], str) and 24 <= len(data[k]) <= 3000,
                "INSUFFICIENT_" + k.upper())
    require(data["risk_disposition"] == "NO_KNOWN_BLOCKERS",
            "BLOCKING_OR_UNRESOLVED_RISK_DISPOSITION")
    return data


def protected_path(path: str) -> bool:
    if path == "ENGINEERING_LOG.md":
        return False
    if not path.startswith("implementation/"):
        return True
    lower = path.lower()
    protected_markers = (
        "owner_signer", "genesis", "trust_anchor", "authorization",
        "admission", "memory_engine", "continuity", "self_model",
        "identity_contract", "governance", "secret", "credential",
    )
    return any(token in lower for token in protected_markers)


def validate_candidate(pr: dict, record: dict, files: list[dict],
                       reviews: list[dict], threads: list[dict],
                       runs: dict[int, dict]) -> list[str]:
    """Evaluate already-fetched public repository metadata deterministically."""
    require(pr.get("state") == "open" and not pr.get("draft"),
            "PR_NOT_OPEN_AND_READY")
    require(pr.get("base", {}).get("ref") == "main", "WRONG_BASE_BRANCH")
    head = pr.get("head", {}).get("sha")
    require(head == record["reviewed_head_sha"], "STALE_REVIEW_RECORD_SHA")

    actual = [f.get("filename") for f in files]
    require(actual and len(actual) < MAX_ITEMS and all(isinstance(p, str) for p in actual),
            "UNKNOWN_OR_OVERSIZED_DIFF")
    require(set(actual) == set(record["files"]) and len(actual) == len(record["files"]),
            "PR_DIFF_NOT_EQUAL_TO_REVIEW_RECORD")
    require("ENGINEERING_LOG.md" in actual, "APPEND_ONLY_LOG_MISSING")
    require(not any(protected_path(p) for p in actual),
            "PROTECTED_GOVERNANCE_OR_AUTHORITY_PATH")

    author = (pr.get("user") or {}).get("login", "").lower()
    matching = [
        review for review in reviews
        if (review.get("user") or {}).get("login", "").lower() in BOT_NAMES
        and (review.get("user") or {}).get("login", "").lower() != author
        and review.get("state") in ("COMMENTED", "APPROVED")
        and review.get("commit_id") == head
    ]
    require(bool(matching), "NO_FRESH_INDEPENDENT_BOT_REVIEW_OF_HEAD")
    require(not any(review.get("state") == "CHANGES_REQUESTED" for review in reviews),
            "CHANGES_REQUESTED_REVIEW_PRESENT")
    require(len(threads) < MAX_ITEMS, "REVIEW_THREADS_NOT_EXHAUSTIVELY_CHECKED")
    require(not any(not t.get("isResolved", False) for t in threads),
            "UNRESOLVED_REVIEW_THREAD")

    for red_id in record["red_run_ids"]:
        run = runs.get(red_id)
        require(isinstance(run, dict) and run.get("conclusion") == "failure",
                "RED_RUN_NOT_FAILED_OR_UNVERIFIED")
        require(run.get("name") == "Implementation Regression",
                "RED_NOT_IMPLEMENTATION_REGRESSION")
    green = runs.get(record["green_run_id"])
    require(isinstance(green, dict) and green.get("conclusion") == "success",
            "GREEN_RUN_NOT_SUCCESSFUL_OR_UNVERIFIED")
    require(green.get("name") == "Implementation Regression"
            and green.get("head_sha") == head, "GREEN_NOT_CURRENT_HEAD")
    return [
        "GATE_PASS: scope is ROUTINE_LAB, PR metadata bound to current HEAD",
        "GATE_PASS: declared RED/GREEN runs checked against GitHub Actions",
        "GATE_PASS: fresh distinct CodeRabbit review and no unresolved threads found",
        "GATE_LIMIT: recorded review is COMMENTED, not a GitHub APPROVED review",
        "GATE_LIMIT: machine checks cannot verify that RED failure proves a specific defect",
    ]


def api_request(path: str, *, method: str = "GET", payload: dict | None = None) -> object:
    token = os.environ.get("GITHUB_TOKEN", "")
    require(bool(token), "GITHUB_TOKEN_MISSING")
    endpoint = "https://api.github.com" + path
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ario-review-evidence-gate-v1",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    try:
        with urlopen(Request(endpoint, headers=headers, method=method, data=data),
                     timeout=15) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise GateError("GITHUB_API_UNAVAILABLE_OR_INVALID_RESPONSE") from exc


def graphql_threads(owner: str, name: str, number: int) -> list[dict]:
    query = """query($owner:String!, $name:String!, $number:Int!) {
      repository(owner:$owner,name:$name) {
        pullRequest(number:$number) {
          reviewThreads(first:100) {
            nodes { isResolved }
            pageInfo { hasNextPage }
          }
        }
      }
    }"""
    response = api_request("/graphql", method="POST", payload={
        "query": query,
        "variables": {"owner": owner, "name": name, "number": number},
    })
    require(isinstance(response, dict) and not response.get("errors"),
            "REVIEW_THREADS_QUERY_ERROR")
    try:
        collection = response["data"]["repository"]["pullRequest"]["reviewThreads"]
        require(not collection["pageInfo"]["hasNextPage"], "REVIEW_THREADS_OVER_100")
        return collection["nodes"]
    except (KeyError, TypeError) as exc:
        raise GateError("UNVERIFIED_REVIEW_THREADS") from exc


def fetch_limited(path: str) -> list[dict]:
    data = api_request(path + "?per_page=100")
    require(isinstance(data, list) and len(data) < MAX_ITEMS,
            "PAGINATION_LIMIT_EXCEEDED")
    return data


def main() -> int:
    try:
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) is not None,
                "INVALID_REPOSITORY")
        owner, name = repo.split("/")
        event_path = os.environ.get("GITHUB_EVENT_PATH", "")
        require(bool(event_path), "EVENT_NOT_AVAILABLE")
        with open(event_path, encoding="utf-8") as handle:
            event = json.load(handle)
        number = event.get("number")
        require(type(number) is int and number > 0, "PR_NUMBER_UNKNOWN")
        base = "/repos/" + repo
        pr = api_request(f"{base}/pulls/{number}")
        record = parse_record(pr.get("body") or "")
        files = fetch_limited(f"{base}/pulls/{number}/files")
        reviews = fetch_limited(f"{base}/pulls/{number}/reviews")
        threads = graphql_threads(owner, name, number)
        run_ids = set(record["red_run_ids"] + [record["green_run_id"]])
        runs = {run_id: api_request(f"{base}/actions/runs/{run_id}")
                for run_id in run_ids}
        require(all((run.get("repository") or {}).get("full_name") == repo
                    for run in runs.values()), "CROSS_REPOSITORY_CI_RUN")
        for finding in validate_candidate(pr, record, files, reviews, threads, runs):
            print(finding)
        print("GATE_RESULT=PASS_PROCESS_EVIDENCE_ONLY")
        return 0
    except (GateError, OSError, TypeError, RecursionError) as exc:
        code = str(exc) if isinstance(exc, GateError) else type(exc).__name__
        print("GATE_RESULT=HOLD", code, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
