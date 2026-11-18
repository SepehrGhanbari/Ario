"""W08 read-only verifier for *preexisting* W22 SYNTHETIC signed log notes.

No signing, key generation, remote calls, state changes or trust activation.
This is intentionally NOT a witness cosignature verifier; W27 already tests
synthetic cosignatures and we do not repeat or upgrade those claims.
"""
from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

_VKEY = re.compile(r"^([^+\s]{1,250})\+([0-9a-f]{8})\+([A-Za-z0-9+/]+={0,2})$")
_COUNT = re.compile(rb"^[1-9][0-9]{0,6}$")
_B64 = re.compile(rb"^[A-Za-z0-9+/]+={0,2}$")


@dataclass(frozen=True)
class Head:
    origin: str
    size: int
    root: bytes
    signature_bytes_sha256: str
    note_sha256: str


def _b64_canonical(value: bytes, *, max_length: int) -> bytes:
    if not value or len(value) > 2 * max_length or not _B64.fullmatch(value):
        raise ValueError("invalid base64 format")
    decoded = base64.b64decode(value, validate=True)
    if len(decoded) > max_length or base64.b64encode(decoded) != value:
        raise ValueError("noncanonical base64")
    return decoded


def verify_log_note(note: bytes, supplied_vkey: str, expected_origin: str) -> Head | None:
    """Check exact format + Ed25519 signature of a W22 C2SP-note subset.

    The public key is *supplied by the caller*, not OOB-authenticated.
    """
    if (type(note) is not bytes or not note or len(note) > 4096 or
            type(supplied_vkey) is not str or len(supplied_vkey) > 390 or
            type(expected_origin) is not str or not expected_origin or
            len(expected_origin) > 250):
        return None
    try:
        v = _VKEY.fullmatch(supplied_vkey)
        if not v:
            return None
        vname, key_id, b64pub = v.groups()
        if vname != expected_origin:
            return None
        raw_pub = _b64_canonical(b64pub.encode("ascii"), max_length=33)
        if len(raw_pub) != 33 or raw_pub[0] != 1:
            return None
        kid = hashlib.sha256(vname.encode("utf-8") + b"\n" + raw_pub).digest()[:4]
        if kid.hex() != key_id:
            return None
        pieces = note.split(b"\n\n")
        if len(pieces) != 2 or not pieces[1].endswith(b"\n"):
            return None
        signed_content = pieces[0] + b"\n"
        lines = signed_content.split(b"\n")
        if (len(lines) != 4 or lines[-1] != b"" or
                lines[0].decode("utf-8") != expected_origin or
                not _COUNT.fullmatch(lines[1])):
            return None
        size = int(lines[1])
        if not 1 <= size <= 10000:
            return None
        root = _b64_canonical(lines[2], max_length=32)
        if len(root) != 32:
            return None
        sig_prefix = ("— " + vname + " ").encode("utf-8")
        line = pieces[1]
        if not line.startswith(sig_prefix) or line.count(b"\n") != 1:
            return None
        sig = _b64_canonical(line[len(sig_prefix):-1], max_length=68)
        if len(sig) != 68 or sig[:4] != kid:
            return None
        Ed25519PublicKey.from_public_bytes(raw_pub[1:]).verify(sig[4:], signed_content)
        return Head(expected_origin, size, root,
                    hashlib.sha256(sig).hexdigest(), hashlib.sha256(note).hexdigest())
    except (ValueError, InvalidSignature, UnicodeError, OverflowError, TypeError):
        return None


def read_only_assess(candidate: bytes, *, log_public_key: str,
                     origin: str, local_retained: bytes | None = None,
                     submitted_claims: dict | None = None) -> dict:
    """Crypto-only result; never admits external witness/admin/trust authority."""
    base = {
        "status": "HOLD_NO_EXTERNAL_TRUST",
        "scope": "ARIO_W08_LOG_NOTE_ONLY_RESEARCH_V1",
        "log_note_crypto": "NOT_VERIFIED",
        "external_witness_cosignature": "NOT_PRESENT_OR_VERIFIED",
        "oob_key_pin": "NOT_ESTABLISHED",
        "independent_operator_custody": "NOT_ESTABLISHED",
        "external_monitor_highwater": "NOT_ESTABLISHED",
        "world_freshness": "UNKNOWN",
        "source_completeness": "UNKNOWN",
        "authority": "NONE",
        "trust_activation": "NO_GO",
        "production": "NO_GO",
        "external_actions": 0,
        "signatures_issued": 0,
    }
    # Claims are deliberately inert even if they contain arbitrary booleans,
    # stale timestamps, a hundred witness IDs, or nested OOB provenance labels.
    _ = submitted_claims
    head = verify_log_note(candidate, log_public_key, origin)
    if head is None:
        return {**base, "decision": "HOLD_INVALID_OR_UNPINNED_LOG_NOTE"}
    base["log_note_crypto"] = "VALID_FOR_CALLER_SUPPLIED_KEY_ONLY"
    base["current_head"] = {"size": head.size, "root": head.root.hex(),
                            "note_sha256": head.note_sha256}
    if local_retained is None:
        return {**base, "decision": "HOLD_NO_PREVIOUSLY_RETAINED_REFERENCE"}
    old = verify_log_note(local_retained, log_public_key, origin)
    if old is None:
        return {**base, "decision": "HOLD_INVALID_RETAINED_REFERENCE"}
    if head.size < old.size:
        return {**base, "decision": "HOLD_OLD_VIEW_RELATIVE_TO_LOCAL_REFERENCE"}
    if head.size == old.size and head.root != old.root:
        return {**base, "decision": "CONFLICT_SAME_SIGNER_SAME_SIZE_DIFFERENT_ROOT",
                "retained_note_sha256": old.note_sha256,
                "candidate_note_sha256": head.note_sha256}
    if head.size == old.size:
        return {**base, "decision": "HISTORICAL_MATCH_NOT_WORLD_FRESHNESS"}
    return {**base, "decision": "HOLD_GROWTH_WITHOUT_CONSISTENCY_PROOF"}
