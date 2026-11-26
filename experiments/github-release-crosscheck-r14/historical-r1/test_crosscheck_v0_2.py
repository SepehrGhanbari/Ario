import hashlib
import json
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

import ario_github_crosscheck_v0_2 as m


class CrossCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.data = b"Ario synthetic test bytes\r\n"
        self.refobj = {
            "commit": m.RELEASE.source_commit,
            "git_tree": m.RELEASE.source_tree,
            "tracked_files": 204,
            "ario-full.txt": {"bytes": len(self.data), "sha256": hashlib.sha256(self.data).hexdigest()},
        }
        self.refbytes = json.dumps(self.refobj, sort_keys=True).encode()
        self.cfg = replace(m.RELEASE, checksums_sha256=hashlib.sha256(self.refbytes).hexdigest())
        self.path = self.dir / "downloaded.txt"
        self.path.write_bytes(self.data)

    def check(self):
        return m.verify_file(self.path, "ario-full.txt", self.cfg, fetcher=lambda _: self.refbytes)

    def test_valid_fixture(self):
        self.assertEqual(self.check()["status"], "PINNED_REFERENCE_BYTES_MATCH_GITHUB_NOT_CHECKED")

    def test_tampered_bytes_same_size(self):
        self.path.write_bytes(self.data[:-1] + b"X")
        with self.assertRaisesRegex(m.VerificationRejected, "FILE_SHA256_MISMATCH"):
            self.check()

    def test_bad_size(self):
        self.path.write_bytes(self.data + b"X")
        with self.assertRaisesRegex(m.VerificationRejected, "FILE_SIZE_OR_ID_MISMATCH"):
            self.check()

    def test_swapped_checksum_registry(self):
        self.refbytes += b" "
        with self.assertRaisesRegex(m.VerificationRejected, "OFFICIAL_REFERENCE_PIN_MISMATCH"):
            self.check()

    def test_wrong_source_commit(self):
        self.refobj["commit"] = "f" * 40
        self.refbytes = json.dumps(self.refobj, sort_keys=True).encode()
        self.cfg = replace(self.cfg, checksums_sha256=hashlib.sha256(self.refbytes).hexdigest())
        with self.assertRaisesRegex(m.VerificationRejected, "source commit mismatch"):
            self.check()

    def test_duplicate_keys(self):
        self.refbytes = b'{"commit":1,"commit":2}'
        self.cfg = replace(self.cfg, checksums_sha256=hashlib.sha256(self.refbytes).hexdigest())
        with self.assertRaisesRegex(m.VerificationRejected, "duplicate checksum JSON field"):
            self.check()

    def test_unrecognized_asset(self):
        with self.assertRaisesRegex(m.VerificationRejected, "unrecognized release asset"):
            m.verify_file(self.path, "not-in-release.zip", self.cfg, fetcher=lambda _: self.refbytes)

    def test_symlink_refused(self):
        link = self.dir / "link.txt"
        try:
            link.symlink_to(self.path)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaisesRegex(m.VerificationRejected, "refuse symlink"):
            m.verify_file(link, "ario-full.txt", self.cfg, fetcher=lambda _: self.refbytes)

    def test_offline_reference_unknown(self):
        def fail(_):
            raise m.ReferenceUnknown("offline")
        with self.assertRaisesRegex(m.ReferenceUnknown, "offline"):
            m.verify_file(self.path, "ario-full.txt", self.cfg, fetcher=fail)

    def test_actual_repo_checksum_fixture_sha(self):
        sample = Path(__file__).parent / "research_reference_checksums.json"
        # The real reference sample is an optional independent source-pin check.
        if not sample.exists():
            self.skipTest("reference sample not available")
        self.assertEqual(hashlib.sha256(sample.read_bytes()).hexdigest(), m.RELEASE.checksums_sha256)


if __name__ == "__main__":
    unittest.main()
