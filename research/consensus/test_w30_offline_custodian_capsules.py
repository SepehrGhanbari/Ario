#!/usr/bin/env python3
"""W30 synthetic-only cryptographic edge/falsification suite.

Only this test file generates disposable RAM-only Ed25519 private keys.
The W30 verifier does NOT contain a signing or publishing interface.
"""
from __future__ import annotations
import base64
import copy
import hashlib
import json
from pathlib import Path
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from w30_offline_custodian_capsules import (
    SCHEMA, RECORD_SCHEMA, SIGN_DOMAIN, ROTATE_DOMAIN,
    ORIGIN, canonical, verify_chain
)

HERE=Path(__file__).resolve().parent
FIX=json.loads((HERE/"W22_PUBLIC_SYNTHETIC_SIGNED_NOTES_2026-11-17.json").read_text("utf-8"))
W20=json.loads((HERE/"W20_SYNTHETIC_LOG_CHECKPOINTS_AND_PROOFS_2026-11-17.json").read_text("utf-8"))
LOGKEY=FIX["public_vkey_for_synthetic_demo_only"]
OLD=FIX["previous_checkpoint"].encode()
NEW=FIX["current_checkpoint"].encode()
FORK=FIX["same_signer_fork_checkpoint"].encode()
PROOF=W20["consistency_proof"]
NOW=1800000000

def b64(data): return base64.b64encode(data).decode("ascii")

def pub(key):
    from cryptography.hazmat.primitives import serialization
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )


class W30(unittest.TestCase):
    def setUp(self):
        self.k1=Ed25519PrivateKey.generate()
        self.k2=Ed25519PrivateKey.generate()
        self.k3=Ed25519PrivateKey.generate()
        self.records=[]
        self.clock=NOW-100

    def add(self,event,*,note=None,proof=None,signer=None,
            next_key=None,revoked_fingerprint=None,approval_key=None):
        if signer is None: signer=self.k1
        if proof is None: proof=[]
        if next_key is None and event=="ROTATE": next_key=self.k2
        if revoked_fingerprint is None and event=="REVOKE":
            revoked_fingerprint=hashlib.sha256(pub(signer)).hexdigest()
        self.clock+=1
        record={
            "schema":RECORD_SCHEMA,
            "seq":len(self.records)+1,
            "prev_hash":(
                hashlib.sha256(canonical(self.records[-1])).hexdigest()
                if self.records else "0"*64
            ),
            "event":event,"origin":ORIGIN,
            "checkpoint_b64":b64(note) if note is not None else None,
            "consistency_proof":list(proof),"observed_at":self.clock,
            "operator_claim":"same-experimenter-controls-all-keys",
            "next_key_b64":b64(pub(next_key)) if event=="ROTATE" else None,
            "revoked_key_sha256":revoked_fingerprint if event=="REVOKE" else None
        }
        raw=canonical(record)
        receipt={
            "record":record,
            "signature_b64":b64(signer.sign(SIGN_DOMAIN+raw)),
            "rotation_acceptance_b64":None
        }
        if event=="ROTATE":
            if approval_key is None: approval_key=next_key
            receipt["rotation_acceptance_b64"]=b64(
                approval_key.sign(ROTATE_DOMAIN+hashlib.sha256(raw).digest())
            )
        self.records.append(receipt)
        return receipt

    def initial(self):
        self.add("OBSERVE",note=OLD)

    def grown(self):
        self.initial()
        self.add("OBSERVE",note=NEW,proof=PROOF)

    def rotated(self):
        self.grown()
        self.add("ROTATE",next_key=self.k2)

    def full(self):
        self.rotated()
        self.add("OBSERVE",note=NEW,signer=self.k2)
        self.add("REVOKE",signer=self.k2)

    def run_chain(self,**kw):
        return verify_chain(self.records,pinned_initial_key_b64=b64(pub(self.k1)),
                            pinned_log_vkey=LOGKEY,as_of=NOW,**kw)
    def resign(self,index,signer=None):
        if signer is None: signer=self.k1
        record=self.records[index]["record"]
        self.records[index]["signature_b64"]=b64(signer.sign(SIGN_DOMAIN+canonical(record)))
    def floor(self,seq):
        return {"seq":seq,"capsule_sha256":
                hashlib.sha256(canonical(self.records[seq-1])).hexdigest()}
    def assert_failed(self,reason):
        result=self.run_chain()
        self.assertEqual(result["reason"],reason,result)
        self.assertEqual(result["status"],"HOLD")
        self.assertEqual(result["production"],"NO_GO")

    def test_01_initial_signed_w22_note_verified(self):
        self.initial()
        r=self.run_chain()
        self.assertEqual(r["cryptographic_chain"],"VALID_FOR_CALLER_SUPPLIED_PIN")
        self.assertEqual(r["last_signed_checkpoint_size"],3)
        self.assertEqual(r["independently_administered_custody"],"NOT_ESTABLISHED")
    def test_02_valid_w22_merkle_growth_3_to8(self):
        self.grown()
        r=self.run_chain()
        self.assertEqual(r["last_signed_checkpoint_size"],8)
        self.assertEqual(r["chain_length"],2)
    def test_03_rotation_and_revocation_full_chain(self):
        self.full()
        r=self.run_chain()
        self.assertEqual(r["cryptographic_chain"],"VALID_FOR_CALLER_SUPPLIED_PIN")
        self.assertTrue(r["revocation_seen"])
        self.assertEqual(r["rotations_checked"],1)
        self.assertEqual(r["chain_length"],5)
    def test_04_valid_chain_never_issues_cosignature_or_admits_memory(self):
        self.full();r=self.run_chain()
        self.assertEqual(r["authority"],"NONE")
        self.assertEqual(r["signatures_issued"],0)
        self.assertEqual(r["external_actions"],0)
        self.assertFalse(r["memory_admitted"])
        self.assertEqual(r["trust_activation"],"NO_GO")
        self.assertEqual(r["genesis"],"NO_GO")
    def test_05_claimed_different_operator_does_not_establish_independence(self):
        self.initial()
        self.records[0]["record"]["operator_claim"]="TRUSTED_EXTERNAL_NOTARIZER"
        self.resign(0)
        r=self.run_chain()
        self.assertEqual(r["external_key_provenance"],"NOT_ESTABLISHED")
        self.assertEqual(r["independently_administered_custody"],"NOT_ESTABLISHED")
    def test_06_tampered_signature_rejected(self):
        self.initial()
        sig=bytearray(base64.b64decode(self.records[0]["signature_b64"]))
        sig[-1]^=1;self.records[0]["signature_b64"]=b64(sig)
        self.assert_failed("INVALID_CAPSULE_SIGNATURE")
    def test_07_wrong_custodian_pin_fails(self):
        self.initial()
        r=verify_chain(self.records,pinned_initial_key_b64=b64(pub(self.k3)),
                       pinned_log_vkey=LOGKEY,as_of=NOW)
        self.assertEqual(r["reason"],"INVALID_CAPSULE_SIGNATURE")
    def test_08_noncanonical_initial_pin_rejected(self):
        self.initial()
        r=verify_chain(self.records,pinned_initial_key_b64="???",pinned_log_vkey=LOGKEY,as_of=NOW)
        self.assertEqual(r["reason"],"INVALID_PINNED_INITIAL_KEY")
    def test_09_swapped_sequence_rejected(self):
        self.grown();self.records.reverse()
        self.assert_failed("INVALID_SEQUENCE_PREV_OR_METADATA")
    def test_10_middle_record_omission_rejected(self):
        self.full();del self.records[1]
        self.assert_failed("INVALID_SEQUENCE_PREV_OR_METADATA")
    def test_11_duplicate_record_not_a_new_sequential_receipt(self):
        self.initial();self.records.append(copy.deepcopy(self.records[0]))
        self.assert_failed("INVALID_SEQUENCE_PREV_OR_METADATA")
    def test_12_mutate_predecessor_hash_even_when_signed(self):
        self.grown();self.records[1]["record"]["prev_hash"]="f"*64
        self.resign(1)
        self.assert_failed("INVALID_SEQUENCE_PREV_OR_METADATA")
    def test_13_splice_new_signed_alternative_first_record_fails_old_chain(self):
        self.grown()
        self.records[0]["record"]["operator_claim"]="replaced-and-resigned"
        self.resign(0)
        self.assert_failed("INVALID_SEQUENCE_PREV_OR_METADATA")
    def test_14_truncated_chain_detected_against_supplied_floor(self):
        self.full();remembered=self.floor(5)
        self.records=self.records[:2]
        self.assertEqual(self.run_chain(floor=remembered)["reason"],
                         "CHAIN_TRUNCATED_BELOW_CALLER_FLOOR")
    def test_15_floor_hash_match_is_only_caller_supplied(self):
        self.full();r=self.run_chain(floor=self.floor(3))
        self.assertEqual(r["floor_binding"],"CALLER_SUPPLIED_UNAUTHENTICATED")
        self.assertEqual(r["external_retained_floor"],"NOT_ESTABLISHED")
    def test_16_floor_digest_mismatch_detected(self):
        self.full()
        self.assertEqual(self.run_chain(floor={"seq":3,"capsule_sha256":"0"*64})["reason"],
                         "CALLER_FLOOR_HASH_MISMATCH")
    def test_17_coordinated_truncation_with_rewritten_floor_undetectable(self):
        self.full()
        old_floor=self.floor(2)
        self.records=self.records[:2]
        r=self.run_chain(floor=old_floor)
        self.assertEqual(r["cryptographic_chain"],"VALID_FOR_CALLER_SUPPLIED_PIN")
        self.assertFalse(r["revocation_seen"])
        self.assertEqual(r["external_retained_floor"],"NOT_ESTABLISHED")
    def test_18_signed_checkpoint_rollback_rejected(self):
        self.grown();self.add("OBSERVE",note=OLD)
        self.assert_failed("CHECKPOINT_ROLLBACK_OR_FORK")
    def test_19_signed_same_size_fork_rejected(self):
        self.grown();self.add("OBSERVE",note=FORK)
        self.assert_failed("CHECKPOINT_ROLLBACK_OR_FORK")
    def test_20_bad_merkle_proof_rejected(self):
        self.grown();self.records[1]["record"]["consistency_proof"][0]="0"*64
        self.resign(1)
        self.assert_failed("CHECKPOINT_ROLLBACK_OR_FORK")
    def test_21_missing_growth_proof_rejected(self):
        self.grown();self.records[1]["record"]["consistency_proof"]=[]
        self.resign(1)
        self.assert_failed("CHECKPOINT_ROLLBACK_OR_FORK")
    def test_22_initial_checkpoint_cannot_have_consistency_proof(self):
        self.initial();self.records[0]["record"]["consistency_proof"]=PROOF
        self.resign(0)
        self.assert_failed("GENESIS_PROOF_MUST_BE_EMPTY")
    def test_23_tampered_original_w22_note_detected(self):
        self.initial()
        altered=OLD.replace(b"\n3\n",b"\n4\n")
        self.records[0]["record"]["checkpoint_b64"]=b64(altered)
        self.resign(0)
        self.assert_failed("INVALID_SIGNED_LOG_CHECKPOINT")
    def test_24_checkpoint_b64_invalid_even_when_signed(self):
        self.initial();self.records[0]["record"]["checkpoint_b64"]="?"
        self.resign(0)
        self.assert_failed("INVALID_CHECKPOINT_BASE64")
    def test_25_observe_cannot_smuggle_next_key(self):
        self.initial()
        self.records[0]["record"]["next_key_b64"]=b64(pub(self.k2))
        self.resign(0)
        self.assert_failed("OBSERVE_HAS_FORBIDDEN_CONTROL_FIELDS")
    def test_26_observe_cannot_smuggle_revocation(self):
        self.initial()
        self.records[0]["record"]["revoked_key_sha256"]=hashlib.sha256(pub(self.k1)).hexdigest()
        self.resign(0)
        self.assert_failed("OBSERVE_HAS_FORBIDDEN_CONTROL_FIELDS")
    def test_27_observe_cannot_smuggle_new_key_acceptance(self):
        self.initial();self.records[0]["rotation_acceptance_b64"]=b64(b"x"*64)
        self.assert_failed("OBSERVE_HAS_FORBIDDEN_CONTROL_FIELDS")
    def test_28_new_key_acceptance_required(self):
        self.rotated();self.records[2]["rotation_acceptance_b64"]=None
        self.assert_failed("MISSING_OR_INVALID_NEW_KEY_ACCEPTANCE")
    def test_29_invalid_new_key_acceptance_rejected(self):
        self.rotated();self.records[2]["rotation_acceptance_b64"]=b64(b"x"*64)
        self.assert_failed("MISSING_OR_INVALID_NEW_KEY_ACCEPTANCE")
    def test_30_attacker_cannot_sign_acceptance_for_a_different_next_key(self):
        self.rotated()
        rec=self.records[2]["record"]
        rec["next_key_b64"]=b64(pub(self.k3))
        self.resign(2)
        self.assert_failed("MISSING_OR_INVALID_NEW_KEY_ACCEPTANCE")
    def test_31_rotation_to_same_key_rejected(self):
        self.grown()
        self.add("ROTATE",next_key=self.k1)
        self.assert_failed("ROTATION_KEY_REUSED_OR_RETURNED")
    def test_32_rotation_to_former_key_rejected(self):
        self.rotated()
        self.add("ROTATE",signer=self.k2,next_key=self.k1)
        self.assert_failed("ROTATION_KEY_REUSED_OR_RETURNED")
    def test_33_old_key_cannot_sign_after_rotation(self):
        self.rotated();self.add("OBSERVE",note=NEW,signer=self.k1)
        self.assert_failed("INVALID_CAPSULE_SIGNATURE")
    def test_34_new_key_can_sign_after_dual_authorized_rotation(self):
        self.rotated();self.add("OBSERVE",note=NEW,signer=self.k2)
        self.assertEqual(self.run_chain()["rotations_checked"],1)
    def test_35_rotation_without_a_checkpoint_rejected(self):
        self.add("ROTATE",next_key=self.k2)
        self.assert_failed("ROTATION_HAS_INVALID_FIELDS_OR_NO_HEAD")
    def test_36_revoke_without_checkpoint_rejected(self):
        self.add("REVOKE")
        self.assert_failed("MALFORMED_REVOCATION_OR_WRONG_KEY")
    def test_37_wrong_revoked_fingerprint_denied(self):
        self.initial()
        self.add("REVOKE",revoked_fingerprint="0"*64)
        self.assert_failed("MALFORMED_REVOCATION_OR_WRONG_KEY")
    def test_38_no_event_after_signed_revocation(self):
        self.initial();self.add("REVOKE");self.add("OBSERVE",note=OLD)
        self.assert_failed("EVENT_AFTER_SIGNED_REVOCATION")
    def test_39_revocation_cannot_smuggle_checkpoint(self):
        self.initial();self.add("REVOKE")
        self.records[-1]["record"]["checkpoint_b64"]=b64(OLD)
        self.resign(-1)
        self.assert_failed("MALFORMED_REVOCATION_OR_WRONG_KEY")
    def test_40_rotations_are_not_custody_proof(self):
        self.full()
        self.assertEqual(self.run_chain()["independently_administered_custody"],
                         "NOT_ESTABLISHED")
    def test_41_older_timestamp_rejected_even_with_new_signature(self):
        self.grown()
        self.records[-1]["record"]["observed_at"]=self.records[0]["record"]["observed_at"]-1
        self.resign(-1)
        self.assert_failed("INVALID_SEQUENCE_PREV_OR_METADATA")
    def test_42_future_timestamp_rejected_as_invalid_input(self):
        self.initial()
        self.records[0]["record"]["observed_at"]=NOW+301
        self.resign(0)
        self.assert_failed("INVALID_SEQUENCE_PREV_OR_METADATA")
    def test_43_boolean_seq_rejected(self):
        self.initial()
        self.records[0]["record"]["seq"]=True
        self.resign(0)
        self.assert_failed("INVALID_SEQUENCE_PREV_OR_METADATA")
    def test_44_extra_capsule_field_rejected(self):
        self.initial();self.records[0]["promote_to_trust"]=True
        self.assert_failed("MALFORMED_CAPSULE")
    def test_45_extra_record_field_rejected(self):
        self.initial();self.records[0]["record"]["promote"]=True
        self.assert_failed("MALFORMED_RECORD")
    def test_46_wrong_research_schema_rejected(self):
        self.initial();self.records[0]["record"]["schema"]="ARIO_W30_PRODUCTION"
        self.resign(0)
        self.assert_failed("INVALID_SEQUENCE_PREV_OR_METADATA")
    def test_47_empty_chain_rejected(self):
        self.assertEqual(self.run_chain()["reason"],"INVALID_ENVELOPE_OR_LIMITS")
    def test_48_over32_entries_rejected_before_crypto(self):
        self.initial();self.records*=33
        self.assertEqual(self.run_chain()["reason"],"INVALID_ENVELOPE_OR_LIMITS")
    def test_49_floor_unknown_field_rejected(self):
        self.initial();f=self.floor(1);f["operator_proof"]=True
        self.assertEqual(self.run_chain(floor=f)["reason"],
                         "MALFORMED_CALLER_SUPPLIED_FLOOR")
    def test_50_boolean_floor_sequence_rejected(self):
        self.initial();f=self.floor(1);f["seq"]=True
        self.assertEqual(self.run_chain(floor=f)["reason"],
                         "MALFORMED_CALLER_SUPPLIED_FLOOR")
    def test_51_wrong_log_verifier_key_rejected(self):
        self.initial()
        r=verify_chain(self.records,pinned_initial_key_b64=b64(pub(self.k1)),
                       pinned_log_vkey=LOGKEY[:-2]+"ab",as_of=NOW)
        self.assertEqual(r["reason"],"INVALID_SIGNED_LOG_CHECKPOINT")
    def test_52_caller_owned_fresh_key_and_first_record_can_verify_but_hold(self):
        attacker=Ed25519PrivateKey.generate()
        self.initial()
        self.resign(0,attacker)
        r=verify_chain(self.records,pinned_initial_key_b64=b64(pub(attacker)),
                       pinned_log_vkey=LOGKEY,as_of=NOW)
        self.assertEqual(r["cryptographic_chain"],"VALID_FOR_CALLER_SUPPLIED_PIN")
        self.assertEqual(r["external_key_provenance"],"NOT_ESTABLISHED")
    def test_53_reissued_identical_head_is_not_world_freshness(self):
        self.initial();self.add("OBSERVE",note=OLD)
        r=self.run_chain()
        self.assertEqual(r["world_freshness"],"UNKNOWN")
    def test_54_original_revocation_cannot_be_omitted_if_floor_retained(self):
        self.full();floor=self.floor(5)
        self.records.pop()
        self.assertEqual(self.run_chain(floor=floor)["reason"],
                         "CHAIN_TRUNCATED_BELOW_CALLER_FLOOR")
    def test_55_duplicate_same_head_can_be_logged_but_untrusted(self):
        self.initial();self.add("OBSERVE",note=OLD)
        self.assertEqual(self.run_chain()["status"],"HOLD")
    def test_56_bare_bytes_instead_of_list_rejected(self):
        self.records=b"no"
        self.assertEqual(self.run_chain()["reason"],"INVALID_ENVELOPE_OR_LIMITS")
    def test_57_invalid_event_type_rejected(self):
        self.initial()
        self.records[0]["record"]["event"]=["OBSERVE"]
        self.assert_failed("INVALID_SEQUENCE_PREV_OR_METADATA")
    def test_58_revoke_under_current_key_after_rotation(self):
        self.rotated();self.add("REVOKE",signer=self.k2)
        self.assertTrue(self.run_chain()["revocation_seen"])
    def test_59_rotation_approval_cannot_be_replayed_on_altered_record(self):
        self.rotated()
        self.records[2]["record"]["operator_claim"]="different-operator"
        self.resign(2,self.k1)
        self.assert_failed("MISSING_OR_INVALID_NEW_KEY_ACCEPTANCE")
    def test_60_invalid_asof_bool_does_not_become_an_authenticated_clock(self):
        self.initial()
        r=verify_chain(self.records,pinned_initial_key_b64=b64(pub(self.k1)),
                       pinned_log_vkey=LOGKEY,as_of=True)
        self.assertEqual(r["reason"],"INVALID_ENVELOPE_OR_LIMITS")

if __name__=="__main__":
    unittest.main(verbosity=2)
