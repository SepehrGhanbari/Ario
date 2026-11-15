"""Ario research-only same-snapshot differential comparator, candidate v0.1.

No filesystem access, repository writes, memory mutations, evidentiary admission,
truth assessment, source authentication or permanent record storage is performed
by this module. The two existing parser modules are passed in by the caller.

The legacy observer is invoked with a FUNCTION-LOCAL replacement of its Path
binding. This avoids mutating its module globals and forces the identical bytes
object to be read by both candidate parsers.
"""
from __future__ import annotations

import hashlib
import io
import types
from pathlib import PurePosixPath
from typing import Any

COMPARATOR_VERSION = "ario_same_snapshot_research_v0_1"
DEFAULT_MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024


class _SnapshotPath:
    """Pure read-only, in-memory stand-in for legacy observer Path."""

    def __init__(self, raw: bytes) -> None:
        self._raw = raw
        self.open_count = 0

    def absolute(self) -> PurePosixPath:
        return PurePosixPath("/RESEARCH-ONLY-SNAPSHOT-NO-HOST-PATH")

    def is_symlink(self) -> bool:
        return False

    def open(self, mode: str) -> io.BytesIO:
        if mode != "rb":
            raise ValueError("read-only synthetic snapshot")
        self.open_count += 1
        if self.open_count > 1:
            raise ValueError("legacy observer reopened input unexpectedly")
        return io.BytesIO(self._raw)


def _fresh_report(length: int) -> dict[str, Any]:
    return {
        "comparison_version": COMPARATOR_VERSION,
        "comparison": "UNKNOWN_COMPARISON",
        "reason_code": None,
        "source_kind": "CALLER_PROVIDED_IMMUTABLE_BYTES",
        "source_authenticity": "UNKNOWN",
        "assessment": "NOT_ASSESSED",
        "memory_mutation": "NONE",
        "history_mutation": "NONE",
        "raw_bytes": length,
        "digest_scheme": "raw_line_sha256_v0_2",
        "snapshot_sha256": None,  # omit linkable digest unless explicitly requested
        "legacy_status": None,
        "candidate_status": None,
        "candidate_reason_code": None,
        "legacy_record_count": None,
        "candidate_eligible_records": None,
    }


def compare_snapshot(
    raw: bytes,
    *,
    legacy_observer_module: Any,
    strict_lab_module: Any,
    include_digest: bool = False,
    max_snapshot_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES,
) -> dict[str, Any]:
    """Compare two unmodified parsers on the SAME bytes object.

    Comparison outcomes: AGREE_OBSERVED, AGREE_UNKNOWN, DISAGREE,
    UNKNOWN_COMPARISON. None implies independent proof, safety or truth.

    The legacy module function's *own* globals are shallow-copied and the copy's
    Path binding is replaced. Its original module object and global names are
    not monkeypatched. The strict lab receives the same immutable bytes.
    """
    if type(raw) is not bytes:
        raise TypeError("raw must be immutable bytes")
    if type(max_snapshot_bytes) is not int or not 0 < max_snapshot_bytes <= DEFAULT_MAX_SNAPSHOT_BYTES:
        raise ValueError("max_snapshot_bytes must be an integer within the research cap")
    if type(include_digest) is not bool:
        raise TypeError("include_digest must be a boolean")

    result = _fresh_report(len(raw))
    if len(raw) > max_snapshot_bytes:
        result["reason_code"] = "SNAPSHOT_SIZE_LIMIT"
        return result
    if not raw:
        result["reason_code"] = "EMPTY_SNAPSHOT"
        return result

    path = _SnapshotPath(raw)
    try:
        old_function = legacy_observer_module.observe_ledger
        if not isinstance(old_function, types.FunctionType):
            result["reason_code"] = "UNSUPPORTED_OBSERVER_INTERFACE"
            return result
        copied_globals = dict(old_function.__globals__)
        copied_globals["Path"] = lambda _ignored: path
        isolated_old_function = types.FunctionType(
            old_function.__code__, copied_globals, old_function.__name__,
            old_function.__defaults__, old_function.__closure__,
        )
        legacy = isolated_old_function("snapshot-only")
        strict = strict_lab_module.inspect_jsonl_bytes(raw)
        if not isinstance(legacy, dict) or not isinstance(strict, dict):
            result["reason_code"] = "UNEXPECTED_PARSER_RESULT"
            return result
        if path.open_count != 1:
            result["reason_code"] = "SNAPSHOT_READ_COUNT_MISMATCH"
            return result
    except Exception:
        # Deliberately do not disclose source data or exception text/paths.
        result["reason_code"] = "COMPARATOR_EXECUTION_ERROR"
        return result

    old_status = legacy.get("status")
    new_status = strict.get("status")
    result["legacy_status"] = old_status if old_status in ("OBSERVED", "UNKNOWN") else "UNKNOWN"
    result["candidate_status"] = new_status if new_status in ("OBSERVED", "UNKNOWN") else "UNKNOWN"
    reason = strict.get("reason_code")
    result["candidate_reason_code"] = reason if isinstance(reason, str) else None
    if result["legacy_status"] != old_status or result["candidate_status"] != new_status:
        result["reason_code"] = "UNRECOGNIZED_PARSER_STATUS"
        return result
    if old_status == "OBSERVED" and new_status == "OBSERVED":
        digest = hashlib.sha256(raw).hexdigest()
        if (legacy.get("sha256") != digest or strict.get("file_sha256") != digest
                or legacy.get("event_count") != strict.get("eligible_records")):
            result["reason_code"] = "ACCEPTED_DIGEST_OR_COUNT_MISMATCH"
            return result
        result["comparison"] = "AGREE_OBSERVED"
        result["legacy_record_count"] = legacy["event_count"]
        result["candidate_eligible_records"] = strict["eligible_records"]
        if include_digest:
            result["snapshot_sha256"] = digest
    elif old_status == "UNKNOWN" and new_status == "UNKNOWN":
        result["comparison"] = "AGREE_UNKNOWN"  # only top-level status agreed
    else:
        result["comparison"] = "DISAGREE"
    return result
