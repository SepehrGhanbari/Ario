"""Ario R2 D9: offline, non-authoritative checkpoint/floor consistency lab.

RESEARCH_ONLY. Inputs, even public keys, are supplied by the caller: no
independently enrolled custodian, remote read, trusted time, or independent
floor is established. A positive LAB diagnostic is NEVER evidence admission.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

EVENT = b"ARIO-R2-D9-EVENT-V1\x00"
FLOOR = b"ARIO-R2-D9-FLOOR-V1\x00"
HEAD = b"ARIO-R2-D9-HEAD-V1\x00"
ROTATION = b"ARIO-R2-D9-ROTATION-V1\x00"
ZERO = "0" * 64
HEX = re.compile(r"[0-9a-f]{64}\Z")
EVENT_FIELDS = {"schema", "sequence", "prev", "kind", "state_sha256", "revocation_tip", "observer_pin", "epoch"}
FLOOR_FIELDS = {"schema", "sequence", "event_hash", "revocation_tip", "observer_pin", "epoch"}
HEAD_FIELDS = {"schema", "sequence", "event_hash", "revocation_tip", "observer_pin", "epoch", "nonce"}


@dataclass(frozen=True)
class Signed:
    body: bytes
    signature: bytes
    rotation_signature: bytes | None = None


@dataclass(frozen=True)
class LabPins:
    custodian_key: bytes
    floor_key: bytes
    rotation_key: bytes
    fresh_nonce: str
    # This field is a label, not independently authenticated origin.
    source_basis: str = "LAB_SUPPLIED"


def canonical(o: dict) -> bytes:
    return json.dumps(o, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def digest(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def event_digest(e: Signed) -> str:
    return digest(EVENT + e.body + e.signature + (e.rotation_signature or b""))


def _object(raw: bytes, fields: set[str], schema: str) -> dict | None:
    if type(raw) is not bytes or len(raw) > 1024:
        return None
    try:
        def unique(pairs):
            result = {}
            for k, v in pairs:
                if k in result:
                    raise ValueError("duplicate JSON key")
                result[k] = v
            return result
        o = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
        if type(o) is not dict or set(o) != fields or o.get("schema") != schema or canonical(o) != raw:
            return None
        return o
    except (UnicodeError, TypeError, ValueError, OverflowError, RecursionError):
        return None


def _sig(pub: bytes, signed: Signed, domain: bytes) -> bool:
    if (type(pub) is not bytes or len(pub) != 32 or type(signed) is not Signed or
        type(signed.body) is not bytes or len(signed.body) > 1024 or
        type(signed.signature) is not bytes or len(signed.signature) != 64):
        return False
    try:
        Ed25519PublicKey.from_public_bytes(pub).verify(signed.signature, domain + signed.body)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def _rotation(pub: bytes, item: Signed) -> bool:
    if type(item.rotation_signature) is not bytes or len(item.rotation_signature) != 64:
        return False
    try:
        Ed25519PublicKey.from_public_bytes(pub).verify(item.rotation_signature, ROTATION + item.body)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def _hex(x: object) -> bool:
    return type(x) is str and bool(HEX.fullmatch(x))


def _num(x: object, lower: int, upper: int = 128) -> bool:
    return type(x) is int and lower <= x <= upper


def _valid_snapshot(o: dict) -> bool:
    return (_num(o.get("sequence"), 1) and _num(o.get("epoch"), 1) and
            all(_hex(o.get(k)) for k in ("event_hash", "revocation_tip", "observer_pin")))


def _out(reason: str, *, lab: str = "NONE", history: str = "UNKNOWN") -> dict:
    return {"schema": "ARIO-R2-D9-RESULT-V1", "status": "UNKNOWN",
            "claim_truth": "UNKNOWN", "evidence_admission": "NOT_EVALUATED",
            "real_world_custody": "NOT_ESTABLISHED", "external_enrollment": "NOT_ESTABLISHED",
            "actual_remote_read": "NOT_RUN", "independently_retained_floor": "NOT_ESTABLISHED",
            "remote_freshness": "NOT_ESTABLISHED", "trusted_time": "NOT_ESTABLISHED",
            "original_github_execution": "NOT_ESTABLISHED", "undisclosed_fork_absence": "NOT_ESTABLISHED",
            "unobserved_revocation_absence": "NOT_ESTABLISHED",
            "history_diagnostic": history, "lab_diagnostic": lab, "reason": reason}


def evaluate(history: tuple[Signed, ...], head: Signed, floor: Signed,
             pins: LabPins, alternative_head: Signed | None = None) -> dict:
    """Compare *supplied* signed bytes. Never read a network or mutate a floor."""
    if (type(pins) is not LabPins or pins.source_basis != "LAB_SUPPLIED" or
        not all(type(k) is bytes and len(k) == 32 for k in (pins.custodian_key, pins.floor_key, pins.rotation_key)) or
        len({pins.custodian_key, pins.floor_key, pins.rotation_key}) != 3 or
        type(pins.fresh_nonce) is not str or not re.fullmatch(r"[0-9a-f]{32}", pins.fresh_nonce)):
        return _out("MISSING_OR_INVALID_LAB_PINS")
    if type(history) is not tuple or not (1 <= len(history) <= 128):
        return _out("MISSING_OR_UNBOUNDED_HISTORY")
    if (type(floor) is not Signed or type(head) is not Signed or
        floor.rotation_signature is not None or head.rotation_signature is not None or
        not (_sig(pins.floor_key, floor, FLOOR) and _sig(pins.custodian_key, head, HEAD))):
        return _out("FLOOR_OR_HEAD_SIGNATURE_INVALID")
    f = _object(floor.body, FLOOR_FIELDS, "ARIO-R2-D9-FLOOR-V1")
    h = _object(head.body, HEAD_FIELDS, "ARIO-R2-D9-HEAD-V1")
    if not (f and h and _valid_snapshot(f) and _valid_snapshot(h) and
            type(h.get("nonce")) is str and h["nonce"] == pins.fresh_nonce):
        return _out("FLOOR_HEAD_OR_CHALLENGE_INVALID")
    prev = ZERO
    prev_rev = ZERO
    prev_pin = None
    prev_epoch = None
    observed = []
    for index, item in enumerate(history, 1):
        if not _sig(pins.custodian_key, item, EVENT):
            return _out("EVENT_SIGNATURE_INVALID")
        o = _object(item.body, EVENT_FIELDS, "ARIO-R2-D9-EVENT-V1")
        if (o is None or not _num(o.get("sequence"), 1) or not _num(o.get("epoch"), 1) or
            not all(_hex(o.get(k)) for k in ("prev", "state_sha256", "revocation_tip", "observer_pin")) or
            o.get("kind") not in ("STATE", "REVOKE", "OBSERVER_ROTATE", "ROOT_ROTATE") or
            o["sequence"] != index or o["prev"] != prev):
            return _out("GAP_NONCANONICAL_OR_HASH_CHAIN_CONFLICT")
        if o["kind"] == "ROOT_ROTATE":
            return _out("CUSTODIAN_ROOT_ROTATION_REQUIRES_OOB_REENROLLMENT")
        if index == 1:
            if o["kind"] != "STATE" or o["revocation_tip"] != ZERO or o["epoch"] != 1 or item.rotation_signature is not None:
                return _out("BAD_GENESIS")
        else:
            if o["kind"] == "REVOKE":
                if o["revocation_tip"] == prev_rev or o["observer_pin"] != prev_pin or o["epoch"] != prev_epoch or item.rotation_signature is not None:
                    return _out("INVALID_REVOCATION_TRANSITION")
            elif o["kind"] == "OBSERVER_ROTATE":
                if (o["observer_pin"] == prev_pin or o["revocation_tip"] != prev_rev or
                    o["epoch"] != prev_epoch + 1 or not _rotation(pins.rotation_key, item)):
                    return _out("UNAUTHORIZED_OBSERVER_ROTATION")
            else:
                if o["revocation_tip"] != prev_rev or o["observer_pin"] != prev_pin or o["epoch"] != prev_epoch or item.rotation_signature is not None:
                    return _out("SILENT_REVOCATION_OR_KEY_CHANGE")
        if o["kind"] != "OBSERVER_ROTATE" and item.rotation_signature is not None:
            return _out("UNEXPECTED_ROTATION_AUTHORITY")
        prev_rev, prev_pin, prev_epoch = o["revocation_tip"], o["observer_pin"], o["epoch"]
        prev = event_digest(item)
        observed.append((prev, o))
    if f["sequence"] > len(observed):
        return _out("ROLLBACK_BELOW_PROTECTED_FLOOR", history="BELOW_FLOOR")
    floor_hash, floor_event = observed[f["sequence"] - 1]
    if floor_hash != f["event_hash"] or any(f[k] != floor_event[k] for k in ("revocation_tip", "observer_pin", "epoch")):
        return _out("FORK_OR_REVOCATION_VS_PROTECTED_FLOOR", history="FORK_VS_FLOOR")
    tip_hash, tip = observed[-1]
    if h["sequence"] != len(history) or h["event_hash"] != tip_hash or any(h[k] != tip[k] for k in ("revocation_tip", "observer_pin", "epoch")):
        return _out("HEAD_MISMATCH_OR_WITHHELD_COMMITTED_EVENT")
    if alternative_head is not None:
        if (type(alternative_head) is not Signed or alternative_head.rotation_signature is not None or
            not _sig(pins.custodian_key, alternative_head, HEAD)):
            return _out("ALTERNATIVE_HEAD_SIGNATURE_INVALID")
        alt = _object(alternative_head.body, HEAD_FIELDS, "ARIO-R2-D9-HEAD-V1")
        if not (alt and _valid_snapshot(alt) and alt.get("nonce") == pins.fresh_nonce):
            return _out("ALTERNATIVE_HEAD_INVALID")
        if alt["sequence"] > len(observed):
            return _out("NEWER_SIGNED_VIEW_WAS_WITHHELD", history="STALE_RELATIVE_TO_VIEW")
        known_hash, known_obj = observed[alt["sequence"] - 1]
        if alt["event_hash"] != known_hash or any(alt[k] != known_obj[k] for k in ("revocation_tip", "observer_pin", "epoch")):
            return _out("VISIBLE_SIGNED_EQUIVOCATION", history="FORK_OBSERVED")
    return _out("LAB_HISTORY_AND_SIGNED_FLOOR_CONSISTENT_NOT_FRESHNESS",
                lab="LAB_CONSISTENT_ONLY", history="MATCHES_SUPPLIED_FLOOR")
