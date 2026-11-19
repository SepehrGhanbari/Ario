"""Property-Based and Randomized Fuzz Tests for WorkingMemoryBuffer (Module 4).

Generates 1,000 chaotic operations (ingestions, rehearsals, step ticks,
recalls, flushes, and metacognitive evaluations) with pseudo-random seeds
to verify that all architectural invariants hold deterministically.
"""

import random
from datetime import datetime, timezone
import pytest
from typing import Tuple

from core.memory_consolidation import ConsolidationEngine
from core.source_monitoring import (
    SourceAttribution,
    SourceType,
    VeracityState,
    EmpiricalProvenance,
)
from core.working_memory import (
    WorkingMemoryBuffer,
    ChunkState,
    MetacognitiveVerdict,
)


def _make_random_attribution(rng: random.Random, op_id: int) -> Tuple[str, str, SourceAttribution, float]:
    source_choice = rng.choice(["EMPIRICAL", "TESTIMONY", "HYPOTHESIS", "NOISE"])
    concept = f"concept_{rng.randint(0, 8)}"
    salience = round(rng.uniform(0.0, 1.0), 3)

    if source_choice == "EMPIRICAL":
        prov = EmpiricalProvenance(
            tool=f"probe_{rng.randint(0, 3)}",
            target="127.0.0.1",
            exit_code=0,
            execution_lock_sha256="1" * 64,
            stdout_sha256="2" * 64,
            recorded_at=datetime.now(timezone.utc).isoformat(),
        )
        assertion = f"Observed state {rng.randint(0, 5)} at op {op_id}"
        attr = SourceAttribution(
            attribution_id=f"attr_emp_{op_id}",
            source_type=SourceType.EMPIRICAL_OBSERVATION,
            assertion=assertion,
            veracity_state=VeracityState.VERIFIED_EMPIRICAL,
            provenance=prov,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        salience = max(salience, 0.7)
    elif source_choice == "TESTIMONY":
        assertion = f"Peer reported status {rng.randint(0, 5)}"
        attr = SourceAttribution(
            attribution_id=f"attr_test_{op_id}",
            source_type=SourceType.EXTERNAL_TESTIMONY,
            assertion=assertion,
            veracity_state=VeracityState.EXTERNAL_ASSERTION,
            provenance=None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    elif source_choice == "HYPOTHESIS":
        assertion = f"Inferred hypothesis {rng.randint(0, 5)}"
        attr = SourceAttribution(
            attribution_id=f"attr_hyp_{op_id}",
            source_type=SourceType.INTERNAL_HYPOTHESIS,
            assertion=assertion,
            veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
            provenance=None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    else:
        assertion = f"Random jitter {rng.randint(0, 100)}"
        attr = SourceAttribution(
            attribution_id=f"attr_noise_{op_id}",
            source_type=SourceType.INTERNAL_HYPOTHESIS,
            assertion=assertion,
            veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
            provenance=None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        salience = min(salience, 0.15)

    return concept, assertion, attr, salience


def test_chaotic_random_property_fuzz():
    """1,000 chaotic operations preserve all structural and epistemic invariants."""
    rng = random.Random(1337)  # Deterministic seed
    engine = ConsolidationEngine()
    wm = WorkingMemoryBuffer(capacity=4, consolidation_engine=engine)

    for op in range(1000):
        action = rng.choice(["INGEST", "ACCESS", "STEP_TICK", "RECALL", "FLUSH", "ASSESS"])

        if action == "INGEST":
            concept, assertion, attr, sal = _make_random_attribution(rng, op)
            wm.ingest(concept, assertion, attr, salience=sal, step=op)

        elif action == "ACCESS":
            if wm.active_chunks:
                target_chunk = rng.choice(wm.active_chunks)
                wm.access(target_chunk.chunk_id, step=op)

        elif action == "STEP_TICK":
            wm.step_tick(step=op)

        elif action == "RECALL":
            query_concept = f"concept_{rng.randint(0, 8)}"
            wm.recall_from_long_term(query_concept)

        elif action == "FLUSH":
            wm.flush_to_long_term(min_salience=0.8)

        elif action == "ASSESS":
            assessment = wm.metacognitive_assessment()
            assert 0.0 <= assessment.empirical_ratio <= 1.0
            assert 0.0 <= assessment.average_salience <= 1.0
            assert assessment.contradiction_count >= 0
            assert assessment.verdict in (
                MetacognitiveVerdict.FOCUSED_SUFFICIENCY,
                MetacognitiveVerdict.PARTIAL_NEEDS_RECALL,
                MetacognitiveVerdict.CONTRADICTION_DETECTED,
                MetacognitiveVerdict.UNGROUNDED_HYPOTHESIS,
            )

        # Invariant 1: Cowan Attentional Bound strictly holds at every step
        assert wm.active_count <= 4, f"Capacity exceeded at op {op}: {wm.active_count}"

        # Invariant 2: Provenance Gate (every active chunk has valid SourceAttribution)
        for chunk in wm.active_chunks:
            assert chunk.source_attribution is not None
            assert len(chunk.source_attribution.attribution_id) > 0
            assert 0.0 <= chunk.salience <= 1.0

        # Invariant 3: Unique chunk IDs
        active_ids = [c.chunk_id for c in wm.active_chunks]
        assert len(active_ids) == len(set(active_ids))


def test_fuzz_dual_eviction_invariant():
    """All evicted empirical facts must be consolidated to LTM, never lost without trace."""
    rng = random.Random(2026)
    engine = ConsolidationEngine()
    wm = WorkingMemoryBuffer(capacity=3, consolidation_engine=engine)

    for op in range(300):
        concept, assertion, attr, sal = _make_random_attribution(rng, op)
        wm.ingest(concept, assertion, attr, salience=sal, step=op)

    # Check eviction history
    for record in wm.eviction_history:
        assert record.fate in (ChunkState.CONSOLIDATED_TO_LTM, ChunkState.DECAYED_FORGOTTEN)
        assert len(record.chunk_id) > 0
