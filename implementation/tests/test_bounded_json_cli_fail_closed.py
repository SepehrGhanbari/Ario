"""CLI JSON inputs fail closed identically across CPython versions.

Before bounded_json, deeply nested input raised an uncaught RecursionError
(traceback, exit 1) on CPython 3.12/3.13 in five CLIs, while 3.14 returned
their ordinary structured rejection (exit 2). These tests pin the
structured outcome so it no longer depends on the interpreter.
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import admission_review_evaluator
import ario_cli
import candidate_dossier_builder
import ledger_audit_bridge
import reviewer_authorization_preflight
from bounded_json import (
    MAX_JSON_DEPTH,
    JSONDepthExceeded,
    loads_bounded,
    nesting_exceeds,
)

DEEP = "[" * 12000 + "]" * 12000


def _nested(levels: int) -> str:
    return "[" * levels + "]" * levels


class BoundedJsonUnitTests(unittest.TestCase):
    def test_depth_error_is_a_json_decode_error(self):
        with self.assertRaises(json.JSONDecodeError) as caught:
            loads_bounded(DEEP)
        self.assertIsInstance(caught.exception, JSONDepthExceeded)
        self.assertEqual(caught.exception.pos, MAX_JSON_DEPTH)

    def test_boundary(self):
        self.assertIsInstance(loads_bounded(_nested(MAX_JSON_DEPTH)), list)
        with self.assertRaises(JSONDepthExceeded):
            loads_bounded(_nested(MAX_JSON_DEPTH + 1))

    def test_brackets_and_escaped_quotes_inside_strings_are_ignored(self):
        text = json.dumps({"note": "[{" * 500 + '\\"' + "}]" * 500})
        self.assertIsNone(nesting_exceeds(text))
        self.assertIn("note", loads_bounded(text))
        self.assertIsNone(nesting_exceeds('{"a": "\\"[[["}', limit=1))
        self.assertEqual(nesting_exceeds('{"a": [[1]]}', limit=2), 7)

    def test_kwargs_are_forwarded(self):
        self.assertEqual(loads_bounded('{"a": 1}', object_pairs_hook=list), [("a", 1)])


class CliFailClosedTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.deep = self.dir / "deep.json"
        self.deep.write_text(DEEP, encoding="utf-8")
        self.ledger = self.dir / "ledger.jsonl"
        self.ledger.write_bytes(b'{"event":"TASK_STARTED","timestamp":"t"}\n')

    def tearDown(self):
        self._tmp.cleanup()

    def run_main(self, module, argv):
        """Run a CLI in-process; return exit code and its single JSON outcome."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main(argv)
        lines = (out.getvalue() + err.getvalue()).strip().splitlines()
        self.assertEqual(len(lines), 1, lines)
        return code, json.loads(lines[0])

    def assert_inputs_unchanged(self):
        self.assertEqual(self.deep.read_text(encoding="utf-8"), DEEP)
        self.assertEqual(self.ledger.read_bytes(), b'{"event":"TASK_STARTED","timestamp":"t"}\n')

    def test_ario_cli(self):
        code, result = self.run_main(ario_cli, ["--input", str(self.deep)])
        self.assertEqual(code, 2)
        self.assertEqual(result["error"], "AUDIT_INPUT_OR_EXECUTION_FAILED")
        self.assertEqual(result["verdict"], "UNKNOWN")
        self.assertIn("nesting-depth limit", result["detail"])
        self.assert_inputs_unchanged()

    def test_ledger_audit_bridge(self):
        code, result = self.run_main(ledger_audit_bridge, [str(self.deep), str(self.ledger)])
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("not valid UTF-8 JSON", result["reason"])
        self.assert_inputs_unchanged()

    def test_candidate_dossier_builder(self):
        code, result = self.run_main(candidate_dossier_builder, [
            str(self.deep), str(self.ledger), "--line", "1", "--claim-id", "c",
            "--claim-scope", "s", "--support-relation", "r",
        ])
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["admission_decision"], "NOT_EVALUATED")
        self.assert_inputs_unchanged()

    def test_admission_review_evaluator(self):
        # Existing contract: unloadable input -> UNKNOWN with exit 0.
        code, result = self.run_main(admission_review_evaluator, [
            str(self.deep), str(self.deep), str(self.ledger),
        ])
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("JSONDepthExceeded", result["reason"])
        self.assertEqual(result["admission_decision"], "NOT_EVALUATED")
        self.assert_inputs_unchanged()

    def test_reviewer_authorization_preflight(self):
        # Existing contract: unavailable bounded input -> UNKNOWN (RAC-14), exit 0.
        code, result = self.run_main(reviewer_authorization_preflight, [str(self.deep)])
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["rule_id"], "RAC-14")
        self.assertEqual(result["admission_decision"], "NOT_EVALUATED")
        self.assertEqual(result["authorization_decision"], "NOT_CHECKED")
        self.assert_inputs_unchanged()


if __name__ == "__main__":
    unittest.main()
