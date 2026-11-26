"""Independent R1.4 offline controls. Real HTTPResponse; no network or TLS."""
import gzip, hashlib, http.client, importlib.util, io, os, socket, sys, unittest
from pathlib import Path
from unittest.mock import patch
BASE=Path(__file__).resolve().parents[1]
TARGET=Path(os.environ.get('ARIO_TEST_TARGET', BASE/'candidate'/'ario_github_crosscheck_v0_4.py'))
spec=importlib.util.spec_from_file_location('target',TARGET); v=importlib.util.module_from_spec(spec); sys.modules[spec.name]=v; spec.loader.exec_module(v)
REG=(BASE/'fixtures'/'research_reference_checksums.json').read_bytes()
MAN=(BASE/'fixtures'/'retrieved-ario-manifest.json').read_bytes()
assert hashlib.sha256(REG).hexdigest()==v.RELEASE.checksums_sha256
assert len(REG)==962

def offline(event,args):
    if event in ('socket.getaddrinfo','socket.connect'):
        raise AssertionError('offline test attempted network')
sys.addaudithook(offline)

class HeldOpen(io.BytesIO):
    """Model a connection that does not send EOF after a complete body."""
    def __init__(self,wire): super().__init__(wire); self.read_sizes=[]
    def read(self,n=-1):
        self.read_sizes.append(n)
        if n<0 or n>len(self.getbuffer())-self.tell():
            raise TimeoutError('simulated wait beyond HTTP body; peer stays open')
        return super().read(n)

class Socket:
    def __init__(self,wire,held=False): self.fp=HeldOpen(wire) if held else io.BytesIO(wire)
    def makefile(self,*args,**kwargs): return self.fp

class Controls(unittest.TestCase):
    def decode(self,headers,body=REG,held=False):
        wire=b'HTTP/1.1 200 OK\r\n'+b'\r\n'.join(headers)+b'\r\n\r\n'+body
        socket=Socket(wire,held); response=http.client.HTTPResponse(socket);response.begin();response.url=v.url_for(v.RELEASE)
        requests=[]
        class Opener:
            def open(self,request,timeout): requests.append(request);return response
        with patch.object(v.urllib.request,'build_opener',return_value=Opener()):
            raw,validated=v._retrieve_reference(v.RELEASE)
        self.assertFalse(validated)
        return raw,requests[0]
    def assert_registry(self,headers,body=REG,held=False):
        raw,_=self.decode(headers,body,held)
        self.assertEqual(raw,REG)
        self.assertEqual(v.parse_reference(raw,v.RELEASE,'ario-manifest.json'),(len(MAN),hashlib.sha256(MAN).hexdigest()))
    def test_combined_equal_content_length_held_open(self):
        self.assert_registry([b'Content-Length: 962, 962'],held=True)
    @unittest.skipUnless(os.name == 'posix' and hasattr(socket, 'socketpair'), 'local POSIX socketpair')
    def test_combined_content_length_with_real_held_open_socket(self):
        # Actual local stream; writer remains open. No external networking.
        reader, writer = socket.socketpair()
        with reader, writer:
            reader.settimeout(0.3)
            writer.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 962, 962\r\n\r\n' + REG)
            response = http.client.HTTPResponse(reader)
            response.begin()
            response.url = v.url_for(v.RELEASE)
            class Opener:
                def open(self, request, timeout): return response
            with patch.object(v.urllib.request, 'build_opener', return_value=Opener()):
                raw, validated = v._retrieve_reference(v.RELEASE)
            self.assertEqual(raw, REG)
            self.assertFalse(validated)
    def test_combined_equal_content_length_leading_zeros(self):
        self.assert_registry([b'Content-Length: 0962, 962'],held=True)
    def test_repeated_equal_content_length_held_open(self):
        self.assert_registry([b'Content-Length: 962',b'Content-Length: 962'],held=True)
    def test_fixed_length_held_open(self):
        self.assert_registry([b'Content-Length: 962'],held=True)
    def test_conflicting_combined_content_length(self):
        with self.assertRaises(v.ReferenceUnknown): self.decode([b'Content-Length: 962, 963'],held=True)
    def test_combined_length_truncated(self):
        with self.assertRaises(v.ReferenceUnknown): self.decode([b'Content-Length: 962, 962'],REG[:-1])
    def test_combined_length_reads_only_declared_message(self):
        self.assert_registry([b'Content-Length: 962, 962'],REG+b'EXTRA NEXT MESSAGE')
    def test_gzip_correct_registry_is_unknown_before_pin(self):
        coded=gzip.compress(REG,mtime=0)
        with self.assertRaisesRegex(v.ReferenceUnknown,'Content-Encoding'):
            raw,_=self.decode([b'Content-Encoding: gzip',f'Content-Length: {len(coded)}'.encode()],coded)
            v.parse_reference(raw,v.RELEASE,'ario-manifest.json')
    def test_unsupported_encoding_even_with_matching_raw_bytes(self):
        for enc in (b'br',b'deflate',b'gzip',b'identity, gzip',b''):
            with self.subTest(enc=enc),self.assertRaisesRegex(v.ReferenceUnknown,'Content-Encoding'):
                self.decode([b'Content-Length: 962',b'Content-Encoding: '+enc])
    def test_repeated_content_encoding_unknown(self):
        with self.assertRaisesRegex(v.ReferenceUnknown,'Content-Encoding'):
            self.decode([b'Content-Length: 962',b'Content-Encoding: identity',b'Content-Encoding: gzip'])
    def test_identity_encoding_accepted(self):
        self.assert_registry([b'Content-Length: 962',b'Content-Encoding: IDENTITY \t'])
    def test_explicit_identity_request(self):
        raw,req=self.decode([b'Content-Length: 962']); self.assertEqual(raw,REG)
        self.assertEqual(req.get_header('Accept-encoding'),'identity')
    def test_canonical_chunked_accepted(self):
        chunk=b'3c2\r\n'+REG+b'\r\n0\r\n\r\n';self.assert_registry([b'Transfer-Encoding: chunked'],chunk)
    def test_chunked_ows_remains_unknown(self):
        chunk=b'3c2\r\n'+REG+b'\r\n0\r\n\r\n'
        for suffix in (b' ',b'\t'):
            with self.subTest(suffix=suffix),self.assertRaises(v.ReferenceUnknown): self.decode([b'Transfer-Encoding: chunked'+suffix],chunk)
    def test_pin_mismatch_still_rejected_for_identity(self):
        raw,_=self.decode([b'Content-Length: 962'],REG.replace(b'204',b'203',1))
        with self.assertRaisesRegex(v.VerificationRejected,'OFFICIAL_REFERENCE_PIN_MISMATCH'):
            v.parse_reference(raw,v.RELEASE,'ario-manifest.json')

if __name__=='__main__': unittest.main(verbosity=2)
