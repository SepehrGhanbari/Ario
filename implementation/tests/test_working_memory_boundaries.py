"""Boundary and Stress Tests for WorkingMemoryBuffer (Module 4).

Validates extreme parameters, concurrency bursts, zero/negative salience,
rehearsal saturation, multi-contradiction detection, and fail-closed security.
"""

import pytest
from datetime import datetime, timezone

from core.memory_consolidation import ConsolidationEngine
from core.source_monitoring import (
    SourceAttribution,
    SourceMonitoringGuard,
    SourceType,
    VeracityState,
    EmpiricalProvenance,
    SourceMonitoringError,
)
from core.working_memory import (
    WorkingMemoryBuffer,
    WorkingMemoryChunk,
    ChunkState,
    MetacognitiveVerdict,
)


def _make_dummy_provenance(tool: str = "test_probe") -> EmpiricalProvenance:
    return EmpiricalProvenance(
        tool=tool,
        target="127.0.0.1",
        exit_code=0,
        execution_lock_sha256="a" * 64,
        stdout_sha256="b" * 64,
        recorded_at=datetime.now(timezone.utc).isoformat(),
    )


def _make_empirical_attribution(aid: str, assertion: str) -> SourceAttribution:
    return SourceAttribution(
        attribution_id=aid,
        source_type=SourceType.EMPIRICAL_OBSERVATION,
        assertion=assertion,
        veracity_state=VeracityState.VERIFIED_EMPIRICAL,
        provenance=_make_dummy_provenance(),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def _make_hypothesis_attribution(aid: str, assertion: str) -> SourceAttribution:
    return SourceAttribution(
        attribution_id=aid,
        source_type=SourceType.INTERNAL_HYPOTHESIS,
        assertion=assertion,
        veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
        provenance=None,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


class TestWorkingMemoryBoundaries:
    def test_capacity_boundary_minimum_one(self, tmp_path):
        """Buffer with capacity=1 strictly retains only 1 active item, evicting previous."""
        engine = ConsolidationEngine()
        wm = WorkingMemoryBuffer(capacity=1, consolidation_engine=engine)

        attr1 = _make_empirical_attribution("attr_1", "Initial statement")
        attr2 = _make_empirical_attribution("attr_2", "Subsequent statement")

        wm.ingest("concept_a", "Initial statement", attr1, salience=0.5)
        assert wm.active_count == 1
        assert wm.active_chunks[0].concept == "concept_a"

        # Ingesting second item forces eviction of the first
        wm.ingest("concept_b", "Subsequent statement", attr2, salience=0.8)
        assert wm.active_count == 1
        assert wm.active_chunks[0].concept == "concept_b"
        assert len(wm.eviction_history) == 1
        assert wm.eviction_history[0].concept == "concept_a"
        # Empirical fact is consolidated to LTM on eviction
        assert wm.eviction_history[0].fate == ChunkState.CONSOLIDATED_TO_LTM

    def test_capacity_invalid_zero_or_negative(self):
        """Capacity less than 1 raises ValueError fail-closed."""
        with pytest.raises(ValueError, match="at least 1"):
            WorkingMemoryBuffer(capacity=0)
        with pytest.raises(ValueError, match="at least 1"):
            WorkingMemoryBuffer(capacity=-5)

    def test_burst_ingestion_stress(self, tmp_path):
        """Ingesting 200 items in rapid burst maintains strict capacity and tracks history without leak."""
        engine = ConsolidationEngine()
        wm = WorkingMemoryBuffer(capacity=4, consolidation_engine=engine)

        for i in range(200):
            attr = _make_hypothesis_attribution(f"hyp_{i}", f"Statement variant {i}")
            wm.ingest(f"topic_{i % 10}", f"Statement variant {i}", attr, salience=(i % 10) / 10.0)
            assert wm.active_count <= 4

        assert wm.active_count == 4
        assert len(wm.eviction_history) == 196

    def test_extreme_salience_clamping(self):
        """Salience values exceeding [0.0, 1.0] are strictly clamped without error."""
        wm = WorkingMemoryBuffer(capacity=4)

        attr_high = _make_hypothesis_attribution("high_sal", "Hyper salient")
        attr_low = _make_hypothesis_attribution("low_sal", "Sub zero salient")

        chunk_high = wm.ingest("focus", "Hyper salient", attr_high, salience=999.0)
        assert chunk_high.salience == 1.0

        chunk_low = wm.ingest("noise", "Sub zero salient", attr_low, salience=-50.0)
        assert chunk_low.salience == 0.0

    def test_long_temporal_decay_purging(self):
        """Unaccessed chunks steadily decay to 0 and get purged on step ticks."""
        wm = WorkingMemoryBuffer(capacity=4, salience_decay_rate=0.1)

        attr = _make_hypothesis_attribution("decay_attr", "Transient observation")
        wm.ingest("ephemeral", "Transient observation", attr, salience=0.25, step=0)

        assert wm.active_count == 1
        # Step 1: salience decays to 0.15
        wm.step_tick(step=1)
        assert wm.active_count == 1
        assert round(wm.active_chunks[0].salience, 2) == 0.15

        # Step 2: salience decays to 0.05
        wm.step_tick(step=2)
        assert wm.active_count == 1
        assert round(wm.active_chunks[0].salience, 2) == 0.05

        # Step 3: salience reaches <= 0.0 and chunk is purged
        evicted = wm.step_tick(step=3)
        assert wm.active_count == 0
        assert len(evicted) == 1
        assert evicted[0].fate == ChunkState.DECAYED_FORGOTTEN

    def test_rehearsal_saturation(self):
        """Continuous access / rehearsal saturates salience at 1.0 without numeric drift."""
        wm = WorkingMemoryBuffer(capacity=4)
        attr = _make_hypothesis_attribution("rehearsal_attr", "Crucial fact")
        chunk = wm.ingest("critical", "Crucial fact", attr, salience=0.5)

        for _ in range(50):
            wm.access(chunk.chunk_id)

        # Returned chunks are snapshots; only canonical internal state rehearses.
        current = wm.active_chunks[0]
        assert chunk.salience == 0.5
        assert chunk.access_count == 1
        assert current.salience == 1.0
        assert current.access_count == 51

    def test_metacognitive_empty_buffer(self):
        """Empty buffer returns diagnostic assessment without division by zero."""
        wm = WorkingMemoryBuffer(capacity=4)
        assessment = wm.metacognitive_assessment()

        assert assessment.verdict == MetacognitiveVerdict.PARTIAL_NEEDS_RECALL
        assert assessment.active_chunk_count == 0
        assert assessment.empirical_ratio == 0.0
        assert "EMPTY_WORKING_MEMORY" in assessment.diagnostics

    def test_multiple_active_contradictions(self):
        """Simultaneous contradictory assertions across concepts are accurately flagged."""
        wm = WorkingMemoryBuffer(capacity=4)

        # Concept 1 contradiction
        attr1 = _make_hypothesis_attribution("a1", "auth_proxy is true")
        attr2 = _make_hypothesis_attribution("a2", "auth_proxy is false")
        wm.ingest("auth_proxy", "auth_proxy is true", attr1)
        wm.ingest("auth_proxy", "auth_proxy is false", attr2)

        assessment = wm.metacognitive_assessment()
        assert assessment.verdict == MetacognitiveVerdict.CONTRADICTION_DETECTED
        assert assessment.contradiction_count >= 1

    def test_fail_closed_on_invalid_inputs(self):
        """Empty concept, empty assertion, or missing SourceAttribution fail closed."""
        wm = WorkingMemoryBuffer(capacity=4)
        valid_attr = _make_hypothesis_attribution("valid_id", "Test")

        with pytest.raises(ValueError, match="Concept cannot be empty"):
            wm.ingest("   ", "Test assertion", valid_attr)

        with pytest.raises(ValueError, match="Assertion cannot be empty"):
            wm.ingest("concept", "   ", valid_attr)

        with pytest.raises(SourceMonitoringError, match="verified SourceAttribution"):
            wm.ingest("concept", "Test assertion", source_attribution=None)  # type: ignore

        with pytest.raises(SourceMonitoringError, match="verified SourceAttribution"):
            wm.ingest("concept", "Test assertion", source_attribution={"bogus": "dict"})  # type: ignore
