"""RED-then-GREEN tests for #233's read-only file preflight.

These source-focused tests run against an isolated disposable source:
- permission errors on final-path symlink metadata must return UNKNOWN;
- directories and FIFOs must be rejected as NON_REGULAR_SOURCE;
- a POSIX FIFO with no writer must never block a CI worker.
No production ledger, trust, state or memory is touched.
"""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from event_intake_validator_lab import inspect_jsonl_file


def _valid_line() -> bytes:
    return (
        b'{"event":"TASK_STARTED","task_id":"t",'
        b'"goal":"research-only","timestamp":"2026-11-15T00:00:00Z"}\n'
    )


def test_metadata_permission_error_is_reported_not_raised(tmp_path, monkeypatch):
    target = tmp_path / "not-readable.jsonl"
    original = Path.is_symlink

    def denied(path):
        if path == target:
            raise PermissionError("synthetic directory traversal denied")
        return original(path)

    monkeypatch.setattr(Path, "is_symlink", denied)
    report = inspect_jsonl_file(target)
    assert report["status"] == "UNKNOWN"
    assert report["reason_code"] == "FILE_READ_FAILED"
    assert report["eligible_records"] == 0
    assert report["file_sha256"] is None


def test_directory_is_reported_as_nonregular_source(tmp_path):
    report = inspect_jsonl_file(tmp_path)
    assert report["status"] == "UNKNOWN"
    assert report["reason_code"] == "NON_REGULAR_SOURCE"
    assert report["eligible_records"] == 0


@pytest.mark.skipif(os.name != "posix" or not hasattr(os, "mkfifo"),
                    reason="requires POSIX mkfifo")
def test_posix_fifo_without_writer_returns_bounded_failure(tmp_path):
    fifo = tmp_path / "no_writer.fifo"
    os.mkfifo(fifo)
    # The child is mandatory: an unfixed blocking open must not hang pytest/CI.
    script = (
        "import json,sys;"
        "from event_intake_validator_lab import inspect_jsonl_file;"
        "print(json.dumps(inspect_jsonl_file(sys.argv[1])))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script, str(fifo)],
        capture_output=True, text=True, timeout=3, check=True,
    )
    report = json.loads(completed.stdout)
    assert report["status"] == "UNKNOWN"
    assert report["reason_code"] == "NON_REGULAR_SOURCE"
    assert report["eligible_records"] == 0


def test_regular_file_still_passes_without_mutating_source(tmp_path):
    path = tmp_path / "good.jsonl"
    original = _valid_line()
    path.write_bytes(original)
    before = path.stat().st_mtime_ns
    report = inspect_jsonl_file(path)
    assert report["status"] == "OBSERVED"
    assert report["source_kind"] == "READ_ONLY_FILE"
    assert report["eligible_records"] == 1
    assert report["source_authenticity"] == "UNKNOWN"
    assert report["assessment"] == "NOT_ASSESSED"
    assert path.read_bytes() == original
    assert path.stat().st_mtime_ns == before


def test_ordinary_symlink_refusal_still_holds(tmp_path):
    target = tmp_path / "good.jsonl"
    target.write_bytes(_valid_line())
    link = tmp_path / "link.jsonl"
    try:
        link.symlink_to(target)
    except (NotImplementedError, OSError):
        pytest.skip("symlink creation not available on this runner")
    report = inspect_jsonl_file(link)
    assert report["status"] == "UNKNOWN"
    assert report["reason_code"] == "SYMLINK_REFUSED"
