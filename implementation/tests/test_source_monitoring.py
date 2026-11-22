"""Tests for Ario Metacognitive Source Monitoring Guard.

Tests the core invariants from Issue #209:
- T-SRC-01: Anti-Self-Citation & Inviolable Reality Monitoring Gating
- T-SRC-02: Tool Binding Integrity & Execution Lock Checksum Verification
- Working Memory Gating & Circular Dependency Protection
- Serialization / Contract Conformance (SourceAttributionV1)
"""

import hashlib
import json
import pytest
from core.source_monitoring import (
    AttributionMismatchError,
    EmpiricalProvenance,
    SelfCitationError,
    SourceAttribution,
    SourceMonitoringError,
    SourceMonitoringGuard,
    SourceType,
    VeracityState,
)


def _make_dummy_hash(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def test_t_src_01_anti_self_citation():
    """T-SRC-01: A claim citing only internal hypotheses or itself cannot promote to verified evidence."""
    guard = SourceMonitoringGuard()

    # Step 1: Create an internal planner hypothesis
    hyp1 = guard.create_hypothesis(
        assertion="Planner model claims loopback socket is secure without test",
        attribution_id="ATTR-HYP-001",
    )
    assert hyp1.veracity_state == VeracityState.UNVERIFIED_HYPOTHESIS

    # Direct self-citation must fail closed
    with pytest.raises(SelfCitationError, match="Self-citation detected"):
        guard.evaluate_claim_promotion(claim_id="ATTR-HYP-001", supporting_ids=["ATTR-HYP-001"])

    # Step 2: Create a second hypothesis and try to promote hyp1 citing only hyp2
    hyp2 = guard.create_hypothesis(
        assertion="Second unverified thought assuming loopback is safe",
        attribution_id="ATTR-HYP-002",
    )
    with pytest.raises(SelfCitationError, match="Anti-Self-Citation"):
        guard.evaluate_claim_promotion(claim_id="ATTR-HYP-001", supporting_ids=["ATTR-HYP-002"])

    # Claim status must transition to UNSUPPORTED
    assert guard.attributions["ATTR-HYP-001"].veracity_state == VeracityState.UNSUPPORTED


def test_t_src_01_circular_citation_loop():
    """T-SRC-01: Mutual or circular citation loops between hypotheses are detected and rejected."""
    guard = SourceMonitoringGuard()

    hA = guard.create_hypothesis("Hypothesis A", attribution_id="HYP-A")
    hB = guard.create_hypothesis("Hypothesis B", attribution_id="HYP-B", parent_attribution_ids=["HYP-A"])

    # Attempting to make A cite B creates a loop A -> B -> A
    with pytest.raises(SelfCitationError, match="Circular citation loop detected"):
        guard.evaluate_claim_promotion(claim_id="HYP-A", supporting_ids=["HYP-B"])


def test_t_src_02_tool_binding_integrity():
    """T-SRC-02: Empirical observation with mismatched execution lock or stdout hash is rejected."""
    guard = SourceMonitoringGuard()

    valid_lock = "lock-secret-session-abc"
    expected_lock_hash = _make_dummy_hash(valid_lock)
    tampered_lock = "tampered-lock-session-xyz"

    # Mismatch in execution lock hash
    with pytest.raises(AttributionMismatchError, match="T-SRC-02: execution lock mismatch"):
        guard.record_empirical_observation(
            assertion="Unit tests passed on Windows",
            tool="run_tests",
            target="implementation/tests/test_planner_transport.py",
            exit_code=0,
            stdout="1141 passed in 1.2s",
            execution_lock=tampered_lock,
            expected_execution_lock_sha256=expected_lock_hash,
        )

    # Mismatch in stdout checksum
    expected_stdout_hash = _make_dummy_hash("authentic stdout output")
    with pytest.raises(AttributionMismatchError, match="T-SRC-02: stdout hash mismatch"):
        guard.record_empirical_observation(
            assertion="Compiler exited cleanly",
            tool="compile_python",
            target="implementation/ario_planner.py",
            exit_code=0,
            stdout="forged stdout output",
            execution_lock=valid_lock,
            expected_stdout_sha256=expected_stdout_hash,
        )


def test_valid_empirical_promotion():
    """Empirical observation backed by verified execution lock promotes hypothesis to verified state."""
    guard = SourceMonitoringGuard()

    hyp = guard.create_hypothesis(
        assertion="tool_exit:run_tests:implementation/tests/test_planner_transport.py:0",
        attribution_id="ATTR-HYP-BIND",
    )

    lock_data = "ci-execution-lock-run-842"
    lock_hash = _make_dummy_hash(lock_data)
    stdout_content = "1141 passed in 1.4s"
    stdout_hash = _make_dummy_hash(stdout_content)

    obs = guard.record_empirical_observation(
        assertion="tool_exit:run_tests:implementation/tests/test_planner_transport.py:0",
        tool="run_tests",
        target="implementation/tests/test_planner_transport.py",
        exit_code=0,
        stdout=stdout_content,
        execution_lock=lock_data,
        expected_execution_lock_sha256=lock_hash,
        expected_stdout_sha256=stdout_hash,
        attribution_id="ATTR-EMP-001",
    )
    assert obs.veracity_state == VeracityState.VERIFIED_EMPIRICAL

    # Now promote hypothesis citing the empirical observation
    promoted = guard.evaluate_claim_promotion(
        claim_id=hyp.attribution_id,
        supporting_ids=[obs.attribution_id],
    )
    assert promoted.veracity_state == VeracityState.VERIFIED_EMPIRICAL
    assert obs.attribution_id in promoted.parent_attribution_ids


def test_non_allowlisted_tool_rejected():
    """Arbitrary / non-allowlisted tool execution cannot forge empirical observation."""
    guard = SourceMonitoringGuard()
    with pytest.raises(SourceMonitoringError, match="not allowlisted"):
        guard.record_empirical_observation(
            assertion="Untrusted tool ran arbitrary script",
            tool="malicious_eval_script",
            target="system.sh",
            exit_code=0,
            stdout="done",
            execution_lock="lock",
        )


def test_working_memory_gating():
    """Working memory injection filters out unverified or mismatched records."""
    guard = SourceMonitoringGuard()

    hyp = guard.create_hypothesis("Speculative planner idea", attribution_id="ATTR-1")
    ext = guard.create_external_testimony("User claims server is down", attribution_id="ATTR-2")

    lock_data = "lock-valid-123"
    obs = guard.record_empirical_observation(
        assertion="tool_exit:inspect_directory:.:0",
        tool="inspect_directory",
        target=".",
        exit_code=0,
        stdout="valid",
        execution_lock=lock_data,
        attribution_id="ATTR-3",
    )

    # When verified is not strictly required, valid unverified hypotheses can be examined
    all_candidates = guard.filter_working_memory_candidates(["ATTR-1", "ATTR-2", "ATTR-3"], require_verified=False)
    assert len(all_candidates) == 3

    # When require_verified=True, only EMPIRICALLY verified items survive
    verified_only = guard.filter_working_memory_candidates(["ATTR-1", "ATTR-2", "ATTR-3"], require_verified=True)
    assert len(verified_only) == 1
    assert verified_only[0].attribution_id == "ATTR-3"


def test_schema_contract_serialization():
    """SourceAttribution and EmpiricalProvenance serialize and deserialize losslessly."""
    lock_hash = _make_dummy_hash("lock-123")
    stdout_hash = _make_dummy_hash("stdout-123")

    prov = EmpiricalProvenance(
        tool="compile_python",
        target="implementation/ario_planner.py",
        exit_code=0,
        execution_lock_sha256=lock_hash,
        stdout_sha256=stdout_hash,
        recorded_at="2026-11-16T12:00:00Z",
    )

    attr = SourceAttribution(
        attribution_id="ATTR-EMP-TEST",
        source_type=SourceType.EMPIRICAL_OBSERVATION,
        assertion="Compiler check succeeded",
        veracity_state=VeracityState.VERIFIED_EMPIRICAL,
        provenance=prov,
        falsification_condition="Any SyntaxError on compilation",
    )

    d = attr.to_dict()
    assert d["source_type"] == "EMPIRICAL_OBSERVATION"
    assert d["veracity_state"] == "VERIFIED_EMPIRICAL"
    assert d["provenance"]["tool"] == "compile_python"
    assert d["provenance"]["execution_lock_sha256"] == lock_hash

    restored = SourceAttribution.from_dict(d)
    assert restored == attr
