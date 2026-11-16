"""Regression tests for proposed numeric *reason-view* compatibility only.

Exactly the same synthetic immutable bytes feed existing historical observer,
current strict lab and the proposed integer-budget sidecar. No production
ingestion, external data, source authenticity or truth is asserted.
"""
import json

import pytest

import event_intake_validator_lab
import ledger_observation_adapter
from ario_same_snapshot_comparator import compare_snapshot
from numeric_resource_contract_lab import NumericResourceLimits
import numeric_reason_compatibility_view as view


def record(token: bytes, *, goal: str = "synthetic") -> bytes:
    return (
        b'{"event":"TASK_STARTED","timestamp":"t","task_id":"t","goal":'
        + json.dumps(goal).encode()
        + b',"meta":{"value":' + token + b'}}\n'
    )


def expect_safe(result):
    assert result["source_authenticity"] == "UNKNOWN"
    assert result["assessment"] == "NOT_ASSESSED"
    assert result["memory_mutation"] == "NONE"
    assert result["history_mutation"] == "NONE"
    assert result["contract_adoption"] == "NOT_ADOPTED"
    assert "snapshot_sha256" not in result
    assert "source_text" not in result


@pytest.mark.parametrize("digits", [4301, 4400])
def test_proposed_resource_reason_does_not_rewrite_existing_invalid_json(digits):
    raw = record(b"9" * digits)
    before = event_intake_validator_lab.inspect_jsonl_bytes(raw)
    existing_comparison = compare_snapshot(
        raw, legacy_observer_module=ledger_observation_adapter,
        strict_lab_module=event_intake_validator_lab,
    )
    result = view.compare_numeric_reason_views(raw)
    assert result["status"] == "DIAGNOSTIC_ONLY"
    assert result["relation"] == "PROPOSED_NUMERIC_RECLASSIFICATION"
    assert result["proposed_numeric_reason"] == "NUMERIC_RESOURCE_LIMIT"
    assert result["existing_strict_lab_reason"] == "INVALID_JSON"
    assert result["historical_comparison"] == existing_comparison["comparison"]
    assert event_intake_validator_lab.inspect_jsonl_bytes(raw) == before
    expect_safe(result)


@pytest.mark.parametrize("digits", [20, 4300])
def test_valid_historical_agreement_remains_separate(digits):
    raw = record(b"9" * digits)
    result = view.compare_numeric_reason_views(raw)
    assert result["status"] == "DIAGNOSTIC_ONLY"
    assert result["historical_comparison"] == "AGREE_OBSERVED"
    assert result["relation"] == "NO_NUMERIC_LIMIT_OBSERVED"
    assert result["proposed_numeric_reason"] is None
    expect_safe(result)


def test_explicit_lower_future_cap_is_not_a_retroactive_invalidation():
    raw = record(b"9" * 21)
    old_before = event_intake_validator_lab.inspect_jsonl_bytes(raw)
    report = view.compare_numeric_reason_views(
        raw, limits=NumericResourceLimits(max_integer_digits=20),
    )
    assert report["status"] == "DIAGNOSTIC_ONLY"
    assert report["historical_comparison"] == "AGREE_OBSERVED"
    assert report["relation"] == "PROPOSED_LOWER_NUMERIC_LIMIT"
    assert report["proposed_numeric_reason"] == "NUMERIC_RESOURCE_LIMIT"
    assert event_intake_validator_lab.inspect_jsonl_bytes(raw) == old_before
    expect_safe(report)


def test_nested_integer_exceeding_limit_is_only_diagnostic():
    raw = record(b'{"items":[' + b"9" * 4301 + b"]}")
    result = view.compare_numeric_reason_views(raw)
    assert result["relation"] == "PROPOSED_NUMERIC_RECLASSIFICATION"
    assert result["proposed_numeric_reason"] == "NUMERIC_RESOURCE_LIMIT"
    expect_safe(result)


def test_digit_string_is_not_a_numeric_token():
    raw = record(b'"' + b"9" * 4301 + b'"')
    result = view.compare_numeric_reason_views(raw)
    assert result["historical_comparison"] == "AGREE_OBSERVED"
    assert result["relation"] == "NO_NUMERIC_LIMIT_OBSERVED"
    expect_safe(result)


@pytest.mark.parametrize("token", [b"NaN", b"Infinity", b"1e999"])
def test_nonfinite_and_float_overflow_are_not_integer_reclassifications(token):
    result = view.compare_numeric_reason_views(record(token))
    assert result["status"] == "UNKNOWN_COMPARISON"
    assert result["reason_code"] == "NO_NUMERIC_DECISION"
    assert result["proposed_numeric_reason"] is None
    expect_safe(result)


def test_invalid_suffix_cannot_launder_valid_numeric_resource_diagnosis():
    raw = record(b"9" * 4301) + b'{"event":,}\n'
    result = view.compare_numeric_reason_views(raw)
    assert result["status"] == "UNKNOWN_COMPARISON"
    assert result["reason_code"] == "NO_NUMERIC_DECISION"
    assert result["proposed_numeric_reason"] is None
    expect_safe(result)


def test_missing_lf_cannot_become_numeric_reclassification():
    result = view.compare_numeric_reason_views(record(b"9" * 4301)[:-1])
    assert result["status"] == "UNKNOWN_COMPARISON"
    assert result["reason_code"] == "NO_NUMERIC_DECISION"
    expect_safe(result)


def test_private_goal_is_never_echoed_in_compatibility_report():
    marker = "NEVER-ECHO-THIS-PRIVATE-SYNTHETIC-GOAL"
    raw = record(b"9" * 4301, goal=marker)
    result = view.compare_numeric_reason_views(raw)
    assert marker not in json.dumps(result)
    expect_safe(result)


def test_above_total_snapshot_budget_is_blocked_before_comparison(monkeypatch):
    def forbidden(*_a, **_k):
        raise AssertionError("parser should not be called")
    monkeypatch.setattr(view, "compare_snapshot", forbidden)
    monkeypatch.setattr(view, "diagnose_numeric_resource_bytes", forbidden)
    result = view.compare_numeric_reason_views(b"x" * (8 * 1024 * 1024 + 1))
    assert result["status"] == "UNKNOWN_COMPARISON"
    assert result["reason_code"] == "SNAPSHOT_SIZE_LIMIT"
    expect_safe(result)


def test_empty_source_stays_unknown_without_parser_calls():
    report = view.compare_numeric_reason_views(b"")
    assert report["reason_code"] == "EMPTY_SNAPSHOT"
    assert report["proposed_numeric_reason"] is None
    expect_safe(report)


@pytest.mark.parametrize("payload", ["str", bytearray(b"a"), 7, None])
def test_only_immutable_bytes_are_accepted(payload):
    with pytest.raises(TypeError):
        view.compare_numeric_reason_views(payload)


def test_invalid_limits_instance_refused():
    with pytest.raises(TypeError):
        view.compare_numeric_reason_views(b"a\n", limits=object())


def test_inconsistent_source_reports_fail_closed_without_echo(monkeypatch):
    def mismatched(*args, **kwargs):
        return {
            "status": "UNKNOWN", "reason_code": "NUMERIC_RESOURCE_LIMIT",
            "existing_lab_status": "OBSERVED", "existing_lab_reason": None,
            "resource_records": 1,
        }
    monkeypatch.setattr(view, "diagnose_numeric_resource_bytes", mismatched)
    result = view.compare_numeric_reason_views(record(b"9" * 4301))
    assert result["status"] == "UNKNOWN_COMPARISON"
    assert result["reason_code"] == "VERSION_REPORT_MISMATCH"
    assert result["proposed_numeric_reason"] is None
    expect_safe(result)


def test_exception_message_with_private_text_never_leaks(monkeypatch):
    def bad(*_a, **_k):
        raise ValueError("PRIVATE SOURCE CONTENT")
    monkeypatch.setattr(view, "diagnose_numeric_resource_bytes", bad)
    result = view.compare_numeric_reason_views(record(b"9" * 4301))
    assert result["reason_code"] == "COMPARISON_EXECUTION_ERROR"
    assert "PRIVATE SOURCE CONTENT" not in json.dumps(result)
    expect_safe(result)


def test_stacked_versioned_view_does_not_mutate_existing_module_functions():
    original_lab = event_intake_validator_lab.inspect_jsonl_bytes
    original_legacy = ledger_observation_adapter.observe_ledger
    original_comparator = compare_snapshot
    view.compare_numeric_reason_views(record(b"9" * 4301))
    assert event_intake_validator_lab.inspect_jsonl_bytes is original_lab
    assert ledger_observation_adapter.observe_ledger is original_legacy
    assert compare_snapshot is original_comparator
