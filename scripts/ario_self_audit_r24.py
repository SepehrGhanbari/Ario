#!/usr/bin/env python3
"""Ario Self-Audit R2.4: pinned, read-only verification of R2.3-D log evidence.

This verifier is deliberately offline. It does not call GitHub, execute logs,
accept new hashes from the report, authorize merges, or admit memory/trust.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

REPO = "SepehrGhanbari/Ario"
RUN_ID = 45460415487
EXPECTED_CHECKOUT = "bb49574475f6e4c4bf9a740c4bbb986a603a4cd0"
SCHEMA_IN = "ARIO-SELF-AUDIT-R2.3-D"
SCHEMA_OUT = "ARIO-SELF-AUDIT-R2.4"
MAX_REPORT_BYTES = 256 * 1024
MAX_LOG_BYTES = 8 * 1024 * 1024

# Pins were independently recomputed from the GitHub job-log connector read and
# compared byte-for-byte with both local R2.3-D reads. These are fixed anchors;
# a report cannot replace them with a newly supplied digest.
EXPECTED = {
    "m0-regression": {
        "job_id": 138681144591,
        "files": ("138681144591-1.log", "138681144591-2.log"),
        "sha256": "def5b16d547b34ed2fe14fb31a1068cb105d91291a783f821ebfd6bae2c181b4",
        "bytes": 22782,
        "os_marker": "Ubuntu",
        "python_marker": "Python/3.13.",
        "pytest_command": "python -m pytest -q tests",
        "summary": "1715 passed, 7 skipped, 2 warnings, 359 subtests passed in 14.36s",
        "timestamp_lines": 240,
        "line_count": 241,
    },
    "python-314-differential-advisory": {
        "job_id": 138681144245,
        "files": ("138681144245-1.log", "138681144245-2.log"),
        "sha256": "48dd555debd9377944b0380f3a7d00dd11208b31881c34f743af55b255991763",
        "bytes": 24017,
        "os_marker": "Ubuntu",
        "python_marker": "Python/3.14.",
        "pytest_command": "python -m pytest -q tests",
        "summary": "1715 passed, 7 skipped, 2 warnings, 359 subtests passed in 14.14s",
        "timestamp_lines": 254,
        "line_count": 255,
    },
    "windows-differential-advisory": {
        "job_id": 138681144844,
        "files": ("138681144844-1.log", "138681144844-2.log"),
        "sha256": "5d5a634095767b714b62e29961b7380e5209fce43938529d1b6361c8de406045",
        "bytes": 24059,
        "os_marker": "Microsoft Windows Server 2022",
        "python_marker": "Python\\3.13.",
        "pytest_command": "python -B -m pytest -p no:cacheprovider -p tests.test_m0_reproducibility_demo -q tests",
        "summary": "1714 passed, 8 skipped, 2 warnings, 359 subtests passed in 33.53s",
        "timestamp_lines": 243,
        "line_count": 244,
    },
}

STAMP = re.compile(r"^\ufeff?(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z)[ \t](.*)$")
SUMMARY = re.compile(r"\b\d+ passed, .*\d+ skipped, .*subtests passed in .*s\b")

class Rejected(Exception):
    pass

class Unknown(Exception):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise Rejected("duplicate JSON key")
        out[key] = value
    return out


def parse_json_bytes(data: bytes):
    def reject_constant(_value):
        raise Rejected("non-finite JSON value")
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=unique_object,
                          parse_constant=reject_constant)
    except Rejected:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise Rejected("invalid JSON") from exc


def safe_regular_read(path: Path, limit: int) -> bytes:
    """Bounded regular-file read; reject symlinks and observed file races."""
    try:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise Rejected("evidence path is not a regular file")
        if before.st_size < 0 or before.st_size > limit:
            raise Rejected("evidence file exceeds size limit")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(str(path), flags)
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise Rejected("opened evidence is not a regular file")
            if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) != (
                before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns
            ):
                raise Unknown("evidence changed before read")
            data = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            if len(data) != before.st_size or len(data) > limit:
                raise Unknown("evidence changed or exceeded limit during read")
            if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (
                opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns
            ):
                raise Unknown("evidence changed during read")
        final = path.lstat()
        if stat.S_ISLNK(final.st_mode) or (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns) != (
            before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns
        ):
            raise Unknown("evidence path changed during read")
        return data
    except (Rejected, Unknown):
        raise
    except OSError as exc:
        raise Unknown("evidence file unavailable") from exc


def payload_lines(data: bytes):
    if len(data) > MAX_LOG_BYTES:
        raise Rejected("log exceeds maximum size")
    try:
        text = data.decode("utf-8-sig", errors="strict")
    except UnicodeError as exc:
        raise Rejected("log is not strict UTF-8") from exc
    if "\x00" in text:
        raise Rejected("NUL byte in text log")
    raw_lines = text.split("\n")
    trailing_newline = bool(raw_lines and raw_lines[-1] == "")
    if trailing_newline:
        raw_lines = raw_lines[:-1]
    out = []
    for raw in raw_lines:
        raw = raw.removesuffix("\r")
        match = STAMP.match(raw)
        if not match:
            raise Rejected("un-timestamped or malformed log line")
        out.append((match.group(1), match.group(2)))
    # GitHub's downloaded logs end in LF/CRLF. The R2.3 diagnostic's line_count
    # includes the terminal empty split field; timestamp_lines does not.
    return out, len(out) + (1 if trailing_newline else 0)


def inspect_log(data: bytes, expected: dict):
    """Verify exact pinned bytes plus independently parsed claims in the log."""
    if len(data) != expected["bytes"]:
        raise Rejected("RAW_BYTE_LENGTH_MISMATCH")
    digest = sha256(data)
    if digest != expected["sha256"]:
        raise Rejected("RAW_SHA256_MISMATCH")
    lines, reported_line_count = payload_lines(data)
    messages = [message for _stamp, message in lines]

    if not data.startswith(b"\xef\xbb\xbf"):
        raise Rejected("EXPECTED_UTF8_BOM_MISSING")
    if reported_line_count != expected["line_count"]:
        raise Rejected("LOG_LINE_COUNT_MISMATCH")
    if len(lines) != expected["timestamp_lines"]:
        raise Rejected("TIMESTAMP_LINE_COUNT_MISMATCH")

    # The log must contain the exact fetch ref and the output of git log -1.
    fetch_needle = f"+{EXPECTED_CHECKOUT}:refs/remotes/pull/366/merge"
    if sum(fetch_needle in message for message in messages) != 1:
        raise Rejected("WRONG_OR_AMBIGUOUS_FETCH_CHECKOUT")
    git_log_positions = [i for i, message in enumerate(messages) if message.strip().endswith(" log -1 --format=%H")]
    if len(git_log_positions) != 1:
        raise Rejected("GIT_LOG_CHECKOUT_COMMAND_MISSING_OR_DUPLICATED")
    pos = git_log_positions[0]
    if pos + 1 >= len(messages) or messages[pos + 1].strip() != EXPECTED_CHECKOUT:
        raise Rejected("WRONG_CHECKOUT_OUTPUT")

    if expected["os_marker"] not in messages:
        raise Rejected("RUNNER_OS_MISMATCH")
    if not any(expected["python_marker"] in message for message in messages):
        raise Rejected("PYTHON_VERSION_MARKER_MISSING")

    group = f"##[group]Run {expected['pytest_command']}"
    if messages.count(group) != 1:
        raise Rejected("EXPECTED_PYTEST_COMMAND_MISSING_OR_DUPLICATED")
    summaries = [message for message in messages if SUMMARY.search(message)]
    if summaries != [expected["summary"]]:
        raise Rejected("TEST_SUMMARY_MISSING_DUPLICATED_OR_FABRICATED")
    return {
        "sha256": digest,
        "bytes": len(data),
        "checkout": EXPECTED_CHECKOUT,
        "pytest_command": expected["pytest_command"],
        "summary": expected["summary"],
        "runner_os": expected["os_marker"],
        "timestamp_lines": expected["timestamp_lines"],
        "line_count": expected["line_count"],
        "utf8_bom": True,
    }


def validate_report(report: dict):
    if not isinstance(report, dict):
        raise Rejected("report root must be an object")
    exact = {
        "schema": SCHEMA_IN,
        "repository": REPO,
        "run_id": RUN_ID,
        "expected_checkout": EXPECTED_CHECKOUT,
        "authorization_used": True,
        "source_origin": "UNATTESTED_READER_RESPONSES",
        "execution_attestation": "NOT_ESTABLISHED",
        "merge_authorized": False,
        "memory_admission": False,
        "trust_activation": False,
        "status": "UNKNOWN",
    }
    for key, value in exact.items():
        if report.get(key) != value or (type(value) is bool and type(report.get(key)) is not bool):
            raise Rejected("report identity/safety field mismatch: " + key)
    jobs = report.get("jobs")
    if not isinstance(jobs, list) or len(jobs) != len(EXPECTED):
        raise Rejected("report job set mismatch")
    indexed = {}
    for job in jobs:
        if not isinstance(job, dict) or job.get("job") in indexed:
            raise Rejected("duplicate or malformed job record")
        indexed[job.get("job")] = job
    if set(indexed) != set(EXPECTED):
        raise Rejected("unexpected job names")
    return indexed


def verify_directory(directory: Path, expected_map=None):
    expected_map = EXPECTED if expected_map is None else expected_map
    directory = Path(directory).absolute()
    try:
        dstat = directory.lstat()
    except OSError as exc:
        raise Unknown("evidence directory unavailable") from exc
    if stat.S_ISLNK(dstat.st_mode) or not stat.S_ISDIR(dstat.st_mode):
        raise Rejected("evidence path must be a real directory")

    report_path = directory / "LOG_TRANSPORT_REPORT.json"
    report_bytes = safe_regular_read(report_path, MAX_REPORT_BYTES)
    report = parse_json_bytes(report_bytes)
    indexed = validate_report(report)
    results = []

    for name, expected in expected_map.items():
        record = indexed[name]
        if record.get("job_id") != expected["job_id"]:
            raise Rejected("job id/name binding mismatch: " + name)
        if record.get("correspondence") != "MATCH_RAW_BYTES_AT_TWO_READS":
            raise Rejected("reported sample correspondence is not exact: " + name)
        if record.get("raw_body_correspondence") != "MATCH_RAW_BYTES_AT_TWO_READS":
            raise Rejected("reported raw correspondence is not exact: " + name)
        samples = record.get("samples")
        if not isinstance(samples, list) or len(samples) != 2:
            raise Rejected("exactly two samples required: " + name)
        sample_results = []
        for index, sample in enumerate(samples, 1):
            if not isinstance(sample, dict) or sample.get("sample") != index:
                raise Rejected("sample order mismatch: " + name)
            if sample.get("reason") != "LOG_RECEIVED":
                raise Rejected("sample was not accepted as a log: " + name)
            if sample.get("local_file") != expected["files"][index - 1]:
                raise Rejected("sample filename/job binding mismatch: " + name)
            if sample.get("sha256") != expected["sha256"] or sample.get("bytes") != expected["bytes"]:
                raise Rejected("report digest/length differs from pinned observation: " + name)
            if sample.get("checkout_text_present") is not True:
                raise Rejected("report lacks checkout observation: " + name)
            diagnostic = sample.get("body_diagnostic")
            if (not isinstance(diagnostic, dict) or diagnostic.get("format") != "TIMESTAMPED_TEXT"
                or diagnostic.get("utf8_bom") is not True
                or diagnostic.get("timestamp_lines") != expected["timestamp_lines"]
                or diagnostic.get("line_count") != expected["line_count"]):
                raise Rejected("unexpected body diagnostic: " + name)
            events = sample.get("events")
            if not isinstance(events, list) or len(events) != 2:
                raise Rejected("transport event chain incomplete: " + name)
            api, storage = events
            if (api.get("stage"), api.get("http_status"), api.get("location_present")) != ("API", 302, True):
                raise Rejected("API redirect observation mismatch: " + name)
            if (storage.get("stage"), storage.get("http_status"), storage.get("location_present")) != ("STORAGE", 200, False):
                raise Rejected("storage response observation mismatch: " + name)
            raw = safe_regular_read(directory / expected["files"][index - 1], MAX_LOG_BYTES)
            parsed = inspect_log(raw, expected)
            if len(raw) != sample["bytes"] or sha256(raw) != sample["sha256"]:
                raise Rejected("local raw bytes differ from report: " + name)
            sample_results.append(parsed)
        if sample_results[0]["sha256"] != sample_results[1]["sha256"]:
            raise Rejected("two raw samples differ: " + name)
        results.append({"job": name, "job_id": expected["job_id"], "samples": 2,
                        "raw_bytes": expected["bytes"], "sha256": expected["sha256"],
                        "status": "PASS_BOUNDED"})

    return {
        "schema": SCHEMA_OUT,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repository": REPO,
        "run_id": RUN_ID,
        "expected_checkout": EXPECTED_CHECKOUT,
        "status": "PASS_BOUNDED",
        "checks": results,
        "execution_attestation": "NOT_ESTABLISHED",
        "run_to_pr_exclusive_association": "NOT_ESTABLISHED",
        "source_custody": "NOT_ESTABLISHED",
        "freshness": "NOT_ESTABLISHED",
        "correctness_of_tested_code": "NOT_ESTABLISHED",
        "merge_authorized": False,
        "memory_admission": False,
        "trust_activation": False,
        "qualification": (
            "The local raw files match fixed SHA-256/length pins, each contains the expected checkout command/output, "
            "runner/Python markers, exact pytest invocation and exact summary, and two reads match byte-for-byte. "
            "This verifies bounded correspondence of the supplied historical logs only. It does not prove that the "
            "logs were generated by an uncompromised runner, that the tests are correct, that the run is exclusively "
            "bound to PR #366, or that source custody/freshness is independent. Pins and verifier are distributed "
            "together and are not signed."
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline read-only verifier for Ario Self-Audit R2.3-D evidence")
    parser.add_argument("--verify", metavar="R2_3_OUTPUT_DIRECTORY", help="folder containing LOG_TRANSPORT_REPORT.json and six raw logs")
    args = parser.parse_args(argv)
    if not args.verify:
        parser.error("--verify is required")
    try:
        report = verify_directory(Path(args.verify))
        out_dir = Path(args.verify).absolute()
        out = out_dir / "R2.4_VERIFICATION_REPORT.json"
        suffix = 2
        while out.exists():
            out = out_dir / f"R2.4_VERIFICATION_REPORT-{suffix}.json"
            suffix += 1
        with out.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(report, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        print("R2.4 STATUS: PASS_BOUNDED")
        print("Execution attestation: NOT_ESTABLISHED")
        print("PR-exclusive association: NOT_ESTABLISHED")
        print("Merge / memory / trust: NO")
        print("Report:", out)
        return 0
    except Rejected as exc:
        print("R2.4 STATUS: REJECTED")
        print("Reason:", str(exc))
        return 2
    except Unknown as exc:
        print("R2.4 STATUS: UNKNOWN")
        print("Reason:", str(exc))
        return 3

if __name__ == "__main__":
    raise SystemExit(main())
