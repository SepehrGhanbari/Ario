"""Offline wrapper tests: mocks never constitute real HTTPS evidence."""
import hashlib
import http.client
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import ario_verified_release as m

ASSET = 'ario-manifest.json'


def live_result(asset):
    size, sha = m.ASSETS[asset]
    return {'status': 'GITHUB_RELEASE_BYTES_MATCH', 'reference_transport': 'HTTPS_GITHUB', 'exit_code': 0,
            'repository': 'https://github.com/SepehrGhanbari/Ario', 'publication_commit': m.PUBLICATION,
            'source_commit': m.SOURCE, 'checksums_sha256': m.PIN, 'asset': asset, 'size_bytes': size, 'sha256': sha}


class Wrapper(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)

    def test_exact_reviewed_verifier(self):
        self.assertEqual(hashlib.sha256(m.pinned_verifier()).hexdigest(), m.VERIFIER_SHA)

    def test_changed_verifier_never_runs_or_downloads(self):
        bad = self.root / 'bad.py'
        bad.write_text('raise RuntimeError("must not execute")')
        with patch.object(m, 'VERIFIER', bad), patch.object(m, 'download_asset') as download, patch.object(m, 'verify_asset') as verify:
            code, result = m.run('download', self.root, (ASSET,))
        self.assertEqual(code, 2)
        download.assert_not_called()
        verify.assert_not_called()
        self.assertEqual(list(self.root.iterdir()), [bad])

    def test_check_all_read_only(self):
        for asset in m.ASSETS:
            (self.root / asset).write_bytes(b'fixture')
        with patch.object(m, 'verify_asset', side_effect=lambda v,a,p: live_result(a)) as v, patch.object(m, 'download_asset') as d:
            code, report = m.run('check', self.root, tuple(m.ASSETS))
        self.assertEqual(code, 0)
        self.assertEqual(v.call_count, 3)
        d.assert_not_called()
        self.assertTrue(all(p.read_bytes() == b'fixture' for p in self.root.iterdir()))

    def test_rejection_and_unknown_not_success(self):
        with patch.object(m, 'verify_asset', side_effect=[live_result('ario-full.zip'), m.Unknown('offline'), m.Rejected('bad')]):
            code, result = m.run('check', self.root, tuple(m.ASSETS))
        self.assertEqual(code, 2)
        self.assertNotIn('directory', result)
        self.assertEqual(len(result['results']), 3)

    def test_download_verify_and_preserve_existing(self):
        marker = self.root / ASSET
        marker.write_bytes(b'existing')
        calls = []
        def download(a,p):
            calls.append(('download',a)); p.write_bytes(b'fixture')
        def verify(v,a,p):
            calls.append(('verify',a)); self.assertEqual(p.read_bytes(), b'fixture'); return live_result(a)
        with patch.object(m, 'download_asset', side_effect=download), patch.object(m, 'verify_asset', side_effect=verify):
            code, report = m.run('download', self.root, tuple(m.ASSETS))
        self.assertEqual(code, 0)
        self.assertEqual(calls, [(kind,a) for a in m.ASSETS for kind in ('download','verify')])
        self.assertEqual(marker.read_bytes(), b'existing')
        self.assertEqual(len(list(Path(report['directory']).iterdir())), 3)

    def test_download_failure_cleans_own_directory(self):
        marker = self.root / 'existing.txt'; marker.write_bytes(b'keep')
        with patch.object(m, 'download_asset', side_effect=lambda a,p: p.write_bytes(b'fixture')), patch.object(m, 'verify_asset', side_effect=m.Unknown('offline')):
            code, result = m.run('download', self.root, (ASSET,))
        self.assertEqual(code, 3)
        self.assertEqual(list(self.root.iterdir()), [marker])

    def test_unverified_transport_and_bad_fields_not_accepted(self):
        for k,v in [('reference_transport','CALLER_SUPPLIED_TRANSPORT_UNVERIFIED'), ('publication_commit','wrong'), ('sha256','wrong'), ('status','UNKNOWN'), ('asset','wrong'), ('size_bytes',0), ('exit_code',3)]:
            with self.subTest(k=k), patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(dict(live_result(ASSET), **{k:v})).encode(), b'')):
                with self.assertRaises(m.Unknown): m.verify_asset(self.root/'v.py',ASSET,self.root/ASSET)

    def test_child_valid_result_and_isolated_invocation(self):
        with patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([],0,json.dumps(live_result(ASSET)).encode(),b'')) as p:
            self.assertEqual(m.verify_asset(self.root/'v.py', ASSET, self.root/ASSET), live_result(ASSET))
        self.assertEqual(p.call_args.args[0][1:3], ['-I','-B'])

    def test_child_failure_and_timeout(self):
        for exitcode,status,exc in [(2,'REJECTED',m.Rejected),(3,'UNKNOWN',m.Unknown),(1,'GITHUB_RELEASE_BYTES_MATCH',m.Unknown)]:
            with self.subTest(exitcode=exitcode),patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],exitcode,json.dumps({'status':status,'exit_code':exitcode}).encode(),b'')):
                with self.assertRaises(exc): m.verify_asset(self.root/'v.py',ASSET,self.root/ASSET)
        with patch.object(m.subprocess,'run',side_effect=subprocess.TimeoutExpired([],90)):
            with self.assertRaises(m.Unknown): m.verify_asset(self.root/'v.py',ASSET,self.root/ASSET)

    def wire(self, headers, body):
        class Socket:
            def makefile(self, mode): return io.BytesIO(b'HTTP/1.1 200 OK\r\n'+headers+b'\r\n\r\n'+body)
        r = http.client.HTTPResponse(Socket()); r.begin(); return r

    def test_download_real_decoder_fixed_and_chunked(self):
        size,_ = m.ASSETS[ASSET]; body = b'A'*size
        for n,(header,wire) in enumerate([(f'Content-Length: {size}'.encode(),body),(b'Transfer-Encoding: chunked',f'{size:x}\r\n'.encode()+body+b'\r\n0\r\n\r\n')]):
            dest = self.root/f'{n}.bin'
            with patch.object(m.http.client,'HTTPSConnection') as c:
                c.return_value.getresponse.return_value = self.wire(header,wire)
                m.download_asset(ASSET,dest)
                self.assertEqual(dest.read_bytes(),body)
                self.assertIn(m.PUBLICATION,c.return_value.request.call_args.args[1])
                self.assertEqual(c.return_value.request.call_args.kwargs['headers']['Accept-Encoding'],'identity')

    def test_download_rejects_bad_transport(self):
        size,_ = m.ASSETS[ASSET]
        variants=[(f'Content-Length: {size}\r\nContent-Encoding: gzip'.encode(),b'A'*size), (f'Content-Length: {size}'.encode(),b'short'), (b'Content-Length: 1',b'A'),(b'Transfer-Encoding: chunked',b'1000000\r\n'+b'A'*(size+1)),(f'Content-Length: {size}\r\nTransfer-Encoding: chunked'.encode(),b'A'*size)]
        for n,(header,body) in enumerate(variants):
            with self.subTest(n=n),patch.object(m.http.client,'HTTPSConnection') as c:
                c.return_value.getresponse.return_value=self.wire(header,body)
                with self.assertRaises(m.Unknown): m.download_asset(ASSET,self.root/f'{n}.bin')

if __name__ == '__main__': unittest.main(verbosity=2)
