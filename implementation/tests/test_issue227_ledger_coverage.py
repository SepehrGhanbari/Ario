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
    assert not engine.inspect_ledger_integrity(p).is_clean
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
