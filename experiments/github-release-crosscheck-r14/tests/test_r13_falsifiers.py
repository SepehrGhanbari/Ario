"""Independent stdlib-only, offline adversarial tests for R1.3 candidate.
The imported candidate is a scratch copy; no GitHub write or release activation.
"""
from dataclasses import replace
from email.message import Message
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

# Resolve only the adjacent scratch candidate. No global PYTHONPATH needed.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "candidate"))
import ario_github_crosscheck_v0_3 as v


class MemorySocket:
    def __init__(self, wire): self.wire = wire
    def makefile(self, mode): return io.BytesIO(self.wire)


class OfflineOpener:
    def __init__(self, response): self.response = response
    def open(self, request, timeout): return self.response


class R13Independent(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.file = Path(self.temp.name)/'manifest.txt'
        self.payload = b'hello synthetic manifest bytes\n'
        self.file.write_bytes(self.payload)
        self.doc = {
            'commit': v.RELEASE.source_commit,
            'git_tree': v.RELEASE.source_tree,
            'tracked_files': 204,
            'ario-manifest.json': {'bytes':len(self.payload),'sha256':hashlib.sha256(self.payload).hexdigest()},
        }
        self.registry = json.dumps(self.doc,sort_keys=True).encode('ascii')
        self.cfg = replace(v.RELEASE,checksums_sha256=hashlib.sha256(self.registry).hexdigest())

    def test_caller_supplied_fixture_does_not_claim_network_happened_or_did_not_happen(self):
        result=v.verify_file(self.file,'ario-manifest.json',self.cfg,fetcher=lambda _:self.registry)
        self.assertEqual(result['status'],'PINNED_REFERENCE_BYTES_MATCH_ORIGIN_UNVERIFIED')
        self.assertEqual(result['reference_transport'],'CALLER_SUPPLIED_TRANSPORT_UNVERIFIED')
        self.assertIn('whether GitHub was queried is unverified',result['qualification'])
        self.assertNotIn('GitHub was NOT queried',result['qualification'])

    def test_explicit_own_helper_may_have_queried_live_but_verifier_only_knows_callback(self):
        # Simulate the helper's internally verified return path, without network.
        # The source of the bytes remains opaque to verify_file(fetcher=...).
        with patch.object(v,'_retrieve_reference',return_value=(self.registry,True)):
            result=v.verify_file(self.file,'ario-manifest.json',self.cfg,fetcher=v.fetch_official_reference)
        self.assertEqual(result['reference_transport'],'CALLER_SUPPLIED_TRANSPORT_UNVERIFIED')
        self.assertNotIn('GitHub was NOT queried',result['qualification'])

    def test_explicit_provider_error_maps_to_unknown(self):
        def timeout(_): raise TimeoutError('synthetic provider timeout')
        with self.assertRaisesRegex(v.ReferenceUnknown,'provider failed'):
            v.verify_file(self.file,'ario-manifest.json',self.cfg,fetcher=timeout)

    def test_explicit_provider_reference_unknown_retains_classification(self):
        def unavailable(_): raise v.ReferenceUnknown('offline test condition')
        with self.assertRaisesRegex(v.ReferenceUnknown,'offline test condition'):
            v.verify_file(self.file,'ario-manifest.json',self.cfg,fetcher=unavailable)

    def test_bad_explicit_pins_are_rejected_not_type_error(self):
        pins=[None,123,b'x'*64,'é'*64,'x'*64,'a'*63,'a'*65,'a'*63+'!']
        for pin in pins:
            with self.subTest(pin=repr(pin)[:24]):
                with self.assertRaisesRegex(v.VerificationRejected,'invalid expected checksum registry pin'):
                    v.parse_reference(self.registry,replace(self.cfg,checksums_sha256=pin),'ario-manifest.json')

    def test_strict_valid_reference_and_local_bytes(self):
        size,digest=v.parse_reference(self.registry,self.cfg,'ario-manifest.json')
        self.assertEqual((size,digest),(len(self.payload),hashlib.sha256(self.payload).hexdigest()))
        self.assertEqual(v.local_sha256(self.file,size),digest)

    def test_helper_without_validated_tls_observation_returns_unknown(self):
        with patch.object(v,'_retrieve_reference',return_value=(self.registry,False)):
            with self.assertRaisesRegex(v.ReferenceUnknown,'validated GitHub TLS'):
                v.fetch_official_reference(self.cfg)

    def test_helper_with_validated_tls_observation_passes_bytes(self):
        with patch.object(v,'_retrieve_reference',return_value=(self.registry,True)):
            self.assertEqual(v.fetch_official_reference(self.cfg),self.registry)

    def test_default_verify_does_not_trust_unvalidated_fetch(self):
        with patch.object(v,'_retrieve_reference',return_value=(self.registry,False)):
            with self.assertRaises(v.ReferenceUnknown):
                v.verify_file(self.file,'ario-manifest.json')

    def test_official_fixture_bytes_match_pinned_registry_with_origin_unverified(self):
        import zipfile
        # These are exact R1.2 public fixtures. No network request is made.
        archived = Path(__file__).resolve().parents[1] / "input" / "candidate"
        registry=(archived / 'research_reference_checksums.json').read_bytes()
        manifest=(archived / 'retrieved-ario-manifest.json').read_bytes()
        self.assertEqual(hashlib.sha256(registry).hexdigest(),v.RELEASE.checksums_sha256)
        self.assertEqual(len(registry),962)
        self.assertEqual(len(manifest),63205)
        self.file.write_bytes(manifest)
        result=v.verify_file(self.file,'ario-manifest.json',fetcher=lambda _:registry)
        self.assertEqual(result['status'],'PINNED_REFERENCE_BYTES_MATCH_ORIGIN_UNVERIFIED')
        self.assertEqual(result['reference_transport'],'CALLER_SUPPLIED_TRANSPORT_UNVERIFIED')
        self.assertEqual(result['sha256'],'f86fb10ef3eb71dd6e3c348b3f0c9b42c88b3837ae889918c33d8f5d62fe11d8')

    def test_default_live_path_requires_validated_observation_before_live_label(self):
        registry=(Path(__file__).resolve().parents[1] / 'input' / 'candidate' / 'research_reference_checksums.json').read_bytes()
        manifest=(Path(__file__).resolve().parents[1] / 'input' / 'candidate' / 'retrieved-ario-manifest.json').read_bytes()
        self.file.write_bytes(manifest)
        # Synthetic seam only: NOT a genuine TLS retrieval demonstration.
        with patch.object(v,'_retrieve_reference',return_value=(registry,True)):
            result=v.verify_file(self.file,'ario-manifest.json')
        self.assertEqual(result['status'],'GITHUB_RELEASE_BYTES_MATCH')
        self.assertEqual(result['reference_transport'],'HTTPS_GITHUB')

    def test_offline_chunked_wire_canonical_decodes(self):
        data=self.registry
        chunk=(format(len(data),'x').encode()+b'\r\n'+data+b'\r\n0\r\n\r\n')
        raw=self._decode_wire(b'Transfer-Encoding: chunked',chunk)
        self.assertEqual(raw,data)
        self.assertEqual(v.parse_reference(raw,self.cfg,'ario-manifest.json')[0],len(self.payload))

    def test_trailing_ows_te_is_unknown_before_pin_not_false_mismatch(self):
        data=self.registry
        chunk=(format(len(data),'x').encode()+b'\r\n'+data+b'\r\n0\r\n\r\n')
        for suffix in (b' ',b'\t'):
            with self.subTest(suffix=suffix):
                with self.assertRaisesRegex(v.ReferenceUnknown,'decoder/header disagreement'):
                    self._decode_wire(b'Transfer-Encoding: chunked'+suffix,chunk)

    def test_header_and_decoder_disagreement_is_unknown_even_if_parser_bytes_look_good(self):
        class FakeResponse:
            status=200
            chunked=False
            length=None
            headers=Message()
            def geturl(self):return v.url_for(v.RELEASE)
            def read(self,n):return b'bad wire payload'
            def __enter__(self):return self
            def __exit__(self,*args):return False
        FakeResponse.headers.add_header('Transfer-Encoding','chunked')
        with patch.object(v.urllib.request,'build_opener',return_value=OfflineOpener(FakeResponse())):
            with self.assertRaises(v.ReferenceUnknown):v._retrieve_reference(v.RELEASE)

    def test_conflicting_cl_rejected(self):
        with self.assertRaises(v.ReferenceUnknown):
            self._decode_wire(b'Content-Length: 12\r\nContent-Length: 13',b'x'*13)

    def test_valid_repeated_equal_cl(self):
        self.assertEqual(self._decode_wire(b'Content-Length: '+str(len(self.registry)).encode(),self.registry),self.registry)

    def test_same_size_local_edit_rejected(self):
        self.file.write_bytes(self.payload[:-1]+b'x')
        with self.assertRaisesRegex(v.VerificationRejected,'FILE_SHA256_MISMATCH'):
            v.verify_file(self.file,'ario-manifest.json',self.cfg,fetcher=lambda _:self.registry)

    def test_live_branch_is_explicit_and_cannot_be_reached_with_custom_release(self):
        with self.assertRaises(v.VerificationRejected):
            v.verify_file(self.file,'ario-manifest.json',self.cfg)

    @unittest.skipUnless(os.name=='posix' and hasattr(os,'mkfifo'),'requires POSIX FIFO')
    def test_fifo_swap_after_lstat_returns_immediately(self):
        original=Path.lstat
        target=self.file
        touched=[]
        def race(path,*args,**kwargs):
            stat_result=original(path,*args,**kwargs)
            if path==target and not touched:
                touched.append(True)
                target.unlink()
                os.mkfifo(target)
            return stat_result
        with patch.object(Path,'lstat',race):
            with self.assertRaises(v.VerificationRejected):
                v.local_sha256(target,len(self.payload))
        self.assertTrue(touched)

    @unittest.skipUnless(os.name=='posix','POSIX-specific descriptor check')
    def test_regular_file_still_hashes_using_posix_descriptor_path(self):
        self.assertEqual(v.local_sha256(self.file,len(self.payload)),hashlib.sha256(self.payload).hexdigest())

    def _decode_wire(self,header,body):
        msg=b'HTTP/1.1 200 OK\r\n'+header+b'\r\n\r\n'+body
        response=http.client.HTTPResponse(MemorySocket(msg))
        response.begin()
        response.url=v.url_for(v.RELEASE)
        with patch.object(v.urllib.request,'build_opener',return_value=OfflineOpener(response)):
            raw,seen=v._retrieve_reference(v.RELEASE)
        self.assertFalse(seen)
        return raw


if __name__=='__main__':
    unittest.main(verbosity=2)
