"""W1 cross-layer witness-to-M0 adversarial regression (synthetic only).

Reuses existing TB-002/003/004, RAC/ARP, and M0 test fixtures.
Neither a laboratory witness nor a caller-supplied report can become a
production source-authentication or evidence-admission authority.
No keys, live trust roots, production evidence, or network devices.
"""

from dataclasses import replace
import copy
import json

import pytest

import independent_witness_experiment as witness
import witness_provenance_experiment as provenance
import witness_compromise_recovery_experiment_v0_2 as recovery
from core.audit_engine import parse_evidence_ancestry_findings
from core.schema import IndependenceStatus

import test_independent_witness_experiment as tb002
import test_witness_provenance_experiment as tb003
import test_witness_compromise_recovery_experiment_v0_2 as tb004
import test_m0_regression as m0
import test_reviewer_authorization_preflight as rac


def _assert_no_witness_authority(report):
    assert report.evidence_admission == "NOT_EVALUATED"
    assert report.historical_event_truth == "UNKNOWN"
    assert report.production_historical_continuity == "INCONCLUSIVE"


def _caller_wrap_report(report, *, wrappers=2):
    """Explicitly untrusted CALLER wrapper; NOT an authorized M0 adapter.

    The report's own kind is used as a *claimed* reference type.
    This test does not authenticate the reporter or the reference.
    """
    return m0._eag_fixture(
        parent=m0._eag_ref("W1-UNTRUSTED-LAB-REPORT", report.kind),
        wrappers=wrappers,
    )


def _assert_m0_no_promotion(artifacts, name):
    result = m0.run(name, artifacts)
    findings = parse_evidence_ancestry_findings(result.verdict_basis)
    assert findings["independent_admission_authority"] == "NONE"
    assert findings["claim_truth"] == "UNKNOWN"
    assert findings["entity_continuity"] == "UNKNOWN"
    rows = findings["assessments"]
    assert len(rows) == 1
    assert rows[0]["source_authentication"] == "UNKNOWN"
    assert rows[0]["use_disposition"] in ("UNKNOWN", "KNOWN_INADMISSIBLE")
    return result, findings


def test_w1_01_agreeing_tb002_witnesses_do_not_admit_m0_evidence():
    out = witness.verify_witnesses(tb002.case())
    assert out.aggregate_verdict == "CONDITIONAL_CORRESPONDENCE"
    assert out.custody_independence == "ASSUMED_FOR_EXPERIMENT"
    assert out.cryptographic_witness_authenticity == "NOT_CHECKED"
    assert out.historical_custody_independence == "NOT_ESTABLISHED"
    _assert_no_witness_authority(out)
    _assert_m0_no_promotion(_caller_wrap_report(out), "W1-01")


def test_w1_02_tb003_control_graph_is_lab_conditional_not_authenticated():
    out = provenance.evaluate_provenance(tb003.baseline())
    assert out.source_independence.status == "LAB_CONDITIONALLY_DISTINCT"
    assert out.administrative_separation.status == "LAB_CONDITIONALLY_SEPARATE"
    assert out.production_custody_authenticity == "NOT_ESTABLISHED"
    _assert_no_witness_authority(out)
    _assert_m0_no_promotion(_caller_wrap_report(out), "W1-02")


def test_w1_03_duplicate_control_domain_does_not_create_two_witnesses():
    out = witness.verify_witnesses(
        tb002.case(b=tb002.envelope("B", group="LAB-GROUP-A")))
    assert out.cross_witness_commitment_relation.status == "AGREE"
    assert out.custody_independence == "UNKNOWN"
    _assert_no_witness_authority(out)
    _assert_m0_no_promotion(_caller_wrap_report(out), "W1-03")


def test_w1_04_tb004_usable_checkpoint_is_not_a_trust_root():
    out = recovery.evaluate_recovery(tb004.base())
    assert out.evidentiary_usability.status == (
        "CONDITIONALLY_USABLE_FOR_NAMED_COMPARISON")
    assert out.production_custody_authenticity == "NOT_ESTABLISHED"
    assert out.actual_revocation == "NOT_PERFORMED"
    _assert_no_witness_authority(out)
    _assert_m0_no_promotion(_caller_wrap_report(out), "W1-04")


@pytest.mark.parametrize("generator", [
    pytest.param(lambda: witness.verify_witnesses(tb002.case()), id="TB-002"),
    pytest.param(lambda: provenance.evaluate_provenance(tb003.baseline()), id="TB-003"),
    pytest.param(lambda: recovery.evaluate_recovery(tb004.base()), id="TB-004"),
])
def test_w1_05_attacker_wraps_lab_report_in_m0_independent_label(generator):
    report = generator()
    artifacts = _caller_wrap_report(report)
    # This independence label is asserted by the caller, not authenticated.
    assert artifacts.evidence[0].independence_status == IndependenceStatus.INDEPENDENT
    _assert_m0_no_promotion(artifacts, "W1-05-" + report.kind)


def test_w1_06_known_multihop_c0_to_o1_o2_o3_c1_cannot_promote():
    from core.schema import EpistemicStatus
    source = m0._eag_claim("W1-C0", EpistemicStatus.UNSUPPORTED)
    artifacts = m0._eag_fixture(
        parent=m0._eag_ref("W1-C0", "CLAIM"), wrappers=3)
    artifacts = replace(artifacts, claims=(source, *artifacts.claims))
    _, findings = _assert_m0_no_promotion(artifacts, "W1-06")
    assert source.status == EpistemicStatus.UNSUPPORTED
    assert findings["assessments"][0]["ancestry"] == (
        "TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT")
    assert findings["assessments"][0]["use_disposition"] == "UNKNOWN"
    # Omitted semantic equivalence cannot be inferred from a missing link.


def test_w1_07_fake_reviewer_grant_does_not_grant_admission():
    from reviewer_authorization_preflight import preflight_authorization
    grant = rac.grant()
    grant["signature_or_attestation"] = "SELF-SIGNED-EXPERIMENT"
    grant["verification_result"] = "VERIFIED_FOR_REVIEW_ONLY"
    original = copy.deepcopy(grant)
    out = preflight_authorization(grant)
    assert out["status"] == "UNKNOWN"
    assert out["authorization_decision"] == "NOT_CHECKED"
    assert out["admission_decision"] == "NOT_EVALUATED"
    assert grant == original
    grant["permitted_action"] = "ADMIT_EVIDENCE"
    assert preflight_authorization(grant)["status"] == "REJECTED"


def test_w1_08_revoked_grant_and_conflicting_witnesses_fail_closed():
    from reviewer_authorization_preflight import preflight_authorization
    grant = rac.grant()
    grant["revocation_check"] = "REVOKED"
    assert preflight_authorization(grant)["status"] == "REJECTED"
    _, parent, child = tb002.altered_b_checkpoint(0, "hostile other history")
    report = witness.verify_witnesses(
        tb002.case(b=tb002.envelope("B", child, parent)))
    assert report.cross_witness_commitment_relation.status == "CONFLICT"
    assert report.aggregate_verdict == "UNRESOLVED_CONFLICT"
    _assert_no_witness_authority(report)
    _assert_m0_no_promotion(_caller_wrap_report(report), "W1-08")


def test_w1_09_record_presence_positive_control_does_not_become_truth():
    findings = parse_evidence_ancestry_findings(
        m0.run("W1-09", m0._eag_fixture(presence=True)).verdict_basis)
    row = findings["assessments"][0]
    assert row["record_presence"] == "MATCH"
    assert row["use_disposition"] == "RECORD_DESCRIPTION_ONLY"
    assert row["source_authentication"] == "UNKNOWN"
    assert findings["independent_admission_authority"] == "NONE"
    assert findings["claim_truth"] == "UNKNOWN"
    assert findings["entity_continuity"] == "UNKNOWN"


def test_w1_10_repeated_audit_same_snapshot_keeps_findings_stable():
    lab = witness.verify_witnesses(tb002.case())
    artifacts = _caller_wrap_report(lab)
    first = m0.run("W1-10", artifacts)
    second = m0.run("W1-10", artifacts)
    assert parse_evidence_ancestry_findings(first.verdict_basis) == (
        parse_evidence_ancestry_findings(second.verdict_basis))
    _assert_m0_no_promotion(artifacts, "W1-10")


def test_w1_11_replayed_report_cannot_authenticate_itself():
    report = provenance.evaluate_provenance(tb003.baseline())
    artifacts = _caller_wrap_report(report, wrappers=3)
    _, findings = _assert_m0_no_promotion(artifacts, "W1-11")
    assert "ADMITTED" not in json.dumps(findings, sort_keys=True)


def test_w1_12_compromised_tb004_witness_cannot_authorize():
    report = recovery.evaluate_recovery(
        tb004.base(observations=(tb004.obs(earliest=9, confirmed=25),)))
    assert report.evidentiary_usability.status == "SUSPENDED"
    _assert_no_witness_authority(report)
    _assert_m0_no_promotion(_caller_wrap_report(report), "W1-12")


def test_w1_13_audit_result_ancestry_is_explicitly_inadmissible():
    artifacts = m0._eag_fixture(
        parent=m0._eag_ref("W1-PRIOR-AUDIT", "AUDIT_RESULT"), wrappers=2)
    artifacts = replace(artifacts, prior_audit_results=(
        m0._f11_audit_result("W1-PRIOR-AUDIT"),))
    result, findings = _assert_m0_no_promotion(artifacts, "W1-13")
    assert "COMPOSITION_FORBIDDEN" in result.violations
    assert findings["assessments"][0]["use_disposition"] == "KNOWN_INADMISSIBLE"


def test_w1_14_arp_cannot_admit_fake_tb_corroboration(tmp_path):
    from admission_review_evaluator import evaluate_review_request
    from candidate_dossier_builder import build_candidate_dossier
    from ledger_observation_adapter import observe_ledger

    ledger = tmp_path / "w1-synthetic-events.jsonl"
    ledger.write_text(json.dumps({
        "event": "TASK_FINISHED",
        "timestamp": "2026-10-11T00:00:00Z",
        "status": "COMPLETED",
    }) + "\n", encoding="utf-8")
    before = ledger.read_bytes()
    manifest = observe_ledger(ledger)
    dossier = build_candidate_dossier(
        manifest, ledger, line=1, claim_id="W1-C1",
        claim_scope="Only synthetic ledger event is reported",
        proposed_support_relation="Only reported status")
    assert dossier["status"] == "CANDIDATE"
    req = {
        "policy_version": "ARP-0.1",
        "candidate": dossier,
        "candidate_digest": "UNKNOWN",
        "reviewer_id": "claimed-independent-reviewer",
        "reviewer_role": "human",
        "authorization_reference": "claimed-not-trusted",
        "requested_claim_id": "W1-C1",
        "requested_claim_scope": "Only synthetic ledger event is reported",
        "requested_support_relation": "Only reported status",
        "corroboration_refs": [
            {"type": "TB-002", "claimed_status": "CONDITIONAL_CORRESPONDENCE"},
            {"type": "TB-003", "claimed_status": "LAB_CONDITIONALLY_DISTINCT"},
        ],
        "review_rule_ids": ["ARP-0.1"],
        "limitations": "Untrusted synthetic witness aliases, no external root",
        "recorded_at": "reported-local-only",
        "decision": "NOT_EVALUATED",
    }
    result = evaluate_review_request(req, manifest, ledger)
    assert result["status"] == "UNKNOWN"
    assert result["admission_decision"] == "NOT_EVALUATED"
    assert ledger.read_bytes() == before
