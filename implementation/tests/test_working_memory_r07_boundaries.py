"""R07: explicit trust boundaries in research WorkingMemoryBuffer.

Source: independent synthetic RED cases on PR #288 before this fix.
Every test is an expectation for the *research candidate*, not production.
"""
from __future__ import annotations

from datetime import datetime, timezone
import time

import pytest

from core.memory_consolidation import ConsolidationEngine, NodeEpistemicStatus
from core.source_monitoring import (
    EmpiricalProvenance,
    SourceAttribution,
    SourceMonitoringError,
    SourceMonitoringGuard,
    SourceType,
    VeracityState,
)
from core.working_memory import WorkingMemoryBuffer, MetacognitiveVerdict


def _unregistered_empirical(
    aid: str = "NOT-ADMITTED",
    assertion: str = "synthetic witness is independently fresh",
) -> SourceAttribution:
    return SourceAttribution(
        attribution_id=aid,
        assertion=assertion,
        source_type=SourceType.EMPIRICAL_OBSERVATION,
        veracity_state=VeracityState.VERIFIED_EMPIRICAL,
        provenance=EmpiricalProvenance(
            tool="NOT_AN_ALLOWED_EXECUTION",
            target="none",
            exit_code=0,
            execution_lock_sha256="a" * 64,
            stdout_sha256="b" * 64,
            recorded_at=datetime.now(timezone.utc).isoformat(),
        ),
    )


def _registered_empirical(guard: SourceMonitoringGuard, aid: str = "OBS-1"):
    return guard.record_empirical_observation(
        assertion="tool_exit:run_tests:synthetic-r07:0",
        tool="run_tests",
        target="synthetic-r07",
        exit_code=0,
        stdout="test passed",
        execution_lock="synthetic-execution-lock",
        attribution_id=aid,
    )


def test_reject_unregistered_self_declared_empirical_before_mutating_state():
    guard = SourceMonitoringGuard()
    wm = WorkingMemoryBuffer(source_guard=guard, capacity=1)
    good = guard.create_hypothesis("keep me", attribution_id="GOOD")
    wm.ingest("keep", good.assertion, good, salience=0.6)
    previous = wm.active_chunks[0].chunk_id
    with pytest.raises(SourceMonitoringError):
        wm.ingest("bad", "synthetic witness is independently fresh", _unregistered_empirical(), salience=0.9)
    assert wm.active_count == 1
    assert wm.active_chunks[0].chunk_id == previous
    assert len(wm.eviction_history) == 0


def test_reject_same_registered_id_with_different_payload():
    guard = SourceMonitoringGuard()
    good = _registered_empirical(guard, "EMP-ID")
    assert good.attribution_id in guard.attributions
    wm = WorkingMemoryBuffer(source_guard=guard)
    impostor = _unregistered_empirical(aid="EMP-ID", assertion=good.assertion)
    with pytest.raises(SourceMonitoringError):
        wm.ingest("x", good.assertion, impostor, salience=1)
    assert wm.active_count == 0


def test_original_genuine_registered_empirical_remains_focus_eligible():
    guard = SourceMonitoringGuard()
    good = _registered_empirical(guard)
    wm = WorkingMemoryBuffer(source_guard=guard)
    chunk = wm.ingest("test", good.assertion, good, salience=0.9)
    assert chunk.source_attribution.attribution_id == good.attribution_id
    assert wm.metacognitive_assessment().verdict == MetacognitiveVerdict.FOCUSED_SUFFICIENCY
    assert wm.metacognitive_assessment().empirical_ratio == 1.0


def test_absent_guard_does_not_warrant_verified_empirical_readiness():
    wm = WorkingMemoryBuffer()
    bad = _unregistered_empirical()
    wm.ingest("unverified", bad.assertion, bad, salience=1.0)
    a = wm.metacognitive_assessment()
    assert a.verdict != MetacognitiveVerdict.FOCUSED_SUFFICIENCY
    assert a.empirical_ratio == 0


def test_exposed_active_chunks_are_defensive_snapshots():
    guard = SourceMonitoringGuard()
    original = guard.create_hypothesis("guess", attribution_id="HYP-ORIGINAL")
    wm = WorkingMemoryBuffer(source_guard=guard)
    wm.ingest("concept", original.assertion, original, salience=0.5)
    outside = wm.active_chunks[0]
    outside.source_attribution = _unregistered_empirical()
    outside.salience = 1.0
    outside.metadata["forged"] = True
    current = wm.active_chunks[0]
    assert current.source_attribution.attribution_id == "HYP-ORIGINAL"
    assert current.salience == 0.5
    assert "forged" not in current.metadata
    assert wm.metacognitive_assessment().verdict == MetacognitiveVerdict.UNGROUNDED_HYPOTHESIS


def test_returned_ingest_chunk_and_nested_metadata_cannot_tamper_state():
    guard = SourceMonitoringGuard()
    h = guard.create_hypothesis("guess", attribution_id="HYP-RET")
    wm = WorkingMemoryBuffer(source_guard=guard)
    chunk = wm.ingest("concept", h.assertion, h, metadata={"nested": {"v": 1}})
    chunk.metadata["nested"]["v"] = 99
    chunk.source_attribution = _unregistered_empirical()
    assert wm.active_chunks[0].metadata["nested"]["v"] == 1
    assert wm.active_chunks[0].source_attribution.attribution_id == "HYP-RET"


def test_unverified_flush_is_only_structurally_recorded_not_truth():
    engine = ConsolidationEngine(node_id_version="v2")
    wm = WorkingMemoryBuffer(consolidation_engine=engine)
    h = SourceAttribution(
        attribution_id="HYP-RECORDED",
        assertion="no authentic independent witness",
        source_type=SourceType.INTERNAL_HYPOTHESIS,
        veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
    )
    wm.ingest("check", h.assertion, h, salience=0.9)
    assert len(wm.flush_to_long_term()) == 1
    node = next(iter(engine.nodes.values()))
    assert node.status == NodeEpistemicStatus.RECORDED


def test_repeated_flush_must_be_idempotent_per_source_unit():
    engine = ConsolidationEngine(node_id_version="v2")
    wm = WorkingMemoryBuffer(consolidation_engine=engine)
    h = SourceAttribution(
        attribution_id="HYP-ONE",
        assertion="one unverified statement",
        source_type=SourceType.INTERNAL_HYPOTHESIS,
        veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
    )
    wm.ingest("x", h.assertion, h, salience=0.9)
    assert len(wm.flush_to_long_term()) == 1
    for _ in range(3):
        time.sleep(0.002)
        assert wm.flush_to_long_term() == []
    node = next(iter(engine.nodes.values()))
    assert node.reinforcement_count == 1
    assert len(node.source_event_hashes) == 1
    assert wm.active_count == 1


def test_eviction_after_flush_does_not_generate_fake_extra_evidence():
    engine = ConsolidationEngine(node_id_version="v2")
    wm = WorkingMemoryBuffer(capacity=1, consolidation_engine=engine)
    h = SourceAttribution(
        attribution_id="HYP-REUSED",
        assertion="single observation",
        source_type=SourceType.INTERNAL_HYPOTHESIS,
        veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
    )
    wm.ingest("x", h.assertion, h, salience=0.9)
    wm.flush_to_long_term()
    other = SourceAttribution(
        attribution_id="HYP-NEXT",
        assertion="another",
        source_type=SourceType.INTERNAL_HYPOTHESIS,
        veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
    )
    wm.ingest("new", other.assertion, other, salience=0.1)
    node = engine.retrieve_active_context("x")[0]
    assert node.reinforcement_count == 1
    assert len(node.source_event_hashes) == 1


def test_recall_is_hypothesis_not_automatically_accepted_proof():
    engine = ConsolidationEngine(node_id_version="v2")
    engine.ingest_event_stream([(
        "1" * 64, {"concept": "history", "assertion": "previously accepted long-term item", "status": "ACCEPTED"}
    )])
    guard = SourceMonitoringGuard()
    wm = WorkingMemoryBuffer(consolidation_engine=engine, source_guard=guard)
    recalled = wm.recall_from_long_term("history")
    assert len(recalled) == 1
    assert recalled[0].source_attribution.veracity_state == VeracityState.UNVERIFIED_HYPOTHESIS
    assert guard.attributions[recalled[0].source_attribution.attribution_id] == recalled[0].source_attribution
    assert wm.metacognitive_assessment().empirical_ratio == 0.0


def test_reingest_existing_chunk_must_still_validate_source():
    guard = SourceMonitoringGuard()
    h = guard.create_hypothesis("guess", attribution_id="HYP-R")
    wm = WorkingMemoryBuffer(source_guard=guard)
    original = wm.ingest("x", h.assertion, h, salience=0.4)
    spoof = SourceAttribution(
        attribution_id="HYP-R", assertion="guess",
        source_type=SourceType.INTERNAL_HYPOTHESIS,
        veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
        parent_attribution_ids=("forged-extra-parent",),
    )
    with pytest.raises(SourceMonitoringError):
        wm.ingest("x", "guess", spoof, salience=1.0)
    a = wm.active_chunks[0]
    assert a.access_count == 1
    assert a.salience == 0.4
    assert a.chunk_id == original.chunk_id


def test_fresh_working_memory_replay_cannot_reinforce_same_engine_evidence():
    """New buffer instance, same event anchor: still only one semantic source."""
    engine = ConsolidationEngine(node_id_version="v2")
    h = SourceAttribution(
        attribution_id="HYP-STABLE-CROSS-BUFFER",
        assertion="one stable unverified observation",
        source_type=SourceType.INTERNAL_HYPOTHESIS,
        veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
    )
    for _ in range(2):
        wm = WorkingMemoryBuffer(consolidation_engine=engine)
        wm.ingest("stable-topic", h.assertion, h, salience=0.95)
        assert len(wm.flush_to_long_term()) == 1
    node = next(iter(engine.nodes.values()))
    assert node.reinforcement_count == 1
    assert len(node.source_event_hashes) == 1
    assert node.status == NodeEpistemicStatus.RECORDED


def test_eviction_history_returns_defensive_snapshot_not_mutable_authority():
    """Inspection may not mutate even volatile research eviction history."""
    wm = WorkingMemoryBuffer(capacity=1)
    for i in range(2):
        a = SourceAttribution(
            attribution_id=f"UNCHECKED-{i}",
            assertion=f"synthetic claim {i}",
            source_type=SourceType.INTERNAL_HYPOTHESIS,
            veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
        )
        wm.ingest(f"concept-{i}", a.assertion, a, salience=0.1)
    assert len(wm.eviction_history) == 1
    snapshot = wm.eviction_history[0]
    snapshot.reason = "FORGED_REWRITE_OF_REASON"
    snapshot.final_salience = 1.0
    assert wm.eviction_history[0].reason == "capacity_limit_exceeded"
    assert wm.eviction_history[0].final_salience == 0.1
