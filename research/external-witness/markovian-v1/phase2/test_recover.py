"""Offline controls against retained public size-2 fixture; not external custody evidence."""
import hashlib
import pathlib
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile

import recover

HERE = pathlib.Path(__file__).resolve().parent
EXPECTED = 'f9e9cbaf85c3735e96ddc2b81fd2e55a202fd13a57fbc1aaf0cc55d569dbf828'


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = pathlib.Path(self.tmp.name)
        self.note = (HERE / 'cosigned-checkpoint-size-2.txt').read_bytes()
        self.files = {name: (HERE / name).read_bytes() for name in recover.FILES}

    def archive(self, files=None, duplicate=False):
        p = self.path / 'capsule.zip'
        with zipfile.ZipFile(p, 'w') as z:
            for k, v in (self.files if files is None else files).items():
                z.writestr(k, v)
            if duplicate:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    z.writestr('entries', self.files['entries'])
        return p

    def cli(self, archive, output):
        note = self.path / 'note.txt'
        note.write_bytes(self.note)
        return subprocess.run([sys.executable, str(HERE / 'recover.py'), str(archive), str(note), str(output)], cwd=self.path, capture_output=True, check=False)

    def test_exact_recovery(self):
        result = recover.recover(self.archive(), self.note)
        self.assertEqual(hashlib.sha256(result).hexdigest(), EXPECTED)

    def test_fresh_process(self):
        out = self.path / 'out.json'
        self.assertEqual(self.cli(self.archive(), out).returncode, 0)
        self.assertEqual(hashlib.sha256(out.read_bytes()).hexdigest(), EXPECTED)

    def test_stale_content(self):
        self.files['capsule-size-2.json'] = self.files['capsule-size-1.json']
        with self.assertRaises(ValueError):
            recover.recover(self.archive(), self.note)

    def test_tampered_content(self):
        self.files['capsule-size-2.json'] = self.files['capsule-size-2.json'].replace(b'delta', b'omega')
        with self.assertRaises(ValueError):
            recover.recover(self.archive(), self.note)

    def test_missing_member(self):
        del self.files['capsule-size-2.json']
        with self.assertRaises(ValueError):
            recover.recover(self.archive(), self.note)

    def test_wrong_floor(self):
        with self.assertRaises(ValueError):
            recover.recover(self.archive(), self.note.replace(b'\n2\n', b'\n1\n', 1))

    def test_changed_entry(self):
        self.files['entries'] = self.files['entries'].replace(b'MCR-01', b'MCR-02')
        with self.assertRaises(ValueError):
            recover.recover(self.archive(), self.note)

    def test_extra_member(self):
        self.files['extra'] = b'not authorized'
        with self.assertRaises(ValueError):
            recover.recover(self.archive(), self.note)

    def test_duplicate_member(self):
        with self.assertRaises(ValueError):
            recover.recover(self.archive(duplicate=True), self.note)

    def test_no_overwrite(self):
        out = self.path / 'out.json'
        out.write_bytes(b'preserve')
        self.assertEqual(self.cli(self.archive(), out).returncode, 2)
        self.assertEqual(out.read_bytes(), b'preserve')


if __name__ == '__main__':
    unittest.main()
