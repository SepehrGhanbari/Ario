"""Source-guard fail-closed configuration / primitive type boundary.

Test-first RED for two source-inspected issues at Ario Draft #267 head
ac5b1a7191b832d118afbced81a7b092fcdddc1f.

1. An explicitly supplied empty tool allowlist must deny every tool.
2. Python bool (False == 0) must never count as an integer exit_code=0.

Synthetic direct calls only; not a source-authentication solution.
"""
import pytest

from core.source_monitoring import (
    EmpiricalProvenance, SourceMonitoringError, SourceMonitoringGuard,
    VeracityState,
)


def _record(guard, *, tool="run_tests", exit_code=0):
    return guard.record_empirical_observation(
        assertion=f"tool_exit:{tool}:synthetic/do-not-execute:{exit_code}",
        tool=tool, target="synthetic/do-not-execute",
        exit_code=exit_code, stdout="synthetic", execution_lock="synthetic",
    )


def test_explicit_empty_allowlist_denies_even_default_tool():
    guard = SourceMonitoringGuard(allowlisted_tools=set())
    # RED under original implementation: empty set is falsy, so defaults are
    # silently reinstated. Do not let deny-all become allow-default.
    with pytest.raises(SourceMonitoringError):
        _record(guard, tool="run_tests")


def test_explicit_empty_frozenset_denies_default_tool():
    guard = SourceMonitoringGuard(allowlisted_tools=frozenset())
    with pytest.raises(SourceMonitoringError):
        _record(guard, tool="file_fingerprint")


def test_bool_false_exit_code_cannot_masquerade_as_zero_success():
    guard = SourceMonitoringGuard()
    # RED before strict type validation: False == 0, so this creates a
    # VERIFIED_EMPIRICAL attribution from a boolean, not an int.
    with pytest.raises(SourceMonitoringError):
        _record(guard, exit_code=False)


def test_bool_true_exit_code_cannot_masquerade_as_one_failure():
    guard = SourceMonitoringGuard()
    with pytest.raises(SourceMonitoringError):
        _record(guard, exit_code=True)


def test_empirical_provenance_rejects_bool_exit_code_at_constructor():
    with pytest.raises(SourceMonitoringError):
        EmpiricalProvenance(
            tool="run_tests", target="synthetic",
            exit_code=False, execution_lock_sha256="a" * 64,
            stdout_sha256="b" * 64, recorded_at="synthetic-time",
        )


def test_positive_explicit_allowlist_enables_only_its_tool():
    guard = SourceMonitoringGuard(allowlisted_tools={"run_tests"})
    good = _record(guard, tool="run_tests", exit_code=0)
    # Compatibility positive control only: this API still does not
    # authenticate who really executed a tool.
    assert good.veracity_state == VeracityState.VERIFIED_EMPIRICAL
    with pytest.raises(SourceMonitoringError):
        _record(guard, tool="file_fingerprint")


def test_positive_default_allowlist_retains_existing_behavior():
    guard = SourceMonitoringGuard()
    attr = _record(guard, tool="run_tests", exit_code=0)
    assert attr.veracity_state == VeracityState.VERIFIED_EMPIRICAL


def test_positive_integer_nonzero_exit_code_remains_unsupported():
    guard = SourceMonitoringGuard()
    attr = _record(guard, tool="run_tests", exit_code=1)
    assert attr.veracity_state == VeracityState.UNSUPPORTED


@pytest.mark.parametrize("invalid_exit", [False, True, "0", "1", 0.0, None])
def test_provenance_deserialization_rejects_noninteger_exit_codes(invalid_exit):
    data = {
        "tool": "run_tests", "target": "synthetic/not-run",
        "exit_code": invalid_exit,
        "execution_lock_sha256": "a" * 64,
        "stdout_sha256": "b" * 64,
        "recorded_at": "2026-11-17T00:00:00Z",
    }
    with pytest.raises(SourceMonitoringError):
        EmpiricalProvenance.from_dict(data)


def test_provenance_serialization_preserves_strict_integer_exit_code():
    prov = EmpiricalProvenance(
        tool="run_tests", target="synthetic",
        exit_code=0, execution_lock_sha256="a" * 64,
        stdout_sha256="b" * 64, recorded_at="synthetic-time",
    )
    restored = EmpiricalProvenance.from_dict(prov.to_dict())
    assert type(restored.exit_code) is int
    assert restored.to_dict() == prov.to_dict()
