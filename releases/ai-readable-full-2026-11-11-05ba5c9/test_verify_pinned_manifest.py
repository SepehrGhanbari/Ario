"""Independent negative controls for the read-only pinned-manifest verifier.

These are synthetic bytes. The expected pin is passed separately from the
manifest/TXT. Running restore alone must NOT be confused with authentication.
"""
import hashlib
import tracemalloc
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import RESTORE_FROM_TXT_HARDENED as hardened
import verify_pinned_manifest as pinned
from RESTORE_FROM_TXT_HARDENED import restore
from test_restore_from_txt import snap, sha
from verify_pinned_manifest import VerificationError, verify

SCRIPT = pathlib.Path(__file__).with_name("verify_pinned_manifest.py")


def fixture(rows):
    records = []
    for path, raw in rows:
        try:
            raw.decode("utf-8")
            encoding = "raw-utf8"
        except UnicodeDecodeError:
            encoding = "base64"
        records.append({"path": path, "mode": "100644",
                        "git_blob_sha1": sha(raw),
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "bytes": len(raw), "encoding": encoding})
    manifest = {"format": "ARIO_FULL_SNAPSHOT_v1", "source_repo": "https://example.invalid",
                "commit": "a" * 40, "tree": "b" * 40,
                "tracked_files": len(records),
                "tracked_bytes": sum(len(raw) for _, raw in rows), "files": records}
    mb = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    pin = hashlib.sha256(mb).hexdigest()
    txt = snap(rows).replace(b"c" * 64, pin.encode("ascii"))
    return mb, txt, pin


class PinnedManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.manifest = self.root / "manifest.json"
        self.txt = self.root / "snapshot.txt"
        self.good_bytes, self.good_txt, self.good_pin = fixture([("safe.txt", b"hello")])
        self.write(self.good_bytes, self.good_txt)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, manifest, txt):
        self.manifest.write_bytes(manifest)
        self.txt.write_bytes(txt)

    def test_base64_whitespace_compaction_avoids_token_explosion(self):
        # A ~1 MiB attacker-controlled payload can previously allocate ~44 MiB
        # transiently via bytes.split(), despite the record-size input cap.
        payload = b"AA " * 350_000
        for compact in (hardened.compact_base64, pinned.compact_base64):
            with self.subTest(consumer=compact.__module__):
                tracemalloc.start()
                try:
                    cleaned = compact(payload)
                    _, peak = tracemalloc.get_traced_memory()
                finally:
                    tracemalloc.stop()
                self.assertEqual(len(cleaned), 700_000)
                self.assertLess(peak, 8 * 1024 * 1024)

    def test_base64_compaction_keeps_nonwhitespace_invalid_bytes(self):
        for compact in (hardened.compact_base64, pinned.compact_base64):
            with self.subTest(consumer=compact.__module__):
                self.assertEqual(compact(b"YQ==\n!"), b"YQ==!")
                self.assertEqual(compact(b"YQ==\r\n"), b"YQ==")

    def test_non_utf8_manifest_rejected_with_scoped_verification_error(self):
        raw = b"\xff\xfe\x80"
        self.manifest.write_bytes(raw)
        with self.assertRaisesRegex(VerificationError, "manifest is not valid UTF-8"):
            verify(self.txt, self.manifest, hashlib.sha256(raw).hexdigest())

    def test_valid_external_pin_and_contents_match(self):
        result = verify(self.txt, self.manifest, self.good_pin)
        self.assertEqual(result["files"], 1)
        self.assertEqual(result["bytes"], 5)
        self.assertIn("PIN_CUSTODY_NOT_VERIFIED", result["scope"])

    def test_wrong_out_of_band_pin_rejected(self):
        with self.assertRaisesRegex(VerificationError, "EXTERNAL_MANIFEST_PIN_MISMATCH"):
            verify(self.txt, self.manifest, "0" * 64)

    def test_pin_must_be_explicit_and_valid(self):
        for pin in ("", "not-a-sha", "A" * 64, None):
            with self.subTest(pin=pin), self.assertRaises(VerificationError):
                verify(self.txt, self.manifest, pin)

    def test_self_consistent_replacement_passes_restore_not_trusted_pin(self):
        # Attacker changes payload, recomputes BOTH manifest and TXT embedded hashes.
        # Both snapshots are structurally valid, but only the originally pinned one
        # can be matched against the trusted original SHA-256.
        altered_manifest, altered_txt, altered_pin = fixture([("safe.txt", b"changed")])
        self.assertNotEqual(altered_pin, self.good_pin)
        self.write(altered_manifest, altered_txt)
        untrusted_output = self.root / "structural-only"
        self.assertEqual(restore(self.txt, untrusted_output), 1)
        self.assertEqual((untrusted_output / "safe.txt").read_bytes(), b"changed")
        with self.assertRaisesRegex(VerificationError, "EXTERNAL_MANIFEST_PIN_MISMATCH"):
            verify(self.txt, self.manifest, self.good_pin)
        # Proof of boundary, not recommendation: trusting the attacker's NEW pin
        # would make the altered package pass all local integrity checks.
        self.assertEqual(verify(self.txt, self.manifest, altered_pin)["files"], 1)

    def test_trusted_manifest_does_not_match_changed_txt_payload(self):
        self.txt.write_bytes(self.good_txt.replace(b"hello", b"HELLO", 1))
        with self.assertRaisesRegex(VerificationError, "SHA-256 mismatch"):
            verify(self.txt, self.manifest, self.good_pin)

    def test_matching_manifest_hash_but_wrong_txt_token_rejected(self):
        self.txt.write_bytes(self.good_txt.replace(self.good_pin.encode(), b"d" * 64))
        with self.assertRaisesRegex(VerificationError, "TXT_MANIFEST_PIN_MISMATCH"):
            verify(self.txt, self.manifest, self.good_pin)

    def test_record_metadata_not_merely_payload_sha(self):
        self.txt.write_bytes(self.good_txt.replace(b'"mode":"100644"', b'"mode":"100755"'))
        with self.assertRaisesRegex(VerificationError, "metadata mismatch"):
            verify(self.txt, self.manifest, self.good_pin)

    def test_injected_extra_record_rejected(self):
        self.txt.write_bytes(self.good_txt.replace(b"@@ARIO_COMPLETE", b"@@ARIO_FILE {}\n@@ARIO_COMPLETE"))
        with self.assertRaises(VerificationError):
            verify(self.txt, self.manifest, self.good_pin)

    def test_manifest_duplicate_keys_rejected_even_with_matching_pin(self):
        raw = self.good_bytes.replace(b'"tracked_files": 1', b'"tracked_files": 1, "tracked_files": 1')
        self.manifest.write_bytes(raw)
        with self.assertRaises(VerificationError):
            verify(self.txt, self.manifest, hashlib.sha256(raw).hexdigest())

    def test_manifest_file_hash_wrong_even_if_manifest_pinned(self):
        altered = self.good_bytes.replace(hashlib.sha256(b"hello").hexdigest().encode(), b"f" * 64)
        self.manifest.write_bytes(altered)
        altered_pin = hashlib.sha256(altered).hexdigest()
        changed_txt = self.good_txt.replace(self.good_pin.encode(), altered_pin.encode())
        self.txt.write_bytes(changed_txt)
        with self.assertRaisesRegex(VerificationError, "metadata mismatch"):
            verify(self.txt, self.manifest, altered_pin)

    def test_missing_footer_and_trailing_data_rejected(self):
        variants = [self.good_txt.replace(b"@@ARIO_COMPLETE", b"@@ARIO_MISSING"),
                    self.good_txt + b"EXTRA"]
        for blob in variants:
            with self.subTest(blob_length=len(blob)):
                self.txt.write_bytes(blob)
                with self.assertRaises(VerificationError):
                    verify(self.txt, self.manifest, self.good_pin)

    def test_binary_base64_payload(self):
        manifest, txt, pin = fixture([("one.bin", b"\0\xff\xfe"), ("two.txt", b"yes")])
        self.write(manifest, txt)
        self.assertEqual(verify(self.txt, self.manifest, pin)["files"], 2)

    def test_manifest_rejects_windows_reserved_name_with_pre_extension_space(self):
        manifest, txt, pin = fixture([("CON .txt", b"x")])
        self.write(manifest, txt)
        with self.assertRaisesRegex(VerificationError, "non-portable manifest path"):
            verify(self.txt, self.manifest, pin)

    def test_manifest_rejects_unicode_nfc_aliases(self):
        manifest, txt, pin = fixture([("é.txt", b"a"), ("e" + chr(0x301) + ".txt", b"b")])
        self.write(manifest, txt)
        with self.assertRaisesRegex(VerificationError, "case/Unicode-colliding"):
            verify(self.txt, self.manifest, pin)

    def test_manifest_rejects_overlong_path_component(self):
        manifest, txt, pin = fixture([("é" * 128 + ".txt", b"x")])
        self.write(manifest, txt)
        with self.assertRaisesRegex(VerificationError, "component byte limit"):
            verify(self.txt, self.manifest, pin)

    def test_verifier_distinguishes_raw_and_base64_payload_limits(self):
        manifest, txt, pin = fixture([("binary.bin", b"\\x00" * 10)])
        self.write(manifest, txt)
        with mock.patch.object(pinned, "PER_RECORD_RAW_LIMIT", 10), \\
             mock.patch.object(pinned, "PER_RECORD_PAYLOAD_LIMIT", 20):
            self.assertEqual(verify(self.txt, self.manifest, pin)["files"], 1)

    def test_cli_refuses_missing_external_pin(self):
        completed = subprocess.run([sys.executable, str(SCRIPT),
                                    "--txt", str(self.txt),
                                    "--manifest", str(self.manifest)],
                                   capture_output=True, text=True)
        self.assertNotEqual(completed.returncode, 0)

    def test_cli_prints_scoped_status_not_authenticity_claim(self):
        completed = subprocess.run([sys.executable, str(SCRIPT),
                                    "--txt", str(self.txt),
                                    "--manifest", str(self.manifest),
                                    "--expected-manifest-sha256", self.good_pin],
                                   capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("PIN_CUSTODY_NOT_VERIFIED", completed.stdout)


if __name__ == "__main__":
    unittest.main()
