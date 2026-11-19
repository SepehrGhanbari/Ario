"""ARIO-PR-CI-0.1: offline, read-only comparison of PR test-count claims and CI evidence.

This is a research probe, not a CI attestation service, merge gate, or security
validator. Evidence JSON and its log may themselves be untrusted or incomplete.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "ARIO-PR-CI-0.1"
OPEN = "<!-- ARIO-CI-CLAIM-V0.1"
CLOSE = "ARIO-CI-CLAIM-V0.1 -->"
MAX_PR_BYTES = 128 * 1024
MAX_EVIDENCE_BYTES = 2 * 1024 * 1024
MAX_CLAIM_BYTES = 8192
MAX_LOG_CHARS = 1_500_000
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
ANSI = re.compile(r"\x1b\[[0-9;]*m")
STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\S+Z\s+")
SUMMARY = re.compile(
    r"(?P<counts>\d+ (?:subtests passed|passed|failed|skipped)"
    r"(?:,\s*\d+ (?:subtests passed|passed|failed|skipped))*)"
    r"\s+in\s+\d+(?:\.\d+)?s(?:\s*\([^()]*\))?\s*$"
)
COUNT_PART = re.compile(r"(\d+) (subtests passed|passed|failed|skipped)\Z")
VERSION = re.compile(r"\bPython (\d+\.\d+\.\d+)(?:\s|\(|$)")
RUN_COMMAND = "python -m pytest -q tests"
COUNT_KEYS = ("passed", "failed", "skipped", "subtests_passed")
LIMITATIONS = (
    "CI logs and tests are not independently authenticated ground truth",
    "matching a CI run does not validate tests, scientific claims, security or merging",
    "the JSON evidence snapshot and completeness flag may be supplied by the same actor as the claim",
)


class Invalid(Exception):
    """Malformed or incomplete evidence. Never convert to a verdict other than UNKNOWN."""


def _pairs_unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, val in pairs:
        if key in result:
            raise Invalid("duplicate JSON key")
        result[key] = val
    return result


def _decode_json(source: str) -> Any:
    try:
        return json.loads(source, object_pairs_hook=_pairs_unique)
    except (ValueError, TypeError, RecursionError) as exc:
        raise Invalid("invalid JSON") from exc


def _int(x: Any) -> bool:
    return type(x) is int and x >= 0


def _exact_keys(data: dict[str, Any], keys: set[str]) -> None:
    if set(data) != keys:
        raise Invalid("claim has missing or unexpected keys")


def _object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise Invalid("expected JSON object")
    return value


def read_claim(pr_text: str) -> dict[str, Any]:
    if not isinstance(pr_text, str) or len(pr_text.encode("utf-8")) > MAX_PR_BYTES:
        raise Invalid("PR body too large")
    if pr_text.count(OPEN) != 1 or pr_text.count(CLOSE) != 1:
        raise Invalid("exactly one claim block is required")
    first = pr_text.index(OPEN) + len(OPEN)
    last = pr_text.index(CLOSE)
    if last <= first:
        raise Invalid("inverted claim markers")
    body = pr_text[first:last].strip()
    if len(body.encode("utf-8")) > MAX_CLAIM_BYTES:
        raise Invalid("claim block too large")
    claim = _object(_decode_json(body))
    required = {
        "schema", "head_sha", "run_id", "run_attempt", "job_id", "python_version",
        "pytest_command", "passed", "failed", "skipped", "subtests_passed",
        "job_conclusion",
    }
    _exact_keys(claim, required)
    if claim["schema"] != SCHEMA:
        raise Invalid("unsupported schema")
    if not isinstance(claim["head_sha"], str) or not SHA40.fullmatch(claim["head_sha"]):
        raise Invalid("invalid head sha")
    for k in ("run_id", "job_id", "run_attempt", *COUNT_KEYS):
        if not _int(claim[k]) or (k in ("run_id", "job_id", "run_attempt") and claim[k] == 0):
            raise Invalid("invalid claim integer")
    if claim["job_conclusion"] not in ("success", "failure"):
        raise Invalid("unsupported job conclusion")
    if claim["pytest_command"] != RUN_COMMAND:
        raise Invalid("unsupported pytest command")
    if not isinstance(claim["python_version"], str) or not re.fullmatch(r"\d+\.\d+\.\d+", claim["python_version"]):
        raise Invalid("invalid python version")
    return claim


def _strip_log_prefix(line: str) -> str:
    return STAMP.sub("", ANSI.sub("", line)).strip()


def _check_summary_step(lines: list[str], summary_index: int) -> None:
    marker = "##[group]Run " + RUN_COMMAND
    if lines.count(marker) != 1:
        raise Invalid("expected exactly one pytest invocation")
    start = lines.index(marker) + 1
    preceding = lines[start:summary_index]
    if summary_index < start or any(
        line.startswith("##[group]") or line == "Post job cleanup." for line in preceding
    ):
        raise Invalid("pytest summary outside the claimed command")
    # Expanded Actions headers echo the script, then shell metadata. Output
    # follows endgroup. Compact snapshots can omit the whole header body.
    if preceding[:1] == [RUN_COMMAND] or "##[endgroup]" in preceding:
        if (len(preceding) < 3 or preceding[0] != RUN_COMMAND
                or not preceding[1].startswith("shell: ") or "##[endgroup]" not in preceding):
            raise Invalid("ambiguous pytest command header")


def _extract_log(log: str) -> dict[str, Any]:
    if not isinstance(log, str) or len(log) > MAX_LOG_CHARS:
        raise Invalid("missing or oversize job log")
    lines = [_strip_log_prefix(l) for l in log.splitlines()]
    summaries = []
    for index, line in enumerate(lines):
        m = SUMMARY.search(line)
        if m:
            stats = {k: 0 for k in COUNT_KEYS}
            seen: set[str] = set()
            for section in m.group("counts").split(","):
                match = COUNT_PART.fullmatch(section.strip())
                if not match:
                    raise Invalid("invalid pytest summary field")
                count, name = match.groups()
                key = "subtests_passed" if name == "subtests passed" else name
                if key in seen:
                    raise Invalid("duplicate pytest summary field")
                seen.add(key)
                stats[key] = int(count)
            if "passed" not in seen and "failed" not in seen:
                raise Invalid("no test outcome count")
            if m.start() != 0:
                raise Invalid("expected a complete pytest summary line")
            summaries.append((index, stats))
    if len(summaries) != 1:
        raise Invalid("missing or ambiguous pytest summary")
    versions = {m.group(1) for line in lines for m in VERSION.finditer(line)}
    if len(versions) != 1:
        raise Invalid("missing or conflicting python version in log")
    summary_index, stats = summaries[0]
    _check_summary_step(lines, summary_index)
    return {**stats, "python_version": next(iter(versions)), "pytest_command": RUN_COMMAND}


def _evidence(evidence: Any, claim: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    e = _object(evidence)
    run = _object(e.get("run"))
    job = _object(e.get("job"))
    log = e.get("job_log")
    checksum = e.get("job_log_sha256")
    if e.get("job_log_complete") is not True:
        raise Invalid("full job log not available")
    if not isinstance(checksum, str) or not SHA256.fullmatch(checksum):
        raise Invalid("missing log digest")
    if not isinstance(log, str) or hashlib.sha256(log.encode("utf-8")).hexdigest() != checksum:
        raise Invalid("log digest mismatch")
    if run.get("id") != claim["run_id"] or run.get("run_attempt") != claim["run_attempt"]:
        raise Invalid("run identity mismatch")
    if run.get("head_sha") != claim["head_sha"]:
        raise Invalid("run head not bound to claim head")
    if run.get("status") != "completed" or run.get("event") != "pull_request":
        raise Invalid("run incomplete or not a PR run")
    if run.get("conclusion") not in ("success", "failure"):
        raise Invalid("unknown run conclusion")
    if job.get("id") != claim["job_id"] or job.get("run_id") != claim["run_id"]:
        raise Invalid("job identity mismatch")
    if "head_sha" in job and job["head_sha"] != run["head_sha"]:
        raise Invalid("job head not bound to run head")
    if job.get("status") != "completed" or job.get("conclusion") not in ("success", "failure"):
        raise Invalid("job incomplete or inconclusive")
    if not isinstance(job.get("name"), str) or not job["name"]:
        raise Invalid("job name absent")
    if "run_attempt" in job and job["run_attempt"] != claim["run_attempt"]:
        raise Invalid("job attempt mismatch")
    observed = _extract_log(log)
    observed["job_conclusion"] = job["conclusion"]
    binding = {
        "head_sha": claim["head_sha"],
        "run_id": claim["run_id"],
        "run_attempt": claim["run_attempt"],
        "job_id": claim["job_id"],
        "job_name": job["name"],
        "job_log_sha256": checksum,
    }
    return observed, binding


def assess(pr_text: str, evidence: Any) -> dict[str, Any]:
    """Compare scoped CI claim vs supplied raw-log snapshot; no network or writes."""
    answer: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "UNKNOWN", "reason": "UNASSESSED", "binding": None,
        "differences": [], "observed": None, "limitations": list(LIMITATIONS),
    }
    try:
        claim = read_claim(pr_text)
        observed, binding = _evidence(evidence, claim)
    except (Invalid, UnicodeError, OverflowError, RecursionError) as exc:
        answer["reason"] = str(exc) if isinstance(exc, Invalid) else "invalid input"
        return answer
    keys = (*COUNT_KEYS, "python_version", "pytest_command", "job_conclusion")
    answer["binding"] = binding
    answer["observed"] = observed
    answer["differences"] = [k for k in keys if claim[k] != observed[k]]
    answer["status"] = "MISMATCH" if answer["differences"] else "MATCH"
    answer["reason"] = "VERIFIED_DIFFERENCE_IN_SUPPLIED_SNAPSHOT" if answer["differences"] else "COUNTS_MATCH_SUPPLIED_SNAPSHOT"
    return answer


def _read_limited(path: Path, cap: int) -> str:
    with path.open("rb") as handle:
        contents = handle.read(cap + 1)
    if len(contents) > cap:
        raise Invalid("input exceeds size cap")
    try:
        return contents.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Invalid("input not UTF-8") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ario PR claim audit (offline, never grants approval)")
    parser.add_argument("--pr-body", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        body = _read_limited(args.pr_body, MAX_PR_BYTES)
        data = _decode_json(_read_limited(args.evidence, MAX_EVIDENCE_BYTES))
        result = assess(body, data)
    except (OSError, Invalid, UnicodeError, OverflowError, RecursionError):
        result = assess("", {})
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    # Exit 0 means *the evaluator ran*. It is never admission or approval.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
