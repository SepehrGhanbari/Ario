#!/usr/bin/env python3
"""Fail-closed, read-only repository PR review evidence gate (not evidence admission).

This checks *process metadata*, not code correctness, consciousness, real-world
provenance or authorization to activate an Ario runtime.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import html
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MARKER = "ARIO_REVIEW_EVIDENCE_V1"
# Verified via GitHub REST /users/coderabbitai%5Bbot%5D on 2026-11-05.
# ID, login AND account type are required together, never alternatives.
BOT_USER_ID = 136622811
BOT_LOGIN = "coderabbitai[bot]"
WORKFLOW_PATH = ".github/workflows/implementation-regression.yml"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MAX_ITEMS = 100


class GateError(Exception):
    """A reason to block the PR rather than assume a positive decision."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise GateError(code)


def _strict_record_object(pairs: list[tuple[str, object]]) -> dict:
    """Reject ambiguous JSON object members, including identical duplicates."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise GateError("DUPLICATE_REVIEW_RECORD_FIELD")
        result[key] = value
    return result


def parse_record(body: str) -> dict:
    require(isinstance(body, str), "MISSING_PR_BODY")
    # Reject every marker-like opener, including malformed or incomplete
    # duplicates; counting only full regex matches would hide a corrupt
    # second block after one otherwise valid record.
    # Treat ANY V1-prefixed opener as ambiguous, including newline after <!--.
    # This deliberately fails closed on quoted/comment-like false positives.
    starts = re.findall(r"<!--\s*" + re.escape(MARKER), body)
    require(len(starts) == 1, "REVIEW_RECORD_ABSENT_OR_AMBIGUOUS")
    pattern = r"<!--[ \t]*" + MARKER + r"[ \t]*\r?\n(.*?)\r?\n-->"
    blocks = re.findall(pattern, body, flags=re.DOTALL)
    require(len(blocks) == 1, "REVIEW_RECORD_ABSENT_OR_AMBIGUOUS")
    try:
        data = json.loads(blocks[0], object_pairs_hook=_strict_record_object)
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


# This tiny allowlist does NOT establish semantic source-change authorization.
ROUTINE_PATHS = frozenset({
    "implementation/witness_provenance_experiment.py",
    "implementation/tests/test_witness_provenance_experiment.py",
})


def protected_path(path: str) -> bool:
    """Default-deny noncanonical or unknown Git paths."""
    if not isinstance(path, str) or not path or len(path) > 256:
        return True
    if ("\\" in path or "\x00" in path or path.startswith("/")
            or any(p in ("", ".", "..") for p in path.split("/"))):
        return True
    return path != "ENGINEERING_LOG.md" and path not in ROUTINE_PATHS


def validate_log_append_only(original: bytes, proposed: bytes) -> None:
    require(type(original) is bytes and type(proposed) is bytes,
            "LOG_BYTES_NOT_VERIFIED")
    require(len(original) > 0 and len(proposed) > len(original),
            "LOG_NOT_APPENDED")
    require(original.endswith(b"\n") and proposed.startswith(original),
            "LOG_HISTORICAL_PREFIX_CHANGED")


def independent_bot(user: dict, author_id: int) -> bool:
    return (type(user.get("id")) is int and user["id"] == BOT_USER_ID
            and user.get("login") == BOT_LOGIN and user.get("type") == "Bot"
            and user["id"] != author_id)


def reports_blocker(body: str) -> bool:
    # CodeRabbit can put <picture> artwork inside a bold severity label.
    visible = re.sub(r"<[^>]*>", "", html.unescape(body))
    return bool(re.search(r"(?:\*\*|alt=[\"'])\s*(?:Major|Critical)\b",
                          body + "\n" + visible, flags=re.IGNORECASE))


def validate_run_binding(pr: dict, run: dict) -> None:
    require(run.get("event") == "pull_request" and run.get("status") == "completed",
            "RUN_NOT_COMPLETED_PR_EVENT")
    number = pr.get("number")
    head_repo = (pr.get("head", {}).get("repo") or {}).get("id")
    base_repo = (pr.get("base", {}).get("repo") or {}).get("id")
    require(type(number) is int and type(head_repo) is int and
            type(base_repo) is int and head_repo > 0 and base_repo > 0,
            "PR_REPOSITORY_IDENTITY_UNKNOWN")
    associations = run.get("pull_requests")
    require(isinstance(associations, list) and any(
        p.get("number") == number and
        p.get("head", {}).get("ref") == pr.get("head", {}).get("ref") and
        (p.get("head", {}).get("repo") or {}).get("id") == head_repo and
        p.get("base", {}).get("ref") == "main" and
        (p.get("base", {}).get("repo") or {}).get("id") == base_repo
        for p in associations), "RUN_NOT_ASSOCIATED_WITH_INTENDED_PR")
    # The association's head.sha is live PR metadata, not the historical
    # run revision. The run's head_sha and checkout parents bind that instead.


def validate_candidate(pr: dict, record: dict, files: list[dict],
                       reviews: list[dict], threads: list[dict],
                       runs: dict[int, dict], comments: list[dict] | None = None) -> list[str]:
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
    require(all(f.get("status") == "modified" and
                "previous_filename" not in f for f in files),
            "RENAME_DELETE_OR_UNKNOWN_FILE_OPERATION")

    author_id = (pr.get("user") or {}).get("id")
    require(type(author_id) is int and author_id > 0, "PR_AUTHOR_IDENTITY_UNKNOWN")
    matching = [
        review for review in reviews
        if independent_bot(review.get("user") or {}, author_id)
        and review.get("state") in ("COMMENTED", "APPROVED")
        and review.get("commit_id") == head
    ]
    require(bool(matching), "NO_FRESH_INDEPENDENT_BOT_REVIEW_OF_HEAD")
    # A review body can be edited without changing submitted_at. Checking
    # only the newest review permits an edited older Major to be overlooked.
    # Fail closed while ANY exact-head independent review contains a blocker.
    for review in matching:
        review_text = review.get("body") or ""
        require(isinstance(review_text, str) and not reports_blocker(review_text),
                "INDEPENDENT_REVIEW_REPORTS_MAJOR_OR_CRITICAL")
    for comment in comments or []:
        commit = comment.get("commit_id")
        require(isinstance(commit, str) and SHA_RE.fullmatch(commit) and
                isinstance(comment.get("body"), str), "INLINE_COMMENT_EVIDENCE_UNKNOWN")
        if independent_bot(comment.get("user") or {}, author_id) and reports_blocker(comment["body"]):
            # A stale commit and a resolved thread do not prove remediation.
            # No independently attributable disposition contract exists yet.
            if commit != head:
                raise GateError("STALE_BLOCKING_INLINE_COMMENT_UNDISPOSED")
            raise GateError("INDEPENDENT_INLINE_REVIEW_REPORTS_MAJOR_OR_CRITICAL")
    require(not any(review.get("state") == "CHANGES_REQUESTED" for review in reviews),
            "CHANGES_REQUESTED_REVIEW_PRESENT")
    require(len(threads) < MAX_ITEMS, "REVIEW_THREADS_NOT_EXHAUSTIVELY_CHECKED")
    require(not any(not t.get("isResolved", False) for t in threads),
            "UNRESOLVED_REVIEW_THREAD")

    for red_id in record["red_run_ids"]:
        run = runs.get(red_id)
        require(isinstance(run, dict) and run.get("conclusion") == "failure",
                "RED_RUN_NOT_FAILED_OR_UNVERIFIED")
        validate_run_binding(pr, run)
        require(run.get("name") == "Implementation Regression",
                "RED_NOT_IMPLEMENTATION_REGRESSION")
        require(run.get("head_branch") == pr.get("head", {}).get("ref"),
                "RED_RUN_FROM_OTHER_BRANCH")
        require(isinstance(run.get("head_sha"), str) and
                SHA_RE.fullmatch(run["head_sha"]) and
                run["head_sha"] != head, "RED_IS_NOT_PRIOR_COMMIT")
        require((run.get("head_repository") or {}).get("full_name") ==
                (pr.get("head", {}).get("repo") or {}).get("full_name") and
                bool((pr.get("head", {}).get("repo") or {}).get("full_name")),
                "RED_RUN_FROM_UNRELATED_HEAD_REPOSITORY")
    green = runs.get(record["green_run_id"])
    require(isinstance(green, dict) and green.get("conclusion") == "success",
            "GREEN_RUN_NOT_SUCCESSFUL_OR_UNVERIFIED")
    validate_run_binding(pr, green)
    require(green.get("name") == "Implementation Regression"
            and green.get("head_sha") == head, "GREEN_NOT_CURRENT_HEAD")
    require(green.get("head_branch") == pr.get("head", {}).get("ref"),
            "GREEN_RUN_FROM_OTHER_BRANCH")
    require((green.get("head_repository") or {}).get("full_name") ==
            (pr.get("head", {}).get("repo") or {}).get("full_name") and
            bool((pr.get("head", {}).get("repo") or {}).get("full_name")),
            "GREEN_WRONG_HEAD_REPOSITORY")
    jobs = green.get("jobs")
    require(isinstance(jobs, list) and any(
        job.get("name") == "m0-regression" and job.get("conclusion") == "success" and
        any(step.get("name") == "Run M0 and runtime regression suites" and
            step.get("conclusion") == "success" for step in (job.get("steps") or []))
        for job in jobs), "GREEN_REQUIRED_REGRESSION_JOB_NOT_VERIFIED")
    return [
        "GATE_PASS: scope is ROUTINE_LAB, PR metadata bound to current HEAD",
        "GATE_PASS: declared RED/GREEN runs checked against GitHub Actions",
        "GATE_PASS: fresh distinct CodeRabbit review and no unresolved threads found",
        "GATE_LIMIT: recorded review is COMMENTED, not a GitHub APPROVED review",
        "GATE_LIMIT: machine checks cannot verify that RED failure proves a specific defect",
        "GATE_LIMIT: workflow/checkout/log observations do not independently attest test execution",
        "GATE_LIMIT: in-process evidence recheck is NOT_MERGE_ATOMIC; later changes remain possible",
    ]


def api_request(path: str, *, method: str = "GET", payload: dict | None = None,
                raw: bool = False) -> object:
    token = os.environ.get("GITHUB_TOKEN", "")
    require(bool(token), "GITHUB_TOKEN_MISSING")
    endpoint = "https://api.github.com" + path
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ario-review-evidence-gate-v1",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(endpoint, headers=headers, method=method, data=data)
    # Job logs redirect to signed storage URLs. Authenticate the GitHub request
    # without forwarding its bearer header to the redirected download host.
    request.add_unredirected_header("Authorization", "Bearer " + token)
    try:
        with urlopen(request, timeout=15) as response:
            if raw:
                data = response.read(5_000_001)
                require(len(data) <= 5_000_000, "JOB_LOG_OVERSIZED")
                return data.decode("utf-8")
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise GateError("GITHUB_API_UNAVAILABLE_OR_INVALID_RESPONSE") from exc


def graphql_threads(owner: str, name: str, number: int) -> list[dict]:
    query = """query($owner:String!, $name:String!, $number:Int!) {
      repository(owner:$owner,name:$name) {
        pullRequest(number:$number) {
          reviewThreads(first:100) {
            nodes { id isResolved isOutdated }
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


def fetch_verified_file_bytes(repo: str, commit_sha: str, path: str,
                              label: str = "WORKFLOW") -> bytes:
    """Read commit-addressed bytes; reject missing/oversized/unverified Git blobs."""
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha),
            "COMMIT_SHA_INVALID")
    info = api_request(f"/repos/{repo}/contents/{path}?ref={commit_sha}")
    require(isinstance(info, dict) and info.get("type") == "file" and
            info.get("encoding") == "base64" and type(info.get("size")) is int and
            0 < info["size"] <= 2_000_000, label + "_CONTENT_UNVERIFIED")
    try:
        payload = base64.b64decode(info["content"].replace("\n", ""), validate=True)
    except (KeyError, AttributeError, binascii.Error, ValueError) as exc:
        raise GateError(label + "_CONTENT_MALFORMED") from exc
    require(len(payload) == info["size"], label + "_SIZE_MISMATCH")
    calc = hashlib.sha1(b"blob " + str(len(payload)).encode("ascii")
                        + b"\0" + payload).hexdigest()
    require(calc == info.get("sha"), label + "_BLOB_IDENTITY_MISMATCH")
    return payload


def fetch_log_bytes(repo: str, commit_sha: str) -> bytes:
    return fetch_verified_file_bytes(repo, commit_sha, "ENGINEERING_LOG.md", "LOG")


def validate_execution(repo: str, pr: dict, run: dict, jobs: list[dict],
                       outcome: str, trusted_workflow: bytes) -> None:
    """Constrain observed source/checkout/test execution, not semantic truth.

    Logs are GitHub observations, not independent producer attestation. Unknown
    or noncanonical execution stays HOLD; no candidate code is executed here.
    """
    require(fetch_verified_file_bytes(repo, run["head_sha"], WORKFLOW_PATH) ==
            trusted_workflow, "RUN_WORKFLOW_SOURCE_CHANGED")
    regression_jobs = [job for job in jobs if job.get("name") == "m0-regression"]
    require(len(regression_jobs) == 1, "REGRESSION_JOB_AMBIGUOUS")
    job = regression_jobs[0]
    require(type(job.get("id")) is int and job["id"] > 0 and
            job.get("status") == "completed" and job.get("run_id") == run.get("id") and
            job.get("run_attempt") == run.get("run_attempt") and
            job.get("head_sha") == run.get("head_sha"), "JOB_RUN_ATTEMPT_MISMATCH")
    logs = api_request(f"/repos/{repo}/actions/jobs/{job['id']}/logs", raw=True)
    require(isinstance(logs, str) and 0 < len(logs) <= 5_000_000, "JOB_LOG_UNKNOWN")
    logs = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", logs.replace("\r\n", "\n"))
    logs = re.sub(r"(?m)^\d{4}-\d\d-\d\dT[0-9:.]+Z ", "", logs)
    segments = logs.split("##[group]Run python -m pytest -q tests\n")
    require(len(segments) == 2, "PYTEST_COMMAND_NOT_OBSERVED")
    checkout = re.findall(r"(?m)^\[command\]\S*git log -1 --format=%H\n([0-9a-f]{40})$",
                          segments[0])
    require(len(checkout) == 1, "CHECKOUT_REVISION_UNKNOWN")
    commit = api_request(f"/repos/{repo}/git/commits/{checkout[0]}")
    parents = commit.get("parents") if isinstance(commit, dict) else None
    require(isinstance(parents, list) and len(parents) == 2 and
            commit.get("sha") == checkout[0] and
            parents[1].get("sha") == run["head_sha"], "CHECKOUT_NOT_RUN_HEAD_MERGE")
    executed_base = parents[0].get("sha")
    base_sha = pr.get("base", {}).get("sha")
    require(isinstance(executed_base, str) and SHA_RE.fullmatch(executed_base),
            "CHECKOUT_BASE_UNKNOWN")
    if outcome == "success":
        require(executed_base == base_sha, "GREEN_CHECKOUT_NOT_CURRENT_BASE")
    if executed_base != base_sha:
        comparison = api_request(f"/repos/{repo}/compare/{executed_base}...{base_sha}")
        require(isinstance(comparison, dict) and comparison.get("status") == "ahead" and
                (comparison.get("merge_base_commit") or {}).get("sha") == executed_base,
                "CHECKOUT_BASE_NOT_VERIFIED_ANCESTOR")
    require(fetch_verified_file_bytes(repo, checkout[0], WORKFLOW_PATH) == trusted_workflow,
            "EXECUTED_WORKFLOW_SOURCE_CHANGED")
    summaries = [line for line in segments[1].splitlines()
                 if re.search(r"\bin \d+(?:\.\d+)?s\b", line) and
                 re.search(r"\b\d+ (?:passed|failed|errors?)\b", line)]
    require(len(summaries) == 1, "PYTEST_EXECUTION_SUMMARY_UNKNOWN")
    counts = {kind.rstrip("s"): int(count) for count, kind in
              re.findall(r"\b(\d+) (passed|failed|errors?)\b", summaries[0])}
    require(counts.get("error", 0) == 0 and
            (counts.get("failed", 0) > 0 if outcome == "failure" else
             counts.get("passed", 0) > 0 and counts.get("failed", 0) == 0),
            "NONZERO_TEST_EXECUTION_NOT_VERIFIED")


def pr_binding(pr: dict) -> dict:
    """Compare stable decision-critical values, not volatile repository stats."""
    def branch_identity(branch: object) -> dict:
        ref = branch if isinstance(branch, dict) else {}
        repo = ref.get("repo") if isinstance(ref.get("repo"), dict) else {}
        return {"ref": ref.get("ref"), "sha": ref.get("sha"),
                "repo": {"id": repo.get("id"), "full_name": repo.get("full_name")}}

    user = pr.get("user") if isinstance(pr.get("user"), dict) else {}
    return {"number": pr.get("number"), "state": pr.get("state"),
            "draft": pr.get("draft"), "body": pr.get("body"),
            "user": {"id": user.get("id"), "login": user.get("login"),
                     "type": user.get("type")},
            "head": branch_identity(pr.get("head")),
            "base": branch_identity(pr.get("base"))}


def regular_modes_at_commit(repo: str, commit_sha: str) -> dict[str, str]:
    """Fetch canonical tree modes, refusing truncated or ambiguous metadata."""
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha),
            "TREE_COMMIT_SHA_UNKNOWN")
    c = api_request(f"/repos/{repo}/git/commits/{commit_sha}")
    tree_sha = (c.get("tree") or {}).get("sha") if isinstance(c, dict) else None
    require(isinstance(tree_sha, str) and SHA_RE.fullmatch(tree_sha),
            "TREE_SHA_UNKNOWN")
    tree = api_request(f"/repos/{repo}/git/trees/{tree_sha}?recursive=1")
    require(isinstance(tree, dict) and tree.get("truncated") is False and
            isinstance(tree.get("tree"), list) and len(tree["tree"]) < 10000,
            "TREE_TRUNCATED_OR_OVERSIZED")
    return {x["path"]: x["mode"] for x in tree["tree"]
            if isinstance(x, dict) and x.get("type") == "blob"
            and isinstance(x.get("path"), str) and isinstance(x.get("mode"), str)}


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
        number = event.get("number") or (event.get("pull_request") or {}).get("number")
        require(type(number) is int and number > 0, "PR_NUMBER_UNKNOWN")
        # A deleted inline comment can disappear before the FIRST API read.
        # A deletion-triggered run must therefore HOLD from its own event,
        # regardless of the later (possibly matching) API snapshots.
        if event.get("action") == "deleted":
            require(os.environ.get("GITHUB_EVENT_NAME") == "pull_request_review_comment",
                    "DELETION_EVENT_SOURCE_UNVERIFIED")
            evt_repo = event.get("repository")
            evt_pr = event.get("pull_request")
            require(isinstance(evt_repo, dict) and
                    evt_repo.get("full_name") == repo and
                    type(evt_repo.get("id")) is int and evt_repo["id"] > 0 and
                    isinstance(evt_pr, dict) and
                    type(evt_pr.get("number")) is int and
                    evt_pr["number"] == number,
                    "DELETION_EVENT_IDENTITY_UNVERIFIED")
            raise GateError("INLINE_REVIEW_COMMENT_DELETED_EVENT")
        base = "/repos/" + repo
        pr = api_request(f"{base}/pulls/{number}")
        record = parse_record(pr.get("body") or "")
        files = fetch_limited(f"{base}/pulls/{number}/files")
        reviews = fetch_limited(f"{base}/pulls/{number}/reviews")
        threads = graphql_threads(owner, name, number)
        comments = fetch_limited(f"{base}/pulls/{number}/comments")
        base_sha = pr.get("base", {}).get("sha", "")
        head_sha = pr.get("head", {}).get("sha", "")
        validate_log_append_only(fetch_log_bytes(repo, base_sha),
                                 fetch_log_bytes(repo, head_sha))
        base_modes = regular_modes_at_commit(repo, base_sha)
        head_modes = regular_modes_at_commit(repo, head_sha)
        require(all(base_modes.get(x.get("filename")) == "100644" and
                    head_modes.get(x.get("filename")) == "100644" for x in files),
                "NONREGULAR_OR_UNKNOWN_FILE_MODE")
        expected_flow = api_request(f"{base}/actions/workflows/implementation-regression.yml")
        require(isinstance(expected_flow, dict) and
                type(expected_flow.get("id")) is int and
                expected_flow.get("path") == WORKFLOW_PATH,
                "REGRESSION_WORKFLOW_IDENTITY_UNKNOWN")
        trusted_workflow = fetch_verified_file_bytes(repo, base_sha, WORKFLOW_PATH)
        runs = {}
        run_snapshots = {}
        for run_id in record["red_run_ids"] + [record["green_run_id"]]:
            run = api_request(f"{base}/actions/runs/{run_id}")
            require(isinstance(run, dict) and
                    run.get("workflow_id") == expected_flow["id"] and
                    run.get("path") == expected_flow["path"],
                    "UNEXPECTED_WORKFLOW_PRODUCER")
            validate_run_binding(pr, run)
            attempt = run.get("run_attempt")
            require(run.get("id") == run_id and type(attempt) is int and attempt > 0,
                    "RUN_ATTEMPT_UNKNOWN")
            run_snapshots[run_id] = dict(run)
            job_data = api_request(
                f"{base}/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100")
            require(isinstance(job_data, dict) and
                    isinstance(job_data.get("jobs"), list) and
                    type(job_data.get("total_count")) is int and
                    0 < job_data["total_count"] < MAX_ITEMS and
                    len(job_data["jobs"]) == job_data["total_count"],
                    "INCOMPLETE_JOB_EVIDENCE")
            outcome = "failure" if run_id in record["red_run_ids"] else "success"
            require(any(
                job.get("name") == "m0-regression" and
                job.get("conclusion") == outcome and
                any(step.get("name") == "Run M0 and runtime regression suites" and
                    step.get("conclusion") == outcome for step in
                    (job.get("steps") or []))
                for job in job_data["jobs"]),
                "REGRESSION_STEP_NOT_EXECUTED_AS_CLAIMED")
            require((run.get("repository") or {}).get("full_name") == repo,
                    "CROSS_REPOSITORY_CI_RUN")
            if run_id in record["red_run_ids"]:
                red_sha = run.get("head_sha")
                require(isinstance(red_sha, str) and SHA_RE.fullmatch(red_sha)
                        and red_sha != head_sha, "RED_NOT_PRIOR_HEAD")
                comparison = api_request(f"{base}/compare/{red_sha}...{head_sha}")
                require(isinstance(comparison, dict) and
                        comparison.get("status") == "ahead" and
                        (comparison.get("merge_base_commit") or {}).get("sha") == red_sha,
                        "RED_NOT_VERIFIED_ANCESTOR")
            validate_execution(repo, pr, run, job_data["jobs"], outcome, trusted_workflow)
            run["jobs"] = job_data["jobs"]
            runs[run_id] = run
        validate_candidate(pr, record, files, reviews, threads, runs, comments)
        # Re-fetch mutable evidence at the decision boundary. Equality invalidates
        # deletions and edits as well as newly observed blockers. This narrows the
        # audit window; the separate API reads and eventual merge are NOT atomic.
        latest = api_request(f"{base}/pulls/{number}")
        latest_record = parse_record(latest.get("body") or "")
        latest_reviews = fetch_limited(f"{base}/pulls/{number}/reviews")
        latest_threads = graphql_threads(owner, name, number)
        latest_comments = fetch_limited(f"{base}/pulls/{number}/comments")
        require(pr_binding(latest) == pr_binding(pr) and latest_record == record and
                latest_reviews == reviews and latest_threads == threads and
                latest_comments == comments, "MUTABLE_PR_EVIDENCE_CHANGED_DURING_AUDIT")
        for run_id, snapshot in run_snapshots.items():
            require(api_request(f"{base}/actions/runs/{run_id}") == snapshot,
                    "RUN_CHANGED_DURING_AUDIT")
        findings = validate_candidate(latest, latest_record, files, latest_reviews,
                                      latest_threads, runs, latest_comments)
        require(pr_binding(api_request(f"{base}/pulls/{number}")) == pr_binding(latest),
                "PR_CHANGED_DURING_BOUNDARY_RECHECK")
        for finding in findings:
            print(finding)
        print("GATE_RESULT=PASS_PROCESS_EVIDENCE_ONLY_NO_MERGE_AUTHORITY")
        return 0
    except (GateError, OSError, TypeError, RecursionError) as exc:
        code = str(exc) if isinstance(exc, GateError) else type(exc).__name__
        print("GATE_RESULT=HOLD", code, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
