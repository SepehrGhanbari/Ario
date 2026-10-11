import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from ario_agent import AgentRequestError
from ario_workflow import parse_workflow, run_workflow


class BoundedWorkflowTests(unittest.TestCase):
    def stage(self, stage_id, task_id, actions, when=None):
        item = {
            "stage_id": stage_id,
            "task": {
                "task_id": task_id,
                "goal": f"Run {stage_id}",
                "actions": actions,
            },
        }
        if when is not None:
            item["when"] = when
        return item

    def workflow(self, stages, workflow_id="WF-001"):
        return {"workflow_id": workflow_id, "goal": "Exercise a bounded conditional workflow", "stages": stages}

    def test_completed_condition_runs_declared_branch_and_records_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "result.txt").write_text("ready", encoding="utf-8")
            ledger = root / "events.jsonl"
            payload = self.workflow([
                self.stage("inspect", "TASK-INSPECT", [{"step_id": "read", "tool": "read_text", "path": "result.txt"}]),
                self.stage("verify", "TASK-VERIFY", [{"step_id": "check", "tool": "verify_text", "path": "result.txt", "expected_text": "ready"}],
                           {"stage_id": "inspect", "status": "COMPLETED"}),
            ])

            result = run_workflow(payload, root, ledger)

            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual([s["status"] for s in result["stages"]], ["COMPLETED", "COMPLETED"])
            events = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(events[0]["event"], "WORKFLOW_STARTED")
            self.assertEqual(events[-1]["event"], "WORKFLOW_FINISHED")
            self.assertEqual(events[-1]["status"], "COMPLETED")

    def test_stopped_stage_can_select_only_predeclared_read_only_diagnostic_branch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "evidence.txt").write_text("preserve", encoding="utf-8")
            ledger = root / "events.jsonl"
            payload = self.workflow([
                self.stage("primary", "TASK-PRIMARY", [{"step_id": "missing", "tool": "read_text", "path": "missing.txt"}]),
                self.stage("diagnose", "TASK-DIAGNOSE", [{"step_id": "fingerprint", "tool": "file_fingerprint", "path": "evidence.txt"}],
                           {"stage_id": "primary", "status": "STOPPED"}),
            ])

            result = run_workflow(payload, root, ledger)

            self.assertEqual(result["status"], "STOPPED")
            self.assertEqual([s["status"] for s in result["stages"]], ["STOPPED", "COMPLETED"])
            self.assertEqual((root / "evidence.txt").read_text(encoding="utf-8"), "preserve")
            events = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(events[-1]["status"], "STOPPED")

    def test_branch_not_selected_is_skipped_without_running_its_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "events.jsonl"
            (root / "evidence.txt").write_text("ok", encoding="utf-8")
            payload = self.workflow([
                self.stage("first", "TASK-FIRST", [{"step_id": "read", "tool": "read_text", "path": "evidence.txt"}]),
                self.stage("on-stop", "TASK-STOP-BRANCH", [{"step_id": "read", "tool": "read_text", "path": "missing.txt"}],
                           {"stage_id": "first", "status": "STOPPED"}),
            ])

            result = run_workflow(payload, root, ledger)

            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual(result["stages"][1]["status"], "SKIPPED")
            self.assertIn("condition not met", result["stages"][1]["reason"])

    def test_explicit_null_condition_is_rejected_by_parser(self):
        stage = self.stage("first", "TASK-NULL", [
            {"step_id": "read", "tool": "read_text", "path": "evidence.txt"},
        ])
        stage["when"] = None

        with self.assertRaisesRegex(
            AgentRequestError, r"stages\[0\]\.when must contain exactly stage_id and status"
        ):
            parse_workflow(self.workflow([stage]))

    def test_null_condition_in_any_stage_rejects_before_actions_or_ledger_locks(self):
        for null_index in range(3):
            with self.subTest(null_index=null_index), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                target = root / "evidence.txt"
                target.write_text("preserve", encoding="utf-8")
                ledger = root / "ledger" / "events.jsonl"
                stages = [
                    self.stage(f"stage-{index}", f"TASK-{index}", [
                        {"step_id": "read", "tool": "read_text", "path": "evidence.txt"},
                    ])
                    for index in range(3)
                ]
                stages[null_index]["when"] = None

                with (
                    patch("ario_workflow.run_task") as execute,
                    patch("ario_workflow._append_event") as append_event,
                    patch("ario_workflow.os.open") as open_lock,
                ):
                    with self.assertRaisesRegex(
                        AgentRequestError,
                        rf"stages\[{null_index}\]\.when must contain exactly stage_id and status",
                    ):
                        run_workflow(self.workflow(stages), root, ledger)

                execute.assert_not_called()
                append_event.assert_not_called()
                open_lock.assert_not_called()
                self.assertFalse(ledger.parent.exists())
                self.assertFalse(ledger.exists())
                self.assertFalse(ledger.with_name(ledger.name + ".workflow.lock").exists())
                self.assertFalse(ledger.with_name(ledger.name + ".lock").exists())
                self.assertEqual(target.read_text(encoding="utf-8"), "preserve")

    def test_writes_are_rejected_in_a_stopped_branch_before_any_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "events.jsonl"
            payload = self.workflow([
                self.stage("first", "TASK-FIRST", [{"step_id": "status", "tool": "git_status"}]),
                self.stage("on-stop", "TASK-STOP-WRITE", [{
                    "step_id": "write", "tool": "replace_text", "path": "file.txt",
                    "content": "x", "expected_sha256": "0" * 64,
                }], {"stage_id": "first", "status": "STOPPED"}),
            ])

            with self.assertRaisesRegex(AgentRequestError, "read-only actions only"):
                parse_workflow(payload)
            self.assertFalse(ledger.exists())

    def test_any_write_stage_after_failure_is_skipped_even_if_other_condition_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "file.txt"
            target.write_text("unchanged", encoding="utf-8")
            ledger = root / "events.jsonl"
            payload = self.workflow([
                self.stage("first", "TASK-FAIL", [{"step_id": "missing", "tool": "read_text", "path": "absent.txt"}]),
                self.stage("diagnose", "TASK-DIAG", [{"step_id": "read", "tool": "read_text", "path": "file.txt"}],
                           {"stage_id": "first", "status": "STOPPED"}),
                self.stage("unsafe-followup", "TASK-WRITE", [{
                    "step_id": "replace", "tool": "replace_text", "path": "file.txt",
                    "content": "changed", "expected_sha256": "0" * 64,
                }], {"stage_id": "diagnose", "status": "COMPLETED"}),
            ])

            result = run_workflow(payload, root, ledger)

            self.assertEqual(result["status"], "STOPPED")
            self.assertEqual(result["stages"][2]["status"], "SKIPPED")
            self.assertIn("write-capable stage skipped", result["stages"][2]["reason"])
            self.assertEqual(target.read_text(encoding="utf-8"), "unchanged")

    def test_rejects_forward_reference_duplicate_ids_and_unknown_fields(self):
        base = self.workflow([
            self.stage("first", "TASK-1", [{"step_id": "status", "tool": "git_status"}]),
            self.stage("second", "TASK-2", [{"step_id": "status", "tool": "git_status"}],
                       {"stage_id": "future", "status": "COMPLETED"}),
        ])
        with self.assertRaisesRegex(AgentRequestError, "earlier stage"):
            parse_workflow(base)
        duplicate = self.workflow([
            self.stage("same", "TASK-1", [{"step_id": "status", "tool": "git_status"}]),
            self.stage("same", "TASK-2", [{"step_id": "status", "tool": "git_status"}]),
        ])
        with self.assertRaisesRegex(AgentRequestError, "stage_id must be unique"):
            parse_workflow(duplicate)
        unknown = {**self.workflow([self.stage("one", "TASK-1", [{"step_id": "status", "tool": "git_status"}])]), "shell": "no"}
        with self.assertRaisesRegex(AgentRequestError, "exactly workflow_id"):
            parse_workflow(unknown)

    def test_stage_count_accepts_eight_and_rejects_nine(self):
        stages = [
            self.stage(
                f"stage-{index}",
                f"TASK-{index}",
                [{"step_id": "status", "tool": "git_status"}],
            )
            for index in range(1, 9)
        ]

        parsed = parse_workflow(self.workflow(stages))
        self.assertEqual(len(parsed["stages"]), 8)

        too_many_stages = [
            self.stage(
                f"stage-{index}",
                f"TASK-{index}",
                [{"step_id": "status", "tool": "git_status"}],
            )
            for index in range(1, 10)
        ]
        with self.assertRaisesRegex(AgentRequestError, "between 1 and 8 stages"):
            parse_workflow(self.workflow(too_many_stages))

    def test_eight_stage_workflow_executes_and_records_every_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "evidence.txt").write_text("observed", encoding="utf-8")
            ledger = root / "events.jsonl"
            stages = [
                self.stage(
                    f"stage-{index}",
                    f"TASK-{index}",
                    [{"step_id": "read", "tool": "read_text", "path": "evidence.txt"}],
                )
                for index in range(1, 9)
            ]

            result = run_workflow(
                self.workflow(stages, workflow_id="WF-EIGHT-STAGES"), root, ledger
            )

            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual([stage["status"] for stage in result["stages"]], ["COMPLETED"] * 8)
            events = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            stage_events = [
                event for event in events if event["event"] == "WORKFLOW_STAGE_OBSERVED"
            ]
            self.assertEqual([event["stage_id"] for event in stage_events], [
                f"stage-{index}" for index in range(1, 9)
            ])
            self.assertEqual(events[-1]["event"], "WORKFLOW_FINISHED")
            self.assertEqual(events[-1]["status"], "COMPLETED")

    def test_duplicate_workflow_id_is_rejected_before_new_stages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "events.jsonl"
            ledger.write_text(json.dumps({"event": "WORKFLOW_FINISHED", "workflow_id": "WF-DUP"}) + "\n", encoding="utf-8")
            target = root / "evidence.txt"
            target.write_text("unchanged", encoding="utf-8")
            payload = self.workflow([
                self.stage("inspect", "TASK-NEW", [{"step_id": "read", "tool": "read_text", "path": "evidence.txt"}]),
            ], workflow_id="WF-DUP")

            with self.assertRaisesRegex(AgentRequestError, "refusing duplicate execution"):
                run_workflow(payload, root, ledger)
            self.assertEqual(target.read_text(encoding="utf-8"), "unchanged")
            self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 1)

    def test_used_task_id_in_later_stage_blocks_workflow_before_first_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "evidence.txt"
            target.write_text("unchanged", encoding="utf-8")
            ledger = root / "events.jsonl"
            ledger.write_text(json.dumps({"event": "TASK_FINISHED", "task_id": "TASK-ALREADY-USED", "status": "COMPLETED"}) + "\n", encoding="utf-8")
            payload = self.workflow([
                self.stage("first", "TASK-NEW", [{"step_id": "read", "tool": "read_text", "path": "evidence.txt"}]),
                self.stage("second", "TASK-ALREADY-USED", [{"step_id": "read", "tool": "read_text", "path": "evidence.txt"}],
                           {"stage_id": "first", "status": "COMPLETED"}),
            ])

            with self.assertRaisesRegex(AgentRequestError, "refusing duplicate execution"):
                run_workflow(payload, root, ledger)
            events = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(events), 1)
            self.assertEqual(target.read_text(encoding="utf-8"), "unchanged")

    def test_invalid_branch_path_is_rejected_before_any_ledger_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "events.jsonl"
            payload = self.workflow([
                self.stage("first", "TASK-1", [{"step_id": "read", "tool": "read_text", "path": "ok.txt"}]),
                self.stage("second", "TASK-2", [{"step_id": "read", "tool": "read_text", "path": "../escape.txt"}],
                           {"stage_id": "first", "status": "COMPLETED"}),
            ])

            with self.assertRaisesRegex(AgentRequestError, "escapes the configured workspace"):
                run_workflow(payload, root, ledger)
            self.assertFalse(ledger.exists())


if __name__ == "__main__":
    unittest.main()
