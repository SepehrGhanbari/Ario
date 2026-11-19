"""ARIO-PR-CI-0.8: strict full-line Python version recognition.

Additive sidecar; v0.1-v0.7 are not modified. This module parses supplied
log text; it does NOT establish log custody, genuine pytest execution, or trust.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

import pr_claim_audit as v01

SCHEMA = "ARIO-PR-CI-0.8"
# Full-line matching is intentional: never accept just the suffix of a line
# with an unsupported term (e.g. '2 warnings') or attacker-supplied prefix.
SUMMARY_LINE = re.compile(
    r"(?P<counts>\d+ [^\r\n]+?) in (?P<seconds>\d+(?:\.\d+)?)s"
    r"(?:\s+\([^()]*\))?\Z"
)
COUNT_PART = re.compile(
    r"(?P<count>0|[1-9]\d*) (?P<name>subtests passed|passed|failed|skipped|warnings|warning)\Z"
)
PY_VERSION_LINE = re.compile(r"Python (?P<version>\d+\.\d+\.\d+)\Z")
SETUP_CPYTHON_LINE = re.compile(
    r"Successfully set up CPython \((?P<version>\d+\.\d+\.\d+)\)\Z"
)
COUNT_KEYS = ("passed", "failed", "skipped", "subtests_passed")
RUN_COMMAND = v01.RUN_COMMAND
LIMITATIONS = (
    "A matching supplied log is not independent execution attestation",
    "An author-controlled or replayed log may include a fabricated pytest summary",
    "The source/custody of the supplied evidence snapshot is not verified",
    "No merge, policy, signer, or trust authority is granted",
)


def extract_log(log: str) -> dict[str, Any]:
    """Fail closed on malformed/ambiguous pytest summaries and Python versions.

    Accept only the exact historical pytest summary vocabulary plus a bounded
    optional warning count. Unknown terms do not silently disappear. Version
    recognition is limited to v0.1 'Python X.Y.Z' and setup-python CPython.
    """
    if not isinstance(log, str) or len(log) > v01.MAX_LOG_CHARS:
        raise v01.Invalid("missing or oversize job log")
    lines = [v01._strip_log_prefix(x) for x in log.splitlines()]
    summaries: list[tuple[int, dict[str, int]]] = []
    for index, line in enumerate(lines):
        match = SUMMARY_LINE.fullmatch(line)
        if not match:
            continue
        stats = {k: 0 for k in COUNT_KEYS}
        seen: set[str] = set()
        pieces = match.group("counts").split(",")
        for piece in pieces:
            parsed = COUNT_PART.fullmatch(piece.strip())
            if parsed is None:
                raise v01.Invalid("unsupported pytest summary component")
            key = parsed.group("name")
            key = "subtests_passed" if key == "subtests passed" else key
            key = "warnings" if key == "warning" else key
            if key in seen:
                raise v01.Invalid("duplicate pytest summary field")
            seen.add(key)
            count = v01._parse_count(parsed.group("count"))
            if key in COUNT_KEYS:
                stats[key] = count
        if not ({"passed", "failed"} & seen):
            raise v01.Invalid("no test outcome count")
        summaries.append((index, stats))
    if len(summaries) != 1:
        raise v01.Invalid("missing or ambiguous pytest summary")

    # The original v0.7 finditer() promoted arbitrary log-text substrings to
    # interpreter evidence. Accept only two explicit complete-line formats,
    # after the pre-existing bounded timestamp/ANSI normalization. Both forms
    # remain untrusted log claims; this is format attribution, not custody.
    versions: set[str] = set()
    for line in lines:
        old = PY_VERSION_LINE.fullmatch(line)
        setup = SETUP_CPYTHON_LINE.fullmatch(line)
        if old is not None:
            versions.add(old.group("version"))
        if setup is not None:
            versions.add(setup.group("version"))
    if len(versions) != 1:
        raise v01.Invalid("missing or conflicting python version in log")
    summary_index, stats = summaries[0]
    v01._check_summary_step(lines, summary_index)
    return {**stats, "python_version": next(iter(versions)), "pytest_command": RUN_COMMAND}


def _compare_bound_snapshot(pr_text: str, evidence: Any) -> dict[str, Any]:
    """Offline correspondence only; all untrusted/partial snapshots => UNKNOWN."""
    claim = v01.read_claim(pr_text)
    e = v01._object(evidence)
    run = v01._object(e.get("run"))
    job = v01._object(e.get("job"))
    raw = e.get("job_log")
    digest = e.get("job_log_sha256")
    if e.get("job_log_complete") is not True:
        raise v01.Invalid("full job log not available")
    if not isinstance(digest, str) or not v01.SHA256.fullmatch(digest):
        raise v01.Invalid("missing log digest")
    if not isinstance(raw, str) or hashlib.sha256(raw.encode("utf-8")).hexdigest() != digest:
        raise v01.Invalid("log digest mismatch")
    if (type(run.get("id")) is not int or run["id"] != claim["run_id"] or
            type(run.get("run_attempt")) is not int or run["run_attempt"] != claim["run_attempt"] or
            run.get("head_sha") != claim["head_sha"] or run.get("status") != "completed" or
            run.get("event") != "pull_request" or
            run.get("conclusion") not in ("success", "failure")):
        raise v01.Invalid("run identity or status unavailable")
    if (type(job.get("id")) is not int or job["id"] != claim["job_id"] or
            type(job.get("run_id")) is not int or job["run_id"] != claim["run_id"] or
            job.get("status") != "completed" or job.get("conclusion") not in ("success", "failure") or
            not isinstance(job.get("name"), str) or not job["name"] or
            ("run_attempt" in job and not v01.matches_id(job["run_attempt"], claim["run_attempt"])) or
            ("head_sha" in job and job["head_sha"] != claim["head_sha"])):
        raise v01.Invalid("job identity or status unavailable")
    observed = extract_log(raw)
    observed["job_conclusion"] = job["conclusion"]
    keys = (*COUNT_KEYS, "python_version", "pytest_command", "job_conclusion")
    differences = [k for k in keys if claim[k] != observed[k]]
    return {
        "claim_correspondence": "MISMATCH" if differences else "MATCH",
        "observed": observed,
        "differences": differences,
        "binding": {
            "head_sha": claim["head_sha"],
            "run_id": claim["run_id"],
            "run_attempt": claim["run_attempt"],
            "job_id": claim["job_id"],
            "job_name": job["name"],
            "job_log_sha256": digest,
        },
    }


def assess(pr_text: str, evidence: Any) -> dict[str, Any]:
    """Public facade. Intentionally NEVER returns MATCH as the final status."""
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "UNKNOWN",
        "claim_correspondence": "UNKNOWN",
        "source_delivery": "UNVERIFIED",
        "execution_attestation": "NOT_ESTABLISHED",
        "reason": "UNASSESSED",
        "binding": None,
        "observed": None,
        "differences": [],
        "limitations": list(LIMITATIONS),
    }
    try:
        result = _compare_bound_snapshot(pr_text, evidence)
    except (v01.Invalid, ValueError, TypeError, UnicodeError, OverflowError, RecursionError) as exc:
        out["reason"] = str(exc) if isinstance(exc, v01.Invalid) else "invalid input"
        return out
    out.update(result)
    out["reason"] = "BOUNDED_SNAPSHOT_COMPARISON_NOT_EXECUTION_ATTESTATION"
    return out
