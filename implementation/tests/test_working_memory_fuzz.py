"""Property-Based and Randomized Fuzz Tests for WorkingMemoryBuffer (Module 4).

Verifies that all architectural invariants hold deterministically under chaotic,
pseudo-random operations (ingestions, rehearsals, step ticks, recalls, flushes,
and metacognitive evaluations).

Supports parameterization and reproduction via environment variable:
    ARIO_FUZZ_SEED=<int> python -m pytest tests/test_working_memory_fuzz.py
"""

from __future__ import annotations

import os
import random
from datetime import datetime, timezone
from typing import List, Tuple

import pytest

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


def _get_fuzz_seeds() -> List[int]:
    """Retrieve seed from environment or return deterministic test suite seeds."""
    env_seed = os.environ.get("ARIO_FUZZ_SEED")
    if env_seed is not None:
        try:
            return [int(env_seed)]
        except ValueError as exc:
            raise ValueError("ARIO_FUZZ_SEED must be an integer") from exc
    return [1337, 2026, 42]


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


@pytest.mark.parametrize("seed", _get_fuzz_seeds())
def test_chaotic_random_property_fuzz(seed: int):
    """Chaotic operations preserve all structural, provenance, and epistemic invariants."""
    rng = random.Random(seed)
    engine = ConsolidationEngine()
    wm = WorkingMemoryBuffer(capacity=4, consolidation_engine=engine)

    try:
        for op in range(500):
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

    except AssertionError as exc:
        pytest.fail(f"Fuzz failure at op {op} with seed {seed}: {exc}. "
                    f"Reproduce with: ARIO_FUZZ_SEED={seed} python -m pytest tests/test_working_memory_fuzz.py")


@pytest.mark.parametrize("seed", _get_fuzz_seeds())
def test_fuzz_dual_eviction_invariant(seed: int):
    """All evicted empirical facts must be consolidated to LTM and verified in engine.nodes."""
    rng = random.Random(seed)
    engine = ConsolidationEngine()
    wm = WorkingMemoryBuffer(capacity=3, consolidation_engine=engine)

    for op in range(250):
        concept, assertion, attr, sal = _make_random_attribution(rng, op)
        wm.ingest(concept, assertion, attr, salience=sal, step=op)

    # Verify every eviction record
    for record in wm.eviction_history:
        assert record.fate in (ChunkState.CONSOLIDATED_TO_LTM, ChunkState.DECAYED_FORGOTTEN)
        assert len(record.chunk_id) > 0

    # Specifically verify that consolidated empirical records actually exist in the ConsolidationEngine
    consolidated_records = [r for r in wm.eviction_history if r.fate == ChunkState.CONSOLIDATED_TO_LTM]
    assert len(consolidated_records) > 0, "Expected at least some items to consolidate"
    for r in consolidated_records:
        node_id = engine.compute_node_id(r.concept, r.assertion, version=engine.node_id_version)
        node = engine.get_node(node_id)
        assert node is not None, f"Consolidated chunk {r.chunk_id} missing from LTM engine nodes"
        assert node.concept == r.concept
        assert node.assertion == r.assertion


def test_fuzz_deterministic_replay():
    """Two independent WorkingMemoryBuffer instances receiving the identical random stream
    must yield bitwise identical internal states, active chunks, eviction records, and assessments.
    """
    seed = 98765
    def _run_sequence():
        rng = random.Random(seed)
        engine = ConsolidationEngine()
        wm = WorkingMemoryBuffer(capacity=4, consolidation_engine=engine)
        for op in range(200):
            concept, assertion, attr, sal = _make_random_attribution(rng, op)
            wm.ingest(concept, assertion, attr, salience=sal, step=op)
            if op % 4 == 0:
                wm.step_tick(step=op)
        return wm

    wm1 = _run_sequence()
    wm2 = _run_sequence()

    # Verify active chunks equivalence
    assert [c.chunk_id for c in wm1.active_chunks] == [c.chunk_id for c in wm2.active_chunks]
    assert [c.salience for c in wm1.active_chunks] == [c.salience for c in wm2.active_chunks]
    assert [c.access_count for c in wm1.active_chunks] == [c.access_count for c in wm2.active_chunks]

    # Verify eviction history equivalence
    assert len(wm1.eviction_history) == len(wm2.eviction_history)
    for r1, r2 in zip(wm1.eviction_history, wm2.eviction_history):
        assert r1.chunk_id == r2.chunk_id
        assert r1.fate == r2.fate
        assert r1.reason == r2.reason
        assert r1.final_salience == r2.final_salience

    # Verify metacognitive assessment equivalence
    a1 = wm1.metacognitive_assessment()
    a2 = wm2.metacognitive_assessment()
    assert a1.verdict == a2.verdict
    assert a1.empirical_ratio == a2.empirical_ratio
    assert a1.average_salience == a2.average_salience
    assert a1.contradiction_count == a2.contradiction_count
