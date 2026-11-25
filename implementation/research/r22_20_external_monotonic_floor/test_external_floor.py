import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from coincurve import PrivateKey
import external_floor as f

def fixture_ledger(count=6, seed="A"):
    out=b""
    previous=None
    for i in range(count):
        row={"record_id":f"ROW-{i}","observed_at":f"LAB-{i}",
             "payload":{"claim_id":"TEST","node_id":f"N{i}","value":f"{seed}-{i}"},
             "previous_sha256":previous}
        row["sha256"]=f.sha(json.dumps(row,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode())
        previous=row["sha256"]
        out+=f.canonical(row)
    return out

def pair(seed="A"):
    key=PrivateKey()
    ledger6=fixture_ledger(6,seed)
    prior=hashlib.sha256(b"prior-checkpoint").hexdigest()
    scope="a"*48
    e6=f.make_envelope(scope,6,ledger6,prior,f.sha(ledger6),"GENESIS","GENESIS","GENESIS")
    ev6=f.make_event(e6,ledger6,key)
    ledger8=f.ledger_extend(ledger6)
    e8=f.make_envelope(scope,8,ledger8,prior,f.sha(ledger6),f.checksum(e6),ev6["id"],f.sha(ledger6))
    ev8=f.make_event(e8,ledger8,key)
    return key,prior,ledger6,e6,ev6,ledger8,e8,ev8

class ExternalFloorTests(unittest.TestCase):
    def test_valid_signed_6_to_8_chain(self):
        key,prior,l6,e6,v6,l8,e8,v8=pair()
        status,result=f.validate_successor(v6,v8,f.target_for_event(v8),key.public_key_xonly.format().hex(),prior)
        self.assertEqual(status,"RECOVERED_LINKED_SYNTHETIC_EXTERNAL_FLOOR_ONLY")
        self.assertEqual(result["seq"],8)
        self.assertEqual(result["ledger"],l8)

    def test_stale_event_cannot_match_new_log_leaf(self):
        key,prior,l6,e6,v6,l8,e8,v8=pair()
        target=f.target_for_event(v8)
        self.assertIsNone(f.extract_target([v6],target,key.public_key_xonly.format().hex())[0])

    def test_no_relay_content_is_hold(self):
        key,prior,l6,e6,v6,l8,e8,v8=pair()
        target=f.target_for_event(v8)
        event,payload=f.extract_target([],target,key.public_key_xonly.format().hex())
        self.assertIsNone(event)
        self.assertIsNone(payload)

    def test_tampered_event_id_rejected(self):
        key,prior,l6,e6,v6,l8,e8,v8=pair()
        bad=copy.deepcopy(v8);bad["content"]+="x"
        with self.assertRaises(ValueError): f.verify_event(bad,key.public_key_xonly.format().hex())

    def test_wrong_pubkey_rejected(self):
        key,prior,l6,e6,v6,l8,e8,v8=pair()
        with self.assertRaises(ValueError): f.verify_event(v8,PrivateKey().public_key_xonly.format().hex())

    def test_invalid_signature_rejected(self):
        key,prior,l6,e6,v6,l8,e8,v8=pair()
        bad=copy.deepcopy(v8);bad["sig"]="0"*128
        with self.assertRaises(ValueError): f.verify_event(bad,key.public_key_xonly.format().hex())

    def test_wrong_target_rejected(self):
        key,prior,l6,e6,v6,l8,e8,v8=pair()
        with self.assertRaises(ValueError): f.extract_target([v8], "0"*64,key.public_key_xonly.format().hex())

    def test_wrong_predecessor_rejected(self):
        key,prior,l6,e6,v6,l8,e8,v8=pair()
        x=f.parse_envelope(e8);x["previous_checksum"]="0"*64
        bad=f.make_event(f.canonical(x),l8,key)
        status,_=f.validate_successor(v6,bad,f.target_for_event(bad),key.public_key_xonly.format().hex(),prior)
        self.assertEqual(status,"HOLD_PREDECESSOR_OR_SCOPE")

    def test_wrong_event_parent_rejected(self):
        key,prior,l6,e6,v6,l8,e8,v8=pair()
        x=f.parse_envelope(e8);x["previous_event_id"]="0"*64
        bad=f.make_event(f.canonical(x),l8,key)
        status,_=f.validate_successor(v6,bad,f.target_for_event(bad),key.public_key_xonly.format().hex(),prior)
        self.assertEqual(status,"HOLD_PREDECESSOR_OR_SCOPE")

    def test_wrong_scope_rejected(self):
        key,prior,l6,e6,v6,l8,e8,v8=pair()
        x=f.parse_envelope(e8);x["scope"]="b"*48
        bad=f.make_event(f.canonical(x),l8,key)
        status,_=f.validate_successor(v6,bad,f.target_for_event(bad),key.public_key_xonly.format().hex(),prior)
        self.assertEqual(status,"HOLD_PREDECESSOR_OR_SCOPE")

    def test_wrong_prior_checkpoint_rejected(self):
        key,prior,l6,e6,v6,l8,e8,v8=pair()
        status,_=f.validate_successor(v6,v8,f.target_for_event(v8),key.public_key_xonly.format().hex(),"0"*64)
        self.assertEqual(status,"HOLD_FIRST_ANCHOR")

    def test_wrong_ledger_prefix_rejected(self):
        key,prior,l6,e6,v6,l8,e8,v8=pair()
        altered=fixture_ledger(8,"B")
        x=f.parse_envelope(e8);x["ledger_sha256"]=f.sha(altered)
        rows=f.parse_ledger(altered,8);x["head_sha256"]=rows[-1]["sha256"]
        bad=f.make_event(f.canonical(x),altered,key)
        status,_=f.validate_successor(v6,bad,f.target_for_event(bad),key.public_key_xonly.format().hex(),prior)
        self.assertEqual(status,"HOLD_LEDGER_PREFIX")

    def test_wrong_sequence_rejected(self):
        key,prior,l6,e6,v6,l8,e8,v8=pair()
        x=f.parse_envelope(e8);x["seq"]=6;x["ledger_sha256"]=f.sha(l6)
        x["head_sha256"]=f.parse_ledger(l6,6)[-1]["sha256"]
        bad=f.make_event(f.canonical(x),l6,key)
        status,_=f.validate_successor(v6,bad,f.target_for_event(bad),key.public_key_xonly.format().hex(),prior)
        self.assertEqual(status,"HOLD_PREDECESSOR_OR_SCOPE")

    def test_authority_flag_rejected(self):
        key,prior,l6,e6,v6,l8,e8,v8=pair()
        x=f.parse_envelope(e8);x["authoritative"]=True
        with self.assertRaises(ValueError): f.parse_envelope(f.canonical(x))

    def test_duplicate_envelope_field_rejected(self):
        key,prior,l6,e6,v6,l8,e8,v8=pair()
        raw=e8.replace(b'"seq":8,',b'"seq":8,"seq":8,')
        with self.assertRaises(ValueError): f.parse_envelope(raw)

    def test_wrong_ledger_hash_rejected(self):
        key,prior,l6,e6,v6,l8,e8,v8=pair()
        bad=copy.deepcopy(v8)
        bad["content"]=bad["content"].replace(
            f.base64.b64encode(l8).decode(),f.base64.b64encode(l6).decode())
        bad["id"]=f.nostr_event_id(bad)
        bad["sig"]=key.sign_schnorr(bytes.fromhex(bad["id"])).hex()
        with self.assertRaises(ValueError): f.verify_event(bad,key.public_key_xonly.format().hex())

    def test_two_different_events_for_same_logged_target_rejected(self):
        key,prior,l6,e6,v6,l8,e8,v8=pair()
        target=f.target_for_event(v8)
        other=copy.deepcopy(v8);other["created_at"]+=1
        other["id"]=f.nostr_event_id(other);other["sig"]=key.sign_schnorr(bytes.fromhex(other["id"])).hex()
        with patch("external_floor.target_for_event", return_value=target):
            with self.assertRaises(ValueError): f.extract_target([v8,other],target,key.public_key_xonly.format().hex())

if __name__=="__main__":
    unittest.main(verbosity=2)
