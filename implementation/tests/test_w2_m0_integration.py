"""W2 synthetic negative cross-layer probes against real Ario M0/RAC/ARP.

No trust authority, production adapter, historical evidence or positive admission.
This intentionally characterizes the untrusted-payload visibility gap.
"""
from dataclasses import replace
import json

import test_m0_regression as m0
import test_witness_eag_integration as w1
from core.audit_engine import parse_evidence_ancestry_findings
from core.schema import IndependenceStatus
from reviewer_authorization_preflight import preflight_authorization
from admission_review_evaluator import evaluate_review_request
from ledger_observation_adapter import observe_ledger
from candidate_dossier_builder import build_candidate_dossier


def _guard(artifacts, label):
    result = m0.run(label, artifacts)
    report = parse_evidence_ancestry_findings(result.verdict_basis)
    assert report["independent_admission_authority"] == "NONE"
    assert report["claim_truth"] == "UNKNOWN"
    assert report["entity_continuity"] == "UNKNOWN"
    assert len(report["assessments"]) == 1
    row = report["assessments"][0]
    assert row["source_authentication"] == "UNKNOWN"
    return result, report, row


def test_w2_m0_01_signed_looking_report_and_grant_are_not_authority():
    report = w1.provenance.evaluate_provenance(w1.tb003.baseline())
    grant = w1.rac.grant()
    grant["signature_or_attestation"] = "LAB-FAKE-SIGNATURE"
    grant["verification_result"] = "VERIFIED_FOR_REVIEW_ONLY"
    review = preflight_authorization(grant)
    assert review["status"] == "UNKNOWN"
    assert review["authorization_decision"] == "NOT_CHECKED"
    assert review["admission_decision"] == "NOT_EVALUATED"
    _, findings, row = _guard(w1._caller_wrap_report(report), "W2-M0-01")
    assert row["use_disposition"] == "UNKNOWN"
    assert findings["independent_admission_authority"] == "NONE"


def test_w2_m0_02_stale_claimed_digest_is_a_visibility_gap_not_detection():
    original = w1.witness.verify_witnesses(w1.tb002.case())
    changed = replace(original, aggregate_verdict="ATTACKER_REWROTE_REPORT")
    old_digest = w1._lab_report_digest(original)
    assert old_digest != w1._lab_report_digest(changed)
    correct = w1._caller_wrap_report(original, claimed_digest=old_digest)
    forged = w1._caller_wrap_report(changed, claimed_digest=old_digest)
    assert correct.observations == forged.observations
    assert correct.evidence == forged.evidence
    _, first, row_a = _guard(correct, "W2-M0-02")
    _, second, row_b = _guard(forged, "W2-M0-02")
    assert first == second
    assert row_a["use_disposition"] == row_b["use_disposition"] == "UNKNOWN"


def test_w2_m0_03_two_independent_labels_with_shared_typed_root_inflate():
    shared = m0._eag_ref("W2-UPSTREAM-C0", "CLAIM")
    first = m0._eag_fixture(parent=shared)
    target = first.assessments[0].target
    other_observation = m0._eag_obs("W2-O2", target, (shared,))
    other_evidence = m0._eag_ev("W2-E2", ("W2-O2",), IndependenceStatus.INDEPENDENT)
    joint = replace(first,
        claims=(m0._eag_claim("W2-UPSTREAM-C0"), *first.claims),
        observations=(*first.observations, other_observation),
        evidence=(*first.evidence, other_evidence),
        assessments=(m0._eag_assessment(target, evidence_ids=("EAG-E1", "W2-E2")),))
    result, _, row = _guard(joint, "W2-M0-03")
    assert "EVIDENCE_INFLATION" in result.violations
    assert row["use_disposition"] == "UNKNOWN"


def test_w2_m0_04_omitted_ancestry_cannot_become_independent_support():
    missing = m0._eag_ref("W2-MISSING-CUSTODY", "OBSERVATION")
    _, findings, row = _guard(m0._eag_fixture(parent=missing, wrappers=2), "W2-M0-04")
    assert row["use_disposition"] == "UNKNOWN"
    assert row["ancestry"] == "UNKNOWN"
    assert findings["independent_admission_authority"] == "NONE"


def test_w2_m0_05_revoked_grant_never_upgrades_witness_report():
    report = w1.recovery.evaluate_recovery(w1.tb004.base())
    grant = w1.rac.grant()
    grant["revocation_check"] = "REVOKED"
    decision = preflight_authorization(grant)
    assert (decision["status"], decision["admission_decision"]) == ("REJECTED", "NOT_EVALUATED")
    _, _, row = _guard(w1._caller_wrap_report(report), "W2-M0-05")
    assert row["use_disposition"] == "UNKNOWN"


def test_w2_m0_06_real_arp_screening_does_not_instantiate_m0_evidence(tmp_path):
    ledger = tmp_path / "w2-synthetic-events.jsonl"
    ledger.write_text(json.dumps({"event": "TASK_FINISHED", "timestamp": "2026-10-15T00:00:00Z",
                                  "status": "COMPLETED"}) + "\n", encoding="utf-8")
    before = ledger.read_bytes()
    manifest = observe_ledger(ledger)
    candidate = build_candidate_dossier(manifest, ledger, line=1, claim_id="W2-C1",
        claim_scope="Synthetic ledger reports a status",
        proposed_support_relation="Only the recorded status")
    assert candidate["status"] == "CANDIDATE"
    request = {
        "policy_version": "ARP-0.1", "candidate": candidate,
        "candidate_digest": "UNKNOWN", "reviewer_id": "FAKE-REVIEWER",
        "reviewer_role": "human", "authorization_reference": "FAKE-GRANT",
        "requested_claim_id": "W2-C1",
        "requested_claim_scope": "Synthetic ledger reports a status",
        "requested_support_relation": "Only the recorded status",
        "corroboration_refs": [{"type": "TB-002", "claimed_status": "CONDITIONAL_CORRESPONDENCE"}],
        "review_rule_ids": ["ARP-0.1"], "limitations": "synthetic source only",
        "recorded_at": "reported-local-time", "decision": "NOT_EVALUATED",
    }
    checked = evaluate_review_request(request, manifest, ledger)
    assert (checked["status"], checked["admission_decision"]) == ("UNKNOWN", "NOT_EVALUATED")
    assert ledger.read_bytes() == before
    _, _, row = _guard(m0._eag_fixture(
        parent=m0._eag_ref("W2-ARP-CANDIDATE", "ADMISSION_REVIEW")), "W2-M0-06")
    assert row["use_disposition"] == "UNKNOWN"
