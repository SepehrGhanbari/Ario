import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATE = HERE / "custodian_state.py"


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


class CustodianStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ario-r22-31-")
        self.root = Path(self.temp.name)
        self.private = self.root / "custodian.key"
        self.public = self.root / "custodian.pub"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(self.private)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["openssl", "pkey", "-in", str(self.private), "-pubout", "-out", str(self.public)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self.anchor = {
            "format": "ARIO-R22.31-ANCHOR-V1",
            "device_ek_sha256": digest(b"synthetic-ek-7"),
            "storage_root_sha256": digest(b"synthetic-storage-root-7"),
            "epoch": 7,
            "head_sha256": digest(b"synthetic-head-7"),
        }
        self.anchor_path = self.root / "anchor.json"
        self.anchor_sig = self.root / "anchor.sig"
        self.anchor_path.write_bytes(canonical(self.anchor))
        signed = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", str(self.private)],
            input=self.anchor_path.read_bytes(), check=True, stdout=subprocess.PIPE,
        ).stdout
        self.anchor_sig.write_bytes(signed)
        self.journal = self.root / "custodian-state.jsonl"
        self.lock = self.root / "custodian-state.lock"

    def tearDown(self):
        self.temp.cleanup()

    def request(self, *, nonce="1" * 64, root=b"synthetic-storage-root-8", head=b"synthetic-head-8"):
        return {
            "device_ek_sha256": self.anchor["device_ek_sha256"],
            "storage_root_sha256": digest(root),
            "previous_epoch": 7,
            "next_epoch": 8,
            "previous_head_sha256": self.anchor["head_sha256"],
            "next_head_sha256": digest(head),
            "reason": "TPM_CLEAR_RECOVERY",
            "nonce": nonce,
        }

    def invoke(self, request, *, extra=(), suffix="default"):
        req_path = self.root / f"request-{suffix}.json"
        response = self.root / f"response-{suffix}.json"
        response_sig = self.root / f"response-{suffix}.sig"
        req_path.write_bytes(canonical(request))
        cmd = [
            sys.executable, str(GATE),
            "--anchor", str(self.anchor_path),
            "--anchor-signature", str(self.anchor_sig),
            "--public-key", str(self.public),
            "--private-key", str(self.private),
            "--journal", str(self.journal),
            "--lock", str(self.lock),
            "--request", str(req_path),
            "--response", str(response),
            "--response-signature", str(response_sig),
            *extra,
        ]
        result = subprocess.run(cmd, text=True, capture_output=True, check=False)
        return result, response, response_sig

    def verify_receipt(self, response, signature):
        subprocess.run(
            ["openssl", "dgst", "-sha256", "-verify", str(self.public),
             "-signature", str(signature), str(response)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def test_one_transition_commits_and_advances_epoch(self):
        result, response, signature = self.invoke(self.request())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        receipt = json.loads(response.read_text())
        self.assertEqual(receipt["next_epoch"], 8)
        self.assertEqual(receipt["storage_root_provenance"], "CALLER_SUPPLIED_UNATTESTED")
        self.verify_receipt(response, signature)
        self.assertEqual(len(self.journal.read_text().splitlines()), 1)

    def test_second_distinct_request_cannot_reuse_consumed_epoch(self):
        first, _, _ = self.invoke(self.request(), suffix="first")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        second_request = self.request(
            nonce="2" * 64,
            root=b"another-root-claim",
            head=b"another-next-head",
        )
        second, _, _ = self.invoke(second_request, suffix="second")
        self.assertEqual(second.returncode, 3)
        self.assertIn("REJECT EPOCH_STALE", second.stdout)
        self.assertEqual(len(self.journal.read_text().splitlines()), 1)

    def test_exact_retry_returns_original_signed_receipt_without_new_record(self):
        request = self.request()
        first, response1, sig1 = self.invoke(request, suffix="first")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        original_response = response1.read_bytes()
        original_signature = sig1.read_bytes()
        retry, response2, sig2 = self.invoke(request, suffix="retry")
        self.assertEqual(retry.returncode, 0, retry.stdout + retry.stderr)
        self.assertIn("IDEMPOTENT_RECEIPT_REPLAY", retry.stdout)
        self.assertEqual(response2.read_bytes(), original_response)
        self.assertEqual(sig2.read_bytes(), original_signature)
        self.assertEqual(len(self.journal.read_text().splitlines()), 1)

    def test_same_nonce_with_different_request_is_rejected(self):
        first, _, _ = self.invoke(self.request(), suffix="first")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        altered = self.request(root=b"altered-root", head=b"altered-head")
        retry, _, _ = self.invoke(altered, suffix="altered")
        self.assertEqual(retry.returncode, 3)
        self.assertIn("REJECT NONCE_REUSE_DIFFERENT_REQUEST", retry.stdout)
        self.assertEqual(len(self.journal.read_text().splitlines()), 1)

    def test_post_commit_crash_recovers_same_receipt(self):
        request = self.request()
        crashed, response1, _ = self.invoke(
            request, extra=("--crash-after-commit",), suffix="crash",
        )
        self.assertEqual(crashed.returncode, 99, crashed.stdout + crashed.stderr)
        self.assertFalse(response1.exists())
        self.assertEqual(len(self.journal.read_text().splitlines()), 1)
        retry, response2, signature2 = self.invoke(request, suffix="recovery")
        self.assertEqual(retry.returncode, 0, retry.stdout + retry.stderr)
        self.assertIn("IDEMPOTENT_RECEIPT_REPLAY", retry.stdout)
        self.verify_receipt(response2, signature2)
        self.assertEqual(len(self.journal.read_text().splitlines()), 1)

    def test_tampered_journal_is_rejected(self):
        first, _, _ = self.invoke(self.request(), suffix="first")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        raw = self.journal.read_bytes().replace(b"APPROVED_EXPLICIT_RECOVERY", b"DENIED_EXPLICIT_RECOVERY", 1)
        self.journal.write_bytes(raw)
        second_request = self.request(nonce="2" * 64, root=b"next-root", head=b"next-head")
        second, _, _ = self.invoke(second_request, suffix="after-tamper")
        self.assertEqual(second.returncode, 3)
        self.assertIn("REJECT JOURNAL_RECORD_HASH_MISMATCH", second.stdout)

    def test_concurrent_distinct_requests_only_one_epoch_transition_wins(self):
        processes = []
        for i in range(8):
            request = self.request(
                nonce=f"{i + 1:064x}",
                root=f"concurrent-root-{i}".encode(),
                head=f"concurrent-head-{i}".encode(),
            )
            req_path = self.root / f"concurrent-{i}.json"
            response = self.root / f"concurrent-{i}-response.json"
            response_sig = self.root / f"concurrent-{i}-response.sig"
            req_path.write_bytes(canonical(request))
            cmd = [
                sys.executable, str(GATE),
                "--anchor", str(self.anchor_path),
                "--anchor-signature", str(self.anchor_sig),
                "--public-key", str(self.public),
                "--private-key", str(self.private),
                "--journal", str(self.journal),
                "--lock", str(self.lock),
                "--request", str(req_path),
                "--response", str(response),
                "--response-signature", str(response_sig),
                "--test-delay-after-lock-ms", "120",
            ]
            processes.append(subprocess.Popen(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
        results = [p.communicate(timeout=20) + (p.returncode,) for p in processes]
        successes = [r for r in results if r[2] == 0]
        rejected = [r for r in results if r[2] == 3 and "REJECT EPOCH_STALE" in r[0]]
        self.assertEqual(len(successes), 1, results)
        self.assertEqual(len(rejected), 7, results)
        self.assertEqual(len(self.journal.read_text().splitlines()), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
