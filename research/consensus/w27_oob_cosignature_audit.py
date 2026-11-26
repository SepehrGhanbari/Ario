#!/usr/bin/env python3
"""W27 offline C2SP Ed25519 cosignature / out-of-band pin boundary probe.

NO NETWORK, NO DISK IO, NO SIGNING, NO LIVE WITNESS, NO ARIO TRUST.
Reads a caller-supplied RESEARCH JSON object. A passing signature proves only
cryptographic correspondence to a supplied key; NOT independent administration,
key provenance, freshness of the world, mirror completeness or a real C2SP peer.
Supported W22 subset only (Ed25519 log note; Ed25519 witness cosignature).
Reference: https://c2sp.org/tlog-cosignature@v1.1.0 and
https://c2sp.org/tlog-checkpoint@v1.1.0.
"""
from __future__ import annotations
import base64
import hashlib
import re
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from w23_checkpoint_gossip import read_signed_note

SCHEMA = "ARIO_W27_OOB_COSIGNATURE_RESEARCH_V1"
_VKEY = re.compile(r"^([^+\s]{1,255})\+([0-9a-f]{8})\+([A-Za-z0-9+/]+={0,2})$")
_B64 = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")
_MAX_AGE = 7 * 86400
_MAX_DRIFT = 300


def _b64(s, max_bytes=4096):
    if type(s) is not str or len(s) > max_bytes * 2 or not _B64.fullmatch(s):
        raise ValueError("noncanonical base64 input")
    raw = base64.b64decode(s, validate=True)
    if len(raw) > max_bytes or base64.b64encode(raw).decode() != s:
        raise ValueError("noncanonical base64 encoding")
    return raw


def _witness_vkey(vkey):
    if type(vkey) is not str or len(vkey) > 380:
        raise ValueError("invalid witness verifier key")
    m = _VKEY.fullmatch(vkey)
    if not m:
        raise ValueError("bad witness key format")
    name, kid_hex, encoded = m.groups()
    raw = _b64(encoded, 33)
    if len(raw) != 33 or raw[0] != 4:
        raise ValueError("unsupported witness algorithm; W27 Ed25519 only")
    kid = hashlib.sha256(name.encode() + b"\n" + raw).digest()[:4]
    if kid.hex() != kid_hex:
        raise ValueError("untrusted or incorrect witness key ID")
    return name, kid, raw[1:]


def _verdict(reason, *, crypto="NOT_VERIFIED", details=None):
    x = {
        "status": "HOLD",
        "reason": reason,
        "cryptographic_verification": crypto,
        "out_of_band_pin_provenance": "NOT_ESTABLISHED",
        "independently_administered_custody": "NOT_ESTABLISHED",
        "witness_retained_checkpoint": "NOT_ESTABLISHED",
        "live_monitor_readback": "NOT_RUN",
        "log_completeness": "UNKNOWN",
        "world_freshness": "UNKNOWN",
        "authority": "NONE",
        "trust_activation": "NO_GO",
        "production": "NO_GO",
        "external_actions": 0,
        "signatures_issued": 0,
        "memory_admitted": False,
    }
    if details is not None:
        x["details"] = details
    return x


def audit(packet):
    """Verify a bounded supplied C2SP cosignature; NEVER elevate custody."""
    if type(packet) is not dict or set(packet) != {"schema","log","witness","oob","as_of"}:
        return _verdict("MALFORMED_EVIDENCE_ENVELOPE")
    if packet["schema"] != SCHEMA:
        return _verdict("UNSUPPORTED_RESEARCH_SCHEMA")
    log, witness, oob = packet["log"], packet["witness"], packet["oob"]
    if (type(log) is not dict or set(log) != {"origin","vkey","checkpoint_b64"}
        or type(witness) is not dict or set(witness) != {"name","claimed_vkey","cosignature_line"}
        or type(oob) is not dict or set(oob) != {"pinned_vkey","channel","source_id","claimed_operator"}
        or type(packet["as_of"]) is not int or not 1_000_000_000 < packet["as_of"] < 5_000_000_000):
        return _verdict("MALFORMED_FIELDS")
    if (type(log["origin"]) is not str or len(log["origin"]) > 220
        or type(log["vkey"]) is not str or len(log["vkey"]) > 380
        or type(witness["name"]) is not str or len(witness["name"]) > 255
        or type(witness["claimed_vkey"]) is not str or len(witness["claimed_vkey"]) > 380
        or type(oob["pinned_vkey"]) is not str or len(oob["pinned_vkey"]) > 380
        or type(oob["channel"]) is not str or len(oob["channel"]) > 60
        or type(oob["source_id"]) is not str or len(oob["source_id"]) > 255
        or type(oob["claimed_operator"]) is not str or len(oob["claimed_operator"]) > 255):
        return _verdict("MALFORMED_FIELDS")
    if not oob["channel"] or not oob["source_id"] or not oob["claimed_operator"]:
        return _verdict("MISSING_OUT_OF_BAND_PROVENANCE_RECORD")
    # Neither a URL nor a claimed 'separate' channel authenticates a human operator.
    if oob["channel"] not in ("offline_manual_pin","authenticated_external_directory","separate_operator_message"):
        return _verdict("PIN_CHANNEL_UNSUPPORTED_OR_CLAIMANT_ONLY")
    if oob["pinned_vkey"] != witness["claimed_vkey"]:
        return _verdict("PIN_MISMATCH_OR_KEY_ROTATION_UNVERIFIED")
    try:
        name, kid, public = _witness_vkey(oob["pinned_vkey"])
        if name != witness["name"]:
            return _verdict("WITNESS_NAME_MISMATCH")
        if type(log["checkpoint_b64"]) is not str:
            return _verdict("MALFORMED_CHECKPOINT")
        note = _b64(log["checkpoint_b64"], 4096)
        head = read_signed_note(note, log["vkey"], origin=log["origin"])
        if head is None:
            return _verdict("INVALID_SIGNED_LOG_CHECKPOINT")
        if type(witness["cosignature_line"]) is not str or len(witness["cosignature_line"]) > 550:
            return _verdict("MALFORMED_COSIGNATURE_LINE")
        expected_prefix = "— " + name + " "
        line = witness["cosignature_line"]
        if not line.startswith(expected_prefix) or not line.endswith("\n") or "\n" in line[:-1]:
            return _verdict("MALFORMED_COSIGNATURE_LINE")
        payload = _b64(line[len(expected_prefix):-1], 76)
        if len(payload) != 76 or payload[:4] != kid:
            return _verdict("INVALID_COSIGNATURE_KEY_ID_OR_SIZE")
        timestamp = int.from_bytes(payload[4:12], "big")
        signed = (
            "cosignature/v1\n"
            + "time " + str(timestamp) + "\n"
            + log["origin"] + "\n"
            + str(head["size"]) + "\n"
            + base64.b64encode(bytes.fromhex(head["root"])).decode() + "\n"
        ).encode()
        # Does not sign additional statements; original W22 subset has none.
        Ed25519PublicKey.from_public_bytes(public).verify(payload[12:], signed)
        if timestamp > packet["as_of"] + _MAX_DRIFT:
            return _verdict("COSIGNATURE_TIMESTAMP_IN_FUTURE", crypto="VALID_FOR_PINNED_KEY")
        if timestamp < packet["as_of"] - _MAX_AGE:
            return _verdict("COSIGNATURE_TIMESTAMP_TOO_OLD_FOR_LAB", crypto="VALID_FOR_PINNED_KEY")
        return _verdict(
            "VALID_C2SP_ED25519_COSIGNATURE_BUT_OPERATOR_CUSTODY_UNPROVEN",
            crypto="VALID_FOR_PINNED_KEY",
            details={"tree_size":head["size"],"root_sha256":head["root"],
                     "cosignature_timestamp":timestamp, "checkpoint_note_sha256":head["note_sha256"],
                     "pin_channel_is_unverified_claim":True}
        )
    except (ValueError, TypeError, UnicodeError, OverflowError, InvalidSignature):
        return _verdict("MALFORMED_OR_INVALID_CRYPTOGRAPHIC_EVIDENCE")
