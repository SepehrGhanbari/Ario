"""Read-only integration probes against EXISTING Ario evidence/review modules.

This is not a deployed adapter. All inputs and ledger bytes are synthetic.
Exercises real functions from SourceMonitoringGuard, claim-support sidecar,
ledger observation, dossier builder, and ARP-0.1 review evaluator together.
"""
from __future__ import annotations

import hashlib
import json

from core.source_monitoring import SourceMonitoringGuard
from claim_support_readonly_lab import inspect_claim_support
from claim_support_consumer_boundary_lab import inspect_consumer_boundary
from ledger_observation_adapter import observe_ledger
from candidate_dossier_builder import build_candidate_dossier
from admission_review_evaluator import evaluate_review_request


def _chain(tmp_path):
    ledger = tmp_path / "synthetic-events.jsonl"
    ledger.write_bytes(
        (json.dumps({
            "event": "TASK_FINISHED",
            "timestamp": "2026-11-17T00:00:00Z",
            "status": "COMPLETED",
        }, sort_keys=True) + "\n").encode("utf-8")
    )
    initial_bytes = ledger.read_bytes()
    manifest = observe_ledger(ledger)
    assert manifest["status"] == "OBSERVED"
    dossier = build_candidate_dossier(
        manifest, ledger, line=1, claim_id="claim",
        claim_scope="Only the synthetic ledger's reported status",
        proposed_support_relation="Only reported status, not real-world truth",
    )
    assert dossier["status"] == "CANDIDATE"

    guard = SourceMonitoringGuard()
    guard.create_hypothesis("SYNTHETIC: task has objectively succeeded",
                            attribution_id="claim")
    stdout = "SYNTHETIC: local tool completed"
    execution_lock = "synthetic-integration-lock"
    guard.record_empirical_observation(
        assertion="SYNTHETIC: local tool ran, no claim entailment established",
        tool="run_tests",
        target="synthetic/local_test.py",
        exit_code=0,
        stdout=stdout,
        execution_lock=execution_lock,
        expected_stdout_sha256=hashlib.sha256(stdout.encode()).hexdigest(),
        expected_execution_lock_sha256=hashlib.sha256(execution_lock.encode()).hexdigest(),
        attribution_id="receipt",
    )
    original_attributions = guard.attributions
    view = inspect_claim_support(
        original_attributions, claim_id="claim",
        supporting_ids=("receipt",), proposed_relations={"receipt": "SUPPORTS"},
    )
    assert view["review_status"] == "REVIEWABLE_ONLY"
    queue = inspect_consumer_boundary(view)
    assert queue["queue_state"] == "MANUAL_REVIEW_CANDIDATE_ONLY"
    return ledger, initial_bytes, guard, original_attributions, manifest, dossier, view, queue


def _no_admission(outcome, queue):
    assert outcome["admission_decision"] == "NOT_EVALUATED"
    assert outcome["status"] in ("UNKNOWN", "REJECTED")
    assert queue["evidence_admission_allowed"] is False
    assert queue["memory_write_allowed"] is False
    assert queue["tool_execution_allowed"] is False
    assert queue["signing_allowed"] is False
    assert queue["trust_activation_allowed"] is False


def _arp_request(dossier):
    return {
        "policy_version": "ARP-0.1",
        "candidate": dossier,
        "candidate_digest": "UNKNOWN",
        "reviewer_id": "synthetic-user",
        "reviewer_role": "human-declared-only",
        "authorization_reference": "unverified-declaration",
        "requested_claim_id": dossier["claim_id"],
        "requested_claim_scope": dossier["claim_scope"],
        "requested_support_relation": dossier["proposed_support_relation"],
        "corroboration_refs": [],
        "review_rule_ids": ["ARP-0.1"],
        "limitations": "No independent authentication or truth review",
        "recorded_at": "SYNTHETIC",
        "decision": "REVIEWABLE",
    }


def test_real_arp_consumer_rejects_sidecar_report_as_wrong_envelope(tmp_path):
    ledger, before, guard, attrs, manifest, dossier, view, queue = _chain(tmp_path)
    outcome = evaluate_review_request(view, manifest, ledger)
    assert outcome["status"] == "REJECTED"
    _no_admission(outcome, queue)
    assert ledger.read_bytes() == before
    assert guard.attributions == attrs


def test_real_arp_consumer_does_not_admit_well_formed_declared_review(tmp_path):
    ledger, before, guard, attrs, manifest, dossier, view, queue = _chain(tmp_path)
    request = _arp_request(dossier)
    outcome = evaluate_review_request(request, manifest, ledger)
    assert outcome["status"] == "UNKNOWN"
    _no_admission(outcome, queue)
    assert ledger.read_bytes() == before
    assert guard.attributions == attrs


def test_real_arp_consumer_does_not_promote_sidecar_echoes_to_independence(tmp_path):
    ledger, before, guard, attrs, manifest, dossier, view, queue = _chain(tmp_path)
    request = _arp_request(dossier)
    request["corroboration_refs"] = [dict(view), dict(queue)]
    outcome = evaluate_review_request(request, manifest, ledger)
    assert outcome["status"] == "UNKNOWN"
    _no_admission(outcome, queue)
    assert ledger.read_bytes() == before
    assert guard.attributions == attrs


def test_real_arp_consumer_rejects_forged_admitted_request(tmp_path):
    ledger, before, guard, attrs, manifest, dossier, view, queue = _chain(tmp_path)
    request = _arp_request(dossier)
    request["decision"] = "ADMITTED"
    outcome = evaluate_review_request(request, manifest, ledger)
    assert outcome["status"] == "REJECTED"
    _no_admission(outcome, queue)
    assert ledger.read_bytes() == before
    assert guard.attributions == attrs
