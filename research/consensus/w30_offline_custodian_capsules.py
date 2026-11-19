#!/usr/bin/env python3
"""W30: strict offline research capsule chain for a FUTURE external keeper.

CUSTOM 'ARIO-W30-RESEARCH' signatures ARE NOT C2SP cosignatures, not
independently authenticated operator credentials, and not external custody.
Verify original W22 C2SP signed notes with W23; verify this *separate*
research-only receipt chain with Ed25519 using explicit caller-provided pins.
NO signing function, filesystem access, network or Ario trust/memory authority.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from w23_checkpoint_gossip import read_signed_note, verify_compact_consistency

SCHEMA = "ARIO_W30_RESEARCH_CUSTODIAN_CAPSULE_V1"
RECORD_SCHEMA = "ARIO_W30_RESEARCH_RECORD_V1"
SIGN_DOMAIN = b"ARIO-W30-RESEARCH-CAPSULE-V1\n"
ROTATE_DOMAIN = b"ARIO-W30-RESEARCH-KEY-ACCEPT-V1\n"
ORIGIN = "ario-w22-research.invalid/synthetic-log"
HEX = re.compile(r"[0-9a-f]{64}\Z")
B64 = re.compile(r"[A-Za-z0-9+/]+={0,2}\Z")
RECORD_FIELDS = frozenset((
    "schema","seq","prev_hash","event","origin","checkpoint_b64",
    "consistency_proof","observed_at","operator_claim",
    "next_key_b64","revoked_key_sha256"
))
CAPSULE_FIELDS = frozenset(("record","signature_b64","rotation_acceptance_b64"))
FLOOR_FIELDS = frozenset(("seq","capsule_sha256"))
MAX_RECORDS = 32


def canonical(obj):
    """Canonical solely for this bounded research schema. Not general JCS."""
    return json.dumps(obj, sort_keys=True, separators=(",",":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _b64(value, exact):
    if type(value) is not str or len(value) > 8192 or not B64.fullmatch(value):
        raise ValueError("invalid base64")
    raw = base64.b64decode(value, validate=True)
    if len(raw) != exact or base64.b64encode(raw).decode("ascii") != value:
        raise ValueError("noncanonical base64 or wrong length")
    return raw


def _note(value):
    if type(value) is not str or len(value)>8192 or not B64.fullmatch(value):
        raise ValueError("invalid signed note encoding")
    raw=base64.b64decode(value,validate=True)
    if len(raw)>4096 or base64.b64encode(raw).decode("ascii")!=value:
        raise ValueError("noncanonical or oversized note")
    return raw


def _result(reason, **extra):
    result = dict(
        status="HOLD", reason=reason, production="NO_GO",
        trust_activation="NO_GO", genesis="NO_GO", authority="NONE",
        memory_admitted=False, signatures_issued=0, external_actions=0,
        cryptographic_chain="NOT_VERIFIED",
        external_key_provenance="NOT_ESTABLISHED",
        independently_administered_custody="NOT_ESTABLISHED",
        external_retained_floor="NOT_ESTABLISHED",
        source_truth="UNKNOWN", world_freshness="UNKNOWN",
    )
    # Allow detailed crypto diagnostics to replace only diagnostic fields.
    # Never let caller-controlled fields override trust/authority/no-go labels.
    allowed = {"cryptographic_chain","chain_length","latest_seq",
               "latest_capsule_sha256","last_signed_checkpoint_size",
               "last_signed_checkpoint_root","rotations_checked",
               "revocation_seen","floor_binding","final_active_key_sha256",
               "at","floor_sequence"}
    if not set(extra).issubset(allowed):
        return dict(result, reason="UNEXPECTED_DIAGNOSTIC_FIELD")
    result.update(extra)
    return result


def verify_chain(capsules, *, pinned_initial_key_b64, pinned_log_vkey,
                 as_of, floor=None):
    """Verify a supplied research chain. A supplied floor has NO OOB authenticity."""
    if (type(capsules) is not list or not 1<=len(capsules)<=MAX_RECORDS
        or type(pinned_initial_key_b64) is not str
        or type(pinned_log_vkey) is not str or not 0<len(pinned_log_vkey)<=380
        or type(as_of) is not int or not 1_000_000_000<as_of<5_000_000_000):
        return _result("INVALID_ENVELOPE_OR_LIMITS")
    if floor is not None and (
        type(floor) is not dict or set(floor)!=FLOOR_FIELDS
        or type(floor["seq"]) is not int or floor["seq"]<1
        or type(floor["capsule_sha256"]) is not str
        or HEX.fullmatch(floor["capsule_sha256"]) is None
    ):
        return _result("MALFORMED_CALLER_SUPPLIED_FLOOR")
    try:
        active_key=_b64(pinned_initial_key_b64,32)
        Ed25519PublicKey.from_public_bytes(active_key)
    except (ValueError,TypeError,binascii.Error):
        return _result("INVALID_PINNED_INITIAL_KEY")
    used_keys={active_key}
    previous_hash="0"*64
    last_head=None
    last_time=None
    revoked=False
    rotations=0
    hashes=[]
    for index,cap in enumerate(capsules,1):
        if type(cap) is not dict or set(cap)!=CAPSULE_FIELDS:
            return _result("MALFORMED_CAPSULE", at=index)
        record=cap["record"]
        if type(record) is not dict or set(record)!=RECORD_FIELDS:
            return _result("MALFORMED_RECORD", at=index)
        if (record["schema"]!=RECORD_SCHEMA
            or type(record["seq"]) is not int or record["seq"]!=index
            or type(record["prev_hash"]) is not str
            or record["prev_hash"]!=previous_hash
            or type(record["origin"]) is not str or record["origin"]!=ORIGIN
            or record["event"] not in ("OBSERVE","ROTATE","REVOKE")
            or type(record["observed_at"]) is not int
            or not 1_000_000_000<record["observed_at"]<=as_of+300
            or last_time is not None and record["observed_at"]<last_time
            or type(record["operator_claim"]) is not str
            or not 1<=len(record["operator_claim"])<=255
            or type(record["consistency_proof"]) is not list
            or len(record["consistency_proof"])>16
            or any(type(n) is not str or HEX.fullmatch(n) is None
                   for n in record["consistency_proof"])):
            return _result("INVALID_SEQUENCE_PREV_OR_METADATA",at=index)
        if revoked:
            return _result("EVENT_AFTER_SIGNED_REVOCATION",at=index)
        try:
            body_bytes=canonical(record)
            sig=_b64(cap["signature_b64"],64)
            Ed25519PublicKey.from_public_bytes(active_key).verify(
                sig,SIGN_DOMAIN+body_bytes
            )
        except (InvalidSignature,TypeError,ValueError,binascii.Error,OverflowError):
            return _result("INVALID_CAPSULE_SIGNATURE",at=index)
        event=record["event"]
        if event=="OBSERVE":
            if (record["next_key_b64"] is not None
                or record["revoked_key_sha256"] is not None
                or cap["rotation_acceptance_b64"] is not None):
                return _result("OBSERVE_HAS_FORBIDDEN_CONTROL_FIELDS",at=index)
            try:
                note=_note(record["checkpoint_b64"])
            except (ValueError,TypeError,binascii.Error):
                return _result("INVALID_CHECKPOINT_BASE64",at=index)
            candidate=read_signed_note(note,pinned_log_vkey,origin=ORIGIN)
            if candidate is None:
                return _result("INVALID_SIGNED_LOG_CHECKPOINT",at=index)
            if last_head is None:
                if record["consistency_proof"]:
                    return _result("GENESIS_PROOF_MUST_BE_EMPTY",at=index)
            elif not verify_compact_consistency(
                last_head["size"],candidate["size"],last_head["root"],
                candidate["root"],record["consistency_proof"]
            ):
                return _result("CHECKPOINT_ROLLBACK_OR_FORK",at=index)
            last_head=candidate
        elif event=="ROTATE":
            if (last_head is None or record["checkpoint_b64"] is not None
                or record["consistency_proof"]
                or record["revoked_key_sha256"] is not None):
                return _result("ROTATION_HAS_INVALID_FIELDS_OR_NO_HEAD",at=index)
            try:
                next_key=_b64(record["next_key_b64"],32)
                acceptance=_b64(cap["rotation_acceptance_b64"],64)
                Ed25519PublicKey.from_public_bytes(next_key).verify(
                    acceptance,
                    ROTATE_DOMAIN+hashlib.sha256(body_bytes).digest()
                )
            except (InvalidSignature,TypeError,ValueError,binascii.Error):
                return _result("MISSING_OR_INVALID_NEW_KEY_ACCEPTANCE",at=index)
            if next_key in used_keys:
                return _result("ROTATION_KEY_REUSED_OR_RETURNED",at=index)
            active_key=next_key
            used_keys.add(next_key)
            rotations+=1
        else: # REVOKE
            if (last_head is None or record["checkpoint_b64"] is not None
                or record["consistency_proof"] or record["next_key_b64"] is not None
                or cap["rotation_acceptance_b64"] is not None
                or record["revoked_key_sha256"]!=hashlib.sha256(active_key).hexdigest()):
                return _result("MALFORMED_REVOCATION_OR_WRONG_KEY",at=index)
            revoked=True
        last_time=record["observed_at"]
        previous_hash=hashlib.sha256(canonical(cap)).hexdigest()
        hashes.append(previous_hash)
    if floor is not None:
        if floor["seq"]>len(hashes):
            return _result("CHAIN_TRUNCATED_BELOW_CALLER_FLOOR",
                           chain_length=len(hashes),floor_sequence=floor["seq"])
        if hashes[floor["seq"]-1]!=floor["capsule_sha256"]:
            return _result("CALLER_FLOOR_HASH_MISMATCH",
                           floor_sequence=floor["seq"])
    return _result(
        "VALID_CUSTOM_RESEARCH_CHAIN_BUT_EXTERNAL_CUSTODY_UNPROVEN",
        cryptographic_chain="VALID_FOR_CALLER_SUPPLIED_PIN",
        chain_length=len(capsules),latest_seq=len(capsules),
        latest_capsule_sha256=previous_hash,
        last_signed_checkpoint_size=last_head["size"] if last_head else None,
        last_signed_checkpoint_root=last_head["root"] if last_head else None,
        rotations_checked=rotations,revocation_seen=revoked,
        floor_binding="CALLER_SUPPLIED_UNAUTHENTICATED" if floor else "NONE",
        final_active_key_sha256=hashlib.sha256(active_key).hexdigest()
    )
