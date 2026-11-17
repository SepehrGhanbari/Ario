"""Adversarial, synthetic consumer-side tests for research-only #260.

Do not mistake these tests for an integration proof: no real consumer is
currently wired to the experimental view or to this projection.
"""
import copy
import pytest

from core.source_monitoring import SourceMonitoringGuard
from claim_support_readonly_lab import inspect_claim_support
from claim_support_consumer_boundary_lab import inspect_consumer_boundary


DENIED_FLAGS = (
    "evidence_admission_allowed",
    "tool_execution_allowed",
    "memory_write_allowed",
    "signing_allowed",
    "trust_activation_allowed",
)


def _candidate(*, relation="SUPPORTS"):
    guard = SourceMonitoringGuard()
    guard.create_hypothesis("SYNTHETIC PRIVATE: three tests passed",
                            attribution_id="claim")
    receipt = "SYNTHETIC: three tests passed"
    import hashlib
    lock = "synthetic-consumer-lock"
    guard.record_empirical_observation(
        assertion=receipt,
        tool="run_tests",
        target="synthetic/consumer_demo.py",
        exit_code=0,
        stdout=receipt,
        execution_lock=lock,
        expected_stdout_sha256=hashlib.sha256(receipt.encode()).hexdigest(),
        expected_execution_lock_sha256=hashlib.sha256(lock.encode()).hexdigest(),
        attribution_id="receipt",
    )
    history = guard.attributions
    view = inspect_claim_support(
        history, claim_id="claim", supporting_ids=("receipt",),
        proposed_relations={"receipt": relation},
    )
    return guard, history, view


def _assert_denied(result):
    for flag in DENIED_FLAGS:
        assert result[flag] is False
    assert result["epistemic_verdict"] == "NOT_ASSESSED"
    assert result["contract_adoption"] == "NOT_ADOPTED"
    assert "assertion" not in result


def test_positive_candidate_is_queue_only_never_evidence():
    guard, original, view = _candidate()
    assert view["review_status"] == "REVIEWABLE_ONLY"
    before = copy.deepcopy(view)
    result = inspect_consumer_boundary(view)
    assert result["queue_state"] == "MANUAL_REVIEW_CANDIDATE_ONLY"
    assert result["reason_code"] == "UNAUTHENTICATED_PROPOSAL"
    assert view == before
    assert guard.attributions == original
    _assert_denied(result)


def test_unrelated_declared_receipt_has_no_queue_candidate():
    _, _, view = _candidate(relation="UNRELATED")
    assert view["review_status"] == "UNKNOWN"
    result = inspect_consumer_boundary(view)
    assert result["queue_state"] == "NO_CANDIDATE"
    assert result["reason_code"] == "SOURCE_VIEW_UNKNOWN"
    _assert_denied(result)


def test_naive_consumer_counterexample_is_not_an_authorization():
    # Illustrates the proposed risk, NOT a claim about existing production code.
    _, _, view = _candidate()
    unsafe_hypothetical_consumer = view["review_status"] == "REVIEWABLE_ONLY"
    assert unsafe_hypothetical_consumer is True
    result = inspect_consumer_boundary(view)
    assert result["evidence_admission_allowed"] is False
    assert result["memory_write_allowed"] is False
    _assert_denied(result)


@pytest.mark.parametrize("field,value", [
    ("contract_version", "attacker_v1"),
    ("source_authenticity", "AUTHENTICATED"),
    ("semantic_support", "SUPPORTED"),
    ("claim_assessment", "TRUE"),
    ("admission_decision", "ADMITTED"),
    ("reviewer_authorization", "APPROVED"),
    ("memory_mutation", "WRITE"),
    ("history_mutation", "OVERWRITE"),
    ("contract_adoption", "ADOPTED"),
    ("independent_support_count", 1),
    ("reason_code", "AUTHORIZED_SUPPORT"),
    ("execution_integrity", "INDEPENDENT_VERIFIED"),
    ("review_status", "VERIFIED_EMPIRICAL"),
    ("review_status", "ACCEPTED"),
])
def test_authority_forgery_and_old_statuses_never_grant(field, value):
    _, _, view = _candidate()
    view[field] = value
    result = inspect_consumer_boundary(view)
    assert result["queue_state"] == "NO_CANDIDATE"
    _assert_denied(result)


@pytest.mark.parametrize("field,value", [
    ("claimed_support_count", True),
    ("unique_receipt_count", True),
    ("claimed_support_count", -1),
    ("claimed_support_count", 17),
    ("claimed_support_count", 2),
    ("unique_receipt_count", 0),
    ("unique_receipt_count", 17),
    ("independent_support_count", True),
])
def test_invalid_counts_and_boolean_as_integer_are_rejected(field, value):
    _, _, view = _candidate()
    view[field] = value
    result = inspect_consumer_boundary(view)
    assert result["queue_state"] == "NO_CANDIDATE"
    _assert_denied(result)


@pytest.mark.parametrize("payload", [
    None, [], "REVIEWABLE_ONLY", True, 1, {"review_status": "REVIEWABLE_ONLY"},
])
def test_malformed_raw_payloads_fail_closed(payload):
    result = inspect_consumer_boundary(payload)
    assert result["queue_state"] == "NO_CANDIDATE"
    _assert_denied(result)


def test_extra_approval_field_cannot_override_gate_or_leak_text():
    _, _, view = _candidate()
    view["admit_now"] = "PRIVATE_SYNTHETIC_DO_NOT_ECHO"
    result = inspect_consumer_boundary(view)
    assert result["queue_state"] == "NO_CANDIDATE"
    assert "PRIVATE_SYNTHETIC_DO_NOT_ECHO" not in str(result)
    _assert_denied(result)


def test_no_untrusted_claim_or_receipt_text_is_echoed():
    _, _, view = _candidate()
    view["reason_code"] = "PRIVATE_SYNTHETIC_DO_NOT_ECHO"
    result = inspect_consumer_boundary(view)
    assert "PRIVATE_SYNTHETIC_DO_NOT_ECHO" not in str(result)
    _assert_denied(result)


def test_dictionary_subclass_cannot_claim_approval():
    class UntrustedMapping(dict):
        pass
    _, _, view = _candidate()
    result = inspect_consumer_boundary(UntrustedMapping(view))
    assert result["queue_state"] == "NO_CANDIDATE"
    _assert_denied(result)


def test_state_is_not_cached_across_untrusted_view_changes():
    _, _, view = _candidate()
    first = inspect_consumer_boundary(view)
    assert first["queue_state"] == "MANUAL_REVIEW_CANDIDATE_ONLY"
    view["review_status"] = "UNKNOWN"
    second = inspect_consumer_boundary(view)
    assert second["queue_state"] == "NO_CANDIDATE"
    _assert_denied(first)
    _assert_denied(second)


def test_output_contains_no_raw_report_or_legacy_approval_keys():
    _, _, view = _candidate()
    result = inspect_consumer_boundary(view)
    assert "review_status" not in result
    assert "claimed_support_count" not in result
    assert "unique_receipt_count" not in result
    assert "verified" not in result
    assert "supported" not in result
    assert "accepted" not in result
    _assert_denied(result)
