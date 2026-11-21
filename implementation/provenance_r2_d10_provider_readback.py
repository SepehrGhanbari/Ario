"""Ario R2 D10: bounded read-only GitHub metadata sampling, no trust admission.

Never converts caller-selected API metadata, HTTPS delivery or CI success into
an independently witnessed execution or evidence source. No imports have I/O.
This research adapter is intentionally not a signer, M0 adapter, or custodian.
"""
from __future__ import annotations

import http.client
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from pr_ci_github_evidence import links_pr, matches_id, read_bounded_body

REPO = "SepehrGhanbari/Ario"
HOST = "api.github.com"
MAX_BYTES = 262144
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
EXPECTED_JOB_NAMES = frozenset(("m0-regression", "windows-differential-advisory"))


@dataclass(frozen=True)
class Target:
    pr_number: int
    run_id: int
    head_sha: str


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class DirectGithubReader:
    """No tokens, fixed GitHub host, GET only, redirects refused, bounded data."""

    def __init__(self, timeout: float = 8):
        if type(timeout) not in (int, float) or not 0 < timeout <= 15:
            raise ValueError("invalid timeout")
        self._timeout = timeout

    def get(self, path: str) -> bytes:
        if type(path) is not str or not re.fullmatch(
                r"/repos/SepehrGhanbari/Ario/(?:pulls/[0-9]{1,10}|actions/runs/[0-9]{1,20}(?:/jobs\?per_page=100)?)",
                path):
            raise ValueError("not a fixed read-only GitHub API resource")
        req = urllib.request.Request(
            "https://" + HOST + path,
            headers={"Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28",
                     "User-Agent": "Ario-R2-D10-readonly-research"},
            method="GET")
        opener = urllib.request.build_opener(_NoRedirect())
        try:
            with opener.open(req, timeout=self._timeout) as response:
                if response.status != 200:
                    raise ValueError("non-200 GitHub response")
                content_type = response.headers.get("Content-Type", "").lower().split(";", 1)[0].strip()
                if content_type not in ("application/json", "application/vnd.github+json"):
                    raise ValueError("response is not JSON")
                return read_bounded_body(response, MAX_BYTES)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                OSError, http.client.HTTPException) as exc:
            raise ValueError("network response unavailable or redirect blocked") from exc


def _decode(raw: bytes) -> dict:
    if type(raw) is not bytes or not raw or len(raw) > MAX_BYTES:
        raise ValueError("missing/oversized response bytes")
    def no_duplicates(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ValueError("duplicate JSON key")
            out[k] = v
        return out
    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates,
                         parse_constant=lambda v: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    except (UnicodeError, RecursionError, OverflowError) as exc:
        raise ValueError("unreadable JSON") from exc
    if type(obj) is not dict:
        raise ValueError("response was not a JSON object")
    return obj


def _id(value: object) -> bool:
    return type(value) is int and value > 0


def _base(reason: str, *, metadata: str = "UNKNOWN", source: str = "NO_COMPLETE_PROVIDER_READBACK") -> dict:
    return {
        "schema": "ARIO-R2-D10-READBACK-V1", "status": "UNKNOWN",
        "metadata_correspondence": metadata, "readback_status": source,
        "reason": reason, "source_control_independence": "NOT_ESTABLISHED",
        "github_transport_authentication": "NOT_ATTESTED_BY_THIS_ADAPTER",
        "artifact_provenance": "NOT_EVALUATED", "pytest_execution_attestation": "NOT_ESTABLISHED",
        "externally_pinned_custodian": "NOT_ESTABLISHED",
        "independently_retained_floor": "NOT_ESTABLISHED", "global_freshness": "NOT_ESTABLISHED",
        "evidence_admission": "NOT_EVALUATED", "claim_truth": "UNKNOWN"}


def audit(target: Target, reader: object) -> dict:
    """Read PR, run, page-one jobs, reread PR. Positive means matching supplied HTTP JSON only."""
    if (type(target) is not Target or not _id(target.pr_number) or target.pr_number > 10000000
            or not _id(target.run_id) or target.run_id > 10**20
            or type(target.head_sha) is not str or not SHA40.fullmatch(target.head_sha)):
        return _base("INVALID_PINNED_TARGET")
    if not callable(getattr(reader, "get", None)):
        return _base("MISSING_READ_ONLY_READER")
    paths = (
        f"/repos/{REPO}/pulls/{target.pr_number}",
        f"/repos/{REPO}/actions/runs/{target.run_id}",
        f"/repos/{REPO}/actions/runs/{target.run_id}/jobs?per_page=100",
        f"/repos/{REPO}/pulls/{target.pr_number}")
    replies = []
    for path in paths:
        try:
            replies.append(_decode(reader.get(path)))
        except (ValueError, TypeError, OSError, TimeoutError, http.client.HTTPException, AttributeError,
                RecursionError, OverflowError) as exc:
            return _base("INCOMPLETE_OR_UNAVAILABLE_READBACK")
    first, run, page, last = replies
    try:
        for p in (first, last):
            if (not matches_id(p.get("number"), target.pr_number) or not _id(p.get("id")) or
                    not isinstance(p.get("head"), dict) or
                    not SHA40.fullmatch(p["head"].get("sha", ""))):
                return _base("INVALID_PR_RESPONSE")
        if first["id"] != last["id"] or first["head"]["sha"] != last["head"]["sha"]:
            return _base("PR_HEAD_CHANGED_DURING_READBACK", source="MULTIPLE_PR_VIEWS_OBSERVED")
        if first["head"]["sha"] != target.head_sha:
            return _base("PR_HEAD_DIFFERS_FROM_PINNED_TARGET", source="COMPLETE_RESPONSE_SAMPLED")
        if (not matches_id(run.get("id"), target.run_id) or run.get("head_sha") != target.head_sha or
                not _id(run.get("workflow_id")) or not _id(run.get("run_attempt")) or
                run.get("event") != "pull_request" or run.get("status") != "completed" or
                run.get("conclusion") != "success"):
            return _base("RUN_METADATA_MISMATCH_OR_NOT_SUCCESS", source="COMPLETE_RESPONSE_SAMPLED")
        if not links_pr(run.get("pull_requests"), target.pr_number, first["id"], target.head_sha):
            return _base("RUN_NOT_LINKED_TO_PINNED_PR", source="COMPLETE_RESPONSE_SAMPLED")
        jobs = page.get("jobs")
        count = page.get("total_count")
        if (type(jobs) is not list or type(count) is not int or
                not 1 <= count <= 100 or len(jobs) != count):
            return _base("PAGINATION_OR_PARTIAL_JOB_LIST", source="COMPLETE_RESPONSE_SAMPLED")
        seen_ids = set()
        seen_names = set()
        for job in jobs:
            if (type(job) is not dict or not _id(job.get("id")) or job["id"] in seen_ids or
                    not matches_id(job.get("run_id"), target.run_id) or
                    not matches_id(job.get("run_attempt"), run["run_attempt"]) or
                    job.get("head_sha") != target.head_sha or
                    job.get("status") != "completed" or job.get("conclusion") != "success" or
                    type(job.get("name")) is not str):
                return _base("JOB_METADATA_MISMATCH_OR_NOT_SUCCESS", source="COMPLETE_RESPONSE_SAMPLED")
            seen_ids.add(job["id"])
            seen_names.add(job["name"])
        if not EXPECTED_JOB_NAMES.issubset(seen_names):
            return _base("REQUIRED_JOBS_NOT_IN_SNAPSHOT", source="COMPLETE_RESPONSE_SAMPLED")
    except (TypeError, ValueError, KeyError, AttributeError):
        return _base("MALFORMED_PROVIDER_METADATA", source="COMPLETE_RESPONSE_SAMPLED")
    return _base("FOUR_HTTP_JSON_SNAPSHOTS_MATCH_PINNED_METADATA_NOT_INDEPENDENT_EXECUTION",
                 metadata="CONSISTENT_CALLER_SUPPLIED_READBACK", source="FOUR_RESPONSE_BYTES_ACCEPTED")


if __name__ == "__main__":
    # No automatic network execution on import. Manual research-only one-shot GET.
    import sys
    if sys.argv[1:] == ["--public-d9-probe"]:
        t = Target(270, 44392429462, "277570d4f26afb4c69f58ec5426aff8b919d58e1")
        print(json.dumps(audit(t, DirectGithubReader()), sort_keys=True))
    else:
        print(json.dumps(_base("NO_LIVE_READ_REQUESTED"), sort_keys=True))
