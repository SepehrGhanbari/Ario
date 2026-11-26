"""Independent review regressions for unverified ledger source identity under defensive-copy registry semantics.

Historical RED against #267 initial implementation; preserve this test-first
commit in append-only Git history. All strings/hashes are synthetic.
"""
import pytest

from core.source_monitoring import (
    SelfCitationError, SourceMonitoringError, SourceMonitoringGuard,
    SourceType, VeracityState,
)


def test_identical_report_replay_preserves_initial_registration_value_and_time():
    guard = SourceMonitoringGuard()
    first = guard.record_unverified_ledger_report(
        assertion="synthetic repeated ledger status", record_sha256="a" * 64,
    )
    first_time = first.created_at
    second = guard.record_unverified_ledger_report(
        assertion="synthetic repeated ledger status", record_sha256="a" * 64,
    )
    # The guard deliberately returns defensive copies. Replays must keep
    # the same registered value/time and must not append a false revision.
    assert second == first
    assert second.created_at == first_time
    assert guard.attributions[first.attribution_id] == first
    assert len(guard.attribution_history(first.attribution_id)) == 1
    assert first.veracity_state == VeracityState.REPORTED_UNVERIFIED


def test_ledger_report_claim_is_rejected_before_any_lineage_mutation():
    guard = SourceMonitoringGuard()
    parent = guard.create_hypothesis(
        assertion="synthetic unverified hypothesis", attribution_id="parent",
    )
    report = guard.record_unverified_ledger_report(
        assertion="synthetic replayed completion report", record_sha256="b" * 64,
    )
    assert report.parent_attribution_ids == ()
    before = dict(guard.attributions)
    # The current code can insert a temp parent before a failing dataclass
    # replacement. The rejection must not leave a stale lineage edge.
    with pytest.raises(SourceMonitoringError):
        guard.evaluate_claim_promotion(report.attribution_id, [parent.attribution_id])
    assert guard.attributions == before
    assert guard.attributions[report.attribution_id] == report
    assert len(guard.attribution_history(report.attribution_id)) == 1


def test_ledger_report_cannot_be_made_empirical_even_with_direct_verified_support():
    guard = SourceMonitoringGuard()
    report = guard.record_unverified_ledger_report(
        assertion="synthetic replayed completion", record_sha256="c" * 64,
    )
    direct = guard.record_empirical_observation(
        assertion="tool_exit:run_tests:synthetic/example.py:0",
        tool="run_tests", target="synthetic/example.py",
        exit_code=0, stdout="ok", execution_lock="local-lock",
        attribution_id="synthetic-direct",
    )
    before = dict(guard.attributions)
    with pytest.raises(SourceMonitoringError):
        guard.evaluate_claim_promotion(report.attribution_id, [direct.attribution_id])
    assert guard.attributions == before
    assert guard.attributions[report.attribution_id] == report
    assert len(guard.attribution_history(report.attribution_id)) == 1


def test_hypothesis_still_cannot_promote_using_ledger_report_as_support():
    guard = SourceMonitoringGuard()
    hypothesis = guard.create_hypothesis(
        assertion="synthetic claim", attribution_id="synthetic-claim",
    )
    report = guard.record_unverified_ledger_report(
        assertion="synthetic untrusted evidence", record_sha256="d" * 64,
    )
    with pytest.raises(SelfCitationError):
        guard.evaluate_claim_promotion(hypothesis.attribution_id, [report.attribution_id])
    assert guard.attributions[hypothesis.attribution_id].veracity_state == VeracityState.UNSUPPORTED
    assert guard.attributions[report.attribution_id].source_type == SourceType.LEDGER_REPORT


def test_distinct_line_hashes_have_distinct_report_ids():
    guard = SourceMonitoringGuard()
    first = guard.record_unverified_ledger_report(
        assertion="synthetic report", record_sha256="1" * 64,
    )
    second = guard.record_unverified_ledger_report(
        assertion="synthetic report", record_sha256="2" * 64,
    )
    assert first.attribution_id != second.attribution_id
    assert len(guard.attributions) == 2
