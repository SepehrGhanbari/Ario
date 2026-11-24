"""Tests for Ario Cognitive Memory Consolidation Engine.

Tests the four core invariants from Issue #209:
- T-CONS-01: Lineage Traceability & Dangling Hash Rejection
- T-CONS-02: Non-Erasure Principle (Ledger Size Monotonicity)
- T-CONS-03: Contradiction Preservation (Contested Epistemic Status)
- T-CONS-04: Decay Boundedness & Saliency Threshold Retrieval
"""

import hashlib
import json
import tempfile
from pathlib import Path

import pytest
from core.memory_consolidation import (
    ConsolidationEngine,
    ConsolidationError,
    NodeEpistemicStatus,
    SemanticNode,
)


def _make_dummy_hash(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def test_t_cons_01_lineage_traceability():
    """T-CONS-01: Consolidated nodes must retain immutable hashes to ingested events."""
    engine = ConsolidationEngine()
    h1 = _make_dummy_hash("event-1")
    event1 = {"concept": "network_isolation", "assertion": "Planner loopback strictly bound"}
    engine.ingest_event_stream([(h1, event1)])

    assert len(engine.nodes) == 1
    node = list(engine.nodes.values())[0]
    assert h1 in node.source_event_hashes
    assert engine.validate_lineage_integrity() is True

    # Corrupt a node with a dangling uningested hash
    dangling_hash = _make_dummy_hash("dangling-unseen")
    corrupt_node = SemanticNode(
        node_id="SEM-corrupt",
        concept="bad_lineage",
        assertion="Untracked claim",
        status=NodeEpistemicStatus.ACCEPTED,
        source_event_hashes=(dangling_hash,),
        saliency_score=0.8,
        created_at="2026-11-15T00:00:00Z",
        last_reinforced_at="2026-11-15T00:00:00Z",
        reinforcement_count=1,
    )
    engine._nodes[corrupt_node.node_id] = corrupt_node

    with pytest.raises(ConsolidationError, match="T-CONS-01"):
        engine.validate_lineage_integrity()


def test_t_cons_02_non_erasure_principle(tmp_path: Path):
    """T-CONS-02: Ingestion must not mutate, truncate, or alter the raw ledger file."""
    ledger_file = tmp_path / "test_ledger.jsonl"
    events = [
        {"task_id": "T1", "concept": "crypto_guard", "assertion": "HMAC secret not exported"},
        {"task_id": "T2", "concept": "crypto_guard", "assertion": "Key derivation strictly PBKDF2"},
    ]
    with open(ledger_file, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")

    initial_bytes = ledger_file.stat().st_size
    initial_content = ledger_file.read_bytes()

    engine = ConsolidationEngine()
    count = engine.ingest_ledger_file(ledger_file)
    assert count == 2

    final_bytes = ledger_file.stat().st_size
    final_content = ledger_file.read_bytes()

    assert final_bytes == initial_bytes
    assert final_content == initial_content


def test_t_cons_03_contradiction_preservation():
    """T-CONS-03: Contradictory events must NOT be smoothed into false consensus; must be CONTESTED."""
    engine = ConsolidationEngine()
    h1 = _make_dummy_hash("claim-approved")
    h2 = _make_dummy_hash("claim-rejected")

    ev1 = {
        "concept": "request_204",
        "assertion": "Request 204 was approved at 10:15",
        "value": "APPROVED",
    }
    engine.ingest_event_stream([(h1, ev1)])
    node_id_1 = list(engine.nodes.values())[0].node_id
    assert engine.nodes[node_id_1].status == NodeEpistemicStatus.ACCEPTED

    ev2 = {
        "concept": "request_204",
        "assertion": "Request 204 was rejected at 10:15",
        "value": "REJECTED",
        "negates": node_id_1,
        "relation": "opposite",
    }
    engine.ingest_event_stream([(h2, ev2)])

    # Both nodes must now reflect CONTESTED status, acknowledging discrepancy
    for node in engine.nodes.values():
        assert node.status == NodeEpistemicStatus.CONTESTED


def test_t_cons_04_decay_and_saliency_retrieval():
    """T-CONS-04: Inactive nodes decay below threshold; active nodes are reinforced."""
    engine = ConsolidationEngine(decay_rate=0.1, retrieval_threshold=0.3)
    h1 = _make_dummy_hash("routine_check")
    ev1 = {"concept": "routine", "assertion": "System heart-beat checked"}
    engine.ingest_event_stream([(h1, ev1)])

    # Initially salient
    active = engine.retrieve_active_context(concept_cue="routine")
    assert len(active) == 1
    assert active[0].saliency_score == 0.7

    # After 12 cycles of inactivity (decay)
    engine.apply_saliency_decay(cycles=12)
    decayed = engine.retrieve_active_context(concept_cue="routine")
    assert len(decayed) == 0  # Below 0.3 threshold

    # But still present in memory graph and can be reinforced
    h2 = _make_dummy_hash("routine_check_revisited")
    engine.ingest_event_stream([(h2, ev1)])
    reactivated = engine.retrieve_active_context(concept_cue="routine")
    assert len(reactivated) == 1
    assert reactivated[0].reinforcement_count == 2
    assert reactivated[0].saliency_score >= 0.3


def test_invalid_node_instantiation():
    """Fail-closed on invalid schema attributes."""
    with pytest.raises(ConsolidationError):
        SemanticNode(
            node_id="",
            concept="test",
            assertion="test",
            status=NodeEpistemicStatus.ACCEPTED,
            source_event_hashes=(_make_dummy_hash("x"),),
            saliency_score=0.5,
            created_at="2026-11-15",
            last_reinforced_at="2026-11-15",
            reinforcement_count=1,
        )

    with pytest.raises(ConsolidationError, match="invalid sha256"):
        SemanticNode(
            node_id="SEM-1",
            concept="test",
            assertion="test",
            status=NodeEpistemicStatus.ACCEPTED,
            source_event_hashes=("not-a-valid-sha256",),
            saliency_score=0.5,
            created_at="2026-11-15",
            last_reinforced_at="2026-11-15",
            reinforcement_count=1,
        )
