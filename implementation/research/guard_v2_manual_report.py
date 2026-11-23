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
# Every reason/status the reader can emit is an upper-case token (fixed literals,
# HTTP status codes, fixed labels). A closed key set is not enough: values of
# allowed keys must not carry objects, lists, numbers or free text either.
TOKEN = re.compile(r"[A-Z0-9_]{1,256}\Z")
# Reader main() emits type(exc).__name__ only for constructor failures.
# Match known caught exception classes and common OSError subclasses, rather
# than accepting a forged decision-looking string as an exception class.
ERROR_TYPE_NAMES = frozenset({
    "ReviewGraphUnknown", "ReadUnknown", "ValueError", "TypeError", "OSError",
    "TimeoutError", "ConnectionError", "ConnectionRefusedError",
    "ConnectionResetError", "ConnectionAbortedError", "BrokenPipeError",
    "PermissionError", "FileNotFoundError", "FileExistsError", "IsADirectoryError",
    "NotADirectoryError", "BlockingIOError", "InterruptedError", "ChildProcessError",
    "ProcessLookupError", "URLError", "HTTPError", "RemoteDisconnected",
    "SSLError", "SSLCertVerificationError", "SSLEOFError", "SSLZeroReturnError",
    "SSLSyscallError",
})
SUCCESS_GRAPH_REASON = "TWO_COMPLETE_GRAPH_SAMPLES_MATCH"
FRESHNESS = "TWO_SAMPLED_GRAPHS_MATCH_NON_ATOMIC"
SUCCESS_REASONS = frozenset({"PR_DRAFT_READ_ONLY_HOLD", "LIVE_READ_ONLY_NON_ATOMIC_HOLD"})
# Keys only a COMPLETED observation sets (guard_v2_trusted_manual.observe sets
# them last, immediately before the success reason). A failed run never has them.
SUCCESS_ONLY_KEYS = frozenset({"live_identity", "review_freshness"})
SAMPLE_VALUES = frozenset({"SAMPLED_STABLE_UNATTESTED", "UNKNOWN"})
# CLOSED failure-reason vocabulary: every reason the manual reader can emit on a
# failed run, derived from the pinned sources (guard_v2_review_graph.py,
# guard_v2_trusted_manual.py, ario_repo_self_audit.GitHubReadOnly.get_json).
# The in-repository test_guard_v2_r21a_vocabulary_contract.py re-derives
# these sets from reader AST and rejects vocabulary drift in both directions.
# There is deliberately NO keyword denylist and NO open fallback: an
# unlisted token on a failed run is rejected (fail-closed, report is replaced by
# INVALID_DIAGNOSTIC_JSON by the workflow, exit code stays nonzero).
GRAPH_REASON_LITERALS = frozenset({
    "DUPLICATE_GRAPH_NODE_ID", "GRAPHQL_DATA_MISSING", "GRAPHQL_ERROR_OR_MISSING_PAGE",
    "GRAPHQL_HTTP_NOT_200", "GRAPHQL_NETWORK_UNKNOWN", "GRAPHQL_RESPONSE_TOO_LARGE",
    "GRAPH_COLLECTION_OVERFLOW", "GRAPH_PAGE_TOO_LARGE", "GRAPH_PR_IDENTITY_MISMATCH",
    "GRAPH_PR_REVISION_CHANGED", "GRAPH_TOTAL_CHANGED_DURING_PAGES",
    "IDENTITY_CHANGED_DURING_PAGINATION", "INCOMPLETE_GRAPH_COLLECTION",
    "INCOMPLETE_THREAD_REPLIES", "INVALID_GRAPHQL_TARGET", "INVALID_GRAPH_NODE",
    "INVALID_GRAPH_PR_STATE", "INVALID_ISSUE_COMMENT", "INVALID_OR_DUPLICATE_THREAD_REPLY",
    "INVALID_OR_REPEATED_GRAPH_CURSOR", "INVALID_PAGE_CURSOR", "INVALID_REVIEW",
    "INVALID_THREAD_STATE", "MALFORMED_BIGINT_ID", "MALFORMED_GRAPHQL_ENVELOPE",
    "MALFORMED_GRAPHQL_JSON", "MALFORMED_GRAPH_CONNECTION", "MALFORMED_GRAPH_PAGE_INFO",
    "MALFORMED_OR_UNAVAILABLE_GRAPH", "MAX_GRAPH_PAGES_EXCEEDED", "MISSING_READ_ONLY_TOKEN",
    "PULL_REQUEST_NOT_VISIBLE", "REPOSITORY_NOT_VISIBLE",
    "REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES",
    "UNASSESSED", "UNKNOWN",
})
MANUAL_REASON_LITERALS = frozenset({
    "INVALID_FIXED_TARGET_OR_SOURCE_SHA", "MALFORMED_REST_REPOSITORY_OR_PR",
    "READER_OR_METADATA_UNAVAILABLE", "REST_PR_BASE_OR_STATE_UNEXPECTED",
    "REST_PR_CHANGED_DURING_GRAPH_READ", "REST_PR_IDENTITY_OR_HEAD_MISMATCH",
    "REST_PR_METADATA_MISSING", "TRUSTED_OBSERVER_INITIALIZATION_FAILED",
})
HTTP_REASON = re.compile(r"GRAPHQL_HTTP_[0-9]{3}\Z")
# ario_repo_self_audit.GitHubReadOnly.get_json is the ONLY REST call the manual
# reader makes (it uses rest.API, rest.GitHubReadOnly, rest.ReadUnknown only), so
# its ReadUnknown reasons are the complete REST vocabulary. GITHUB_HTTP_### is
# bounded to three digits: http.client rejects status lines outside 100..999.
REST_REASON_LITERALS = frozenset({
    "FORBIDDEN_HOST", "FORBIDDEN_PATH", "NON_200_RESPONSE",
    "INCOMPLETE_OR_OVERSIZED_RESPONSE", "GITHUB_READ_UNAVAILABLE",
    "INVALID_JSON", "INVALID_API_JSON",
    "PAGINATION_NEXT_LINK_PRESENT",
})
REST_HTTP_REASON = re.compile(r"GITHUB_HTTP_[0-9]{3}\Z")


def _failure_token_ok(value: Any) -> bool:
    if not _token(value) or value in SUCCESS_REASONS or value == SUCCESS_GRAPH_REASON:
        return False
    if value in GRAPH_REASON_LITERALS or value in MANUAL_REASON_LITERALS:
        return True
    if HTTP_REASON.fullmatch(value):
        return True
    if value.startswith("GRAPH_") and (value[6:] in GRAPH_REASON_LITERALS or
                                       HTTP_REASON.fullmatch(value[6:])):
        return True
    return value in REST_REASON_LITERALS or REST_HTTP_REASON.fullmatch(value) is not None


def _token(value: Any) -> bool:
    return type(value) is str and TOKEN.fullmatch(value) is not None


def _identity_bound(identity: Any, number: int, head: str) -> bool:
    return (type(identity) is dict and set(identity) == IDENTITY_KEYS and
            type(identity["repository_id"]) is int and identity["repository_id"] > 0 and
            type(identity["pr_id"]) is int and identity["pr_id"] > 0 and
            type(identity["pr_number"]) is int and identity["pr_number"] == number and
            identity["head_sha"] == head and
            type(identity["base_sha"]) is str and
            SHA40.fullmatch(identity["base_sha"]) is not None)


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
    _assert(value.get("schema") == SCHEMA and
            value.get("status") == EXPECTED_UNKNOWN and
            value.get("disposition") == "HOLD",
            "INVALID_REPORT_SCHEMA_OR_STATUS")
    _assert(_token(value.get("reason")), "INVALID_REPORT_REASON")
    # Optional fields are typed on EVERY exit code, not only on success:
    # a failed run's artifact is still read by humans and tools.
    _assert("review_graph_sample" not in value or
            (type(value["review_graph_sample"]) is str and
             value["review_graph_sample"] in SAMPLE_VALUES),
            "INVALID_OPTIONAL_FIELD")
    _assert("review_graph_reason" not in value or _token(value["review_graph_reason"]),
            "INVALID_OPTIONAL_FIELD")
    _assert("review_freshness" not in value or value["review_freshness"] == FRESHNESS,
            "INVALID_OPTIONAL_FIELD")
    _assert("error_type" not in value or
            (value["reason"] == "TRUSTED_OBSERVER_INITIALIZATION_FAILED" and
             type(value["error_type"]) is str and
             value["error_type"] in ERROR_TYPE_NAMES),
            "INVALID_OPTIONAL_FIELD")
    for key in ("first_digest", "second_digest"):
        _assert(key not in value or value[key] is None or
                (type(value[key]) is str and SHA256.fullmatch(value[key]) is not None),
                "INVALID_OPTIONAL_FIELD")
    _assert("source_commit_sha" not in value or value["source_commit_sha"] == source,
            "SOURCE_COMMIT_MISMATCH")
    _assert("live_identity" not in value or
            _identity_bound(value["live_identity"], number, head),
            "INVALID_BOUND_PR_IDENTITY")
    _assert(value.get("merge_authorized") is False and
            value.get("check_publish_authorized") is False and
            value.get("trust_activated") is False,
            "INVALID_REPORT_AUTHORITY")
    _assert(value.get("execution_attestation") == EXPECTED_NOT_ESTABLISHED and
            value.get("independent_custody") == EXPECTED_NOT_ESTABLISHED and
            value.get("atomic_merge_attestation") == EXPECTED_NOT_ESTABLISHED and
            value.get("source_provenance") == "PROVIDED_BY_CALLER_NOT_INDEPENDENTLY_VERIFIED",
            "INVALID_REPORT_BOUNDARY")
    if reader_exit != 0:
        # The reader returns 0 only for a completed observation, and a completed
        # observation is the only path that sets these. A nonzero exit therefore
        # cannot legitimately carry a success shape or a decision-like reason.
        _assert(not (SUCCESS_ONLY_KEYS & set(value)), "SUCCESS_SHAPE_ON_FAILED_RUN")
        _assert(_failure_token_ok(value["reason"]), "INVALID_FAILURE_REASON")
        # review_graph_reason may legitimately be the graph success token when the
        # later REST recheck failed, so only decision-like text is rejected here.
        _assert("review_graph_reason" not in value or
                value["review_graph_reason"] == SUCCESS_GRAPH_REASON or
                _failure_token_ok(value["review_graph_reason"]), "INVALID_FAILURE_REASON")
    if reader_exit == 0:
        _assert(value["reason"] in SUCCESS_REASONS and
                value.get("review_graph_sample") == "SAMPLED_STABLE_UNATTESTED" and
                value.get("review_graph_reason") == SUCCESS_GRAPH_REASON and
                value.get("review_freshness") == FRESHNESS and
                "error_type" not in value and
                value.get("source_commit_sha") == source,
                "INCOMPLETE_SUCCESS_DIAGNOSTIC")
        first, second = value.get("first_digest"), value.get("second_digest")
        _assert(type(first) is str and SHA256.fullmatch(first) is not None and
                first == second, "INVALID_SAMPLE_DIGEST")
        _assert("live_identity" in value, "INVALID_BOUND_PR_IDENTITY")
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
