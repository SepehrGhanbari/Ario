"""Comprehensive Falsifiable Tests for Ario Working Memory Buffer (Module 4).

Tests operationalization of Cowan's K=4 chunk capacity, Baddeley's episodic buffer,
salience decay, adaptive forgetting, LTM consolidation, and metacognitive monitoring.
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest

from core.memory_consolidation import ConsolidationEngine, NodeEpistemicStatus
from core.source_monitoring import (
    SourceAttribution,
    SourceMonitoringGuard,
    SourceType,
    VeracityState,
    SourceMonitoringError,
    EmpiricalProvenance,
)
from core.working_memory import (
    ChunkState,
    MetacognitiveVerdict,
    WorkingMemoryBuffer,
    WorkingMemoryChunk,
)


@pytest.fixture
def consolidation_engine() -> ConsolidationEngine:
    return ConsolidationEngine(node_id_version="v2")


@pytest.fixture
def source_guard() -> SourceMonitoringGuard:
    return SourceMonitoringGuard()


def make_attribution(
    assertion: str,
    veracity: VeracityState = VeracityState.VERIFIED_EMPIRICAL,
    source_type: SourceType = SourceType.EMPIRICAL_OBSERVATION,
    attr_id: str = "attr_test",
) -> SourceAttribution:
    provenance = None
    if veracity == VeracityState.VERIFIED_EMPIRICAL:
        provenance = EmpiricalProvenance(
            tool="run_tests",
            target="tests/test_m0.py",
            exit_code=0,
            execution_lock_sha256="a" * 64,
            stdout_sha256="b" * 64,
            recorded_at=datetime.now(timezone.utc).isoformat(),
        )
    return SourceAttribution(
        attribution_id=attr_id,
        source_type=source_type,
        assertion=assertion,
        veracity_state=veracity,
        provenance=provenance,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def test_capacity_strictly_bounded_cowan_four(consolidation_engine: ConsolidationEngine):
    """Invariant: Working memory buffer never exceeds Cowan K=4 chunks simultaneously."""
    buf = WorkingMemoryBuffer(capacity=4, consolidation_engine=consolidation_engine)
    assert buf.capacity == 4
    assert buf.active_count == 0

    # Ingest 4 distinct chunks
    for i in range(1, 5):
        attr = make_attribution(f"assertion_{i}", attr_id=f"attr_{i}")
        chunk = buf.ingest(concept=f"concept_{i}", assertion=f"assertion_{i}", source_attribution=attr, salience=0.5)
        assert chunk.state == ChunkState.ACTIVE

    assert buf.active_count == 4
    assert len(buf.eviction_history) == 0

    # Ingest 5th chunk -> Must trigger eviction of one chunk to maintain K=4
    attr5 = make_attribution("assertion_5", attr_id="attr_5")
    buf.ingest(concept="concept_5", assertion="assertion_5", source_attribution=attr5, salience=0.8)

    assert buf.active_count == 4
    assert len(buf.eviction_history) == 1
    assert buf.eviction_history[0].reason == "capacity_limit_exceeded"


def test_eviction_promotes_high_salience_to_ltm(consolidation_engine: ConsolidationEngine):
    """Invariant: Evicted chunk with high salience or empirical status consolidates to Long-Term Memory."""
    buf = WorkingMemoryBuffer(capacity=2, consolidation_engine=consolidation_engine, consolidation_threshold=0.6)

    attr1 = make_attribution("verified statement 1", veracity=VeracityState.VERIFIED_EMPIRICAL, attr_id="attr_1")
    attr2 = make_attribution("verified statement 2", veracity=VeracityState.VERIFIED_EMPIRICAL, attr_id="attr_2")
    attr3 = make_attribution("verified statement 3", veracity=VeracityState.VERIFIED_EMPIRICAL, attr_id="attr_3")

    buf.ingest(concept="c1", assertion="verified statement 1", source_attribution=attr1, salience=0.9, step=1)
    buf.ingest(concept="c2", assertion="verified statement 2", source_attribution=attr2, salience=0.4, step=1)

    # Ingest 3rd chunk with high salience -> c2 (salience 0.4, but empirical) or least salient is evicted
    buf.ingest(concept="c3", assertion="verified statement 3", source_attribution=attr3, salience=0.8, step=2)

    assert len(buf.eviction_history) == 1
    evicted = buf.eviction_history[0]
    assert evicted.concept == "c2"
    assert evicted.fate == ChunkState.CONSOLIDATED_TO_LTM

    # Verify LTM contains consolidated node
    node_id = consolidation_engine.resolve_node_id(consolidation_engine.compute_node_id("c2", "verified statement 2", version="v2"))
    assert node_id is not None
    node = consolidation_engine.get_node(node_id)
    assert node is not None
    assert node.concept == "c2"


def test_eviction_adaptive_forgetting_low_salience_hypothesis(consolidation_engine: ConsolidationEngine):
    """Invariant: Transient low-salience unverified hypothesis is adaptively forgotten without LTM pollution."""
    buf = WorkingMemoryBuffer(capacity=2, consolidation_engine=consolidation_engine, consolidation_threshold=0.7)

    attr_hypo = make_attribution("transient guess", veracity=VeracityState.UNVERIFIED_HYPOTHESIS, source_type=SourceType.INTERNAL_HYPOTHESIS, attr_id="hypo_1")
    attr_emp = make_attribution("strong empirical fact", veracity=VeracityState.VERIFIED_EMPIRICAL, attr_id="emp_1")
    attr_new = make_attribution("another strong fact", veracity=VeracityState.VERIFIED_EMPIRICAL, attr_id="emp_2")

    buf.ingest(concept="guess_c", assertion="transient guess", source_attribution=attr_hypo, salience=0.2, step=1)
    buf.ingest(concept="emp_c", assertion="strong empirical fact", source_attribution=attr_emp, salience=0.9, step=1)

    # Overfill capacity
    buf.ingest(concept="new_c", assertion="another strong fact", source_attribution=attr_new, salience=0.85, step=2)

    assert len(buf.eviction_history) == 1
    evicted = buf.eviction_history[0]
    assert evicted.concept == "guess_c"
    assert evicted.fate == ChunkState.DECAYED_FORGOTTEN

    # Verify LTM was NOT polluted with transient guess
    hypo_node_id = consolidation_engine.compute_node_id("guess_c", "transient guess", version="v2")
    assert consolidation_engine.get_node(hypo_node_id) is None


def test_rehearsal_boosts_salience_and_access_count():
    """Invariant: Accessing or re-ingesting a chunk boosts salience and updates recency."""
    buf = WorkingMemoryBuffer(capacity=4)
    attr = make_attribution("statement A", attr_id="attr_a")

    chunk = buf.ingest(concept="cA", assertion="statement A", source_attribution=attr, salience=0.5, step=1)
    initial_salience = chunk.salience
    assert chunk.access_count == 1

    # Re-access chunk at step 3
    updated = buf.access(chunk.chunk_id, step=3)
    assert updated is not None
    assert updated.access_count == 2
    assert updated.last_accessed_step == 3
    assert updated.salience > initial_salience

    # Re-ingest same concept and assertion
    re_ingested = buf.ingest(concept="cA", assertion="statement A", source_attribution=attr, salience=0.5, step=4)
    assert re_ingested.chunk_id == chunk.chunk_id
    assert re_ingested.access_count == 3
    assert re_ingested.last_accessed_step == 4


def test_step_tick_temporal_decay():
    """Invariant: Unrehearsed chunks experience temporal decay and purge when salience reaches zero."""
    buf = WorkingMemoryBuffer(capacity=4, salience_decay_rate=0.2)
    attr = make_attribution("fading statement", attr_id="attr_fade")

    chunk = buf.ingest(concept="fade", assertion="fading statement", source_attribution=attr, salience=0.3, step=1)
    assert buf.active_count == 1

    # Advance 1 step
    buf.step_tick(step=2)
    chunk_ref = buf.active_chunks[0]
    assert round(chunk_ref.salience, 2) == 0.1

    # Advance another step -> salience reaches 0 -> pruned
    evicted = buf.step_tick(step=3)
    assert len(evicted) == 1
    assert evicted[0].chunk_id == chunk.chunk_id
    assert evicted[0].reason == "salience_decay_to_zero"
    assert buf.active_count == 0


def test_metacognitive_assessment_scenarios():
    """Invariant: Metacognitive assessment accurately flags sufficiency, lack of empirical grounding, and contradiction."""
    buf = WorkingMemoryBuffer(capacity=4)

    # 1. Empty buffer
    report1 = buf.metacognitive_assessment()
    assert report1.verdict == MetacognitiveVerdict.PARTIAL_NEEDS_RECALL
    assert report1.active_chunk_count == 0

    # 2. Only ungrounded hypotheses
    hypo_attr = make_attribution("guess 1", veracity=VeracityState.UNVERIFIED_HYPOTHESIS, source_type=SourceType.INTERNAL_HYPOTHESIS, attr_id="h1")
    buf.ingest(concept="h_concept", assertion="guess 1", source_attribution=hypo_attr, salience=0.5)
    report2 = buf.metacognitive_assessment()
    assert report2.verdict == MetacognitiveVerdict.UNGROUNDED_HYPOTHESIS

    # 3. Grounded empirical focus requires guard-admitted execution evidence.
    guard = SourceMonitoringGuard()
    empirical = guard.record_empirical_observation(
        assertion="tool_exit:run_tests:synthetic-memory-test:0",
        tool="run_tests",
        target="synthetic-memory-test",
        exit_code=0,
        stdout="PASS",
        execution_lock="sandbox-execution-lock",
        attribution_id="e1",
    )
    verified_buf = WorkingMemoryBuffer(capacity=4, source_guard=guard)
    verified_buf.ingest(concept="e_concept", assertion=empirical.assertion, source_attribution=empirical, salience=0.8)
    report3 = verified_buf.metacognitive_assessment()
    assert report3.verdict == MetacognitiveVerdict.FOCUSED_SUFFICIENCY
    assert report3.empirical_ratio == 1.0

    # 4. Active contradiction between two chunks on the same concept
    contra_attr1 = make_attribution("target service is active", veracity=VeracityState.VERIFIED_EMPIRICAL, attr_id="c1")
    contra_attr2 = make_attribution("target service is not active", veracity=VeracityState.VERIFIED_EMPIRICAL, attr_id="c2")
    buf.ingest(concept="service_state", assertion="target service is active", source_attribution=contra_attr1, salience=0.9)
    buf.ingest(concept="service_state", assertion="target service is not active", source_attribution=contra_attr2, salience=0.9)

    report4 = buf.metacognitive_assessment()
    assert report4.verdict == MetacognitiveVerdict.CONTRADICTION_DETECTED
    assert report4.contradiction_count >= 1


def test_zero_trust_unattributed_ingest_rejected():
    """Invariant: Ingesting an assertion without valid SourceAttribution is strictly rejected."""
    buf = WorkingMemoryBuffer(capacity=4)
    with pytest.raises(SourceMonitoringError):
        buf.ingest(concept="test", assertion="unattributed rumor", source_attribution="not_an_attribution")  # type: ignore


def test_recall_from_long_term_memory(consolidation_engine: ConsolidationEngine):
    """Invariant: Querying LTM via concept cue imports consolidated nodes into active working memory."""
    # Pre-populate LTM
    consolidation_engine.ingest_event_stream([
        ("1" * 64, {"concept": "network_config", "assertion": "gateway_ip_is_10_0_0_1", "status": "ACCEPTED"})
    ])

    buf = WorkingMemoryBuffer(capacity=4, consolidation_engine=consolidation_engine)
    assert buf.active_count == 0

    recalled = buf.recall_from_long_term("network_config")
    assert len(recalled) == 1
    assert recalled[0].concept == "network_config"
    assert recalled[0].assertion == "gateway_ip_is_10_0_0_1"
    assert recalled[0].metadata.get("recalled_from_ltm") is True
    assert buf.active_count == 1
