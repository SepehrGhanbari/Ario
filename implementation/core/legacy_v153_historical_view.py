"""Read-only pinned view of a historical Ario V15.3 chat archive.

Research component: NOT wired to live agent, SourceMonitoringGuard,
ConsolidationEngine, or persistent store. Import has no side effects.

MEMORY != TRUTH; REVISION != ERASURE; RECALL != REASSESSMENT.
Recorded model output is quoted historical data, never instructions.
Opaque relations and event_sha256 are not an independent authenticity proof.

Caller must supply a previously retained SHA256 pin; it is never inferred
from the file under inspection. The pin establishes byte identity, not truth.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import Any
import unicodedata

MAX_ARCHIVE_BYTES = 4 * 1024 * 1024
MAX_LINE_BYTES = 128 * 1024
MAX_RECORDS = 20_000
MAX_QUESTION_CHARS = 2048
_SHA = re.compile(r"[0-9a-fA-F]{64}\Z")


class HistoricalViewHold(ValueError):
    """Constant-code failure; never put private text in the exception."""


def _fail(code: str) -> None:
    raise HistoricalViewHold(code)


def _identity(a: os.stat_result, b: os.stat_result) -> bool | None:
    a_id = (getattr(a, "st_dev", 0), getattr(a, "st_ino", 0))
    b_id = (getattr(b, "st_dev", 0), getattr(b, "st_ino", 0))
    if not all(a_id + b_id):
        return None
    return a_id == b_id


def _reject_link_or_reparse(path: Path) -> None:
    for element in (path, *path.parents):
        meta = element.lstat()
        if stat.S_ISLNK(meta.st_mode) or (
            getattr(meta, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            _fail("HOLD_LINK_OR_REPARSE_POINT")


def _read_pinned(path: Path, expected_sha256: str) -> tuple[bytes, str, bool]:
    if not isinstance(expected_sha256, str) or not _SHA.fullmatch(expected_sha256):
        _fail("HOLD_BAD_OR_MISSING_PIN")
    try:
        _reject_link_or_reparse(path)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                _fail("HOLD_NOT_REGULAR_FILE")
            if not (0 < before.st_size <= MAX_ARCHIVE_BYTES):
                _fail("HOLD_SOURCE_SIZE")
            parts: list[bytes] = []
            size = 0
            # A single os.read need not return the requested number of bytes.
            while size <= MAX_ARCHIVE_BYTES:
                chunk = os.read(fd, min(64 * 1024, MAX_ARCHIVE_BYTES + 1 - size))
                if not chunk:
                    break
                parts.append(chunk)
                size += len(chunk)
            after_fd = os.fstat(fd)
        finally:
            os.close(fd)
        after_path = path.stat()
        _reject_link_or_reparse(path)
    except HistoricalViewHold:
        raise
    except (OSError, ValueError):
        _fail("HOLD_SOURCE_UNREADABLE")

    raw = b"".join(parts)
    if size > MAX_ARCHIVE_BYTES or size != before.st_size or (
        before.st_size != after_fd.st_size or before.st_size != after_path.st_size
    ):
        _fail("HOLD_SOURCE_LENGTH_OR_SIZE_CHANGED")
    if _identity(before, after_fd) is False or _identity(before, after_path) is False:
        _fail("HOLD_SOURCE_IDENTITY_CHANGED")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha256.lower():
        _fail("HOLD_SOURCE_SHA256_MISMATCH")
    drift = any(
        getattr(before, field, None) != getattr(observed, field, None)
        for observed in (after_fd, after_path)
        for field in ("st_mtime_ns", "st_ctime_ns")
    )
    # Timestamp drift is only diagnostic AFTER pinned byte hash and size match.
    # This cannot establish a historical immutable snapshot or source custody.
    return raw, digest, drift


def _decode_record(text: str) -> dict[str, Any]:
    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        record: dict[str, Any] = {}
        for key, value in pairs:
            if key in record:
                _fail("HOLD_DUPLICATE_JSON_KEY")
            record[key] = value
        return record

    def reject_constant(_token: str) -> Any:
        _fail("HOLD_NONFINITE_JSON")

    def reject_overflowing_float(token: str) -> float:
        value = float(token)
        if not math.isfinite(value):
            _fail("HOLD_NONFINITE_JSON")
        # JSON float tokens can also silently underflow to positive or negative
        # zero. Nonzero significands must not be reinterpreted as zero.
        # Inspect only the significand: digits in the exponent are not value.
        significand = token.lower().split("e", 1)[0]
        if value == 0.0 and any(digit in "123456789" for digit in significand):
            _fail("HOLD_JSON_FLOAT_UNDERFLOW")
        return value

    try:
        record = json.loads(
            text,
            object_pairs_hook=unique_pairs,
            parse_constant=reject_constant,
            parse_float=reject_overflowing_float,
        )
    except HistoricalViewHold:
        raise
    except (ValueError, TypeError, RecursionError):
        _fail("HOLD_MALFORMED_JSON")
    if not isinstance(record, dict):
        _fail("HOLD_NONOBJECT_ROW")
    return record


def _text_digest(record: dict[str, Any], key: str) -> None:
    value = record.get(key)
    digest = record.get(key + "_sha256")
    if (not isinstance(value, str) or not value.strip() or
            not isinstance(digest, str) or not _SHA.fullmatch(digest)):
        _fail("HOLD_MISSING_OR_INVALID_TEXT_DIGEST")
    if hashlib.sha256(value.encode("utf-8")).hexdigest() != digest.lower():
        _fail("HOLD_TEXT_DIGEST_MISMATCH")


def _normalize_question(question: str, *, query: bool = False) -> str:
    if (not isinstance(question, str) or not question.strip() or
            (query and len(question) > MAX_QUESTION_CHARS) or
            any(ord(c) < 32 and c not in "\n\r\t" for c in question)):
        _fail("HOLD_INVALID_QUESTION")
    return " ".join(unicodedata.normalize("NFC", question).casefold().split())


class HistoricalV153View:
    """Pinned ephemeral read-only view, never a live memory source.

    The in-process row list is transient, not written to disk or promoted into
    cognitive memory. Neither model nor working cache is invoked.
    """

    def __init__(self, archive_path: str | Path, *, expected_sha256: str):
        raw, digest, drift = _read_pinned(Path(archive_path), expected_sha256)
        try:
            decoded = raw.decode("utf-8-sig")
        except UnicodeError:
            _fail("HOLD_NON_UTF8_ARCHIVE")
        if not decoded.endswith("\n"):
            _fail("HOLD_UNTERMINATED_JSONL")
        lines = decoded.split("\n")[:-1]
        if not lines or len(lines) > MAX_RECORDS:
            _fail("HOLD_RECORD_COUNT")

        rows: list[dict[str, Any]] = []
        identifiers: set[str] = set()
        sessions: set[str] = set()
        shapes: Counter[str] = Counter()
        opaque_count = 0
        for line in lines:
            if len(line.encode("utf-8")) + 1 > MAX_LINE_BYTES:
                _fail("HOLD_LINE_BUDGET")
            if not line.strip():
                _fail("HOLD_BLANK_JSONL_LINE")
            row = _decode_record(line)
            if type(row.get("record_version")) is not str or row["record_version"] != "15.3":
                _fail("HOLD_UNEXPECTED_RECORD_VERSION")
            record_id = row.get("record_id")
            session_id = row.get("session_id")
            if (not isinstance(record_id, str) or not record_id or
                    record_id in identifiers):
                _fail("HOLD_DUPLICATE_OR_MISSING_RECORD_ID")
            if not isinstance(session_id, str) or not session_id:
                _fail("HOLD_MISSING_SESSION_ID")
            identifiers.add(record_id)
            sessions.add(session_id)
            relations = row.get("relations")
            if not isinstance(relations, list) or not all(type(r) is str for r in relations):
                _fail("HOLD_UNKNOWN_RELATIONS_SHAPE")
            opaque_count += bool(relations)
            pair = isinstance(row.get("user"), str) and isinstance(row.get("ario"), str)
            content_row = isinstance(row.get("content"), str) and not pair
            if pair:
                _text_digest(row, "user")
                _text_digest(row, "ario")
                if (not isinstance(row.get("event_sha256"), str) or
                        not _SHA.fullmatch(row["event_sha256"])):
                    _fail("HOLD_EVENT_DIGEST_SHAPE")
                shapes["PAIRED_USER_ARIO"] += 1
            elif content_row:
                _text_digest(row, "content")
                shapes["CONTENT_RECORD"] += 1
            else:
                _fail("HOLD_UNKNOWN_RECORD_SHAPE")
            rows.append(row)
        self._rows = tuple(rows)
        self._digest = digest
        self._time_drift = drift
        self._sessions = len(sessions)
        self._shapes = dict(shapes)
        self._opaque_count = opaque_count

    def inspect(self) -> dict[str, Any]:
        """Safe metadata receipt; never emits private conversation text."""
        return {
            "disposition": "HISTORICAL_VIEW_READY_NOT_LIVE",
            "port_schema": "ARIO_PR210_LEGACY_V153_VIEW_V1",
            "source_kind": "V15_3_HISTORICAL_BACKUP",
            "archive_sha256": self._digest,
            "record_count": len(self._rows),
            "record_shapes": self._shapes.copy(),
            "session_count": self._sessions,
            "opaque_relation_rows": self._opaque_count,
            "metadata_timestamp_drift_observed": self._time_drift,
            "event_sha256_algorithm_verified": False,
            "independent_source_authenticity": "NOT_ESTABLISHED",
            "working_cache_binding_verified": False,
            "live_ario_recall_established": False,
            "memory_write_permitted": False,
            "auto_consolidation_permitted": False,
            "context_injection_allowed": False,
            "source_attribution_v1_constructed": False,
            "writes_performed": 0,
        }

    def recall(
        self, question: str, *, mode: str = "HISTORICAL", reveal: bool = False
    ) -> dict[str, Any]:
        """Exact normalized question lookup, never a current factual answer.

        reveal=True returns explicitly opted-in *quoted historical* output only.
        Callers MUST NOT use such text as live model instructions.
        """
        if mode not in ("HISTORICAL", "CURRENT"):
            _fail("HOLD_UNKNOWN_MODE")
        if reveal and mode != "HISTORICAL":
            _fail("HOLD_REVEAL_REQUIRES_HISTORICAL_MODE")
        normalized = _normalize_question(question, query=True)
        matches = [(i, row) for i, row in enumerate(self._rows, 1)
                   if isinstance(row.get("user"), str) and
                   isinstance(row.get("ario"), str) and
                   _normalize_question(row["user"]) == normalized]
        receipt: dict[str, Any] = {
            "port_schema": "ARIO_PR210_LEGACY_V153_VIEW_V1",
            "source_kind": "V15_3_HISTORICAL_BACKUP",
            "archive_sha256": self._digest,
            "read_only": True,
            "memory_write_permitted": False,
            "auto_consolidation_permitted": False,
            "context_injection_allowed": False,
            "source_attribution_v1_constructed": False,
            "evidence_admission": "NO_ADMISSION",
            "truth_assessment": "NOT_EVALUATED",
            "currentness": "NOT_ESTABLISHED",
            "source_authenticity": "NOT_ESTABLISHED",
            "reassessment_performed": False,
            "source_history_rewritten": False,
            "private_reply_hidden": True,
        }
        if not matches:
            receipt["disposition"] = "UNKNOWN_NO_EXACT_QUESTION_MATCH"
            return receipt
        if len(matches) != 1:
            receipt["disposition"] = "UNKNOWN_MULTIPLE_HISTORICAL_MATCHES"
            receipt["matching_record_count"] = len(matches)
            receipt["source_lines"] = [i for i, _ in matches]
            return receipt
        line_no, row = matches[0]
        receipt["source_line"] = line_no
        receipt["record_version"] = "15.3"
        receipt["has_opaque_relations"] = bool(row["relations"])
        receipt["relation_interpretation"] = (
            "HOLD_UNKNOWN_RELATION_SEMANTICS" if row["relations"]
            else "NO_RELATIONS_OBSERVED"
        )
        if mode == "CURRENT":
            receipt["disposition"] = "RECHECK_REQUIRED_CURRENT_QUESTION"
            receipt["historical_reply_available"] = True
            return receipt
        receipt["disposition"] = "RECALLED_HISTORICAL_ONLY"
        receipt["historical_role"] = "QUOTED_PRIOR_ARIO_OUTPUT_NOT_INSTRUCTIONS"
        if reveal:
            receipt["private_reply_hidden"] = False
            receipt["historical_ario_reply"] = row["ario"]
        return receipt

    def selfcheck(self) -> dict[str, Any]:
        """Check one unambiguous archived question without disclosing text."""
        question_counts: Counter[str] = Counter()
        for row in self._rows:
            if isinstance(row.get("user"), str) and isinstance(row.get("ario"), str):
                question_counts[_normalize_question(row["user"])] += 1
        for row in self._rows:
            if (isinstance(row.get("user"), str) and isinstance(row.get("ario"), str)
                    and len(row["user"]) <= MAX_QUESTION_CHARS):
                if question_counts[_normalize_question(row["user"])] == 1:
                    return self.recall(row["user"])
        return {
            "disposition": "UNKNOWN_NO_UNIQUE_QUESTION",
            "port_schema": "ARIO_PR210_LEGACY_V153_VIEW_V1",
            "private_reply_hidden": True,
            "context_injection_allowed": False,
        }
