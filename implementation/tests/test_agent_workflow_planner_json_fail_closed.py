"""Agent, workflow and planner entry points fail closed on deep JSON input.

PR #248 bounded five CLIs against an uncaught RecursionError from
``json.loads``. The same escape remained in ``ario_agent.py``,
``ario_workflow.py`` and ``ario_planner.py``, where at least ``ario_agent
--inspect-task-id <id> --ledger <deep>`` reproduced a traceback/exit 1 on
CPython 3.14.8. These tests pin the structured, interpreter-independent
outcome for those three entry points.
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import ario_agent
import ario_planner
from ario_agent import AgentRequestError

# Deep enough to raise RecursionError from a bare json.loads on CPython 3.14
# (whose threshold is ~52k levels, unlike 3.12/3.13 which raise at ~12k).
DEEP = "[" * 100_000 + "]" * 100_000

MODULE_DIR = Path(__file__).resolve().parents[1]
TARGET_MODULES = ("ario_agent.py", "ario_workflow.py", "ario_planner.py")


class DeepInputsAreBoundedStatically(unittest.TestCase):
    def test_target_modules_no_longer_call_json_loads_directly(self):
        for name in TARGET_MODULES:
            source = (MODULE_DIR / name).read_text(encoding="utf-8")
            self.assertNotIn(
                "json.loads(", source,
                f"{name} still calls json.loads directly; route inputs through loads_bounded",
            )
            self.assertIn("from bounded_json import loads_bounded", source, name)


class AgentEntryPointFailClosedTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.deep = self.dir / "deep.json"
        self.deep.write_text(DEEP, encoding="utf-8")
        self.deep_ledger = self.dir / "deep.jsonl"
        self.deep_ledger.write_bytes((DEEP + "\n").encode("utf-8"))

    def tearDown(self):
        self._tmp.cleanup()

    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ario_agent.main(argv)
        lines = (out.getvalue() + err.getvalue()).strip().splitlines()
        self.assertEqual(len(lines), 1, lines)
        return code, json.loads(lines[0])

    def test_inspect_task_id_on_deep_ledger_fails_closed(self):
        code, result = self.run_main(
            ["--inspect-task-id", "foo", "--ledger", str(self.deep_ledger)]
        )
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("malformed JSONL ledger at line 1", result["error"])
        self.assertEqual(self.deep_ledger.read_bytes(), (DEEP + "\n").encode("utf-8"))

    def test_deep_task_json_fails_closed(self):
        code, result = self.run_main(
            ["--task", str(self.deep), "--workspace", str(self.dir),
             "--ledger", str(self.dir / "ledger.jsonl")]
        )
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("nesting-depth limit", result["error"])


class WorkflowEntryPointFailClosedTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.deep = self.dir / "deep.json"
        self.deep.write_text(DEEP, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_deep_workflow_json_fails_closed_subprocess(self):
        import subprocess
        import sys
        done = subprocess.run(
            [sys.executable, "-B", str(MODULE_DIR / "ario_workflow.py"),
             "--workflow", str(self.deep), "--workspace", str(self.dir),
             "--ledger", str(self.dir / "ledger.jsonl")],
            capture_output=True, text=True, timeout=60,
        )
        self.assertNotIn("Traceback", done.stderr, done.stderr)
        self.assertEqual(done.returncode, 2)
        result = json.loads(done.stdout)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("nesting-depth limit", result["error"])


class PlannerTransportFailClosedTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_deep_ollama_response_fails_closed(self):
        # A deep but byte-legal Ollama response must surface as the planner's
        # ordinary bounded-input error, not an uncaught RecursionError.
        class _FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self, _n=-1):
                return DEEP.encode("utf-8")

        original = ario_planner._open_local_ollama
        ario_planner._open_local_ollama = lambda request, *, timeout: _FakeResponse()
        try:
            with self.assertRaises(AgentRequestError) as caught:
                ario_planner.request_plan("goal", self.dir)
        finally:
            ario_planner._open_local_ollama = original
        self.assertNotIsInstance(caught.exception, RecursionError)
        self.assertIn("valid JSON recommendation", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
