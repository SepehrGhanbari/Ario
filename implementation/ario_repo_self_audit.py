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
CANONICAL_WORKFLOW_ID = 379498305
CANONICAL_WORKFLOW_PATH = ".github/workflows/implementation-regression.yml"
CANONICAL_JOB_NAME = "m0-regression"
ACTIONS_APP_ID = 15368
SHA = re.compile(r"[0-9a-f]{40}\Z")
# GitHub check-run details URLs bind the named job to its actual workflow run.
# A push check with the same name is NOT evidence of a PR job.
CHECK_JOB = re.compile(
    r"https://github[.]com/SepehrGhanbari/Ario/actions/runs/"
    r"([1-9][0-9]*)/job/([1-9][0-9]*)\Z"
)
# GitHub's REST API advertises pagination with Web Linking (RFC 8288).
# Do not look for rel=next in raw URL, title or unrelated relation names.
LINK_TOKEN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+")


def _link_has_next(values: list[str]) -> bool:
    """Parse bounded RFC 8288 Link fields without dereferencing their URLs.

    Reject malformed/ambiguous headers rather than treating them as proof of a
    complete response. This is a conservative subset of Web Linking syntax.
    """
    if len(values) > 8 or sum(len(s) for s in values if isinstance(s, str)) > 8192:
        raise ValueError("oversized Link headers")
    found_next = False
    for value in values:
        if not isinstance(value, str) or not value or any(
            (ord(ch) < 32 and ch != "\t") or ord(ch) > 126 for ch in value
        ):
            raise ValueError("invalid Link header bytes")
        if not value.strip():
            raise ValueError("empty Link header")
        pos, n = 0, len(value)
        while pos < n:
            while pos < n and value[pos] in " \t":
                pos += 1
            if pos == n:
                break
            if value[pos] != "<":
                raise ValueError("missing Link target")
            close = value.find(">", pos + 1)
            if close < 0 or "<" in value[pos + 1:close]:
                raise ValueError("invalid Link target")
            pos = close + 1
            rel = None
            while True:
                while pos < n and value[pos] in " \t":
                    pos += 1
                if pos == n or value[pos] == ",":
                    break
                if value[pos] != ";":
                    raise ValueError("invalid Link parameter delimiter")
                pos += 1
                while pos < n and value[pos] in " \t":
                    pos += 1
                match = LINK_TOKEN.match(value, pos)
                if match is None:
                    raise ValueError("missing Link parameter name")
                key = match.group().lower()
                pos = match.end()
                while pos < n and value[pos] in " \t":
                    pos += 1
                param = None
                if pos < n and value[pos] == "=":
                    pos += 1
                    while pos < n and value[pos] in " \t":
                        pos += 1
                    if pos < n and value[pos] == '"':
                        pos += 1
                        chars = []
                        while pos < n and value[pos] != '"':
                            if value[pos] == "\\":
                                pos += 1
                                if pos == n:
                                    raise ValueError("incomplete quoted Link escape")
                            chars.append(value[pos])
                            pos += 1
                        if pos == n:
                            raise ValueError("unclosed Link quoted-string")
                        pos += 1
                        param = "".join(chars)
                    else:
                        match = LINK_TOKEN.match(value, pos)
                        if match is None:
                            raise ValueError("invalid Link parameter value")
                        param = match.group()
                        pos = match.end()
                if key == "rel":
                    if rel is not None or not param:
                        raise ValueError("missing or repeated Link rel")
                    rel = param
            if rel is None:
                raise ValueError("Link without rel")
            relations = rel.split()
            if not relations or any("," in item or ";" in item for item in relations):
                raise ValueError("invalid Link relation list")
            if any(item.lower() == "next" for item in relations):
                found_next = True
            if pos < n:
                pos += 1  # comma: next link-value
                if not value[pos:].strip():
                    raise ValueError("trailing Link delimiter")
    return found_next

ALLOWED = (
    re.compile(r"pulls/[1-9][0-9]*\Z"),
    re.compile(r"commits/[0-9a-f]{40}/check-runs\?per_page=100\Z"),
    re.compile(r"actions/runs\?head_sha=[0-9a-f]{40}&event=pull_request&per_page=100\Z"),
    re.compile(r"actions/runs/[1-9][0-9]*/attempts/[1-9][0-9]*/jobs\?per_page=100\Z"),
)
LIMITATIONS = [
    "GitHub Actions success is not independently attested test execution",
    "Check Runs use GitHub default latest filtering, not a historical inventory",
    "Reported check and linked-run records are initial samples, not full attempt history",
    "The repository author may also control tests and workflow definitions",
    "Two PR GET samples and repeated metadata reads do not form an atomic or permanent snapshot",
    "A PR revision or workflow rerun after its last relevant sample remains unobservable",
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
    """Allow exact repository metadata GET plus four fixed subpath GET shapes."""

    def __init__(self, token: str | None = None):
        self.token = token
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        )

    def get_json(self, url: str) -> dict:
        if not isinstance(url, str) or (url != API and not url.startswith(API + "/")):
            raise ReadUnknown("FORBIDDEN_HOST")
        # Only the exact root API URL is allowed for repository numeric ID.
        # Reject /, query parameters, fragments, sibling repositories and
        # any unrecognized nested path; retain the original narrow allowlist.
        if url != API:
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
                    has_next = _link_has_next(response.headers.get_all("Link", []))
                except ValueError as exc:
                    raise ReadUnknown("PAGINATION_LINK_INVALID") from exc
                if has_next:
                    raise ReadUnknown("PAGINATION_NEXT_LINK_PRESENT")
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



def _check_snapshot(value: Any, expected_head: str, target_run_id: int,
                    target_check_id: int, label: str) -> tuple:
    """Project checks for the selected canonical run onto binding fields."""
    obj = _object(value, label)
    records = obj.get("check_runs")
    count = obj.get("total_count")
    if (type(count) is not int or not 0 <= count <= 100
            or not isinstance(records, list) or len(records) != count):
        raise ReadUnknown(label + "_INCOMPLETE")
    ids = set()
    relevant = []
    for record in records:
        item = _object(record, "CHECK_RECHECK")
        app = _object(item.get("app"), "APP_RECHECK")
        details = item.get("details_url")
        if (not _positive(item.get("id")) or item["id"] in ids
                or not isinstance(item.get("name"), str)
                or item.get("head_sha") != expected_head
                or not _positive(app.get("id"))
                or item.get("status") not in ("queued", "in_progress", "completed")
                or item.get("conclusion") not in (
                    None, "success", "failure", "neutral", "skipped",
                    "cancelled", "timed_out", "action_required", "stale")
                or (item["status"] == "completed")
                   != (item.get("conclusion") is not None)
                or (details is not None and not isinstance(details, str))):
            raise ReadUnknown("INVALID_OR_DUPLICATE_CHECK")
        ids.add(item["id"])
        if item["name"] == CANONICAL_JOB_NAME and app["id"] == ACTIONS_APP_ID:
            match = CHECK_JOB.fullmatch(details) if isinstance(details, str) else None
            points_to_target_run = (
                match is not None and int(match.group(1)) == target_run_id
            )
            if item["id"] == target_check_id or points_to_target_run:
                relevant.append((
                    item["id"], item["name"], item["head_sha"], app["id"],
                    item["status"], item.get("conclusion"), details,
                ))
    # Old-attempt canonical checks and unrelated checks do not affect the
    # selected latest run. Order and presentation-only fields are excluded.
    return tuple(sorted(relevant))


def _run_snapshot(value: Any, expected_head: str, pr_number: int,
                  pr_id: int, label: str) -> tuple:
    """Project sampled canonical PR-linked runs onto their binding fields."""
    obj = _object(value, label)
    records = obj.get("workflow_runs")
    count = obj.get("total_count")
    if (type(count) is not int or not 0 <= count <= 100
            or not isinstance(records, list) or len(records) != count):
        raise ReadUnknown(label + "_INCOMPLETE")
    run_ids = set()
    workflow_sequences = set()
    canonical_runs = []
    for record in records:
        run = _object(record, "RUN_RECHECK")
        if (not _positive(run.get("id")) or not _positive(run.get("run_attempt"))
                or not _positive(run.get("workflow_id"))
                or not _positive(run.get("run_number"))
                or not isinstance(run.get("path"), str) or not run["path"]
                or run.get("head_sha") != expected_head
                or run.get("event") != "pull_request"
                or run["id"] in run_ids
                or run.get("status") not in ("queued", "in_progress", "completed")
                or run.get("conclusion") not in (
                    None, "success", "failure", "neutral", "skipped", "cancelled",
                    "timed_out", "action_required", "stale", "startup_failure")
                or (run["status"] == "completed")
                   != (run.get("conclusion") is not None)):
            raise ReadUnknown("INVALID_RUN")
        run_ids.add(run["id"])
        sequence = (run["workflow_id"], run["run_number"])
        if sequence in workflow_sequences:
            raise ReadUnknown("DUPLICATE_WORKFLOW_RUN_NUMBER")
        workflow_sequences.add(sequence)

        pr_links = run.get("pull_requests")
        if not isinstance(pr_links, list) or not pr_links:
            raise ReadUnknown("RUN_PR_ASSOCIATION_INCOMPLETE")
        link_view = []
        for link in pr_links:
            item = _object(link, "RUN_PR_LINK")
            link_head = _object(item.get("head"), "RUN_PR_HEAD")
            if (not _positive(item.get("id")) or not _positive(item.get("number"))
                    or not isinstance(link_head.get("sha"), str)
                    or not SHA.fullmatch(link_head["sha"])):
                raise ReadUnknown("INVALID_RUN_PR_ASSOCIATION")
            if item["number"] == pr_number or item["id"] == pr_id:
                if (item["number"] != pr_number or item["id"] != pr_id
                        or link_head["sha"] != expected_head):
                    raise ReadUnknown("RUN_PR_ASSOCIATION_MISMATCH")
            link_view.append((item["id"], item["number"], link_head["sha"]))

        if (run["workflow_id"] == CANONICAL_WORKFLOW_ID
                and links_pr(pr_links, pr_number, pr_id, expected_head)):
            candidate = (
                run["id"], run["workflow_id"], run["path"], run["run_number"],
                run["run_attempt"], run["head_sha"], run["event"],
                run["status"], run.get("conclusion"), tuple(sorted(link_view)),
            )
            canonical_runs.append(candidate)
    # Keep current-run selection separate from sampled-set consistency.
    # An observed change to an older canonical PR-linked run invalidates the
    # observation too; stable historical failures do not override the current run.
    # This is not a complete attempt history or an atomic snapshot.
    return tuple(sorted(canonical_runs))

def observe(pr_number: int, expected_head: str, *,
            repository: str = REPOSITORY, reader: Any = None) -> dict:
    """Two pinned PR reads plus a final run-list sample; non-atomic and read-only."""
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
        checks_url = API + "/commits/" + expected_head + "/check-runs?per_page=100"
        check_obj = _object(source.get_json(checks_url), "CHECKS")
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
                        "cancelled", "timed_out", "action_required", "stale")
                    or (item["status"] == "completed")
                       != (item.get("conclusion") is not None)):
                raise ReadUnknown("INVALID_OR_DUPLICATE_CHECK")
            ids.add(item["id"])
            details = item.get("details_url")
            if details is not None and not isinstance(details, str):
                raise ReadUnknown("INVALID_OR_DUPLICATE_CHECK")
            observed_checks.append({
                "id": item["id"], "name": item["name"], "status": item["status"],
                "conclusion": item.get("conclusion"), "app_id": app["id"],
                "details_url": details,
            })
        runs_url = (API + "/actions/runs?head_sha=" + expected_head
                     + "&event=pull_request&per_page=100")
        runs_obj = _object(source.get_json(runs_url), "RUNS")
        runs = runs_obj.get("workflow_runs")
        run_count = runs_obj.get("total_count")
        if (type(run_count) is not int or not 0 <= run_count <= 100
                or not isinstance(runs, list) or len(runs) != run_count):
            raise ReadUnknown("RUNS_INCOMPLETE")
        linked = []
        run_ids = set()
        workflow_run_numbers = set()
        for record in runs:
            run = _object(record, "RUN")
            if (not _positive(run.get("id")) or not _positive(run.get("run_attempt"))
                    or not _positive(run.get("workflow_id"))
                    or not _positive(run.get("run_number"))
                    or not isinstance(run.get("path"), str) or not run["path"]
                    or run.get("head_sha") != expected_head
                    or run.get("event") != "pull_request"
                    or run["id"] in run_ids
                    or run.get("status") not in ("queued", "in_progress", "completed")
                    or run.get("conclusion") not in (
                        None, "success", "failure", "neutral", "skipped", "cancelled",
                        "timed_out", "action_required", "stale", "startup_failure")
                    or (run["status"] == "completed")
                       != (run.get("conclusion") is not None)):
                raise ReadUnknown("INVALID_RUN")
            run_ids.add(run["id"])
            pr_links = run.get("pull_requests")
            if not isinstance(pr_links, list) or not pr_links:
                raise ReadUnknown("RUN_PR_ASSOCIATION_INCOMPLETE")
            for link in pr_links:
                item = _object(link, "RUN_PR_LINK")
                link_head = _object(item.get("head"), "RUN_PR_HEAD")
                if (not _positive(item.get("id")) or not _positive(item.get("number"))
                        or not isinstance(link_head.get("sha"), str)
                        or not SHA.fullmatch(link_head["sha"])):
                    raise ReadUnknown("INVALID_RUN_PR_ASSOCIATION")
                # A partial/mismatched identity for the requested PR is not
                # evidence that this newer same-head run belongs elsewhere.
                if item["number"] == pr_number or item["id"] == first["id"]:
                    if (item["number"] != pr_number or item["id"] != first["id"]
                            or link_head["sha"] != expected_head):
                        raise ReadUnknown("RUN_PR_ASSOCIATION_MISMATCH")
            workflow_sequence = (run["workflow_id"], run["run_number"])
            if workflow_sequence in workflow_run_numbers:
                raise ReadUnknown("DUPLICATE_WORKFLOW_RUN_NUMBER")
            workflow_run_numbers.add(workflow_sequence)
            if links_pr(run.get("pull_requests"), pr_number, first["id"], expected_head):
                linked.append({
                    "id": run["id"], "attempt": run["run_attempt"],
                    "workflow_id": run["workflow_id"],
                    "run_number": run["run_number"],
                    "path": run["path"],
                    "status": run["status"], "conclusion": run.get("conclusion"),
                })
        # A green job from an older run is stale when a newer run of the SAME
        # workflow is linked to this PR and exact head. GitHub's run_number is
        # monotonic within a workflow; run_attempt orders reruns of that run.
        # The newest run must itself own the named job and be completed green.
        latest_by_workflow = {}
        for run in linked:
            current = latest_by_workflow.get(run["workflow_id"])
            sequence = (run["run_number"], run["attempt"])
            if current is None or sequence > (current["run_number"], current["attempt"]):
                latest_by_workflow[run["workflow_id"]] = run

        # Correlate the check to the latest run of the pinned canonical workflow.
        # A same-named job from another workflow is not a substitute.
        linked_by_id = {run["id"]: run for run in linked}
        pr_regression_jobs = []
        for check in observed_checks:
            if check["name"] != CANONICAL_JOB_NAME or check["app_id"] != ACTIONS_APP_ID:
                continue
            details = check.get("details_url")
            match = CHECK_JOB.fullmatch(details) if isinstance(details, str) else None
            if match is None or int(match.group(2)) != check["id"]:
                continue
            linked_run = linked_by_id.get(int(match.group(1)))
            if linked_run is not None:
                latest = latest_by_workflow.get(linked_run["workflow_id"])
                if (latest is not None
                        and latest["id"] == linked_run["id"]
                        and latest["attempt"] == linked_run["attempt"]
                        and linked_run["workflow_id"] == CANONICAL_WORKFLOW_ID
                        and linked_run["path"] == CANONICAL_WORKFLOW_PATH):
                    pr_regression_jobs.append((check, linked_run))

        canonical_workflow_observation = (
            "MATCH" if len(pr_regression_jobs) == 1 else "NOT_CONFIRMED"
        )
        attempt_binding_observation = "NOT_CONFIRMED"
        named_regression_confirmed = False
        if len(pr_regression_jobs) == 1:
            check, run = pr_regression_jobs[0]
            jobs_url = (
                API + "/actions/runs/" + str(run["id"]) + "/attempts/"
                + str(run["attempt"]) + "/jobs?per_page=100"
            )
            jobs_obj = _object(source.get_json(jobs_url), "JOBS")
            jobs = jobs_obj.get("jobs")
            job_count = jobs_obj.get("total_count")
            if (type(job_count) is not int or not 0 <= job_count <= 100
                    or not isinstance(jobs, list) or len(jobs) != job_count):
                raise ReadUnknown("JOBS_INCOMPLETE")
            job_ids = set()
            for record in jobs:
                item = _object(record, "JOB")
                if not _positive(item.get("id")) or item["id"] in job_ids:
                    raise ReadUnknown("INVALID_OR_DUPLICATE_JOB")
                job_ids.add(item["id"])
            selected_jobs = [job for job in jobs if job.get("name") == CANONICAL_JOB_NAME]
            if len(selected_jobs) == 1:
                job = selected_jobs[0]
                job_status = job.get("status")
                job_conclusion = job.get("conclusion")
                job_state_coherent = (
                    job_status in ("queued", "in_progress", "completed")
                    and job_conclusion in (
                        None, "success", "failure", "neutral", "skipped",
                        "cancelled", "timed_out", "action_required", "stale",
                    )
                    and ((job_status == "completed") == (job_conclusion is not None))
                )
                job_bound = (
                    job["id"] == check["id"]
                    and _positive(job.get("run_id")) and job["run_id"] == run["id"]
                    and _positive(job.get("run_attempt")) and job["run_attempt"] == run["attempt"]
                    and isinstance(job.get("head_sha"), str)
                    and SHA.fullmatch(job["head_sha"]) is not None
                    and job["head_sha"] == expected_head
                    and job_state_coherent
                    and job_status == check["status"]
                    and job_conclusion == check["conclusion"]
                )
                if job_bound:
                    attempt_binding_observation = "MATCH"
                named_regression_confirmed = (
                    job_bound
                    and job_status == "completed" and job_conclusion == "success"
                    and check["status"] == "completed" and check["conclusion"] == "success"
                    and run["status"] == "completed" and run["conclusion"] == "success"
                )
        # Sample PR identity before the final metadata reads. The latest
        # workflow-run collection is deliberately the last network request:
        # this catches a rerun that starts during the PR read, while making
        # explicit that no non-atomic API sequence can prevent a later rerun.
        last = _identity(source.get_json(url), pr_number)
        if last != first:
            raise ReadUnknown("PR_CHANGED_BETWEEN_SAMPLES")

        if named_regression_confirmed:
            check_snapshot = _check_snapshot(
                check_obj, expected_head, run["id"], check["id"], "CHECKS"
            )
            run_snapshot = _run_snapshot(
                runs_obj, expected_head, pr_number, first["id"], "RUNS"
            )
            final_check_obj = source.get_json(checks_url)
            final_check_snapshot = _check_snapshot(
                final_check_obj, expected_head, run["id"], check["id"],
                "CHECKS_RECHECK"
            )
            if final_check_snapshot != check_snapshot:
                raise ReadUnknown("CHECKS_CHANGED_DURING_OBSERVATION")

            final_runs_obj = source.get_json(runs_url)
            final_run_snapshot = _run_snapshot(
                final_runs_obj, expected_head, pr_number, first["id"], "RUNS_RECHECK"
            )
            if final_run_snapshot != run_snapshot:
                raise ReadUnknown("RUNS_CHANGED_DURING_OBSERVATION")
        result.update({
            "reason": "NON_AUTHORITATIVE_GITHUB_METADATA_READBACK",
            "pr_sample_consistency": "SAME_AT_TWO_SAMPLED_READS",
            "check_count": len(observed_checks),
            "checks": observed_checks,
            "linked_run_count": len(linked),
            "linked_runs": linked,
            "canonical_workflow_observation": canonical_workflow_observation,
            "attempt_binding_observation": attempt_binding_observation,
            "required_check_observation": (
                "REPORTED_SUCCESS_BY_LINKED_PR_RUN"
                if named_regression_confirmed else "NOT_CONFIRMED"
            ),
            "workflow_freshness": (
                "SAMPLED_NOT_ATOMIC" if named_regression_confirmed else "NOT_CONFIRMED"
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
