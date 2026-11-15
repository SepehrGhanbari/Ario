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

# A versioned, source-content-free reason vocabulary. Arbitrary strings from
# caller-supplied parser objects are not safe to echo in a diagnostic report.
_ALLOWED_CANDIDATE_REASON_CODES = frozenset({
    "SCHEMA_REJECTED",  # synthetic legacy unit-test fixture
    "LEDGER_SIZE_LIMIT", "EMPTY_LEDGER", "EVENT_COUNT_LIMIT",
    "LINE_SIZE_LIMIT", "INCOMPLETE_JSONL_RECORD", "EMPTY_JSONL_RECORD",
    "JSON_DUPLICATE_KEY", "JSON_NONFINITE_CONSTANT", "INVALID_UTF8",
    "INVALID_JSON", "NOT_JSON_OBJECT", "MISSING_EVENT_KIND",
    "UNSUPPORTED_EVENT_KIND", "MISSING_OR_INVALID_TIMESTAMP",
    "MISSING_OR_INVALID_TASK_ID", "MISSING_OR_INVALID_GOAL",
    "MISSING_OR_INVALID_STEP_ID", "MISSING_OR_INVALID_STATUS",
    "MISSING_OR_INVALID_CRITERION_ID", "MISSING_OR_INVALID_WORKFLOW_ID",
    "MISSING_OR_INVALID_STAGE_ID", "SYMLINK_REFUSED", "NON_REGULAR_SOURCE",
    "FILE_READ_FAILED",
})


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
        if type(legacy) is not dict or type(strict) is not dict:
            result["reason_code"] = "UNEXPECTED_PARSER_RESULT"
            return result
        if path.open_count != 1:
            result["reason_code"] = "SNAPSHOT_READ_COUNT_MISMATCH"
            return result
        old_status = legacy.get("status")
        new_status = strict.get("status")
        if (type(old_status) is not str or type(new_status) is not str
                or old_status not in ("OBSERVED", "UNKNOWN")
                or new_status not in ("OBSERVED", "UNKNOWN")):
            result["reason_code"] = "UNRECOGNIZED_PARSER_STATUS"
            return result
        result["legacy_status"] = old_status
        result["candidate_status"] = new_status
        reason = strict.get("reason_code")
        if reason is None:
            result["candidate_reason_code"] = None
        elif type(reason) is str and reason in _ALLOWED_CANDIDATE_REASON_CODES:
            result["candidate_reason_code"] = reason
        else:
            # Caller-supplied parser messages may contain the original private
            # event bytes. Never echo unrecognized reason strings or objects.
            result["candidate_reason_code"] = "UNRECOGNIZED_CANDIDATE_REASON"
            result["reason_code"] = "UNRECOGNIZED_CANDIDATE_REASON"
            return result
        if result["legacy_status"] != old_status or result["candidate_status"] != new_status:
            result["reason_code"] = "UNRECOGNIZED_PARSER_STATUS"
            return result
        if old_status == "OBSERVED" and new_status == "OBSERVED":
            digest = hashlib.sha256(raw).hexdigest()
            old_count = legacy.get("event_count")
            strict_count = strict.get("eligible_records")
            old_digest = legacy.get("sha256")
            strict_digest = strict.get("file_sha256")
            if (type(old_count) is not int or type(strict_count) is not int
                    or old_count < 1 or strict_count < 1
                    or type(old_digest) is not str or type(strict_digest) is not str
                    or old_digest != digest or strict_digest != digest
                    or old_count != strict_count):
                result["reason_code"] = "ACCEPTED_DIGEST_OR_COUNT_MISMATCH"
                return result
            result["comparison"] = "AGREE_OBSERVED"
            # Only copy already checked integers, not re-read untrusted mappings.
            result["legacy_record_count"] = old_count
            result["candidate_eligible_records"] = strict_count
            if include_digest:
                result["snapshot_sha256"] = digest
        elif old_status == "UNKNOWN" and new_status == "UNKNOWN":
            result["comparison"] = "AGREE_UNKNOWN"  # only top-level status agreed
        else:
            result["comparison"] = "DISAGREE"
        return result
    except Exception:
        # A parser or hostile result may raise during status/metadata access.
        # Return a fresh safe report; never echo raw exception text or source.
        safe = _fresh_report(len(raw))
        safe["reason_code"] = "COMPARATOR_EXECUTION_ERROR"
        return safe
