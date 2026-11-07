"""Offline fake-key tests; no provider, production key, or historical file access."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from crypto import ario_file_aead_v1 as lib


class ArioFileAeadResearchTests(unittest.TestCase):
    def setUp(self):
        self.content_key = os.urandom(32)
        self.anchor_key = os.urandom(32)

    def seal(self, data=b"PRIVATE DEMO", path="labs/conversation.jsonl",
             kind="conversation-history", generation=1):
        return lib.seal_file(data, path, kind, generation, self.content_key, self.anchor_key)

    def open(self, envelope, receipt, path="labs/conversation.jsonl",
             kind="conversation-history", generation=1):
        return lib.open_file(envelope, receipt, path, kind, generation,
                             self.content_key, self.anchor_key)

    def test_binary_round_trip(self):
        box, receipt = self.seal(b"hello\x00\xff\xe2\x98\x83")
        self.assertEqual(self.open(box, receipt), b"hello\x00\xff\xe2\x98\x83")
        self.assertNotIn(b"hello", box)

    def test_same_length_ciphertext_edit_rejected(self):
        box, receipt = self.seal()
        data = json.loads(box)
        encrypted = bytearray(lib.unb64(data["ciphertext"]))
        encrypted[0] ^= 1
        data["ciphertext"] = lib.b64(bytes(encrypted))
        with self.assertRaisesRegex(lib.Refuse, "EXTERNAL_RECEIPT_MISMATCH"):
            self.open(lib.canonical(data), receipt)

    def test_tampered_envelope_and_public_hash_rejected_without_anchor_key(self):
        box, receipt = self.seal()
        data = json.loads(box)
        encrypted = bytearray(lib.unb64(data["ciphertext"]))
        encrypted[2] ^= 1
        data["ciphertext"] = lib.b64(bytes(encrypted))
        wrong_box = lib.canonical(data)
        fraudulent = json.loads(receipt)
        fraudulent["envelope_sha256"] = lib.sha256(wrong_box)
        with self.assertRaisesRegex(lib.Refuse, "EXTERNAL_RECEIPT_INVALID"):
            self.open(wrong_box, lib.canonical(fraudulent))

    def test_wrong_decrypt_key_rejected(self):
        box, receipt = self.seal()
        with self.assertRaisesRegex(lib.Refuse, "AEAD_AUTHENTICATION_FAILED"):
            lib.open_file(box, receipt, "labs/conversation.jsonl", "conversation-history",
                          1, os.urandom(32), self.anchor_key)

    def test_valid_file_swapped_to_wrong_logical_path_rejected(self):
        box, receipt = self.seal(path="logs/A.jsonl")
        with self.assertRaisesRegex(lib.Refuse, "EXTERNAL_RECEIPT_MISMATCH"):
            self.open(box, receipt, path="logs/B.jsonl")

    def test_rollback_rejected_only_with_external_expected_generation(self):
        box, receipt = self.seal(generation=1)
        self.assertEqual(self.open(box, receipt, generation=1), b"PRIVATE DEMO")
        with self.assertRaisesRegex(lib.Refuse, "EXTERNAL_RECEIPT_MISMATCH"):
            self.open(box, receipt, generation=2)

    def test_two_random_seals_happen_to_differ_not_a_nonce_reuse_proof(self):
        a, _ = self.seal()
        b, _ = self.seal()
        x = json.loads(a)["header"]
        y = json.loads(b)["header"]
        self.assertNotEqual((x["salt"], x["nonce"]), (y["salt"], y["nonce"]))

    def test_wrong_anchor_key_rejected(self):
        box, receipt = self.seal()
        with self.assertRaisesRegex(lib.Refuse, "EXTERNAL_RECEIPT_INVALID"):
            lib.open_file(box, receipt, "labs/conversation.jsonl", "conversation-history",
                          1, self.content_key, os.urandom(32))

    def test_three_named_files_commitment_not_independent_storage(self):
        files = [
            ("a.jsonl", b"one", "conversation-history"),
            ("b.md", b"PUBLIC", "public-document"),
            ("c.json", b'{"findings":"UNKNOWN"}', "research-evidence"),
        ]
        envelopes, receipts = {}, {}
        for name, data, kind in files:
            envelopes[name], receipts[name] = self.seal(data, path=name, kind=kind)
        root = lib.collection_receipt(receipts, self.anchor_key, generation=3)
        lib.verify_collection(receipts, root, self.anchor_key, expected_generation=3)
        for name, data, kind in files:
            self.assertEqual(self.open(envelopes[name], receipts[name],
                                       path=name, kind=kind), data)
        substituted = dict(receipts)
        substituted["b.md"] = receipts["a.jsonl"]
        with self.assertRaisesRegex(lib.Refuse, "COLLECTION_ROOT_MISMATCH"):
            lib.verify_collection(substituted, root, self.anchor_key, 3)

    def test_wrong_content_class_rejected(self):
        box, receipt = self.seal(kind="research-evidence")
        with self.assertRaisesRegex(lib.Refuse, "EXTERNAL_RECEIPT_MISMATCH"):
            self.open(box, receipt, kind="conversation-history")

    def test_noncanonical_or_traversal_paths_rejected(self):
        for path in ("../etc/passwd", "/etc/passwd", "a/../b", "a\\b",
                     "a//b", "", "./a", "a/./b"):
            with self.subTest(path=path), self.assertRaises(lib.Refuse):
                self.seal(path=path)

    def test_invalid_key_and_key_role_reuse_rejected(self):
        with self.assertRaisesRegex(lib.Refuse, "KEY_ROLE_REUSE"):
            lib.seal_file(b"a", "a", "other", 1, self.content_key, self.content_key)
        with self.assertRaisesRegex(lib.Refuse, "INVALID_CONTENT_MASTER_KEY"):
            lib.seal_file(b"a", "a", "other", 1, b"x", self.anchor_key)

    def test_full_sha_detects_same_size_byte_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "events.jsonl"
            p.write_bytes(b'{"timestamp_utc":"2026-11-05T00:00:00Z"}\n')
            original = lib.LocalIntegrityBaseline.capture(p)
            raw = bytearray(p.read_bytes())
            raw[raw.index(b"2026")] = ord("9")
            p.write_bytes(raw)
            self.assertEqual(len(raw), original.byte_count)
            with self.assertRaisesRegex(lib.Refuse, "LEDGER_SAME_SIZE_BYTES_MUTATED"):
                original.verify_before_append(p)

    def test_unchanged_bytes_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "events.jsonl"
            p.write_bytes(b'{"x":1}\n')
            original = lib.LocalIntegrityBaseline.capture(p)
            original.verify_before_append(p)

    def test_distinct_inode_replacement_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "events.jsonl"
            p.write_bytes(b'{"x":1}\n')
            original = lib.LocalIntegrityBaseline.capture(p)
            other = Path(tmp) / "other"
            other.write_bytes(p.read_bytes())
            self.assertNotEqual(p.stat().st_ino, other.stat().st_ino)
            os.replace(other, p)
            with self.assertRaisesRegex(lib.Refuse, "LEDGER_REPLACED"):
                original.verify_before_append(p)

    def test_hardlink_alias_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "events.jsonl"
            p.write_bytes(b"ok\n")
            os.link(p, Path(tmp) / "alias")
            with self.assertRaisesRegex(lib.Refuse, "LEDGER_NOT_PRIVATE_REGULAR_FILE"):
                lib.LocalIntegrityBaseline.capture(p)

    def test_symlink_alias_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / "real"
            real.write_bytes(b"ok\n")
            link = Path(tmp) / "link"
            try:
                link.symlink_to(real)
            except (OSError, NotImplementedError) as exc:
                self.skipTest("symlink creation unavailable: " + type(exc).__name__)
            with self.assertRaisesRegex(lib.Refuse, "LEDGER_SYMLINK"):
                lib.LocalIntegrityBaseline.capture(link)


    def test_nested_untrusted_json_must_fail_as_refuse_not_recursionerror(self):
        box, _ = self.seal()
        hostile_receipt = (b"[" * 20000) + b"0" + (b"]" * 20000)
        with self.assertRaisesRegex(lib.Refuse, "MALFORMED_ENVELOPE_OR_RECEIPT"):
            self.open(box, hostile_receipt)

    def test_symlink_unavailable_should_skip_not_error(self):
        from unittest.mock import patch
        with patch.object(Path, "symlink_to", side_effect=OSError("symlink privilege absent")):
            with self.assertRaises(unittest.SkipTest):
                self.test_symlink_alias_refused()

    def test_baseline_uses_only_bounded_size_reads(self):
        from unittest.mock import patch
        class ReadGuard:
            def __init__(self, base):
                self.base = base
            def __enter__(self):
                self.base.__enter__()
                return self
            def __exit__(self, *args):
                return self.base.__exit__(*args)
            def read(self, size=-1):
                if type(size) is not int or size <= 0:
                    raise AssertionError("UNBOUNDED_FILE_READ")
                return self.base.read(size)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "events.jsonl"
            payload = (b"synthetic-long-archive:" + b"x" * 2700000)
            p.write_bytes(payload)
            old_fdopen = os.fdopen
            def guarded_fdopen(fd, mode, *args, **kwargs):
                return ReadGuard(old_fdopen(fd, mode, *args, **kwargs))
            with patch.object(lib.os, "fdopen", side_effect=guarded_fdopen):
                base = lib.LocalIntegrityBaseline.capture(p)
            self.assertEqual(base.byte_count, len(payload))
            self.assertEqual(base.content_sha256, lib.sha256(payload))

    def test_visible_metadata_is_not_confidential(self):
        box, receipt = self.seal(path="private/sensitive-research.jsonl",
                                 kind="conversation-history")
        self.assertIn(b"private/sensitive-research.jsonl", box)
        self.assertIn(b"conversation-history", receipt)
        self.assertNotIn(b"PRIVATE DEMO", box)

    def test_old_valid_generation_remains_acceptable_without_external_pin(self):
        box1, receipt1 = self.seal(data=b"old", path="history.jsonl", generation=1)
        box2, receipt2 = self.seal(data=b"new", path="history.jsonl", generation=2)
        self.assertEqual(self.open(box2, receipt2, path="history.jsonl", generation=2), b"new")
        # This is a *limit* demonstration: choosing the old generation admits rollback.
        self.assertEqual(self.open(box1, receipt1, path="history.jsonl", generation=1), b"old")


if __name__ == "__main__":
    unittest.main()
