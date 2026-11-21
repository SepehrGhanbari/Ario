"""W44 research-only conditional byte binding to a separately pinned checkpoint.

No claim of external key custody or real independent witness. The caller MUST
obtain and retain VerifierAnchor outside the writer's administrative authority;
this Python module cannot establish or enforce that real-world separation.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
from pathlib import Path
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from research.w38_receipt_fd_guard import read_bounded_regular

MAX_W44_BYTES = 8 * 1024 * 1024
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ARTIFACT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")


@dataclass(frozen=True)
class SignedPin:
    artifact_id: str
    sequence: int
    byte_length: int
    sha256: str
    signature: bytes


@dataclass(frozen=True)
class VerifierAnchor:
    """Verifier-retained exact floor; *not* evidence of separate custody by itself."""
    artifact_id: str
    sequence: int
    checkpoint_sha256: str
    public_key_bytes: bytes


def pin_payload(artifact_id: str, sequence: int, byte_length: int, sha256: str) -> bytes:
    """Domain-separated deterministic checkpoint bytes (public synthetic use)."""
    return b"ARIO-W44-SYNTHETIC-PIN-V1\x00" + json.dumps(
        {"artifact_id": artifact_id, "byte_length": byte_length,
         "sequence": sequence, "sha256": sha256, "version": 1},
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")


def checkpoint_hash(pin: SignedPin) -> str:
    return hashlib.sha256(pin_payload(pin.artifact_id, pin.sequence, pin.byte_length, pin.sha256)).hexdigest()


def verify_pinned_file(
    path: str | Path, *, pin: SignedPin, anchor: VerifierAnchor,
) -> dict:
    """Return a *byte-equivalence observation only*. Never authorize use.

    The independent authority for anchor is an external premise, not
    something this verifier learns from the pin or from local disk bytes.
    """
    def result(status: str, reason: str) -> dict:
        return {
            "status": status, "reason": reason, "may_use": False,
            "historical_event_truth": "UNKNOWN",
            "custody_independence": "NOT_ESTABLISHED",
            "evidence_admission": "NOT_EVALUATED",
        }

    if not isinstance(anchor, VerifierAnchor):
        return result("UNKNOWN", "VERIFIER_ANCHOR_REQUIRED")
    if not isinstance(pin, SignedPin):
        return result("UNKNOWN", "SIGNED_PIN_REQUIRED")
    if (type(anchor.artifact_id) is not str or not _ARTIFACT_ID.fullmatch(anchor.artifact_id)
            or type(anchor.sequence) is not int or anchor.sequence < 0
            or type(anchor.checkpoint_sha256) is not str
            or not _SHA256.fullmatch(anchor.checkpoint_sha256)
            or type(anchor.public_key_bytes) is not bytes
            or len(anchor.public_key_bytes) != 32):
        return result("UNKNOWN", "VERIFIER_ANCHOR_MALFORMED")
    if (type(pin.artifact_id) is not str or not _ARTIFACT_ID.fullmatch(pin.artifact_id)
            or type(pin.sequence) is not int or pin.sequence < 0
            or type(pin.byte_length) is not int
            or not 1 <= pin.byte_length <= MAX_W44_BYTES
            or type(pin.sha256) is not str or not _SHA256.fullmatch(pin.sha256)
            or type(pin.signature) is not bytes or len(pin.signature) != 64):
        return result("UNKNOWN", "SIGNED_PIN_MALFORMED")
    if pin.artifact_id != anchor.artifact_id:
        return result("UNKNOWN", "ARTIFACT_BINDING_MISMATCH")
    if pin.sequence != anchor.sequence:
        return result("UNKNOWN", "CHECKPOINT_NOT_AT_VERIFIER_FLOOR")
    payload = pin_payload(pin.artifact_id, pin.sequence, pin.byte_length, pin.sha256)
    if not hmac.compare_digest(hashlib.sha256(payload).hexdigest(), anchor.checkpoint_sha256):
        return result("UNKNOWN", "CHECKPOINT_NOT_AT_VERIFIER_FLOOR")
    try:
        Ed25519PublicKey.from_public_bytes(anchor.public_key_bytes).verify(pin.signature, payload)
    except (InvalidSignature, ValueError):
        return result("UNKNOWN", "CHECKPOINT_SIGNATURE_UNTRUSTED")

    try:
        observed = read_bounded_regular(Path(path), MAX_W44_BYTES)
    except (OSError, ValueError):
        return result("UNKNOWN", "BOUNDED_INPUT_READ_REJECTED")
    if type(observed) is not bytes or len(observed) != pin.byte_length:
        return result("UNKNOWN", "INPUT_LENGTH_MISMATCH")
    actual_sha256 = hashlib.sha256(observed).hexdigest()
    if not hmac.compare_digest(actual_sha256, pin.sha256):
        return result("UNKNOWN", "INPUT_DIGEST_MISMATCH")
    return result("PIN_MATCH_ONLY", "EXACT_BYTES_MATCH_VERIFIER_ANCHOR")
