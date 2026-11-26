"""RIO-01 R2.2: real subprocess, metadata-only IPC, synthetic archive only.

No real memory or Ollama is read. Tests do NOT prove separate OS identity.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
WORKER = REPO / "implementation" / "core" / "historical_metadata_ipc_worker_r2.py"
sys.path.insert(0, str(REPO / "implementation"))
from core.historical_metadata_ipc_worker_r2 import (  # noqa: E402
    OP, SCHEMA, WorkerHold, _request_from_bytes,
)


class TestHistoricalMetadataIPCR2(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="rio01-ipc-lab-")
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "RIO01_SYNTHETIC_ARCHIVE.jsonl"
        self.question = "Synthetic question for external process?"
        self.secret = "SYNTHETIC_PRIVATE_ARCHIVE_REPLY_NEVER_ON_WIRE"
        row = {
            "record_id": "fake-r1", "session_id": "fake-s1",
            "record_version": "15.3", "user": self.question, "ario": self.secret,
            "user_sha256": hashlib.sha256(self.question.encode()).hexdigest(),
            "ario_sha256": hashlib.sha256(self.secret.encode()).hexdigest(),
            "event_sha256": "a" * 64, "relations": [],
        }
        self.raw = (json.dumps(row) + "\n").encode()
        self.path.write_bytes(self.raw)
        self.pin = hashlib.sha256(self.raw).hexdigest()
        self.request = {
            "op": OP, "archive_path": str(self.path),
            "expected_sha256": self.pin,
            "question": self.question, "mode": "HISTORICAL",
        }

    def _child(self, data=None, *, flags=None):
        raw = json.dumps(self.request).encode() if data is None else data
        command = [sys.executable, "-I", "-B", str(WORKER)]
        command += ["--research-synthetic-only"] if flags is None else flags
        result = subprocess.run(
            command, input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=12, cwd=str(REPO), check=False,
        )
        self.assertNotIn(self.secret.encode(), result.stdout)
        self.assertNotIn(self.secret.encode(), result.stderr)
        self.assertNotIn(self.question.encode(), result.stdout)
        self.assertNotIn(self.question.encode(), result.stderr)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(len(result.stdout.splitlines()), 1)
        return result.returncode, json.loads(result.stdout.decode())

    def test_real_subprocess_never_returns_quote(self):
        code, receipt = self._child()
        self.assertEqual(code, 0)
        self.assertEqual(receipt["schema"], SCHEMA)
        self.assertEqual(receipt["status"], "METADATA_ONLY_NOT_AUTHENTICATED")
        self.assertEqual(receipt["disposition"], "RECALLED_HISTORICAL_ONLY")
        self.assertEqual(receipt["archive_sha256"], self.pin)
        self.assertEqual(receipt["source_line"], 1)
        self.assertFalse(receipt["independent_custody_established"])
        self.assertFalse(receipt["real_os_sandbox_established"])
        for key in ("historical_quote", "rendered_html", "model_prompt", "question", "archive_path"):
            self.assertNotIn(key, receipt)
        self.assertEqual(self.path.read_bytes(), self.raw)

    def test_current_question_has_no_quote_or_line(self):
        self.request["mode"] = "CURRENT"
        code, receipt = self._child()
        self.assertEqual(code, 0)
        self.assertEqual(receipt["disposition"], "RECHECK_REQUIRED_CURRENT_QUESTION")
        self.assertNotIn("source_line", receipt)

    def test_forbidden_operations_rejected(self):
        for op in ("DISPLAY", "RAW_QUOTE", "MODEL", "TOOL", "WORKING_MEMORY", ""):
            with self.subTest(op=op):
                self.request["op"] = op
                code, receipt = self._child()
                self.assertEqual(code, 2)
                self.assertEqual(receipt["status"], "HOLD_UNSUPPORTED_IPC_OPERATION")

    def test_unknown_fields_fail_before_archive(self):
        self.request["target"] = "MODEL_PROMPT"
        self.request["archive_path"] = "not-a-file"
        code, receipt = self._child()
        self.assertEqual(code, 2)
        self.assertEqual(receipt["status"], "HOLD_UNEXPECTED_IPC_SCHEMA")

    def test_archive_byte_change_rejected(self):
        self.path.write_bytes(self.raw.replace(b"fake-r1", b"fake-r2"))
        code, receipt = self._child()
        self.assertEqual(code, 2)
        self.assertEqual(receipt["status"], "HOLD_SOURCE_SHA256_MISMATCH")

    def test_duplicate_keys_rejected(self):
        raw = json.dumps(self.request).encode().replace(
            b'"op": ', b'"op": "RAW_QUOTE", "op": ', 1
        )
        code, receipt = self._child(raw)
        self.assertEqual(code, 2)
        self.assertEqual(receipt["status"], "HOLD_DUPLICATE_IPC_KEY")

    def test_two_json_messages_rejected(self):
        raw = json.dumps(self.request).encode() + b"\n" + json.dumps(self.request).encode()
        code, receipt = self._child(raw)
        self.assertEqual(code, 2)
        self.assertEqual(receipt["status"], "HOLD_INVALID_IPC_JSON")

    def test_no_explicit_opt_in_never_reads_archive(self):
        self.request["archive_path"] = str(self.path) + ".missing"
        code, receipt = self._child(flags=[])
        self.assertEqual(code, 2)
        self.assertEqual(receipt["status"], "HOLD_EXPLICIT_SYNTHETIC_OPT_IN_REQUIRED")

    def test_filename_marker_rejects_untagged_path(self):
        self.request["archive_path"] = str(self.path.parent / "untagged.jsonl")
        code, receipt = self._child()
        self.assertEqual(code, 2)
        self.assertEqual(receipt["status"], "HOLD_SYNTHETIC_ONLY_SOURCE_REQUIRED")

    def test_invalid_field_types_fail(self):
        for key, value in (("question", 1), ("mode", False)):
            with self.subTest(key=key):
                self.request[key] = value
                code, receipt = self._child()
                self.assertEqual(code, 2)
                self.assertEqual(receipt["status"], "HOLD_UNEXPECTED_IPC_SCHEMA")
                self.request[key] = self.question if key == "question" else "HISTORICAL"

    def test_bounded_request_and_deep_json_fail(self):
        for raw, status in (
            (b" " * 8193, "HOLD_IPC_REQUEST_SIZE"),
            (b"[" * 1800, "HOLD_INVALID_IPC_JSON"),
        ):
            with self.subTest(status=status):
                code, receipt = self._child(raw)
                self.assertEqual(code, 2)
                self.assertEqual(receipt["status"], status)

    def test_same_os_account_still_reads_source(self):
        # Expected limitation: same OS account has file access.
        self.assertIn(self.secret.encode(), self.path.read_bytes())
        code, receipt = self._child()
        self.assertEqual(code, 0)
        self.assertFalse(receipt["independent_custody_established"])
        self.assertFalse(receipt["real_os_sandbox_established"])

    def test_in_process_duplicate_key_validation(self):
        with self.assertRaisesRegex(WorkerHold, "^HOLD_DUPLICATE_IPC_KEY$"):
            _request_from_bytes(b'{"op":"METADATA_LOOKUP_ONLY","op":"MODEL"}')


if __name__ == "__main__":
    unittest.main(verbosity=2)
