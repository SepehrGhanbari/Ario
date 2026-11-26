#!/usr/bin/env python3
"""W28 original synthetic W22 notes + RAM-only W27-format cosigners.

These tests prove *bounded parsing* and falsifiers only, not independent custody.
"""
import base64
import copy
import hashlib
import json
from pathlib import Path
import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from w23_checkpoint_gossip import read_signed_note
from w28_quorum_independence_falsifier import SCHEMA, review

HERE=Path(__file__).resolve().parent
FIX=json.loads((HERE/"W22_PUBLIC_SYNTHETIC_SIGNED_NOTES_2026-11-17.json").read_text("utf-8"))
W20=json.loads((HERE/"W20_SYNTHETIC_LOG_CHECKPOINTS_AND_PROOFS_2026-11-17.json").read_text("utf-8"))
ORIGIN="ario-w22-research.invalid/synthetic-log"
LOGKEY=FIX["public_vkey_for_synthetic_demo_only"]
OLD=FIX["previous_checkpoint"].encode()
NEW=FIX["current_checkpoint"].encode()
FORK=FIX["same_signer_fork_checkpoint"].encode()
PROOF=W20["consistency_proof"]
NOW=1800000000

def b64(raw):return base64.b64encode(raw).decode()

def keeper(name, secret=None):
    if secret is None:secret=Ed25519PrivateKey.generate()  # RAM-only synthetic
    raw=secret.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,format=serialization.PublicFormat.Raw)
    keyid=hashlib.sha256(name.encode()+b"\n\x04"+raw).digest()[:4]
    return {"name":name,"secret":secret,"kid":keyid,"vkey":name+"+"+keyid.hex()+"+"+b64(b"\x04"+raw)}

def packet(witness,note=NEW,time=NOW):
    head=read_signed_note(note,LOGKEY)
    if head is None:raise AssertionError("invalid test fixture")
    msg=("cosignature/v1\n"+"time "+str(time)+"\n"+ORIGIN+"\n"+str(head["size"])+"\n"
        +b64(bytes.fromhex(head["root"]))+"\n").encode()
    signed=witness["kid"]+time.to_bytes(8,"big")+witness["secret"].sign(msg)
    name=witness["name"]; vkey=witness["vkey"]
    return {
        "schema":"ARIO_W27_OOB_COSIGNATURE_RESEARCH_V1",
        "log":{"origin":ORIGIN,"vkey":LOGKEY,"checkpoint_b64":b64(note)},
        "witness":{"name":name,"claimed_vkey":vkey,"cosignature_line":"— "+name+" "+b64(signed)+"\n"},
        "oob":{"pinned_vkey":vkey,"channel":"offline_manual_pin",
               "source_id":"W28_SYNTHETIC_NOT_EXTERNAL",
               "claimed_operator":"UNVERIFIED_CONTROL_GROUP"},
        "as_of":NOW
    }

class W28(unittest.TestCase):
    def setUp(self):
        self.a=keeper("w28-first.invalid/synthetic")
        self.b=keeper("w28-second.invalid/synthetic")
        self.bundle={
            "schema":SCHEMA,"origin":ORIGIN,"log_vkey":LOGKEY,
            "previous_note_b64":b64(OLD),"candidate_note_b64":b64(NEW),
            "consistency_proof":list(PROOF),
            "pinned_witness_keys":{self.a["name"]:self.a["vkey"],self.b["name"]:self.b["vkey"]},
            "operator_group_claims":{self.a["name"]:"CLAIMED-OP-A",self.b["name"]:"CLAIMED-OP-B"},
            "cosignature_packets":[packet(self.a),packet(self.b)],
            "required_signatures":2,"as_of":NOW
        }
    def run_bundle(self):return review(self.bundle)
    def to_candidate(self,note,prev=None,proof=None):
        self.bundle["candidate_note_b64"]=b64(note)
        self.bundle["cosignature_packets"]=[packet(self.a,note),packet(self.b,note)]
        if prev is not None:self.bundle["previous_note_b64"]=b64(prev)
        if proof is not None:self.bundle["consistency_proof"]=list(proof)

    def test_01_valid_two_key_quorum_always_hold(self):
        r=self.run_bundle()
        self.assertEqual(r["reason"],"CRYPTOGRAPHIC_QUORUM_AND_CONSISTENCY_BOUNDED_PASS_ONLY")
        self.assertEqual(r["status"],"HOLD")
        self.assertEqual(r["signatures"],2)
        self.assertEqual(r["independent_operators"],"NOT_ESTABLISHED")
    def test_02_no_production_or_operational_authority(self):
        r=self.run_bundle()
        for k,v in (("policy_admission","DENIED"),("production","NO_GO"),
                    ("genesis","NO_GO"),("trust_activation","NO_GO"),
                    ("operational_authority","NONE"),("external_actions",0),
                    ("memory_admitted",False),("signatures_issued",0)):
            self.assertEqual(r[k],v)
    def test_03_same_claimed_admin_group_fails_quorum_independence(self):
        self.bundle["operator_group_claims"][self.b["name"]]="CLAIMED-OP-A"
        self.assertEqual(self.run_bundle()["reason"],"CLAIMED_OPERATOR_GROUP_COLLISION")
    def test_04_two_names_one_ed25519_private_key_rejected(self):
        reused=keeper(self.b["name"],self.a["secret"])
        self.bundle["pinned_witness_keys"][self.b["name"]]=reused["vkey"]
        self.bundle["cosignature_packets"][1]=packet(reused)
        self.assertEqual(self.run_bundle()["reason"],"TWO_WITNESS_NAMES_REUSE_ONE_PUBLIC_KEY")
    def test_05_insufficient_signature_count(self):
        self.bundle["cosignature_packets"].pop()
        self.assertEqual(self.run_bundle()["reason"],"SIGNATURE_QUORUM_INSUFFICIENT")
    def test_06_duplicate_witness_signature_not_second_vote(self):
        self.bundle["cosignature_packets"][1]=copy.deepcopy(self.bundle["cosignature_packets"][0])
        self.assertEqual(self.run_bundle()["reason"],"DUPLICATE_OR_UNPINNED_WITNESS")
    def test_07_unpinned_witness_rejected(self):
        unknown=keeper("w28-third.invalid/synthetic")
        self.bundle["cosignature_packets"][1]=packet(unknown)
        self.assertEqual(self.run_bundle()["reason"],"DUPLICATE_OR_UNPINNED_WITNESS")
    def test_08_tampered_signature_denied(self):
        item=self.bundle["cosignature_packets"][1]["witness"]
        sig=bytearray(base64.b64decode(item["cosignature_line"].split(" ")[-1].strip()))
        sig[-1]^=1
        item["cosignature_line"]="— "+self.b["name"]+" "+b64(sig)+"\n"
        self.assertEqual(self.run_bundle()["reason"],"COSIGNATURE_INVALID_OR_TIME_WINDOW_FAILED")
    def test_09_signature_for_other_head_cannot_vote(self):
        self.bundle["cosignature_packets"][0]=packet(self.a,OLD)
        self.assertEqual(self.run_bundle()["reason"],"COSIGNATURE_UNBOUND_FROM_CANDIDATE_OR_PIN")
    def test_10_cosignature_claims_wrong_log_origin(self):
        self.bundle["cosignature_packets"][0]["log"]["origin"]="wrong.invalid"
        self.assertEqual(self.run_bundle()["reason"],"COSIGNATURE_UNBOUND_FROM_CANDIDATE_OR_PIN")
    def test_11_pin_mismatch_rejected(self):
        self.bundle["pinned_witness_keys"][self.a["name"]]=self.b["vkey"]
        self.assertEqual(self.run_bundle()["reason"],"COSIGNATURE_UNBOUND_FROM_CANDIDATE_OR_PIN")
    def test_12_stale_cosignature_does_not_count(self):
        self.bundle["cosignature_packets"][1]=packet(self.b,NEW,NOW-8*86400)
        self.assertEqual(self.run_bundle()["reason"],"COSIGNATURE_INVALID_OR_TIME_WINDOW_FAILED")
    def test_13_future_cosignature_does_not_count(self):
        self.bundle["cosignature_packets"][1]=packet(self.b,NEW,NOW+301)
        self.assertEqual(self.run_bundle()["reason"],"COSIGNATURE_INVALID_OR_TIME_WINDOW_FAILED")
    def test_14_signed_rollback_below_supplied_anchor_detected(self):
        self.to_candidate(OLD,prev=NEW,proof=[])
        self.assertEqual(self.run_bundle()["reason"],"ROLLBACK_BELOW_PROVIDED_HIGH_WATER")
    def test_15_same_size_signed_fork_detected(self):
        self.to_candidate(FORK,prev=NEW,proof=[])
        self.assertEqual(self.run_bundle()["reason"],"EQUAL_SIZE_SIGNED_FORK")
    def test_16_valid_w22_3_to_8_consistency(self):
        r=self.run_bundle()
        self.assertEqual(r["continuity"],"CONSISTENT_WITH_PROVIDED_PREVIOUS_HEAD")
    def test_17_invalid_merkle_proof_rejected(self):
        self.bundle["consistency_proof"][0]="0"*64
        self.assertEqual(self.run_bundle()["reason"],"MERKLE_CONSISTENCY_UNVERIFIED")
    def test_18_without_previous_anchor_no_rollback_proof(self):
        self.bundle["previous_note_b64"]=None
        self.bundle["consistency_proof"]=[]
        r=self.run_bundle()
        self.assertEqual(r["continuity"],"NO_PREVIOUS_HEAD_SELF_REPORTED")
        self.assertEqual(r["independent_operators"],"NOT_ESTABLISHED")
    def test_19_proof_without_previous_anchor_rejected(self):
        self.bundle["previous_note_b64"]=None
        self.assertEqual(self.run_bundle()["reason"],"PROOF_WITHOUT_PREVIOUS_PIN")
    def test_20_coordinated_old_state_looks_consistent_without_external_pin(self):
        self.to_candidate(OLD,prev=OLD,proof=[])
        r=self.run_bundle()
        self.assertEqual(r["reason"],"CRYPTOGRAPHIC_QUORUM_AND_CONSISTENCY_BOUNDED_PASS_ONLY")
        self.assertEqual(r["signer_custody"],"NOT_ESTABLISHED")
    def test_21_invalid_signed_candidate_denied(self):
        body=NEW.replace(b"\n8\n",b"\n9\n")
        self.bundle["candidate_note_b64"]=b64(body)
        self.assertEqual(self.run_bundle()["reason"],"INVALID_SIGNED_CANDIDATE")
    def test_22_invalid_signed_previous_denied(self):
        self.bundle["previous_note_b64"]=b64(OLD.replace(b"\n3\n",b"\n4\n"))
        self.assertEqual(self.run_bundle()["reason"],"INVALID_SIGNED_PREVIOUS")
    def test_23_extra_schema_field_denied(self):
        self.bundle["approve"]=True
        self.assertEqual(self.run_bundle()["reason"],"MALFORMED_REVIEW_ENVELOPE")
    def test_24_bad_top_level_schema(self):
        self.bundle["schema"]="ARIO_W28_PRODUCTION"
        self.assertEqual(self.run_bundle()["reason"],"UNSUPPORTED_SCHEMA")
    def test_25_missing_pin_denied(self):
        del self.bundle["pinned_witness_keys"][self.b["name"]]
        self.assertEqual(self.run_bundle()["reason"],"PIN_REGISTRY_OR_OPERATOR_CLAIMS_MISSING")
    def test_26_claimed_fully_independent_still_hold(self):
        self.bundle["operator_group_claims"]={
            self.a["name"]:"INDEPENDENT_CUSTODY_CONFIRMED_BY_SELF",
            self.b["name"]:"INDEPENDENT_CUSTODY_CONFIRMED_BY_SELF_TOO"}
        r=self.run_bundle()
        self.assertEqual(r["independent_operators"],"NOT_ESTABLISHED")
        self.assertEqual(r["out_of_band_pin_provenance"],"NOT_ESTABLISHED")
    def test_27_bare_bytes_not_an_evidence_object(self):
        self.assertEqual(review(b"not-a-bundle")["reason"],"MALFORMED_REVIEW_ENVELOPE")
    def test_28_more_than_four_packets_denied(self):
        self.bundle["cosignature_packets"]*=3
        self.assertEqual(self.run_bundle()["reason"],"INVALID_BOUNDS_OR_TYPES")
    def test_29_invalid_proof_hash_denied(self):
        self.bundle["consistency_proof"]=["xyz"]
        self.assertEqual(self.run_bundle()["reason"],"INVALID_BOUNDS_OR_TYPES")
    def test_30_boolean_quorum_is_not_int(self):
        self.bundle["required_signatures"]=True
        self.assertEqual(self.run_bundle()["reason"],"INVALID_BOUNDS_OR_TYPES")
    def test_31_invalid_as_of_is_rejected(self):
        self.bundle["as_of"]=True
        self.assertEqual(self.run_bundle()["reason"],"INVALID_BOUNDS_OR_TYPES")
    def test_32_noncanonical_base64_rejected(self):
        self.bundle["candidate_note_b64"]="AAAA=="
        self.assertEqual(self.run_bundle()["reason"],"MALFORMED_CANDIDATE_NOTE")
    def test_33_candidate_origin_substitution_denied(self):
        self.bundle["origin"]="unrelated.invalid/log"
        self.assertEqual(self.run_bundle()["reason"],"INVALID_SIGNED_CANDIDATE")
    def test_34_other_key_material_even_if_same_claimed_operator(self):
        self.bundle["operator_group_claims"][self.b["name"]]=self.bundle["operator_group_claims"][self.a["name"]]
        self.assertEqual(self.run_bundle()["reason"],"CLAIMED_OPERATOR_GROUP_COLLISION")
    def test_35_witness_metadata_clock_must_match_explicit_evaluation_clock(self):
        self.bundle["cosignature_packets"][0]["as_of"]=NOW-1
        self.assertEqual(self.run_bundle()["reason"],"COSIGNATURE_UNBOUND_FROM_CANDIDATE_OR_PIN")
    def test_36_cosignature_wrong_log_vkey_denied(self):
        self.bundle["cosignature_packets"][0]["log"]["vkey"]=LOGKEY+"e"
        self.assertEqual(self.run_bundle()["reason"],"COSIGNATURE_UNBOUND_FROM_CANDIDATE_OR_PIN")
    def test_37_witness_packet_unknown_name_no_autodiscovery(self):
        self.bundle["cosignature_packets"][0]["witness"]["name"]="no-autodiscovery.invalid"
        self.assertEqual(self.run_bundle()["reason"],"DUPLICATE_OR_UNPINNED_WITNESS")

if __name__=="__main__":
    unittest.main(verbosity=2)
