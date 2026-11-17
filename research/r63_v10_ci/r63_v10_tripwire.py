"""R63 V10 RESEARCH-ONLY candidate: compare V1 disk, V2 disk, RPC memory.

This is a *read-only* precondition for the guest witness spend RPC. It contains
no CNG calls, no keys, no filesystem mutation and no host/production installer.
It is intentionally not a complete concurrency, durability or antirollback
solution.  In particular it cannot pin data against cross-process writes after
validation or an administrator's coherent rollback.

Caller MUST hold the witness-server lock throughout comparison and the
subsequent durable append/decision boundary; cross-process writers require
separately enforced exclusion. DO NOT treat an unanchored V2 head as trusted.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any, Callable

MAX_V1_BYTES = 2 * 1024 * 1024
MAX_V2_BYTES = 2 * 1024 * 1024
MAX_ROWS = 100_000
MAX_LINE_BYTES = 8192
_HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


class TripwireHold(ValueError):
    """Validation failure. Caller must fail closed, before any new CNG use."""


def _hash64(value: Any) -> bool:
    return type(value) is str and _HEX64.fullmatch(value) is not None


def _read_bounded(path: Path, limit: int) -> bytes:
    """Best-effort bounded read. Not a lock or race-free filesystem snapshot."""
    try:
        with path.open("rb") as stream:
            raw = stream.read(limit + 1)
    except OSError as exc:
        raise TripwireHold("MISSING_OR_UNREADABLE_DURABLE_JOURNAL") from exc
    if len(raw) > limit:
        raise TripwireHold("JOURNAL_LIMIT_EXCEEDED")
    return raw


def parse_v1(raw: bytes, *, canonical: Callable[[Any], bytes]) -> list[list[str]]:
    """Parse actual legacy [nonce,id] append-order records, without sorting."""
    if type(raw) is not bytes:
        raise TripwireHold("V1_NOT_BYTES")
    if len(raw) > MAX_V1_BYTES:
        raise TripwireHold("V1_TOO_LARGE")
    if raw and not raw.endswith(b"\n"):
        raise TripwireHold("V1_PARTIAL_LAST_LINE")
    lines = raw[:-1].split(b"\n") if raw else []
    if len(lines) > MAX_ROWS:
        raise TripwireHold("V1_TOO_MANY_ROWS")
    rows: list[list[str]] = []
    seen_nonce, seen_id = set(), set()
    for line in lines:
        if not line or len(line) > MAX_LINE_BYTES:
            raise TripwireHold("V1_EMPTY_OR_OVERSIZED_ROW")
        try:
            record = json.loads(line.decode("ascii"))
        except (ValueError, UnicodeError, TypeError, RecursionError) as exc:
            raise TripwireHold("V1_BAD_JSON_OR_ENCODING") from exc
        if (type(record) is not list or len(record) != 2
            or not _hash64(record[0]) or not _hash64(record[1])):
            raise TripwireHold("V1_BAD_NONCE_OR_ID")
        try:
            if canonical(record) != line:
                raise TripwireHold("V1_NONCANONICAL")
        except (ValueError, TypeError, UnicodeError) as exc:
            raise TripwireHold("V1_NONCANONICAL") from exc
        nonce, identifier = record
        if nonce in seen_nonce or identifier in seen_id:
            raise TripwireHold("V1_DUPLICATE_NONCE_OR_ID")
        seen_nonce.add(nonce)
        seen_id.add(identifier)
        rows.append(record)
    return rows


def compare_tripwire(
    *,
    v1_path: Path,
    v2_path: Path,
    in_memory_pairs: Any,
    broker_before: str,
    canonical: Callable[[Any], bytes],
    digest: Callable[[Any], str],
    spendv2: Any,
):
    """Pure compare of legacy/V2/memory append order and R60 sorted content.

    Call with V9's protocol.canonical, protocol.digest, spend_chain_v2 module.
    Returns reviewed V2 state on success; raises TripwireHold otherwise.
    No persistence, signature, retry or automatic reconciliation is performed.
    """
    raw_v1 = _read_bounded(Path(v1_path), MAX_V1_BYTES)
    raw_v2 = _read_bounded(Path(v2_path), MAX_V2_BYTES)
    v1_pairs = parse_v1(raw_v1, canonical=canonical)
    try:
        v2_state = spendv2.review(raw_v2)
    except Exception as exc:
        raise TripwireHold("V2_REVIEW_FAILED") from exc
    try:
        v2_pairs = [list(p) for p in v2_state.pairs]
    except (AttributeError, TypeError, ValueError) as exc:
        raise TripwireHold("V2_INVALID_PAIRS") from exc
    if not isinstance(in_memory_pairs, list) or in_memory_pairs != v1_pairs or v1_pairs != v2_pairs:
        raise TripwireHold("V1_DISK_V2_DISK_MEMORY_DIVERGENCE")
    if not _hash64(broker_before):
        raise TripwireHold("R60_BAD_BROKER_HASH")
    sorted_content = sorted(v1_pairs, key=lambda pair: pair[0])
    try:
        if digest(sorted_content) != broker_before:
            raise TripwireHold("R60_SORTED_CONTENT_MISMATCH")
        if spendv2.snapshot(v2_state.pairs) != broker_before:
            raise TripwireHold("V2_SORTED_CONTENT_MISMATCH")
    except TripwireHold:
        raise
    except Exception as exc:
        raise TripwireHold("SORTED_CONTENT_REVIEW_EXCEPTION") from exc
    return v2_state
