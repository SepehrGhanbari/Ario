"""Synthetic tests for non-persistent scoped correction classification."""
import pytest

from human_revision_policy import CorrectionEvent, evaluate_correction


def event(**changes):
    values = dict(
        event_id="CORR-1", target_reference="SUMMARY-T1",
        subject_reference="SUBJECT-1", scope="FUTURE_PERSONALIZATION",
        new_interpretation_reference="SUMMARY-T2",
        authority_status="EXTERNALLY_VERIFIED",
    )
    values.update(changes)
    return CorrectionEvent(**values)


def test_authorized_same_scope_is_reviewable_not_applied():
    result = evaluate_correction(event(), expected_scope="FUTURE_PERSONALIZATION")
    assert result.status == "ACCEPTABLE_FOR_SCOPED_REVIEW"
    assert result.future_use == "DO_NOT_USE_SUPERSEDED_INTERPRETATION_IN_THIS_SCOPE"
    assert result.historical_record_action == "NO_MUTATION"
    assert result.persistence == "NONE"


def test_unknown_authority_remains_unknown():
    result = evaluate_correction(
        event(authority_status="UNKNOWN"),
        expected_scope="FUTURE_PERSONALIZATION",
    )
    assert result.status == "UNKNOWN"
    assert result.reason == "AUTHORITY_UNKNOWN"


def test_unverified_authority_is_rejected():
    result = evaluate_correction(
        event(authority_status="UNVERIFIED"),
        expected_scope="FUTURE_PERSONALIZATION",
    )
    assert result.status == "REJECTED"


def test_scope_mismatch_cannot_change_other_context():
    result = evaluate_correction(
        event(scope="HEALTH_CONTEXT"),
        expected_scope="FUTURE_PERSONALIZATION",
    )
    assert result.status == "REJECTED"
    assert result.reason == "SCOPE_MISMATCH"
    assert result.future_use == "NO_CHANGE"


def test_replayed_event_is_rejected():
    result = evaluate_correction(
        event(), expected_scope="FUTURE_PERSONALIZATION",
        seen_event_ids=frozenset({"CORR-1"}),
    )
    assert result.reason == "REPLAYED_EVENT_ID"


@pytest.mark.parametrize("changes", [
    {"event_id": ""}, {"target_reference": ""},
    {"subject_reference": ""}, {"scope": ""},
    {"new_interpretation_reference": ""},
])
def test_missing_required_context_stays_unknown(changes):
    result = evaluate_correction(
        event(**changes), expected_scope="FUTURE_PERSONALIZATION"
    )
    assert result.status == "UNKNOWN"
    assert result.future_use == "NO_CHANGE"


def test_correction_requires_no_explanation_field():
    result = evaluate_correction(event(), expected_scope="FUTURE_PERSONALIZATION")
    assert result.status == "ACCEPTABLE_FOR_SCOPED_REVIEW"


def test_third_party_claim_is_not_verified_by_helper():
    result = evaluate_correction(
        event(authority_status="THIRD_PARTY_ASSERTS_AUTHORITY"),
        expected_scope="FUTURE_PERSONALIZATION",
    )
    assert result.status == "REJECTED"


def test_policy_makes_no_retention_or_erasure_decision():
    result = evaluate_correction(event(), expected_scope="FUTURE_PERSONALIZATION")
    assert result.persistence == "NONE"
    assert result.historical_record_action == "NO_MUTATION"
    assert result.identity_verdict == "NONE"
