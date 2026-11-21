"""Research-only pending-format positive/negative tests; no HTTP submission."""
import hashlib,unittest
from g4_ots_attestation import PENDING_TAG,ALLOWED_URI,InvalidPendingProof,parse_pending

def vint(n):
    b=bytearray()
    while True:
        k=n&127;n>>=7
        if n:b.append(k|128)
        else:b.append(k);return bytes(b)
def fixture(uri=ALLOWED_URI):
    u=uri.encode("utf8")
    return bytes.fromhex("f004")+b"test"+bytes.fromhex("0800")+PENDING_TAG+vint(len(u))+u

class PendingAttestationTests(unittest.TestCase):
    digest=b"\x17"*32
    def test_positive_strict_pending(self):
        result=parse_pending(fixture(),self.digest)
        self.assertEqual(result.uri,ALLOWED_URI)
        self.assertEqual(result.ops,("APPEND(4)","SHA256"))
        self.assertEqual(result.commitment_hex,hashlib.sha256(self.digest+b"test").hexdigest())
    def test_leading_dash_is_not_whitelisted(self):
        with self.assertRaisesRegex(InvalidPendingProof,"PENDING_URI_NOT_EXACT"):
            parse_pending(fixture("-"+ALLOWED_URI),self.digest)
    def test_wrong_calendar_is_not_whitelisted(self):
        with self.assertRaises(InvalidPendingProof):
            parse_pending(fixture("https://bob.btc.calendar.opentimestamps.org"),self.digest)
    def test_truncated(self):
        with self.assertRaises(InvalidPendingProof):parse_pending(fixture()[:-2],self.digest)
    def test_wrong_attestation(self):
        with self.assertRaisesRegex(InvalidPendingProof,"UNEXPECTED_ATTESTATION_TAG"):
            parse_pending(fixture().replace(PENDING_TAG,b"\x01"*8),self.digest)
    def test_unknown_opcode(self):
        with self.assertRaisesRegex(InvalidPendingProof,"UNSUPPORTED_OP"):
            parse_pending(b"\x91"+fixture(),self.digest)
    def test_wrong_digest_length(self):
        with self.assertRaisesRegex(InvalidPendingProof,"INVALID_DIGEST"):
            parse_pending(fixture(),b"x")
    def test_trailing(self):
        with self.assertRaisesRegex(InvalidPendingProof,"MALFORMED_CALENDAR_URI"):
            parse_pending(fixture()+b"\x00",self.digest)
    def test_missing_attestation(self):
        with self.assertRaisesRegex(InvalidPendingProof,"MISSING_FINAL_ATTESTATION"):
            parse_pending(b"\xf0\x0aabcdefghij\x08",self.digest)
if __name__=="__main__":unittest.main(verbosity=2)
