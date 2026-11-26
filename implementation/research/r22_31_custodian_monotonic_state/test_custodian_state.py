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

    def test_expected_red_valid_prefix_rollback_is_not_detected_without_external_floor(self):
        first, _, _ = self.invoke(self.request(), suffix="before-rollback")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        committed = self.journal.read_bytes()
        self.assertTrue(committed.endswith(b"\\n"))

        # A same-domain administrator deletes the complete tail. Empty is a
        # valid zero-record prefix, so the signed initial anchor still verifies.
        self.journal.write_bytes(b"")
        second_request = self.request(
            nonce="2" * 64,
            root=b"rollback-replacement-root",
            head=b"rollback-replacement-head",
        )
        second, _, _ = self.invoke(second_request, suffix="after-valid-prefix-rollback")

        # This PASS means the expected RED was reproduced: local replay accepts
        # a second 7->8 transition after the prior committed journal was erased.
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn("APPROVED epoch=8", second.stdout)
        self.assertEqual(len(self.journal.read_text().splitlines()), 1)
        self.assertNotEqual(committed, self.journal.read_bytes())

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


class R2230SourceRegressionTests(unittest.TestCase):
    def test_exact_r2230_embedded_gate_approves_two_distinct_requests_for_same_epoch(self):
        repo_root = HERE.parents[2]
        source = repo_root / "implementation/research/r22_30_tpm_clear_custody/run_swtpm_clear_custody.sh"
        shell_text = source.read_text(encoding="utf-8")
        marker = "cat > \"$SHARED/custodian_gate.py\" <<'PY'\n"
        self.assertIn(marker, shell_text)
        start = shell_text.index(marker) + len(marker)
        end = shell_text.index("\nPY\n", start)
        gate_source = shell_text[start:end] + "\n"

        with tempfile.TemporaryDirectory(prefix="ario-r22-30-repro-") as directory:
            root = Path(directory)
            gate = root / "custodian_gate.py"
            gate.write_text(gate_source, encoding="utf-8")
            private_key = root / "custodian.key"
            public_key = root / "custodian.pub"
            subprocess.run(
                ["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private_key)],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["openssl", "pkey", "-in", str(private_key), "-pubout", "-out", str(public_key)],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            anchor = {
                "device_ek_sha256": digest(b"r22.30-synthetic-ek"),
                "storage_root_sha256": digest(b"r22.30-original-storage-root"),
                "epoch": 7,
                "head_sha256": digest(b"r22.30-previous-head"),
            }
            anchor_path = root / "anchor.json"
            anchor_sig = root / "anchor.sig"
            anchor_bytes = canonical(anchor)
            anchor_path.write_bytes(anchor_bytes)
            anchor_sig.write_bytes(subprocess.run(
                ["openssl", "dgst", "-sha256", "-sign", str(private_key)],
                input=anchor_bytes, check=True, stdout=subprocess.PIPE,
            ).stdout)
            nonce_ledger = root / "consumed_nonces.jsonl"
            approvals = []
            for index in (1, 2):
                request = {
                    "device_ek_sha256": anchor["device_ek_sha256"],
                    "storage_root_sha256": digest(f"r22.30-claimed-root-{index}".encode()),
                    "previous_epoch": 7,
                    "next_epoch": 8,
                    "previous_head_sha256": anchor["head_sha256"],
                    "reason": "TPM_CLEAR_RECOVERY",
                    "nonce": f"{index:064x}",
                }
                request_path = root / f"request-{index}.json"
                response_path = root / f"response-{index}.json"
                request_path.write_bytes(canonical(request))
                result = subprocess.run([
                    sys.executable, str(gate),
                    "--anchor", str(anchor_path),
                    "--anchor-signature", str(anchor_sig),
                    "--public-key", str(public_key),
                    "--private-key", str(private_key),
                    "--nonce-ledger", str(nonce_ledger),
                    "--request", str(request_path),
                    "--response", str(response_path),
                ], text=True, capture_output=True, check=False)
                approvals.append((result.returncode, result.stdout, result.stderr, response_path))

            self.assertEqual([item[0] for item in approvals], [0, 0], approvals)
            self.assertTrue(all("APPROVED EXPLICIT_RECOVERY epoch=8" in item[1] for item in approvals))
            self.assertEqual(len(nonce_ledger.read_text().splitlines()), 2)
            self.assertEqual(anchor_path.read_bytes(), anchor_bytes)


