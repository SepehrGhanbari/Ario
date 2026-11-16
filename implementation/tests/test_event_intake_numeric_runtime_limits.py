"""Bounded, runtime-aware characterization of unadopted JSONL intake limits.

Only synthetic records are inspected. This is NOT an approved JSON-number
standard, a lossless numeric parser, or a CPU/memory denial-of-service proof.
"""

import sys

import pytest

from event_intake_validator_lab import IntakeLimits, inspect_jsonl_bytes


def _event_with_value(value_token: bytes) -> bytes:
    assert isinstance(value_token, bytes)
    return (
        b'{"event":"TASK_STARTED","timestamp":"t","task_id":"T",'
        b'"goal":"synthetic-only","meta":{"value":'
        + value_token
        + b'}}\n'
    )


@pytest.mark.parametrize("digits", [100, 1000, 4200, 4300, 4301])
def test_integer_length_is_runtime_dependent_not_syntax_validation(digits):
    """Characterize CPython's configurable integer-string conversion ceiling."""
    raw = _event_with_value(b"9" * digits)
    assert len(raw) < 64 * 1024
    observed = inspect_jsonl_bytes(raw)
    limit_getter = getattr(sys, "get_int_max_str_digits", None)
    limit = limit_getter() if callable(limit_getter) else 0

    if limit and digits > limit:
        assert observed["status"] == "UNKNOWN"
        assert observed["reason_code"] == "INVALID_JSON"
        assert observed["eligible_records"] == 0
    else:
        assert observed["status"] == "OBSERVED"
        assert observed["reason_code"] is None
        assert observed["eligible_records"] == 1

    assert observed["source_authenticity"] == "UNKNOWN"
    assert observed["assessment"] == "NOT_ASSESSED"
    assert observed["memory_mutation"] == "NONE"


@pytest.mark.parametrize("depth", [10, 100, 300, 600])
def test_bounded_nested_arrays_remain_structurally_eligible(depth):
    """Small research characterization, not an arbitrary-depth guarantee."""
    raw = _event_with_value(b"[" * depth + b"0" + b"]" * depth)
    assert len(raw) < 4096
    result = inspect_jsonl_bytes(raw)
    assert result["status"] == "OBSERVED"
    assert result["eligible_records"] == 1
    assert result["assessment"] == "NOT_ASSESSED"
    assert result["memory_mutation"] == "NONE"


def test_raw_line_limit_takes_precedence_over_numeric_conversions():
    raw = _event_with_value(b"9" * 4301)
    result = inspect_jsonl_bytes(
        raw, limits=IntakeLimits(max_line_bytes=256)
    )
    assert result["status"] == "UNKNOWN"
    assert result["reason_code"] == "LINE_SIZE_LIMIT"
    assert result["eligible_records"] == 0


@pytest.mark.parametrize("numeric", [b"1e-9999", b"-1e-9999", b"9007199254740993.0"])
def test_finite_conversion_is_not_lossless_numeric_certification(numeric):
    """The lab currently tests structure, not exact decimal value retention."""
    result = inspect_jsonl_bytes(_event_with_value(numeric))
    assert result["status"] == "OBSERVED"
    assert result["source_authenticity"] == "UNKNOWN"
    assert result["assessment"] == "NOT_ASSESSED"
    assert result["memory_mutation"] == "NONE"
    assert "value" not in result
