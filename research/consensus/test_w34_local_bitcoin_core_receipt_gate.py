#!/usr/bin/env python3
"""W34 synthetic RPC falsifiers. A simulated response NEVER verifies Bitcoin Core."""
from __future__ import annotations
import copy
import hashlib
import json
import subprocess
import unittest
from unittest.mock import patch

import w34_local_bitcoin_core_receipt_gate as lab

W32_BLOB="dab717f48a9483a7909f70f86b174cadce0ca171"


class W34(unittest.TestCase):
    def setUp(self):
        self.roots=lab.load_receipt_roots()
        raw=subprocess.run(
            ["git","cat-file","blob",W32_BLOB],
            cwd=str(lab.REPO),capture_output=True,check=True
        ).stdout
        self.w32=json.loads(raw)
        self.headers={
            x["height"]:x["public_api_checks"][0]["header_hex"]
            for x in self.w32["results"]
        }
        self.height=976700
        self.tip="f"*64
        self.info={
            "chain":"main","blocks":self.height,"headers":self.height,
            "bestblockhash":self.tip,"verificationprogress":1.0,
            "initialblockdownload":False,"chainwork":"0"*60+"ffff",
            "pruned":True
        }
        self.calls=[]
        self.forcehash={}
        self.forceheader={}
        self.raise_method=None

    def rpc(self,method,*params):
        self.calls.append((method,params))
        if self.raise_method==method:
            raise RuntimeError("mock missing Core RPC")
        if method=="getblockchaininfo":
            return self.info
        if method=="getblockhash":
            height=params[0]
            if height in self.forcehash:return self.forcehash[height]
            if height==0:return lab.GENESIS
            if height==self.height:return self.tip
            return lab.EXPECTED[height]["blockhash"]
        if method=="getblockheader":
            h=params[0]
            if h in self.forceheader:return self.forceheader[h]
            for height in self.headers:
                if lab.EXPECTED[height]["blockhash"]==h:
                    return self.headers[height]
            raise ValueError("unrecognized hash")
        raise AssertionError("Unexpected method "+method)

    def outcome(self):
        return lab.evaluate(self.rpc,receipts=self.roots)

    def check_hold(self,reason):
        r=self.outcome()
        self.assertEqual(r["reason"],reason,r)
        self.assertEqual(r["status"],"HOLD")
        self.assertEqual(r["genesis"],"NO_GO")
        self.assertEqual(r["production"],"NO_GO")
        self.assertEqual(r["authority"],"NONE")
        self.assertFalse(r["fully_validated_bitcoin_node_independently_attested"])

    def test_01_original_two_ots_proofs_bound_to_w31(self):
        self.assertEqual(set(self.roots),{976596,976598})
        self.assertEqual({h["blockhash"] for h in self.roots.values()},
                         {x["blockhash"] for x in lab.EXPECTED.values()})
    def test_02_ots_roots_match_w32_raw_headers(self):
        for height,header in self.headers.items():
            expected=self.roots[height]
            self.assertTrue(lab.check_header(header,expected["blockhash"],expected["raw_merkle_root"]))
    def test_03_perfect_fake_rpc_is_still_hold(self):
        r=self.outcome()
        self.assertEqual(r["reason"],"LOCAL_CORE_RPC_CLAIMS_MATCH_ORIGINAL_OTS_PROOFS_BUT_OPERATOR_UNATTESTED")
        self.assertEqual(r["core_rpc_observation"],"CALLER_RPC_ADAPTER_MATCHES_PINNED_HEADERS")
        self.assertFalse(r["fully_validated_bitcoin_node_independently_attested"])
        self.assertEqual(r["bitcoin_core_operator_provenance"],"NOT_ESTABLISHED")
        self.assertEqual(r["c2sp_external_custody"],"NOT_ESTABLISHED")
    def test_04_only_read_only_methods_used(self):
        self.outcome()
        self.assertEqual([x[0] for x in self.calls],[
            "getblockchaininfo","getblockhash","getblockhash","getblockheader",
            "getblockhash","getblockheader","getblockhash"])
    def test_05_regtest_denied(self):
        self.info["chain"]="regtest";self.check_hold("CORE_NOT_SYNCED_MAINNET_OR_BAD_STATUS")
    def test_06_testnet_denied(self):
        self.info["chain"]="test";self.check_hold("CORE_NOT_SYNCED_MAINNET_OR_BAD_STATUS")
    def test_07_ibd_denied(self):
        self.info["initialblockdownload"]=True;self.check_hold("CORE_NOT_SYNCED_MAINNET_OR_BAD_STATUS")
    def test_08_low_progress_denied(self):
        self.info["verificationprogress"]=0.70;self.check_hold("CORE_NOT_SYNCED_MAINNET_OR_BAD_STATUS")
    def test_09_boolean_progress_denied(self):
        self.info["verificationprogress"]=True;self.check_hold("CORE_NOT_SYNCED_MAINNET_OR_BAD_STATUS")
    def test_10_too_early_height_no_six_conf_denied(self):
        self.info["blocks"]=976600;self.info["headers"]=976600
        self.check_hold("CORE_NOT_SYNCED_MAINNET_OR_BAD_STATUS")
    def test_11_boolean_height_denied(self):
        self.info["blocks"]=True;self.check_hold("CORE_NOT_SYNCED_MAINNET_OR_BAD_STATUS")
    def test_12_unsynced_headers_denied(self):
        self.info["headers"]=self.height+100;self.check_hold("CORE_NOT_SYNCED_MAINNET_OR_BAD_STATUS")
    def test_13_missing_pruned_bool_denied(self):
        self.info["pruned"]="false";self.check_hold("CORE_NOT_SYNCED_MAINNET_OR_BAD_STATUS")
    def test_14_zero_chainwork_denied(self):
        self.info["chainwork"]="00000";self.check_hold("CORE_NOT_SYNCED_MAINNET_OR_BAD_STATUS")
    def test_15_nonhex_chainwork_denied(self):
        self.info["chainwork"]="invalid";self.check_hold("CORE_NOT_SYNCED_MAINNET_OR_BAD_STATUS")
    def test_16_wrong_genesis_denied(self):
        self.forcehash[0]="0"*64;self.check_hold("GENESIS_MISMATCH")
    def test_17_wrong_block_976596_denied(self):
        self.forcehash[976596]="0"*64;self.check_hold("LOCAL_CORE_BLOCKHASH_MISMATCH")
    def test_18_wrong_block_976598_denied(self):
        self.forcehash[976598]="0"*64;self.check_hold("LOCAL_CORE_BLOCKHASH_MISMATCH")
    def test_19_modified_raw_header_denied(self):
        h=lab.EXPECTED[976596]["blockhash"]
        raw=bytearray.fromhex(self.headers[976596]);raw[-1]^=1
        self.forceheader[h]=raw.hex()
        self.check_hold("LOCAL_CORE_HEADER_OR_OTS_MERKLE_MISMATCH")
    def test_20_missing_header_rpc_denied(self):
        self.raise_method="getblockheader"
        self.check_hold("CORE_RPC_RESPONSE_MALFORMED_OR_UNAVAILABLE")
    def test_21_bad_tip_hash_denied(self):
        self.forcehash[self.height]="0"*64
        self.check_hold("CORE_TIP_CHANGED_DURING_REVIEW_RETRY_REQUIRED")
    def test_22_missing_rpc_denied(self):
        self.raise_method="getblockchaininfo"
        self.check_hold("CORE_RPC_UNAVAILABLE_OR_UNTRUSTED")
    def test_23_attacker_swaps_expected_ots_merkle(self):
        changed=copy.deepcopy(self.roots)
        changed[976596]["raw_merkle_root"]="0"*64
        r=lab.evaluate(self.rpc,receipts=changed)
        self.assertEqual(r["reason"],"LOCAL_CORE_HEADER_OR_OTS_MERKLE_MISMATCH")
    def test_24_no_api_that_authorizes_trust(self):
        r=self.outcome()
        self.assertEqual(r["signatures_issued"],0)
        self.assertEqual(r["calendar_posts"],0)
        self.assertFalse(r["memory_admitted"])
        self.assertFalse(r["actual_ario_log_witnessed"])
    def test_25_invalid_ots_proof_bad_digest_with_user_loader(self):
        raw=lab.git_blob_raw(lab.OTS_BLOB)
        wrong=json.loads(raw)
        wrong["w31_preimage_sha256"]="0"*64
        with self.assertRaises(ValueError):
            lab.load_receipt_roots(raw_loader=lambda h:json.dumps(wrong).encode())
    def test_26_ots_receipt_malformed_noncanonical(self):
        raw=lab.git_blob_raw(lab.OTS_BLOB)
        wrong=json.loads(raw)
        wrong["results"][0]["upgraded_ots_b64"]="*"
        with self.assertRaises(ValueError):
            lab.load_receipt_roots(raw_loader=lambda h:json.dumps(wrong).encode())
    def test_27_ots_receipt_wrong_claimed_sha(self):
        raw=lab.git_blob_raw(lab.OTS_BLOB)
        wrong=json.loads(raw)
        wrong["results"][0]["upgraded_ots_sha256"]="0"*64
        with self.assertRaises(ValueError):
            lab.load_receipt_roots(raw_loader=lambda h:json.dumps(wrong).encode())
    def test_28_unexpected_evidence_git_blob_not_readable(self):
        with self.assertRaises(ValueError):lab.git_blob_raw("a"*40)
    def test_29_non_read_only_bitcoin_rpc_refused_without_subprocess(self):
        with self.assertRaises(ValueError):lab.local_bitcoin_cli("sendrawtransaction","danger")
    def test_30_wrong_node_height_method_denied(self):
        with self.assertRaises(ValueError):lab.local_bitcoin_cli("getblockhash",True)
    def test_31_fake_header_rpc_bool_denied(self):
        with self.assertRaises(ValueError):lab.local_bitcoin_cli("getblockheader","0"*64,True)
    def test_32_no_cli_available_is_reported_honestly(self):
        with patch.object(lab.subprocess,"run",side_effect=FileNotFoundError()):
            with self.assertRaises(RuntimeError):lab.local_bitcoin_cli("getblockchaininfo")
    def test_33_mutated_pow_target_denied(self):
        raw=bytearray.fromhex(self.headers[976598])
        raw[72:76]=(0x207fffff).to_bytes(4,"little")
        self.assertFalse(lab.check_header(raw.hex(),lab.EXPECTED[976598]["blockhash"],
                                          self.roots[976598]["raw_merkle_root"]))
    def test_34_no_runtime_can_override_hard_no_go_labels(self):
        r=lab.verdict("x",production="YES",trust_activation="YES")
        self.assertEqual(r["reason"],"UNEXPECTED_DIAGNOSTIC_FIELD")
        self.assertEqual(r["genesis"],"NO_GO")
        self.assertEqual(r["production"],"NO_GO")
        self.assertEqual(r["trust_activation"],"NO_GO")
    def test_35_offline_verifier_requires_no_bitcoin_node(self):
        r=lab.verdict("VALID_ORIGINAL_PUBLIC_W31_OTS_INPUT_ONLY",
                      input_git_blob=lab.OTS_BLOB,input_digest=lab.DIGEST)
        self.assertEqual(r["status"],"HOLD")
        self.assertFalse(r["fully_validated_bitcoin_node_independently_attested"])
    def test_36_forged_pruned_node_flag_does_not_prove_custody(self):
        self.info["pruned"]=False
        self.assertEqual(self.outcome()["bitcoin_core_operator_provenance"],
                         "NOT_ESTABLISHED")
    def test_37_min_confirmations_at_976604_in_mock(self):
        self.info["blocks"]=976604;self.info["headers"]=976604
        self.height=976604
        self.assertEqual(self.outcome()["status"],"HOLD")
    def test_38_missing_bestblockhash_rejected(self):
        del self.info["bestblockhash"]
        self.check_hold("CORE_NOT_SYNCED_MAINNET_OR_BAD_STATUS")
    def test_39_bad_rpc_result_non_dict_denied(self):
        self.info="fake"
        self.check_hold("CORE_NOT_SYNCED_MAINNET_OR_BAD_STATUS")
    def test_40_invalid_raw_header_bitcoin_not_trusted(self):
        self.assertFalse(lab.check_header("0"*160,lab.EXPECTED[976596]["blockhash"],
                                          self.roots[976596]["raw_merkle_root"]))

if __name__=="__main__":
    unittest.main(verbosity=2)
