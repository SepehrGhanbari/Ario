"""Additional synthetic adversarial controls for research candidate v0.2.
Tests use scratch files and mock GitHub transport. Not a live GitHub TLS test.
"""
from contextlib import redirect_stdout
from dataclasses import replace
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import ssl
import tempfile
import unittest
from unittest import mock

import ario_github_crosscheck_v0_2 as m

class ExtendedControls(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'data.txt'
        self.payload=b'a\x00synthetic release payload\n'
        self.path.write_bytes(self.payload)
        self.doc={
            'commit':m.RELEASE.source_commit,
            'git_tree':m.RELEASE.source_tree,
            'tracked_files':204,
            'ario-full.txt':{'bytes':len(self.payload),'sha256':hashlib.sha256(self.payload).hexdigest()},
        }
        self.refresh()

    def refresh(self):
        self.ref=json.dumps(self.doc,sort_keys=True,allow_nan=False).encode('utf-8')
        self.cfg=replace(m.RELEASE,checksums_sha256=hashlib.sha256(self.ref).hexdigest())

    def test_fixed_origin_and_exact_publication_commit(self):
        self.assertEqual(m.url_for(m.RELEASE),
          'https://raw.githubusercontent.com/SepehrGhanbari/Ario/'
          '4731c912ba4b34b302843dd37067822ffb699ba7/'
          'releases/ai-readable-full-2026-11-11-05ba5c9/checksums.json')

    def test_config_rejects_host_prefix_slashes_and_dot_segments(self):
        paths=['//example.com/fake.json','../checksums.json','x/./y.json',
               'x/../y.json','x//y.json','/absolute/path','x/%2e%2e/y.json',
               'x\\y.json','x?token=secret','x#fragment']
        for path in paths:
            with self.subTest(path=path),self.assertRaises(m.VerificationRejected):
                m.url_for(replace(m.RELEASE, checksums_path=path))

    def test_https_context_and_redirect_proxy_wiring(self):
        opener=m.urllib.request.build_opener(
            m.urllib.request.ProxyHandler({}),
            m.urllib.request.HTTPSHandler(context=ssl.create_default_context()),
            m.NoRedirect(),
        )
        self.assertTrue(any(isinstance(x,m.NoRedirect) for x in opener.handlers))
        https=next(x for x in opener.handlers if isinstance(x,m.urllib.request.HTTPSHandler))
        self.assertTrue(https._context.check_hostname)
        self.assertEqual(https._context.verify_mode,ssl.CERT_REQUIRED)
        redirects=next(x for x in opener.handlers if isinstance(x,m.NoRedirect))
        self.assertIsNone(redirects.redirect_request(None,None,302,'redirect',{},'https://evil.test/'))
        self.assertFalse(any(isinstance(x,m.urllib.request.ProxyHandler) and x.proxies for x in opener.handlers))

    def test_real_fetch_branch_success_through_stubbed_https_opener(self):
        class FakeResponse:
            status=200
            def __init__(self,url,body):self.url=url;self.body=body
            def geturl(self):return self.url
            def read(self,n):return self.body[:n]
            def __enter__(self):return self
            def __exit__(self,*a):return False
        class StubOpener:
            def open(self,req,timeout=0):
                self.assert_timeout=timeout
                return FakeResponse(req.full_url,self.body)
        stub=StubOpener();stub.body=self.ref
        with mock.patch.object(m.urllib.request,'build_opener',return_value=stub):
            # Invoke the live-fetch branch but supply synthetic pinned test config.
            result=m.verify_file(self.path,'ario-full.txt', self.cfg)
        self.assertEqual(stub.assert_timeout,15)
        self.assertEqual(result['status'],'GITHUB_RELEASE_BYTES_MATCH')
        self.assertEqual(result['reference_transport'],'HTTPS_GITHUB')
        self.assertIn('not established', result['qualification'].lower())

    def test_redirect_and_non200_fail_closed(self):
        class FakeResponse:
            def __init__(self,url,status):self.url=url;self.status=status
            def geturl(self):return self.url
            def read(self,n):raise AssertionError('must reject before read')
            def __enter__(self):return self
            def __exit__(self,*a):return False
        class StubOpener:
            def __init__(self,status,url):self.status=status;self.url=url
            def open(self,req,timeout):return FakeResponse(self.url,self.status)
        for status,url in [(200,'https://evil.test/redirected'),(301,m.url_for(self.cfg)),(404,m.url_for(self.cfg))]:
            with self.subTest(status=status,url=url),mock.patch.object(m.urllib.request,'build_opener',return_value=StubOpener(status,url)):
                with self.assertRaises(m.ReferenceUnknown):m.fetch_official_reference(self.cfg)

    def test_reference_size_limit_on_wire(self):
        class FakeResponse:
            status=200
            def __init__(self,url):self.url=url
            def geturl(self):return self.url
            def read(self,n):return b'a'*(m.MAX_REFERENCE_BYTES+1)
            def __enter__(self):return self
            def __exit__(self,*a):return False
        class StubOpener:
            def open(self,req,timeout):return FakeResponse(req.full_url)
        with mock.patch.object(m.urllib.request,'build_opener',return_value=StubOpener()):
            with self.assertRaisesRegex(m.ReferenceUnknown,'oversized'):
                m.fetch_official_reference(self.cfg)

    def test_bad_reference_types_fail_closed(self):
        for val in (None,object(),'not-bytes',bytearray(self.ref)):
            with self.subTest(value_type=type(val).__name__),self.assertRaises(m.VerificationRejected):
                m.parse_reference(val,self.cfg,'ario-full.txt')

    def test_integer_limit_and_duplicate_nested_hash_fields(self):
        oversized=b'{"tracked_files":99999999999999999}'
        cfg=replace(self.cfg,checksums_sha256=hashlib.sha256(oversized).hexdigest())
        with self.assertRaises(m.VerificationRejected):m.parse_reference(oversized,cfg,'ario-full.txt')
        nested=self.ref.replace(b'"bytes": ',b'"bytes": 77, "bytes": ')
        cfg=replace(self.cfg,checksums_sha256=hashlib.sha256(nested).hexdigest())
        with self.assertRaisesRegex(m.VerificationRejected,'duplicate'):
            m.parse_reference(nested,cfg,'ario-full.txt')

    def test_float_exponent_overflow_fails_closed(self):
        ref=self.ref[:-1]+b', "extra": 1e999}'
        cfg=replace(self.cfg,checksums_sha256=hashlib.sha256(ref).hexdigest())
        with self.assertRaisesRegex(m.VerificationRejected,'non-finite'):
            m.parse_reference(ref,cfg,'ario-full.txt')

    def test_renamed_same_bytes_valid_by_explicit_asset_name(self):
        result=m.verify_file(self.path,'ario-full.txt',self.cfg,fetcher=lambda _:self.ref)
        self.assertEqual(result['status'],'PINNED_REFERENCE_BYTES_MATCH_GITHUB_NOT_CHECKED')

    def test_local_mutation_during_streaming_detected(self):
        original=m.hashlib.sha256
        changed=[False]
        class Wrapped:
            def __init__(self):self.inner=original()
            def update(self,data):
                self.inner.update(data)
                if not changed[0]:
                    changed[0]=True
                    self.outer.path.write_bytes(b'X'*len(self.outer.payload))
            def hexdigest(self):return self.inner.hexdigest()
        def factory():
            w=Wrapped();w.outer=self;return w
        with mock.patch.object(m.hashlib,'sha256',side_effect=factory):
            with self.assertRaises(m.ReferenceUnknown):m.local_sha256(self.path,len(self.payload))
        self.assertTrue(changed[0])

    def test_symlink_swap_between_lstat_and_open_rejected(self):
        victim=self.path
        alternate=Path(self.tmp.name)/'other.txt'
        alternate.write_bytes(self.payload)
        original=Path.open
        swapped=[False]
        def raced_open(path,*a,**kw):
            if path==victim and not swapped[0]:
                victim.unlink()
                try: victim.symlink_to(alternate)
                except OSError:self.skipTest('symlinks unavailable')
                swapped[0]=True
            return original(path,*a,**kw)
        with mock.patch.object(Path,'open',new=raced_open):
            with self.assertRaisesRegex(m.VerificationRejected,'ID_MISMATCH'):
                m.local_sha256(victim,len(self.payload))
        self.assertTrue(swapped[0])

    def test_cli_unknown_is_json_and_nonzero(self):
        with mock.patch.object(m,'verify_file',side_effect=m.ReferenceUnknown('DNS offline')):
            buf=io.StringIO()
            with redirect_stdout(buf):exit_code=m.main(['--file',str(self.path),'--asset','ario-full.txt'])
        result=json.loads(buf.getvalue())
        self.assertEqual(exit_code,3)
        self.assertEqual(result['status'],'UNKNOWN')
        self.assertEqual(result['exit_code'],3)

    def test_cli_rejected_is_json_and_nonzero(self):
        with mock.patch.object(m,'verify_file',side_effect=m.VerificationRejected('SHA mismatch')):
            buf=io.StringIO()
            with redirect_stdout(buf):exit_code=m.main(['--file',str(self.path),'--asset','ario-full.txt'])
        result=json.loads(buf.getvalue())
        self.assertEqual(exit_code,2)
        self.assertEqual(result['status'],'REJECTED')
        self.assertEqual(result['exit_code'],2)

if __name__=='__main__': unittest.main()
