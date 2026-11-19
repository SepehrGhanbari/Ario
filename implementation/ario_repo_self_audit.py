"""Ario's own GitHub PR/check metadata: a read-only, non-authoritative probe."""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import ssl
import urllib.error
import urllib.request
from typing import Any

from pr_claim_audit import Invalid, _decode_json
from pr_ci_github_evidence import links_pr, read_bounded_body

REPOSITORY = "SepehrGhanbari/Ario"
API = "https://api.github.com/repos/" + REPOSITORY
SCHEMA = "ARIO-REPO-SELF-AUDIT-0.1"
SHA = re.compile(r"[0-9a-f]{40}\Z")
ALLOWED = (
    re.compile(r"pulls/[1-9][0-9]*\Z"),
    re.compile(r"commits/[0-9a-f]{40}/check-runs\?per_page=100\Z"),
    re.compile(r"actions/runs\?head_sha=[0-9a-f]{40}&event=pull_request&per_page=100\Z"),
)
LIMITATIONS = [
    "GitHub Actions success is not independently attested test execution",
    "The repository author may also control tests and workflow definitions",
    "Two PR GET samples do not form an atomic or permanent snapshot",
    "This probe does not validate job logs, code quality, truth or merge eligibility",
    "No memory update, M0 evidence admission, real signer, Genesis or trust permission",
]


class ReadUnknown(Exception):
    pass


def _positive(value: Any) -> bool:
    return type(value) is int and value > 0


def _object(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise ReadUnknown("INVALID_" + label)
    return value


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class GitHubReadOnly:
    """Only allow three fixed API GET shapes for the Ario repository."""

    def __init__(self, token: str | None = None):
        self.token = token
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        )

    def get_json(self, url: str) -> dict:
        if not isinstance(url, str) or not url.startswith(API + "/"):
            raise ReadUnknown("FORBIDDEN_HOST")
        path = url[len(API) + 1:]
        if not any(pattern.fullmatch(path) for pattern in ALLOWED):
            raise ReadUnknown("FORBIDDEN_PATH")
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Ario-Repo-Self-Audit-Research",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with self.opener.open(request, timeout=12) as response:
                if response.status != 200:
                    raise ReadUnknown("NON_200_RESPONSE")
                try:
                    data = read_bounded_body(response, 400_000)
                except ValueError as exc:
                    raise ReadUnknown("INCOMPLETE_OR_OVERSIZED_RESPONSE") from exc
        except urllib.error.HTTPError as exc:
            raise ReadUnknown("GITHUB_HTTP_" + str(exc.code)) from exc
        except (OSError, urllib.error.URLError, TimeoutError, http.client.HTTPException) as exc:
            raise ReadUnknown("GITHUB_READ_UNAVAILABLE") from exc
        try:
            return _object(_decode_json(data.decode("utf-8")), "JSON")
        except (Invalid, UnicodeError, ValueError, RecursionError) as exc:
            raise ReadUnknown("INVALID_API_JSON") from exc


def _identity(value: Any, requested_number: int) -> dict:
    pr = _object(value, "PR")
    head = _object(pr.get("head"), "HEAD")
    base = _object(pr.get("base"), "BASE")
    head_sha, base_sha = head.get("sha"), base.get("sha")
    if (not _positive(pr.get("id")) or not _positive(pr.get("number"))
            or pr["number"] != requested_number
            or not isinstance(head_sha, str) or not SHA.fullmatch(head_sha)
            or not isinstance(base_sha, str) or not SHA.fullmatch(base_sha)
            or not isinstance(pr.get("body"), str)
            or type(pr.get("draft")) is not bool
            or pr.get("state") not in ("open", "closed")):
        raise ReadUnknown("INVALID_PR_IDENTITY")
    return {
        "id": pr["id"], "number": pr["number"], "head": head_sha, "base": base_sha,
        "state": pr["state"], "draft": pr["draft"],
        "body_digest": hashlib.sha256(pr["body"].encode("utf-8")).hexdigest(),
    }


def _unknown(reason: str, **extra) -> dict:
    return {
        "schema": SCHEMA, "status": "UNKNOWN", "reason": reason,
        "source_delivery": "GITHUB_API_RESPONSE_UNATTESTED",
        "execution_attestation": "NOT_ESTABLISHED",
        "evidence_admission": "NOT_EVALUATED",
        "merge_authorized": False, "memory_updated": False, "trust_activated": False,
        "limitations": list(LIMITATIONS), **extra,
    }


def observe(pr_number: int, expected_head: str, *,
            repository: str = REPOSITORY, reader: Any = None) -> dict:
    """Two pinned PR reads surrounding bounded, read-only check/run metadata."""
    if (repository != REPOSITORY or not _positive(pr_number)
            or not isinstance(expected_head, str) or not SHA.fullmatch(expected_head)):
        return _unknown("INVALID_FIXED_TARGET")
    result = _unknown("UNASSESSED", expected_head=expected_head)
    try:
        source = reader if reader is not None else GitHubReadOnly()
        url = API + "/pulls/" + str(pr_number)
        first = _identity(source.get_json(url), pr_number)
        result["first_head_observed"] = first["head"]
        if first["head"] != expected_head:
            raise ReadUnknown("PR_HEAD_CHANGED")
        check_obj = _object(
            source.get_json(API + "/commits/" + expected_head + "/check-runs?per_page=100"),
            "CHECKS",
        )
        checks = check_obj.get("check_runs")
        count = check_obj.get("total_count")
        if (type(count) is not int or not 0 <= count <= 100
                or not isinstance(checks, list) or len(checks) != count):
            raise ReadUnknown("CHECKS_INCOMPLETE")
        observed_checks = []
        ids = set()
        for record in checks:
            item = _object(record, "CHECK")
            app = _object(item.get("app"), "APP")
            if (not _positive(item.get("id")) or item["id"] in ids
                    or not isinstance(item.get("name"), str)
                    or item.get("head_sha") != expected_head
                    or not _positive(app.get("id"))
                    or item.get("status") not in ("queued", "in_progress", "completed")
                    or item.get("conclusion") not in (
                        None, "success", "failure", "neutral", "skipped",
                        "cancelled", "timed_out", "action_required", "stale")):
                raise ReadUnknown("INVALID_OR_DUPLICATE_CHECK")
            ids.add(item["id"])
            observed_checks.append({
                "name": item["name"], "status": item["status"],
                "conclusion": item.get("conclusion"), "app_id": app["id"],
            })
        runs_obj = _object(
            source.get_json(API + "/actions/runs?head_sha=" + expected_head
                            + "&event=pull_request&per_page=100"),
            "RUNS",
        )
        runs = runs_obj.get("workflow_runs")
        run_count = runs_obj.get("total_count")
        if (type(run_count) is not int or not 0 <= run_count <= 100
                or not isinstance(runs, list) or len(runs) != run_count):
            raise ReadUnknown("RUNS_INCOMPLETE")
        linked = []
        for record in runs:
            run = _object(record, "RUN")
            if (not _positive(run.get("id")) or not _positive(run.get("run_attempt"))
                    or run.get("head_sha") != expected_head
                    or run.get("event") != "pull_request"
                    or run.get("status") not in ("queued", "in_progress", "completed")):
                raise ReadUnknown("INVALID_RUN")
            if links_pr(run.get("pull_requests"), pr_number, first["id"], expected_head):
                linked.append({
                    "id": run["id"], "attempt": run["run_attempt"],
                    "status": run["status"], "conclusion": run.get("conclusion"),
                })
        last = _identity(source.get_json(url), pr_number)
        if last != first:
            raise ReadUnknown("PR_CHANGED_BETWEEN_SAMPLES")
        result.update({
            "reason": "NON_AUTHORITATIVE_GITHUB_METADATA_READBACK",
            "pr_sample_consistency": "SAME_AT_TWO_SAMPLED_READS",
            "check_count": len(observed_checks),
            "checks": observed_checks,
            "linked_run_count": len(linked),
            "linked_runs": linked,
            "required_check_observation": (
                "REPORTED_SUCCESS_BY_GITHUB_APP"
                if any(c["name"] == "m0-regression"
                       and c["app_id"] == 15368 and c["status"] == "completed"
                       and c["conclusion"] == "success" for c in observed_checks)
                else "NOT_CONFIRMED"
            ),
        })
    except (ReadUnknown, ValueError, TypeError, OSError, UnicodeError,
            OverflowError, RecursionError) as exc:
        result.update({
            "reason": str(exc) if isinstance(exc, ReadUnknown) else "READER_UNAVAILABLE",
            "pr_sample_consistency": "UNKNOWN",
            "required_check_observation": "NOT_CONFIRMED",
        })
        for key in ("checks", "linked_runs", "check_count", "linked_run_count"):
            result.pop(key, None)
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Ario self-audit of real GitHub metadata, read only")
    p.add_argument("--repository", default=REPOSITORY)
    p.add_argument("--pr", type=int, required=True)
    p.add_argument("--expected-head", required=True)
    args = p.parse_args(argv)
    # Validate the fixed target before even allocating a network reader.
    if (args.repository != REPOSITORY or not _positive(args.pr)
            or not SHA.fullmatch(args.expected_head)):
        result = _unknown("INVALID_FIXED_TARGET")
    else:
        try:
            result = observe(args.pr, args.expected_head, reader=GitHubReadOnly(
                os.environ.get("ARIO_GITHUB_READ_TOKEN")))
        except (ReadUnknown, OSError, ValueError, TypeError) as exc:
            result = _unknown("READER_UNAVAILABLE", error_type=type(exc).__name__)
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0  # A successful diagnostic program is not authority or proof.


if __name__ == "__main__":
    raise SystemExit(main())
