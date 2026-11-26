import base64
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import enroll


class EnrollmentTests(unittest.TestCase):
    def test_published_vkey_vector(self):
        example = 'example.com/foo+530d903a+AekyeRrm56hApGFkyQR4ZCbV54Id2LKaANYcrnKv3U2k'
        self.assertEqual(enroll.vkey('example.com/foo', base64.b64decode(example.split('+', 2)[2])[1:]), example)

    def test_identity_roundtrip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'identity'
            pw = b'temporary-test-passphrase'
            first = enroll.create_identity(p, pw)
            original = (p / 'research-log.private.pem').read_bytes()
            self.assertIn(b'ENCRYPTED PRIVATE KEY', original)
            self.assertEqual(enroll.load_vkey(p, pw), first)
            with self.assertRaises(FileExistsError):
                enroll.create_identity(p, pw)
            self.assertEqual((p / 'research-log.private.pem').read_bytes(), original)
            with self.assertRaises(ValueError):
                enroll.load_vkey(p, b'wrong')

    def test_exact_membership(self):
        a = enroll.public_vkey(Ed25519PrivateKey.generate())
        b = enroll.public_vkey(Ed25519PrivateKey.generate())
        def raw(*keys):
            return ('logs/v0\n' + ''.join('vkey '+k+'\nqpd 24\ncontact test@example.org\n' for k in keys)).encode()
        self.assertTrue(enroll.enrolled(raw(a), a))
        self.assertFalse(enroll.enrolled(raw(), a))
        self.assertFalse(enroll.enrolled(raw(b), a))
        self.assertFalse(enroll.enrolled(raw(a,b), a))
        self.assertFalse(enroll.enrolled(raw(a,a), a))
        with self.assertRaises(ValueError):
            enroll.enrolled(b'not a list', a)

    def test_short_password_no_state(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'identity'
            with self.assertRaises(ValueError):
                enroll.create_identity(p,b'short')
            self.assertFalse(p.exists())


if __name__ == '__main__':
    unittest.main()
