"""Synthetic nonprivileged tests of the read-only claim-support proposal view."""
import hashlib
import dataclasses

import pytest

from core.source_monitoring import SourceMonitoringGuard, VeracityState
from claim_support_readonly_lab import inspect_claim_support, CONTRACT_VERSION


def _receipt(guard, identifier, assertion="SYNTHETIC: calculator ran",
             parents=(), stdout="SYNTHETIC: 3 tests passed"):
    lock = "synthetic-lock-" + identifier
    return guard.record_empirical_observation(
        assertion=assertion,
        tool="run_tests",
        target="synthetic/calculator_test.py",
        exit_code=0,
        stdout=stdout,
        execution_lock=lock,
        expected_stdout_sha256=hashlib.sha256(stdout.encode()).hexdigest(),
        expected_execution_lock_sha256=hashlib.sha256(lock.encode()).hexdigest(),
        parent_attribution_ids=parents,
        attribution_id=identifier,
    )


def _check_firewall(report):
    assert report["contract_version"] == CONTRACT_VERSION
    assert report["source_authenticity"] == "UNKNOWN"
    assert report["claim_assessment"] == "NOT_ASSESSED"
    assert report["semantic_support"] == "NOT_ASSESSED"
    assert report["admission_decision"] == "NOT_EVALUATED"
    assert report["reviewer_authorization"] == "NOT_ESTABLISHED"
    assert report["independent_support_count"] == 0
    assert report["memory_mutation"] == "NONE"
    assert report["history_mutation"] == "NONE"
    assert report["contract_adoption"] == "NOT_ADOPTED"
    assert "assertion" not in report


def test_unrelated_successful_tool_never_verifies_astro_claim():
    g = SourceMonitoringGuard()
    g.create_hypothesis("SYNTHETIC: the moon is made of cheese", attribution_id="c")
    _receipt(g, "r")
    before = g.attributions
    report = inspect_claim_support(
        before, claim_id="c", supporting_ids=("r",),
        proposed_relations={"r": "UNRELATED"})
    assert report["review_status"] == "UNKNOWN"
    assert report["reason_code"] == "DECLARED_UNRELATED"
    assert g.attributions == before
    _check_firewall(report)


def test_contradictory_receipt_never_proves_claim():
    g = SourceMonitoringGuard()
    g.create_hypothesis("SYNTHETIC: tests had 0 failures", attribution_id="c")
    _receipt(g, "r", assertion="SYNTHETIC: tests had 1 failure",
             stdout="SYNTHETIC: 1 failed, 2 passed")
    report = inspect_claim_support(
        g.attributions, claim_id="c", supporting_ids=("r",),
        proposed_relations={"r": "CONTRADICTS"})
    assert report["reason_code"] == "DECLARED_CONTRADICTION"
    assert report["review_status"] == "UNKNOWN"
    _check_firewall(report)


def test_duplicate_receipt_id_does_not_mint_independent_support():
    g = SourceMonitoringGuard()
    g.create_hypothesis("SYNTHETIC: tests ran", attribution_id="c")
    _receipt(g, "r")
    report = inspect_claim_support(
        g.attributions, claim_id="c", supporting_ids=("r", "r"),
        proposed_relations={"r": "SUPPORTS"})
    assert report["reason_code"] == "DUPLICATE_RECEIPT"
    assert report["unique_receipt_count"] == 1
    assert report["review_status"] == "UNKNOWN"
    _check_firewall(report)


def test_relevant_positive_receipt_is_reviewable_not_admitted():
    g = SourceMonitoringGuard()
    g.create_hypothesis("SYNTHETIC: 3 calculator tests passed", attribution_id="c")
    _receipt(g, "r", assertion="SYNTHETIC: 3 calculator tests passed")
    old = g.attributions
    report = inspect_claim_support(
        old, claim_id="c", supporting_ids=("r",),
        proposed_relations={"r": "SUPPORTS"})
    assert report["review_status"] == "REVIEWABLE_ONLY"
    assert report["reason_code"] == "UNAUTHENTICATED_SUPPORT_PROPOSAL"
    assert report["claimed_support_count"] == 1
    assert report["execution_integrity"] == "LEGACY_REPORTED_VERIFIED"
    assert g.attributions == old
    _check_firewall(report)


def test_malicious_supports_label_still_cannot_verify_unrelated_claim():
    g = SourceMonitoringGuard()
    g.create_hypothesis("SYNTHETIC: moon made of cheese", attribution_id="c")
    _receipt(g, "r", assertion="SYNTHETIC: calculator output is 2")
    report = inspect_claim_support(
        g.attributions, claim_id="c", supporting_ids=("r",),
        proposed_relations={"r": "SUPPORTS"})
    assert report["review_status"] == "REVIEWABLE_ONLY"
    assert report["claim_assessment"] == "NOT_ASSESSED"
    _check_firewall(report)


def test_missing_relation_or_unknown_stays_unknown():
    g = SourceMonitoringGuard()
    g.create_hypothesis("SYNTHETIC: tests ran", attribution_id="c")
    _receipt(g, "r")
    a = inspect_claim_support(
        g.attributions, claim_id="c", supporting_ids=("r",),
        proposed_relations={})
    b = inspect_claim_support(
        g.attributions, claim_id="c", supporting_ids=("r",),
        proposed_relations={"r": "UNKNOWN"})
    assert a["reason_code"] == "MISSING_OR_INVALID_RELATION"
    assert b["reason_code"] == "RELATION_UNKNOWN"
    _check_firewall(a)
    _check_firewall(b)


def test_bad_or_unverified_tool_receipt_not_reviewable():
    g = SourceMonitoringGuard()
    g.create_hypothesis("SYNTHETIC: tests ran", attribution_id="c")
    g.create_external_testimony("SYNTHETIC: tests ran", attribution_id="r")
    report = inspect_claim_support(
        g.attributions, claim_id="c", supporting_ids=("r",),
        proposed_relations={"r": "SUPPORTS"})
    assert report["reason_code"] == "NO_ELIGIBLE_EXECUTION_RECEIPT"
    _check_firewall(report)


def test_shared_ancestor_not_distinct_source_independence():
    g = SourceMonitoringGuard()
    g.create_hypothesis("SYNTHETIC: tests ran", attribution_id="c")
    g.create_external_testimony("SYNTHETIC: original common source", attribution_id="root")
    _receipt(g, "r1", parents=("root",))
    _receipt(g, "r2", parents=("root",))
    report = inspect_claim_support(
        g.attributions, claim_id="c", supporting_ids=("r1", "r2"),
        proposed_relations={"r1": "SUPPORTS", "r2": "SUPPORTS"})
    assert report["reason_code"] == "SHARED_DECLARED_ANCESTRY"
    assert report["review_status"] == "UNKNOWN"
    _check_firewall(report)


def test_disjoint_declared_sources_remain_unproven_but_reviewable():
    g = SourceMonitoringGuard()
    g.create_hypothesis("SYNTHETIC: tests ran", attribution_id="c")
    _receipt(g, "r1")
    _receipt(g, "r2")
    report = inspect_claim_support(
        g.attributions, claim_id="c", supporting_ids=("r1", "r2"),
        proposed_relations={"r1": "SUPPORTS", "r2": "SUPPORTS"})
    assert report["review_status"] == "REVIEWABLE_ONLY"
    assert report["claimed_support_count"] == 2
    assert report["independent_support_count"] == 0
    _check_firewall(report)


def test_unknown_parent_and_cycle_fail_closed_without_mutation():
    g = SourceMonitoringGuard()
    g.create_hypothesis("SYNTHETIC: tests ran", attribution_id="c")
    _receipt(g, "orphan", parents=("missing",))
    _receipt(g, "cyclic", parents=("c",))
    old = g.attributions
    a = inspect_claim_support(
        old, claim_id="c", supporting_ids=("orphan",),
        proposed_relations={"orphan": "SUPPORTS"})
    b = inspect_claim_support(
        old, claim_id="c", supporting_ids=("cyclic",),
        proposed_relations={"cyclic": "SUPPORTS"})
    assert a["reason_code"] == "UNKNOWN_ANCESTRY"
    assert b["reason_code"] == "CLAIM_CYCLE"
    assert g.attributions == old
    _check_firewall(a)
    _check_firewall(b)


def test_historical_verified_claim_not_reinterpreted_as_truth():
    g = SourceMonitoringGuard()
    g.create_hypothesis("SYNTHETIC: moon cheese", attribution_id="c")
    _receipt(g, "r")
    g.evaluate_claim_promotion("c", ["r"])  # scratch V1 outcome only
    assert g.attributions["c"].veracity_state is VeracityState.VERIFIED_EMPIRICAL
    old = g.attributions
    report = inspect_claim_support(
        old, claim_id="c", supporting_ids=("r",),
        proposed_relations={"r": "UNRELATED"})
    assert report["review_status"] == "UNKNOWN"
    assert g.attributions == old
    _check_firewall(report)


def test_reject_oversize_and_malformed_inputs_without_echo():
    g = SourceMonitoringGuard()
    g.create_hypothesis("PRIVATE_SYNTHETIC_SECRET_GOAL", attribution_id="c")
    _receipt(g, "r")
    a = inspect_claim_support(
        g.attributions, claim_id="c", supporting_ids=("r",) * 17,
        proposed_relations={"r": "SUPPORTS"})
    b = inspect_claim_support(
        g.attributions, claim_id="c", supporting_ids=["r"],
        proposed_relations={"r": "SUPPORTS"})
    c = inspect_claim_support(
        g.attributions, claim_id="c", supporting_ids=("r",),
        proposed_relations={"r": "AUTOMATICALLY_APPROVED"})
    assert a["review_status"] == b["review_status"] == c["review_status"] == "UNKNOWN"
    for result in [a, b, c]:
        assert "PRIVATE_SYNTHETIC_SECRET_GOAL" not in str(result)
        _check_firewall(result)


def test_receipt_must_not_cite_itself_as_ancestor():
    g = SourceMonitoringGuard()
    g.create_hypothesis("SYNTHETIC: completed test", attribution_id="c")
    _receipt(g, "r", parents=("r",))
    old = g.attributions
    result = inspect_claim_support(
        old, claim_id="c", supporting_ids=("r",),
        proposed_relations={"r": "SUPPORTS"})
    assert result["review_status"] == "UNKNOWN"
    assert result["reason_code"] == "EVIDENCE_CYCLE"
    assert old == g.attributions
    _check_firewall(result)


def test_mutually_citing_receipts_must_not_be_reviewable():
    g = SourceMonitoringGuard()
    g.create_hypothesis("SYNTHETIC: completed test", attribution_id="c")
    _receipt(g, "r1", parents=("r2",))
    _receipt(g, "r2", parents=("r1",))
    result = inspect_claim_support(
        g.attributions, claim_id="c", supporting_ids=("r1",),
        proposed_relations={"r1": "SUPPORTS"})
    assert result["review_status"] == "UNKNOWN"
    assert result["reason_code"] == "EVIDENCE_CYCLE"
    _check_firewall(result)


def test_large_declared_ancestry_is_rejected_before_expansion():
    g = SourceMonitoringGuard()
    g.create_hypothesis("SYNTHETIC: completed test", attribution_id="c")
    _receipt(g, "r", parents=("untrusted",) * 257)
    before = g.attributions
    report = inspect_claim_support(
        before, claim_id="c", supporting_ids=("r",),
        proposed_relations={"r": "SUPPORTS"})
    assert report["review_status"] == "UNKNOWN"
    assert report["reason_code"] == "ANCESTRY_BUDGET_EXCEEDED"
    assert before == g.attributions
    _check_firewall(report)


def test_direct_derivation_between_receipts_is_shared_ancestry():
    """Two receipts are not two recorded lineages when one cites the other."""
    g = SourceMonitoringGuard()
    g.create_hypothesis("SYNTHETIC: one calculation ran", attribution_id="c")
    _receipt(g, "r1")
    _receipt(g, "r2", parents=("r1",))
    before = g.attributions
    result = inspect_claim_support(
        before, claim_id="c", supporting_ids=("r1", "r2"),
        proposed_relations={"r1": "SUPPORTS", "r2": "SUPPORTS"})
    assert result["reason_code"] == "SHARED_DECLARED_ANCESTRY"
    assert result["review_status"] == "UNKNOWN"
    assert result["claimed_support_count"] == 0
    assert g.attributions == before
    _check_firewall(result)


def test_transitive_receipt_derivation_is_shared_ancestry():
    """A -> intermediate -> B must not appear independent of A."""
    g = SourceMonitoringGuard()
    g.create_hypothesis("SYNTHETIC: checks passed", attribution_id="c")
    _receipt(g, "r1")
    _receipt(g, "middle", parents=("r1",))
    _receipt(g, "r3", parents=("middle",))
    result = inspect_claim_support(
        g.attributions, claim_id="c", supporting_ids=("r1", "r3"),
        proposed_relations={"r1": "SUPPORTS", "r3": "SUPPORTS"})
    assert result["reason_code"] == "SHARED_DECLARED_ANCESTRY"
    assert result["review_status"] == "UNKNOWN"
    _check_firewall(result)


def test_independent_declared_receipt_roots_keep_positive_control():
    """No recorded dependency is not proof of independence or truth."""
    g = SourceMonitoringGuard()
    g.create_hypothesis("SYNTHETIC: a result exists", attribution_id="c")
    _receipt(g, "r1")
    _receipt(g, "r2")
    result = inspect_claim_support(
        g.attributions, claim_id="c", supporting_ids=("r1", "r2"),
        proposed_relations={"r1": "SUPPORTS", "r2": "SUPPORTS"})
    assert result["review_status"] == "REVIEWABLE_ONLY"
    assert result["claimed_support_count"] == 2
    assert result["independent_support_count"] == 0
    _check_firewall(result)


@pytest.mark.parametrize(
    "bad_provenance",
    [
        pytest.param({}, id="dict"),
        pytest.param([], id="list"),
        pytest.param("UNTRUSTED_SYNTHETIC", id="string"),
    ],
)
def test_malformed_receipt_provenance_must_fail_closed(bad_provenance):
    """CodeRabbit finding: SourceAttribution dataclass permits non-None
    malformed provenance, so a read-only view MUST return UNKNOWN, not throw.
    """
    g = SourceMonitoringGuard()
    g.create_hypothesis("SYNTHETIC: tests ran", attribution_id="c")
    _receipt(g, "r")
    baseline = g.attributions
    supplied_snapshot = dict(baseline)
    supplied_snapshot["r"] = dataclasses.replace(
        baseline["r"], provenance=bad_provenance,
    )
    report = inspect_claim_support(
        supplied_snapshot, claim_id="c", supporting_ids=("r",),
        proposed_relations={"r": "SUPPORTS"},
    )
    assert report["review_status"] == "UNKNOWN"
    assert report["reason_code"] == "NO_ELIGIBLE_EXECUTION_RECEIPT"
    assert report["execution_integrity"] == "NOT_ASSESSED"
    assert g.attributions == baseline
    assert "UNTRUSTED_SYNTHETIC" not in str(report)
    _check_firewall(report)
