#!/usr/bin/env python3
"""W28: offline, bounded witness-quorum / rollback / independence FALSIFIER.

Pure verification of caller-provided research bytes; no network, I/O, signing,
actual trust, identity attestation, persisted state, enrollment or Ario memory.
All outcomes remain HOLD. A valid quorum of key signatures is NOT a quorum
of independently administered, externally authenticated operators.
"""
from __future__ import annotations
import base64
import re
from w23_checkpoint_gossip import read_signed_note, verify_compact_consistency
from w27_oob_cosignature_audit import audit as audit_cosignature

SCHEMA = "ARIO_W28_WITNESS_EVIDENCE_REVIEW_V1"
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_B64 = re.compile(r"[A-Za-z0-9+/]+={0,2}\Z")
_FIELDS = frozenset(("schema","origin","log_vkey","previous_note_b64",
                     "candidate_note_b64","consistency_proof","pinned_witness_keys",
                     "operator_group_claims","cosignature_packets",
                     "required_signatures","as_of"))
_MAX_PACKET = 4

def _out(reason, **data):
    result = {
        "status": "HOLD", "reason": reason, "policy_admission": "DENIED",
        "signer_custody": "NOT_ESTABLISHED",
        "independent_operators": "NOT_ESTABLISHED",
        "out_of_band_pin_provenance": "NOT_ESTABLISHED",
        "publisher_control_over_retained_history": "UNKNOWN",
        "world_freshness": "UNKNOWN", "log_completeness": "UNKNOWN",
        "genesis": "NO_GO", "trust_activation": "NO_GO", "production": "NO_GO",
        "operational_authority": "NONE", "memory_admitted": False,
        "external_actions": 0, "signatures_issued": 0
    }
    result.update(data)
    return result

def _decode(s):
    if type(s) is not str or len(s) > 8192 or not _B64.fullmatch(s):
        return None
    try:
        b=base64.b64decode(s,validate=True)
    except (ValueError,base64.binascii.Error):
        return None
    return b if len(b) <= 4096 and base64.b64encode(b).decode() == s else None

def review(bundle):
    """Never authorize: checking independent administration needs *external* evidence."""
    if type(bundle) is not dict or frozenset(bundle) != _FIELDS:
        return _out("MALFORMED_REVIEW_ENVELOPE")
    if bundle["schema"] != SCHEMA:
        return _out("UNSUPPORTED_SCHEMA")
    origin=bundle["origin"]; log_vkey=bundle["log_vkey"]
    previous=bundle["previous_note_b64"]; current=bundle["candidate_note_b64"]
    proof=bundle["consistency_proof"]; pins=bundle["pinned_witness_keys"]
    groups=bundle["operator_group_claims"]; packets=bundle["cosignature_packets"]
    required=bundle["required_signatures"]; clock=bundle["as_of"]
    if (type(origin) is not str or not (0 < len(origin) <= 220)
        or type(log_vkey) is not str or not (0 < len(log_vkey) <= 380)
        or previous is not None and type(previous) is not str
        or type(proof) is not list or len(proof) > 16
        or any(type(x) is not str or _HEX.fullmatch(x) is None for x in proof)
        or type(pins) is not dict or type(groups) is not dict
        or type(packets) is not list or not 1 <= len(packets) <= _MAX_PACKET
        or type(required) is not int or not 1 <= required <= _MAX_PACKET
        or type(clock) is not int or not 1_000_000_000 < clock < 5_000_000_000):
        return _out("INVALID_BOUNDS_OR_TYPES")
    if not pins or len(pins) > _MAX_PACKET or set(pins) != set(groups):
        return _out("PIN_REGISTRY_OR_OPERATOR_CLAIMS_MISSING")
    for name in pins:
        if (type(name) is not str or not (1 <= len(name) <= 255)
            or type(pins[name]) is not str or not (0 < len(pins[name]) <= 380)
            or type(groups[name]) is not str or not (0 < len(groups[name]) <= 255)):
            return _out("INVALID_PIN_OR_OPERATOR_CLAIM")
    note=_decode(current)
    if note is None:return _out("MALFORMED_CANDIDATE_NOTE")
    candidate=read_signed_note(note,log_vkey,origin=origin)
    if candidate is None:return _out("INVALID_SIGNED_CANDIDATE")
    if previous is None:
        if proof:return _out("PROOF_WITHOUT_PREVIOUS_PIN")
        continuity="NO_PREVIOUS_HEAD_SELF_REPORTED"
    else:
        old_raw=_decode(previous)
        if old_raw is None:return _out("MALFORMED_PREVIOUS_NOTE")
        old=read_signed_note(old_raw,log_vkey,origin=origin)
        if old is None:return _out("INVALID_SIGNED_PREVIOUS")
        if candidate["size"]<old["size"]:
            return _out("ROLLBACK_BELOW_PROVIDED_HIGH_WATER", previous_size=old["size"],
                        candidate_size=candidate["size"])
        if candidate["size"]==old["size"] and candidate["root"]!=old["root"]:
            return _out("EQUAL_SIZE_SIGNED_FORK", tree_size=old["size"])
        if not verify_compact_consistency(old["size"],candidate["size"],old["root"],
                                          candidate["root"],proof):
            return _out("MERKLE_CONSISTENCY_UNVERIFIED")
        continuity="CONSISTENT_WITH_PROVIDED_PREVIOUS_HEAD"
    if len(packets)<required:
        return _out("SIGNATURE_QUORUM_INSUFFICIENT", verified=0,required=required)
    seen_names=set();seen_key_material=set();valid=0
    for packet in packets:
        if type(packet) is not dict:
            return _out("INVALID_WITNESS_PACKET", verified=valid)
        wp=packet.get("witness")
        if type(wp) is not dict or type(wp.get("name")) is not str:
            return _out("INVALID_WITNESS_PACKET", verified=valid)
        name=wp["name"]
        if name not in pins or name in seen_names:
            return _out("DUPLICATE_OR_UNPINNED_WITNESS", verified=valid)
        seen_names.add(name)
        vkey=pins[name]
        try:
            encoding=vkey.rsplit("+",1)[1]
            raw=base64.b64decode(encoding,validate=True)
        except (IndexError,ValueError,base64.binascii.Error):
            return _out("INVALID_EXTERNALLY_SUPPLIED_KEY", verified=valid)
        if len(raw)!=33 or raw[0]!=4:
            return _out("UNSUPPORTED_KEY_OR_KEY_TYPE", verified=valid)
        if raw[1:] in seen_key_material:
            return _out("TWO_WITNESS_NAMES_REUSE_ONE_PUBLIC_KEY", verified=valid)
        seen_key_material.add(raw[1:])
        lp=packet.get("log")
        op=packet.get("oob")
        if (type(lp) is not dict or type(op) is not dict or
            lp.get("origin")!=origin or lp.get("vkey")!=log_vkey or
            lp.get("checkpoint_b64")!=current or
            op.get("pinned_vkey")!=vkey or
            wp.get("claimed_vkey")!=vkey or
            packet.get("as_of")!=clock):
            return _out("COSIGNATURE_UNBOUND_FROM_CANDIDATE_OR_PIN",verified=valid)
        cos=audit_cosignature(packet)
        if (cos["cryptographic_verification"]!="VALID_FOR_PINNED_KEY" or
            cos["reason"]!="VALID_C2SP_ED25519_COSIGNATURE_BUT_OPERATOR_CUSTODY_UNPROVEN"):
            return _out("COSIGNATURE_INVALID_OR_TIME_WINDOW_FAILED", verified=valid,
                        subreason=cos["reason"])
        valid+=1
    if valid < required:
        return _out("SIGNATURE_QUORUM_INSUFFICIENT",verified=valid,required=required)
    # Operator grouping is claimant supplied and NOT an independent registry.
    if len({groups[n] for n in seen_names}) < required:
        return _out("CLAIMED_OPERATOR_GROUP_COLLISION", crypto="VERIFIED_WITH_SUPPLIED_PINS",
                    continuity=continuity,signatures=valid,
                    note_sha256=candidate["note_sha256"])
    return _out("CRYPTOGRAPHIC_QUORUM_AND_CONSISTENCY_BOUNDED_PASS_ONLY",
                crypto="VERIFIED_WITH_SUPPLIED_PINS", continuity=continuity,
                signatures=valid, distinct_key_material=len(seen_key_material),
                distinct_claimed_groups=len({groups[n] for n in seen_names}),
                note_sha256=candidate["note_sha256"],
                reviewer_warning="pin provenance and admin control NOT verified")
