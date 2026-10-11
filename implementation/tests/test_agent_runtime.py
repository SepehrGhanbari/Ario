import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ario_agent import MAX_READ_BYTES, AgentRequestError, execute_action, inspect_execution_lock, inspect_task_history, parse_task, run_task


class BoundedAgentTests(unittest.TestCase):
    def task(self, actions):
        return {"task_id": "TASK-001", "goal": "Inspect a workspace safely", "actions": actions}

    def test_cli_rejects_invalid_task_input_before_execution(self):
        cli = Path(__file__).resolve().parents[1] / "ario_agent.py"
        for label, raw in (("invalid-utf8", b"\xff"), ("invalid-json", b"{")):
            with self.subTest(input=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                target = root / "evidence.txt"
                target.write_bytes(b"preserve")
                task_file = root / "task.json"
                task_file.write_bytes(raw)
                ledger = root / "ledger" / "events.jsonl"

                result = subprocess.run(
                    [sys.executable, "-B", "-X", "utf8", str(cli), "--task", str(task_file),
                     "--workspace", str(root), "--ledger", str(ledger)],
                    capture_output=True, text=True, encoding="utf-8", check=False,
                )

                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, "")
                response = json.loads(result.stderr)
                self.assertEqual(set(response), {"status", "error"})
                self.assertEqual(response["status"], "UNKNOWN")
                self.assertIsInstance(response["error"], str)
                self.assertTrue(response["error"])
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(target.read_bytes(), b"preserve")
                self.assertFalse(ledger.parent.exists())
                self.assertFalse(ledger.exists())
                self.assertFalse(ledger.with_name(ledger.name + ".lock").exists())
                self.assertEqual(sorted(path.name for path in root.iterdir()),
                                 ["evidence.txt", "task.json"])

    def test_cli_accepts_valid_utf8_task_input_with_or_without_bom(self):
        cli = Path(__file__).resolve().parents[1] / "ario_agent.py"
        for bom in (False, True):
            with self.subTest(bom=bom), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                target = root / "evidence.txt"
                target.write_bytes(b"ready")
                task = self.task([
                    {"step_id": "read", "tool": "read_text", "path": "evidence.txt"},
                ])
                task["goal"] = "Read caf\u00e9"
                raw = json.dumps(task, ensure_ascii=False).encode("utf-8")
                task_file = root / "task.json"
                task_file.write_bytes((b"\xef\xbb\xbf" if bom else b"") + raw)
                ledger = root / "ledger" / "events.jsonl"

                result = subprocess.run(
                    [sys.executable, "-B", "-X", "utf8", str(cli), "--task", str(task_file),
                     "--workspace", str(root), "--ledger", str(ledger)],
                    capture_output=True, text=True, encoding="utf-8", check=False,
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                response = json.loads(result.stdout)
                self.assertEqual(response["status"], "COMPLETED")
                self.assertEqual(response["goal"], task["goal"])
                self.assertEqual(target.read_bytes(), b"ready")
                self.assertTrue(ledger.is_file())
                self.assertFalse(ledger.with_name(ledger.name + ".lock").exists())

    def test_rejects_unknown_fields_and_non_allowlisted_tools(self):
        with self.assertRaisesRegex(AgentRequestError, "exactly"):
            parse_task({**self.task([{"step_id": "s1", "tool": "git_status"}]), "shell": "whoami"})
        with self.assertRaisesRegex(AgentRequestError, "not allowlisted"):
            parse_task(self.task([{"step_id": "s1", "tool": "run_shell"}]))

    def test_rejects_non_string_tool_and_path_escape(self):
        with self.assertRaisesRegex(AgentRequestError, "must be a string"):
            parse_task(self.task([{"step_id": "s1", "tool": [], "path": "."}]))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = self.task([{"step_id": "s1", "tool": "inspect_directory", "path": "../"}])
            result = run_task(task, root, root / "audit.jsonl")
            self.assertEqual(result["status"], "STOPPED")
            self.assertIn("workspace", result["steps"][0]["observation"]["error"])

    @patch("ario_agent._run")
    def test_run_tests_disables_bytecode_and_pytest_cache(self, run):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "implementation" / "tests").mkdir(parents=True)
            run.return_value = {"exit_code": 0, "stdout": "tests passed", "stderr": ""}

            result = execute_action({"tool": "run_tests"}, root)

            self.assertTrue(result["ok"])
            command, working_directory = run.call_args.args
            self.assertEqual(command, [
                sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "-q", "tests",
            ])
            self.assertEqual(working_directory, root / "implementation")
            self.assertEqual(run.call_args.kwargs, {"timeout": 180})

    @patch("ario_agent._run")
    def test_run_tests_selects_each_allowlisted_module_and_retains_selector(self, run):
        modules = (
            "test_agent_runtime.py", "test_m0_regression.py", "test_planner_runtime.py",
            "test_runtime_cli.py", "test_workflow_runtime.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "implementation" / "tests").mkdir(parents=True)
            run.return_value = {"exit_code": 0, "stdout": "selected tests passed", "stderr": ""}
            for module in modules:
                with self.subTest(module=module):
                    action = {"step_id": "verify", "tool": "run_tests", "test_module": module}
                    normalized = parse_task(self.task([action]))["actions"][0]
                    self.assertEqual(normalized, action)
                    result = execute_action(normalized, root)
                    self.assertTrue(result["ok"])
                    self.assertEqual(run.call_args.args, ([
                        sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider",
                        "-q", f"tests/{module}",
                    ], root / "implementation"))
                    self.assertEqual(run.call_args.kwargs, {"timeout": 180})

    def test_run_tests_selector_is_retained_in_failure_diagnostics(self):
        diagnostic = {
            "step_id": "verify", "tool": "run_tests",
            "test_module": "test_agent_runtime.py",
        }
        payload = {
            **self.task([{"step_id": "read", "tool": "read_text", "path": "evidence.txt"}]),
            "failure_diagnostics": [diagnostic],
        }
        self.assertEqual(parse_task(payload)["failure_diagnostics"], [diagnostic])

    def test_run_tests_rejects_invalid_selectors_before_actions_or_ledger(self):
        invalid = (None, False, 123, [], {}, "", "test_unknown.py",
                   "../test_agent_runtime.py", "test_agent_runtime.py -q")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "implementation" / "tests").mkdir(parents=True)
            target = root / "evidence.txt"
            target.write_bytes(b"preserve")
            ledger = root / "ledger" / "events.jsonl"
            for module in invalid:
                with self.subTest(module=module):
                    action = {"step_id": "verify", "tool": "run_tests", "test_module": module}
                    payload = self.task([
                        {"step_id": "read", "tool": "read_text", "path": "evidence.txt"},
                        action,
                    ])
                    with (
                        patch("ario_agent.execute_action") as execute,
                        patch("ario_agent._append_event") as append_event,
                        patch("ario_agent.os.open") as open_lock,
                    ):
                        with self.assertRaisesRegex(AgentRequestError, "allowlisted regression modules"):
                            run_task(payload, root, ledger)
                    execute.assert_not_called()
                    append_event.assert_not_called()
                    open_lock.assert_not_called()
                    self.assertFalse(ledger.parent.exists())
                    self.assertFalse(ledger.exists())
                    self.assertFalse(ledger.with_name(ledger.name + ".lock").exists())
                    self.assertEqual(target.read_bytes(), b"preserve")
                    with patch("ario_agent._run") as run:
                        with self.assertRaisesRegex(AgentRequestError, "allowlisted regression modules"):
                            execute_action(action, root)
                        run.assert_not_called()

    def test_run_tests_selector_is_invalid_on_other_tools(self):
        action = {
            "step_id": "inspect", "tool": "inspect_directory", "path": ".",
            "test_module": "test_agent_runtime.py",
        }
        with self.assertRaisesRegex(AgentRequestError, "valid only for run_tests"):
            parse_task(self.task([action]))
        with tempfile.TemporaryDirectory() as directory, patch("ario_agent._run") as run:
            with self.assertRaisesRegex(AgentRequestError, "valid only for run_tests"):
                execute_action(action, Path(directory))
            run.assert_not_called()

    def test_inspect_execution_lock_reports_valid_record_without_modifying_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "audit.jsonl"
            lock = root / "audit.jsonl.lock"
            original = json.dumps({"pid": 123, "task_id": "TASK-LOCKED", "started_at": "2026-10-09T00:00:00+00:00"}).encode()
            lock.write_bytes(original)

            result = inspect_execution_lock(ledger)

            self.assertEqual(result["status"], "LOCK_PRESENT")
            self.assertEqual(result["lock_record"]["pid"], 123)
            self.assertEqual(result["lock_record"]["task_id"], "TASK-LOCKED")
            self.assertEqual(result["sha256"], hashlib.sha256(original).hexdigest())
            self.assertFalse(result["write_performed"])
            self.assertFalse(result["automatic_removal"])
            self.assertEqual(lock.read_bytes(), original)

    def test_inspect_execution_lock_reports_absent_lock_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "audit.jsonl"

            result = inspect_execution_lock(ledger)

            self.assertEqual(result["status"], "NO_LOCK")
            self.assertFalse(result["write_performed"])
            self.assertFalse(result["automatic_removal"])

    def test_inspect_execution_lock_malformed_record_returns_unknown_without_modification(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "audit.jsonl"
            lock = Path(str(ledger) + ".lock")
            original = b"not-json"
            lock.write_bytes(original)

            result = inspect_execution_lock(ledger)

            self.assertEqual(result["status"], "UNKNOWN")
            self.assertFalse(result["write_performed"])
            self.assertFalse(result["automatic_removal"])
            self.assertEqual(lock.read_bytes(), original)

    def test_inspect_execution_lock_bounds_oversized_file_read_without_modification(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "audit.jsonl"
            lock = Path(str(ledger) + ".lock")
            original = b"x" * (MAX_READ_BYTES + 100)
            lock.write_bytes(original)

            original_open = Path.open
            read_sizes = []

            class ReadRecorder:
                def __init__(self, stream):
                    self.stream = stream

                def __enter__(self):
                    self.stream.__enter__()
                    return self

                def __exit__(self, *args):
                    return self.stream.__exit__(*args)

                def read(self, size=-1):
                    read_sizes.append(size)
                    return self.stream.read(size)

            def tracked_open(path, *args, **kwargs):
                stream = original_open(path, *args, **kwargs)
                if path == lock:
                    return ReadRecorder(stream)
                return stream

            with patch.object(Path, "open", tracked_open):
                result = inspect_execution_lock(ledger)

            self.assertEqual(result["status"], "UNKNOWN")
            self.assertIn("exceeds the", result["error"])
            self.assertNotIn("sha256", result)
            self.assertEqual(read_sizes, [MAX_READ_BYTES + 1])
            self.assertFalse(result["write_performed"])
            self.assertFalse(result["automatic_removal"])
            self.assertEqual(lock.read_bytes(), original)

    def test_existing_execution_lock_blocks_task_without_modifying_target_or_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "notes.txt"
            target.write_text("unchanged", encoding="utf-8")
            ledger = root / "audit.jsonl"
            lock = root / "audit.jsonl.lock"
            lock.write_text('{"pid": 123, "task_id": "OTHER-TASK"}', encoding="utf-8")
            target_before = target.read_bytes()
            lock_before = lock.read_bytes()
            task = self.task([{"step_id": "s1", "tool": "replace_text", "path": "notes.txt",
                               "expected_sha256": hashlib.sha256(target_before).hexdigest(),
                               "content": "must not be written"}])

            with self.assertRaisesRegex(AgentRequestError, "task execution lock already exists"):
                run_task(task, root, ledger)

            self.assertEqual(target.read_bytes(), target_before)
            self.assertFalse(ledger.exists())
            self.assertEqual(lock.read_bytes(), lock_before)

    def test_execution_lock_is_removed_after_task_finishes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "notes.txt").write_text("unchanged", encoding="utf-8")
            ledger = root / "audit.jsonl"

            result = run_task(self.task([{"step_id": "s1", "tool": "read_text", "path": "notes.txt"}]), root, ledger)

            self.assertEqual(result["status"], "COMPLETED")
            self.assertFalse((root / "audit.jsonl.lock").exists())

    def test_duplicate_task_id_is_rejected_before_actions_or_ledger_append(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "notes.txt"
            target.write_text("unchanged", encoding="utf-8")
            ledger = root / "audit.jsonl"
            task = self.task([{"step_id": "s1", "tool": "read_text", "path": "notes.txt"}])

            first = run_task(task, root, ledger)
            self.assertEqual(first["status"], "COMPLETED")
            ledger_before = ledger.read_bytes()
            target_before = target.read_bytes()

            with self.assertRaisesRegex(AgentRequestError, "already exists.*duplicate execution"):
                run_task(task, root, ledger)

            self.assertEqual(ledger.read_bytes(), ledger_before)
            self.assertEqual(target.read_bytes(), target_before)

    def test_malformed_existing_ledger_blocks_task_before_any_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "notes.txt"
            target.write_text("unchanged", encoding="utf-8")
            ledger = root / "audit.jsonl"
            ledger.write_text('{"event":"TASK_STARTED"}\nnot-json\n', encoding="utf-8")
            ledger_before = ledger.read_bytes()
            target_before = target.read_bytes()
            task = self.task([{"step_id": "s1", "tool": "read_text", "path": "notes.txt"}])

            with self.assertRaisesRegex(AgentRequestError, "malformed at line 2"):
                run_task(task, root, ledger)

            self.assertEqual(ledger.read_bytes(), ledger_before)
            self.assertEqual(target.read_bytes(), target_before)

    def test_successful_steps_are_observed_and_ledger_is_append_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "notes.txt").write_text("read-only observation", encoding="utf-8")
            ledger = root / "audit.jsonl"
            ledger.write_text('{"previous":true}\n', encoding="utf-8")
            task = self.task([
                {"step_id": "s1", "tool": "read_text", "path": "notes.txt"},
                {"step_id": "s2", "tool": "inspect_directory", "path": "."},
            ])
            result = run_task(task, root, ledger)
            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual(result["steps"][0]["observation"]["content"], "read-only observation")
            records = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertTrue(records[0]["previous"])
            self.assertEqual(records[-1]["status"], "COMPLETED")

    def test_replace_text_requires_hash_and_keeps_external_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            target = root / "notes.txt"
            target.write_text("before", encoding="utf-8")
            digest = hashlib.sha256(b"before").hexdigest()
            ledger = Path(directory) / "state" / "events.jsonl"
            task = self.task([{
                "step_id": "s1", "tool": "replace_text", "path": "notes.txt",
                "content": "after", "expected_sha256": digest,
            }])
            result = run_task(task, root, ledger)
            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual(target.read_text(encoding="utf-8"), "after")
            step = result["steps"][0]["observation"]
            backup = Path(step["backup_path"])
            self.assertTrue(backup.is_file())
            self.assertEqual(backup.read_text(encoding="utf-8"), "before")
            self.assertEqual(step["before_sha256"], digest)
            self.assertTrue(step["verified"])
            self.assertFalse(backup.is_relative_to(root))

    def test_replace_text_hash_mismatch_leaves_target_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            target = root / "notes.txt"
            target.write_text("keep", encoding="utf-8")
            task = self.task([{
                "step_id": "s1", "tool": "replace_text", "path": "notes.txt",
                "content": "replace", "expected_sha256": "0" * 64,
            }])
            result = run_task(task, root, Path(directory) / "state" / "events.jsonl")
            self.assertEqual(result["status"], "STOPPED")
            self.assertEqual(target.read_text(encoding="utf-8"), "keep")
            self.assertIn("SHA-256 precondition failed", result["steps"][0]["observation"]["error"])

    def test_restore_backup_requires_hash_and_preserves_current_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            target = root / "notes.txt"
            target.write_text("new version", encoding="utf-8")
            ledger = Path(directory) / "state" / "events.jsonl"
            backup = ledger.parent / "backups" / "fixture" / "notes.txt"
            backup.parent.mkdir(parents=True)
            backup.write_text("old version", encoding="utf-8")
            expected = hashlib.sha256(b"new version").hexdigest()
            task = self.task([{
                "step_id": "s1", "tool": "restore_backup", "path": "notes.txt",
                "backup_path": "fixture/notes.txt", "expected_sha256": expected,
            }])
            result = run_task(task, root, ledger)
            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual(target.read_text(encoding="utf-8"), "old version")
            observation = result["steps"][0]["observation"]
            self.assertTrue(observation["verified"])
            preserved = Path(observation["preserved_current_version"])
            self.assertEqual(preserved.read_text(encoding="utf-8"), "new version")

    def test_restore_backup_hash_mismatch_does_not_change_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            target = root / "notes.txt"
            target.write_text("keep this", encoding="utf-8")
            ledger = Path(directory) / "state" / "events.jsonl"
            backup = ledger.parent / "backups" / "fixture" / "notes.txt"
            backup.parent.mkdir(parents=True)
            backup.write_text("old", encoding="utf-8")
            task = self.task([{
                "step_id": "s1", "tool": "restore_backup", "path": "notes.txt",
                "backup_path": "fixture/notes.txt", "expected_sha256": "0" * 64,
            }])
            result = run_task(task, root, ledger)
            self.assertEqual(result["status"], "STOPPED")
            self.assertEqual(target.read_text(encoding="utf-8"), "keep this")

    def test_recovery_preflight_records_target_and_backup_evidence_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            target = root / "notes.txt"
            target.write_bytes(b"current version")
            ledger = Path(directory) / "state" / "events.jsonl"
            backup = ledger.parent / "backups" / "fixture" / "notes.txt"
            backup.parent.mkdir(parents=True)
            backup.write_bytes(b"saved version")
            before_target = target.read_bytes()
            before_backup = backup.read_bytes()
            task = self.task([{
                "step_id": "preflight", "tool": "recovery_preflight",
                "path": "notes.txt", "backup_path": "fixture/notes.txt",
            }])
            result = run_task(task, root, ledger)
            self.assertEqual(result["status"], "COMPLETED")
            observation = result["steps"][0]["observation"]
            self.assertEqual(observation["assessment"], "DIFFERENT_CONTENT")
            self.assertFalse(observation["content_identical"])
            self.assertFalse(observation["write_performed"])
            self.assertFalse(observation["automatic_restore"])
            self.assertEqual(observation["target_sha256"], hashlib.sha256(before_target).hexdigest())
            self.assertEqual(observation["backup_sha256"], hashlib.sha256(before_backup).hexdigest())
            self.assertEqual(target.read_bytes(), before_target)
            self.assertEqual(backup.read_bytes(), before_backup)
            events = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            step_event = next(event for event in events if event["event"] == "STEP_OBSERVED")
            self.assertEqual(step_event["observation"]["assessment"], "DIFFERENT_CONTENT")

    def test_recovery_preflight_rejects_backup_traversal_before_any_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            target = root / "notes.txt"
            target.write_text("keep", encoding="utf-8")
            task = self.task([{
                "step_id": "preflight", "tool": "recovery_preflight",
                "path": "notes.txt", "backup_path": "../outside.txt",
            }])
            result = run_task(task, root, Path(directory) / "state" / "events.jsonl")
            self.assertEqual(result["status"], "STOPPED")
            self.assertEqual(target.read_text(encoding="utf-8"), "keep")

    def test_file_fingerprint_and_backup_inspection_are_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            target = root / "result.txt"
            target.write_bytes(b"current bytes")
            ledger = Path(directory) / "state" / "events.jsonl"
            backup = ledger.parent / "backups" / "fixture" / "result.txt"
            backup.parent.mkdir(parents=True)
            backup.write_bytes(b"saved version")

            task = self.task([
                {"step_id": "fingerprint", "tool": "file_fingerprint", "path": "result.txt"},
                {"step_id": "backup", "tool": "inspect_backup", "path": "fixture/result.txt"},
            ])
            result = run_task(task, root, ledger)
            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual(
                result["steps"][0]["observation"]["sha256"],
                hashlib.sha256(b"current bytes").hexdigest(),
            )
            self.assertEqual(result["steps"][0]["observation"]["bytes"], len(b"current bytes"))
            self.assertEqual(
                result["steps"][1]["observation"]["sha256"],
                hashlib.sha256(b"saved version").hexdigest(),
            )
            self.assertEqual(target.read_bytes(), b"current bytes")
            self.assertEqual(backup.read_bytes(), b"saved version")

    def test_guarded_replace_then_verify_workflow_completes_and_records_all_steps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            target = root / "result.txt"
            target.write_text("before", encoding="utf-8")
            before_hash = hashlib.sha256(b"before").hexdigest()
            ledger = Path(directory) / "state" / "events.jsonl"
            task = self.task([
                {"step_id": "replace", "tool": "replace_text", "path": "result.txt",
                 "content": "expected result", "expected_sha256": before_hash},
                {"step_id": "verify", "tool": "verify_text", "path": "result.txt",
                 "expected_text": "expected result"},
                {"step_id": "readback", "tool": "read_text", "path": "result.txt"},
            ])
            result = run_task(task, root, ledger)
            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual([s["status"] for s in result["steps"]],
                             ["SUCCEEDED", "SUCCEEDED", "SUCCEEDED"])
            self.assertTrue(result["steps"][1]["observation"]["matches"])
            self.assertEqual(result["steps"][2]["observation"]["content"], "expected result")

    def test_guarded_workflow_stops_after_failed_postcondition(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            target = root / "result.txt"
            target.write_text("before", encoding="utf-8")
            before_hash = hashlib.sha256(b"before").hexdigest()
            task = self.task([
                {"step_id": "replace", "tool": "replace_text", "path": "result.txt",
                 "content": "new value", "expected_sha256": before_hash},
                {"step_id": "verify", "tool": "verify_text", "path": "result.txt",
                 "expected_text": "wrong value"},
                {"step_id": "readback", "tool": "read_text", "path": "result.txt"},
            ])
            result = run_task(task, root, Path(directory) / "state" / "events.jsonl")
            self.assertEqual(result["status"], "STOPPED")
            self.assertEqual([s["status"] for s in result["steps"]], ["SUCCEEDED", "FAILED"])
            self.assertEqual(len(result["steps"]), 2)
            self.assertEqual(target.read_text(encoding="utf-8"), "new value")

    def test_verify_text_passes_only_when_postcondition_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "result.txt"
            target.write_text("expected result", encoding="utf-8")
            task = self.task([{
                "step_id": "s1", "tool": "verify_text", "path": "result.txt",
                "expected_text": "expected result",
            }])
            result = run_task(task, root, root / "audit.jsonl")
            self.assertEqual(result["status"], "COMPLETED")
            self.assertTrue(result["steps"][0]["observation"]["matches"])

    def test_verify_text_mismatch_stops_task_and_blocks_later_steps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "result.txt"
            target.write_text("actual result", encoding="utf-8")
            task = self.task([
                {"step_id": "s1", "tool": "verify_text", "path": "result.txt",
                 "expected_text": "expected result"},
                {"step_id": "s2", "tool": "inspect_directory", "path": "."},
            ])
            result = run_task(task, root, root / "audit.jsonl")
            self.assertEqual(result["status"], "STOPPED")
            self.assertEqual(len(result["steps"]), 1)
            self.assertFalse(result["steps"][0]["observation"]["matches"])
            self.assertEqual(target.read_text(encoding="utf-8"), "actual result")

    def test_verify_text_rejects_unexpected_fields(self):
        with self.assertRaisesRegex(AgentRequestError, "verify_text accepts only"):
            parse_task(self.task([{
                "step_id": "s1", "tool": "verify_text", "path": "result.txt",
                "expected_text": "x", "content": "not allowed",
            }]))

    def test_history_inspection_marks_unfinished_task_incomplete_without_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "audit.jsonl"
            ledger.write_text("\n".join([
                json.dumps({"event": "TASK_STARTED", "task_id": "CRASH-1", "goal": "edit file"}),
                json.dumps({"event": "STEP_OBSERVED", "task_id": "CRASH-1", "step_id": "s1",
                            "tool": "replace_text", "status": "SUCCEEDED", "timestamp": "t1"}),
            ]) + "\n", encoding="utf-8")
            before = ledger.read_bytes()
            result = inspect_task_history("CRASH-1", ledger)
            self.assertEqual(result["status"], "INCOMPLETE")
            self.assertEqual(result["next_step_state"], "UNKNOWN")
            self.assertFalse(result["automatic_resume"])
            self.assertFalse(result["write_performed"])
            self.assertEqual(result["observed_steps"][0]["step_id"], "s1")
            self.assertEqual(ledger.read_bytes(), before)

    def test_history_inspection_accepts_real_completed_task_without_explicit_criteria(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "notes.txt").write_text("inspection only", encoding="utf-8")
            ledger = root / "audit.jsonl"
            task = self.task([{"step_id": "s1", "tool": "read_text", "path": "notes.txt"}])

            execution = run_task(task, root, ledger)
            self.assertEqual(execution["status"], "COMPLETED")

            events = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            started = next(event for event in events if event["event"] == "TASK_STARTED")
            self.assertEqual(started["success_criteria_ids"], [])
            self.assertEqual(started["step_ids"], ["s1"])

            ledger_before = ledger.read_bytes()
            history = inspect_task_history(task["task_id"], ledger)
            self.assertEqual(history["status"], "COMPLETED")
            self.assertEqual(history["next_step_state"], "NONE_TERMINAL_TASK")
            self.assertFalse(history["automatic_resume"])
            self.assertFalse(history["write_performed"])
            self.assertEqual(ledger.read_bytes(), ledger_before)

    def test_history_inspection_recognizes_terminal_task(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "audit.jsonl"
            events = [
                {"event": "TASK_STARTED", "task_id": "DONE-1",
                 "goal": "inspect", "step_ids": ["s1"],
                 "success_criteria_ids": []},
                {"event": "STEP_OBSERVED", "task_id": "DONE-1",
                 "step_id": "s1", "tool": "read_text",
                 "status": "SUCCEEDED"},
                {"event": "TASK_FINISHED", "task_id": "DONE-1",
                 "status": "COMPLETED"},
            ]
            ledger.write_text(
                "\n".join(json.dumps(event) for event in events) + "\n",
                encoding="utf-8",
            )
            result = inspect_task_history("DONE-1", ledger)
            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual(result["next_step_state"], "NONE_TERMINAL_TASK")
            self.assertFalse(result["automatic_resume"])

    def test_history_inspection_requires_exact_declared_step_observations(self):
        cases = [
            ("missing", ["s1"], []),
            ("duplicate", ["s1"], ["s1", "s1"]),
            ("extra", ["s1"], ["s1", "s2"]),
            ("out_of_order", ["s1", "s2"], ["s2", "s1"]),
            ("legacy_without_contract", None, []),
        ]
        for label, declared, observed in cases:
            with self.subTest(case=label), tempfile.TemporaryDirectory() as directory:
                ledger = Path(directory) / "audit.jsonl"
                started = {
                    "event": "TASK_STARTED",
                    "task_id": "STEP-CONTRACT",
                    "goal": "inspect",
                    "success_criteria_ids": [],
                }
                if declared is not None:
                    started["step_ids"] = declared

                events = [started]
                for step_id in observed:
                    events.append({
                        "event": "STEP_OBSERVED",
                        "task_id": "STEP-CONTRACT",
                        "step_id": step_id,
                        "tool": "read_text",
                        "status": "SUCCEEDED",
                    })
                events.append({
                    "event": "TASK_FINISHED",
                    "task_id": "STEP-CONTRACT",
                    "status": "COMPLETED",
                })
                ledger.write_text(
                    "\n".join(json.dumps(event) for event in events) + "\n",
                    encoding="utf-8",
                )
                before = ledger.read_bytes()
                result = inspect_task_history("STEP-CONTRACT", ledger)
                self.assertEqual(result["status"], "UNKNOWN")
                self.assertEqual(
                    result["error"],
                    "step observations do not exactly match the start contract",
                )
                self.assertFalse(result["automatic_resume"])
                self.assertFalse(result["write_performed"])
                self.assertEqual(ledger.read_bytes(), before)

    def test_history_inspection_rejects_contradictory_completion_and_event_order(self):
        cases = {
            "failed_step": [
                {"event": "TASK_STARTED", "task_id": "X", "goal": "test"},
                {"event": "STEP_OBSERVED", "task_id": "X", "step_id": "s1",
                 "tool": "read_text", "status": "FAILED"},
                {"event": "TASK_FINISHED", "task_id": "X", "status": "COMPLETED"},
            ],
            "failed_criterion": [
                {"event": "TASK_STARTED", "task_id": "X", "goal": "test"},
                {"event": "GOAL_CRITERION_OBSERVED", "task_id": "X",
                 "criterion": "c1", "status": "FAILED"},
                {"event": "TASK_FINISHED", "task_id": "X", "status": "COMPLETED"},
            ],
            "step_after_finish": [
                {"event": "TASK_STARTED", "task_id": "X", "goal": "test"},
                {"event": "TASK_FINISHED", "task_id": "X", "status": "COMPLETED"},
                {"event": "STEP_OBSERVED", "task_id": "X", "step_id": "s1",
                 "tool": "read_text", "status": "SUCCEEDED"},
            ],
            "event_before_start": [
                {"event": "STEP_OBSERVED", "task_id": "X", "step_id": "s1",
                 "tool": "read_text", "status": "SUCCEEDED"},
                {"event": "TASK_STARTED", "task_id": "X", "goal": "test"},
                {"event": "TASK_FINISHED", "task_id": "X", "status": "COMPLETED"},
            ],
        }
        expected_errors = {
            "failed_step": "completed task has failed or unrecognized step observations",
            "failed_criterion": "completed task has failed or unrecognized goal criteria",
            "step_after_finish": "task events appear after TASK_FINISHED",
            "event_before_start": "task event precedes TASK_STARTED",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, events in cases.items():
                with self.subTest(case=name):
                    ledger = root / f"{name}.jsonl"
                    ledger.write_text(
                        "\n".join(json.dumps(event) for event in events) + "\n",
                        encoding="utf-8",
                    )
                    before = ledger.read_bytes()
                    result = inspect_task_history("X", ledger)
                    self.assertEqual(result["status"], "UNKNOWN")
                    self.assertEqual(result.get("error"), expected_errors[name])
                    self.assertFalse(result["automatic_resume"])
                    self.assertFalse(result["write_performed"])
                    self.assertEqual(ledger.read_bytes(), before)

    def test_history_inspection_fails_closed_on_malformed_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "audit.jsonl"
            ledger.write_text('{"event":"TASK_STARTED","task_id":"X"}\nnot-json\n', encoding="utf-8")
            result = inspect_task_history("X", ledger)
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertIn("malformed JSONL", result["error"])
            self.assertFalse(result["automatic_resume"])

    def test_history_inspection_requires_exact_declared_criterion_observations(self):
        cases = {
            "missing": [
                {"event": "TASK_STARTED", "task_id": "X", "goal": "test",
                 "success_criteria_ids": ["c1", "c2"]},
                {"event": "GOAL_CRITERION_OBSERVED", "task_id": "X",
                 "criterion_id": "c1", "status": "PASSED"},
                {"event": "TASK_FINISHED", "task_id": "X", "status": "COMPLETED"},
            ],
            "duplicate": [
                {"event": "TASK_STARTED", "task_id": "X", "goal": "test",
                 "success_criteria_ids": ["c1"]},
                {"event": "GOAL_CRITERION_OBSERVED", "task_id": "X",
                 "criterion_id": "c1", "status": "PASSED"},
                {"event": "GOAL_CRITERION_OBSERVED", "task_id": "X",
                 "criterion_id": "c1", "status": "PASSED"},
                {"event": "TASK_FINISHED", "task_id": "X", "status": "COMPLETED"},
            ],
            "extra": [
                {"event": "TASK_STARTED", "task_id": "X", "goal": "test",
                 "success_criteria_ids": ["c1"]},
                {"event": "GOAL_CRITERION_OBSERVED", "task_id": "X",
                 "criterion_id": "c1", "status": "PASSED"},
                {"event": "GOAL_CRITERION_OBSERVED", "task_id": "X",
                 "criterion_id": "c2", "status": "PASSED"},
                {"event": "TASK_FINISHED", "task_id": "X", "status": "COMPLETED"},
            ],
            "criterion_without_start_contract": [
                {"event": "TASK_STARTED", "task_id": "X", "goal": "test"},
                {"event": "GOAL_CRITERION_OBSERVED", "task_id": "X",
                 "criterion_id": "c1", "status": "PASSED"},
                {"event": "TASK_FINISHED", "task_id": "X", "status": "COMPLETED"},
            ],
        }

        for case_name, events in cases.items():
            with self.subTest(case=case_name), tempfile.TemporaryDirectory() as directory:
                ledger = Path(directory) / "audit.jsonl"
                ledger.write_text(
                    "\n".join(json.dumps(event) for event in events) + "\n",
                    encoding="utf-8",
                )
                before = ledger.read_bytes()

                result = inspect_task_history("X", ledger)

                self.assertEqual(result["status"], "UNKNOWN")
                self.assertFalse(result["automatic_resume"])
                self.assertFalse(result["write_performed"])
                self.assertEqual(ledger.read_bytes(), before)

    def test_stops_after_first_failed_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = self.task([
                {"step_id": "s1", "tool": "read_text", "path": "missing.txt"},
                {"step_id": "s2", "tool": "inspect_directory", "path": "."},
            ])
            result = run_task(task, root, root / "audit.jsonl")
            self.assertEqual(result["status"], "STOPPED")
            self.assertEqual(len(result["steps"]), 1)
            self.assertIn("Fail-closed", result["recovery"])



    def test_goal_contract_is_independently_verified_after_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "result.txt"
            target.write_text("expected", encoding="utf-8")
            ledger = root / "audit.jsonl"
            task = {
                **self.task([{"step_id": "inspect", "tool": "read_text", "path": "result.txt"}]),
                "success_criteria": [{
                    "criterion_id": "result-is-expected",
                    "path": "result.txt",
                    "expected_text": "expected",
                }],
            }

            result = run_task(task, root, ledger)

            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual(result["goal_verification"][0]["status"], "PASSED")
            self.assertTrue(result["goal_verification"][0]["observation"]["matches"])
            events = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            criterion_event = next(event for event in events if event["event"] == "GOAL_CRITERION_OBSERVED")
            self.assertEqual(criterion_event["criterion_id"], "result-is-expected")
            self.assertEqual(events[-1]["status"], "COMPLETED")

    def test_goal_contract_failure_stops_even_when_all_actions_succeed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "result.txt"
            target.write_text("actual", encoding="utf-8")
            task = {
                **self.task([{"step_id": "inspect", "tool": "read_text", "path": "result.txt"}]),
                "success_criteria": [{
                    "criterion_id": "result-is-expected",
                    "path": "result.txt",
                    "expected_text": "expected",
                }],
            }

            result = run_task(task, root, root / "audit.jsonl")

            self.assertEqual(result["status"], "STOPPED")
            self.assertEqual(result["goal_verification"][0]["status"], "FAILED")
            self.assertFalse(result["goal_verification"][0]["observation"]["matches"])
            self.assertIn("independent goal verification failed", result["recovery"])
            self.assertEqual(target.read_text(encoding="utf-8"), "actual")

    def test_goal_contract_observes_later_criteria_after_a_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "action.txt").write_text("inspect", encoding="utf-8")
            (root / "first.txt").write_text("actual", encoding="utf-8")
            (root / "second.txt").write_text("expected", encoding="utf-8")
            ledger = root / "audit.jsonl"
            task = {
                **self.task([{
                    "step_id": "inspect", "tool": "read_text", "path": "action.txt"
                }]),
                "success_criteria": [
                    {
                        "criterion_id": "first-mismatch",
                        "path": "first.txt",
                        "expected_text": "expected",
                    },
                    {
                        "criterion_id": "second-match",
                        "path": "second.txt",
                        "expected_text": "expected",
                    },
                ],
            }

            result = run_task(task, root, ledger)

            self.assertEqual(result["status"], "STOPPED")
            self.assertEqual(
                [(item["criterion_id"], item["status"]) for item in result["goal_verification"]],
                [("first-mismatch", "FAILED"), ("second-match", "PASSED")],
            )
            events = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            criterion_events = [
                event for event in events if event["event"] == "GOAL_CRITERION_OBSERVED"
            ]
            self.assertEqual(
                [event["criterion_id"] for event in criterion_events],
                ["first-mismatch", "second-match"],
            )
            self.assertEqual(events[-1]["status"], "STOPPED")

    def test_invalid_goal_contract_is_rejected_before_any_action(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "result.txt"
            target.write_text("unchanged", encoding="utf-8")
            ledger = root / "audit.jsonl"
            task = {
                **self.task([{
                    "step_id": "replace", "tool": "replace_text", "path": "result.txt",
                    "content": "changed", "expected_sha256": hashlib.sha256(b"unchanged").hexdigest(),
                }]),
                "success_criteria": [{
                    "criterion_id": "bad", "path": "../outside.txt", "expected_text": "x",
                }],
            }

            with self.assertRaisesRegex(AgentRequestError, "escapes the configured workspace"):
                run_task(task, root, ledger)

            self.assertEqual(target.read_text(encoding="utf-8"), "unchanged")
            self.assertFalse(ledger.exists())

    def test_goal_contract_rejects_duplicate_or_unknown_criterion_fields(self):
        base = {
            **self.task([{"step_id": "inspect", "tool": "git_status"}]),
            "success_criteria": [
                {"criterion_id": "same", "path": "result.txt", "expected_text": "x"},
                {"criterion_id": "same", "path": "result.txt", "expected_text": "x"},
            ],
        }
        with self.assertRaisesRegex(AgentRequestError, "unique and non-empty"):
            parse_task(base)
        malformed = {
            **self.task([{"step_id": "inspect", "tool": "git_status"}]),
            "success_criteria": [{
                "criterion_id": "c1", "path": "result.txt", "expected_text": "x", "shell": "no",
            }],
        }
        with self.assertRaisesRegex(AgentRequestError, "exactly criterion_id"):
            parse_task(malformed)


    def test_failed_step_runs_only_declared_read_only_diagnostics_and_remains_stopped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "present.txt"
            target.write_text("evidence", encoding="utf-8")
            ledger = root / "audit.jsonl"
            task = {
                **self.task([{
                    "step_id": "missing-read", "tool": "read_text", "path": "missing.txt"
                }]),
                "failure_diagnostics": [
                    {"step_id": "inspect-root", "tool": "inspect_directory", "path": "."},
                    {"step_id": "fingerprint-evidence", "tool": "file_fingerprint", "path": "present.txt"},
                ],
            }

            result = run_task(task, root, ledger)

            self.assertEqual(result["status"], "STOPPED")
            self.assertEqual(len(result["steps"]), 1)
            self.assertEqual([item["status"] for item in result["failure_diagnostics"]],
                             ["SUCCEEDED", "SUCCEEDED"])
            self.assertEqual(result["failure_diagnostics"][1]["observation"]["sha256"],
                             hashlib.sha256(b"evidence").hexdigest())
            events = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(
                len([event for event in events if event["event"] == "FAILURE_DIAGNOSTIC_OBSERVED"]), 2
            )
            self.assertEqual(target.read_text(encoding="utf-8"), "evidence")
            self.assertEqual(events[-1]["status"], "STOPPED")

    def test_failure_diagnostics_reject_writes_before_any_task_action(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "notes.txt"
            target.write_text("unchanged", encoding="utf-8")
            ledger = root / "audit.jsonl"
            task = {
                **self.task([{
                    "step_id": "read", "tool": "read_text", "path": "notes.txt"
                }]),
                "failure_diagnostics": [{
                    "step_id": "write", "tool": "replace_text", "path": "notes.txt",
                    "content": "changed", "expected_sha256": hashlib.sha256(b"unchanged").hexdigest(),
                }],
            }

            with self.assertRaisesRegex(AgentRequestError, "must be read-only"):
                run_task(task, root, ledger)

            self.assertEqual(target.read_text(encoding="utf-8"), "unchanged")
            self.assertFalse(ledger.exists())

    def test_failure_diagnostics_reject_workspace_escape_before_any_action(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "audit.jsonl"
            task = {
                **self.task([{
                    "step_id": "read", "tool": "git_status"
                }]),
                "failure_diagnostics": [{
                    "step_id": "escape", "tool": "read_text", "path": "../outside.txt"
                }],
            }

            with self.assertRaisesRegex(AgentRequestError, "escapes the configured workspace"):
                run_task(task, root, ledger)

            self.assertFalse(ledger.exists())


    def test_read_text_reads_large_files_in_bounded_line_chunks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "large.txt"
            lines = [f"{index:04d}:" + ("x" * 95) + chr(10) for index in range(300)]
            expected = "".join(lines)
            target.write_text(expected, encoding="utf-8", newline="")

            first = execute_action({"tool": "read_text", "path": "large.txt"}, root)
            self.assertTrue(first["ok"])
            self.assertTrue(first["truncated"])
            self.assertLessEqual(first["bytes"], 20_000)
            self.assertEqual(first["start_line"], 1)
            self.assertGreater(first["next_start_line"], 1)

            second = execute_action({
                "tool": "read_text", "path": "large.txt",
                "start_line": first["next_start_line"],
                "expected_next_start_line": 301,
                "expected_truncated": False,
            }, root)
            self.assertTrue(second["ok"])
            self.assertFalse(second["truncated"])
            self.assertEqual(first["content"] + second["content"], expected)
            self.assertEqual(second["start_line"], first["next_start_line"])
            self.assertEqual(target.read_text(encoding="utf-8"), expected)

    def test_read_text_start_line_must_be_positive_integer_and_only_for_read_text(self):
        with self.assertRaisesRegex(AgentRequestError, "positive integer"):
            parse_task(self.task([{
                "step_id": "s1", "tool": "read_text", "path": "notes.txt", "start_line": True
            }]))
        with self.assertRaisesRegex(AgentRequestError, "only for read_text"):
            parse_task(self.task([{
                "step_id": "s1", "tool": "inspect_directory", "path": ".", "start_line": 2
            }]))

    def test_read_text_rejects_changed_chunk_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "large.txt"
            target.write_text("".join(f"{index:04d}:" + ("x" * 95) + "\n" for index in range(300)), encoding="utf-8", newline="")
            first = execute_action({"tool": "read_text", "path": "large.txt"}, root)

            mismatched = execute_action({
                "tool": "read_text",
                "path": "large.txt",
                "start_line": 1,
                "expected_next_start_line": first["next_start_line"] + 1,
                "expected_truncated": True,
            }, root)

            self.assertFalse(mismatched["ok"])
            self.assertIn("next_start_line", mismatched["error"])
            self.assertTrue(mismatched["truncated"])

    def test_read_text_chunk_expectations_require_valid_paired_fields(self):
        with self.assertRaisesRegex(AgentRequestError, "positive integer"):
            parse_task(self.task([{
                "step_id": "s1", "tool": "read_text", "path": "notes.txt",
                "expected_next_start_line": True, "expected_truncated": False,
            }]))
        with self.assertRaisesRegex(AgentRequestError, "both expected_next_start_line and expected_truncated"):
            parse_task(self.task([{
                "step_id": "s1", "tool": "read_text", "path": "notes.txt",
                "expected_next_start_line": 2,
            }]))
        with self.assertRaisesRegex(AgentRequestError, "only for read_text"):
            parse_task(self.task([{
                "step_id": "s1", "tool": "git_status",
                "expected_next_start_line": 2, "expected_truncated": False,
            }]))

    def test_read_text_rejects_single_line_exceeding_chunk_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "long-line.txt").write_text("x" * 20_001, encoding="utf-8")
            with self.assertRaisesRegex(AgentRequestError, "single line longer"):
                execute_action({"tool": "read_text", "path": "long-line.txt"}, root)

if __name__ == "__main__":
    unittest.main()
