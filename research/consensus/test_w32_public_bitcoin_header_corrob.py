#!/usr/bin/env python3
"""W32 Bitcoin raw-header validation boundary tests. ALL OFFLINE.

Mempool/Blockstream lookup fields can be faked in this test; raw Bitcoin
header hash/PoW checking is NOT the same as validating chain consensus.
"""
import hashlib
import unittest
from unittest.mock import patch
import w32_public_bitcoin_header_corrob as lab

GENESIS=("01000000" + "00"*32 +
         "3ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a"
         + "29ab5f49" + "ffff001d" + "1dac2b7c")
GENESIS_HASH="000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"

class W32Bitcoin(unittest.TestCase):
    def test_01_real_genesis_80_byte_header_hash(self):
        self.assertEqual(len(bytes.fromhex(GENESIS)),80)
        self.assertEqual(lab.hash_header(bytes.fromhex(GENESIS)),GENESIS_HASH)
    def test_02_genesis_pow_meets_mainnet_target(self):
        self.assertTrue(lab.pow_valid(bytes.fromhex(GENESIS)))
    def test_03_wrong_size_header_denied(self):
        with self.assertRaises(ValueError):lab.hash_header(b"bad")
        self.assertFalse(lab.pow_valid(b"bad"))
    def test_04_corrupt_nonce_fails_header_hash(self):
        raw=bytearray.fromhex(GENESIS)
        raw[-1]^=1
        self.assertNotEqual(lab.hash_header(bytes(raw)),GENESIS_HASH)
    def test_05_corrupt_merkle_is_not_original(self):
        raw=bytearray.fromhex(GENESIS)
        raw[36]^=1
        self.assertNotEqual(raw[36:68],bytes.fromhex(GENESIS)[36:68])
    def test_06_unknown_provider_rejected(self):
        with self.assertRaises(ValueError):
            lab.explorer_header("my.fake-provider",976596)
    def test_07_unapproved_block_height_rejected(self):
        with self.assertRaises(ValueError):
            lab.explorer_header("blockstream",976595)
    def test_08_disallow_http_host_switch(self):
        with self.assertRaises(ValueError):
            lab.get_plain_text("http://blockstream.info/api/block-height/976596")
    def test_09_disallow_duplicate_or_traversal_path(self):
        with self.assertRaises(ValueError):
            lab.get_plain_text("https://blockstream.info/api/../evade")
    def test_10_disallow_redirect_to_another_host(self):
        self.assertIsNone(lab.NoRedirect().redirect_request(None,None,301,"Move",{},"https://evil.invalid/"))
    def test_11_read_exact_pinned_real_proofs(self):
        r=lab.saved_proof_views()
        self.assertEqual(len(r),2)
        self.assertEqual({x["height"] for x in r},{976596,976598})
        self.assertEqual({x["upgraded_ots_sha256"] for x in r},{
            "5968fd87749621f96c42d1763bd41a8d457187cd55380d2e1ca7132a4518ac35",
            "886a46e7ffe9bc7dcb4d8a118bf98cc1805fa5df7f6002aa1fb15573648dc70a"
        })
    def test_12_mocked_api_header_hash_and_pow(self):
        def fake(url):
            if "/block-height/" in url:return GENESIS_HASH
            if "/header" in url:return GENESIS
            self.fail("Unexpected GET")
        x=lab.explorer_header("blockstream",976596,getter=fake)
        self.assertEqual(x["status"],"RAW_HEADER_HASH_AND_POW_MATCHED")
        self.assertEqual(x["derived_block_hash"],GENESIS_HASH)
    def test_13_mocked_different_blockhash_fails(self):
        def fake(url):
            return "f"*64 if "/block-height/" in url else GENESIS
        x=lab.explorer_header("blockstream",976596,getter=fake)
        self.assertEqual(x["status"],"INVALID_HEADER_HASH_OR_POW")
    def test_14_missing_api_result_never_passes(self):
        x=lab.explorer_header("mempool",976598,getter=lambda url: None)
        self.assertEqual(x["status"],"HEIGHT_LOOKUP_UNAVAILABLE")
    def test_15_missing_raw_header_never_passes(self):
        x=lab.explorer_header("mempool",976598,getter=lambda url: GENESIS_HASH if "block-height" in url else None)
        self.assertEqual(x["status"],"HEADER_UNAVAILABLE_OR_MALFORMED")
    def test_16_both_mocked_genesis_are_not_real_proof_merkle_roots(self):
        def fake(url):
            return GENESIS_HASH if "block-height" in url else GENESIS
        result=lab.run(offline=False,getter=fake)
        self.assertEqual(len(result["results"]),2)
        self.assertTrue(all(x["result"]=="NOT_CORROBORATED_OR_MISSING_PROVIDER" for x in result["results"]))
        self.assertFalse(result["full_bitcoin_header_chain_validated"])
        self.assertEqual(result["calendar_posts"],0)
    def test_17_offline_never_contacts_explorers(self):
        with patch.object(lab,"get_plain_text",side_effect=AssertionError("UNEXPECTED GET")):
            result=lab.run(offline=True)
        self.assertTrue(all(x["result"]=="OFFLINE_NO_EXTERNAL_HEADERS" for x in result["results"]))
        self.assertEqual(result["calendar_posts"],0)
    def test_18_mainnet_pow_limit_not_regtest_limit(self):
        raw=bytearray.fromhex(GENESIS)
        raw[72:76]=(0x207fffff).to_bytes(4,"little")
        self.assertFalse(lab.pow_valid(bytes(raw)))
    def test_19_no_internal_network_stamping_interface(self):
        self.assertFalse(hasattr(lab,"stamp"))
        self.assertFalse(hasattr(lab,"submit"))
    def test_20_no_trust_approval(self):
        result=lab.run(offline=True)
        self.assertEqual(result["trust_activation"],"NO_GO")
        self.assertEqual(result["genesis"],"NO_GO")
        self.assertEqual(result["production"],"NO_GO")
        self.assertFalse(result["bitcoin_node_connected"])
    def test_21_unsupported_raw_block_height_bounded(self):
        for bad in (-1,True,"976596",0):
            with self.assertRaises(ValueError):lab.explorer_header("blockstream",bad)
    def test_22_fake_explorer_404_does_not_prove_absence(self):
        self.assertEqual(lab.explorer_header("blockstream",976596,getter=lambda url:None)["status"],"HEIGHT_LOOKUP_UNAVAILABLE")

if __name__=="__main__":
    unittest.main(verbosity=2)
