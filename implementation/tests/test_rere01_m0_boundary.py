"""RERE-01: exact-source, research-only probes of Ario's unmerged memory candidate.

PRE-REGISTRATION: implementation/research/rere01/RERE_01_PREREGISTRATION_V0_1.json
Target: PR #210 HEAD 6235df45444f112c3a7a699d5c96cac85a4e5b66
No real source, key, signer, journal, memory or trust state is used.

Expected XFAILs are *failures of desired safety contracts*, not successful
epistemic validations. strict=True turns a repaired/unexpected XPASS red.
"""
from __future__ import annotations

import hashlib
from dataclasses import fields

import pytest

from core.audit_engine import AuditEngine, AuditInput
from core.memory_consolidation import (
    ConsolidationEngine,
    ConsolidationError,
    NodeEpistemicStatus,
    SemanticNode,
)
from core.schema import (
    Assessment,
    AuditResult,
    HistoricalMutationCandidate,
    IntegrityRepresentation,
    Reference,
    Timestamp,
)


EVENT_ID = "LAB-E101"
EVENT_TIME = "2026-11-18T00:00:00Z"
SEED = 510101


def _hash(label: str) -> str:
    return hashlib.sha256(f"{SEED}:{EVENT_ID}:{label}".encode("utf-8")).hexdigest()


def _event(assertion: str, **extra: object) -> dict:
    return {
        "event_id": EVENT_ID,
        "event_time": EVENT_TIME,
        "concept": EVENT_ID,
        "assertion": assertion,
        **extra,
    }


def _feed(engine: ConsolidationEngine, label: str, event: dict) -> None:
    assert engine.ingest_event_stream([(_hash(label), event)]) == 1


def _run_m0(name: str, artifacts: AuditInput, rules=("M0-1.0",)):
    return AuditEngine().audit(
        artifacts, rule_versions=tuple(rules),
        configuration_id="RERE01-SYNTHETIC-ONLY",
        execution_timestamp=Timestamp(EVENT_TIME),
        audit_id=f"RERE01-{name}",
    )


# Positive controls: guard must not simply reject all records.
def test_rere01_p01_explicit_recorded_mode():
    engine = ConsolidationEngine(default_status=NodeEpistemicStatus.RECORDED)
    _feed(engine, "A", _event("Door was OPEN", source="A"))
    assert len(engine.nodes) == 1
    assert next(iter(engine.nodes.values())).status == NodeEpistemicStatus.RECORDED


@pytest.mark.xfail(strict=True, reason="N01: raw testimony defaults to legacy ACCEPTED; #216 HOLD")
def test_rere01_n01_raw_ingestion_does_not_accept_truth():
    engine = ConsolidationEngine()
    _feed(engine, "A", _event("Door was OPEN", source="A"))
    assert next(iter(engine.nodes.values())).status == NodeEpistemicStatus.RECORDED


@pytest.mark.xfail(strict=True, reason="N02: ordinary conflicting text without caller negates is not detected")
def test_rere01_n02_plain_open_closed_conflict_is_unknown_or_contested():
    engine = ConsolidationEngine(default_status=NodeEpistemicStatus.RECORDED)
    _feed(engine, "A", _event("Door was OPEN", source="A", value="OPEN"))
    _feed(engine, "B", _event("Door was CLOSED", source="B", value="CLOSED"))
    assert len(engine.nodes) == 2
    assert any(n.status == NodeEpistemicStatus.CONTESTED for n in engine.nodes.values())


def test_rere01_p02_explicit_negates_is_detected():
    engine = ConsolidationEngine(default_status=NodeEpistemicStatus.RECORDED)
    _feed(engine, "A", _event("Door was OPEN", source="A", value="OPEN"))
    first_id = next(iter(engine.nodes))
    _feed(engine, "B", _event("Door was CLOSED", source="B", negates=first_id))
    assert len(engine.nodes) == 2
    assert all(n.status == NodeEpistemicStatus.CONTESTED for n in engine.nodes.values())
    assert engine.validate_lineage_integrity() is True


@pytest.mark.xfail(strict=True, reason="N03: caller-chosen SUPPORTED status is accepted without evidence authority")
def test_rere01_n03_untrusted_supported_cannot_promote():
    engine = ConsolidationEngine(default_status=NodeEpistemicStatus.RECORDED)
    _feed(engine, "C", _event("Door was CLOSED", source="C", status="SUPPORTED"))
    assert next(iter(engine.nodes.values())).status != NodeEpistemicStatus.SUPPORTED


@pytest.mark.xfail(strict=True, reason="N04: no typed, versioned prior-assessment history interface")
def test_rere01_n04_previous_assessment_is_retrievable_after_contestation():
    engine = ConsolidationEngine(default_status=NodeEpistemicStatus.RECORDED)
    _feed(engine, "A", _event("Door was OPEN", source="A"))
    first_id = next(iter(engine.nodes))
    _feed(engine, "B", _event("Door was CLOSED", source="B", negates=first_id))
    assert hasattr(engine, "get_assessment_history")
    history = engine.get_assessment_history(first_id)
    assert any(item.status == NodeEpistemicStatus.RECORDED for item in history)
    assert any(item.status == NodeEpistemicStatus.CONTESTED for item in history)


@pytest.mark.xfail(strict=True, reason="N05: replay of identical event reinforces saliency/count")
def test_rere01_n05_exact_replay_is_idempotent():
    engine = ConsolidationEngine(default_status=NodeEpistemicStatus.RECORDED)
    event = _event("Door was OPEN", source="A")
    _feed(engine, "A", event)
    before = next(iter(engine.nodes.values()))
    _feed(engine, "A", event)
    after = next(iter(engine.nodes.values()))
    assert len(engine.nodes) == 1
    assert after.reinforcement_count == before.reinforcement_count
    assert after.saliency_score == before.saliency_score
    assert after.source_event_hashes == before.source_event_hashes


@pytest.mark.xfail(strict=True, reason="N06: caller-supplied hex hash is registered without source-byte authentication")
def test_rere01_n06_fabricated_digest_is_not_complete_receipt():
    engine = ConsolidationEngine(default_status=NodeEpistemicStatus.RECORDED)
    # A synthetic 64-character string, NOT a hash of authenticated source bytes.
    engine.ingest_event_stream([("f" * 64, _event("Door was OPEN", source="A"))])
    assert engine.validate_lineage_integrity() is False


def test_rere01_p03_invalid_digest_shape_rejected():
    engine = ConsolidationEngine(default_status=NodeEpistemicStatus.RECORDED)
    with pytest.raises(ConsolidationError):
        engine.ingest_event_stream([("short", _event("Door was OPEN"))])


def _order_outcome(order):
    engine = ConsolidationEngine(default_status=NodeEpistemicStatus.RECORDED)
    first_id = ConsolidationEngine.compute_node_id(EVENT_ID, "Door was OPEN")
    cases = {
        "A": _event("Door was OPEN", source="A", value="OPEN"),
        "B": _event("Door was CLOSED", source="B", value="CLOSED", negates=first_id),
    }
    for key in order:
        _feed(engine, key, cases[key])
    return tuple(sorted((node.assertion, node.status.value) for node in engine.nodes.values()))


@pytest.mark.xfail(strict=True, reason="N07: a forward negates reference is not resolved retroactively")
def test_rere01_n07_order_swap_does_not_change_conflict():
    assert _order_outcome(("A", "B")) == _order_outcome(("B", "A"))


@pytest.mark.xfail(strict=True, reason="N08: caller REVISED value needs no reason or predecessor")
def test_rere01_n08_revision_requires_reason_and_prior_assessment():
    engine = ConsolidationEngine(default_status=NodeEpistemicStatus.RECORDED)
    _feed(engine, "T4", _event("Door was CLOSED", source="unauthenticated", status="REVISED"))
    assert next(iter(engine.nodes.values())).status != NodeEpistemicStatus.REVISED


def test_rere01_p04_m0_does_not_launder_prior_audit_into_evidence():
    previous = AuditResult(
        audit_id="RERE01-OLD-AUDIT",
        inspector_id="SYNTHETIC",
        inspector_version="0.1",
        execution_timestamp=Timestamp(EVENT_TIME),
        configuration_id="RERE01",
        rule_versions=("M0-1.0",),
        artifacts_examined=(),
        violations=(),
        verdict="PASS",
        verdict_basis="Synthetic prior structural result, not evidence",
    )
    review = Assessment(
        assessment_id="RERE01-CLAIM-ABOUT-OLD",
        assessment_version="1",
        rule_version="M0-F11-1.0",
        admissible_evidence_refs=(Reference("RERE01-OLD-AUDIT", "AUDIT_RESULT"),),
        condition_evaluation="SUPPORTED",
        assessment_basis="Unsupported attempt to promote a prior PASS",
        scope=EVENT_ID,
    )
    result = _run_m0("P04", AuditInput(assessments=(review,), prior_audit_results=(previous,)),
                     ("M0-1.0", "M0-F11-1.0"))
    assert result.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in result.violations


def test_rere01_p05_m0_flags_declared_history_overwrite():
    candidate = HistoricalMutationCandidate(
        canonical_artifact=Reference("RERE01-T1", "TEST"),
        canonical_integrity=IntegrityRepresentation("SHA256", "a" * 64),
        attempted_replacement=Reference("RERE01-T1-REPLACED", "TEST"),
        attempted_replacement_integrity=IntegrityRepresentation("SHA256", "b" * 64),
        historical_scope=Reference(EVENT_ID, "TEST"),
        mutation_rule_version="M0-F05-1.0",
    )
    result = _run_m0("P05", AuditInput(historical_mutation_candidates=(candidate,)),
                     ("M0-1.0", "M0-F05-1.0"))
    assert result.verdict == "FAIL"
    assert "HISTORY_MUTATION" in result.violations


@pytest.mark.xfail(strict=True, reason="N09: source-root independence authentication not implemented in consolidation")
def test_rere01_n09_shared_origin_requires_independence_review():
    assert any(field.name == "independently_authenticated_root" for field in fields(SemanticNode))


@pytest.mark.xfail(strict=True, reason="N10: recursive assessment target/adjudication API not implemented")
def test_rere01_n10_revise_the_previous_assessment():
    engine = ConsolidationEngine(default_status=NodeEpistemicStatus.RECORDED)
    assert callable(getattr(engine, "reassess_prior_assessment", None))
