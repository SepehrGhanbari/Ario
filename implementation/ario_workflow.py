from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ario_agent import AgentRequestError, _append_event, _ensure_task_id_unused, _inside, parse_task, run_task


MAX_WORKFLOW_STAGES = 8
READ_ONLY_TOOLS = {
    "inspect_directory", "read_text", "file_fingerprint", "inspect_backup",
    "recovery_preflight", "git_status", "compile_python", "run_tests", "verify_text",
}


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_workflow(payload: Any) -> dict:
    """Validate a bounded workflow of predeclared tasks and status-based branches."""
    if not isinstance(payload, dict) or set(payload) != {"workflow_id", "goal", "stages"}:
        raise AgentRequestError("workflow must contain exactly workflow_id, goal, and stages")
    workflow_id, goal, stages = payload["workflow_id"], payload["goal"], payload["stages"]
    if not isinstance(workflow_id, str) or not workflow_id.strip():
        raise AgentRequestError("workflow_id must be a non-empty string")
    if not isinstance(goal, str) or not goal.strip():
        raise AgentRequestError("goal must be a non-empty string")
    if not isinstance(stages, list) or not stages or len(stages) > MAX_WORKFLOW_STAGES:
        raise AgentRequestError(f"stages must contain between 1 and {MAX_WORKFLOW_STAGES} stages")

    stage_ids: set[str] = set()
    task_ids: set[str] = set()
    normalized = []
    for index, stage in enumerate(stages):
        if not isinstance(stage, dict) or set(stage) - {"stage_id", "task", "when"}:
            raise AgentRequestError(f"stages[{index}] has an invalid shape")
        if not {"stage_id", "task"} <= set(stage):
            raise AgentRequestError(f"stages[{index}] requires stage_id and task")
        stage_id = stage["stage_id"]
        if not isinstance(stage_id, str) or not stage_id.strip() or stage_id in stage_ids:
            raise AgentRequestError(f"stages[{index}].stage_id must be unique and non-empty")

        condition = stage.get("when")
        normalized_condition = None
        if "when" in stage:
            if not isinstance(condition, dict) or set(condition) != {"stage_id", "status"}:
                raise AgentRequestError(f"stages[{index}].when must contain exactly stage_id and status")
            ref_id, expected_status = condition["stage_id"], condition["status"]
            if not isinstance(ref_id, str) or not ref_id.strip():
                raise AgentRequestError(f"stages[{index}].when.stage_id must be a non-empty string")
            if ref_id not in stage_ids:
                raise AgentRequestError(f"stages[{index}].when must reference an earlier stage")
            if not isinstance(expected_status, str) or expected_status not in {"COMPLETED", "STOPPED"}:
                raise AgentRequestError(f"stages[{index}].when.status must be COMPLETED or STOPPED")
            normalized_condition = {"stage_id": ref_id, "status": expected_status}

        task = parse_task(stage["task"])
        if task["task_id"] in task_ids:
            raise AgentRequestError("task_id values must be unique across workflow stages")
        task_ids.add(task["task_id"])

        # A branch explicitly selected for STOPPED may gather evidence only.
        if normalized_condition and normalized_condition["status"] == "STOPPED":
            for action in task["actions"]:
                if action["tool"] not in READ_ONLY_TOOLS:
                    raise AgentRequestError(
                        f"stage {stage_id!r} is a STOPPED branch and may contain read-only actions only"
                    )
        normalized.append({
            "stage_id": stage_id,
            "task": task,
            **({"when": normalized_condition} if normalized_condition else {}),
        })
        stage_ids.add(stage_id)

    if normalized[0].get("when"):
        raise AgentRequestError("the first workflow stage must be unconditional")
    return {"workflow_id": workflow_id, "goal": goal, "stages": normalized}


def _ensure_workflow_id_unused(ledger: Path, workflow_id: str) -> None:
    if not ledger.exists():
        return
    try:
        lines = ledger.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise AgentRequestError(f"cannot inspect existing ledger before workflow: {exc}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AgentRequestError(
                f"existing ledger is malformed at line {line_number}; refusing to start workflow"
            ) from exc
        if not isinstance(event, dict):
            raise AgentRequestError(
                f"existing ledger has an invalid event at line {line_number}; refusing to start workflow"
            )
        if event.get("workflow_id") == workflow_id:
            raise AgentRequestError(
                f"workflow_id {workflow_id!r} already exists in the ledger; refusing duplicate execution"
            )


def run_workflow(payload: Any, workspace: str | Path, ledger_path: str | Path) -> dict:
    workflow = parse_workflow(payload)
    root = Path(workspace).resolve()
    if not root.is_dir():
        raise AgentRequestError("workspace must be an existing directory")

    # Preflight every declared path, including paths in branches that may be skipped.
    for stage in workflow["stages"]:
        task = stage["task"]
        for action in task["actions"]:
            if "path" in action and action["tool"] != "inspect_backup":
                _inside(root, action["path"])
        for criterion in task.get("success_criteria", []):
            _inside(root, criterion["path"])
        for diagnostic in task.get("failure_diagnostics", []):
            if "path" in diagnostic and diagnostic["tool"] != "inspect_backup":
                _inside(root, diagnostic["path"])

    ledger = Path(ledger_path).resolve()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    lock_path = ledger.with_name(ledger.name + ".workflow.lock")
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise AgentRequestError(
            f"workflow lock already exists at {lock_path}; inspect before any manual removal"
        ) from exc

    try:
        try:
            os.write(lock_fd, json.dumps({
                "workflow_id": workflow["workflow_id"],
                "pid": os.getpid(),
                "started_at": _timestamp(),
            }).encode("utf-8"))
        finally:
            os.close(lock_fd)

        _ensure_workflow_id_unused(ledger, workflow["workflow_id"])
        # Refuse a partially executed workflow if any declared task ID was already used.
        for stage in workflow["stages"]:
            _ensure_task_id_unused(ledger, stage["task"]["task_id"])
        result = {
            "workflow_id": workflow["workflow_id"],
            "goal": workflow["goal"],
            "status": "RUNNING",
            "stages": [],
            "started_at": _timestamp(),
            "control_basis": (
                "Only predeclared stages and exact prior-stage status conditions are evaluated. "
                "A STOPPED stage never becomes COMPLETED because diagnostics succeed."
            ),
        }
        _append_event(ledger, {
            "event": "WORKFLOW_STARTED",
            "workflow_id": workflow["workflow_id"],
            "goal": workflow["goal"],
            "timestamp": result["started_at"],
        })

        stage_results: dict[str, str] = {}
        failure_seen = False
        for stage in workflow["stages"]:
            stage_id = stage["stage_id"]
            condition = stage.get("when")
            should_run = True
            reason = None
            if condition is not None:
                observed_status = stage_results.get(condition["stage_id"])
                should_run = observed_status == condition["status"]
                if not should_run:
                    reason = (
                        f"condition not met: {condition['stage_id']} status was "
                        f"{observed_status or 'NOT_RUN'}, expected {condition['status']}"
                    )
            elif result["stages"] and stage_results.get(result["stages"][-1]["stage_id"]) != "COMPLETED":
                should_run = False
                reason = "unconditional continuation is skipped after a non-completed stage"

            task = stage["task"]
            if failure_seen and any(action["tool"] not in READ_ONLY_TOOLS for action in task["actions"]):
                should_run = False
                reason = "write-capable stage skipped because an earlier workflow stage stopped"

            if not should_run:
                stage_result = {"stage_id": stage_id, "status": "SKIPPED", "reason": reason}
                result["stages"].append(stage_result)
                stage_results[stage_id] = "SKIPPED"
                _append_event(ledger, {
                    "event": "WORKFLOW_STAGE_OBSERVED",
                    "workflow_id": workflow["workflow_id"],
                    **stage_result,
                    "timestamp": _timestamp(),
                })
                continue

            try:
                task_result = run_task(task, root, ledger)
                stage_status = task_result["status"]
                stage_result = {
                    "stage_id": stage_id,
                    "task_id": task["task_id"],
                    "status": stage_status,
                    "task_result": task_result,
                }
            except (AgentRequestError, OSError, UnicodeError) as exc:
                stage_status = "STOPPED"
                stage_result = {
                    "stage_id": stage_id,
                    "task_id": task["task_id"],
                    "status": "STOPPED",
                    "error": str(exc),
                }
            result["stages"].append(stage_result)
            stage_results[stage_id] = stage_status
            if stage_status == "STOPPED":
                failure_seen = True
            _append_event(ledger, {
                "event": "WORKFLOW_STAGE_OBSERVED",
                "workflow_id": workflow["workflow_id"],
                **stage_result,
                "timestamp": _timestamp(),
            })

        result["status"] = "STOPPED" if failure_seen else "COMPLETED"
        result["finished_at"] = _timestamp()
        _append_event(ledger, {
            "event": "WORKFLOW_FINISHED",
            "workflow_id": workflow["workflow_id"],
            "status": result["status"],
            "timestamp": result["finished_at"],
        })
        return result
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a bounded, declarative Ario workflow.")
    parser.add_argument("--workflow", required=True, help="Path to a UTF-8 workflow JSON file")
    parser.add_argument("--workspace", required=True, help="Existing workspace root")
    parser.add_argument("--ledger", required=True, help="Append-only JSONL event ledger")
    args = parser.parse_args()
    try:
        payload = json.loads(Path(args.workflow).read_text(encoding="utf-8-sig"))
        result = run_workflow(payload, args.workspace, args.ledger)
    except (OSError, UnicodeError, json.JSONDecodeError, AgentRequestError) as exc:
        print(json.dumps({"status": "UNKNOWN", "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
