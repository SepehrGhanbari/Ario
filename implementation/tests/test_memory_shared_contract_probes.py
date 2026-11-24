"""Proposal-only RED and positive fixtures for Ario shared JSONL intake v0.1.

Read-only / synthetic fixture tests. XFAIL means a present interoperation
mismatch or a *new proposed* contract, not an approved security gate.
The production source files, epistemic statuses, identifiers and policies
are untouched by this module.
"""

import hashlib
import json

import pytest

from core.memory_consolidation import ConsolidationEngine, ConsolidationError
from ledger_observation_adapter import observe_ledger


STAMP = "2026-11-15T00:00:00Z"


def _record(goal="Observe without asserting truth"):
    return {
        "event": "TASK_STARTED",
        "task_id": "T-probe",
        "goal": goal,
        "timestamp": STAMP,
    }


def _line(event):
    return (json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.mark.xfail(strict=True, reason="RED: observer accepts duplicate root JSON keys; memory rejects")
def test_observer_should_reject_duplicate_root_keys(tmp_path):
    raw = (
        b'{"event":"TASK_STARTED","task_id":"T",'
        b'"goal":"A","goal":"B","timestamp":"2026-11-15T00:00:00Z"}\n'
    )
    path = tmp_path / "duplicate_root.jsonl"
    path.write_bytes(raw)
    with pytest.raises(ConsolidationError, match="duplicate JSON key"):
        ConsolidationEngine().ingest_ledger_file(path)
    assert observe_ledger(path)["status"] == "UNKNOWN"


@pytest.mark.xfail(strict=True, reason="RED: observer accepts nested duplicate JSON keys; memory rejects")
def test_observer_should_reject_nested_duplicate_keys(tmp_path):
    raw = (
        b'{"event":"TASK_STARTED","task_id":"T","goal":"A",'
        b'"meta":{"source":"A","source":"B"},'
        b'"timestamp":"2026-11-15T00:00:00Z"}\n'
    )
    path = tmp_path / "duplicate_nested.jsonl"
    path.write_bytes(raw)
    with pytest.raises(ConsolidationError, match="duplicate JSON key"):
        ConsolidationEngine().ingest_ledger_file(path)
    assert observe_ledger(path)["status"] == "UNKNOWN"


@pytest.mark.xfail(strict=True, reason="RED: nonfinite NaN is accepted by observer but not memory")
def test_observer_should_reject_nonfinite_json_constants(tmp_path):
    raw = (
        b'{"event":"TASK_STARTED","task_id":"T","goal":"A",'
        b'"meta":{"score":NaN},"timestamp":"2026-11-15T00:00:00Z"}\n'
    )
    path = tmp_path / "nan.jsonl"
    path.write_bytes(raw)
    with pytest.raises(ConsolidationError):
        ConsolidationEngine().ingest_ledger_file(path)
    assert observe_ledger(path)["status"] == "UNKNOWN"


@pytest.mark.xfail(strict=True, reason="PROPOSED: task event envelope should require task_id")
def test_observer_should_flag_missing_task_id(tmp_path):
    path = tmp_path / "missing_task_id.jsonl"
    path.write_bytes(
        b'{"event":"TASK_FINISHED","status":"COMPLETED",'
        b'"timestamp":"2026-11-15T00:00:00Z"}\n'
    )
    assert observe_ledger(path)["status"] == "UNKNOWN"


@pytest.mark.xfail(strict=True, reason="PROPOSED: no implicit str(list) for semantic claim fields")
def test_memory_should_reject_nontext_assertion_in_direct_stream():
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError):
        engine.ingest_event_stream([
            (_sha(b"nontext"), {"concept": "x", "assertion": ["an", "array"]})
        ])
    assert engine.nodes == {}


@pytest.mark.xfail(strict=True, reason="PROPOSED: explicit per-event intake/skipped report absent")
def test_memory_should_report_unmapped_event_reason():
    engine = ConsolidationEngine()
    engine.ingest_event_stream([
        (_sha(b"finished"), {
            "event": "TASK_FINISHED", "task_id": "T",
            "status": "COMPLETED", "timestamp": STAMP,
        })
    ])
    report = getattr(engine, "last_ingest_report", None)
    assert isinstance(report, dict)
    assert report.get("skipped_unmapped_events") == 1
    assert report.get("semantic_nodes_created") == 0


def test_positive_known_emitted_event_can_be_observed_and_structurally_ingested(tmp_path):
    raw = _line(_record())
    path = tmp_path / "healthy.jsonl"
    path.write_bytes(raw)
    observed = observe_ledger(path)
    assert observed["status"] == "OBSERVED"
    assert observed["event_count"] == 1
    assert observed["observations"][0]["record_sha256"] == _sha(raw)
    engine = ConsolidationEngine()
    assert engine.ingest_ledger_file(path) == 1
    assert len(engine.nodes) == 1
    node = next(iter(engine.nodes.values()))
    assert node.source_event_hashes == (_sha(raw),)
    assert node.status.value == "ACCEPTED"  # LEGACY, not evidence support


def test_positive_ledger_record_count_is_not_semantic_learning_count(tmp_path):
    started = _record()
    finished = {
        "event": "TASK_FINISHED",
        "task_id": "T-probe", "status": "COMPLETED",
        "timestamp": STAMP,
    }
    path = tmp_path / "started_finished.jsonl"
    path.write_bytes(_line(started) + _line(finished))
    assert observe_ledger(path)["event_count"] == 2
    engine = ConsolidationEngine()
    assert engine.ingest_ledger_file(path) == 2
    assert len(engine.known_ledger_hashes) == 2
    assert len(engine.nodes) == 1


def test_positive_unknown_envelope_is_not_observer_accepted(tmp_path):
    path = tmp_path / "unknown_kind.jsonl"
    path.write_bytes(
        b'{"event":"UNREGISTERED_KIND","timestamp":"2026-11-15T00:00:00Z"}\n'
    )
    observation = observe_ledger(path)
    assert observation["status"] == "UNKNOWN"
    assert observation["observations"] == []


def test_candidate_v2_identity_distinguishes_delimiter_alias_without_runtime_change():
    """Pure test vector only: does not adopt V2 node-ID semantics."""
    a = ("a:b", "c")
    b = ("a", "b:c")
    legacy = lambda pair: hashlib.sha256((pair[0] + ":" + pair[1]).encode("utf-8")).hexdigest()[:16]
    v2 = lambda pair: hashlib.sha256(
        json.dumps(list(pair), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert legacy(a) == legacy(b)
    assert v2(a) != v2(b)
    assert len(v2(a)) == 64 and len(v2(b)) == 64


def test_candidate_ambiguous_legacy_mapping_stays_unknown():
    """Pure candidate resolver: ambiguous ID cannot choose a V2 assertion."""
    crosswalk = {"SEM-legacy": {"SEM-v2-a", "SEM-v2-b"}}
    matches = crosswalk["SEM-legacy"]
    result = next(iter(matches)) if len(matches) == 1 else "UNKNOWN"
    assert result == "UNKNOWN"


def test_old_trimmed_and_current_raw_digest_are_not_interchangeable():
    raw = _line(_record("A"))
    legacy = hashlib.sha256(raw.strip()).hexdigest()
    raw_line = hashlib.sha256(raw).hexdigest()
    assert legacy != raw_line
    assert _sha(raw) == raw_line
