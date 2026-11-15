"""Candidate RED/GREEN controls for ledger bytes, replay limits and compatibility.

All fixtures are synthetic. No real user ledger or historical record is changed.
This file does not approve any new source authority or legacy hash migration.
"""
import hashlib
import json

import pytest

import core.memory_consolidation as mc
from core.memory_consolidation import ConsolidationEngine, ConsolidationError


def _sha(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _event(i):
    return {"concept": "same", "assertion": f"statement-{i}"}


def test_stream_budget_exact_boundary_and_atomic_overflow(monkeypatch):
    monkeypatch.setattr(mc, "MAX_MEMORY_BATCH_EVENTS", 3)
    engine = ConsolidationEngine()
    assert engine.ingest_event_stream([(_sha(str(i)), _event(i)) for i in range(3)]) == 3
    prior_nodes, prior_hashes = engine.nodes, engine.known_ledger_hashes
    with pytest.raises(ConsolidationError, match="event-count limit"):
        engine.ingest_event_stream([(_sha(f"extra-{i}"), _event(i + 10)) for i in range(4)])
    assert engine.nodes == prior_nodes
    assert engine.known_ledger_hashes == prior_hashes


def test_retained_hash_limit_across_batches(monkeypatch):
    monkeypatch.setattr(mc, "MAX_MEMORY_STORED_HASHES", 2)
    engine = ConsolidationEngine()
    assert engine.ingest_event_stream([(_sha("a"), _event("a"))]) == 1
    assert engine.ingest_event_stream([(_sha("b"), _event("b"))]) == 1
    baseline_nodes = engine.nodes
    with pytest.raises(ConsolidationError, match="retained-event limit"):
        engine.ingest_event_stream([(_sha("a"), _event("a")), (_sha("c"), _event("c"))])
    assert engine.nodes == baseline_nodes
    assert engine.known_ledger_hashes == {_sha("a"), _sha("b")}


def test_event_serialization_size_rejected_without_partial_state(monkeypatch):
    monkeypatch.setattr(mc, "MAX_MEMORY_EVENT_BYTES", 70)
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError, match="event serialized-size limit"):
        engine.ingest_event_stream([
            (_sha("safe"), {"concept": "x", "assertion": "short"}),
            (_sha("large"), {"concept": "x", "assertion": "X" * 128}),
        ])
    assert engine.nodes == {}
    assert engine.known_ledger_hashes == set()


def test_batch_serialization_size_is_bounded(monkeypatch):
    monkeypatch.setattr(mc, "MAX_MEMORY_BATCH_BYTES", 100)
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError, match="batch serialized-size limit"):
        engine.ingest_event_stream([
            (_sha(str(i)), {"concept": "x", "assertion": f"msg-{i}"}) for i in range(10)
        ])
    assert engine.nodes == {}
    assert engine.known_ledger_hashes == set()


def test_incomplete_final_jsonl_line_rejected_atomically(tmp_path):
    file_path = tmp_path / "incomplete.jsonl"
    file_path.write_bytes(b'{"concept":"x","assertion":"A"}\n'
                          b'{"concept":"x","assertion":"B"}')
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError, match="missing final LF"):
        engine.ingest_ledger_file(file_path)
    assert engine.nodes == {}
    assert engine.known_ledger_hashes == set()


def test_completed_crlf_is_kept_byte_exact(tmp_path):
    raw = b'{"concept":"x","assertion":"A"}\r\n'
    file_path = tmp_path / "crlf.jsonl"
    file_path.write_bytes(raw)
    engine = ConsolidationEngine()
    assert engine.ingest_ledger_file(file_path) == 1
    n = next(iter(engine.nodes.values()))
    assert n.source_event_hashes == (hashlib.sha256(raw).hexdigest(),)


def test_blank_line_rejected_without_state(tmp_path):
    file_path = tmp_path / "blank.jsonl"
    file_path.write_bytes(b'{"concept":"x","assertion":"A"}\n\n')
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError, match="blank JSONL"):
        engine.ingest_ledger_file(file_path)
    assert engine.nodes == {}


def test_explicit_legacy_digest_scheme_differs_from_current(tmp_path):
    raw = b'{"concept":"x","assertion":"A"}\n'
    file_path = tmp_path / "line.jsonl"
    file_path.write_bytes(raw)
    e = ConsolidationEngine()
    assert e.ingest_ledger_file(file_path) == 1
    current = next(iter(e.nodes.values())).source_event_hashes[0]
    assert mc.RECORD_DIGEST_SCHEME == "raw_line_sha256_v0_2"
    assert mc.LEGACY_RECORD_DIGEST_SCHEME == "legacy_trimmed_sha256_v0_1"
    assert current == hashlib.sha256(raw).hexdigest()
    assert current != hashlib.sha256(raw.strip()).hexdigest()


def test_agent_event_shape_is_counted_not_overclaimed(tmp_path):
    rows = [
        {"event": "TASK_STARTED", "task_id": "T7", "goal": "Inspect safely",
         "timestamp": "2026-11-15T00:00:00Z"},
        {"event": "STEP_OBSERVED", "task_id": "T7", "tool": "inspect",
         "status": "SUCCEEDED", "timestamp": "2026-11-15T00:01:00Z"},
        {"event": "TASK_FINISHED", "task_id": "T7", "status": "COMPLETED",
         "timestamp": "2026-11-15T00:02:00Z"},
    ]
    file_path = tmp_path / "agent.jsonl"
    file_path.write_bytes(b"".join(
        (json.dumps(row, sort_keys=True) + "\n").encode("utf-8") for row in rows
    ))
    engine = ConsolidationEngine()
    assert engine.ingest_ledger_file(file_path) == 3
    assert len(engine.nodes) == 1  # ingestion != semantic extraction
    assert len(engine.known_ledger_hashes) == 3
    assert engine.validate_lineage_integrity()


def test_empty_batch_and_replay_remain_valid():
    engine = ConsolidationEngine()
    assert engine.ingest_event_stream([]) == 0
    h = _sha("same")
    event = _event("x")
    assert engine.ingest_event_stream([(h, event)]) == 1
    node = next(iter(engine.nodes.values()))
    assert engine.ingest_event_stream([(h.upper(), event)]) == 1
    assert next(iter(engine.nodes.values())) == node
