"""Research-only same-byte-snapshot differential: legacy observer vs intake lab.

No production code is called through a changed route. A single immutable bytes
object feeds both parsers; the legacy observer is supplied a read-only in-memory
Path adapter. Assertions document CURRENT differences, not security acceptance,
truth, external source authenticity, or an agreed shared contract.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest

import ledger_observation_adapter as legacy_observer
from event_intake_validator_lab import inspect_jsonl_bytes


def _event(kind="TASK_STARTED", **kwargs):
    payload = {
        "event": kind,
        "timestamp": "2026-11-15T00:00:00Z",
        "task_id": "T1",
        "goal": "declared goal",
    }
    if kind == "TASK_FINISHED":
        payload.pop("goal")
        payload["status"] = "COMPLETED"
    payload.update(kwargs)
    return (json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


class _ImmutableByteSnapshot:
    """A Path substitute that only ever returns the SAME immutable bytes."""
    def __init__(self, raw: bytes):
        self.raw = raw
        self.opens = 0

    def absolute(self):
        return Path("/RESEARCH-SNAPSHOT-NOT-A-REAL-FILE")

    def is_symlink(self):
        return False

    def open(self, mode):
        assert mode == "rb"
        self.opens += 1
        return io.BytesIO(self.raw)


def _compare(monkeypatch, raw):
    assert type(raw) is bytes
    snapshot = _ImmutableByteSnapshot(raw)
    with monkeypatch.context() as mp:
        mp.setattr(legacy_observer, "Path", lambda _value: snapshot)
        old = legacy_observer.observe_ledger("synthetic-only")
    new = inspect_jsonl_bytes(raw)
    assert snapshot.opens == 1
    assert new["source_authenticity"] == "UNKNOWN"
    assert new["assessment"] == "NOT_ASSESSED"
    assert new["memory_mutation"] == "NONE"
    if old["status"] == "OBSERVED" and new["status"] == "OBSERVED":
        digest = hashlib.sha256(raw).hexdigest()
        assert old["sha256"] == new["file_sha256"] == digest
        assert old["event_count"] == new["eligible_records"]
    return old, new


CASES = [
    ("healthy_started", _event(), "OBSERVED", "OBSERVED", None),
    ("healthy_finished", _event("TASK_FINISHED"), "OBSERVED", "OBSERVED", None),
    ("crlf", _event().replace(b"\n", b"\r\n"), "OBSERVED", "OBSERVED", None),
    ("duplicate_root", b'{"event":"TASK_STARTED","timestamp":"t","task_id":"t","goal":"a","goal":"b"}\n',
     "OBSERVED", "UNKNOWN", "JSON_DUPLICATE_KEY"),
    ("duplicate_nested", b'{"event":"TASK_STARTED","timestamp":"t","task_id":"t","goal":"a","m":{"x":1,"x":2}}\n',
     "OBSERVED", "UNKNOWN", "JSON_DUPLICATE_KEY"),
    ("nan_nested", b'{"event":"TASK_STARTED","timestamp":"t","task_id":"t","goal":"a","m":{"x":NaN}}\n',
     "OBSERVED", "UNKNOWN", "JSON_NONFINITE_CONSTANT"),
    ("missing_task_id", b'{"event":"TASK_FINISHED","timestamp":"t","status":"COMPLETED"}\n',
     "OBSERVED", "UNKNOWN", "MISSING_OR_INVALID_TASK_ID"),
    ("unknown_kind", b'{"event":"UNREGISTERED","timestamp":"t"}\n',
     "UNKNOWN", "UNKNOWN", "UNSUPPORTED_EVENT_KIND"),
    ("unterminated", _event()[:-1],
     "UNKNOWN", "UNKNOWN", "INCOMPLETE_JSONL_RECORD"),
    ("lone_cr", _event()[:-1] + b"\r" + _event(),
     "UNKNOWN", "UNKNOWN", "INVALID_JSON"),
    ("invalid_utf8", b"\xff\n", "UNKNOWN", "UNKNOWN", "INVALID_UTF8"),
    ("large_producer_goal", _event(goal="x" * (70 * 1024)),
     "UNKNOWN", "UNKNOWN", "LINE_SIZE_LIMIT"),
    ("surrogate_escape", b'{"event":"TASK_STARTED","timestamp":"t","task_id":"t","goal":"\\ud800"}\n',
     "OBSERVED", "OBSERVED", None),
]


@pytest.mark.parametrize("label,raw,old_expected,new_expected,reason", CASES, ids=[x[0] for x in CASES])
def test_same_immutable_bytes_reproduce_current_contracts(monkeypatch, label, raw, old_expected, new_expected, reason):
    old, new = _compare(monkeypatch, raw)
    assert old["status"] == old_expected, label
    assert new["status"] == new_expected, label
    assert new["reason_code"] == reason, label


def test_four_mismatches_are_not_reported_as_shared_acceptance(monkeypatch):
    mismatch = [case for case in CASES if case[2] != case[3]]
    assert len(mismatch) == 4
    for name, raw, _, _, _ in mismatch:
        old, new = _compare(monkeypatch, raw)
        assert old["status"] == "OBSERVED", name
        assert new["status"] == "UNKNOWN", name
        assert new["eligible_records"] == 0, name
        assert new["file_sha256"] is None, name


def test_valid_prefix_plus_invalid_suffix_is_not_a_successful_shared_snapshot(monkeypatch):
    raw = _event() + b'{"event":"TASK_FINISHED","timestamp":"t","status":"COMPLETED"}\n'
    old, new = _compare(monkeypatch, raw)
    assert old["status"] == "OBSERVED"  # current observer does not require task_id
    assert new["status"] == "UNKNOWN"  # candidate lab rejects the suffix
    assert new["valid_envelopes"] == 1
    assert new["eligible_records"] == 0
    assert new["file_sha256"] is None


def test_lab_outcome_never_promotes_source_to_truth_or_exposes_goal(monkeypatch):
    marker = "private-research-goal-not-for-reports"
    raw = _event(goal=marker)
    old, new = _compare(monkeypatch, raw)
    assert old["status"] == new["status"] == "OBSERVED"
    assert marker not in json.dumps(new)
    assert "SUPPORTED" not in json.dumps(new)
    assert "recorded_memory" not in new
