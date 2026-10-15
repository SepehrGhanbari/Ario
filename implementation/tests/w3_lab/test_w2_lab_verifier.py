"""Synthetic W2 negative-control fixtures: no Ario runtime or production trust."""
from dataclasses import replace
from hashlib import sha256
import pytest
from w2_lab_verifier import (
    Source, SourceBinding, ReviewGrant, Request, SyntheticOracles,
    inspect, parse_strict_metadata, mock_candidate_digest,
)

PAYLOAD = b'{"event":"TASK_FINISHED","reported_status":"COMPLETED"}\n'
DIGEST = sha256(PAYLOAD).hexdigest()
TARGET = dict(claim_id="C1", scope="Ledger reports an event", use="INDEPENDENT_TARGET_SUPPORT",
              audience="LAB-ARIO", epoch="LAB-EPOCH-A")


def baseline():
    source = Source(label="CLAIMED-WITNESS-A", locator="blob-A", claimed_digest=DIGEST,
                    custodian="CUSTODIAN-A", root="ROOT-A", parents=("ORIGIN-A",), **TARGET)
    bound = SourceBinding(actual_digest=DIGEST, custodian=source.custodian,
                          root=source.root, parents=source.parents, **TARGET)
    request = Request(sources=(source,), reviewer="REVIEWER-A", proposer="PROPOSER-A",
                      grant_id="GRANT-A", action="REVIEW_CANDIDATE", **TARGET)
    grant = ReviewGrant("REVIEWER-A", "REVIEW_CANDIDATE", "C1",
                        TARGET["scope"], "LAB-ARIO", "LAB-EPOCH-A", 20, 40,
                        mock_candidate_digest(request))
    oracle = SyntheticOracles(payload_store={"blob-A": PAYLOAD},
                              authenticated_sources={"blob-A": bound},
                              externally_enrolled_roots=frozenset({"ROOT-A"}),
                              review_grants={"GRANT-A": grant},
                              revocation={"GRANT-A": "FRESH_ACTIVE"}, trusted_now=30)
    return request, oracle


def with_oracle(oracle, **changes):
    return replace(oracle, **changes)


def assert_result(result, status, reason):
    assert result.status == status
    assert result.reason == reason
    assert result.admission_decision == "NOT_EVALUATED"
    assert result.claim_truth == "UNKNOWN"
    assert result.source_authentication == "NOT_ESTABLISHED_IN_PRODUCTION"


def test_w2_p01_only_mock_reviewability_not_real_admission():
    r, o = baseline()
    assert_result(inspect(r, o), "LAB_REVIEWABLE_ONLY", "MOCK_ONLY_NO_AUTHORITY")


def test_w2_n01_stale_digest_with_real_bytes_is_rejected():
    r, o = baseline()
    changed = PAYLOAD.replace(b"COMPLETED", b"FAILED")
    assert sha256(changed).hexdigest() != DIGEST
    assert_result(inspect(r, with_oracle(o, payload_store={"blob-A": changed})),
                  "REJECTED", "PAYLOAD_DIGEST_MISMATCH")


def test_w2_n01b_stale_digest_with_no_bytes_is_unknown():
    r, o = baseline()
    assert_result(inspect(r, with_oracle(o, payload_store={})),
                  "UNKNOWN", "PAYLOAD_NOT_RETRIEVABLE")


def test_w2_n02_two_forged_labels_are_not_two_roots():
    r, o = baseline()
    a = r.sources[0]
    b = replace(a, label="CLAIMED-WITNESS-B", locator="blob-B")
    bound = o.authenticated_sources["blob-A"]
    forged = replace(r, sources=(a, b))
    oracle = with_oracle(o, payload_store={"blob-A": PAYLOAD, "blob-B": PAYLOAD},
                         authenticated_sources={"blob-A": bound, "blob-B": bound})
    assert_result(inspect(forged, oracle), "UNKNOWN", "SHARED_ANCESTRY_NOT_INDEPENDENT")


def test_w2_n03_different_bytes_same_source_parent_cannot_inflate():
    r, o = baseline()
    original = r.sources[0]
    other_bytes = PAYLOAD + b"second representation"
    other_digest = sha256(other_bytes).hexdigest()
    other = replace(original, locator="blob-B", claimed_digest=other_digest,
                    root="ROOT-B", custodian="CUSTODIAN-B", label="WITNESS-B")
    other_bound = replace(o.authenticated_sources["blob-A"], actual_digest=other_digest,
                          custodian="CUSTODIAN-B", root="ROOT-B", parents=("ORIGIN-A",))
    # The declared parent is deliberately forged, unlike the oracle's source.
    req = replace(r, sources=(original, replace(other, parents=("FAKE-UNRELATED",))))
    oracle = with_oracle(o,
        payload_store={"blob-A": PAYLOAD, "blob-B": other_bytes},
        authenticated_sources={"blob-A": o.authenticated_sources["blob-A"], "blob-B": other_bound},
        externally_enrolled_roots=frozenset({"ROOT-A", "ROOT-B"}))
    # Deliberate mismatch between claimed ancestry and verified binding is detected first.
    assert_result(inspect(req, oracle), "REJECTED", "SOURCE_BINDING_MISMATCH")
    req = replace(r, sources=(original, replace(other, parents=("ORIGIN-A",))))
    assert_result(inspect(req, oracle), "UNKNOWN", "SHARED_ANCESTRY_NOT_INDEPENDENT")


def test_w2_n04_omitted_lineage_remains_unknown():
    r, o = baseline()
    req = replace(r, sources=(replace(r.sources[0], parents=None),))
    assert_result(inspect(req, o), "UNKNOWN", "ANCESTRY_OMITTED")


def test_w2_n05_forged_signature_and_self_enrolled_root_not_trusted():
    r, o = baseline()
    assert r.sources[0].signature_claim
    assert_result(inspect(r, with_oracle(o, externally_enrolled_roots=frozenset())),
                  "UNKNOWN", "SOURCE_ROOT_UNTRUSTED")
    assert_result(inspect(r, with_oracle(o, authenticated_sources={})),
                  "UNKNOWN", "SOURCE_BINDING_MISSING")


def test_w2_n06_review_only_grant_cannot_authorize_admission():
    r, o = baseline()
    assert_result(inspect(replace(r, action="ADMIT_EVIDENCE"), o),
                  "REJECTED", "ACTION_NOT_ALLOWED")
    assert_result(inspect(replace(r, sources=(replace(r.sources[0], scope="Claim is true"),)), o),
                  "REJECTED", "SOURCE_TARGET_SCOPE_MISMATCH")
    assert_result(inspect(replace(r, reviewer=r.proposer), o), "REJECTED", "SELF_REVIEW")


def test_w2_n07_revoked_missing_clock_and_stale_revocation_fail_closed():
    r, o = baseline()
    assert_result(inspect(r, with_oracle(o, revocation={"GRANT-A": "REVOKED"})),
                  "REJECTED", "GRANT_REVOKED")
    assert_result(inspect(r, with_oracle(o, revocation={})),
                  "UNKNOWN", "REVOCATION_FRESHNESS_UNVERIFIED")
    assert_result(inspect(r, with_oracle(o, trusted_now=None)),
                  "UNKNOWN", "TRUSTED_CLOCK_UNAVAILABLE")
    assert_result(inspect(r, with_oracle(o, trusted_now=50)),
                  "REJECTED", "REVIEW_GRANT_EXPIRED_OR_NOT_YET_VALID")


def test_w2_n08_replay_wrong_audience_or_epoch_blocked():
    r, o = baseline()
    for key, new in (("audience", "ANOTHER-SERVICE"), ("epoch", "ANOTHER-EPOCH")):
        req = replace(r, **{key: new}, sources=(replace(r.sources[0], **{key: new}),))
        assert_result(inspect(req, o), "REJECTED", "SOURCE_BINDING_MISMATCH")


def test_w2_n09_duplicate_json_keys_and_nonfinite_numbers_rejected():
    for raw in (b'{"claim":"A","claim":"B"}', b'{"amount":NaN}', b'{"x":Infinity}', b'[]'):
        with pytest.raises(ValueError):
            parse_strict_metadata(raw)
    assert parse_strict_metadata(b'{"claim":"A","n":2}') == {"claim": "A", "n": 2}


def test_w2_n10_conflicting_mock_reports_do_not_assert_truth():
    r, o = baseline()
    other_bytes = PAYLOAD.replace(b"COMPLETED", b"FAILED")
    source = replace(r.sources[0], label="WITNESS-B", locator="blob-B",
                     claimed_digest=sha256(other_bytes).hexdigest(),
                     root="ROOT-B", parents=("ORIGIN-B",), custodian="CUSTODIAN-B")
    binding = replace(o.authenticated_sources["blob-A"], actual_digest=source.claimed_digest,
                      root=source.root, parents=source.parents, custodian=source.custodian)
    oracle = with_oracle(o, payload_store={"blob-A": PAYLOAD, "blob-B": other_bytes},
        authenticated_sources={"blob-A": o.authenticated_sources["blob-A"], "blob-B": binding},
        externally_enrolled_roots=frozenset({"ROOT-A", "ROOT-B"}))
    # Reports explicitly disagree over the exact same declared field.
    # We preserve conflict without deciding what occurred externally.
    joint_request = replace(r, sources=(r.sources[0], source))
    mock_grant = replace(o.review_grants["GRANT-A"],
                         bound_candidate_digest=mock_candidate_digest(joint_request))
    oracle = with_oracle(oracle, review_grants={"GRANT-A": mock_grant})
    result = inspect(joint_request, oracle)
    assert_result(result, "UNKNOWN", "CONFLICTING_REPORTED_STATUSES")


def test_w2_n11_incorrect_source_binding_is_rejected_even_for_matching_digest():
    r, o = baseline()
    certified = replace(o.authenticated_sources["blob-A"], custodian="OTHER-CUSTODIAN")
    assert_result(inspect(r, with_oracle(o, authenticated_sources={"blob-A": certified})),
                  "REJECTED", "SOURCE_BINDING_MISMATCH")


def test_w2_n12_no_synthetic_authority_can_change_original_payloads():
    r, o = baseline()
    raw = o.payload_store["blob-A"]
    digest = sha256(raw).hexdigest()
    for _ in range(2):
        inspect(r, o)
    assert o.payload_store["blob-A"] == raw
    assert sha256(o.payload_store["blob-A"]).hexdigest() == digest


def test_w2_n02b_identical_bytes_with_distinct_mock_roots_still_not_proven_independent():
    r, o = baseline()
    a = r.sources[0]
    b = replace(a, label="OTHER-WITNESS", locator="blob-B", root="ROOT-B",
                parents=("ORIGIN-B",), custodian="CUSTODIAN-B")
    binding = replace(o.authenticated_sources["blob-A"], root="ROOT-B",
                      parents=("ORIGIN-B",), custodian="CUSTODIAN-B")
    oracle = with_oracle(o, payload_store={"blob-A": PAYLOAD, "blob-B": PAYLOAD},
        authenticated_sources={"blob-A": o.authenticated_sources["blob-A"], "blob-B": binding},
        externally_enrolled_roots=frozenset({"ROOT-A", "ROOT-B"}))
    assert_result(inspect(replace(r, sources=(a, b)), oracle),
                  "UNKNOWN", "IDENTICAL_PAYLOAD_INDEPENDENCE_UNPROVEN")


def test_w2_n13_bad_digest_size_and_missing_review_grant():
    r, o = baseline()
    req = replace(r, sources=(replace(r.sources[0], claimed_digest="deadbeef"),))
    assert_result(inspect(req, o), "REJECTED", "DIGEST_FORMAT_INVALID")
    oracle = with_oracle(o, payload_store={"blob-A": b"!" * (1024 * 1024 + 1)})
    assert_result(inspect(r, oracle), "REJECTED", "PAYLOAD_TYPE_OR_SIZE_INVALID")
    assert_result(inspect(r, with_oracle(o, review_grants={})),
                  "UNKNOWN", "REVIEW_GRANT_UNVERIFIED")


def test_w2_n14_review_grant_bound_to_candidate_cannot_be_replayed_on_other_dossier():
    r, o = baseline()
    # Rename an otherwise identical report. The same review grant no longer
    # covers the new candidate dossier, even though the payload matches.
    new_source = replace(r.sources[0], label="NEW-CLAIMED-WITNESS")
    different_dossier = replace(r, sources=(new_source,))
    assert mock_candidate_digest(r) != mock_candidate_digest(different_dossier)
    assert_result(inspect(different_dossier, o), "REJECTED",
                  "REVIEW_GRANT_CANDIDATE_BINDING_MISMATCH")
