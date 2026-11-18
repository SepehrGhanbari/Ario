"""RERE-01 v0.2 pre-registered controller-fixture tests (synthetic only).

Passing these tests establishes only the read-only comparator's bounded behavior.
It does not change the seven failures or three missing APIs observed in PR #210.
"""
from dataclasses import replace

import pytest

from core.schema import Assessment, Reference, SupportTarget
from research.rere01.revision_comparator_v0_2 import (
    EVENT_ID, PROFILE, LabAssessment, LabContractError, LabObservation,
    SyntheticPolicy, project,
)


T0 = "2026-11-18T00:00:00Z"


def _assessment(name, target_id, target_type, property_id, evidence, evaluation):
    return Assessment(
        assessment_id=name,
        assessment_version="v0.2",
        rule_version=PROFILE,
        admissible_evidence_refs=(Reference(evidence, "LAB_OBSERVATION"),),
        condition_evaluation=evaluation,
        assessment_basis="Research synthetic controller predicate, never real evidence",
        scope=EVENT_ID,
        target=SupportTarget(Reference(target_id, target_type), property_id),
    )


def _policy():
    return SyntheticPolicy(
        profile=PROFILE, event_id=EVENT_ID, event_time=T0,
        pinned_roots=(("C", "root-C"), ("CAL", "root-CAL")),
        calibration_pairs=(("CAL", "C"),),
    )


def _records():
    a = LabObservation(1, "LAB-A", "A", "root-A", "OPEN", T0, EVENT_ID)
    b = LabObservation(2, "LAB-B", "B", "root-B", "CLOSED", T0, EVENT_ID)
    c = LabObservation(3, "LAB-C", "C", "root-C", "CLOSED", T0, EVENT_ID)
    t3 = LabAssessment(
        4,
        _assessment("LAB-T3", EVENT_ID, "CLAIM", "DOOR_OPEN",
                    "LAB-C", "OPEN_REFUTED"),
        "C_CONTRADICTS_OPEN",
    )
    cal = LabObservation(
        5, "LAB-CAL", "CAL", "root-CAL", "CLOCK_MISMATCH",
        "2026-11-18T00:05:00Z", EVENT_ID, target_record_id="LAB-C",
    )
    t4 = LabAssessment(
        6,
        _assessment("LAB-T4", "LAB-T3", "ASSESSMENT",
                    "PRIOR_JUSTIFICATION_RELIABILITY",
                    "LAB-CAL", "T3_BASIS_UNRELIABLE"),
        "CALIBRATION_REVOKES_C",
    )
    return (a, b, c, t3, cal, t4)


def _reliability(result):
    return dict(result.assessment_reliability)


def test_rere02_p01_t1_t2_keep_unknown_without_pinned_source():
    r = project(_records()[:2], _policy())
    assert r.event_outcome == "UNKNOWN"
    assert r.historical_record_ids == ("LAB-A", "LAB-B")
    assert r.evidence_authorized_for_real_memory is False


def test_rere02_p02_t3_synthetic_controller_conditionally_refutes_open():
    r = project(_records()[:4], _policy())
    assert r.event_outcome == "CONDITIONALLY_REFUTED_IN_LAB"
    assert _reliability(r)["LAB-T3"] == "CONDITIONALLY_WARRANTED_IN_LAB"
    assert "LAB-C" in r.historical_record_ids
    assert not r.evidence_authorized_for_real_memory


def test_rere02_p03_t4_assesses_t3_and_downgrades_without_erasure():
    original = _records()
    r = project(original, _policy())
    assert r.event_outcome == "UNKNOWN"
    assert _reliability(r)["LAB-T3"] == "CHALLENGED_BY_LATER_CALIBRATION"
    assert _reliability(r)["LAB-T4"] == "CONDITIONALLY_WARRANTED_IN_LAB"
    assert r.historical_record_ids == tuple(x.record_id for x in original)
    assert "T3_JUSTIFICATION_NO_LONGER_RELIABLE" in r.active_reasons
    assert original[3].assessment.condition_evaluation == "OPEN_REFUTED"
    assert original[5].assessment.target.subject_reference == Reference(
        "LAB-T3", "ASSESSMENT")


def test_rere02_p04_input_permutation_does_not_change_frozen_sequence_view():
    fixture = _records()
    assert project(fixture, _policy()) == project(tuple(reversed(fixture)), _policy())


def test_rere02_p05_asof_t3_recoverable_even_after_t4():
    fixture = _records()
    r3 = project(fixture[:4], _policy())
    r4 = project(fixture, _policy())
    assert r3.event_outcome == "CONDITIONALLY_REFUTED_IN_LAB"
    assert r4.event_outcome == "UNKNOWN"
    assert r3.historical_record_ids == r4.historical_record_ids[:4]


def test_rere02_n01_newer_unverified_b_does_not_win():
    fixture = _records()
    assert fixture[1].reported_value == "CLOSED"
    assert project(fixture[:2], _policy()).event_outcome == "UNKNOWN"


def test_rere02_n02_copied_root_cannot_independently_invalidate():
    fixture = list(_records())
    fixture[4] = replace(fixture[4], origin_root="root-C")
    policy = replace(_policy(), pinned_roots=(("C", "root-C"), ("CAL", "root-C")))
    r = project(tuple(fixture), policy)
    assert r.event_outcome == "CONDITIONALLY_REFUTED_IN_LAB"
    assert _reliability(r)["LAB-T4"] == "NOT_WARRANTED"


def test_rere02_n03_calibration_wrong_source_target_cannot_invalidate():
    fixture = list(_records())
    fixture[4] = replace(fixture[4], target_record_id="LAB-A")
    r = project(tuple(fixture), _policy())
    assert r.event_outcome == "CONDITIONALLY_REFUTED_IN_LAB"
    assert _reliability(r)["LAB-T4"] == "NOT_WARRANTED"


def test_rere02_n04_reasonless_second_order_review_cannot_invalidate():
    fixture = list(_records())
    fixture[5] = replace(fixture[5], reason_code="")
    r = project(tuple(fixture), _policy())
    assert r.event_outcome == "CONDITIONALLY_REFUTED_IN_LAB"
    assert _reliability(r)["LAB-T4"] == "NOT_WARRANTED"


def test_rere02_n05_missing_prior_assessment_fails_closed():
    a, b, c, t3, cal, t4 = _records()
    with pytest.raises(LabContractError, match="prior assessment"):
        project((a, b, c, replace(cal, seq=4), replace(t4, seq=5)), _policy())


def test_rere02_n06_reused_id_with_changed_content_fails_closed():
    fixture = _records()
    bad = replace(fixture[0], reported_value="CLOSED")
    with pytest.raises(LabContractError, match="altered content"):
        project(fixture + (bad,), _policy())


def test_rere02_n07_replayed_identical_event_id_is_projection_idempotent():
    fixture = _records()
    assert project(fixture, _policy()) == project(fixture + (fixture[0],), _policy())


def test_rere02_n08_missing_sequence_fails_closed():
    fixture = _records()
    with pytest.raises(LabContractError, match="sequence"):
        project((fixture[0], fixture[2]), _policy())


def test_rere02_n09_self_assessment_cycle_fails_closed():
    fixture = list(_records())
    self_target = SupportTarget(Reference("LAB-T4", "ASSESSMENT"),
                                "PRIOR_JUSTIFICATION_RELIABILITY")
    fixture[5] = replace(
        fixture[5],
        assessment=replace(fixture[5].assessment, target=self_target),
    )
    with pytest.raises(LabContractError, match="self-directed"):
        project(tuple(fixture), _policy())


def test_rere02_n10_c_without_controller_root_pin_remains_unknown():
    policy = replace(_policy(), pinned_roots=(("CAL", "root-CAL"),))
    assert project(_records()[:4], policy).event_outcome == "UNKNOWN"


def test_rere02_n11_c_wrong_valid_time_remains_unknown():
    fixture = list(_records())
    fixture[2] = replace(fixture[2], observed_at="2026-11-18T00:01:00Z")
    assert project(tuple(fixture[:4]), _policy()).event_outcome == "UNKNOWN"


def test_rere02_n12_hash_like_receipt_without_pin_does_not_promote():
    fixture = list(_records())
    fixture[2] = replace(fixture[2], declared_receipt="f" * 64)
    policy = replace(_policy(), pinned_roots=(("CAL", "root-CAL"),))
    r = project(tuple(fixture[:4]), policy)
    assert r.event_outcome == "UNKNOWN"
    assert r.evidence_authorized_for_real_memory is False
