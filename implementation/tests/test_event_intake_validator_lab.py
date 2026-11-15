"""Executable review controls for a NON-INTEGRATED event intake lab."""
import hashlib
import json
from pathlib import Path

import pytest

from event_intake_validator_lab import (
    CONTRACT_VERSION,
    IntakeLimits,
    inspect_jsonl_bytes,
    inspect_jsonl_file,
    REQUIRED_FIELDS,
)


def event(kind="TASK_STARTED", **fields):
    base = {"event": kind, "timestamp": "2026-11-15T00:00:00Z"}
    for key in REQUIRED_FIELDS.get(kind, ()):
        base[key] = "reported"
    base.update(fields)
    return base


def line(record, newline="\n"):
    return json.dumps(record, ensure_ascii=False, sort_keys=True).encode() + newline.encode()


def test_healthy_event_records_only_metadata_not_claim_content():
    secret = "secret-goal-only-in-source"
    raw = line(event(goal=secret))
    report = inspect_jsonl_bytes(raw)
    assert report["status"] == "OBSERVED"
    assert report["eligible_records"] == 1
    assert report["valid_envelopes"] == 1
    assert report["records"][0]["outcome"] == "VALID_ENVELOPE"
    assert report["records"][0]["record_sha256"] == hashlib.sha256(raw).hexdigest()
    assert report["file_sha256"] == hashlib.sha256(raw).hexdigest()
    assert report["source_authenticity"] == "UNKNOWN"
    assert report["assessment"] == "NOT_ASSESSED"
    assert report["memory_mutation"] == "NONE"
    assert report["contract_version"] == CONTRACT_VERSION
    assert secret not in str(report)


@pytest.mark.parametrize("kind", list(REQUIRED_FIELDS))
def test_source_shaped_eight_event_types_are_observed(kind):
    result = inspect_jsonl_bytes(line(event(kind)))
    assert result["status"] == "OBSERVED"
    assert result["eligible_records"] == 1
    assert result["records"][0]["event_kind"] == kind


def test_lf_and_crlf_hash_exact_source_bytes():
    first = line(event(goal="first"))
    second = line(event("TASK_FINISHED"), newline="\r\n")
    report = inspect_jsonl_bytes(first + second)
    assert report["status"] == "OBSERVED"
    assert [x["record_sha256"] for x in report["records"]] == [
        hashlib.sha256(first).hexdigest(),
        hashlib.sha256(second).hexdigest(),
    ]


def test_valid_cr_whitespace_inside_one_record_is_not_new_line():
    raw = b'{"event":"TASK_STARTED",\r"timestamp":"2026-11-15T00:00:00Z","task_id":"t","goal":"g"}\n'
    report = inspect_jsonl_bytes(raw)
    assert report["status"] == "OBSERVED"
    assert report["records_checked"] == 1


@pytest.mark.parametrize("raw,expected", [
    (b"", "EMPTY_LEDGER"),
    (b'{"event":"TASK_STARTED"}', "INCOMPLETE_JSONL_RECORD"),
    (b"\n", "EMPTY_JSONL_RECORD"),
    (b"\xff\n", "INVALID_UTF8"),
    (b"not-json\n", "INVALID_JSON"),
    (b'{"event":"TASK_STARTED","event":"TASK_FINISHED"}\n', "JSON_DUPLICATE_KEY"),
    (b'{"event":"TASK_STARTED","meta":{"a":1,"a":2}}\n', "JSON_DUPLICATE_KEY"),
    (b'{"event":"TASK_STARTED","meta":{"bad":NaN}}\n', "JSON_NONFINITE_CONSTANT"),
    (b'{"event":"TASK_STARTED","meta":{"bad":Infinity}}\n', "JSON_NONFINITE_CONSTANT"),
    (b'{"event":"UNKNOWN_KIND","timestamp":"t"}\n', "UNSUPPORTED_EVENT_KIND"),
    (b'{"event":"TASK_FINISHED","timestamp":"t","status":"COMPLETED"}\n', "MISSING_OR_INVALID_TASK_ID"),
    (b'{"event":"TASK_STARTED","timestamp":"t","task_id":"t","goal":[]}\n', "MISSING_OR_INVALID_GOAL"),
    (b'{"event":"TASK_STARTED","timestamp":"t","task_id":"t","goal":"a"}\r'
     b'{"event":"TASK_STARTED","timestamp":"t","task_id":"t","goal":"b"}\n', "INVALID_JSON"),
])
def test_fail_closed_with_reason_and_no_eligibility(raw, expected):
    report = inspect_jsonl_bytes(raw)
    assert report["status"] == "UNKNOWN"
    assert report["reason_code"] == expected
    assert report["eligible_records"] == 0
    assert report["file_sha256"] is None
    assert report["memory_mutation"] == "NONE"


def test_batch_with_valid_prefix_and_invalid_suffix_is_globally_blocked():
    raw = line(event()) + b'{"event":"TASK_FINISHED","status":"COMPLETED","timestamp":"t"}\n'
    report = inspect_jsonl_bytes(raw)
    assert report["records_checked"] == 2
    assert report["valid_envelopes"] == 1
    assert report["eligible_records"] == 0
    assert report["status"] == "UNKNOWN"
    assert report["records"][0]["outcome"] == "VALID_ENVELOPE"
    assert report["records"][1]["reason_code"] == "MISSING_OR_INVALID_TASK_ID"


def test_unmapped_finished_event_is_not_claimed_as_memory_or_truth():
    report = inspect_jsonl_bytes(line(event("TASK_FINISHED")))
    assert report["status"] == "OBSERVED"
    assert report["records"][0]["semantic_extraction"] == "NOT_PERFORMED"
    assert report["assessment"] == "NOT_ASSESSED"
    assert "node_id" not in report["records"][0]


def test_ledger_and_raw_line_limits_have_distinct_codes():
    raw = line(event())
    assert inspect_jsonl_bytes(raw, limits=IntakeLimits(max_ledger_bytes=len(raw)-1))["reason_code"] == "LEDGER_SIZE_LIMIT"
    assert inspect_jsonl_bytes(raw, limits=IntakeLimits(max_line_bytes=len(raw)-1))["reason_code"] == "LINE_SIZE_LIMIT"


def test_event_count_limit_is_visible_and_does_not_return_partial_observed():
    raw = line(event()) * 3
    limits = IntakeLimits(max_events=2)
    result = inspect_jsonl_bytes(raw, limits=limits)
    assert result["reason_code"] == "EVENT_COUNT_LIMIT"
    assert result["records_checked"] == 3
    assert result["eligible_records"] == 0


def test_producer_valid_but_oversized_goal_returns_resource_reason():
    raw = line(event(goal="G" * (70 * 1024)))
    report = inspect_jsonl_bytes(raw)
    assert report["reason_code"] == "LINE_SIZE_LIMIT"
    assert report["eligible_records"] == 0


def test_input_type_and_invalid_limit_guards():
    with pytest.raises(TypeError):
        inspect_jsonl_bytes("not bytes")
    with pytest.raises(ValueError):
        IntakeLimits(max_events=0)
    with pytest.raises(ValueError):
        IntakeLimits(max_line_bytes=True)


def test_readonly_file_path_preserves_exact_bytes(tmp_path):
    raw = line(event())
    file = tmp_path / "records.jsonl"
    file.write_bytes(raw)
    before = file.stat().st_mtime_ns
    result = inspect_jsonl_file(file)
    assert result["status"] == "OBSERVED"
    assert result["source_kind"] == "READ_ONLY_FILE"
    assert result["file_sha256"] == hashlib.sha256(raw).hexdigest()
    assert file.read_bytes() == raw
    assert file.stat().st_mtime_ns == before


def test_real_symlink_is_rejected_when_environment_supports_it(tmp_path):
    original = tmp_path / "events.jsonl"
    original.write_bytes(line(event()))
    link = tmp_path / "alias.jsonl"
    try:
        link.symlink_to(original)
    except (OSError, NotImplementedError):
        pytest.skip("This operating system does not allow this sandbox symlink")
    result = inspect_jsonl_file(link)
    assert result["reason_code"] == "SYMLINK_REFUSED"
    assert result["eligible_records"] == 0


def test_missing_file_has_no_content_or_accepted_records(tmp_path):
    result = inspect_jsonl_file(tmp_path / "missing.jsonl")
    assert result["status"] == "UNKNOWN"
    assert result["reason_code"] == "FILE_READ_FAILED"
    assert result["eligible_records"] == 0
