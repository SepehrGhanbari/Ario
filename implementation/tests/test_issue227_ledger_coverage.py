"""Issue #227 targeted structural coverage / lineage / framing regression tests."""
import hashlib
import json

import pytest

from core.memory_consolidation import ConsolidationEngine, ConsolidationError, NodeEpistemicStatus
from core.ledger_memory_bridge import EpistemicLedgerBridge, BridgeError


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def test_coverage_and_hash_aliases_preserve_legacy_identity(tmp_path):
    records = [
        {"event": "TASK_STARTED", "task_id": "t", "goal": "Inspect safely"},
        {"event": "STEP_OBSERVED", "task_id": "t", "tool": "file_fingerprint", "status": "COMPLETED"},
        {"event": "TASK_FINISHED", "task_id": "t", "status": "COMPLETED"},
    ]
    raw = [json.dumps(r).encode() + end for r, end in zip(records, [b"\r\n", b"\n", b"\n"])]
    p = tmp_path / "events.jsonl"
    p.write_bytes(b"".join(raw))
    engine = ConsolidationEngine()
    report = engine.ingest_ledger_file_with_coverage(p)
    assert (report.records_seen, report.records_structurally_valid, report.records_newly_ingested) == (3, 3, 3)
    assert (report.semantic_nodes_created_or_reinforced, report.skipped_unmapped_events, report.replayed_events) == (1, 2, 0)
    assert [x.outcome for x in report.lines] == ["SEMANTIC_LINKED", "UNMAPPED_EMPTY_ASSERTION", "UNMAPPED_EMPTY_ASSERTION"]
    assert [x.line_number for x in report.lines] == [1, 2, 3]
    for item, original in zip(report.lines, raw):
        assert item.raw_line_sha256 == digest(original)
        assert item.legacy_trimmed_sha256 == digest(original.strip())
    node = next(iter(engine.nodes.values()))
    assert node.source_event_hashes == (digest(raw[0].strip()),)
    assert node.status == NodeEpistemicStatus.RECORDED
    replay = engine.ingest_ledger_file_with_coverage(p)
    assert replay.replayed_events == 3
    assert replay.records_newly_ingested == 0
    assert replay.semantic_nodes_created_or_reinforced == 0
    assert p.read_bytes() == b"".join(raw)
    assert ConsolidationEngine().ingest_ledger_file(p) == 3


def test_same_legacy_hash_can_have_distinct_raw_line_digests(tmp_path):
    p = tmp_path / "events.jsonl"
    line = b'{"goal":"check"}'
    p.write_bytes(line + b"\n" + line + b"\r\n")
    result = ConsolidationEngine().ingest_ledger_file_with_coverage(p)
    a, b = result.lines
    assert a.legacy_trimmed_sha256 == b.legacy_trimmed_sha256
    assert a.raw_line_sha256 != b.raw_line_sha256
    assert (a.outcome, b.outcome) == ("SEMANTIC_LINKED", "REPLAY")


@pytest.mark.parametrize("tail", [b'{"goal":"unfinished"}', b'{"goal":', b" "])
def test_partial_tail_refused_before_any_memory_or_guard_mutation(tmp_path, tail):
    p = tmp_path / "events.jsonl"
    source = b'{"event":"TASK_STARTED","task_id":"t","goal":"ok"}\n' + tail
    p.write_bytes(source)
    engine = ConsolidationEngine()
    before = engine.to_snapshot()
    with pytest.raises(ConsolidationError, match="HOLD_INCOMPLETE_JSONL_LINE"):
        engine.ingest_ledger_file_with_coverage(p)
    assert engine.to_snapshot() == before
    report = engine.inspect_ledger_integrity(p)
    assert not report.is_clean
    assert report.valid_lines == 1
    if tail == b'{"goal":':
        # Unparseable crash tail keeps the historical line-numbered corrupt report.
        assert report.corrupt_line_no == 2
        assert report.diagnostic.startswith("CORRUPT_JSON_OR_TRUNCATED_TAIL")
    else:
        assert report.corrupt_line_no is None
        assert report.diagnostic.startswith("HOLD_INCOMPLETE_JSONL_LINE")
    bridge = EpistemicLedgerBridge()
    with pytest.raises(BridgeError, match="HOLD_INCOMPLETE_JSONL_LINE"):
        bridge.ingest_agent_ledger(p)
    assert not bridge.engine.nodes
    assert not bridge.guard.attributions
    assert p.read_bytes() == source


def test_empty_and_blank_lines_are_not_semantic_records(tmp_path):
    p = tmp_path / "events.jsonl"
    p.write_bytes(b"\n\r\n")
    report = ConsolidationEngine().ingest_ledger_file_with_coverage(p)
    assert report.blank_lines == 2
    assert report.records_seen == 0
    assert report.lines == ()


def test_legacy_and_raw_digests_roundtrip_without_alias_selection(tmp_path):
    from core.memory_consolidation import ledger_line_digests
    line = b'{"event":"TASK_STARTED","task_id":"t1","goal":"same"}'
    variants = [line + b"\n", line + b"\r\n", b"  " + line + b"  \n"]
    pairs = [ledger_line_digests(v) for v in variants]
    assert {p[0] for p in pairs} == {digest(line)}
    assert {p[1] for p in pairs} == {digest(v) for v in variants}
    p = tmp_path / "roundtrip.jsonl"
    p.write_bytes(b"".join(variants))
    engine = ConsolidationEngine()
    report = engine.ingest_ledger_file_with_coverage(p)
    assert (report.records_newly_ingested, report.replayed_events) == (1, 2)
    assert engine.known_ledger_hashes == {digest(line)}
    snap = engine.to_snapshot()
    recovered = ConsolidationEngine.from_snapshot(snap, expected_sha256=digest(snap))
    assert next(iter(recovered.nodes.values())).source_event_hashes == (digest(line),)
    again = recovered.ingest_ledger_file_with_coverage(p)
    assert (again.records_newly_ingested, again.replayed_events) == (0, 3)


@pytest.mark.parametrize("failure", ["malformed", "rejected", "after_attribution"])
def test_bridge_commit_is_atomic_across_memory_and_guard(tmp_path, monkeypatch, failure):
    from core.source_monitoring import SourceMonitoringError
    from core.memory_snapshot import encode_cognitive_memory_snapshot
    bridge = EpistemicLedgerBridge()
    good = tmp_path / "good.jsonl"
    good.write_bytes(b'{"event":"TASK_STARTED","task_id":"g1","goal":"safe inspect"}\n')
    bridge.ingest_agent_ledger(good)
    bridge.guard.record_empirical_observation(
        "tool_exit:run_tests:sample:0", "run_tests", "sample", 0, "out", "lock",
        attribution_id="existing-active")
    before = encode_cognitive_memory_snapshot(bridge.engine, bridge.guard)
    active = set(bridge.guard._active_verified_ids)
    assert "existing-active" in active
    locks = (bridge.engine._batch_lock, bridge.guard._lock)
    registry_before = dict(bridge.registry._intentions)
    bad = tmp_path / "bad.jsonl"
    prefix = b'{"event":"TASK_STARTED","task_id":"b1","goal":"partial"}\n'
    if failure == "malformed":
        bad.write_bytes(prefix + b'{not-json\n')
        exc = BridgeError
    elif failure == "rejected":
        bad.write_bytes(prefix + b'{"event":"STEP_OBSERVED","tool":"not_allowlisted_tool"}\n')
        exc = SourceMonitoringError
    else:
        bad.write_bytes(prefix)
        def fail_after_attribution(*args, **kwargs):
            assert len(bridge.guard.attributions) > 2
            raise KeyboardInterrupt("injected after attribution")
        monkeypatch.setattr(bridge.engine, "ingest_event_stream", fail_after_attribution)
        exc = KeyboardInterrupt
    with pytest.raises(exc):
        bridge.ingest_agent_ledger(bad)
    assert encode_cognitive_memory_snapshot(bridge.engine, bridge.guard) == before
    assert bridge.guard._active_verified_ids == active
    assert (bridge.engine._batch_lock, bridge.guard._lock) == locks
    assert bridge.registry._intentions == registry_before


def test_bridge_conflicting_history_replays_after_joint_recovery(tmp_path):
    from core.memory_snapshot import encode_cognitive_memory_snapshot, decode_cognitive_memory_snapshot
    from core.ledger_memory_bridge import EpistemicLedgerBridge
    p = tmp_path / "conflicts.jsonl"
    lines = [json.dumps({"event":"STEP_OBSERVED", "tool":"file_fingerprint",
                         "result":{"path":"x","sha256":v * 64}}).encode()
             for v in ("1", "2")]
    p.write_bytes(b"\n".join(lines) + b"\n")
    bridge = EpistemicLedgerBridge()
    assert bridge.ingest_agent_ledger(p).contested_nodes_count == 2
    snap = encode_cognitive_memory_snapshot(bridge.engine, bridge.guard)
    engine, guard = decode_cognitive_memory_snapshot(
        ConsolidationEngine, snap, expected_sha256=digest(snap),
        allowlisted_tools={"file_fingerprint"})
    recovered = EpistemicLedgerBridge(consolidation_engine=engine, source_guard=guard)
    p.write_bytes(b"\r\n".join(lines) + b"\r\n")
    assert recovered.ingest_agent_ledger(p).contested_nodes_count == 2
    assert encode_cognitive_memory_snapshot(engine, guard) == snap
