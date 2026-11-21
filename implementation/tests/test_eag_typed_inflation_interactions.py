"""M0-EAG F-A regressions for typed references and shared sources.

These tests constrain only current, invocation-local structural behavior:
distinct canonical types may reuse text IDs, repeated *same-typed* roots
still inflate, and protected result IDs remain forbidden even if the
supplied observation reference has a benign canonical type.
Nothing here authenticates external evidence or resolves issue #263 F-B.
"""
from dataclasses import replace

import pytest

from core.audit_engine import AuditEngine, AuditInput
from core.schema import (
    AuditResult, Claim, EpistemicStatus, Evidence, IndependenceStatus,
    ObservationRecord, Reference, SchemaVersion, Timestamp,
)

TS = Timestamp("SYNTHETIC-F-A")
ENGINE = AuditEngine()


def _claim(identifier="X"):
    return Claim(
        claim_id=identifier,
        schema_version=SchemaVersion("M0-1.0"),
        created_at=TS,
        origin_reference=Reference("SYNTHETIC-ORIGIN", "SOURCE"),
        status=EpistemicStatus.UNKNOWN,
    )


def _observation(identifier="X"):
    return ObservationRecord(
        observation_id=identifier,
        record_version="M0-EAG-OBSERVATION-0.1",
    )


def _evidence(identifier, kind, root_id="X"):
    return Evidence(
        evidence_id=identifier,
        observation_refs=(Reference(root_id, kind),),
        evidence_level="OBSERVATION",
        independence_status=IndependenceStatus.INDEPENDENT,
        derivation_reference=Reference("SYNTHETIC-TR-" + identifier, "TRANSFORMATION"),
        scope="F-A canonical-kind regression",
    )


def _audit(audit_id, evidence, prior=()):
    return ENGINE.audit(
        AuditInput(
            claims=(_claim(),),
            observations=(_observation(),),
            evidence=tuple(evidence),
            prior_audit_results=tuple(prior),
        ),
        rule_versions=("M0-1.0",),
        configuration_id="F-A-INTERACTION-LAB",
        execution_timestamp=TS,
        audit_id=audit_id,
    )


def test_distinct_canonical_kinds_same_text_id_full_verdict():
    # Both OBSERVATION and CLAIM have a real supplied canonical definition.
    result = _audit(
        "F-A-TYPED-DISTINCT",
        (_evidence("E-OBS", "OBSERVATION"), _evidence("E-CLAIM", "CLAIM")),
    )
    assert result.verdict == "PASS"
    assert result.violations == ()


@pytest.mark.parametrize("kinds", [("OBSERVATION", "CLAIM"), ("CLAIM", "OBSERVATION")],
                         ids=["observation-first", "claim-first"])
def test_per_item_dedup_keeps_the_shared_claim_in_either_reference_order(kinds):
    refs = tuple(Reference("X", kind) for kind in kinds)
    first = replace(_evidence("E-A", kinds[0]), observation_refs=refs)
    second = _evidence("E-B", "CLAIM")
    assert ENGINE._check_evidence((first, second)) == ["EVIDENCE_INFLATION"]


def _mixed_siblings():
    return (
        _evidence("E-OBS-1", "OBSERVATION"),
        _evidence("E-OBS-2", "OBSERVATION"),
        _evidence("E-CLAIM", "CLAIM"),
    )


def test_mixed_canonical_sibling_does_not_cancel_real_inflation():
    result = _audit("F-A-TYPED-SIBLING", _mixed_siblings())
    assert result.verdict == "FAIL"
    assert result.violations == ("EVIDENCE_INFLATION",)


def test_mixed_sibling_preserves_the_direct_inflation_diagnostic():
    # The ancestry guard can independently produce the same aggregate diagnostic.
    assert ENGINE._check_evidence(_mixed_siblings()) == ["EVIDENCE_INFLATION"]


def _prior_result():
    return AuditResult(
        audit_id="X",
        inspector_id="SYNTHETIC-INSPECTOR",
        inspector_version="1",
        execution_timestamp=TS,
        configuration_id="F-A-FIXTURE",
        rule_versions=("M0-1.0",),
        artifacts_examined=(),
        violations=(),
        verdict="PASS",
        verdict_basis="Synthetic only; no authority",
    )


def test_result_id_firewall_precedes_typed_plurality():
    # An AUDIT_RESULT ID colliding with a CLAIM reference stays forbidden.
    result = _audit(
        "F-A-TYPED-FIREWALL",
        (_evidence("E-CLAIM", "CLAIM"),),
        prior=(_prior_result(),),
    )
    assert result.verdict == "FAIL"
    assert result.violations == ("COMPOSITION_FORBIDDEN",)


def test_two_protected_references_each_report_only_composition_forbidden():
    prior = (_prior_result(),)
    evidence = (_evidence("E-A", "CLAIM"), _evidence("E-B", "CLAIM"))
    expected = ("COMPOSITION_FORBIDDEN", "COMPOSITION_FORBIDDEN")
    assert tuple(ENGINE._check_evidence(evidence, prior_audit_results=prior)) == expected
    result = _audit("F-A-PROTECTED-PAIR", evidence, prior)
    assert result.verdict == "FAIL"
    assert result.violations == expected
