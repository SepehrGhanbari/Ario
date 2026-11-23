"""Research regression for bounded single-file CLI JSON request reads.

No ledger events or other files are changed by these tests; the oversized
synthetic payload is ~4 MiB, never an unbounded stress test.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ario_agent
import ario_cli
import ario_workflow
from bounded_json import (
    JSONDepthExceeded,
    JSONValueLimitExceeded,
    MAX_JSON_DEPTH,
    MAX_JSON_FILE_BYTES,
    load_json_file_bounded,
)


class BoundedFileHelperTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.path = Path(self.scratch.name) / "request.json"

    def test_limit_minus_one_and_exact_boundary(self):
        for size in (63, 64):
            with self.subTest(size=size):
                self.path.write_bytes(b'"' + b"x" * (size - 2) + b'"')
                self.assertEqual(len(load_json_file_bounded(self.path, max_bytes=64)), size - 2)

    def test_one_byte_over_boundary_rejected_before_decode(self):
        self.path.write_bytes(b'"' + b"x" * 62 + b'"' + b'\xff')
        with self.assertRaises(JSONValueLimitExceeded) as caught:
            load_json_file_bounded(self.path, max_bytes=64)
        self.assertIn("byte limit 64", str(caught.exception))
        self.assertEqual(caught.exception.doc, "")

    def test_utf8_bom_preserved(self):
        self.path.write_bytes(b"\xef\xbb\xbf" + b' {"valid": true} ')
        self.assertEqual(load_json_file_bounded(self.path, max_bytes=64), {"valid": True})

    def test_multibyte_bound_counts_bytes_not_codepoints(self):
        raw = json.dumps({"text": "\u00e9"}, ensure_ascii=False).encode("utf-8")
        self.path.write_bytes(raw)
        self.assertEqual(load_json_file_bounded(self.path, max_bytes=len(raw)), {"text": "\u00e9"})
        with self.assertRaises(JSONValueLimitExceeded):
            load_json_file_bounded(self.path, max_bytes=len(raw) - 1)

    def test_bad_utf8_is_decode_error(self):
        self.path.write_bytes(b'"\xff"')
        with self.assertRaises(UnicodeDecodeError):
            load_json_file_bounded(self.path, max_bytes=64)

    def test_large_max_bytes_and_bool_not_accepted(self):
        self.path.write_bytes(b"{}")
        for bad in (True, False, 0, -1, 1.5, None, MAX_JSON_FILE_BYTES + 1):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    load_json_file_bounded(self.path, max_bytes=bad)

    def test_decoder_depth_limit_remains(self):
        self.path.write_bytes(("[" * (MAX_JSON_DEPTH + 1) + "0" + "]" * (MAX_JSON_DEPTH + 1)).encode())
        with self.assertRaises(JSONDepthExceeded):
            load_json_file_bounded(self.path, max_bytes=1024)

    def test_non_file_error_kept(self):
        with self.assertRaises(FileNotFoundError):
            load_json_file_bounded(self.path, max_bytes=64)


class OversizedCliFileTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.file = self.root / "over-limit.json"
        self.file.write_bytes(b'"' + b"x" * (MAX_JSON_FILE_BYTES - 1) + b'"')
        self.assertEqual(self.file.stat().st_size, MAX_JSON_FILE_BYTES + 1)
        self.ledger = self.root / "should-not-be-created.jsonl"

    def _call(self, mod, argv, use_argv=False):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            if use_argv:
                with patch.object(sys, "argv", [mod.__file__, *argv]):
                    status = mod.main()
            else:
                status = mod.main(argv)
        lines = (stdout.getvalue() + stderr.getvalue()).strip().splitlines()
        self.assertEqual(len(lines), 1, lines)
        return status, json.loads(lines[0])

    def test_ario_cli_unknown_exit2_and_no_ledger(self):
        code, output = self._call(ario_cli, ["--input", str(self.file), "--ledger", str(self.ledger)])
        self.assertEqual(code, 2)
        self.assertEqual(output["verdict"], "UNKNOWN")
        self.assertIn("input byte limit", output["detail"])
        self.assertFalse(self.ledger.exists())

    def test_agent_unknown_exit2_and_no_ledger(self):
        code, output = self._call(ario_agent, ["--task", str(self.file), "--workspace", str(self.root), "--ledger", str(self.ledger)])
        self.assertEqual(code, 2)
        self.assertEqual(output["status"], "UNKNOWN")
        self.assertIn("input byte limit", output["error"])
        self.assertFalse(self.ledger.exists())

    def test_workflow_unknown_exit2_and_no_ledger(self):
        code, output = self._call(ario_workflow, ["--workflow", str(self.file), "--workspace", str(self.root), "--ledger", str(self.ledger)], use_argv=True)
        self.assertEqual(code, 2)
        self.assertEqual(output["status"], "UNKNOWN")
        self.assertIn("input byte limit", output["error"])
        self.assertFalse(self.ledger.exists())


if __name__ == "__main__":
    unittest.main()
