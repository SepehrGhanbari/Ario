"""W2 synthetic-to-real RAC cross-layer *non-authority* checks.

Imports the ACTUAL reviewer_authorization_preflight module in Ario at
test runtime; no preflight implementation is duplicated in this PR.
This does NOT validate a production TB->M0 evidence bridge, Ario's M0 runtime,
or the authenticity of W2's injected SyntheticOracles.
"""
from dataclasses import replace
from hashlib import sha256

from test_w2_lab_verifier import baseline, with_oracle, PAYLOAD
from w2_lab_verifier import inspect
from reviewer_authorization_preflight import FIELDS, preflight_authorization


def rac_record(**changes):
    d = {
        "authorization_contract_version": "RAC-0.1",
        "grant_id": "GRANT-A",
        "issuer_id": "LAB-ISSUER-NOT-TRUSTED",
        "issuer_trust_basis": "externally_enrolled_roots in synthetic oracle only",
        "principal_id": "REVIEWER-A",
        "identity_binding_method": "unverified lab declaration",
        "permitted_action": "REVIEW_CANDIDATE",
        "policy_version": "ARP-0.1",
        "claim_scope": "Ledger reports an event",
        "candidate_binding": "unverified-lab-envelope",
        "validity_start": "20",
        "validity_end": "40",
        "verification_time_basis": "mock-clock-30",
        "revocation_reference": "mock-registry",
        "revocation_check": "ACTIVE",
        "separation_of_duties": "CLAIMED_INDEPENDENT",
        "signature_or_attestation": "MOCK_SIGNATURE",
        "verification_result": "VERIFIED_FOR_REVIEW_ONLY",
        "grant_limitations": "review only",
        "rule_version": "RAC-0.1",
    }
    assert set(d) == FIELDS
    d.update(changes)
    return d


def test_w2_mock_positive_does_not_cross_real_rac_authority_boundary():
    request, oracle = baseline()
    local = inspect(request, oracle)
    assert local.status == "LAB_REVIEWABLE_ONLY"
    assert local.admission_decision == "NOT_EVALUATED"
    real = preflight_authorization(rac_record())
    assert real["status"] == "UNKNOWN"
    assert real["authorization_decision"] == "NOT_CHECKED"
    assert real["admission_decision"] == "NOT_EVALUATED"


def test_w2_mock_trust_enrollment_cannot_be_reused_as_real_rac_trust_anchor():
    request, oracle = baseline()
    assert "ROOT-A" in oracle.externally_enrolled_roots
    assert inspect(request, oracle).status == "LAB_REVIEWABLE_ONLY"
    real = preflight_authorization(rac_record(
        issuer_trust_basis="ROOT-A",
        identity_binding_method="SIGNED_BY_ROOT_A",
        verification_result="VERIFIED_FOR_REVIEW_ONLY"))
    assert real["status"] == "UNKNOWN"
    assert real["authorization_decision"] == "NOT_CHECKED"


def test_w2_mock_reviewer_grant_cannot_authorize_evidence_admission_in_rac():
    request, oracle = baseline()
    assert inspect(request, oracle).status == "LAB_REVIEWABLE_ONLY"
    result = preflight_authorization(rac_record(permitted_action="ADMIT_EVIDENCE"))
    assert result["status"] == "REJECTED"
    assert result["admission_decision"] == "NOT_EVALUATED"


def test_w2_revocation_known_adverse_preserved_in_real_rac_preflight():
    request, oracle = baseline()
    assert inspect(request, with_oracle(oracle, revocation={"GRANT-A": "REVOKED"})).status == "REJECTED"
    result = preflight_authorization(rac_record(revocation_check="REVOKED"))
    assert result["status"] == "REJECTED"
    assert result["authorization_decision"] == "NOT_CHECKED"


def test_w2_same_reviewer_as_proposer_is_not_authorized_in_rac():
    request, oracle = baseline()
    assert inspect(replace(request, reviewer=request.proposer), oracle).status == "REJECTED"
    result = preflight_authorization(rac_record(separation_of_duties="SELF_REVIEW"))
    assert result["status"] == "REJECTED"


def test_w2_byte_level_detection_does_not_create_review_authority():
    request, oracle = baseline()
    tampered = PAYLOAD.replace(b"COMPLETED", b"FAILED")
    assert sha256(tampered).hexdigest() != request.sources[0].claimed_digest
    lab = inspect(request, with_oracle(oracle, payload_store={"blob-A": tampered}))
    assert (lab.status, lab.reason) == ("REJECTED", "PAYLOAD_DIGEST_MISMATCH")
    real = preflight_authorization(rac_record())
    assert real["status"] == "UNKNOWN"
    assert real["admission_decision"] == "NOT_EVALUATED"
