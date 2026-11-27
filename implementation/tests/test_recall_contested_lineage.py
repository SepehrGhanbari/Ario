"""Preserve historical contestation and lineage during existing LTM recall."""
import hashlib

from core.memory_consolidation import ConsolidationEngine, NodeEpistemicStatus
from core.memory_snapshot import encode_cognitive_memory_snapshot, decode_cognitive_memory_snapshot
from core.source_monitoring import SourceMonitoringGuard, VeracityState
from core.working_memory import WorkingMemoryBuffer, MetacognitiveVerdict


def original(engine):
    engine.ingest_event_stream([("1" * 64, {"concept": "door", "assertion": "open"})])
    return next(iter(engine.nodes.values()))


def dispute(engine, node):
    engine.ingest_event_stream([("2" * 64, {"concept": "door", "assertion": "closed",
                                          "negates": node.node_id})])


def test_recall_contested_single_chunk_retains_original_source():
    engine = ConsolidationEngine()
    guard = SourceMonitoringGuard()
    node = original(engine)
    dispute(engine, node)
    wm = WorkingMemoryBuffer(capacity=1, consolidation_engine=engine, source_guard=guard)
    wm.recall_from_long_term("door")
    assert wm.active_count == 1
    chunk = wm.active_chunks[0]
    parent = engine.get_node(chunk.source_attribution.parent_attribution_ids[0])
    assert parent.status == NodeEpistemicStatus.CONTESTED
    assert chunk.metadata["ltm_status_at_recall"] == "CONTESTED"
    assert chunk.metadata["ltm_source_event_hashes_at_recall"] == parent.source_event_hashes
    assert chunk.source_attribution.veracity_state == VeracityState.UNVERIFIED_HYPOTHESIS
    report = wm.metacognitive_assessment()
    assert report.verdict == MetacognitiveVerdict.CONTRADICTION_DETECTED
    assert report.contradiction_count == 1
    assert report.empirical_ratio == 0
    assert wm.flush_to_long_term() == []
    assert len(engine.known_ledger_hashes) == 2


def test_later_contestation_overrides_old_recall_metadata():
    engine = ConsolidationEngine()
    guard = SourceMonitoringGuard()
    node = original(engine)
    wm = WorkingMemoryBuffer(consolidation_engine=engine, source_guard=guard)
    chunk = wm.recall_from_long_term("door")[0]
    assert chunk.metadata["ltm_status_at_recall"] == "RECORDED"
    emp = guard.record_empirical_observation(
        assertion="tool_exit:run_tests:fixture:0", tool="run_tests", target="fixture",
        exit_code=0, stdout="PASS", execution_lock="fixture-lock")
    wm.ingest("test", emp.assertion, emp, salience=0.9)
    assert wm.metacognitive_assessment().verdict == MetacognitiveVerdict.FOCUSED_SUFFICIENCY
    dispute(engine, node)
    assert wm.metacognitive_assessment().verdict == MetacognitiveVerdict.CONTRADICTION_DETECTED
    assert wm.active_chunks[0].metadata["ltm_status_at_recall"] == "RECORDED"


def test_recovered_memory_retains_historical_dispute_without_empirical_promotion():
    engine = ConsolidationEngine()
    guard = SourceMonitoringGuard()
    dispute(engine, original(engine))
    snap = encode_cognitive_memory_snapshot(engine, guard)
    recovered, sources = decode_cognitive_memory_snapshot(
        ConsolidationEngine, snap, expected_sha256=hashlib.sha256(snap).hexdigest(),
        allowlisted_tools={"run_tests"})
    wm = WorkingMemoryBuffer(consolidation_engine=recovered, source_guard=sources)
    chunks = wm.recall_from_long_term("door")
    assert len(chunks) == 2
    assert all(c.metadata["ltm_status_at_recall"] == "CONTESTED" for c in chunks)
    assert wm.metacognitive_assessment().contradiction_count == 1
    assert wm.metacognitive_assessment().empirical_ratio == 0
    assert wm.flush_to_long_term() == []


def test_unresolved_recall_cannot_report_sufficient_grounding():
    engine = ConsolidationEngine()
    guard = SourceMonitoringGuard()
    original(engine)
    wm = WorkingMemoryBuffer(consolidation_engine=engine, source_guard=guard)
    wm.recall_from_long_term("door")
    emp = guard.record_empirical_observation(
        assertion="tool_exit:run_tests:fixture:0", tool="run_tests", target="fixture",
        exit_code=0, stdout="PASS", execution_lock="fixture-lock")
    wm.ingest("test", emp.assertion, emp, salience=0.9)
    wm.consolidation_engine = ConsolidationEngine()
    report = wm.metacognitive_assessment()
    assert report.verdict == MetacognitiveVerdict.PARTIAL_NEEDS_RECALL
    assert "UNRESOLVED_RECALL_LINEAGE: 1" in report.diagnostics


def test_untrusted_metadata_does_not_create_historical_contestation():
    engine = ConsolidationEngine()
    guard = SourceMonitoringGuard()
    node = original(engine)
    wm = WorkingMemoryBuffer(consolidation_engine=engine, source_guard=guard)
    attr = guard.create_hypothesis("unrelated")
    wm.ingest("unrelated", attr.assertion, attr, metadata={
        "recalled_from_ltm": True, "ltm_node_id": node.node_id,
        "ltm_status_at_recall": "CONTESTED"})
    assert wm.metacognitive_assessment().verdict == MetacognitiveVerdict.UNGROUNDED_HYPOTHESIS
