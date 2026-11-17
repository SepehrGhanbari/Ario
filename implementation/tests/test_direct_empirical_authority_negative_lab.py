"""Test-only RED probe: self-declared direct "empirical" data are not attested.

Source: Ario #267 exact commit ac5b1a7191b832d118afbced81a7b092fcdddc1f.
No real tool execution, signer, keys, trusted service or memory deployment.
Do not merge this intentionally RED research-only test into another branch.

Security hypothesis: an in-process caller WITHOUT independent execution
authorization must not gain VERIFIED_EMPIRICAL merely by providing successful
exit_code, stdout, execution_lock and an allowlisted tool name.
The current direct API has no execution-identity authentication. These are
negative characterization tests, not an exploit of a reachable production API.
"""
import pytest

from core.source_monitoring import (
    SourceMonitoringGuard, SelfCitationError, SourceType, VeracityState,
)


def _fabricated_empirical(guard, tmp_path):
    never_created = tmp_path / "tool-target-does-not-exist.txt"
    assert not never_created.exists()
    fake = guard.record_empirical_observation(
        assertion="Self-asserted successful fingerprint of an absent file",
        tool="file_fingerprint",
        target=str(never_created),
        exit_code=0,
        stdout='{"path":"never-created","sha256":"' + "0" * 64 + '"}',
        execution_lock="USER_SUPPLIED_LOCAL_STRING_NOT_EXECUTOR_ATTESTATION",
        attribution_id="synthetic-in-process-call",
    )
    assert not never_created.exists()
    return fake


def test_unattested_direct_empirical_call_is_not_verified(tmp_path):
    guard = SourceMonitoringGuard()
    result = _fabricated_empirical(guard, tmp_path)
    assert result.source_type == SourceType.EMPIRICAL_OBSERVATION
    # Desired safety property. EXPECTED RED: the current direct API returns
    # VERIFIED_EMPIRICAL from self-supplied strings and exit_code == 0.
    assert result.veracity_state != VeracityState.VERIFIED_EMPIRICAL


def test_unattested_direct_observation_cannot_promote_internal_hypothesis(tmp_path):
    guard = SourceMonitoringGuard()
    claim = guard.create_hypothesis(
        assertion="A real tool checked this target", attribution_id="synthetic-claim"
    )
    forged = _fabricated_empirical(guard, tmp_path)
    before = claim.veracity_state
    assert before == VeracityState.UNVERIFIED_HYPOTHESIS
    result = guard.evaluate_claim_promotion(claim.attribution_id, [forged.attribution_id])
    # Desired safety property. EXPECTED RED: a forged direct observation
    # currently permits promotion to VERIFIED_EMPIRICAL.
    assert result.veracity_state != VeracityState.VERIFIED_EMPIRICAL


def test_unattested_direct_observation_not_in_verified_only_context(tmp_path):
    guard = SourceMonitoringGuard()
    fabricated = _fabricated_empirical(guard, tmp_path)
    admitted = guard.filter_working_memory_candidates(
        [fabricated.attribution_id], require_verified=True
    )
    # Desired safety property. EXPECTED RED: the current filter checks the
    # same VERIFED_EMPIRICAL enum, not independently authenticated custody.
    assert admitted == []


def test_positive_control_unverified_hypothesis_alone_cannot_promote():
    guard = SourceMonitoringGuard()
    a = guard.create_hypothesis("Unverified claim A", attribution_id="a")
    b = guard.create_hypothesis("Unverified claim B", attribution_id="b")
    with pytest.raises(SelfCitationError):
        guard.evaluate_claim_promotion(a.attribution_id, [b.attribution_id])
    assert guard.attributions[a.attribution_id].veracity_state != VeracityState.VERIFIED_EMPIRICAL


def test_positive_control_external_testimony_alone_cannot_promote():
    guard = SourceMonitoringGuard()
    claim = guard.create_hypothesis("Unverified claim C", attribution_id="claim")
    testimony = guard.create_external_testimony("Synthetic witness, not verified", attribution_id="testimony")
    with pytest.raises(SelfCitationError):
        guard.evaluate_claim_promotion(claim.attribution_id, [testimony.attribution_id])
    assert guard.attributions[claim.attribution_id].veracity_state != VeracityState.VERIFIED_EMPIRICAL
