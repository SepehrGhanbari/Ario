#!/usr/bin/env python3
"""W27 offline synthetic tests. No external fetch or cosigner enrollment."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from w27_oob_cosignature_audit import audit, SCHEMA
from w23_checkpoint_gossip import read_signed_note

HERE=Path(__file__).resolve().parent
FIX=json.loads((HERE/"W22_PUBLIC_SYNTHETIC_SIGNED_NOTES_2026-11-17.json").read_text("utf-8"))
ORIGIN="ario-w22-research.invalid/synthetic-log"
LOG_KEY=FIX["public_vkey_for_synthetic_demo_only"]
NOTE=FIX["current_checkpoint"].encode()
FORK=FIX["same_signer_fork_checkpoint"].encode()
AS_OF=1800000000

class W27(unittest.TestCase):
    def setUp(self):
        self.private=Ed25519PrivateKey.generate() # disposable RAM-only signer in tests
        self.wname="ario-w27-test.invalid/not-a-real-witness"
        raw=self.private.public_key().public_bytes(encoding=serialization.Encoding.Raw,format=serialization.PublicFormat.Raw)
        self.kid=hashlib.sha256(self.wname.encode()+b"\n\x04"+raw).digest()[:4]
        self.vkey=self.wname+"+"+self.kid.hex()+"+"+base64.b64encode(b"\x04"+raw).decode()
        self.packet={
            "schema":SCHEMA,
            "log":{"origin":ORIGIN,"vkey":LOG_KEY,"checkpoint_b64":base64.b64encode(NOTE).decode()},
            "witness":{"name":self.wname,"claimed_vkey":self.vkey,"cosignature_line":""},
            "oob":{"pinned_vkey":self.vkey,"channel":"offline_manual_pin",
                   "source_id":"TEST_ONLY_NO_INDEPENDENT_CUSTODY","claimed_operator":"SAME_LAB_OPERATOR"},
            "as_of":AS_OF
        }
        self.sign(NOTE,AS_OF)

    def sign(self,note,timestamp,private=None):
        head=read_signed_note(note,LOG_KEY)
        self.assertIsNotNone(head)
        message=("cosignature/v1\n"+"time "+str(timestamp)+"\n"+ORIGIN+"\n"+
                 str(head["size"])+"\n"+base64.b64encode(bytes.fromhex(head["root"])).decode()+"\n").encode()
        sig=(self.private if private is None else private).sign(message)
        self.packet["log"]["checkpoint_b64"]=base64.b64encode(note).decode()
        self.packet["witness"]["cosignature_line"]="— "+self.wname+" "+base64.b64encode(self.kid+timestamp.to_bytes(8,"big")+sig).decode()+"\n"

    def run_packet(self):
        return audit(self.packet)

    def test_01_valid_cosig_never_certifies_independent_operator(self):
        r=self.run_packet()
        self.assertEqual(r["status"],"HOLD")
        self.assertEqual(r["cryptographic_verification"],"VALID_FOR_PINNED_KEY")
        self.assertEqual(r["independently_administered_custody"],"NOT_ESTABLISHED")
        self.assertEqual(r["out_of_band_pin_provenance"],"NOT_ESTABLISHED")
    def test_02_valid_signer_does_not_act(self):
        r=self.run_packet()
        self.assertEqual(r["external_actions"],0)
        self.assertEqual(r["signatures_issued"],0)
        self.assertFalse(r["memory_admitted"])
        self.assertEqual(r["production"],"NO_GO")
    def test_03_missing_oob_pin(self):
        self.packet["oob"]=None
        self.assertNotEqual(self.run_packet()["cryptographic_verification"],"VALID_FOR_PINNED_KEY")
    def test_04_claimant_only_channel_denied(self):
        self.packet["oob"]["channel"]="claimed_by_log_operator"
        self.assertEqual(self.run_packet()["reason"],"PIN_CHANNEL_UNSUPPORTED_OR_CLAIMANT_ONLY")
    def test_05_different_pinned_vkey_denied(self):
        self.packet["oob"]["pinned_vkey"]=self.vkey[:-2]+"zz"
        self.assertEqual(self.run_packet()["reason"],"PIN_MISMATCH_OR_KEY_ROTATION_UNVERIFIED")
    def test_06_operator_name_not_cryptographic_identity(self):
        self.packet["oob"]["claimed_operator"]="INDEPENDENT_ORGANIZATION_IN_MY_OWN_JSON"
        self.assertEqual(self.run_packet()["independently_administered_custody"],"NOT_ESTABLISHED")
    def test_07_invalid_cosignature_signature(self):
        s=self.packet["witness"]["cosignature_line"]
        raw=bytearray(base64.b64decode(s.split(" ")[-1].strip()))
        raw[-1]^=1
        self.packet["witness"]["cosignature_line"]="— "+self.wname+" "+base64.b64encode(raw).decode()+"\n"
        self.assertNotEqual(self.run_packet()["cryptographic_verification"],"VALID_FOR_PINNED_KEY")
    def test_08_wrong_cosigner_keyid(self):
        s=self.packet["witness"]["cosignature_line"]
        raw=bytearray(base64.b64decode(s.split(" ")[-1].strip()))
        raw[0]^=1
        self.packet["witness"]["cosignature_line"]="— "+self.wname+" "+base64.b64encode(raw).decode()+"\n"
        self.assertEqual(self.run_packet()["reason"],"INVALID_COSIGNATURE_KEY_ID_OR_SIZE")
    def test_09_stale_cosignature(self):
        self.sign(NOTE,AS_OF-8*86400)
        self.assertEqual(self.run_packet()["reason"],"COSIGNATURE_TIMESTAMP_TOO_OLD_FOR_LAB")
    def test_10_future_cosignature(self):
        self.sign(NOTE,AS_OF+301)
        self.assertEqual(self.run_packet()["reason"],"COSIGNATURE_TIMESTAMP_IN_FUTURE")
    def test_11_synthetic_signed_fork_can_verify_but_not_establish_consistency(self):
        self.sign(FORK,AS_OF)
        self.assertEqual(self.run_packet()["cryptographic_verification"],"VALID_FOR_PINNED_KEY")
        self.assertEqual(self.run_packet()["witness_retained_checkpoint"],"NOT_ESTABLISHED")
    def test_12_wrong_log_vkey(self):
        self.packet["log"]["vkey"]=LOG_KEY[:-2]+"ab"
        self.assertEqual(self.run_packet()["reason"],"INVALID_SIGNED_LOG_CHECKPOINT")
    def test_13_mismatch_log_origin(self):
        self.packet["log"]["origin"]="different.invalid/log"
        self.assertEqual(self.run_packet()["reason"],"INVALID_SIGNED_LOG_CHECKPOINT")
    def test_14_tamper_signed_log_body(self):
        old=base64.b64decode(self.packet["log"]["checkpoint_b64"])
        self.packet["log"]["checkpoint_b64"]=base64.b64encode(old.replace(b"\n8\n",b"\n9\n")).decode()
        self.assertEqual(self.run_packet()["reason"],"INVALID_SIGNED_LOG_CHECKPOINT")
    def test_15_duplicate_cosignature_lines(self):
        line=self.packet["witness"]["cosignature_line"]
        self.packet["witness"]["cosignature_line"]+=line
        self.assertEqual(self.run_packet()["reason"],"MALFORMED_COSIGNATURE_LINE")
    def test_16_wrong_witness_claimed_name(self):
        self.packet["witness"]["name"]="someone-else.invalid"
        self.assertEqual(self.run_packet()["reason"],"WITNESS_NAME_MISMATCH")
    def test_17_untrusted_key_algorithm(self):
        pub=self.private.public_key().public_bytes(encoding=serialization.Encoding.Raw,format=serialization.PublicFormat.Raw)
        wrong_type=b"\x01"+pub
        wrong_id=hashlib.sha256(self.wname.encode()+b"\n"+wrong_type).digest()[:4]
        wrong_vkey=self.wname+"+"+wrong_id.hex()+"+"+base64.b64encode(wrong_type).decode()
        self.packet["witness"]["claimed_vkey"]=wrong_vkey
        self.packet["oob"]["pinned_vkey"]=wrong_vkey
        self.assertNotEqual(self.run_packet()["cryptographic_verification"],"VALID_FOR_PINNED_KEY")
    def test_18_missing_source_id(self):
        self.packet["oob"]["source_id"]=""
        self.assertEqual(self.run_packet()["reason"],"MISSING_OUT_OF_BAND_PROVENANCE_RECORD")
    def test_19_noncanonical_checkpoint_base64(self):
        self.packet["log"]["checkpoint_b64"]="???"
        self.assertNotEqual(self.run_packet()["cryptographic_verification"],"VALID_FOR_PINNED_KEY")
    def test_20_bad_timestamp_type(self):
        self.packet["as_of"]=True
        self.assertEqual(self.run_packet()["reason"],"MALFORMED_FIELDS")
    def test_21_wrong_schema(self):
        self.packet["schema"]="ARIO_W27_PRODUCTION"
        self.assertEqual(self.run_packet()["reason"],"UNSUPPORTED_RESEARCH_SCHEMA")
    def test_22_unknown_field_refused(self):
        self.packet["execute"]=True
        self.assertEqual(self.run_packet()["reason"],"MALFORMED_EVIDENCE_ENVELOPE")
    def test_23_bad_cosigner_payload_size(self):
        self.packet["witness"]["cosignature_line"]="— "+self.wname+" "+base64.b64encode(self.kid+b"a"*4).decode()+"\n"
        self.assertEqual(self.run_packet()["reason"],"INVALID_COSIGNATURE_KEY_ID_OR_SIZE")
    def test_24_wrong_signature_for_different_checkpoint(self):
        self.packet["log"]["checkpoint_b64"]=base64.b64encode(FORK).decode()
        self.assertNotEqual(self.run_packet()["cryptographic_verification"],"VALID_FOR_PINNED_KEY")
    def test_25_equivalent_url_same_admin_cannot_prove_separation(self):
        self.packet["oob"]["channel"]="authenticated_external_directory"
        self.packet["oob"]["source_id"]="https://also-owned-by-the-same-person.invalid"
        self.packet["oob"]["claimed_operator"]="ANOTHER_NAME_SAME_ADMIN"
        self.assertEqual(self.run_packet()["independently_administered_custody"],"NOT_ESTABLISHED")
    def test_26_attacker_reuses_expired_cosig_with_recent_clock(self):
        self.sign(NOTE,AS_OF-30*86400)
        self.assertEqual(self.run_packet()["cryptographic_verification"],"VALID_FOR_PINNED_KEY")
        self.assertEqual(self.run_packet()["status"],"HOLD")
    def test_27_unsupported_bytes_input(self):
        self.assertEqual(audit(b"anything")["reason"],"MALFORMED_EVIDENCE_ENVELOPE")
    def test_28_boolean_and_negative_asof_fails(self):
        self.packet["as_of"]=-1
        self.assertEqual(self.run_packet()["reason"],"MALFORMED_FIELDS")

if __name__=="__main__":
    unittest.main(verbosity=2)
