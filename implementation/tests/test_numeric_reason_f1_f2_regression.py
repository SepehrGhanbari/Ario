"""RED->GREEN adversarial regression for proposed numeric-resource F1/F2.

F1: proposed custom caps must be enforced BEFORE invoking the existing strict
lab. F2: a versioned compatibility view may not report generic diagnostic
success after a different resource ceiling rejects the same immutable bytes.
All fixtures are generated synthetically and carry no claim/evidence authority.
"""
import pytest

import numeric_resource_contract_lab as side
import numeric_reason_compatibility_view as view


def _record(goal: bytes = b"synthetic", numeric: bytes = b"25") -> bytes:
    return (b'{"event":"TASK_STARTED","timestamp":"t","task_id":"t",'
            b'"goal":"' + goal + b'","meta":{"n":' + numeric + b'}}\n')


def _check_epistemic_firewall(result):
    assert result["source_authenticity"] == "UNKNOWN"
    assert result["assessment"] == "NOT_ASSESSED"
    assert result["memory_mutation"] == "NONE"
    assert result["history_mutation"] == "NONE"


@pytest.mark.parametrize("raw,limit,reason", [
    (_record(), side.NumericResourceLimits(max_line_bytes=16), "LINE_SIZE_LIMIT"),
    (_record() * 2, side.NumericResourceLimits(max_records=1), "EVENT_COUNT_LIMIT"),
], ids=["custom-line-cap", "custom-record-count"])
def test_f1_preflight_prevents_strict_lab_invocation(monkeypatch, raw, limit, reason):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Strict parser executed before custom resource preflight")
    monkeypatch.setattr(side, "inspect_jsonl_bytes", forbidden)
    result = side.diagnose_numeric_resource_bytes(raw, limits=limit)
    assert result["status"] == "UNKNOWN"
    assert result["reason_code"] == reason
    assert result["existing_lab_status"] == "NOT_CHECKED"
    assert result["existing_lab_reason"] is None
    assert result["resource_records"] == 0
    _check_epistemic_firewall(result)


@pytest.mark.parametrize("raw,limit,prior_reason", [
    (_record(goal=b"x" * 70000), side.NumericResourceLimits(max_line_bytes=100000), "LINE_SIZE_LIMIT"),
    (_record() * 5001, side.NumericResourceLimits(max_records=6000), "EVENT_COUNT_LIMIT"),
], ids=["older-line-ceiling", "older-count-ceiling"])
def test_f2_wider_sidecar_never_mislabels_strict_resource_unknown(raw, limit, prior_reason):
    result = view.compare_numeric_reason_views(raw, limits=limit)
    assert result["status"] == "UNKNOWN_COMPARISON"
    assert result["relation"] == "UNKNOWN"
    assert result["reason_code"] == "OTHER_RESOURCE_BOUNDARY"
    assert result["existing_strict_lab_status"] == "UNKNOWN"
    assert result["existing_strict_lab_reason"] == prior_reason
    assert result["proposed_numeric_reason"] is None
    _check_epistemic_firewall(result)


@pytest.mark.parametrize("raw,limit", [
    (_record(), side.NumericResourceLimits(max_line_bytes=16)),
    (_record() * 2, side.NumericResourceLimits(max_records=1)),
], ids=["tighter-line-cap", "tighter-event-cap"])
def test_f2_tighter_sidecar_does_not_invoke_old_comparator(monkeypatch, raw, limit):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Old comparator must not execute on over-budget bytes")
    monkeypatch.setattr(view, "compare_snapshot", forbidden)
    result = view.compare_numeric_reason_views(raw, limits=limit)
    assert result["status"] == "UNKNOWN_COMPARISON"
    assert result["relation"] == "UNKNOWN"
    assert result["reason_code"] == "OTHER_RESOURCE_BOUNDARY"
    assert result["historical_comparison"] is None
    assert result["proposed_numeric_reason"] is None
    _check_epistemic_firewall(result)


def test_normal_source_remains_diagnostic_only_and_not_adopted():
    result = view.compare_numeric_reason_views(_record())
    assert result["status"] == "DIAGNOSTIC_ONLY"
    assert result["relation"] == "NO_NUMERIC_LIMIT_OBSERVED"
    assert result["contract_adoption"] == "NOT_ADOPTED"
    _check_epistemic_firewall(result)


def test_4301_digit_integer_retains_proposed_separate_reason():
    result = view.compare_numeric_reason_views(_record(numeric=b"9" * 4301))
    assert result["status"] == "DIAGNOSTIC_ONLY"
    assert result["relation"] == "PROPOSED_NUMERIC_RECLASSIFICATION"
    assert result["existing_strict_lab_status"] == "UNKNOWN"
    assert result["existing_strict_lab_reason"] == "INVALID_JSON"
    assert result["proposed_numeric_reason"] == "NUMERIC_RESOURCE_LIMIT"
    _check_epistemic_firewall(result)


def test_malformed_suffix_remains_unknown_not_numeric_reclassification():
    result = view.compare_numeric_reason_views(_record(numeric=b"9" * 4301) + b'{"bad":,}\n')
    assert result["status"] == "UNKNOWN_COMPARISON"
    assert result["reason_code"] == "NO_NUMERIC_DECISION"
    assert result["proposed_numeric_reason"] is None
    _check_epistemic_firewall(result)
