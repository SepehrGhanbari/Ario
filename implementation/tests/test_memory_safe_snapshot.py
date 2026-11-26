"""Safety and recovery contract for the data-only cognitive-memory snapshot."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.memory_consolidation import (
    CausalLink,
    ConsolidationEngine,
    ConsolidationError,
    NodeEpistemicStatus,
)
from core.memory_snapshot import restore_snapshot_file, write_snapshot

PAIRS = (("a:b", "c"), ("a", "b:c"))


def event_row(concept: str, assertion: str):
    event = {"concept": concept, "assertion": assertion}
    event_hash = hashlib.sha256(
        json.dumps(event, sort_keys=True, allow_nan=False).encode("utf-8")
    ).hexdigest()
    return event_hash, event


def populated_engine() -> tuple[ConsolidationEngine, list[tuple[str, dict[str, str]]]]:
    engine = ConsolidationEngine(node_id_version="v2")
    events = [event_row(*pair) for pair in PAIRS]
    assert engine.ingest_event_stream(events) == 2
    nodes = list(engine.nodes.values())
    engine._links.append(CausalLink(
        from_node_id=nodes[0].node_id,
        to_node_id=nodes[1].node_id,
        relation="co-observed",
        weight=0.75,
        evidence_hashes=tuple(sorted(event_hash for event_hash, _ in events)),
    ))
    return engine, events


def digest(snapshot: bytes) -> str:
    return hashlib.sha256(snapshot).hexdigest()


def test_valid_snapshot_round_trips_in_fresh_process_and_rejects_replay(tmp_path: Path):
    engine, events = populated_engine()
    path = tmp_path / "memory.snapshot.json"
    retained_sha256 = write_snapshot(engine, path)
    snapshot = path.read_bytes()

    child = r"""
import hashlib, json, sys
from pathlib import Path
from core.memory_consolidation import ConsolidationEngine
snapshot_path, expected, event_a, event_b = sys.argv[1:]
raw = Path(snapshot_path).read_bytes()
assert hashlib.sha256(raw).hexdigest() == expected
engine = ConsolidationEngine.from_snapshot(raw, expected_sha256=expected)
assert len(engine.nodes) == 2
assert len(engine.links) == 1
assert engine.ingest_event_stream([json.loads(event_a), json.loads(event_b)]) == 0
legacy = engine.compute_node_id("a:b", "c", version="v1")
assert engine.resolve_node_id(legacy) is None
for concept, assertion in (("a:b", "c"), ("a", "b:c")):
    node_id = engine.compute_node_id(concept, assertion, version="v2")
    assert engine.get_node(node_id).status.value == "RECORDED"
print("fresh-process recovery and replay rejection passed")
"""
    implementation_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            child,
            str(path),
            retained_sha256,
            json.dumps(events[0]),
            json.dumps(events[1]),
        ],
        cwd=implementation_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "fresh-process recovery" in result.stdout

    restored = ConsolidationEngine.from_snapshot(
        snapshot, expected_sha256=retained_sha256
    )
    assert restored.nodes == engine.nodes
    assert list(restored.nodes) == list(engine.nodes)
    assert restored.links == engine.links
    assert restored.known_ledger_hashes == engine.known_ledger_hashes
    assert restored._event_payload_digests == engine._event_payload_digests
    assert restored._event_stable_digests == engine._event_stable_digests
    assert restored.validate_lineage_integrity()
    assert restored.ingest_event_stream(events) == 0
    legacy = restored.compute_node_id(*PAIRS[0], version="v1")
    assert restored.resolve_node_id(legacy) is None
    assert restored.get_node(legacy) is None


def test_snapshot_is_deterministic_and_derived_aliases_are_not_serialized():
    engine, _ = populated_engine()
    first = engine.to_snapshot()
    second = engine.to_snapshot()
    assert first == second
    assert b"_legacy_aliases" not in first
    assert b"pickle" not in first


def test_corruption_reference_and_schema_failures_preserve_existing_engine():
    populated, _ = populated_engine()
    existing, _ = populated_engine()
    before_snapshot = existing.to_snapshot()
    good = populated.to_snapshot()
    expected = digest(good)

    corrupted = good[:-1] + (b" " if good[-1:] != b" " else b"x")
    with pytest.raises(ConsolidationError, match="HOLD_SNAPSHOT_SHA256_MISMATCH"):
        existing.restore_snapshot(corrupted, expected_sha256=expected)
    assert existing.to_snapshot() == before_snapshot

    invalid_schema = json.loads(good)
    invalid_schema["engine"]["nodes"][0]["source_event_hashes"] = []
    invalid_bytes = json.dumps(
        invalid_schema, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    with pytest.raises(ConsolidationError, match="HOLD_INVALID_SNAPSHOT_SOURCE_EVENT_HASHES"):
        existing.restore_snapshot(invalid_bytes, expected_sha256=digest(invalid_bytes))
    assert existing.to_snapshot() == before_snapshot


def test_decoder_rejects_noncanonical_duplicate_and_oversized_inputs():
    engine, _ = populated_engine()
    canonical = engine.to_snapshot()
    duplicate_key = canonical.replace(b"\"format\":\"ario.cognitive-memory\"", b'"format":"ario.cognitive-memory","format":"ario.cognitive-memory"', 1)
    with pytest.raises(ConsolidationError, match="HOLD_SNAPSHOT_DUPLICATE_JSON_KEY"):
        ConsolidationEngine.from_snapshot(
            duplicate_key, expected_sha256=digest(duplicate_key)
        )

    with pytest.raises(ConsolidationError, match="HOLD_NONCANONICAL_SNAPSHOT_BYTES"):
        ConsolidationEngine.from_snapshot(
            b" " + canonical, expected_sha256=digest(b" " + canonical)
        )

    with pytest.raises(ConsolidationError, match="HOLD_SNAPSHOT_MUST_BE_IMMUTABLE_BYTES"):
        ConsolidationEngine.from_snapshot(
            bytearray(canonical), expected_sha256=digest(canonical)
        )


def test_recovery_rejects_unauthorized_statuses_without_rewriting_source():
    engine, _ = populated_engine()
    before = engine.to_snapshot()
    previous = engine.to_snapshot()
    for status in (NodeEpistemicStatus.ACCEPTED, NodeEpistemicStatus.SUPPORTED):
        document = json.loads(before)
        document["engine"]["nodes"][0]["status"] = status.value
        candidate = json.dumps(
            document, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
        with pytest.raises(ConsolidationError, match="HOLD_UNVERIFIED_SNAPSHOT_ADMISSION"):
            engine.restore_snapshot(candidate, expected_sha256=digest(candidate))
        assert before == engine.to_snapshot()
        assert previous == engine.to_snapshot()


def test_snapshot_refuses_privileged_default_admission_status():
    engine, _ = populated_engine()
    for status in (NodeEpistemicStatus.ACCEPTED, NodeEpistemicStatus.SUPPORTED):
        engine.default_status = status
        with pytest.raises(ConsolidationError, match="HOLD_UNVERIFIED_SNAPSHOT_ADMISSION"):
            engine.to_snapshot()
    engine.default_status = NodeEpistemicStatus.RECORDED


def test_mutable_views_and_link_references_cannot_change_recovered_state():
    source, _ = populated_engine()
    snapshot = source.to_snapshot()
    restored = ConsolidationEngine.from_snapshot(
        snapshot, expected_sha256=digest(snapshot)
    )
    expected_nodes = restored.nodes
    expected_links = restored.links

    mutable_node_view = restored.nodes
    mutable_node_view.clear()
    mutable_link_view = restored.links
    mutable_link_view.clear()
    assert restored.nodes == expected_nodes
    assert restored.links == expected_links
    assert isinstance(restored.links[0].evidence_hashes, tuple)


def test_atomic_write_failure_keeps_previous_snapshot(tmp_path: Path, monkeypatch):
    import core.memory_snapshot as snapshot_module

    first_engine, _ = populated_engine()
    second_engine = ConsolidationEngine()
    target = tmp_path / "memory.snapshot.json"
    previous_sha256 = write_snapshot(first_engine, target)
    previous_bytes = target.read_bytes()
    assert digest(previous_bytes) == previous_sha256

    def fail_replace(*args, **kwargs):
        raise OSError("simulated interruption before atomic replace")

    monkeypatch.setattr(snapshot_module.os, "replace", fail_replace)
    with pytest.raises(ConsolidationError, match="HOLD_SNAPSHOT_WRITE_FAILED"):
        write_snapshot(second_engine, target)
    assert target.read_bytes() == previous_bytes
    assert not list(tmp_path.glob(".memory.snapshot.json.*.tmp"))


def test_file_restore_requires_explicit_digest_and_keeps_target_on_corruption(tmp_path: Path):
    source, events = populated_engine()
    path = tmp_path / "memory.snapshot.json"
    expected = write_snapshot(source, path)
    target, _ = populated_engine()
    before = target.to_snapshot()

    restore_snapshot_file(target, path, expected_sha256=expected)
    assert target.nodes == source.nodes
    assert target.links == source.links
    assert target.ingest_event_stream(events) == 0
    restored_bytes = target.to_snapshot()

    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ConsolidationError, match="HOLD_SNAPSHOT_SHA256_MISMATCH"):
        restore_snapshot_file(target, path, expected_sha256=expected)
    assert target.to_snapshot() == restored_bytes


def test_parser_rejects_resource_limits_unknown_versions_and_pickle_bytes():
    from core.memory_snapshot import MAX_SNAPSHOT_BYTES, MAX_SNAPSHOT_DEPTH

    engine, _ = populated_engine()
    raw_depth_exceeded = b"[" * (MAX_SNAPSHOT_DEPTH + 1) + b"]" * (MAX_SNAPSHOT_DEPTH + 1)
    with pytest.raises(ConsolidationError, match="HOLD_SNAPSHOT_NESTING_LIMIT"):
        ConsolidationEngine.from_snapshot(
            raw_depth_exceeded, expected_sha256=digest(raw_depth_exceeded)
        )

    oversized = b" " * (MAX_SNAPSHOT_BYTES + 1)
    with pytest.raises(ConsolidationError, match="HOLD_SNAPSHOT_BYTES_TOO_LARGE"):
        ConsolidationEngine.from_snapshot(oversized, expected_sha256=digest(oversized))

    document = json.loads(engine.to_snapshot())
    document["schema_version"] = 2
    candidate = json.dumps(
        document, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    with pytest.raises(ConsolidationError, match="HOLD_UNSUPPORTED_SNAPSHOT_VERSION"):
        ConsolidationEngine.from_snapshot(candidate, expected_sha256=digest(candidate))

    import pickle
    legacy_pickle = pickle.dumps(engine)
    with pytest.raises(ConsolidationError, match="HOLD_INVALID_SNAPSHOT_JSON"):
        ConsolidationEngine.from_snapshot(
            legacy_pickle, expected_sha256=digest(legacy_pickle)
        )


def test_parser_rejects_invalid_numeric_and_cross_reference_data():
    engine, _ = populated_engine()
    original = engine.to_snapshot()

    for mutate, error in (
        (lambda doc: doc["engine"].__setitem__("retrieval_threshold", True), "HOLD_INVALID_SNAPSHOT_RETRIEVAL_THRESHOLD"),
        (lambda doc: doc["engine"]["links"][0].__setitem__("to_node_id", "missing"), "HOLD_INVALID_SNAPSHOT_LINK_REFERENCE"),
        (lambda doc: doc["engine"]["nodes"][0].__setitem__("reinforcement_count", True), "HOLD_INVALID_SNAPSHOT_REINFORCEMENT_COUNT"),
    ):
        document = json.loads(original)
        mutate(document)
        candidate = json.dumps(
            document, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
        with pytest.raises(ConsolidationError, match=error):
            ConsolidationEngine.from_snapshot(
                candidate, expected_sha256=digest(candidate)
            )


def test_writer_enforces_reader_structure_budget(tmp_path, monkeypatch):
    import core.memory_snapshot as codec
    engine, _ = populated_engine()
    target = tmp_path / "memory.json"
    pin = write_snapshot(engine, target)
    previous = target.read_bytes()
    monkeypatch.setattr(codec, "MAX_SNAPSHOT_MARKERS", 1)
    with pytest.raises(ConsolidationError, match="HOLD_SNAPSHOT_STRUCTURE_LIMIT"):
        engine.to_snapshot()
    with pytest.raises(ConsolidationError, match="HOLD_SNAPSHOT_STRUCTURE_LIMIT"):
        write_snapshot(engine, target)
    assert target.read_bytes() == previous
    assert digest(previous) == pin


def test_restore_from_batch_generator_cannot_replace_existing_history():
    engine, events = populated_engine()
    previous = engine.to_snapshot()
    empty = ConsolidationEngine().to_snapshot()

    def reentrant():
        yield events[0]
        engine.restore_snapshot(empty, expected_sha256=digest(empty))

    with pytest.raises(ConsolidationError, match="HOLD_REENTRANT_SNAPSHOT_RESTORE"):
        engine.ingest_event_stream(reentrant())
    assert engine.to_snapshot() == previous
    assert engine.ingest_event_stream(events) == 0


def test_restore_during_active_batch_is_rejected(monkeypatch):
    engine, _ = populated_engine()
    previous = engine.to_snapshot()
    empty = ConsolidationEngine().to_snapshot()
    original = ConsolidationEngine._process_raw_event

    def reentrant(self, event_hash, event):
        original(self, event_hash, event)
        self.restore_snapshot(empty, expected_sha256=digest(empty))

    monkeypatch.setattr(ConsolidationEngine, "_process_raw_event", reentrant)
    with pytest.raises(ConsolidationError, match="HOLD_REENTRANT_SNAPSHOT_RESTORE"):
        engine.ingest_event_stream([event_row("new", "claim")])
    assert engine.to_snapshot() == previous
