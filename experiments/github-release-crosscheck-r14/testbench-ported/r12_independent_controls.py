"""Ario independent second-pass security controls: offline, read-only registry fixture.

All files in tests are temporary copies or bundled public registry assets. There
are no live GitHub requests and no modified historical repository bytes.
"""
from dataclasses import replace
from email.message import Message
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

import ario_github_crosscheck_v0_2 as v

ROOT = Path(__file__).resolve().parent
REGISTRY = (ROOT / 'research_reference_checksums.json').read_bytes()
MANIFEST = (ROOT / 'retrieved-ario-manifest.json').read_bytes()

class Response:
    status=200
    length=0
    def __init__(self, body, url=None):
        self.body=body
        self.url=url if url else v.url_for(v.RELEASE)
        self.headers=Message()
        self.headers['Content-Length']=str(len(body))
    def geturl(self): return self.url
    def read(self, n): return self.body[:n]
    def __enter__(self): return self
    def __exit__(self, *_): pass

class Stub:
    def __init__(self, body): self.body=body
    def open(self, req, timeout=0):
        assert timeout == 15
        return Response(self.body, req.full_url)

class CrosscheckR12(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.file=Path(self.temp.name) / 'received.bin'
        self.file.write_bytes(MANIFEST)

    def test_reference_pin_is_the_expected_public_registry(self):
        self.assertEqual(hashlib.sha256(REGISTRY).hexdigest(), v.RELEASE.checksums_sha256)
        self.assertEqual(len(REGISTRY), 962)
        self.assertEqual(len(MANIFEST), 63205)

    def test_explicit_fixture_never_promotes_to_live(self):
        result=v.verify_file(self.file, 'ario-manifest.json', fetcher=lambda _: REGISTRY)
        self.assertEqual(result['status'], 'PINNED_REFERENCE_BYTES_MATCH_ORIGIN_UNVERIFIED')
        self.assertEqual(result['reference_transport'], 'CALLER_SUPPLIED_TRANSPORT_UNVERIFIED')

    def test_offline_opener_replay_even_with_real_bytes_cannot_claim_https(self):
        with mock.patch.object(v.urllib.request, 'build_opener', return_value=Stub(REGISTRY)):
            with self.assertRaisesRegex(v.ReferenceUnknown, 'TLS session was not observed'):
                v.verify_file(self.file, 'ario-manifest.json')

    def test_altered_same_size_manifest_is_rejected(self):
        data=bytearray(MANIFEST)
        data[-1] ^= 0x01
        self.file.write_bytes(bytes(data))
        with self.assertRaisesRegex(v.VerificationRejected, 'FILE_SHA256_MISMATCH'):
            v.verify_file(self.file, 'ario-manifest.json', fetcher=lambda _: REGISTRY)

    def test_local_filename_irrelevant_only_asset_declaration_matters(self):
        result=v.verify_file(self.file, 'ario-manifest.json', fetcher=lambda _: REGISTRY)
        self.assertEqual(result['size_bytes'],63205)
        self.assertEqual(result['sha256'],hashlib.sha256(MANIFEST).hexdigest())

    def test_replace_after_success_must_be_rechecked_by_consumer(self):
        assert v.verify_file(self.file,'ario-manifest.json',fetcher=lambda _:REGISTRY)
        self.file.write_bytes(b'x' * len(MANIFEST))
        with self.assertRaisesRegex(v.VerificationRejected, 'FILE_SHA256_MISMATCH'):
            v.verify_file(self.file,'ario-manifest.json',fetcher=lambda _:REGISTRY)

    def test_header_equal_repeated_content_lengths_accepted(self):
        x=Message();x['Content-Length']='000962, 962';x['Content-Length']='962'
        self.assertEqual(v.reference_framing(x),(962,False))

    def test_header_conflicting_repeated_content_lengths_unknown(self):
        x=Message();x['Content-Length']='962';x['Content-Length']='963'
        with self.assertRaises(v.ReferenceUnknown):v.reference_framing(x)

    def test_chunked_and_length_together_unknown(self):
        x=Message();x['Transfer-Encoding']='chunked';x['Content-Length']='962'
        with self.assertRaises(v.ReferenceUnknown):v.reference_framing(x)

    def test_multiple_transfer_encodings_unknown(self):
        x=Message();x['Transfer-Encoding']='gzip, chunked'
        with self.assertRaises(v.ReferenceUnknown):v.reference_framing(x)

    def test_valid_chunked_header_allowed_for_parser(self):
        x=Message();x['Transfer-Encoding']='Chunked'
        self.assertEqual(v.reference_framing(x),(None,True))

    def test_tls_context_error_is_unknown_not_uncaught(self):
        with mock.patch.object(v.ssl, 'create_default_context', side_effect=OSError('CA unreadable')):
            with self.assertRaises(v.ReferenceUnknown):v.fetch_official_reference(v.RELEASE)

    def test_malformed_commit_types_are_rejected(self):
        for bad in (None, 42, b'a'*40, 'bad', 'g'*40):
            with self.subTest(bad=bad):
                with self.assertRaises(v.VerificationRejected):
                    v.url_for(replace(v.RELEASE, publication_commit=bad))

    def test_custom_pin_must_use_test_provider(self):
        modified=replace(v.RELEASE, checksums_sha256='0'*64)
        with self.assertRaisesRegex(v.VerificationRejected, 'explicit reference provider'):
            v.verify_file(self.file, 'ario-manifest.json', modified)

    def test_dot_segment_path_rejected(self):
        with self.assertRaises(v.VerificationRejected):
            v.url_for(replace(v.RELEASE, checksums_path='releases/../checksums.json'))

    def test_nonfinite_float_rejected_even_with_corresponding_test_pin(self):
        raw=REGISTRY.replace(b'"tracked_bytes": 16183258', b'"tracked_bytes": 1e999')
        self.assertNotEqual(raw,REGISTRY)
        cfg=replace(v.RELEASE, checksums_sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaises(v.VerificationRejected):
            v.parse_reference(raw,cfg,'ario-manifest.json')

    def test_unknown_asset_rejected(self):
        with self.assertRaises(v.VerificationRejected):
            v.verify_file(self.file,'unlisted.zip',fetcher=lambda _:REGISTRY)

    def test_symlink_leaf_rejected_where_supported(self):
        link=self.file.with_name('link-file')
        try:
            link.symlink_to(self.file)
        except (OSError, NotImplementedError):
            self.skipTest('symlink creation prohibited')
        with self.assertRaises(v.VerificationRejected):
            v.local_sha256(link, len(MANIFEST))

if __name__ == '__main__': unittest.main()
