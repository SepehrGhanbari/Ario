"""W3 synthetic laboratory RED controls, never authentication/admission tests.

These oracles are test-injected assumptions, not a real witness or signer.
"""
from dataclasses import replace
from hashlib import sha256

from test_w2_lab_verifier import PAYLOAD, baseline, with_oracle, assert_result
from w2_lab_verifier import inspect, mock_candidate_digest

SECOND = b'{"event":"TASK_FINISHED","reported_status":"COMPLETED","witness":"B"}\n'
OTHER_EVENT = b'{"event":"AUDIT_FINISHED","reported_status":"COMPLETED","witness":"B"}\n'
CONFLICT = b'{"event":"TASK_FINISHED","reported_status":"FAILED","witness":"B"}\n'


def pair_case(raw=SECOND, *, second_custodian="CUSTODIAN-B", reviewer=None):
    """Two distinct mock roots + mock parents + payloads; NOT real independence."""
    req, oracle = baseline()
    a = req.sources[0]
    b = replace(
        a,
        label="LAB-WITNESS-B", locator="blob-B", claimed_digest=sha256(raw).hexdigest(),
        custodian=second_custodian, root="ROOT-B", parents=("ORIGIN-B",),
    )
    binding = replace(
        oracle.authenticated_sources["blob-A"],
        actual_digest=b.claimed_digest, custodian=b.custodian, root=b.root,
        parents=b.parents,
    )
    req = replace(req, sources=(a, b), reviewer=(reviewer or req.reviewer))
    grant = replace(oracle.review_grants["GRANT-A"], reviewer=req.reviewer,
                    bound_candidate_digest=mock_candidate_digest(req))
    oracle = with_oracle(
        oracle,
        payload_store={"blob-A": PAYLOAD, "blob-B": raw},
        authenticated_sources={"blob-A": oracle.authenticated_sources["blob-A"],
                               "blob-B": binding},
        externally_enrolled_roots=frozenset({"ROOT-A", "ROOT-B"}),
        review_grants={"GRANT-A": grant},
    )
    return req, oracle


def test_w3_red_f03_same_custodian_different_roots_not_independent():
    req, oracle = pair_case(second_custodian="CUSTODIAN-A")
    assert req.sources[0].claimed_digest != req.sources[1].claimed_digest
    assert req.sources[0].root != req.sources[1].root
    assert req.sources[0].custodian == req.sources[1].custodian
    assert_result(inspect(req, oracle), "UNKNOWN", "SHARED_CUSTODIAN_NOT_INDEPENDENT")


def test_w3_red_f04_reviewer_controls_source_despite_distinct_proposer():
    req, oracle = pair_case(reviewer="CUSTODIAN-A")
    assert req.reviewer != req.proposer
    assert req.reviewer == req.sources[0].custodian
    assert_result(inspect(req, oracle), "REJECTED", "REVIEWER_SOURCE_CONFLICT")


def test_w3_red_f05_same_status_different_events_not_corroboration():
    req, oracle = pair_case(raw=OTHER_EVENT)
    assert req.sources[0].root != req.sources[1].root
    assert_result(inspect(req, oracle), "UNKNOWN", "EVENT_TYPE_MISMATCH")


def test_w3_p01_consistent_distinct_mock_roles_still_only_reviewable_in_lab():
    req, oracle = pair_case()
    assert_result(inspect(req, oracle), "LAB_REVIEWABLE_ONLY", "MOCK_ONLY_NO_AUTHORITY")


def test_w3_n06_conflicting_status_with_same_event_stays_unknown():
    req, oracle = pair_case(raw=CONFLICT)
    assert_result(inspect(req, oracle), "UNKNOWN", "CONFLICTING_REPORTED_STATUSES")


def test_w3_n07_hidden_same_controller_is_undetectable_from_identical_fixture():
    req, oracle = pair_case()
    # In world A, the mock source labels refer to independently controlled
    # entities. In world B, the SAME bytes and labels conceal a shared real
    # controller. The verifier sees identical inputs in both worlds, and
    # therefore cannot infer historical independence or authenticity.
    world_a = inspect(req, oracle)
    world_b = inspect(req, oracle)
    assert world_a == world_b
    assert_result(world_a, "LAB_REVIEWABLE_ONLY", "MOCK_ONLY_NO_AUTHORITY")
    # The explicit epistemic limits must not be erased by mock reviewability.
    assert world_b.source_authentication == "NOT_ESTABLISHED_IN_PRODUCTION"
    assert world_b.claim_truth == "UNKNOWN"
    assert world_b.admission_decision == "NOT_EVALUATED"


def test_w3_n08_missing_event_field_blocks_cross_report_comparability():
    missing_event = b'{"reported_status":"COMPLETED","witness":"B"}\n'
    req, oracle = pair_case(raw=missing_event)
    assert_result(inspect(req, oracle), "UNKNOWN", "EVENT_TYPE_UNAVAILABLE")


def test_w3_n09_different_events_with_conflicting_status_keeps_type_mismatch():
    different = b'{"event":"AUDIT_FINISHED","reported_status":"FAILED","witness":"B"}\n'
    req, oracle = pair_case(raw=different)
    assert_result(inspect(req, oracle), "UNKNOWN", "EVENT_TYPE_MISMATCH")
