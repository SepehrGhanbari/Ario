"""Validate the *shape* of a manual Guard V2 diagnostic, never authorize merge.

Run only from the protected-main checkout, with no credential or network.
A successful validation means a completed non-authoritative HOLD diagnostic,
not independent evidence attestation or a trustworthy merge decision.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any

SCHEMA = "ARIO-GUARD-V2-TRUSTED-MANUAL-READ-LAB-0.1"
MAX_BYTES = 65536
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
EXPECTED_UNKNOWN = "UNKNOWN"
EXPECTED_NOT_ESTABLISHED = "NOT_ESTABLISHED"
# Exactly the keys research.guard_v2_trusted_manual can emit. Anything else
# (extra "decision" fields, look-alike keys, nested flags) is not this schema.
ALLOWED_KEYS = frozenset({
    "schema", "disposition", "status", "reason", "merge_authorized",
    "check_publish_authorized", "trust_activated", "execution_attestation",
    "independent_custody", "atomic_merge_attestation", "source_provenance",
    "source_commit_sha", "review_graph_sample", "review_graph_reason",
    "first_digest", "second_digest", "live_identity", "review_freshness",
    "error_type",
})
IDENTITY_KEYS = frozenset({"repository_id", "pr_id", "pr_number", "head_sha", "base_sha"})


class InvalidDiagnostic(ValueError):
    pass


def _pairs(items: list[tuple[str, Any]]) -> dict:
    out = {}
    for key, value in items:
        if key in out:
            raise InvalidDiagnostic("DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _constant(_value: str) -> None:
    raise InvalidDiagnostic("INVALID_JSON_CONSTANT")


def _float(_value: str) -> None:
    raise InvalidDiagnostic("NONINTEGER_JSON_NUMBER")


def _assert(condition: bool, reason: str) -> None:
    if not condition:
        raise InvalidDiagnostic(reason)


def validate_file(path: Path, number: int, head: str, source: str,
                  reader_exit: int) -> dict:
    """Reject missing, ambiguous, oversized, unsafe or incomplete reports."""
    _assert(type(number) is int and number > 0 and
            isinstance(head, str) and SHA40.fullmatch(head) is not None and
            isinstance(source, str) and SHA40.fullmatch(source) is not None and
            type(reader_exit) is int and 0 <= reader_exit <= 255,
            "INVALID_EXPECTED_CONTEXT")
    data = path.read_bytes()
    _assert(0 < len(data) <= MAX_BYTES, "MISSING_OR_OVERSIZE_REPORT")
    try:
        value = json.loads(data.decode("utf-8"),
                           object_pairs_hook=_pairs,
                           parse_constant=_constant,
                           parse_float=_float)
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise InvalidDiagnostic("MALFORMED_JSON") from exc
    _assert(type(value) is dict, "REPORT_NOT_OBJECT")
    # The reader prints with ensure_ascii=True; raw non-ASCII is not its output.
    _assert(data.isascii(), "NON_ASCII_REPORT")
    _assert(set(value) <= ALLOWED_KEYS, "UNEXPECTED_REPORT_KEY")
    if "live_identity" in value:
        _assert(type(value["live_identity"]) is dict and
                set(value["live_identity"]) == IDENTITY_KEYS,
                "UNEXPECTED_IDENTITY_KEYS")
    _assert(value.get("schema") == SCHEMA and
            value.get("status") == EXPECTED_UNKNOWN and
            value.get("disposition") == "HOLD",
            "INVALID_REPORT_SCHEMA_OR_STATUS")
    _assert(type(value.get("reason")) is str and
            0 < len(value["reason"]) <= 256,
            "INVALID_REPORT_REASON")
    _assert(value.get("merge_authorized") is False and
            value.get("check_publish_authorized") is False and
            value.get("trust_activated") is False,
            "INVALID_REPORT_AUTHORITY")
    _assert(value.get("execution_attestation") == EXPECTED_NOT_ESTABLISHED and
            value.get("independent_custody") == EXPECTED_NOT_ESTABLISHED and
            value.get("atomic_merge_attestation") == EXPECTED_NOT_ESTABLISHED and
            value.get("source_provenance") == "PROVIDED_BY_CALLER_NOT_INDEPENDENTLY_VERIFIED",
            "INVALID_REPORT_BOUNDARY")
    if reader_exit == 0:
        _assert(value["reason"] in ("PR_DRAFT_READ_ONLY_HOLD",
                                     "LIVE_READ_ONLY_NON_ATOMIC_HOLD") and
                value.get("review_graph_sample") == "SAMPLED_STABLE_UNATTESTED" and
                value.get("review_freshness") == "TWO_SAMPLED_GRAPHS_MATCH_NON_ATOMIC" and
                value.get("source_commit_sha") == source,
                "INCOMPLETE_SUCCESS_DIAGNOSTIC")
        first, second = value.get("first_digest"), value.get("second_digest")
        _assert(type(first) is str and SHA256.fullmatch(first) is not None and
                first == second, "INVALID_SAMPLE_DIGEST")
        identity = value.get("live_identity")
        _assert(type(identity) is dict and
                type(identity.get("repository_id")) is int and identity["repository_id"] > 0 and
                type(identity.get("pr_id")) is int and identity["pr_id"] > 0 and
                type(identity.get("pr_number")) is int and identity["pr_number"] == number and
                identity.get("head_sha") == head and
                type(identity.get("base_sha")) is str and
                SHA40.fullmatch(identity["base_sha"]) is not None,
                "INVALID_BOUND_PR_IDENTITY")
    return value


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 5:
        return 2
    try:
        path, number, head, source, reader_exit = args
        # Plain decimal only: int() would also accept "2_95", " 295 " or "+295".
        if not (number.isascii() and number.isdigit() and
                reader_exit.isascii() and reader_exit.isdigit()):
            return 2
        validate_file(Path(path), int(number), head, source, int(reader_exit))
    except (InvalidDiagnostic, ValueError, TypeError, OSError,
            RecursionError, OverflowError):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
