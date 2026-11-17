"""Ario PR-CI 0.3: bounded read-only GitHub fetch to compare an actual PR claim.

RESEARCH ONLY. GitHub over HTTPS is a *source* distinct from the PR author's
claim, not an external independent custody witness, test-quality verifier, or
merge authority. No credentials, no filesystem writes and no action mutations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from pr_claim_audit import Invalid, assess as assess_snapshot, read_claim

SCHEMA = "ARIO-PR-CI-0.3"
OWNER_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\Z")
REPO_RE = re.compile(r"[A-Za-z0-9_.-]{1,100}\Z")
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
MAX_JSON = 512_000
MAX_LOG = 1_500_000
MAX_JOBS = 500
MAX_PAGES = 5
TIMEOUT = 12
LIMITATIONS = [
    "A GitHub API response over TLS is not an independent custody witness or signed attestation",
    "A passing test is not proof of correct code, scientific truth, security, or merge eligibility",
    "GitHub-hosted workflows and the PR author can share a controlling principal",
    "This experimental tool issues GET requests only; it never comments, approves, signs, or merges",
]


class OriginUnknown(Exception):
    """Missing, ambiguous, untrusted, or unavailable origin evidence."""


def _integer(value: Any) -> bool:
    return type(value) is int and value > 0


def _valid_repo(owner: str, repo: str) -> None:
    if not isinstance(owner, str) or not OWNER_RE.fullmatch(owner):
        raise OriginUnknown("invalid owner")
    if not isinstance(repo, str) or not REPO_RE.fullmatch(repo) or repo in (".", ".."):
        raise OriginUnknown("invalid repository")


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise OriginUnknown("missing/invalid " + name)
    return value


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class PublicGitHubReader:
    """Unauthenticated public GitHub REST reader with bounded requests.

    No Authorization header is ever created or forwarded. Redirects on JSON
    metadata are disallowed. One GitHub-issued log redirect is followed only
    to a known HTTPS Actions artifact host; its bytes are never executed.
    """

    def __init__(self, timeout: int = TIMEOUT):
        self.timeout = timeout
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        )

    def _fetch(self, url: str, cap: int) -> tuple[int, bytes, str | None]:
        if urllib.parse.urlsplit(url).scheme != "https":
            raise OriginUnknown("non-HTTPS transport refused")
        try:
            request = urllib.request.Request(
                url,
                headers={"Accept": "application/vnd.github+json", "User-Agent": "Ario-Research-PR-CI-0.3"},
                method="GET",
            )
            with self.opener.open(request, timeout=self.timeout) as response:
                data = response.read(cap + 1)
                if len(data) > cap:
                    raise OriginUnknown("GitHub response exceeds byte cap")
                return response.status, data, None
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308):
                return exc.code, b"", exc.headers.get("Location")
            raise OriginUnknown("GitHub HTTP error " + str(exc.code)) from exc
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise OriginUnknown("GitHub network response unavailable") from exc

    def get_json(self, url: str) -> dict[str, Any]:
        if urllib.parse.urlsplit(url).hostname != "api.github.com":
            raise OriginUnknown("metadata host is not api.github.com")
        status, data, redirect = self._fetch(url, MAX_JSON)
        if status != 200 or redirect:
            raise OriginUnknown("untrusted API metadata redirect")
        try:
            return _object(json.loads(data.decode("utf-8")), "GitHub response")
        except (ValueError, UnicodeError, RecursionError) as exc:
            raise OriginUnknown("invalid GitHub API JSON") from exc

    @staticmethod
    def _is_actions_log_host(url: str) -> bool:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.username is not None or parsed.password is not None:
            return False
        try:
            if parsed.port not in (None, 443) or not parsed.hostname:
                return False
        except ValueError:
            return False
        host = parsed.hostname.lower()
        return host in (
            "results-receiver.actions.githubusercontent.com",
            "pipelines.actions.githubusercontent.com",
        ) or bool(re.fullmatch(r"productionresultssa\d+\.blob\.core\.windows\.net", host))

    def get_job_log(self, api_log_url: str) -> str:
        if urllib.parse.urlsplit(api_log_url).hostname != "api.github.com":
            raise OriginUnknown("job log endpoint must be GitHub API")
        status, data, redirect = self._fetch(api_log_url, MAX_LOG)
        if status in (301, 302, 303, 307, 308):
            if not redirect or not self._is_actions_log_host(redirect):
                raise OriginUnknown("unexpected GitHub Actions log redirect host")
            status, data, redirect = self._fetch(redirect, MAX_LOG)
        if status != 200 or redirect:
            raise OriginUnknown("incomplete/redirected GitHub Actions job log")
        try:
            return data.decode("utf-8")
        except UnicodeError as exc:
            raise OriginUnknown("job log is not UTF-8") from exc


def _unknown(reason: str, *, correspondence: str = "UNKNOWN") -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "UNKNOWN",
        "reason": reason,
        "correspondence_status": correspondence,
        "origin_status": "UNVERIFIED",
        "origin_basis": None,
        "binding": None,
        "observed": None,
        "differences": [],
        "limitations": list(LIMITATIONS),
    }


def assess_github_pr(owner: str, repo: str, pr_number: int, *,
                     reader: Any = None) -> dict[str, Any]:
    """Fetch one structured claim and its exact run/job/attempt from GitHub.

    *Reader injection is a testing seam, NOT a cryptographic proof of origin.*
    Live use must instantiate PublicGitHubReader, not a user-provided snapshot.
    All failures return UNKNOWN and keep audit status separate from authority.
    """
    try:
        _valid_repo(owner, repo)
        if not _integer(pr_number):
            raise OriginUnknown("invalid PR number")
        injected_reader = reader is not None
        reader = PublicGitHubReader() if reader is None else reader
        api = f"https://api.github.com/repos/{owner}/{repo}"
        pr_url = f"{api}/pulls/{pr_number}"
        pr = _object(reader.get_json(pr_url), "pull request")
        if pr.get("number") != pr_number or not _integer(pr.get("id")):
            raise OriginUnknown("PR identity mismatch")
        pr_id = pr["id"]
        current_head = _object(pr.get("head"), "PR head").get("sha")
        if not isinstance(current_head, str) or not SHA_RE.fullmatch(current_head):
            raise OriginUnknown("invalid PR head")
        body = pr.get("body")
        if not isinstance(body, str):
            raise OriginUnknown("PR body has no structured claim")
        try:
            claim = read_claim(body)
        except (Invalid, ValueError, TypeError, UnicodeError, RecursionError) as exc:
            raise OriginUnknown("PR claim not well-formed or missing") from exc
        if claim["head_sha"] != current_head:
            raise OriginUnknown("claim not attached to current PR head")
        run_id, attempt, job_id = claim["run_id"], claim["run_attempt"], claim["job_id"]
        run_url = f"{api}/actions/runs/{run_id}"
        run = _object(reader.get_json(run_url), "workflow run")
        if run.get("id") != run_id or run.get("run_attempt") != attempt:
            raise OriginUnknown("run/attempt mismatch")
        if run.get("head_sha") != current_head:
            raise OriginUnknown("run commit differs from current PR head")
        if run.get("event") != "pull_request" or run.get("status") != "completed":
            raise OriginUnknown("wrong event or incomplete run")
        linked = run.get("pull_requests")
        if not isinstance(linked, list) or not any(
            isinstance(x, dict) and x.get("number") == pr_number and
            x.get("id") == pr_id and isinstance(x.get("head"), dict) and
            x["head"].get("sha") == current_head
            for x in linked
        ):
            raise OriginUnknown("run is not linked to this exact PR head")
        # GitHub exposes the latest-attempt job list elsewhere. Always ask for
        # jobs of THIS attempt, so rerun jobs cannot be mistaken for prior jobs.
        jobs_url = f"{api}/actions/runs/{run_id}/attempts/{attempt}/jobs"
        jobs: list[dict[str, Any]] = []
        total: int | None = None
        for page in range(1, MAX_PAGES + 1):
            page_obj = _object(reader.get_json(f"{jobs_url}?per_page=100&page={page}"), "attempt jobs")
            count = page_obj.get("total_count")
            page_jobs = page_obj.get("jobs")
            if type(count) is not int or count < 1 or count > MAX_JOBS or not isinstance(page_jobs, list):
                raise OriginUnknown("invalid or excessive job collection")
            if total is not None and total != count:
                raise OriginUnknown("job count changes between pages")
            total = count
            jobs.extend(page_jobs)
            if len(jobs) >= total:
                break
        if total is None or len(jobs) != total:
            raise OriginUnknown("incomplete job pagination")
        ids = [x.get("id") for x in jobs if isinstance(x, dict)]
        if len(ids) != len(set(ids)) or len(ids) != len(jobs):
            raise OriginUnknown("duplicate or invalid job records")
        selected = [x for x in jobs if x.get("id") == job_id]
        if len(selected) != 1:
            raise OriginUnknown("job not in specified run attempt")
        job = _object(selected[0], "job")
        if (job.get("run_id") != run_id or job.get("run_attempt") != attempt or
                job.get("head_sha") != current_head or job.get("status") != "completed"):
            raise OriginUnknown("job/run/attempt/head relation invalid")
        # The log is fetched using the job ID obtained from the attempt-specific
        # GitHub API page; no attacker-supplied log URL is used.
        log = reader.get_job_log(f"{api}/actions/jobs/{job_id}/logs")
        if not isinstance(log, str) or not log:
            raise OriginUnknown("missing job log")
        # Recheck PR head after bounded retrieval: if it moved, no stale MATCH.
        second = _object(reader.get_json(pr_url), "PR head recheck")
        if (_object(second.get("head"), "new PR head").get("sha") != current_head
                or second.get("body") != body):
            raise OriginUnknown("PR head moved during evidence retrieval")
        evidence = {
            "run": run,
            "job": job,
            "job_log": log,
            "job_log_sha256": hashlib.sha256(log.encode("utf-8")).hexdigest(),
            "job_log_complete": True,  # Transport read to EOF under hard cap.
        }
        compared = assess_snapshot(body, evidence)
        if compared["status"] not in ("MATCH", "MISMATCH"):
            raise OriginUnknown("fetched log is not assessable: " + compared["reason"])
        # An injected test reader is NOT an authenticated GitHub transport.
        # Only an internally instantiated HTTPS reader can promote diagnostic
        # correspondence to a scoped final status. Unit mocks do not attest it.
        actual_transport = not injected_reader
        return {
            "schema": SCHEMA,
            "status": compared["status"] if actual_transport else "UNKNOWN",
            "reason": ("CORRESPONDENCE_WITH_GITHUB_API_EVIDENCE" if actual_transport
                       else "INJECTED_READER_ORIGIN_UNVERIFIED"),
            "correspondence_status": compared["status"],
            "origin_status": "GITHUB_API_TLS_FETCHED" if actual_transport else "UNVERIFIED",
            "origin_basis": "TLS_GITHUB_API" if actual_transport else "INJECTED_READER_ONLY",
            "binding": {**compared["binding"], "repo": f"{owner}/{repo}", "pr_number": pr_number},
            "observed": compared["observed"],
            "differences": compared["differences"],
            "limitations": list(LIMITATIONS),
        }
    except (OriginUnknown, Invalid, ValueError, TypeError, UnicodeError, OverflowError, RecursionError, KeyError) as exc:
        return _unknown(str(exc) if isinstance(exc, OriginUnknown) else "malformed source evidence")
    except (OSError, urllib.error.URLError) as exc:
        return _unknown("GitHub read unavailable")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Read-only Ario PR claim comparison against GitHub API")
    p.add_argument("--owner", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--pr", type=int, required=True)
    args = p.parse_args(argv)
    result = assess_github_pr(args.owner, args.repo, args.pr)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0  # CLI exit status never grants merge or evidentiary authority.


if __name__ == "__main__":
    raise SystemExit(main())
