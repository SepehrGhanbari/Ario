"""Read-only experimental event intake preflight for Ario (#232).

This module does NOT replace the existing observer, change memory, authenticate
the producer, admit evidence, infer truth, or persist event/claim content.
Every positive outcome means only 'syntactically eligible under this PROPOSED
research contract'. Source authenticity and epistemic assessment stay UNKNOWN.
"""
from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "event_intake_research_v0_1"
RAW_LINE_DIGEST_SCHEME = "raw_line_sha256_v0_2"
EPISODIC_ASSESSMENT = "NOT_ASSESSED"

# Research defaults mirror the original observer's raw byte budgets.
# They are NOT approved shared production thresholds.
@dataclass(frozen=True)
class IntakeLimits:
    max_ledger_bytes: int = 8 * 1024 * 1024
    max_line_bytes: int = 64 * 1024
    max_events: int = 5000

    def __post_init__(self) -> None:
        for field in ("max_ledger_bytes", "max_line_bytes", "max_events"):
            value = getattr(self, field)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{field} must be a positive integer")


# Minimum fields follow CURRENT emitters, not claims of historical universality.
# Further nested validation, status enums and legacy migrations remain proposals.
REQUIRED_FIELDS = {
    "TASK_STARTED": ("task_id", "goal"),
    "STEP_OBSERVED": ("task_id", "step_id", "status"),
    "GOAL_CRITERION_OBSERVED": ("task_id", "criterion_id", "status"),
    "FAILURE_DIAGNOSTIC_OBSERVED": ("task_id", "step_id", "status"),
    "TASK_FINISHED": ("task_id", "status"),
    "WORKFLOW_STARTED": ("workflow_id", "goal"),
    "WORKFLOW_STAGE_OBSERVED": ("workflow_id", "stage_id", "status"),
    "WORKFLOW_FINISHED": ("workflow_id", "status"),
}


class _InvalidJSON(ValueError):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _InvalidJSON("JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _forbid_nonfinite(_token: str) -> Any:
    raise _InvalidJSON("JSON_NONFINITE_CONSTANT")


def _new_report(source_kind: str, raw_bytes: int | None = None) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "status": "UNKNOWN",
        "reason_code": None,
        "source_kind": source_kind,
        "source_authenticity": "UNKNOWN",
        "assessment": EPISODIC_ASSESSMENT,
        "memory_mutation": "NONE",
        "digest_scheme": RAW_LINE_DIGEST_SCHEME,
        "raw_bytes_observed": raw_bytes,
        "file_sha256": None,
        "records_checked": 0,
        "valid_envelopes": 0,
        "eligible_records": 0,
        "records": [],
    }


def _stop(report: dict[str, Any], reason: str) -> dict[str, Any]:
    report["status"] = "UNKNOWN"
    report["reason_code"] = reason
    # Never present a partially validated ledger as eligible or complete.
    report["eligible_records"] = 0
    report["file_sha256"] = None
    return report


def _parse_envelope(raw_line: bytes) -> tuple[str | None, str]:
    try:
        data = json.loads(
            raw_line.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_forbid_nonfinite,
        )
    except _InvalidJSON as exc:
        return None, exc.reason_code
    except UnicodeDecodeError:
        return None, "INVALID_UTF8"
    except (json.JSONDecodeError, RecursionError, ValueError):
        return None, "INVALID_JSON"
    if not isinstance(data, dict):
        return None, "NOT_JSON_OBJECT"

    kind = data.get("event")
    if not isinstance(kind, str):
        return None, "MISSING_EVENT_KIND"
    if kind not in REQUIRED_FIELDS:
        return None, "UNSUPPORTED_EVENT_KIND"

    stamp = data.get("timestamp")
    if not isinstance(stamp, str) or not stamp.strip():
        return kind, "MISSING_OR_INVALID_TIMESTAMP"

    for required in REQUIRED_FIELDS[kind]:
        field_value = data.get(required)
        if not isinstance(field_value, str) or not field_value.strip():
            return kind, f"MISSING_OR_INVALID_{required.upper()}"
    return kind, "VALID_ENVELOPE"


def inspect_jsonl_bytes(
    raw: bytes,
    *,
    limits: IntakeLimits = IntakeLimits(),
) -> dict[str, Any]:
    """Report only metadata from a caller-provided bounded JSONL snapshot.

    No bytes are persisted. Per-event VALID_ENVELOPE does not mean memory
    RECORDED, evidence ADMITTED, assessment SUPPORTED or source-authenticity.
    A malformed/truncated/over-budget batch returns UNKNOWN globally.
    """
    if not isinstance(raw, bytes):
        raise TypeError("raw must be bytes")
    if not isinstance(limits, IntakeLimits):
        raise TypeError("limits must be IntakeLimits")

    result = _new_report("CALLER_PROVIDED_BYTES", len(raw))
    if len(raw) > limits.max_ledger_bytes:
        return _stop(result, "LEDGER_SIZE_LIMIT")
    if not raw:
        return _stop(result, "EMPTY_LEDGER")

    lines = io.BytesIO(raw)
    while True:
        line = lines.readline(limits.max_line_bytes + 1)
        if not line:
            break

        index = result["records_checked"] + 1
        if index > limits.max_events:
            result["records"].append({
                "line": index, "outcome": "RESOURCE_LIMIT",
                "reason_code": "EVENT_COUNT_LIMIT",
            })
            result["records_checked"] = index
            return _stop(result, "EVENT_COUNT_LIMIT")

        if len(line) > limits.max_line_bytes:
            result["records"].append({
                "line": index, "outcome": "RESOURCE_LIMIT",
                "reason_code": "LINE_SIZE_LIMIT",
            })
            result["records_checked"] = index
            return _stop(result, "LINE_SIZE_LIMIT")
        if not line.endswith(b"\n"):
            result["records"].append({
                "line": index, "outcome": "INVALID_RECORD",
                "reason_code": "INCOMPLETE_JSONL_RECORD",
            })
            result["records_checked"] = index
            return _stop(result, "INCOMPLETE_JSONL_RECORD")
        if not line.strip():
            result["records"].append({
                "line": index, "outcome": "INVALID_RECORD",
                "reason_code": "EMPTY_JSONL_RECORD",
            })
            result["records_checked"] = index
            return _stop(result, "EMPTY_JSONL_RECORD")

        kind, parsed = _parse_envelope(line)
        metadata = {
            "line": index,
            "event_kind": kind,
            "raw_line_bytes": len(line),
            "record_sha256": hashlib.sha256(line).hexdigest(),
            "outcome": parsed,
            "reason_code": None if parsed == "VALID_ENVELOPE" else parsed,
            "semantic_extraction": "NOT_PERFORMED",
            "assessment": EPISODIC_ASSESSMENT,
        }
        result["records"].append(metadata)
        result["records_checked"] = index
        if parsed != "VALID_ENVELOPE":
            return _stop(result, parsed)
        result["valid_envelopes"] += 1

    result["status"] = "OBSERVED"
    result["eligible_records"] = result["valid_envelopes"]
    result["file_sha256"] = hashlib.sha256(raw).hexdigest()
    return result


def inspect_jsonl_file(
    path: str | Path, *,
    limits: IntakeLimits = IntakeLimits(),
) -> dict[str, Any]:
    """Bounded single-read file inspection with final-path symlink refusal.

    Parent symlinks, file replacement races and external source custody are
    NOT solved. Only an immutable byte snapshot is validated by this lab.
    """
    if not isinstance(limits, IntakeLimits):
        raise TypeError("limits must be IntakeLimits")
    target = Path(path)
    if target.is_symlink():
        return _stop(_new_report("READ_ONLY_FILE"), "SYMLINK_REFUSED")
    try:
        with target.open("rb") as handle:
            data = handle.read(limits.max_ledger_bytes + 1)
    except (OSError, ValueError):
        return _stop(_new_report("READ_ONLY_FILE"), "FILE_READ_FAILED")
    report = inspect_jsonl_bytes(data, limits=limits)
    report["source_kind"] = "READ_ONLY_FILE"
    return report
