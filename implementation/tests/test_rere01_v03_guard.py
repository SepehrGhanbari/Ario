"""Post-hoc N15/N16 RERE-01 research comparator regressions.

RESEARCH_ONLY / HOLD. These tests validate a synthetic controller fixture,
not real authentication, custody, memory admission, persistence or truth.
Source and counterexamples: RERE_01_V03_POSTHOC_EXPERIMENT.json.
"""
from core.audit_engine import AuditEngine, AuditInput
from core.schema import Assessment, Reference, SupportTarget, Timestamp
from research.rere01.revision_comparator_v0_2 import (
    EVENT_ID, PROFILE, LabAssessment, LabObservation, SyntheticPolicy, project,
)


def _fixture():
    t = "2026-11-18T00:00:00Z"
    policy = SyntheticPolicy(
        profile=PROFILE, event_id=EVENT_ID, event_time=t,
        pinned_roots=(("C", "root-C"), ("CAL", "root-CAL")),
        calibration_pairs=(("CAL", "C"),),
    )

    def assess(name, seq, target_id, target_type, prop, evidence, evaluation, reason):
        return LabAssessment(
            seq=seq,
            assessment=Assessment(
                assessment_id=name, assessment_version="v0.2",
                rule_version=PROFILE,
                admissible_evidence_refs=(Reference(evidence, "LAB_OBSERVATION"),),
                condition_evaluation=evaluation,
                assessment_basis="synthetic contract, never external authority",
                scope=EVENT_ID,
                target=SupportTarget(Reference(target_id, target_type), prop),
            ),
            reason_code=reason,
        )

    a = LabObservation(1, "LAB-A", "A", "root-A", "OPEN", t, EVENT_ID)
    b = LabObservation(2, "LAB-B", "B", "root-B", "CLOSED", t, EVENT_ID)
    c = LabObservation(3, "LAB-C", "C", "root-C", "CLOSED", t, EVENT_ID)
    t3 = assess(
        "LAB-T3", 4, EVENT_ID, "CLAIM", "DOOR_OPEN", "LAB-C",
        "OPEN_REFUTED", "C_CONTRADICTS_OPEN",
    )
    cal = LabObservation(
        5, "LAB-CAL", "CAL", "root-CAL", "CLOCK_MISMATCH",
        "2026-11-18T00:05:00Z", EVENT_ID, target_record_id="LAB-C",
    )
    t4 = assess(
        "LAB-T4", 6, "LAB-T3", "ASSESSMENT",
        "PRIOR_JUSTIFICATION_RELIABILITY", "LAB-CAL",
        "T3_BASIS_UNRELIABLE", "CALIBRATION_REVOKES_C",
    )
    again = assess(
        "LAB-T3-AGAIN", 7, EVENT_ID, "CLAIM", "DOOR_OPEN",
        "LAB-C", "OPEN_REFUTED", "C_CONTRADICTS_OPEN",
    )
    bad = LabObservation(5, "LAB-BAD", "BAD", "root-BAD", "CLOSED", t, EVENT_ID)
    bad_review = assess(
        "LAB-BAD-REVIEW", 6, EVENT_ID, "CLAIM", "DOOR_OPEN",
        "LAB-BAD", "OPEN_REFUTED", "C_CONTRADICTS_OPEN",
    )
    return policy, (a, b, c, t3, cal, t4, again), (a, b, c, t3, bad, bad_review)


def test_rere03_positive_t3_and_t4_still_have_distinct_views():
    policy, rows, _ = _fixture()
    before = project(rows[:4], policy)
    after = project(rows[:6], policy)
    assert before.event_outcome == "CONDITIONALLY_REFUTED_IN_LAB"
    assert after.event_outcome == "UNKNOWN"
    assert dict(after.assessment_reliability)["LAB-T3"] == "CHALLENGED_BY_LATER_CALIBRATION"
    assert before.historical_record_ids == after.historical_record_ids[:4]
    assert not after.evidence_authorized_for_real_memory


def test_rere03_n15_unwarranted_late_review_cannot_launder_reason():
    policy, _, rows = _fixture()
    result = project(rows, policy)
    assert result.event_outcome == "CONDITIONALLY_REFUTED_IN_LAB"
    assert result.active_reasons == ("C_MATCHED_FROZEN_SYNTHETIC_CONTROLLER",)
    assert dict(result.assessment_reliability)["LAB-BAD-REVIEW"] == "NOT_WARRANTED"


def test_rere03_n16_challenged_c_cannot_resurrect_prior_t3_result():
    policy, rows, _ = _fixture()
    result = project(rows, policy)
    assert result.event_outcome == "UNKNOWN"
    assert "T3_JUSTIFICATION_NO_LONGER_RELIABLE" in result.active_reasons
    assert dict(result.assessment_reliability)["LAB-T3-AGAIN"] == "NOT_WARRANTED"
    assert result.historical_record_ids == tuple(item.record_id for item in rows)
    assert not result.evidence_authorized_for_real_memory


def test_rere03_m0_audit_rejects_unadmitted_toy_evidence():
    policy, rows, _ = _fixture()
    t3, t4 = rows[3], rows[5]
    actual_m0 = AuditEngine().audit(
        AuditInput(assessments=(t3.assessment, t4.assessment)),
        rule_versions=("M0-1.0", "M0-F11-1.0"),
        configuration_id="RERE03-READONLY",
        execution_timestamp=Timestamp("2026-11-18T00:00:00Z"),
        audit_id="RERE03-M0",
    )
    assert actual_m0.verdict == "FAIL"
    assert "EVIDENCE_INADMISSIBLE" in actual_m0.violations
    assert project(rows[:6], policy).evidence_authorized_for_real_memory is False
