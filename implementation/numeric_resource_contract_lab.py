"""Read-only, NOT ADOPTED numeric-resource diagnostic sidecar for Ario.

Classifies bounded JSONL snapshots without modifying existing observers,
the strict lab, historical manifests, semantic memory or trust state.
An oversized integer token is replaced by a local placeholder *only within*
a syntax-checking parse; no converted value or source text is exported.
"""
from __future__ import annotations

import io
import json
import math
import sys
from dataclasses import dataclass
from typing import Any

from event_intake_validator_lab import REQUIRED_FIELDS, inspect_jsonl_bytes

CONTRACT_VERSION = "ario_numeric_resource_diagnostic_v0_1"
PROPOSED_NUMERIC_REASON = "NUMERIC_RESOURCE_LIMIT"


@dataclass(frozen=True)
class NumericResourceLimits:
    max_integer_digits: int = 4300
    max_raw_bytes: int = 8 * 1024 * 1024
    max_line_bytes: int = 64 * 1024
    max_records: int = 5000

    def __post_init__(self) -> None:
        for name in (
            "max_integer_digits", "max_raw_bytes",
            "max_line_bytes", "max_records",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.max_integer_digits > 10000:
            raise ValueError("experimental maximum integer digit budget is 10000")


class _OtherInvalid(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _OtherInvalid("duplicate key")
        result[key] = value
    return result


def _reject_constant(_token: str) -> None:
    raise _OtherInvalid("nonstandard constant")


def _finite_float(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise _OtherInvalid("nonfinite float conversion")
    return value


def _diagnose_line(raw_line: bytes, limits: NumericResourceLimits) -> str:
    """Return a fixed token classification, without echoing raw input.

    A resource classification is emitted only if the entire line is otherwise
    syntactically valid and passes the lab's minimal *proposed* event envelope.
    This does not certify the original numeric value, claim or source.
    """
    over_limit = [False]
    runtime_getter = getattr(sys, "get_int_max_str_digits", None)
    runtime_limit = runtime_getter() if callable(runtime_getter) else 0

    def _bounded_int(token: str) -> int:
        digits = len(token) - (1 if token.startswith("-") else 0)
        if digits > limits.max_integer_digits or (runtime_limit and digits > runtime_limit):
            over_limit[0] = True
            return 0  # syntax-only placeholder; never persisted/exported
        try:
            return int(token)
        except ValueError:
            # json.loads gives this callback syntactically recognized integer
            # tokens. A configured Python conversion limit can still intervene.
            over_limit[0] = True
            return 0

    try:
        data = json.loads(
            raw_line.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
            parse_int=_bounded_int,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, _OtherInvalid,
            RecursionError, ValueError, OverflowError):
        return "OTHER_INVALID_OR_UNSUPPORTED"

    if type(data) is not dict:
        return "OTHER_INVALID_OR_UNSUPPORTED"
    kind = data.get("event")
    stamp = data.get("timestamp")
    if (type(kind) is not str or kind not in REQUIRED_FIELDS
            or type(stamp) is not str or not stamp.strip()):
        return "OTHER_INVALID_OR_UNSUPPORTED"
    for field in REQUIRED_FIELDS[kind]:
        value = data.get(field)
        if type(value) is not str or not value.strip():
            return "OTHER_INVALID_OR_UNSUPPORTED"
    return "NUMERIC_RESOURCE" if over_limit[0] else "NO_NUMERIC_RESOURCE"


def diagnose_numeric_resource_bytes(
    raw: bytes, *,
    limits: NumericResourceLimits = NumericResourceLimits(),
) -> dict[str, Any]:
    """Produce unprivileged metadata; never mutate or promote prior records."""
    if type(raw) is not bytes:
        raise TypeError("raw must be bytes")
    if not isinstance(limits, NumericResourceLimits):
        raise TypeError("limits must be NumericResourceLimits")

    result: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "status": "UNKNOWN",
        "reason_code": None,
        "proposed_numeric_reason": None,
        "legacy_lab_status": "NOT_CHECKED",
        "legacy_lab_reason": None,
        "source_authenticity": "UNKNOWN",
        "assessment": "NOT_ASSESSED",
        "memory_mutation": "NONE",
        "history_mutation": "NONE",
        "bytes_seen": len(raw),
        "records_examined": 0,
        "resource_records": 0,
    }
    if len(raw) > limits.max_raw_bytes:
        result["reason_code"] = "LEDGER_SIZE_LIMIT"
        return result
    if not raw:
        result["reason_code"] = "EMPTY_LEDGER"
        return result

    # The existing lab is consulted without altering it. Its interpretation
    # remains historical research behavior, not an accepted versioned policy.
    old_lab = inspect_jsonl_bytes(raw)
    result["legacy_lab_status"] = old_lab["status"]
    result["legacy_lab_reason"] = old_lab["reason_code"]

    stream = io.BytesIO(raw)
    while True:
        line = stream.readline(limits.max_line_bytes + 1)
        if not line:
            break
        result["records_examined"] += 1
        if result["records_examined"] > limits.max_records:
            result["reason_code"] = "EVENT_COUNT_LIMIT"
            return result
        if len(line) > limits.max_line_bytes:
            result["reason_code"] = "LINE_SIZE_LIMIT"
            return result
        if not line.endswith(b"\n"):
            result["reason_code"] = "INCOMPLETE_JSONL_RECORD"
            return result
        if not line.strip():
            result["reason_code"] = "EMPTY_JSONL_RECORD"
            return result

        outcome = _diagnose_line(line, limits)
        if outcome == "OTHER_INVALID_OR_UNSUPPORTED":
            # Do not label a malformed record "valid JSON exceeding budget"
            # merely because an earlier token happened to be too long.
            result["reason_code"] = "OTHER_INVALID_OR_UNSUPPORTED"
            result["resource_records"] = 0
            return result
        if outcome == "NUMERIC_RESOURCE":
            result["resource_records"] += 1

    if result["resource_records"]:
        result["reason_code"] = PROPOSED_NUMERIC_REASON
        result["proposed_numeric_reason"] = PROPOSED_NUMERIC_REASON
        # UNKNOWN is deliberately retained even when the resource boundary
        # can be characterized: nothing is eligible for memory or truth.
        return result

    result["status"] = "NO_NUMERIC_RESOURCE_OBSERVED"
    return result
