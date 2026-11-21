"""Regression for oversized JSON integers: fail closed, never traceback.

In CPython 3.13, a 5K-digit integer formerly raised ValueError inside
json.loads; manifest CLIs only caught JSONDecodeError and escaped.
All inputs are synthetic and confined to temporary paths.
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import candidate_dossier_builder
import ledger_audit_bridge
from bounded_json import (
    JSONValueLimitExceeded,
    MAX_JSON_INTEGER_DIGITS,
    loads_bounded,
)

OVERSIZED = "9" * (MAX_JSON_INTEGER_DIGITS + 1)


class BoundedIntegerTests(unittest.TestCase):
    def test_explicit_default_integer_converter_keeps_the_bound(self):
        self.assertEqual(loads_bounded("42", parse_int=None), 42)
        with self.assertRaises(JSONValueLimitExceeded):
            loads_bounded(OVERSIZED, parse_int=None)

    def test_text_only_input_and_policy_configuration(self):
        for raw in (b"{}", bytearray(b"{}"), b"", bytearray()):
            with self.subTest(raw=raw), self.assertRaisesRegex(TypeError, "decoded str"):
                loads_bounded(raw)
        with self.assertRaises(ValueError):
            loads_bounded("0", max_depth=65)
        with self.assertRaises(TypeError):
            loads_bounded("0", cls=object)
        with self.assertRaises(TypeError):
            loads_bounded("0", parse_int=False)

    def test_boundary_is_deterministic(self):
        self.assertIsInstance(loads_bounded("9" * MAX_JSON_INTEGER_DIGITS), int)
        for literal in (OVERSIZED, "-" + OVERSIZED):
            with self.subTest(negative=literal.startswith("-")):
                with self.assertRaises(JSONValueLimitExceeded) as caught:
                    loads_bounded(literal)
                self.assertIsInstance(caught.exception, json.JSONDecodeError)
                self.assertIn("integer digit limit", str(caught.exception))

    def test_custom_parse_int_cannot_bypass_bound(self):
        self.assertEqual(loads_bounded('{"n": 123}', parse_int=str), {"n": "123"})
        with self.assertRaises(JSONValueLimitExceeded):
            loads_bounded(OVERSIZED, parse_int=str)

    def test_digits_in_json_string_are_not_numeric_literals(self):
        self.assertEqual(loads_bounded(json.dumps(OVERSIZED)), OVERSIZED)

    def test_runtime_value_error_is_structured_rejection(self):
        def reject_value(value):
            raise ValueError("synthetic converter refusal")
        with self.assertRaises(JSONValueLimitExceeded):
            loads_bounded("123", parse_int=reject_value)

    def test_syntax_errors_retain_decoder_position(self):
        with self.assertRaises(json.JSONDecodeError) as caught:
            loads_bounded('{"n": }')
        self.assertNotIsInstance(caught.exception, JSONValueLimitExceeded)
        self.assertGreater(caught.exception.pos, 0)


class ManifestCliOversizedIntegerTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        root = Path(self.scratch.name)
        self.input = root / "oversized.json"
        self.input.write_text(OVERSIZED, encoding="utf-8")
        self.ledger = root / "synthetic.jsonl"
        self.ledger.write_bytes(b'{"event":"TASK_STARTED","timestamp":"t"}\\n')

    def run_main(self, module, argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = module.main(argv)
        self.assertNotIn("Traceback", stderr.getvalue())
        lines = stdout.getvalue().strip().splitlines()
        self.assertEqual(len(lines), 1, (stdout.getvalue(), stderr.getvalue()))
        return code, json.loads(lines[0])

    def test_ledger_audit_bridge_rejects_without_traceback(self):
        code, result = self.run_main(ledger_audit_bridge, [
            str(self.input), str(self.ledger)])
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("not valid UTF-8 JSON", result["reason"])
        self.assertEqual(self.input.read_text(encoding="utf-8"), OVERSIZED)

    def test_candidate_dossier_builder_rejects_without_traceback(self):
        code, result = self.run_main(candidate_dossier_builder, [
            str(self.input), str(self.ledger), "--line", "1",
            "--claim-id", "c", "--claim-scope", "s", "--support-relation", "r",
        ])
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["admission_decision"], "NOT_EVALUATED")
        self.assertEqual(self.input.read_text(encoding="utf-8"), OVERSIZED)


if __name__ == "__main__":
    unittest.main()
