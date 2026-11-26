"""Adversarial RED before patch; no network access, no real release writes."""
from email.message import Message
import hashlib
import http.client
import json
from dataclasses import replace
from pathlib import Path
from unittest import TestCase, mock
from tempfile import TemporaryDirectory

import ario_github_crosscheck_v0_2 as m

class AdversarialGreenR1Tests(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'ario-full.txt'
        self.payload=b'Ario adversarial synthetic payload\x00'
        self.path.write_bytes(self.payload)
        self.doc={'commit':m.RELEASE.source_commit,'git_tree':m.RELEASE.source_tree,'tracked_files':204,
                  'ario-full.txt':{'bytes':len(self.payload),'sha256':hashlib.sha256(self.payload).hexdigest()}}
        self.refbytes=json.dumps(self.doc,sort_keys=True).encode()
        self.cfg=replace(m.RELEASE,checksums_sha256=hashlib.sha256(self.refbytes).hexdigest())

    def test_red_http_exception_at_open_must_be_unknown(self):
        class BrokenOpen:
            def open(self, request, timeout):
                raise http.client.BadStatusLine('synthetic bad-status-line')
        with mock.patch.object(m.urllib.request,'build_opener',return_value=BrokenOpen()):
            with self.assertRaises(m.ReferenceUnknown):
                m.fetch_official_reference(m.RELEASE)

    def test_red_incomplete_reference_body_must_be_unknown(self):
        class BadResponse:
            headers = Message()
            status=200
            def __init__(self,url): self.url=url
            def geturl(self): return self.url
            def read(self,*a): raise http.client.IncompleteRead(b'partial',12)
            def __enter__(self):return self
            def __exit__(self,*a):return False
        class BrokenRead:
            def open(self,request,timeout):return BadResponse(request.full_url)
        with mock.patch.object(m.urllib.request,'build_opener',return_value=BrokenRead()):
            with self.assertRaises(m.ReferenceUnknown):
                m.fetch_official_reference(m.RELEASE)

    def test_red_partial_declared_http_body_must_be_unknown(self):
        class PartialResponse:
            headers = Message()
            status = 200
            length = 6  # mimics HTTPResponse.read(n) retaining Content-Length shortfall
            def __init__(self, url): self.url = url
            def geturl(self): return self.url
            def read(self, n): return b'abc'
            def __enter__(self): return self
            def __exit__(self,*a): return False
        class BrokenOpener:
            def open(self,request,timeout): return PartialResponse(request.full_url)
        with mock.patch.object(m.urllib.request,'build_opener',return_value=BrokenOpener()):
            with self.assertRaises(m.ReferenceUnknown):
                m.fetch_official_reference(m.RELEASE)

    def test_red_injected_reference_must_not_claim_live_github(self):
        result=m.verify_file(self.path,'ario-full.txt',self.cfg,fetcher=lambda _:self.refbytes)
        self.assertNotEqual(result['status'],'GITHUB_RELEASE_BYTES_MATCH')
        self.assertEqual(result.get('reference_transport'),'CALLER_SUPPLIED_TRANSPORT_UNVERIFIED')

    def test_red_config_traversal_must_be_rejected(self):
        malicious=replace(self.cfg,checksums_path='releases/../unintended.json')
        with self.assertRaises(m.VerificationRejected):m.url_for(malicious)

    def test_red_tracking_count_type_must_be_strict(self):
        self.doc['tracked_files']=204.0
        self.refbytes=json.dumps(self.doc).encode()
        self.cfg=replace(self.cfg,checksums_sha256=hashlib.sha256(self.refbytes).hexdigest())
        with self.assertRaises(m.VerificationRejected):
            m.parse_reference(self.refbytes,self.cfg,'ario-full.txt')

    def test_red_float_exponent_in_unused_field_must_be_rejected(self):
        ref=self.refbytes[:-1]+b', "extra": 1e999}'
        cfg=replace(self.cfg,checksums_sha256=hashlib.sha256(ref).hexdigest())
        with self.assertRaises(m.VerificationRejected):
            m.parse_reference(ref,cfg,'ario-full.txt')

    def test_red_nonfinite_extra_metadata_must_be_rejected(self):
        self.doc['extra']=float('inf')
        self.refbytes=json.dumps(self.doc).encode()
        self.cfg=replace(self.cfg,checksums_sha256=hashlib.sha256(self.refbytes).hexdigest())
        with self.assertRaises(m.VerificationRejected):
            m.parse_reference(self.refbytes,self.cfg,'ario-full.txt')
