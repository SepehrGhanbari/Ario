"""Ario: read-only research inspector for declared key/revocation/nonce history.

This experiment authenticates NO custodian, administrator, witness or storage.
The caller provides both journal bytes and the alleged external anchor/floor.
A valid hash chain is merely structural integrity, NOT independent custody.
No write, signer, network access, key enrollment or production state change.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

PROFILE = "ARIO-DECLARED-AUTHORITY-HISTORY-LAB-0.1"
RECORD_VERSION = "ARIO-AUTHORITY-HISTORY-RECORD-0.1"
DOMAIN = b"ARIO-RESEARCH-AUTHORITY-HISTORY-V0.1\x00"
MAX_BYTES = 32768
MAX_RECORD_BYTES = 512
MAX_RECORDS = 64
GENESIS = "0" * 64
_FIELDS = frozenset(("version", "sequence", "previous_sha256", "kind", "key_id", "nonce", "policy_sha256"))
_KINDS = frozenset(("KEY_ENROLLED", "KEY_REVOKED", "NONCE_SPENT"))
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9._:-]{1,96}\Z")


def _hash(line: bytes) -> str:
    return hashlib.sha256(DOMAIN + line).hexdigest()


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in items:
        if k in out:
            raise ValueError("DUPLICATE_JSON_KEY")
        out[k] = v
    return out


def _bad_number(_: str) -> None:
    raise ValueError("INVALID_JSON_NUMBER")


def _sha(v: Any) -> bool:
    return type(v) is str and _SHA.fullmatch(v) is not None


def _id(v: Any) -> bool:
    return type(v) is str and _ID.fullmatch(v) is not None


def _report(reason: str, *, count: int = 0, head: str = GENESIS,
            floor_matches: bool = False, head_matches: bool = False,
            key_declared_active: bool = False, nonce_declared_spent: bool = False) -> dict[str, Any]:
    return {
        "profile": PROFILE,
        "inspection": "REVIEWABLE_ONLY" if reason == "DECLARED_HISTORY_CONSISTENT" else "UNKNOWN",
        "reason_code": reason,
        "record_count": count,
        "computed_head_sha256": head,
        "declared_floor_matches": floor_matches,
        "declared_head_matches": head_matches,
        "key_declared_active": key_declared_active,
        "nonce_declared_spent": nonce_declared_spent,
        "custody_independence": "NOT_ESTABLISHED",
        "policy_origin_authenticated": False,
        "revocation_source_authenticated": False,
        "nonce_history_durability": "NOT_ESTABLISHED",
        "authority_granted": False,
        "memory_write_allowed": False,
        "evidence_admission_allowed": False,
        "signing_allowed": False,
        "trust_activation_allowed": False,
    }


def inspect_declared_history(*, journal_bytes: bytes, expected_head_sha256: str,
                             floor_sequence: int, floor_sha256: str,
                             requested_key_id: str, expected_policy_sha256: str,
                             requested_nonce: str) -> dict[str, Any]:
    """Check bounded hash-chain consistency against caller-provided external pins.

    Even a perfect chain and pin match authorize nothing. The caller can invent
    a complete fork, update both 'external' pins, and claim a new identity.
    """
    if (not _sha(expected_head_sha256) or not _sha(floor_sha256) or
        not _sha(expected_policy_sha256) or not _id(requested_key_id) or
        not _id(requested_nonce) or type(floor_sequence) is not int or
        not 0 <= floor_sequence <= MAX_RECORDS or
        (floor_sequence == 0 and floor_sha256 != GENESIS)):
        return _report("INVALID_EXTERNAL_BINDINGS")
    if (type(journal_bytes) is not bytes or not 0 < len(journal_bytes) <= MAX_BYTES
        or not journal_bytes.endswith(b"\n")):
        return _report("INVALID_HISTORY_BYTES")
    lines = journal_bytes.split(b"\n")[:-1]
    if not 0 < len(lines) <= MAX_RECORDS:
        return _report("INVALID_RECORD_COUNT")
    active: dict[str, str] = {}
    revoked: set[str] = set()
    nonces: set[str] = set()
    previous = GENESIS
    floor_matched = floor_sequence == 0
    for pos, line in enumerate(lines, 1):
        if not 0 < len(line) <= MAX_RECORD_BYTES:
            return _report("INVALID_RECORD_LENGTH", count=pos - 1, head=previous)
        try:
            item = json.loads(line.decode("ascii"), object_pairs_hook=_pairs,
                              parse_float=_bad_number, parse_constant=_bad_number,
                              parse_int=lambda v: int(v) if len(v) <= 5 else _bad_number(v))
            if (type(item) is not dict or set(item) != _FIELDS or
                json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii") != line):
                return _report("NONCANONICAL_RECORD", count=pos - 1, head=previous)
        except (ValueError, UnicodeError, TypeError, OverflowError, RecursionError):
            return _report("INVALID_RECORD_ENCODING", count=pos - 1, head=previous)
        if (item["version"] != RECORD_VERSION or type(item["sequence"]) is not int
            or not _sha(item["previous_sha256"]) or not _id(item["key_id"])
            or type(item["kind"]) is not str or item["kind"] not in _KINDS
            or not _sha(item["policy_sha256"])
            or (item["nonce"] is not None and not _id(item["nonce"]))):
            return _report("INVALID_RECORD_FIELDS", count=pos - 1, head=previous)
        if item["sequence"] != pos:
            return _report("SEQUENCE_DISCONTINUITY", count=pos - 1, head=previous)
        if item["previous_sha256"] != previous:
            return _report("CHAIN_LINK_MISMATCH", count=pos - 1, head=previous)
        key, policy, nonce, kind = item["key_id"], item["policy_sha256"], item["nonce"], item["kind"]
        if kind == "KEY_ENROLLED":
            if nonce is not None or key in active or key in revoked:
                return _report("DUPLICATE_OR_REVOKED_ENROLLMENT", count=pos - 1, head=previous)
            active[key] = policy
        elif kind == "KEY_REVOKED":
            if nonce is not None or key not in active or key in revoked or active[key] != policy:
                return _report("INVALID_REVOCATION", count=pos - 1, head=previous)
            revoked.add(key)
        elif kind == "NONCE_SPENT":
            if nonce is None or key not in active or key in revoked or active[key] != policy:
                return _report("INVALID_NONCE_SPEND", count=pos - 1, head=previous)
            if nonce in nonces:
                return _report("DUPLICATE_NONCE_SPEND", count=pos - 1, head=previous)
            nonces.add(nonce)
        previous = _hash(line)
        if floor_sequence == pos:
            floor_matched = previous == floor_sha256
            if not floor_matched:
                return _report("EXTERNAL_FLOOR_MISMATCH", count=pos, head=previous)
    if floor_sequence > len(lines):
        return _report("HISTORY_BELOW_DECLARED_FLOOR", count=len(lines), head=previous)
    if previous != expected_head_sha256:
        return _report("EXTERNAL_HEAD_MISMATCH", count=len(lines), head=previous,
                       floor_matches=floor_matched)
    if requested_key_id not in active or active[requested_key_id] != expected_policy_sha256:
        return _report("KEY_OR_POLICY_NOT_DECLARED", count=len(lines), head=previous,
                       floor_matches=floor_matched, head_matches=True)
    if requested_key_id in revoked:
        return _report("DECLARED_KEY_REVOKED", count=len(lines), head=previous,
                       floor_matches=floor_matched, head_matches=True)
    if requested_nonce in nonces:
        return _report("DECLARED_NONCE_SPENT", count=len(lines), head=previous,
                       floor_matches=floor_matched, head_matches=True,
                       key_declared_active=True, nonce_declared_spent=True)
    return _report("DECLARED_HISTORY_CONSISTENT", count=len(lines), head=previous,
                   floor_matches=floor_matched, head_matches=True, key_declared_active=True)
