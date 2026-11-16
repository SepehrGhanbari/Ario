"""Candidate RED controls for the unadopted Ario strict JSONL intake lab.

The first three probes are strict XFAIL until the separate parser change.
Only synthetic JSONL is used. No memory, evidence, source data or keys changed.
"""
import pytest
from event_intake_validator_lab import inspect_jsonl_bytes


def _synthetic_record(token: str) -> bytes:
    prefix = ('{"event":"TASK_STARTED","timestamp":"t","task_id":"T",'
              '"goal":"synthetic","meta":{"score":')
    return (prefix + token + '}}\n').encode("utf-8")


@pytest.mark.parametrize("number", ["1e999", "-1e999", "9.99e999"])
def test_numeric_float_overflow_must_not_be_eligible(number):
    result = inspect_jsonl_bytes(_synthetic_record(number))
    assert result["status"] == "UNKNOWN"
    assert result["reason_code"] in {"JSON_NONFINITE_CONSTANT", "JSON_NUMERIC_RANGE_EXCEEDED"}
    assert result["eligible_records"] == 0
    assert result["assessment"] == "NOT_ASSESSED"
    assert result["source_authenticity"] == "UNKNOWN"


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity"])
def test_nonstandard_nonfinite_constants_are_already_rejected(number):
    result = inspect_jsonl_bytes(_synthetic_record(number))
    assert result["status"] == "UNKNOWN"
    assert result["reason_code"] == "JSON_NONFINITE_CONSTANT"
    assert result["eligible_records"] == 0


@pytest.mark.parametrize("number", ["0.25", "1e308", "-1.5e-4"])
def test_finite_json_numeric_values_remain_structurally_eligible(number):
    result = inspect_jsonl_bytes(_synthetic_record(number))
    assert result["status"] == "OBSERVED"
    assert result["eligible_records"] == 1
    assert result["assessment"] == "NOT_ASSESSED"
    assert result["source_authenticity"] == "UNKNOWN"
    assert result["memory_mutation"] == "NONE"
