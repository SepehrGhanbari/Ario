"""RED -> GREEN F3/F4 synthetic characterization for numeric reason sidecar.

F3: when both legacy nonnumeric resource and proposed numeric limits trigger,
do not hide the legacy resource gate behind generic semantic ambiguity.
F4: huge configured line limits must not overflow an index-sized Python int.
No historic parser, source, memory, or trust status is modified.
"""
import json

import pytest

from numeric_resource_contract_lab import (
    NumericResourceLimits,
    diagnose_numeric_resource_bytes,
)
from numeric_reason_compatibility_view import compare_numeric_reason_views


def _event(value: bytes = b"25", goal: bytes = b"synthetic") -> bytes:
    return (
        b'{"event":"TASK_STARTED","timestamp":"t","task_id":"T",'
        b'"goal":"' + goal + b'","meta":{"amount":' + value + b'}}\n'
    )


def _no_promotion(report):
    assert report["source_authenticity"] == "UNKNOWN"
    assert report["assessment"] == "NOT_ASSESSED"
    assert report["memory_mutation"] == "NONE"
    assert report["history_mutation"] == "NONE"
    assert report.get("proposed_numeric_reason") is None


@pytest.mark.xfail(strict=True, reason="F3 RED: mixed resource and numeric budget reports ambiguous reason")
@pytest.mark.parametrize("source,limits,old_reason", [
    (
        _event(b"9" * 21, goal=b"g" * 70000),
        NumericResourceLimits(max_line_bytes=100000, max_integer_digits=20),
        "LINE_SIZE_LIMIT",
    ),
    (
        _event(b"9" * 21) + _event() * 5000,
        NumericResourceLimits(max_records=6000, max_integer_digits=20),
        "EVENT_COUNT_LIMIT",
    ),
], ids=["mixed-legacy-line-and-new-integer", "mixed-legacy-count-and-new-integer"])
def test_f3_old_nonnumeric_resource_gate_has_precedence(source, limits, old_reason):
    report = compare_numeric_reason_views(source, limits=limits)
    assert report["status"] == "UNKNOWN_COMPARISON"
    assert report["reason_code"] == "OTHER_RESOURCE_BOUNDARY"
    assert report["relation"] == "UNKNOWN"
    assert report["existing_strict_lab_status"] == "UNKNOWN"
    assert report["existing_strict_lab_reason"] == old_reason
    assert report["contract_adoption"] == "NOT_ADOPTED"
    _no_promotion(report)


@pytest.mark.xfail(strict=True, reason="F4 RED: readline cannot convert 2**100 to index-sized integer")
@pytest.mark.parametrize("value,expected_status,expected_reason", [
    (b"25", "NO_NUMERIC_RESOURCE_OBSERVED", None),
    (b"9" * 4301, "UNKNOWN", "NUMERIC_RESOURCE_LIMIT"),
], ids=["ordinary-int", "oversized-int"])
def test_f4_huge_configured_line_limit_does_not_crash_direct_sidecar(
    value, expected_status, expected_reason,
):
    report = diagnose_numeric_resource_bytes(
        _event(value),
        limits=NumericResourceLimits(max_line_bytes=2**100),
    )
    assert report["status"] == expected_status
    assert report["reason_code"] == expected_reason
    assert report["source_authenticity"] == "UNKNOWN"
    assert report["assessment"] == "NOT_ASSESSED"
    assert report["memory_mutation"] == "NONE"
    assert report["history_mutation"] == "NONE"


def test_exact_configured_line_cap_still_accepts_complete_lf():
    source = _event()
    report = diagnose_numeric_resource_bytes(
        source, limits=NumericResourceLimits(max_line_bytes=len(source))
    )
    assert report["status"] == "NO_NUMERIC_RESOURCE_OBSERVED"
    assert report["existing_lab_status"] == "OBSERVED"
    assert report["memory_mutation"] == "NONE"


def test_one_byte_over_line_cap_refuses_before_old_parser(monkeypatch):
    source = _event()

    def forbidden(*_a, **_kw):
        raise AssertionError("Existing parser must not run before size preflight")

    import numeric_resource_contract_lab as module
    monkeypatch.setattr(module, "inspect_jsonl_bytes", forbidden)
    report = diagnose_numeric_resource_bytes(
        source,
        limits=NumericResourceLimits(max_line_bytes=len(source) - 1),
    )
    assert report["status"] == "UNKNOWN"
    assert report["reason_code"] == "LINE_SIZE_LIMIT"
    assert report["existing_lab_status"] == "NOT_CHECKED"
    assert report["history_mutation"] == "NONE"


def test_invalid_json_not_promoted_due_to_other_nested_numeric_limit():
    invalid = _event(b"9" * 4301) + b'{"event":,}\n'
    report = compare_numeric_reason_views(invalid)
    assert report["status"] == "UNKNOWN_COMPARISON"
    assert report["proposed_numeric_reason"] is None
    assert report["contract_adoption"] == "NOT_ADOPTED"
    _no_promotion(report)


def test_goal_string_is_not_echoed_in_mixed_diagnosis():
    marker = b"NEVER_ECHO_SYNTHETIC_PRIVATE_F3"
    report = compare_numeric_reason_views(
        _event(b"9" * 21, goal=marker + b"g" * 70000),
        limits=NumericResourceLimits(max_integer_digits=20, max_line_bytes=100000),
    )
    assert marker.decode() not in json.dumps(report)
    assert report["status"] == "UNKNOWN_COMPARISON"
    _no_promotion(report)
