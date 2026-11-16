"""Synthetic, exact-source checks for a NOT ADOPTED numeric sidecar.

The previous intake lab and legacy observer must stay byte-for-byte unchanged.
No test replays a real/private ledger or mutates memory.
"""
import hashlib
import sys

import pytest

import event_intake_validator_lab as old_lab
import ledger_observation_adapter as old_observer
from ario_same_snapshot_comparator import compare_snapshot
from numeric_resource_contract_lab import (
    CONTRACT_VERSION,
    NumericResourceLimits,
    diagnose_numeric_resource_bytes,
)


def _record(token: bytes, key: bytes = b"n") -> bytes:
    return (b'{"event":"TASK_STARTED","timestamp":"t",'
            b'"task_id":"t","goal":"synthetic","meta":{"'
            + key + b'":' + token + b'}}\n')


def _safe(report):
    assert report["contract_version"] == CONTRACT_VERSION
    assert report["source_authenticity"] == "UNKNOWN"
    assert report["assessment"] == "NOT_ASSESSED"
    assert report["memory_mutation"] == "NONE"
    assert report["history_mutation"] == "NONE"
    assert "source_content" not in report


@pytest.mark.parametrize("digits", [4301, 4400])
def test_valid_json_integer_over_runtime_ceiling_is_versioned_resource(digits):
    raw = _record(b"9" * digits)
    digest = hashlib.sha256(raw).hexdigest()
    baseline = old_lab.inspect_jsonl_bytes(raw)
    versioned = diagnose_numeric_resource_bytes(raw)
    assert baseline["status"] == "UNKNOWN"
    assert baseline["reason_code"] == "INVALID_JSON"  # existing, unchanged
    assert versioned["status"] == "UNKNOWN"
    assert versioned["reason_code"] == "NUMERIC_RESOURCE_LIMIT"
    assert versioned["legacy_lab_reason"] == "INVALID_JSON"
    assert versioned["resource_records"] == 1
    assert hashlib.sha256(raw).hexdigest() == digest
    _safe(versioned)


@pytest.mark.parametrize("digits", [1, 20, 100, 4200, 4300])
def test_valid_integers_at_or_below_cap_are_not_reclassified(digits):
    raw = _record(b"9" * digits)
    result = diagnose_numeric_resource_bytes(raw)
    assert result["status"] == "NO_NUMERIC_RESOURCE_OBSERVED"
    assert result["reason_code"] is None
    assert result["legacy_lab_status"] == "OBSERVED"
    _safe(result)


@pytest.mark.parametrize("token", [b"-999999999999999999999", b"123456789012345678901"])
def test_explicit_new_policy_can_be_lower_than_legacy_without_rewriting(token):
    raw = _record(token)
    before = old_lab.inspect_jsonl_bytes(raw)
    assert before["status"] == "OBSERVED"
    result = diagnose_numeric_resource_bytes(
        raw, limits=NumericResourceLimits(max_integer_digits=20))
    assert result["status"] == "UNKNOWN"
    assert result["reason_code"] == "NUMERIC_RESOURCE_LIMIT"
    assert result["legacy_lab_status"] == "OBSERVED"
    assert result["history_mutation"] == "NONE"
    assert old_lab.inspect_jsonl_bytes(raw) == before


def test_nested_oversized_integer_token_is_detected_without_exporting_value():
    raw = _record(b'{"items":[1,2,' + b"9" * 4301 + b"]}")
    report = diagnose_numeric_resource_bytes(raw)
    assert report["reason_code"] == "NUMERIC_RESOURCE_LIMIT"
    assert report["records_examined"] == 1
    assert "items" not in str(report)
    _safe(report)


def test_large_digit_string_does_not_count_as_integer_token():
    raw = _record(b'"' + b"9" * 4301 + b'"')
    report = diagnose_numeric_resource_bytes(raw)
    assert report["status"] == "NO_NUMERIC_RESOURCE_OBSERVED"
    assert report["resource_records"] == 0
    _safe(report)


@pytest.mark.parametrize("bad_suffix", [
    b'} garbage\n',
    b'}\n',  # incorrectly closed object, invalid JSON when joined
])
def test_malformed_json_with_numeric_overflow_does_not_claim_valid_json(bad_suffix):
    raw = _record(b"9" * 4301)[:-3] + bad_suffix
    result = diagnose_numeric_resource_bytes(raw)
    assert result["status"] == "UNKNOWN"
    assert result["proposed_numeric_reason"] is None
    assert result["reason_code"] == "OTHER_INVALID_OR_UNSUPPORTED"
    _safe(result)


@pytest.mark.parametrize("value", [b"NaN", b"Infinity", b"1e999"])
def test_other_nonfinite_policies_not_mislabeled_as_integer_resource(value):
    raw = _record(value)
    result = diagnose_numeric_resource_bytes(raw)
    assert result["status"] == "UNKNOWN"
    assert result["reason_code"] == "OTHER_INVALID_OR_UNSUPPORTED"
    _safe(result)


def test_partial_batch_with_invalid_suffix_is_not_promoted_to_numeric_resource():
    raw = _record(b"9" * 4301) + b'{"event":"TASK_STARTED",BAD}\n'
    result = diagnose_numeric_resource_bytes(raw)
    assert result["status"] == "UNKNOWN"
    assert result["reason_code"] == "OTHER_INVALID_OR_UNSUPPORTED"
    assert result["resource_records"] == 0
    _safe(result)


def test_other_resource_preflight_precedes_numeric_token():
    raw = _record(b"9" * 4301)
    report = diagnose_numeric_resource_bytes(
        raw, limits=NumericResourceLimits(max_line_bytes=256))
    assert report["reason_code"] == "LINE_SIZE_LIMIT"
    assert report["proposed_numeric_reason"] is None
    _safe(report)


def test_missing_final_lf_not_reinterpreted_as_numeric_resource():
    raw = _record(b"9" * 4301)[:-1]
    report = diagnose_numeric_resource_bytes(raw)
    assert report["reason_code"] == "INCOMPLETE_JSONL_RECORD"
    assert report["resource_records"] == 0
    _safe(report)


def test_real_old_observer_and_research_lab_remain_unchanged_in_comparison():
    raw = _record(b"9" * 4301)
    baseline = compare_snapshot(
        raw, legacy_observer_module=old_observer, strict_lab_module=old_lab
    )
    assert baseline["comparison"] == "AGREE_UNKNOWN"
    assert baseline["memory_mutation"] == "NONE"
    proposed = diagnose_numeric_resource_bytes(raw)
    assert proposed["reason_code"] == "NUMERIC_RESOURCE_LIMIT"
    assert proposed["history_mutation"] == "NONE"
    _safe(proposed)


@pytest.mark.parametrize("param", [
    {"max_integer_digits": 0},
    {"max_integer_digits": True},
    {"max_integer_digits": 10001},
])
def test_invalid_policy_values_are_rejected(param):
    with pytest.raises(ValueError):
        NumericResourceLimits(**param)


@pytest.mark.parametrize("text_token", [b"1e-9999", b"9007199254740993.0"])
def test_lossy_finite_float_conversion_is_a_separate_contract(text_token):
    report = diagnose_numeric_resource_bytes(_record(text_token))
    assert report["status"] == "NO_NUMERIC_RESOURCE_OBSERVED"
    assert report["reason_code"] is None
    _safe(report)
