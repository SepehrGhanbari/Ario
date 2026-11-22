"""End-to-End Integration Tests for Ario Cognitive Memory Architecture.

Integrates all three modules from Issue #209:
1. Module 1: ConsolidationEngine (Systems Consolidation & Saliency Decay)
2. Module 2: SourceMonitoringGuard (Metacognitive Reality Monitoring)
3. Module 3: ProspectiveMemoryRegistry (Delayed Intentions & Condition Gating)

Validates the full epistemic lifecycle:
Hypothesis -> Tool Execution -> Reality Monitoring Gating -> Episodic Logging ->
Semantic Consolidation -> Prospective Trigger -> Audit Lineage Invariance.
"""

import hashlib
import json
from pathlib import Path
import pytest

from core.memory_consolidation import ConsolidationEngine, NodeEpistemicStatus
from core.prospective_memory import IntentionStatus, ProspectiveMemoryRegistry
from core.source_monitoring import (
    SelfCitationError,
    SourceMonitoringGuard,
    SourceType,
    VeracityState,
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_full_cognitive_memory_lifecycle(tmp_path: Path):
    """Verify that unverified claims cannot bypass reality monitoring, and verified claims consolidate cleanly."""
    guard = SourceMonitoringGuard()
    engine = ConsolidationEngine(decay_rate=0.05, retrieval_threshold=0.2)
    prospective = ProspectiveMemoryRegistry()

    # --- Phase 1: Speculative Hypothesis Generation ---
    hyp = guard.create_hypothesis(
        assertion="tool_exit:run_tests:implementation/tests/test_planner_transport.py:0",
        attribution_id="ATTR-HYP-BIND",
    )
    assert hyp.veracity_state == VeracityState.UNVERIFIED_HYPOTHESIS

    # Gating check: Cannot be injected into working memory when verified is required
    verified_candidates = guard.filter_working_memory_candidates(
        [hyp.attribution_id], require_verified=True
    )
    assert len(verified_candidates) == 0

    # Self-citation attempt fails closed
    with pytest.raises(SelfCitationError):
        guard.evaluate_claim_promotion(hyp.attribution_id, [hyp.attribution_id])

    # --- Phase 2: Empirical Observation via Tool Execution ---
    raw_lock = "audit-lock-run-20261116-001"
    lock_hash = _sha256(raw_lock)
    stdout_content = "1141 passed, 0 warnings"
    stdout_hash = _sha256(stdout_content)

    obs = guard.record_empirical_observation(
        assertion="tool_exit:run_tests:implementation/tests/test_planner_transport.py:0",
        tool="run_tests",
        target="implementation/tests/test_planner_transport.py",
        exit_code=0,
        stdout=stdout_content,
        execution_lock=raw_lock,
        expected_execution_lock_sha256=lock_hash,
        expected_stdout_sha256=stdout_hash,
        attribution_id="ATTR-EMP-001",
    )
    assert obs.veracity_state == VeracityState.VERIFIED_EMPIRICAL

    # Now promote hypothesis citing the verified empirical observation
    promoted_claim = guard.evaluate_claim_promotion(
        claim_id=hyp.attribution_id,
        supporting_ids=[obs.attribution_id],
    )
    assert promoted_claim.veracity_state == VeracityState.VERIFIED_EMPIRICAL

    # Now working memory gating permits injection
    verified_candidates = guard.filter_working_memory_candidates(
        [promoted_claim.attribution_id], require_verified=True
    )
    assert len(verified_candidates) == 1

    # --- Phase 3: Episodic Ledger Logging & Consolidation ---
    ledger_path = tmp_path / "agent-events.jsonl"
    event_payload = {
        "event_id": "EVT-202611-01",
        "concept": "planner_loopback",
        "assertion": promoted_claim.assertion,
        "attribution_id": promoted_claim.attribution_id,
        "source_type": promoted_claim.source_type.value,
        "veracity": promoted_claim.veracity_state.value,
    }
    with open(ledger_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(event_payload) + "\n")

    initial_size = ledger_path.stat().st_size
    ingested_count = engine.ingest_ledger_file(ledger_path)
    assert ingested_count == 1

    # Non-erasure check (Revision != Erasure)
    assert ledger_path.stat().st_size == initial_size

    # Semantic knowledge node extracted with lineage
    active_nodes = engine.retrieve_active_context("planner_loopback")
    assert len(active_nodes) == 1
    node = active_nodes[0]
    assert node.status == NodeEpistemicStatus.RECORDED
    assert engine.validate_lineage_integrity() is True

    # --- Phase 4: Prospective Intention Triggering ---
    prospective.register_intention(
        description="Trigger architectural review when loopback is accepted",
        predicate_expr="concept == 'planner_loopback' and status == 'ACCEPTED'",
        action_payload={"task": "schedule_regression_benchmark"},
        created_at_epoch=1000.0,
        ttl_epoch=2000.0,
        intention_id="INT-PROSPECTIVE-01",
        source_attribution_id=promoted_claim.attribution_id,
    )

    # Evaluate with matching cue from consolidated memory
    cue_context = {
        "concept": node.concept,
        "status": node.status.value,
        "saliency": node.saliency_score,
    }
    triggered = prospective.evaluate_cues(cue_context, current_epoch=1500.0)
    assert triggered == []  # RECORDED cannot satisfy the ACCEPTED action cue
