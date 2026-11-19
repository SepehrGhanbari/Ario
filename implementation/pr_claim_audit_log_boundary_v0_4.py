"""ARIO-PR-CI-0.4: distinguish GitHub log custody from execution attestation.

RESEARCH ONLY. This is a read-only, conservative sidecar over v0.3. It never
promotes a pytest-shaped log into an independently attested test execution.
Even a genuine GitHub TLS response can contain author-controlled log text.
"""
from __future__ import annotations

import argparse
import http.client
import json
import urllib.error
from typing import Any

from pr_ci_github_evidence import matches_id
from pr_claim_audit_github_v0_3 import (
    MAX_JOBS, MAX_PAGES, OriginUnknown, PublicGitHubReader,
    assess_github_pr as assess_v03,
)

SCHEMA = "ARIO-PR-CI-0.4"
VALID_CONCLUSIONS = frozenset({
    "success", "failure", "cancelled", "timed_out", "neutral",
    "skipped", "action_required", "stale",
})
LIMITATIONS = (
    "A GitHub-served log may be generated or spoofed by PR-controlled workflow code",
    "The presence of a pytest command marker and summary is not execution attestation",
    "A single job result is not an overall workflow or code-quality verdict",
    "The extra readback is not an atomic snapshot and cannot prove immutable CI evidence",
    "No signer, required status check, trust activation, merge gate, or production use",
)


def _recheck_run_and_job(reader: Any, owner: str, repo: str,
                         binding: dict[str, Any], observed: dict[str, Any]) -> str:
    """Best-effort consistency readback, NOT a test-execution attestation."""
    api = f"https://api.github.com/repos/{owner}/{repo}"
    rid, attempt, jid = binding["run_id"], binding["run_attempt"], binding["job_id"]
    run = reader.get_json(f"{api}/actions/runs/{rid}")
    if not isinstance(run, dict) or (
        not matches_id(run.get("id"), rid) or not matches_id(run.get("run_attempt"), attempt) or
        run.get("head_sha") != binding["head_sha"] or
        run.get("status") != "completed" or
        run.get("event") != "pull_request" or
        run.get("conclusion") not in VALID_CONCLUSIONS
    ):
        raise OriginUnknown("RUN_CHANGED_OR_UNAVAILABLE_ON_RECHECK")

    jobs_url = f"{api}/actions/runs/{rid}/attempts/{attempt}/jobs"
    jobs: list[Any] = []
    total: int | None = None
    for page in range(1, MAX_PAGES + 1):
        result = reader.get_json(f"{jobs_url}?per_page=100&page={page}")
        if not isinstance(result, dict):
            raise OriginUnknown("JOB_COLLECTION_INVALID_ON_RECHECK")
        count, records = result.get("total_count"), result.get("jobs")
        if type(count) is not int or count < 1 or count > MAX_JOBS or not isinstance(records, list):
            raise OriginUnknown("JOB_COLLECTION_INVALID_ON_RECHECK")
        if total is not None and total != count:
            raise OriginUnknown("JOB_PAGINATION_CHANGED_ON_RECHECK")
        total = count
        jobs.extend(records)
        if len(jobs) >= total:
            break
    if total is None or len(jobs) != total:
        raise OriginUnknown("JOB_PAGINATION_INCOMPLETE_ON_RECHECK")
    if any(not isinstance(j, dict) for j in jobs):
        raise OriginUnknown("JOB_COLLECTION_INVALID_ON_RECHECK")
    ids = [j.get("id") for j in jobs]
    if not all(type(i) is int and i > 0 for i in ids) or len(ids) != len(set(ids)):
        raise OriginUnknown("DUPLICATE_JOBS_ON_RECHECK")
    selected = [j for j in jobs if j["id"] == jid]
    if len(selected) != 1:
        raise OriginUnknown("JOB_CHANGED_OR_MISSING_ON_RECHECK")
    job = selected[0]
    if (not matches_id(job.get("run_id"), rid) or not matches_id(job.get("run_attempt"), attempt) or
            job.get("head_sha") != binding["head_sha"] or
            job.get("status") != "completed" or
            job.get("name") != binding["job_name"] or
            job.get("conclusion") != observed["job_conclusion"]):
        raise OriginUnknown("JOB_CHANGED_OR_MISSING_ON_RECHECK")
    return run["conclusion"]


def assess_github_pr(owner: str, repo: str, pr_number: int, *,
                     reader: Any = None) -> dict[str, Any]:
    """Final UNKNOWN unless future separately reviewed execution attestation exists.

    The v0.3 source correspondence is retained as a diagnostic. An explicitly
    injected reader remains unverified. No caller-set 'attested' field is trusted.
    """
    old = assess_v03(owner, repo, pr_number, reader=reader)
    comparison = old.get("correspondence_status", "UNKNOWN")
    out = {
        **old,
        "schema": SCHEMA,
        "status": "UNKNOWN",
        "reason": ("LOG_EXECUTION_NOT_ATTESTED" if comparison in ("MATCH", "MISMATCH")
                   else old.get("reason", "SOURCE_NOT_ASSESSABLE")),
        "source_transport_status": old.get("origin_status", "UNVERIFIED"),
        "log_execution_attestation": "NOT_ESTABLISHED",
        "workflow_overall_conclusion": "UNKNOWN",
        "scope": "ONE_JOB_ONLY",
        "limitations": list(dict.fromkeys([*old.get("limitations", []), *LIMITATIONS])),
    }
    if comparison not in ("MATCH", "MISMATCH"):
        return out
    binding, observed = old.get("binding"), old.get("observed")
    if not isinstance(binding, dict) or not isinstance(observed, dict):
        out["reason"] = "MISSING_VERIFIABLE_JOB_BINDING"
        out["correspondence_status"] = "UNKNOWN"
        return out
    try:
        check_reader = PublicGitHubReader() if reader is None else reader
        out["workflow_overall_conclusion"] = _recheck_run_and_job(
            check_reader, owner, repo, binding, observed
        )
    except (OriginUnknown, urllib.error.URLError, OSError, http.client.HTTPException, KeyError,
            ValueError, TypeError, OverflowError, RecursionError) as exc:
        out["workflow_overall_conclusion"] = "UNKNOWN"
        out["correspondence_status"] = "UNKNOWN"
        out["reason"] = (str(exc) if isinstance(exc, OriginUnknown)
                         else "RUN_OR_JOB_RECHECK_UNAVAILABLE")
        out["binding"] = None
        out["observed"] = None
        out["differences"] = []
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ario CI v0.4 non-attesting read-only research probe")
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", type=int, required=True)
    args = parser.parse_args(argv)
    result = assess_github_pr(args.owner, args.repo, args.pr)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0  # A successful CLI invocation is not evidentiary approval.


if __name__ == "__main__":
    raise SystemExit(main())
