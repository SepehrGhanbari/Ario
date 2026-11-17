"""Research-only RED characterization of claim-evidence semantic relevance.

Parent: draft PR #210, frozen exact head 07068bdfa36abb29a3ce8e927077df3ffe02b0cf.
This file ONLY creates synthetic in-process SourceMonitoringGuard objects. It never
uses credentials, real ledger bytes, external sources, production memory or signing.

The failed negative tests intentionally remain plain pytest assertions (not
xfail): red CI is evidence of the NOT-YET-IMPLEMENTED claim-support contract,
not a production security verification or a reason to merge this Draft PR.
"""
import hashlib

import pytest

from core.source_monitoring import (
    AttributionMismatchError,
    SourceMonitoringError,
    SourceMonitoringGuard,
    VeracityState,
)


def _register_successful_synthetic_tool(guard, *, assertion, identifier):
    stdout = "SYNTHETIC: 3 calculator test cases passed; no astronomy measured"
    lock = "SYNTHETIC-LOCK-ONLY"
    return guard.record_empirical_observation(
        assertion=assertion,
        tool="run_tests",
        target="synthetic/calculator_tests.py",
        exit_code=0,
        stdout=stdout,
        execution_lock=lock,
        expected_stdout_sha256=hashlib.sha256(stdout.encode()).hexdigest(),
        expected_execution_lock_sha256=hashlib.sha256(lock.encode()).hexdigest(),
        attribution_id=identifier,
    )


def _attempt_promotion(guard, claim_id, supporting_ids):
    # A controlled rejection is acceptable; the assertion below disallows
    # VERIFIED_EMPIRICAL after both successful and rejected attempts.
    try:
        guard.evaluate_claim_promotion(claim_id=claim_id, supporting_ids=supporting_ids)
    except SourceMonitoringError:
        pass
    return guard.attributions[claim_id]


def test_ce01_unrelated_successful_tool_receipt_cannot_verify_claim():
    """RED: calculator stdout must NOT verify a synthetic astronomy claim."""
    guard = SourceMonitoringGuard()
    claim = guard.create_hypothesis(
        assertion="SYNTHETIC CLAIM: the moon is made of cheese",
        attribution_id="CE01-HYP",
    )
    receipt = _register_successful_synthetic_tool(
        guard,
        assertion="SYNTHETIC OBSERVATION: calculator addition tests passed",
        identifier="CE01-EMP",
    )
    assert receipt.veracity_state is VeracityState.VERIFIED_EMPIRICAL
    after = _attempt_promotion(guard, claim.attribution_id, [receipt.attribution_id])
    assert after.veracity_state is not VeracityState.VERIFIED_EMPIRICAL, (
        "CE-01: unrelated successful tool execution was mistaken for "
        "semantic support of an unrelated claim"
    )


def test_ce03_contradicting_tool_text_cannot_verify_claim():
    """RED: successful exit status cannot prove an opposite statement."""
    guard = SourceMonitoringGuard()
    claim = guard.create_hypothesis(
        assertion="SYNTHETIC CLAIM: the calculator tests report zero failures",
        attribution_id="CE03-HYP",
    )
    receipt = _register_successful_synthetic_tool(
        guard,
        assertion="SYNTHETIC OBSERVATION: calculator tests report failures",
        identifier="CE03-EMP",
    )
    after = _attempt_promotion(guard, claim.attribution_id, [receipt.attribution_id])
    assert after.veracity_state is not VeracityState.VERIFIED_EMPIRICAL, (
        "CE-03: a successful tool receipt with an opposing assertion "
        "was treated as substantive support"
    )


def test_ce04_duplicate_receipt_id_is_not_two_distinct_sources():
    """RED: repeated references to one receipt must be unique in lineage."""
    guard = SourceMonitoringGuard()
    claim = guard.create_hypothesis(
        assertion="SYNTHETIC CLAIM: calculator tests were run",
        attribution_id="CE04-HYP",
    )
    receipt = _register_successful_synthetic_tool(
        guard,
        assertion="SYNTHETIC OBSERVATION: calculator tests were run",
        identifier="CE04-EMP",
    )
    after = guard.evaluate_claim_promotion(
        claim_id=claim.attribution_id,
        supporting_ids=[receipt.attribution_id, receipt.attribution_id],
    )
    assert after.parent_attribution_ids.count(receipt.attribution_id) == 1, (
        "CE-04: repeated identical receipt ID persisted as duplicate lineage edges"
    )


def test_existing_positive_structural_receipt_path_is_still_observable():
    """Positive baseline only: same-topic provenance currently can promote.

    A passing result here DOES NOT demonstrate semantic entailment.
    """
    guard = SourceMonitoringGuard()
    claim = guard.create_hypothesis(
        assertion="SYNTHETIC: calculator tests executed",
        attribution_id="BASELINE-HYP",
    )
    receipt = _register_successful_synthetic_tool(
        guard,
        assertion="SYNTHETIC: calculator tests executed",
        identifier="BASELINE-EMP",
    )
    after = guard.evaluate_claim_promotion(
        claim_id=claim.attribution_id, supporting_ids=[receipt.attribution_id]
    )
    assert after.veracity_state is VeracityState.VERIFIED_EMPIRICAL
    assert receipt.attribution_id in after.parent_attribution_ids


def test_existing_checksum_mismatch_is_rejected():
    """Positive control: wrong expected tool digest still fails closed."""
    guard = SourceMonitoringGuard()
    with pytest.raises(AttributionMismatchError):
        guard.record_empirical_observation(
            assertion="SYNTHETIC: calculator tests ran",
            tool="run_tests",
            target="synthetic/calculator_tests.py",
            exit_code=0,
            stdout="not the expected text",
            execution_lock="synthetic-lock",
            expected_stdout_sha256="0" * 64,
            attribution_id="BAD-DIGEST",
        )
    assert guard.attributions["BAD-DIGEST"].veracity_state is VeracityState.ATTRIBUTION_MISMATCH
