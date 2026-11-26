"""F-B protected-root ambiguity regressions; synthetic supplied records only.

Policy: a known protected-ID collision is an aggregate UNKNOWN violation,
not proof of a forbidden information-parent edge or a false claim.
"""
from dataclasses import replace

import pytest

from core.audit_engine import AuditEngine, AuditInput, _EvidenceAncestryGuard, parse_evidence_ancestry_findings
from core.schema import (
    Assessment, AuditResult, Claim, CompositionConclusion, CompositionInputScope,
    CompositionParticipantResult, CompositionRequest, CompositionSummary,
    CompositionSummaryRecord, EpistemicStatus, Evidence, EvidenceUse,
    IndependenceStatus, ObservationRecord, Reference, SchemaVersion,
    SupportTarget, Timestamp,
)

TS = Timestamp("SYNTHETIC-F263")
ENGINE = AuditEngine()
ID = "F263-X"
TARGET = SupportTarget(Reference("F263-C", "CLAIM"), "SUPPLIED_RECORD_PRESENT")
USE = EvidenceUse.RECORD_DESCRIPTION
VERSIONS = [
    ("M0-1.0",),
    ("M0-1.0", "M0-F11-1.0"),
    ("M0-1.0", "M0-F15-1.0"),
    ("M0-1.0", "M0-F11-1.0", "M0-F15-1.0"),
]
KINDS = ["AUDIT_RESULT", "COMPOSITION_REQUEST", "COMPOSITION_SUMMARY"]


def prior(audit_id, **kw):
    return AuditResult(
        audit_id=audit_id, inspector_id="F263", inspector_version="1",
        execution_timestamp=TS, configuration_id="F263-LAB",
        rule_versions=("M0-1.0",), artifacts_examined=(), violations=(),
        verdict="PASS", verdict_basis="Synthetic only", **kw,
    )


def fixture(kind=None, bound=False, protected_id=ID):
    obs = ObservationRecord("F263-O", "M0-EAG-OBSERVATION-0.1", TARGET, USE, ())
    ev = Evidence(
        ID, (Reference("F263-O", "OBSERVATION"),), "OBSERVATION",
        IndependenceStatus.INDEPENDENT, Reference("F263-P", "TRANSFORMATION"), "F263",
    )
    claim = Claim("F263-C", SchemaVersion("M0-1.0"), TS,
                  Reference("F263-Origin", "SOURCE"), EpistemicStatus.UNKNOWN)
    assessment = Assessment(
        "F263-A", "1", "M0-EAG-RECORD-PRESENCE-0.1",
        (Reference(ID, "EVIDENCE"),), "SYNTHETIC", "SYNTHETIC",
        "SUPPLIED_INPUT_RECORDS_ONLY", TARGET, USE,
    )
    p, requests = (), ()
    if kind == "AUDIT_RESULT":
        p = (prior(protected_id),)
    elif kind == "COMPOSITION_REQUEST":
        requests = (CompositionRequest(
            protected_id, (CompositionParticipantResult("IRG-01", "F263-R"),),
            "M0-F15-LOCAL-SUMMARY", "1.0", "SYNTHETIC",
            CompositionConclusion.LOCAL_RESULT_SUMMARY, "SYNTHETIC", "SYNTHETIC",
            CompositionInputScope.SUPPLIED_RESULTS_ONLY,
        ),)
        p = (prior("F263-R"),)
    elif kind == "COMPOSITION_SUMMARY":
        record = CompositionSummaryRecord(
            "F263-R", "IRG-01", "SYNTHETIC", "PASS", ("M0-1.0",), "F263-LAB",
        )
        summary = CompositionSummary(
            protected_id, "M0-F15-LOCAL-SUMMARY", "1.0",
            CompositionInputScope.SUPPLIED_RESULTS_ONLY, (record,), (("PASS", 1),),
            "SYNTHETIC", "SYNTHETIC",
        )
        p = (prior("F263-R", composition_summaries=(summary,)),)
    return AuditInput(
        claims=(claim,), observations=(obs,), evidence=(ev,),
        assessments=(assessment,) if bound else (), prior_audit_results=p,
        composition_requests=requests,
    )


def audit(a, versions):
    return ENGINE.audit(
        a, rule_versions=versions, configuration_id="F263-LAB",
        execution_timestamp=TS, audit_id="F263-NEW",
    )


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("bound", [False, True])
def test_protected_id_ambiguity_at_guard(kind, bound):
    guard = _EvidenceAncestryGuard(fixture(kind, bound), ENGINE)
    fact = guard.facts(("EVIDENCE", ID))
    assert fact["unknown"] and "UNKNOWN" in fact["codes"]
    assert "COMPOSITION_FORBIDDEN" not in fact["codes"]
    assert ("OBSERVATION", "F263-O") in fact["reached"]
    violations, report = guard.evaluate()
    assert "UNKNOWN" in violations and report["candidate_ancestry"] == "UNKNOWN"
    assert report["candidate_use"] == "NOT_EVALUATED"
    assert report["claim_truth"] == "UNKNOWN"
    if bound:
        assert report["assessments"][0]["use_disposition"] == "UNKNOWN"


@pytest.mark.parametrize("versions", VERSIONS)
@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("bound", [False, True])
def test_full_audit_protected_collision(versions, kind, bound):
    result = audit(fixture(kind, bound), versions)
    assert result.verdict == "FAIL" and "UNKNOWN" in result.violations
    assert "COMPOSITION_FORBIDDEN" not in result.violations
    doc = parse_evidence_ancestry_findings(result.verdict_basis)
    assert doc["candidate_ancestry"] == "UNKNOWN"
    assert doc["claim_truth"] == "UNKNOWN" and doc["candidate_use"] == "NOT_EVALUATED"
    if bound:
        assert doc["assessments"][0]["use_disposition"] == "UNKNOWN"


@pytest.mark.parametrize("versions", VERSIONS)
@pytest.mark.parametrize("bound", [False, True])
def test_noncolliding_composition_request_control(versions, bound):
    result = audit(fixture("COMPOSITION_REQUEST", bound, protected_id="F263-DISTINCT"), versions)
    doc = parse_evidence_ancestry_findings(result.verdict_basis)
    assert doc["candidate_ancestry"] == "TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT"
    if "M0-F15-1.0" not in versions:
        assert result.verdict == "FAIL" and "UNKNOWN" in result.violations
    else:
        assert result.verdict == "PASS" and result.violations == ()


def test_benign_equal_text_ids_still_pass():
    a = fixture()
    a = replace(a, claims=(*a.claims, replace(a.claims[0], claim_id=ID)),
                observations=(*a.observations, replace(a.observations[0], observation_id=ID)))
    r = audit(a, ("M0-1.0",))
    assert r.verdict == "PASS" and r.violations == ()


@pytest.mark.parametrize("versions", VERSIONS)
@pytest.mark.parametrize("field", ["observation_refs", "derivation_reference"])
def test_explicit_protected_reference_unchanged(versions, field):
    a = fixture("AUDIT_RESULT")
    ref = Reference(ID, "CLAIM")
    v = (ref,) if field == "observation_refs" else ref
    a = replace(a, evidence=(replace(a.evidence[0], **{field: v}),))
    r = audit(a, versions)
    assert r.verdict == "FAIL"
    assert r.violations == ("COMPOSITION_FORBIDDEN", "UNKNOWN")


def test_protected_ancestor_still_forbidden():
    a = fixture("AUDIT_RESULT")
    obs = replace(a.observations[0], provenance_refs=(Reference(ID, "EVIDENCE"),))
    a = replace(a, observations=(obs,))
    fact = _EvidenceAncestryGuard(a, ENGINE).facts(("OBSERVATION", "F263-O"))
    assert "COMPOSITION_FORBIDDEN" in fact["codes"]
    assert audit(a, ("M0-1.0",)).verdict == "FAIL"
