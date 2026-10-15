"""W3 test-assurance mutation controls: a deliberately wrong result MUST be caught."""
import pytest
import test_w3_custody_event_redteam as w3
from w2_lab_verifier import Result


@pytest.mark.parametrize("test_func", [
    w3.test_w3_red_f03_same_custodian_different_roots_not_independent,
    w3.test_w3_red_f04_reviewer_controls_source_despite_distinct_proposer,
    w3.test_w3_red_f05_same_status_different_events_not_corroboration,
    w3.test_w3_red_f06_same_type_status_distinct_event_instances_not_comparable,
])
def test_w3_fault_injection_catches_fake_reviewability(monkeypatch, test_func):
    monkeypatch.setattr(w3, "inspect", lambda request, oracle: Result(
        "LAB_REVIEWABLE_ONLY", "FORGED_BYPASS"))
    with pytest.raises(AssertionError):
        test_func()


def test_w3_fault_injection_catches_wrong_reason_even_if_status_unknown(monkeypatch):
    monkeypatch.setattr(w3, "inspect", lambda request, oracle: Result(
        "UNKNOWN", "UNRELATED_UNKNOWN"))
    with pytest.raises(AssertionError):
        w3.test_w3_red_f03_same_custodian_different_roots_not_independent()
