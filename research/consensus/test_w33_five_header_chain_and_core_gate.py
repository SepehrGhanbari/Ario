#!/usr/bin/env python3
"""W33 falsifiers: original W32 real headers, mocked new headers, no network."""
from __future__ import annotations
import copy
import unittest
from unittest.mock import patch
import urllib.error
import w33_five_header_chain_and_core_gate as lab


class W33(unittest.TestCase):
    def setUp(self):
        self.pinned=lab.stored_w32()
        self.a=self.pinned[976596]
        self.b=self.pinned[976598]
        self.fake=[]
        for h in lab.FETCH_HEIGHTS:
            for provider in lab.PROVIDERS:
                self.fake.append({"provider":provider,"height":h,
                    "status":"HEADER_HASH_POW_PASS",
                    "header_hex":self.a["header_hex"],
                    "info":lab.header_info(self.a["header_hex"])})
    def test_01_exact_pins_still_w32(self):
        self.assertEqual(set(self.pinned),{976596,976598})
        self.assertEqual(self.a["info"]["hash"],"00000000000000000000a6c168915b99fd83334afdc40023901275ac3064ab2d")
        self.assertEqual(self.b["info"]["hash"],"00000000000000000000cc5208897fe9ecf9e7ef72cf8b20140599a3d8e0c5b1")
    def test_02_actual_pinned_headers_have_pow(self):
        self.assertEqual(len(self.a["header_hex"]),160)
        self.assertEqual(len(self.b["header_hex"]),160)
    def test_03_mutated_pow_fails(self):
        h=list(self.a["header_hex"])
        h[-1]="0" if h[-1]!="0" else "1"
        with self.assertRaises(ValueError):
            lab.header_info("".join(h))
    def test_04_wrong_header_length(self):
        with self.assertRaises(ValueError):lab.header_info("ab"*79)
    def test_05_invalid_header_hex(self):
        with self.assertRaises(ValueError):lab.header_info("zz"*80)
    def test_06_false_powlimit_target(self):
        h=bytearray.fromhex(self.a["header_hex"])
        h[72:76]=(0x207fffff).to_bytes(4,"little")
        with self.assertRaises(ValueError):lab.header_info(h.hex())
    def test_07_unknown_provider_refused(self):
        with self.assertRaises(ValueError):lab.fetch_one("malicious",976597)
    def test_08_nonlisted_height_refused(self):
        with self.assertRaises(ValueError):lab.fetch_one("mempool",976596)
    def test_09_bool_not_an_allowed_height(self):
        with self.assertRaises(ValueError):lab.fetch_one("mempool",True)
    def test_10_read_endpoint_rejects_http(self):
        with self.assertRaises(ValueError):lab._read_endpoint("http://blockstream.info/api/block-height/976597")
    def test_11_read_endpoint_rejects_path_traversal(self):
        with self.assertRaises(ValueError):lab._read_endpoint("https://mempool.space/api/../secrets")
    def test_12_redirect_refused(self):
        self.assertIsNone(lab.NoRedirect().redirect_request(None,None,302,"no",{},"https://other.invalid"))
    def test_13_missing_two_explorer_rows(self):
        self.assertEqual(lab.validate_five(self.pinned, self.fake[:-1])["reason"],
                         "EXPECTED_SIX_EXTERNAL_HEADER_RESPONSES")
    def test_14_duplicate_explorer_identity(self):
        self.fake[-1]=copy.deepcopy(self.fake[0])
        self.assertEqual(lab.validate_five(self.pinned,self.fake)["reason"],
                         "DUPLICATE_HEIGHT_PROVIDER")
    def test_15_explorer_unavailable_no_silent_success(self):
        self.fake[0]["status"]="BLOCKHASH_UNAVAILABLE"
        self.assertEqual(lab.validate_five(self.pinned,self.fake)["reason"],
                         "MISSING_OR_INVALID_PROVIDER_RESULT")
    def test_16_tampered_redundant_parsed_fields_refused(self):
        self.fake[0]["info"]["time"]=1
        self.assertEqual(lab.validate_five(self.pinned,self.fake)["reason"],
                         "UNTRUSTWORTHY_PARSED_HEADER_METADATA")
    def test_17_different_sources_can_disagree(self):
        self.fake[1]["header_hex"]=self.b["header_hex"]
        self.fake[1]["info"]=self.b["info"]
        self.assertEqual(lab.validate_five(self.pinned,self.fake)["reason"],
                         "TWO_EXPLORERS_REPORT_DIFFERENT_BYTES")
    def test_18_correctly_hashed_pieces_are_not_a_linked_chain(self):
        self.assertEqual(lab.validate_five(self.pinned,self.fake)["reason"],
                         "BROKEN_PREVIOUS_HEADER_LINK")
    def test_19_no_api_call_in_offline_mode(self):
        with patch.object(lab,"fetch_one",side_effect=AssertionError("NO GET ALLOWED")):
            obj=lab.run(online=False)
        self.assertEqual(obj["verdict"]["status"],"HOLD")
        self.assertEqual(obj["get_requests_max"],0)
        self.assertEqual(obj["http_posts"],0)
    def test_20_core_gate_bad_chain_denied(self):
        snap={"chain":"regtest","blocks":1000000,"headers":1000000,
              "initialblockdownload":False,"verificationprogress":1.0,
              "hash_at_976596":self.a["info"]["hash"],
              "hash_at_976598":self.b["info"]["hash"]}
        x=lab.core_gate(snap,{976596:self.a["info"]["hash"],976598:self.b["info"]["hash"]})
        self.assertEqual(x["reason"],"CORE_RPC_SYNC_OR_CHAIN_NOT_ESTABLISHED")
    def test_21_core_gate_ibid_true_denied(self):
        snap={"chain":"main","blocks":976600,"headers":976600,
              "initialblockdownload":True,"verificationprogress":1.0,
              "hash_at_976596":self.a["info"]["hash"],
              "hash_at_976598":self.b["info"]["hash"]}
        self.assertEqual(lab.core_gate(snap,{976596:self.a["info"]["hash"],976598:self.b["info"]["hash"]})["reason"],"CORE_RPC_SYNC_OR_CHAIN_NOT_ESTABLISHED")
    def test_22_core_gate_user_supplied_fields_never_prove_node(self):
        snap={"chain":"main","blocks":976600,"headers":976600,
              "initialblockdownload":False,"verificationprogress":1.0,
              "hash_at_976596":self.a["info"]["hash"],
              "hash_at_976598":self.b["info"]["hash"]}
        r=lab.core_gate(snap,{976596:self.a["info"]["hash"],976598:self.b["info"]["hash"]})
        self.assertEqual(r["reason"],"CORE_RPC_FIELDS_MATCH_ONLY_UNAUTHENTICATED")
        self.assertEqual(r["bitcoin_consensus_full_node"],"NOT_ESTABLISHED")
        self.assertEqual(r["status"],"HOLD")
    def test_23_core_gate_wrong_pinned_hash_denied(self):
        snap={"chain":"main","blocks":976600,"headers":976600,
              "initialblockdownload":False,"verificationprogress":1.0,
              "hash_at_976596":"0"*64,
              "hash_at_976598":self.b["info"]["hash"]}
        self.assertEqual(lab.core_gate(snap,{976596:self.a["info"]["hash"],976598:self.b["info"]["hash"]})["reason"],"CORE_RPC_CHECKPOINT_HASH_MISMATCH")
    def test_24_core_gate_malformed_dict_denied(self):
        self.assertEqual(lab.core_gate({}, {})["reason"],"CORE_RPC_SNAPSHOT_MALFORMED")
    def test_25_offline_no_genesis_trust_or_memory(self):
        verdict=lab.run(online=False)["verdict"]
        self.assertEqual(verdict["genesis"],"NO_GO")
        self.assertEqual(verdict["trust_activation"],"NO_GO")
        self.assertEqual(verdict["production"],"NO_GO")
        self.assertFalse(verdict["memory_admitted"])
    def test_26_full_chain_from_five_headers_is_not_mainnet_consensus(self):
        self.assertEqual(lab.result("fake")["bitcoin_consensus_full_node"],"NOT_ESTABLISHED")
        self.assertEqual(lab.result("fake")["independent_c2sp_witness"],"NOT_ESTABLISHED")
    def test_27_caller_substitution_of_w32_anchor_is_refused(self):
        forged=copy.deepcopy(self.pinned)
        forged[976596]["header_hex"]=self.b["header_hex"]
        self.assertEqual(lab.validate_five(forged,self.fake)["reason"],
                         "PINNED_W32_ANCHOR_SUBSTITUTION")
    def test_28_external_code_cannot_override_no_go_result(self):
        x=lab.result("fake",production="YES",trust_activation="YES")
        self.assertEqual(x["reason"],"UNEXPECTED_DIAGNOSTIC_FIELD")
        self.assertEqual(x["production"],"NO_GO")
        self.assertEqual(x["trust_activation"],"NO_GO")

if __name__=="__main__":
    unittest.main(verbosity=2)
