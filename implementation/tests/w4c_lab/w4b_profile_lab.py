"""Ario W4-B: isolated TEST-ONLY Ed25519 signed-byte-binding *laboratory*.

NO production authorization, trust-anchor enrollment, evidence admission, or truth.
The code can check bytes and a signature against *injected synthetic* public keys.
No network, ledger reads, secrets, keystore, credentials, M0 or RAC/ARP calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Callable, Mapping
import json
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

PROFILE = "ARIO-W4B-ED25519-ASCIIJSON-V0.1-TEST-ONLY"
DOMAIN = b"ARIO-W4B-SOURCE-ATTESTATION-V0.1-TEST\x00"
MAX_WIRE = 8192
MAX_PAYLOAD = 65536
MAX_PARENTS = 16
TOKEN = re.compile(r"[A-Za-z0-9._:/-]{1,128}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX128 = re.compile(r"[0-9a-f]{128}\Z")

ATTESTATION_KEYS = frozenset({
    "profile", "payload_sha256", "payload_byte_length", "event_namespace",
    "event_id", "event_type", "event_epoch", "claim_id", "claim_scope",
    "requested_use", "audience", "request_id", "witness_key_id", "source_id",
    "custodian_id", "control_group_id", "parent_refs",
})
TOKEN_KEYS = ATTESTATION_KEYS - {"payload_sha256", "payload_byte_length", "parent_refs", "profile"}
ALLOWED_USES = frozenset({"RECORD_DESCRIPTION", "INDEPENDENT_TARGET_SUPPORT"})


@dataclass(frozen=True)
class Context:
    """Independent-from-envelope *test assertions*, not a trusted production oracle."""
    event_namespace: str
    event_id: str
    event_type: str
    event_epoch: str
    claim_id: str
    claim_scope: str
    requested_use: str
    audience: str
    request_id: str


@dataclass(frozen=True)
class Outcome:
    status: str
    reason: str
    test_signature_check: str = "NOT_VERIFIED"
    byte_integrity_check: str = "NOT_VERIFIED"
    source_authentication: str = "UNKNOWN"
    source_independence: str = "UNKNOWN"
    reviewer_authorization: str = "UNKNOWN"
    admission_decision: str = "NOT_EVALUATED"
    claim_truth: str = "UNKNOWN"

    def __post_init__(self) -> None:
        if self.status not in ("UNKNOWN", "REJECTED"):
            raise ValueError("W4B CANNOT GRANT AUTHORITY OR ADMISSION")
        if (self.source_authentication != "UNKNOWN"
                or self.source_independence != "UNKNOWN"
                or self.reviewer_authorization != "UNKNOWN"
                or self.admission_decision != "NOT_EVALUATED"
                or self.claim_truth != "UNKNOWN"):
            raise ValueError("W4B STATUS PROMOTION FORBIDDEN")


def _pairs_no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _bad_constant(_value):
    raise ValueError("NONFINITE_NUMBER")


def canonical_attestation(attestation: dict) -> bytes:
    """A deliberately NARROW ASCII-token JSON test profile, NOT RFC 8785/JCS.

    Only ASCII identifiers + one bounded positive integer + sorted array of tokens.
    Hence there is no floating-point, Unicode normalization or arbitrary-string
    canonicalization ambiguity. This is an exact experimental profile only.
    """
    if type(attestation) is not dict or set(attestation) != ATTESTATION_KEYS:
        raise ValueError("FIELDS_OR_OBJECT_INVALID")
    if attestation["profile"] != PROFILE:
        raise ValueError("UNSUPPORTED_PROFILE")
    for name in TOKEN_KEYS:
        v = attestation[name]
        if type(v) is not str or TOKEN.fullmatch(v) is None:
            raise ValueError("INVALID_TOKEN:" + name)
    if attestation["requested_use"] not in ALLOWED_USES:
        raise ValueError("UNSUPPORTED_USE")
    if type(attestation["payload_sha256"]) is not str or HEX64.fullmatch(attestation["payload_sha256"]) is None:
        raise ValueError("INVALID_DIGEST")
    if type(attestation["payload_byte_length"]) is not int or not (1 <= attestation["payload_byte_length"] <= MAX_PAYLOAD):
        raise ValueError("INVALID_LENGTH")
    parents = attestation["parent_refs"]
    if (type(parents) is not list or len(parents) > MAX_PARENTS or
            any(type(s) is not str or TOKEN.fullmatch(s) is None for s in parents) or
            parents != sorted(set(parents))):
        raise ValueError("INVALID_PARENT_REFS")
    if type(attestation["witness_key_id"]) is not str or not attestation["witness_key_id"].startswith("sha256:"):
        raise ValueError("BAD_KEY_ID")
    # The pattern check above enforces the checksum after sha256: separately.
    # Special handling needed: token regex accepts ':' and max length 128.
    if HEX64.fullmatch(attestation["witness_key_id"][7:]) is None:
        raise ValueError("BAD_KEY_ID")
    return json.dumps(attestation, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def bytes_to_sign(attestation: dict) -> bytes:
    """Domain-separated *raw bytes* for test signing and verification."""
    return DOMAIN + canonical_attestation(attestation)


def public_key_id(public_key_bytes: bytes) -> str:
    if type(public_key_bytes) is not bytes or len(public_key_bytes) != 32:
        raise ValueError("PUBKEY_BYTES_REQUIRED")
    return "sha256:" + sha256(public_key_bytes).hexdigest()


def encode_wire(attestation: dict, signature: bytes) -> bytes:
    """Test fixture serializer only: never signs or generates a key."""
    canonical_attestation(attestation)
    if type(signature) is not bytes or len(signature) != 64:
        raise ValueError("ED25519_SIGNATURE_64_BYTES_REQUIRED")
    return (b'{"attestation":' + canonical_attestation(attestation) +
            b',"signature_hex":"' + signature.hex().encode("ascii") + b'"}')


def _load_wire(raw: bytes) -> tuple[dict, bytes]:
    if type(raw) is not bytes or len(raw) > MAX_WIRE or raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("INVALID_WIRE_BYTES")
    try:
        loaded = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_pairs_no_duplicates,
                            parse_constant=_bad_constant)
    except (UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ValueError("INVALID_JSON") from exc
    if type(loaded) is not dict or set(loaded) != {"attestation", "signature_hex"}:
        raise ValueError("INVALID_WIRE_FIELDS")
    a = loaded["attestation"]
    canonical_attestation(a)
    sig_hex = loaded["signature_hex"]
    if type(sig_hex) is not str or HEX128.fullmatch(sig_hex) is None:
        raise ValueError("INVALID_SIGNATURE_ENCODING")
    sig = bytes.fromhex(sig_hex)
    if encode_wire(a, sig) != raw:
        raise ValueError("NONCANONICAL_WIRE")
    return a, sig


def inspect(
    wire_bytes: bytes,
    read_payload_once: Callable[[], bytes],
    externally_supplied_test_keys: Mapping[str, bytes],
    expected: Context,
) -> Outcome:
    """Never returns a positive authority/status; test-only byte/crypto checks.

    An injected test public-key map does NOT constitute independently enrolled
    real-world identity or a genuine trust root. The reader is called at most once.
    """
    try:
        a, sig = _load_wire(wire_bytes)
    except (ValueError, TypeError) as exc:
        return Outcome("REJECTED", "W4B-WIRE-" + str(exc))
    if type(expected) is not Context:
        return Outcome("REJECTED", "W4B-EXPECTED_CONTEXT_REQUIRED")
    for k in ("event_namespace", "event_id", "event_type", "event_epoch", "claim_id",
              "claim_scope", "requested_use", "audience", "request_id"):
        if getattr(expected, k) != a[k]:
            return Outcome("REJECTED", "W4B-CONTEXT_MISMATCH:" + k)
    try:
        payload = read_payload_once()
    except Exception:
        return Outcome("UNKNOWN", "W4B-PAYLOAD_UNAVAILABLE")
    if type(payload) is not bytes or len(payload) > MAX_PAYLOAD or not payload:
        return Outcome("UNKNOWN", "W4B-PAYLOAD_MISSING_OR_OVERSIZED")
    if len(payload) != a["payload_byte_length"] or sha256(payload).hexdigest() != a["payload_sha256"]:
        return Outcome("REJECTED", "W4B-PAYLOAD_DIGEST_OR_LENGTH_MISMATCH")
    # Structural public-key lookup is always synthetic and EXTERNAL to signed wire.
    if type(externally_supplied_test_keys) is not dict:
        return Outcome("UNKNOWN", "W4B-NO_TEST_KEY_CONTEXT", byte_integrity_check="MATCHED")
    key = externally_supplied_test_keys.get(a["witness_key_id"])
    if key is None:
        return Outcome("UNKNOWN", "W4B-NO_ENROLLED_TEST_KEY", byte_integrity_check="MATCHED")
    try:
        if public_key_id(key) != a["witness_key_id"]:
            return Outcome("REJECTED", "W4B-MISMATCHED_TEST_KEY", byte_integrity_check="MATCHED")
        Ed25519PublicKey.from_public_bytes(key).verify(sig, bytes_to_sign(a))
    except (InvalidSignature, ValueError, TypeError):
        return Outcome("REJECTED", "W4B-INVALID_TEST_SIGNATURE", byte_integrity_check="MATCHED")
    return Outcome(
        "UNKNOWN", "W4B-SYNTHETIC_CRYPTO_ONLY_NO_INDEPENDENT_AUTHENTICATION",
        test_signature_check="VALID_UNDER_INJECTED_TEST_KEY", byte_integrity_check="MATCHED",
    )
