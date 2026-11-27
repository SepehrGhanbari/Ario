"""Resolve existing historical source references without new evidence or migration."""
import hashlib
from core.memory_consolidation import ConsolidationEngine
from core.memory_snapshot import encode_cognitive_memory_snapshot, decode_cognitive_memory_snapshot
from core.source_monitoring import SourceMonitoringGuard, SelfCitationError
from core.working_memory import WorkingMemoryBuffer
from core.ledger_memory_bridge import EpistemicLedgerBridge
from ario_agent import run_task
import pytest


def test_recover_original_revision_after_source_changes_and_snapshot():
    engine, guard = ConsolidationEngine(), SourceMonitoringGuard()
    h = guard.create_hypothesis("historical claim", attribution_id="origin")
    wm = WorkingMemoryBuffer(consolidation_engine=engine, source_guard=guard)
    wm.ingest("topic", h.assertion, h, salience=.9)
    wm.flush_to_long_term()
    testimony = guard.create_external_testimony("different")
    with pytest.raises(SelfCitationError):
        guard.evaluate_claim_promotion("origin", [testimony.attribution_id])
    snap = encode_cognitive_memory_snapshot(engine, guard)
    recovered, sources = decode_cognitive_memory_snapshot(
        ConsolidationEngine, snap, expected_sha256=hashlib.sha256(snap).hexdigest(),
        allowlisted_tools={"run_tests"})
    wm = WorkingMemoryBuffer(consolidation_engine=recovered, source_guard=sources)
    chunk = wm.recall_from_long_term("topic")[0]
    before = encode_cognitive_memory_snapshot(recovered, sources)
    report = wm.inspect_recalled_lineage(chunk.chunk_id)
    row = report["sources"][0]
    assert row["status"] == "MATCHED_WM_EVENT"
    assert row["revision_candidates"] == [{"attribution_id": "origin", "revision_index": 0,
                                         "historical_veracity": "UNVERIFIED_HYPOTHESIS"}]
    assert report["claim_truth"] == report["source_authentication"] == "UNKNOWN"
    assert report["independent_admission_authority"] == "NONE"
    assert encode_cognitive_memory_snapshot(recovered, sources) == before


def test_agent_lineage_returns_reference_not_authenticated_bytes(tmp_path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    ledger = tmp_path / "events.jsonl"
    run_task({"task_id": "T", "goal": "read", "actions": [
        {"step_id": "s", "tool": "file_fingerprint", "path": "a.txt"}]}, tmp_path, ledger)
    bridge = EpistemicLedgerBridge()
    bridge.ingest_agent_ledger(ledger)
    wm = WorkingMemoryBuffer(consolidation_engine=bridge.engine, source_guard=bridge.guard)
    chunk = wm.recall_from_long_term("agent_tool:file_fingerprint")[0]
    report = wm.inspect_recalled_lineage(chunk.chunk_id)
    row = report["sources"][0]
    assert row["status"] == "LEDGER_REFERENCE_ONLY"
    assert row["ledger_report_id"] == "ATTR-LEDGER-" + row["event_sha256"]
    assert report["status"] == "PARTIAL_OR_UNRESOLVED"


def test_unmapped_hash_is_not_inferred_from_matching_text():
    engine, guard = ConsolidationEngine(), SourceMonitoringGuard()
    guard.create_hypothesis("same text", attribution_id="unrelated")
    engine.ingest_event_stream([("1"*64, {"concept": "topic", "assertion": "same text"})])
    wm = WorkingMemoryBuffer(consolidation_engine=engine, source_guard=guard)
    chunk = wm.recall_from_long_term("topic")[0]
    assert wm.inspect_recalled_lineage(chunk.chunk_id)["sources"][0]["status"] == "UNKNOWN"
    assert wm.inspect_recalled_lineage("missing")["status"] == "UNKNOWN"


def test_same_status_revisions_are_not_falsely_distinguished():
    engine, guard = ConsolidationEngine(), SourceMonitoringGuard()
    h = guard.create_hypothesis("claim", attribution_id="origin")
    for aid in ("a", "b"):
        t = guard.create_external_testimony(aid, attribution_id=aid)
        with pytest.raises(SelfCitationError):
            guard.evaluate_claim_promotion("origin", [t.attribution_id])
        if aid == "a":
            wm = WorkingMemoryBuffer(consolidation_engine=engine, source_guard=guard)
            revised = guard.attributions["origin"]
            wm.ingest("topic", revised.assertion, revised, salience=.9)
            wm.flush_to_long_term()
    reader = WorkingMemoryBuffer(consolidation_engine=engine, source_guard=guard)
    chunk = reader.recall_from_long_term("topic")[0]
    row = reader.inspect_recalled_lineage(chunk.chunk_id)["sources"][0]
    assert row["status"] == "AMBIGUOUS_HISTORICAL_REVISION"
    assert row["matching_revision_count"] == 2


def test_large_hash_set_reports_unknown_without_partial_success():
    engine, guard = ConsolidationEngine(), SourceMonitoringGuard()
    engine.ingest_event_stream([(f"{i:064x}", {"concept":"topic", "assertion":"claim"})
                                for i in range(257)])
    wm = WorkingMemoryBuffer(consolidation_engine=engine, source_guard=guard)
    chunk = wm.recall_from_long_term("topic")[0]
    report = wm.inspect_recalled_lineage(chunk.chunk_id)
    assert report["status"] == "UNKNOWN" and not report["sources"]
    assert report["reason"] == "LINEAGE_INSPECTION_LIMIT"
