#!/usr/bin/env python3
"""Integration/tamper tests for the independent R22.32 evidence verifier.

Run only after the R22.32 swtpm workflow has exported a real evidence bundle.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from verify_r22_32_evidence_bundle import VerificationError, verify_bundle

SOURCE = Path(os.environ["ARIO_R22_32_EVIDENCE_DIR"])


def refresh_manifest(root: Path) -> None:
    path = root / "evidence-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for name in manifest["files"]:
        manifest["files"][name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


class EvidenceBundleIntegrationTests(unittest.TestCase):
    def copy_bundle(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temp = tempfile.TemporaryDirectory(prefix="ario-r22-32-tamper-")
        target = Path(temp.name) / "bundle"
        shutil.copytree(SOURCE, target)
        return temp, target

    def assert_rejected_after_mutation(self, filename: str, mutation) -> None:
        temp, target = self.copy_bundle()
        try:
            mutation(target / filename)
            refresh_manifest(target)
            with self.assertRaises(VerificationError):
                verify_bundle(target)
        finally:
            temp.cleanup()

    def test_real_swtpm_bundle_verifies_offline(self) -> None:
        result = verify_bundle(SOURCE)
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(result["checks"]["nv_certify_signature_and_fields"], "PASS_RSASSA_SHA256")
        self.assertIn("external timestamp independence not established", result["challenge_issue_order"])
        self.assertEqual(result["transition_receipt"], "NOT_EMITTED")

    def test_rejects_nv_signature_tampering_after_manifest_refresh(self) -> None:
        def mutate(path: Path) -> None:
            data = bytearray(path.read_bytes())
            data[-1] ^= 0x01
            path.write_bytes(data)
        self.assert_rejected_after_mutation("nv-attestation.sig", mutate)

    def test_rejects_challenge_nonce_mismatch_after_manifest_refresh(self) -> None:
        def mutate(path: Path) -> None:
            value = path.read_text(encoding="ascii").strip()
            path.write_text(("0" if value[0] != "0" else "1") + value[1:] + "\n", encoding="ascii")
        self.assert_rejected_after_mutation("custodian-challenge-nonce.txt", mutate)

    def test_rejects_custodian_challenge_signature_tampering(self) -> None:
        def mutate(path: Path) -> None:
            data = bytearray(path.read_bytes())
            data[-1] ^= 0x01
            path.write_bytes(data)
        self.assert_rejected_after_mutation("custodian-challenge.sig", mutate)

    def test_rejects_custodian_anchor_signature_tampering(self) -> None:
        def mutate(path: Path) -> None:
            data = bytearray(path.read_bytes())
            data[-1] ^= 0x01
            path.write_bytes(data)
        self.assert_rejected_after_mutation("custodian-anchor.sig", mutate)

    def test_rejects_modified_signed_challenge_even_after_manifest_refresh(self) -> None:
        def mutate(path: Path) -> None:
            value = json.loads(path.read_text(encoding="utf-8"))
            value["next_head_sha256"] = "0" * 64
            path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        self.assert_rejected_after_mutation("custodian-challenge.json", mutate)

    def test_rejects_nv_readback_not_matching_storage_root(self) -> None:
        def mutate(path: Path) -> None:
            data = bytearray(path.read_bytes())
            data[0] ^= 0x01
            path.write_bytes(data)
        self.assert_rejected_after_mutation("nv-contents.bin", mutate)

    def test_rejects_pcr_value_not_matching_event_extension(self) -> None:
        def mutate(path: Path) -> None:
            data = bytearray(path.read_bytes())
            data[-1] ^= 0x01
            path.write_bytes(data)
        self.assert_rejected_after_mutation("pcr23-after.bin", mutate)

    def test_rejects_extra_file_even_when_manifest_is_unchanged(self) -> None:
        temp, target = self.copy_bundle()
        try:
            (target / "unexpected.txt").write_text("extra\n", encoding="utf-8")
            with self.assertRaises(VerificationError):
                verify_bundle(target)
        finally:
            temp.cleanup()

    def test_rejects_manifest_hash_tampering(self) -> None:
        temp, target = self.copy_bundle()
        try:
            path = target / "evidence-manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["files"]["nv-attestation.bin"] = "0" * 64
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(VerificationError):
                verify_bundle(target)
        finally:
            temp.cleanup()


if __name__ == "__main__":
    if not SOURCE.is_dir():
        raise SystemExit("ARIO_R22_32_EVIDENCE_DIR must point to a completed raw evidence bundle")
    unittest.main(verbosity=2)
