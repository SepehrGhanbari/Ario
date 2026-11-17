"""ARIO RESEARCH ONLY: signed-metadata inspection, NEVER execution authorization.

No signing API, mutable replay registry, key enrollment, privileged consumer,
production memory or trust activation. A caller-provided policy/pin/nonce set
is NOT proof of independent custody. This lab only tests cryptographic binding
and declared revocation under a synthetic, externally provided policy snapshot.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

PROFILE = "ARIO-READONLY-RECEIPT-LAB-0.1"
POLICY_VERSION = "ARIO-RECEIPT-POLICY-0.1"
ENVELOPE_VERSION = "ARIO-EXECUTION-ENVELOPE-0.1"
PAYLOAD_VERSION = "ARIO-EXECUTION-PAYLOAD-0.1"
SIGNATURE_DOMAIN = b"ARIO-RESEARCH-EXECUTION-RECEIPT-V0.1\x00"
MAX_ENVELOPE_BYTES = 4096
MAX_POLICY_BYTES = 2048
MAX_NONCES = 1024
MAX_AGE_SECONDS = 300
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_HEX128 = re.compile(r"[0-9a-f]{128}\Z")
_ID = re.compile(r"[a-zA-Z0-9._:-]{1,96}\Z")
_POLICY_KEYS = frozenset(("version", "key_id", "public_key_hex", "not_before_epoch", "not_after_epoch", "revoked", "purpose"))
_ENVELOPE_KEYS = frozenset(("version", "payload", "signature_hex"))
_PAYLOAD_KEYS = frozenset(("version", "key_id", "execution_id", "nonce", "tool", "request_sha256", "result_sha256", "exit_code", "observed_epoch"))

def _report(reason: str, *, signature_valid: bool = False, policy_pin_matches: bool = False, replay_seen: bool = False) -> dict[str, Any]:
    """Only inspection claims; all real authority remains false in *all* paths."""
    return {
        "profile": PROFILE,
        "inspection": "REVIEWABLE_ONLY" if reason == "SIGNED_METADATA_CHECKS_PASSED" else "UNKNOWN",
        "reason_code": reason,
        "signature_valid": signature_valid,
        "policy_pin_matches": policy_pin_matches,
        "replay_seen": replay_seen,
        "custody_independence": "NOT_ESTABLISHED",
        "executor_authorization": "NOT_ESTABLISHED",
        "execution_reality": "NOT_ESTABLISHED",
        "semantic_support": "NOT_ASSESSED",
        "claim_truth": "UNKNOWN",
        "evidence_admission_allowed": False,
        "memory_write_allowed": False,
        "tool_execution_allowed": False,
        "signing_allowed": False,
        "trust_activation_allowed": False,
    }

def _duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result

def _reject_number(_: str) -> None:
    raise ValueError("unsupported JSON numeric representation")

def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")

def _load(raw: bytes, bound: int) -> Any:
    if type(raw) is not bytes or not 0 < len(raw) <= bound:
        raise ValueError("invalid length/type")
    obj = json.loads(raw.decode("ascii"), object_pairs_hook=_duplicates, parse_float=_reject_number,
                     parse_constant=_reject_number, parse_int=lambda v: int(v) if len(v) <= 13 else _reject_number(v))
    if _canonical(obj) != raw:
        raise ValueError("noncanonical JSON")
    return obj

def _id(value: Any) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None

def _hex(value: Any, *, signature: bool = False) -> bool:
    return type(value) is str and (_HEX128 if signature else _HEX64).fullmatch(value) is not None

def _nonnegative_int(value: Any) -> bool:
    return type(value) is int and 0 <= value <= 10**12

def inspect_receipt(*, envelope_bytes: bytes, policy_bytes: bytes, expected_policy_sha256: str,
                    expected_request_sha256: str, expected_result_sha256: str,
                    spent_nonces: frozenset[str], now_epoch: int) -> dict[str, Any]:
    """Inspect metadata only. Every input, including the pin and replay set, is
    caller-supplied. REVIEWABLE_ONLY therefore NEVER authorizes evidence.
    """
    if (not all(_hex(s) for s in (expected_policy_sha256, expected_request_sha256, expected_result_sha256))
        or type(spent_nonces) is not frozenset or len(spent_nonces) > MAX_NONCES
        or any(not _id(v) for v in spent_nonces) or not _nonnegative_int(now_epoch)):
        return _report("INVALID_EXTERNAL_BINDINGS")
    try:
        policy, envelope = _load(policy_bytes, MAX_POLICY_BYTES), _load(envelope_bytes, MAX_ENVELOPE_BYTES)
    except (ValueError, UnicodeError, RecursionError, OverflowError, TypeError):
        return _report("MALFORMED_OR_NONCANONICAL_BYTES")
    if type(policy) is not dict or set(policy) != _POLICY_KEYS or policy.get("version") != POLICY_VERSION:
        return _report("INVALID_POLICY_CONTRACT")
    if (not _id(policy["key_id"]) or not _hex(policy["public_key_hex"]) or
        not _nonnegative_int(policy["not_before_epoch"]) or not _nonnegative_int(policy["not_after_epoch"]) or
        type(policy["revoked"]) is not bool or policy["purpose"] != "SYNTHETIC_RESEARCH_ONLY" or
        policy["not_before_epoch"] >= policy["not_after_epoch"]):
        return _report("INVALID_POLICY_FIELDS")
    if hashlib.sha256(policy_bytes).hexdigest() != expected_policy_sha256:
        return _report("EXTERNAL_POLICY_PIN_MISMATCH")
    if policy["revoked"]:
        return _report("DECLARED_KEY_REVOKED", policy_pin_matches=True)
    if not (policy["not_before_epoch"] <= now_epoch <= policy["not_after_epoch"]):
        return _report("POLICY_NOT_CURRENT", policy_pin_matches=True)
    if type(envelope) is not dict or set(envelope) != _ENVELOPE_KEYS or envelope.get("version") != ENVELOPE_VERSION:
        return _report("INVALID_ENVELOPE_CONTRACT", policy_pin_matches=True)
    payload = envelope["payload"]
    if type(payload) is not dict or set(payload) != _PAYLOAD_KEYS or payload.get("version") != PAYLOAD_VERSION:
        return _report("INVALID_PAYLOAD_CONTRACT", policy_pin_matches=True)
    if (not all(_id(payload[k]) for k in ("key_id", "execution_id", "nonce", "tool")) or
        not _hex(payload["request_sha256"]) or not _hex(payload["result_sha256"]) or
        type(payload["exit_code"]) is not int or not 0 <= payload["exit_code"] <= 255 or
        not _nonnegative_int(payload["observed_epoch"]) or not _hex(envelope["signature_hex"], signature=True)):
        return _report("INVALID_PAYLOAD_FIELDS", policy_pin_matches=True)
    if payload["key_id"] != policy["key_id"]:
        return _report("KEY_ID_MISMATCH", policy_pin_matches=True)
    if payload["nonce"] in spent_nonces:
        return _report("REPLAYED_NONCE_DECLARED", policy_pin_matches=True, replay_seen=True)
    if (not policy["not_before_epoch"] <= payload["observed_epoch"] <= now_epoch or
        now_epoch - payload["observed_epoch"] > MAX_AGE_SECONDS):
        return _report("EVENT_TIME_NOT_CURRENT", policy_pin_matches=True)
    try:
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(policy["public_key_hex"]))
        public_key.verify(bytes.fromhex(envelope["signature_hex"]), SIGNATURE_DOMAIN + _canonical(payload))
    except (ValueError, InvalidSignature):
        return _report("INVALID_SIGNATURE", policy_pin_matches=True)
    if (payload["request_sha256"] != expected_request_sha256 or
        payload["result_sha256"] != expected_result_sha256):
        return _report("EXTERNAL_CONTENT_BINDING_MISMATCH", signature_valid=True, policy_pin_matches=True)
    # A signed, self-supplied policy and pin are not evidence of independent custody.
    return _report("SIGNED_METADATA_CHECKS_PASSED", signature_valid=True, policy_pin_matches=True)
