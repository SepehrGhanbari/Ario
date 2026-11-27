"""Regression checks for exact source binding and transferred recall lineage."""
import hashlib
import pytest

from core.memory_consolidation import ConsolidationEngine
from core.memory_snapshot import encode_cognitive_memory_snapshot, decode_cognitive_memory_snapshot
from core.source_monitoring import SourceMonitoringGuard, SourceMonitoringError, SelfCitationError, VeracityState
from core.working_memory import WorkingMemoryBuffer, MetacognitiveVerdict


def empirical(guard):
    return guard.record_empirical_observation(
        assertion="tool_exit:run_tests:fixture:0", tool="run_tests", target="fixture",
        exit_code=0, stdout="PASS", execution_lock="fixture-lock")


def test_registered_source_cannot_ground_different_assertion_or_evict(tmp_path):
    guard = SourceMonitoringGuard()
    engine = ConsolidationEngine()
    wm = WorkingMemoryBuffer(capacity=1, source_guard=guard, consolidation_engine=engine)
    h = guard.create_hypothesis("keep this")
    wm.ingest("keep", h.assertion, h, salience=0.9)
    before = wm.active_chunks
    with pytest.raises(SourceMonitoringError, match="differs"):
        wm.ingest("unrelated", "unverified claim", empirical(guard), salience=1, step=42)
    assert wm.active_chunks == before and not wm.eviction_history
    assert not engine.nodes and wm._current_step == 0


def test_reingest_current_revision_refreshes_chunk_but_not_source_history():
    guard = SourceMonitoringGuard()
    wm = WorkingMemoryBuffer(source_guard=guard)
    h = guard.create_hypothesis("claim")
    wm.ingest("topic", h.assertion, h)
    t = guard.create_external_testimony("other")
    with pytest.raises(SelfCitationError):
        guard.evaluate_claim_promotion(h.attribution_id, [t.attribution_id])
    revised = guard.attributions[h.attribution_id]
    assert revised.veracity_state == VeracityState.UNSUPPORTED
    before = guard.attribution_history(h.attribution_id)
    returned = wm.ingest("topic", revised.assertion, revised)
    assert returned.source_attribution == revised
    assert wm.active_chunks[0].source_attribution == revised
    assert guard.attribution_history(h.attribution_id) == before
    assert len(before) == 2


@pytest.mark.parametrize("guarded", [True, False])
def test_transferred_recall_never_creates_new_ledger_hash(guarded):
    engine = ConsolidationEngine()
    engine.ingest_event_stream([("1"*64, {"concept": "door", "assertion": "open"})])
    guard = SourceMonitoringGuard() if guarded else None
    original = WorkingMemoryBuffer(consolidation_engine=engine, source_guard=guard)
    recalled = original.recall_from_long_term("door")[0]
    before = engine.to_snapshot()
    second = WorkingMemoryBuffer(consolidation_engine=engine, source_guard=guard)
    # Ordinary public ingest, not the special recall method, and no metadata.
    second.ingest(recalled.concept, recalled.assertion, recalled.source_attribution, salience=0.9)
    assert second.flush_to_long_term() == []
    assert engine.to_snapshot() == before
    assert second.metacognitive_assessment().empirical_ratio == 0


def test_recovered_recall_source_is_still_not_new_evidence():
    engine = ConsolidationEngine()
    guard = SourceMonitoringGuard()
    engine.ingest_event_stream([("1"*64, {"concept": "door", "assertion": "open"})])
    original = WorkingMemoryBuffer(consolidation_engine=engine, source_guard=guard)
    recalled = original.recall_from_long_term("door")[0]
    snap = encode_cognitive_memory_snapshot(engine, guard)
    recovered, sources = decode_cognitive_memory_snapshot(
        ConsolidationEngine, snap, expected_sha256=hashlib.sha256(snap).hexdigest(),
        allowlisted_tools={"run_tests"})
    second = WorkingMemoryBuffer(consolidation_engine=recovered, source_guard=sources)
    second.ingest("door", "open", sources.attributions[recalled.source_attribution.attribution_id],
                  salience=1)
    assert second.flush_to_long_term() == []
    assert encode_cognitive_memory_snapshot(recovered, sources) == snap
    assert second.metacognitive_assessment().verdict == MetacognitiveVerdict.UNGROUNDED_HYPOTHESIS


def test_transferred_recall_without_parent_cannot_report_sufficient_grounding():
    engine = ConsolidationEngine()
    guard = SourceMonitoringGuard()
    engine.ingest_event_stream([("1"*64, {"concept": "door", "assertion": "open"})])
    recalled = WorkingMemoryBuffer(consolidation_engine=engine, source_guard=guard).recall_from_long_term("door")[0]
    fresh = ConsolidationEngine()
    second = WorkingMemoryBuffer(consolidation_engine=fresh, source_guard=guard)
    second.ingest("door", "open", recalled.source_attribution, salience=0.9)
    e = empirical(guard)
    second.ingest("test", e.assertion, e, salience=0.9)
    report = second.metacognitive_assessment()
    assert report.verdict == MetacognitiveVerdict.PARTIAL_NEEDS_RECALL
    assert "UNRESOLVED_RECALL_LINEAGE: 1" in report.diagnostics
