#!/usr/bin/env python3
"""W32 offline-only independent-looking falsifiers (NOT third-party review).

No network call is made in this test module. Existing published W31 signed
public digest, real pending receipts and source-hash are used as fixtures.
"""
from __future__ import annotations
import base64
import hashlib
from io import BytesIO
import json
import unittest
from unittest.mock import patch
import urllib.error

from opentimestamps.core.timestamp import Timestamp
from opentimestamps.core.serialize import StreamSerializationContext
from opentimestamps.core.notary import PendingAttestation, BitcoinBlockHeaderAttestation

import w32_read_only_ots_upgrade as lab


class Response:
    def __init__(self, content, status=200):
        self.status=status
        self.body=content
        self.headers={"Content-Type":"application/vnd.opentimestamps.v1"}
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,count):return self.body[:count]

class Opener:
    def __init__(self,response):
        self.response=response
        self.requests=[]
    def open(self,req,timeout):
        self.requests.append((req.full_url,req.get_method(),req.data,timeout))
        if isinstance(self.response,Exception):raise self.response
        return self.response

def serialized_timestamp(msg,calendar=None,height=None):
    t=Timestamp(msg)
    if calendar:
        t.attestations.add(PendingAttestation(calendar))
    if height is not None:
        t.attestations.add(BitcoinBlockHeaderAttestation(height))
    buf=BytesIO()
    t.serialize(StreamSerializationContext(buf))
    return buf.getvalue()


class W32(unittest.TestCase):
    def setUp(self):
        self.fixtures=lab.originals()
        self.first=self.fixtures[0]
    def test_01_original_w31_preimage_is_unchanged(self):
        self.assertEqual(lab.EXPECTED_DIGEST,"2078bc80586d0e4b00afa48eb8dea31ab3d4749b4912c57a897e4d5e2fb436df")
        self.assertEqual(len(self.fixtures),2)
    def test_02_exact_calendar_allowlist(self):
        self.assertEqual(set(f[0] for f in self.fixtures),lab.ALLOWLIST)
    def test_03_original_pending_proof_binding_is_valid(self):
        for url,commit,detached,raw in self.fixtures:
            self.assertEqual(detached.file_digest.hex(),lab.EXPECTED_DIGEST)
            self.assertTrue(1 <= len(commit) <= 64)
            self.assertEqual(lab._serialize_detached(detached),raw)
    def test_04_unlisted_calendar_denied_before_request(self):
        with self.assertRaises(ValueError):
            lab.get_existing_timestamp("https://evil.invalid",b"a"*32)
    def test_05_short_commitment_denied(self):
        with self.assertRaises(ValueError):
            lab.get_existing_timestamp(self.first[0],b"a")
    def test_06_only_one_get_exact_existing_timestamp_path(self):
        op=Opener(Response(b"synthetic"))
        ret=lab.get_existing_timestamp(self.first[0],self.first[1],opener=op)
        self.assertEqual(ret["fetch"],"HTTP_200_PROOF_BYTES")
        self.assertEqual(len(op.requests),1)
        url,method,data,timeout=op.requests[0]
        self.assertEqual(url,self.first[0]+"/timestamp/"+self.first[1].hex())
        self.assertEqual(method,"GET")
        self.assertIsNone(data)
        self.assertEqual(timeout,12)
    def test_07_pending_404_not_proof_of_confirmation(self):
        op=Opener(urllib.error.HTTPError("https://x",404,"pending",{},None))
        ret=lab.get_existing_timestamp(self.first[0],self.first[1],opener=op)
        self.assertEqual(ret["fetch"],"PENDING_NOT_UPGRADED")
        self.assertEqual(ret["http_status"],404)
    def test_08_redirect_refused(self):
        self.assertIsNone(lab.NoRedirect().redirect_request(None,None,302,"new",{},"https://bad.invalid"))
    def test_09_http500_is_not_success(self):
        op=Opener(urllib.error.HTTPError("https://x",500,"error",{},None))
        self.assertEqual(lab.get_existing_timestamp(self.first[0],self.first[1],opener=op)["fetch"],"HTTP_FAILURE")
    def test_10_oversized_body_denied(self):
        op=Opener(Response(b"z"*(lab.MAX_REMOTE+1)))
        self.assertEqual(lab.get_existing_timestamp(self.first[0],self.first[1],opener=op)["fetch"],"HTTP_OR_SIZE_FAILURE")
    def test_11_non200_body_not_success(self):
        op=Opener(Response(b"body",status=201))
        self.assertEqual(lab.get_existing_timestamp(self.first[0],self.first[1],opener=op)["fetch"],"HTTP_OR_SIZE_FAILURE")
    def test_12_invalid_remote_binary_cannot_upgrade(self):
        url,commit,det,raw=self.first
        r=lab.check_one(url,commit,det,raw,getter=lambda u,c:{"fetch":"HTTP_200_PROOF_BYTES","http_status":200,"response_bytes":b"bad"})
        self.assertIn(r["result"],("INVALID_REMOTE_PROOF","REMOTE_PROOF_PARSE_FAILED"))
        self.assertFalse(r["independent_bitcoin_consensus_verification"])
    def test_13_wrong_commitment_cannot_upgrade(self):
        url,commit,det,raw=self.first
        bogus=serialized_timestamp(b"\0"*32,calendar=url)
        r=lab.check_one(url,commit,det,raw,getter=lambda u,c:{"fetch":"HTTP_200_PROOF_BYTES","http_status":200,"response_bytes":bogus})
        self.assertEqual(r["result"],"INVALID_REMOTE_PROOF")
    def test_14_valid_returned_pending_attestation_still_no_bitcoin(self):
        url,commit,det,raw=self.first
        valid=serialized_timestamp(commit,calendar=url)
        r=lab.check_one(url,commit,det,raw,getter=lambda u,c:{"fetch":"HTTP_200_PROOF_BYTES","http_status":200,"response_bytes":valid})
        self.assertEqual(r["result"],"PROOF_UPDATED_BUT_STILL_PENDING")
        self.assertEqual(r["bitcoin_attestations_claimed_by_calendar"],[])
        self.assertFalse(r["bitcoin_consensus_verified"])
        self.assertEqual(lab._parse_detached(base64.b64decode(r["upgraded_ots_b64"])).file_digest.hex(),lab.EXPECTED_DIGEST)
    def test_15_fake_block_header_claim_is_not_independent_verification(self):
        url,commit,det,raw=self.first
        forged=serialized_timestamp(commit,height=888888)
        r=lab.check_one(url,commit,det,raw,getter=lambda u,c:{"fetch":"HTTP_200_PROOF_BYTES","http_status":200,"response_bytes":forged})
        self.assertEqual(r["result"],"CALENDAR_BITCOIN_ATTESTATION_UNVERIFIED")
        self.assertFalse(r["bitcoin_consensus_verified"])
        self.assertFalse(r["independent_bitcoin_consensus_verification"])
    def test_16_unavailable_calendar_keeps_pending_label(self):
        url,commit,det,raw=self.first
        r=lab.check_one(url,commit,det,raw,getter=lambda u,c:{"fetch":"PENDING_NOT_UPGRADED","http_status":404})
        self.assertEqual(r["result"],"PENDING_OR_UNAVAILABLE_NO_CONFIRMATION")
        self.assertNotIn("upgraded_ots_b64",r)
    def test_17_dry_run_zero_network_and_zero_authority(self):
        r=lab.run(offline=True)
        self.assertEqual(r["calendar_queries"],0)
        self.assertEqual(r["calendar_post_requests"],0)
        self.assertEqual(r["new_stamp_submissions"],0)
        self.assertEqual(r["genesis"],"NO_GO")
        self.assertEqual(r["trust_activation"],"NO_GO")
        self.assertEqual(r["production"],"NO_GO")
    def test_18_no_signing_or_timestamp_submit_api(self):
        self.assertFalse(hasattr(lab,"stamp"))
        self.assertFalse(hasattr(lab,"submit"))
        self.assertFalse(hasattr(lab,"sign"))
    def test_19_invalid_original_receipt_digest_rejected(self):
        original=lab.EXPECTED_DIGEST
        with patch.object(lab,"EXPECTED_DIGEST","0"*64):
            with self.assertRaises(ValueError):lab.originals()

if __name__=="__main__":
    unittest.main(verbosity=2)
