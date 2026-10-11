from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_STEPS = 8
MAX_READ_BYTES = 20_000
ALLOWED_TOOLS = {"inspect_directory", "read_text", "file_fingerprint", "inspect_backup", "recovery_preflight", "git_status", "compile_python", "run_tests", "replace_text", "restore_backup", "verify_text"}


class AgentRequestError(ValueError):
    pass


def _inside(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise AgentRequestError("path must be a non-empty relative path")
    candidate = Path(relative)
    if candidate.is_absolute():
        raise AgentRequestError("absolute paths are not permitted")
    lexical = root / candidate
    probe = root
    for part in candidate.parts:
        if part in ("", "."):
            continue
        if part == "..":
            probe = probe / part
            continue
        probe = probe / part
        if probe.is_symlink():
            raise AgentRequestError("symbolic-link paths are not permitted")
    resolved = lexical.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise AgentRequestError("path escapes the configured workspace") from exc
    return resolved


def parse_task(payload: Any) -> dict:
    if not isinstance(payload, dict):
        raise AgentRequestError("task must be a JSON object")
    required_fields = {"task_id", "goal", "actions"}
    allowed_fields = required_fields | {"success_criteria", "failure_diagnostics"}
    if not required_fields <= set(payload) or set(payload) - allowed_fields:
        raise AgentRequestError(
            "task must contain exactly task_id, goal, actions, and optional success_criteria/failure_diagnostics only"
        )
    if not isinstance(payload["task_id"], str) or not payload["task_id"].strip():
        raise AgentRequestError("task_id must be a non-empty string")
    if not isinstance(payload["goal"], str) or not payload["goal"].strip():
        raise AgentRequestError("goal must be a non-empty string")
    actions = payload["actions"]
    if not isinstance(actions, list) or not actions or len(actions) > MAX_STEPS:
        raise AgentRequestError(f"actions must contain between 1 and {MAX_STEPS} steps")
    seen: set[str] = set()
    normalized = []
    for index, action in enumerate(actions):
        if not isinstance(action, dict) or set(action) - {"step_id", "tool", "path", "content", "expected_sha256", "backup_path", "expected_text", "start_line", "expected_next_start_line", "expected_truncated"}:
            raise AgentRequestError(f"actions[{index}] has an invalid shape")
        if not {"step_id", "tool"} <= set(action):
            raise AgentRequestError(f"actions[{index}] requires step_id and tool")
        step_id, tool = action["step_id"], action["tool"]
        if not isinstance(tool, str):
            raise AgentRequestError(f"actions[{index}].tool must be a string")
        if not isinstance(step_id, str) or not step_id.strip() or step_id in seen:
            raise AgentRequestError(f"actions[{index}].step_id must be unique and non-empty")
        if tool not in ALLOWED_TOOLS:
            raise AgentRequestError(f"actions[{index}].tool is not allowlisted")
        if tool in {"inspect_directory", "read_text", "file_fingerprint", "inspect_backup", "recovery_preflight", "compile_python", "replace_text", "restore_backup", "verify_text"}:
            if not isinstance(action.get("path"), str):
                raise AgentRequestError(f"actions[{index}] requires a relative path")
        elif "path" in action:
            raise AgentRequestError(f"actions[{index}] does not accept path")
        if tool == "replace_text":
            if not isinstance(action.get("content"), str):
                raise AgentRequestError(f"actions[{index}].content must be a string")
            expected = action.get("expected_sha256")
            if not isinstance(expected, str) or len(expected) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in expected):
                raise AgentRequestError(f"actions[{index}].expected_sha256 must be a 64-character SHA-256 hex digest")
        elif tool == "restore_backup":
            if not isinstance(action.get("backup_path"), str) or not action["backup_path"].strip():
                raise AgentRequestError(f"actions[{index}].backup_path must be a relative backup path")
            expected = action.get("expected_sha256")
            if not isinstance(expected, str) or len(expected) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in expected):
                raise AgentRequestError(f"actions[{index}].expected_sha256 must be a 64-character SHA-256 hex digest")
            if "content" in action or "expected_text" in action:
                raise AgentRequestError(f"actions[{index}] restore_backup does not accept content or expected_text")
        elif tool == "verify_text":
            if not isinstance(action.get("expected_text"), str):
                raise AgentRequestError(f"actions[{index}].expected_text must be a string")
            if "content" in action or "expected_sha256" in action or "backup_path" in action:
                raise AgentRequestError(f"actions[{index}] verify_text accepts only expected_text")
        elif tool == "recovery_preflight":
            if not isinstance(action.get("backup_path"), str) or not action["backup_path"].strip():
                raise AgentRequestError(f"actions[{index}].backup_path must be a relative backup path")
            if "content" in action or "expected_sha256" in action or "expected_text" in action:
                raise AgentRequestError(f"actions[{index}] recovery_preflight accepts only backup_path")
        elif "content" in action or "expected_sha256" in action or "backup_path" in action or "expected_text" in action:
            raise AgentRequestError(f"actions[{index}] content/hash/backup/expected_text fields are not valid for this tool")
        if "start_line" in action:
            if tool != "read_text":
                raise AgentRequestError(f"actions[{index}] start_line is valid only for read_text")
            start_line = action["start_line"]
            if isinstance(start_line, bool) or not isinstance(start_line, int) or start_line < 1:
                raise AgentRequestError(f"actions[{index}].start_line must be a positive integer")
        if "expected_next_start_line" in action or "expected_truncated" in action:
            if tool != "read_text":
                raise AgentRequestError(f"actions[{index}] chunk expectations are valid only for read_text")
            if not {"expected_next_start_line", "expected_truncated"} <= set(action):
                raise AgentRequestError(
                    f"actions[{index}] must provide both expected_next_start_line and expected_truncated"
                )
            expected_next = action["expected_next_start_line"]
            if isinstance(expected_next, bool) or not isinstance(expected_next, int) or expected_next < 1:
                raise AgentRequestError(f"actions[{index}].expected_next_start_line must be a positive integer")
            if not isinstance(action["expected_truncated"], bool):
                raise AgentRequestError(f"actions[{index}].expected_truncated must be a boolean")
        seen.add(step_id)
        normalized_action = {"step_id": step_id, "tool": tool}
        for field in ("path", "content", "expected_sha256", "backup_path", "expected_text", "start_line", "expected_next_start_line", "expected_truncated"):
            if field in action:
                normalized_action[field] = action[field]
        normalized.append(normalized_action)

    normalized_task = {"task_id": payload["task_id"], "goal": payload["goal"], "actions": normalized}
    if "success_criteria" in payload:
        criteria = payload["success_criteria"]
        if not isinstance(criteria, list) or not criteria or len(criteria) > MAX_STEPS:
            raise AgentRequestError(f"success_criteria must contain between 1 and {MAX_STEPS} criteria")
        criterion_ids: set[str] = set()
        normalized_criteria = []
        for index, criterion in enumerate(criteria):
            if not isinstance(criterion, dict) or set(criterion) != {"criterion_id", "path", "expected_text"}:
                raise AgentRequestError(
                    f"success_criteria[{index}] must contain exactly criterion_id, path, and expected_text"
                )
            criterion_id = criterion["criterion_id"]
            if not isinstance(criterion_id, str) or not criterion_id.strip() or criterion_id in criterion_ids:
                raise AgentRequestError(f"success_criteria[{index}].criterion_id must be unique and non-empty")
            if not isinstance(criterion["path"], str) or not criterion["path"].strip():
                raise AgentRequestError(f"success_criteria[{index}].path must be a relative path")
            if not isinstance(criterion["expected_text"], str):
                raise AgentRequestError(f"success_criteria[{index}].expected_text must be a string")
            criterion_ids.add(criterion_id)
            normalized_criteria.append({
                "criterion_id": criterion_id,
                "path": criterion["path"],
                "expected_text": criterion["expected_text"],
            })
        normalized_task["success_criteria"] = normalized_criteria
    if "failure_diagnostics" in payload:
        diagnostics = payload["failure_diagnostics"]
        if not isinstance(diagnostics, list) or not diagnostics or len(diagnostics) > MAX_STEPS:
            raise AgentRequestError(f"failure_diagnostics must contain between 1 and {MAX_STEPS} actions")
        diagnostic_task = parse_task({
            "task_id": f"{payload['task_id']}-diagnostics",
            "goal": "Read-only diagnostics for a failed task",
            "actions": diagnostics,
        })
        diagnostic_tools = {
            "inspect_directory", "read_text", "file_fingerprint", "inspect_backup",
            "recovery_preflight", "git_status", "compile_python", "run_tests", "verify_text",
        }
        for index, action in enumerate(diagnostic_task["actions"]):
            if action["tool"] not in diagnostic_tools:
                raise AgentRequestError(
                    f"failure_diagnostics[{index}] tool must be read-only; writes and restore actions are forbidden"
                )
        normalized_task["failure_diagnostics"] = diagnostic_task["actions"]
    return normalized_task


def _run(command: list[str], cwd: Path, timeout: int = 90) -> dict:
    try:
        completed = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, timeout=timeout,
            check=False, shell=False,
        )
        return {
            "exit_code": completed.returncode,
            "stdout": completed.stdout[-6000:],
            "stderr": completed.stderr[-3000:],
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "stdout": "", "stderr": f"Timed out after {timeout} seconds."}
    except OSError as exc:
        return {"exit_code": 127, "stdout": "", "stderr": str(exc)}


def _replace_existing_text(action: dict, root: Path, backup_root: Path) -> dict:
    target = _inside(root, action["path"])
    if not target.is_file():
        raise AgentRequestError("replace_text requires an existing regular file")
    if target.is_symlink():
        raise AgentRequestError("replace_text refuses symbolic links")
    backup_root = backup_root.resolve()
    try:
        backup_root.relative_to(root)
    except ValueError:
        pass
    else:
        raise AgentRequestError("backup directory must be outside the workspace")
    old_bytes = target.read_bytes()
    if len(old_bytes) > MAX_READ_BYTES:
        raise AgentRequestError(f"replace_text is limited to {MAX_READ_BYTES} original bytes")
    actual_hash = hashlib.sha256(old_bytes).hexdigest()
    expected_hash = action["expected_sha256"].lower()
    if actual_hash != expected_hash:
        raise AgentRequestError("SHA-256 precondition failed; file was not changed")
    new_bytes = action["content"].encode("utf-8")
    if len(new_bytes) > MAX_READ_BYTES:
        raise AgentRequestError(f"replace_text is limited to {MAX_READ_BYTES} replacement bytes")
    relative = target.relative_to(root)
    backup = backup_root / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") / relative
    backup.parent.mkdir(parents=True, exist_ok=False)
    backup.write_bytes(old_bytes)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=target.parent, prefix=".ario-replace-", delete=False) as temp:
            temp.write(new_bytes)
            temp.flush()
            os.fsync(temp.fileno())
            temp_name = temp.name
        os.replace(temp_name, target)
        temp_name = None
        written_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        expected_new_hash = hashlib.sha256(new_bytes).hexdigest()
        if written_hash != expected_new_hash:
            restore_name = None
            try:
                with tempfile.NamedTemporaryFile(mode="wb", dir=target.parent, prefix=".ario-restore-", delete=False) as restore:
                    restore.write(old_bytes)
                    restore.flush()
                    os.fsync(restore.fileno())
                    restore_name = restore.name
                os.replace(restore_name, target)
                restore_name = None
            finally:
                if restore_name and os.path.exists(restore_name):
                    os.unlink(restore_name)
            raise AgentRequestError("post-write hash verification failed; original bytes restored from memory")
    except Exception:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
        raise
    return {
        "ok": True,
        "path": str(relative),
        "backup_path": str(backup),
        "before_sha256": actual_hash,
        "after_sha256": written_hash,
        "bytes_written": len(new_bytes),
        "verified": True,
    }


def _restore_existing_backup(action: dict, root: Path, backup_root: Path) -> dict:
    target = _inside(root, action["path"])
    if not target.is_file() or target.is_symlink():
        raise AgentRequestError("restore_backup requires an existing regular target file")
    candidate = Path(action["backup_path"])
    if candidate.is_absolute():
        raise AgentRequestError("backup_path must be relative to the backup directory")
    backup = (backup_root / candidate).resolve()
    resolved_backup_root = backup_root.resolve()
    try:
        backup.relative_to(resolved_backup_root)
    except ValueError as exc:
        raise AgentRequestError("backup_path escapes the backup directory") from exc
    probe = resolved_backup_root
    for part in candidate.parts:
        if part in ("", "."):
            continue
        if part == "..":
            raise AgentRequestError("backup_path traversal is not permitted")
        probe = probe / part
        if probe.is_symlink():
            raise AgentRequestError("symbolic-link backup paths are not permitted")
    if not backup.is_file():
        raise AgentRequestError("backup_path does not identify an existing regular file")
    current_bytes = target.read_bytes()
    if len(current_bytes) > MAX_READ_BYTES:
        raise AgentRequestError(f"restore_backup is limited to {MAX_READ_BYTES} current bytes")
    current_hash = hashlib.sha256(current_bytes).hexdigest()
    if current_hash != action["expected_sha256"].lower():
        raise AgentRequestError("SHA-256 precondition failed; target was not changed")
    backup_bytes = backup.read_bytes()
    if len(backup_bytes) > MAX_READ_BYTES:
        raise AgentRequestError(f"restore_backup is limited to {MAX_READ_BYTES} backup bytes")
    backup_hash = hashlib.sha256(backup_bytes).hexdigest()
    relative = target.relative_to(root)
    preserve = backup_root / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") / "rollback-preimage" / relative
    preserve.parent.mkdir(parents=True, exist_ok=False)
    preserve.write_bytes(current_bytes)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=target.parent, prefix=".ario-restore-", delete=False) as temp:
            temp.write(backup_bytes)
            temp.flush()
            os.fsync(temp.fileno())
            temp_name = temp.name
        os.replace(temp_name, target)
        temp_name = None
        restored_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        if restored_hash != backup_hash:
            raise AgentRequestError("restored file hash verification failed")
    except Exception:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
        restore_name = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", dir=target.parent, prefix=".ario-recover-", delete=False) as recovery:
                recovery.write(current_bytes)
                recovery.flush()
                os.fsync(recovery.fileno())
                restore_name = recovery.name
            os.replace(restore_name, target)
            restore_name = None
        finally:
            if restore_name and os.path.exists(restore_name):
                os.unlink(restore_name)
        raise
    return {
        "ok": True,
        "path": str(relative),
        "restored_from": str(backup),
        "preserved_current_version": str(preserve),
        "before_sha256": current_hash,
        "after_sha256": restored_hash,
        "verified": True,
    }


def _inspect_backup(action: dict, backup_root: Path) -> dict:
    candidate = Path(action["path"])
    if candidate.is_absolute() or any(part == ".." for part in candidate.parts):
        raise AgentRequestError("inspect_backup path must remain beneath the backup directory")
    backup_root = backup_root.resolve()
    probe = backup_root
    for part in candidate.parts:
        if part in ("", "."):
            continue
        probe = probe / part
        if probe.is_symlink():
            raise AgentRequestError("symbolic-link backup paths are not permitted")
    target = probe.resolve()
    try:
        target.relative_to(backup_root)
    except ValueError as exc:
        raise AgentRequestError("inspect_backup path escapes the backup directory") from exc
    if not target.is_file():
        raise AgentRequestError("inspect_backup requires an existing regular backup file")
    raw = target.read_bytes()
    if len(raw) > MAX_READ_BYTES:
        raise AgentRequestError(f"inspect_backup is limited to {MAX_READ_BYTES} bytes")
    return {"ok": True, "backup_path": str(candidate), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def _validate_read_text_observation(action: dict, observation: dict) -> dict:
    """Fail closed if a bounded read does not match its precomputed chunk boundary."""
    errors = []
    if "expected_next_start_line" in action:
        if observation["next_start_line"] != action["expected_next_start_line"]:
            errors.append(
                f"read_text next_start_line mismatch: expected {action['expected_next_start_line']}, "
                f"observed {observation['next_start_line']}"
            )
        if observation["truncated"] is not action["expected_truncated"]:
            errors.append(
                f"read_text truncated mismatch: expected {action['expected_truncated']}, "
                f"observed {observation['truncated']}"
            )
    if errors:
        observation["ok"] = False
        observation["error"] = "; ".join(errors)
    return observation


def execute_action(action: dict, root: Path, backup_root: Path | None = None) -> dict:
    tool = action["tool"]
    if tool == "file_fingerprint":
        target = _inside(root, action["path"])
        if not target.is_file() or target.is_symlink():
            raise AgentRequestError("file_fingerprint requires an existing regular file")
        raw = target.read_bytes()
        if len(raw) > MAX_READ_BYTES:
            raise AgentRequestError(f"file_fingerprint is limited to {MAX_READ_BYTES} bytes")
        return {"ok": True, "path": action["path"], "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest()}
    if tool == "inspect_backup":
        if backup_root is None:
            raise AgentRequestError("inspect_backup requires an external backup directory")
        return _inspect_backup(action, backup_root)
    if tool == "recovery_preflight":
        if backup_root is None:
            raise AgentRequestError("recovery_preflight requires an external backup directory")
        target = _inside(root, action["path"])
        if not target.is_file() or target.is_symlink():
            raise AgentRequestError("recovery_preflight requires an existing regular target file")
        candidate = Path(action["backup_path"])
        if candidate.is_absolute() or any(part == ".." for part in candidate.parts):
            raise AgentRequestError("backup_path must remain beneath the backup directory")
        resolved_backup_root = backup_root.resolve()
        probe = resolved_backup_root
        for part in candidate.parts:
            if part in ("", "."):
                continue
            probe = probe / part
            if probe.is_symlink():
                raise AgentRequestError("symbolic-link backup paths are not permitted")
        backup = probe.resolve()
        try:
            backup.relative_to(resolved_backup_root)
        except ValueError as exc:
            raise AgentRequestError("backup_path escapes the backup directory") from exc
        if not backup.is_file():
            raise AgentRequestError("recovery_preflight requires an existing regular backup file")
        target_bytes = target.read_bytes()
        backup_bytes = backup.read_bytes()
        if len(target_bytes) > MAX_READ_BYTES or len(backup_bytes) > MAX_READ_BYTES:
            raise AgentRequestError(f"recovery_preflight is limited to {MAX_READ_BYTES} bytes per file")
        target_hash = hashlib.sha256(target_bytes).hexdigest()
        backup_hash = hashlib.sha256(backup_bytes).hexdigest()
        identical = target_bytes == backup_bytes
        return {
            "ok": True,
            "assessment": "IDENTICAL_CONTENT" if identical else "DIFFERENT_CONTENT",
            "write_performed": False,
            "automatic_restore": False,
            "target_path": str(target.relative_to(root)),
            "target_bytes": len(target_bytes),
            "target_sha256": target_hash,
            "backup_path": str(candidate),
            "backup_bytes": len(backup_bytes),
            "backup_sha256": backup_hash,
            "content_identical": identical,
            "next_step": "No write performed. Review these hashes and explicitly authorize a separate restore_backup action if restoration is intended."
        }
    if tool == "verify_text":
        target = _inside(root, action["path"])
        if not target.is_file():
            raise AgentRequestError("verify_text requires an existing regular file")
        raw = target.read_bytes()
        if len(raw) > MAX_READ_BYTES:
            raise AgentRequestError(f"verify_text is limited to {MAX_READ_BYTES} bytes")
        actual = raw.decode("utf-8-sig")
        matches = actual == action["expected_text"]
        return {
            "ok": matches,
            "path": action["path"],
            "matches": matches,
            "expected_sha256": hashlib.sha256(action["expected_text"].encode("utf-8")).hexdigest(),
            "actual_sha256": hashlib.sha256(raw).hexdigest(),
            "error": None if matches else "postcondition failed: file content did not match expected_text",
        }
    if tool == "restore_backup":
        if backup_root is None:
            raise AgentRequestError("restore_backup requires an external backup directory")
        return _restore_existing_backup(action, root, backup_root)
    if tool == "replace_text":
        if backup_root is None:
            raise AgentRequestError("replace_text requires an external backup directory")
        return _replace_existing_text(action, root, backup_root)
    if tool == "inspect_directory":
        target = _inside(root, action["path"])
        if not target.is_dir():
            raise AgentRequestError("inspect_directory target is not a directory")
        entries = sorted(
            ({"name": p.name, "kind": "directory" if p.is_dir() else "file"} for p in target.iterdir()),
            key=lambda item: (item["kind"], item["name"].casefold()),
        )
        return {"ok": True, "entries": entries[:200], "truncated": len(entries) > 200}
    if tool == "read_text":
        target = _inside(root, action["path"])
        if not target.is_file() or target.is_symlink():
            raise AgentRequestError("read_text target must be an existing regular file")
        start_line = action.get("start_line", 1)
        content = bytearray()
        lines_read = 0
        next_start_line = start_line
        truncated = False
        with target.open("rb") as stream:
            current_line = 1
            while current_line < start_line:
                skipped = stream.readline(MAX_READ_BYTES + 1)
                if not skipped:
                    return _validate_read_text_observation(action, {
                        "ok": True, "path": action["path"], "content": "",
                        "start_line": start_line, "next_start_line": start_line,
                        "bytes": 0, "truncated": False,
                    })
                if len(skipped) > MAX_READ_BYTES:
                    raise AgentRequestError(
                        f"read_text encountered a line longer than {MAX_READ_BYTES} bytes while seeking start_line"
                    )
                current_line += 1
            while len(content) < MAX_READ_BYTES:
                line_offset = stream.tell()
                remaining = MAX_READ_BYTES - len(content)
                line = stream.readline(remaining + 1)
                if not line:
                    break
                if len(line) > remaining:
                    stream.seek(line_offset)
                    if not content:
                        raise AgentRequestError(
                            f"read_text cannot return a single line longer than {MAX_READ_BYTES} bytes"
                        )
                    truncated = True
                    break
                content.extend(line)
                lines_read += 1
                next_start_line = start_line + lines_read
            if not truncated:
                truncated = stream.read(1) != b""
        encoding = "utf-8-sig" if start_line == 1 else "utf-8"
        try:
            decoded = bytes(content).decode(encoding)
        except UnicodeDecodeError as exc:
            raise AgentRequestError("read_text chunk is not valid UTF-8 text") from exc
        return _validate_read_text_observation(action, {
            "ok": True, "path": action["path"], "content": decoded,
            "start_line": start_line, "next_start_line": next_start_line,
            "bytes": len(content), "truncated": truncated,
        })
    if tool == "git_status":
        result = _run(["git", "status", "--short", "--branch"], root)
    elif tool == "compile_python":
        target = _inside(root, action["path"])
        if not target.is_file() or target.suffix != ".py":
            raise AgentRequestError("compile_python requires an existing .py file")
        # Compile in memory so this inspection tool does not create __pycache__ files.
        result = _run([
            sys.executable, "-c",
            "from pathlib import Path; import sys; p=Path(sys.argv[1]); compile(p.read_text(encoding='utf-8-sig'), str(p), 'exec')",
            str(target),
        ], root)
    elif tool == "run_tests":
        tests = root / "implementation" / "tests"
        if not tests.is_dir():
            raise AgentRequestError("implementation/tests directory not found")
        result = _run([
            sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "-q", "tests",
        ], root / "implementation", timeout=180)
    else:
        raise AgentRequestError("tool is not allowlisted")
    return {"ok": result["exit_code"] == 0, **result}


def _append_event(ledger: Path, event: dict) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def _ensure_task_id_unused(ledger: Path, task_id: str) -> None:
    """Refuse duplicate task IDs before any task action or ledger append."""
    if not ledger.exists():
        return
    try:
        lines = ledger.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise AgentRequestError(f"cannot inspect existing ledger before execution: {exc}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AgentRequestError(
                f"existing ledger is malformed at line {line_number}; refusing to start a task"
            ) from exc
        if not isinstance(event, dict):
            raise AgentRequestError(
                f"existing ledger has an invalid event at line {line_number}; refusing to start a task"
            )
        if event.get("task_id") == task_id:
            raise AgentRequestError(
                f"task_id {task_id!r} already exists in the ledger; refusing duplicate execution"
            )


def run_task(payload: Any, workspace: str | Path, ledger_path: str | Path) -> dict:
    task = parse_task(payload)
    root = Path(workspace).resolve()
    if not root.is_dir():
        raise AgentRequestError("workspace must be an existing directory")
    # Validate all declared goal paths before acquiring the lock or running any action.
    for criterion in task.get("success_criteria", []):
        _inside(root, criterion["path"])
    for diagnostic in task.get("failure_diagnostics", []):
        if "path" in diagnostic and diagnostic["tool"] not in {"inspect_backup"}:
            _inside(root, diagnostic["path"])
    ledger = Path(ledger_path).resolve()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    lock_path = ledger.with_name(ledger.name + ".lock")
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise AgentRequestError(
            f"task execution lock already exists at {lock_path}; another task may be running "
            "or a previous process may have stopped unexpectedly; inspect before removing it"
        ) from exc
    try:
        try:
            lock_record = json.dumps({
                "pid": os.getpid(),
                "task_id": task["task_id"],
                "started_at": datetime.now(timezone.utc).isoformat(),
            }).encode("utf-8")
            os.write(lock_fd, lock_record)
        finally:
            os.close(lock_fd)
        return _run_task_locked(task, root, ledger)
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _run_task_locked(task: dict, root: Path, ledger: Path) -> dict:
    _ensure_task_id_unused(ledger, task["task_id"])
    backup_root = ledger.parent / "backups"
    started = datetime.now(timezone.utc).isoformat()
    result = {
        "task_id": task["task_id"], "goal": task["goal"], "status": "RUNNING",
        "started_at": started, "steps": [],
        "completion_basis": (
            "Completion requires every declared action and every independently re-read success criterion to pass; "
            "this does not prove semantic properties not represented by those criteria."
            if task.get("success_criteria") else
            "Completion means all declared allowlisted steps returned success; without success_criteria, "
            "the natural-language goal has no independent final acceptance check."
        ),
    }
    _append_event(ledger, {
        "event": "TASK_STARTED",
        "task_id": task["task_id"],
        "goal": task["goal"],
        "step_ids": [action["step_id"] for action in task["actions"]],
        "success_criteria_ids": [
            criterion["criterion_id"]
            for criterion in task.get("success_criteria", [])
        ],
        "timestamp": started,
    })
    for action in task["actions"]:
        step = {"step_id": action["step_id"], "tool": action["tool"], "status": "RUNNING"}
        try:
            observation = execute_action(action, root, backup_root)
            step["observation"] = observation
            step["status"] = "SUCCEEDED" if observation.get("ok", True) else "FAILED"
        except (AgentRequestError, OSError, UnicodeError) as exc:
            step["status"] = "FAILED"
            step["observation"] = {"ok": False, "error": str(exc)}
        result["steps"].append(step)
        _append_event(ledger, {"event": "STEP_OBSERVED", "task_id": task["task_id"], **step, "timestamp": datetime.now(timezone.utc).isoformat()})
        if step["status"] != "SUCCEEDED":
            result["status"] = "STOPPED"
            result["recovery"] = (
                "Fail-closed: stopped after the first failed step. "
                "Any configured failure_diagnostics are read-only evidence gathering only; "
                "no automatic retry, rollback, or corrective write is attempted."
            )
            diagnostics = task.get("failure_diagnostics", [])
            if diagnostics:
                result["failure_diagnostics"] = []
                for diagnostic in diagnostics:
                    diagnostic_result = {
                        "step_id": diagnostic["step_id"],
                        "tool": diagnostic["tool"],
                    }
                    try:
                        observation = execute_action(diagnostic, root, backup_root)
                        diagnostic_result["observation"] = observation
                        diagnostic_result["status"] = (
                            "SUCCEEDED" if observation.get("ok", True) else "FAILED"
                        )
                    except (AgentRequestError, OSError, UnicodeError) as exc:
                        diagnostic_result["status"] = "FAILED"
                        diagnostic_result["observation"] = {"ok": False, "error": str(exc)}
                    result["failure_diagnostics"].append(diagnostic_result)
                    _append_event(ledger, {
                        "event": "FAILURE_DIAGNOSTIC_OBSERVED",
                        "task_id": task["task_id"],
                        **diagnostic_result,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
            break
    else:
        criteria = task.get("success_criteria", [])
        if criteria:
            result["goal_verification"] = []
            criteria_passed = True
            for criterion in criteria:
                try:
                    observation = execute_action({
                        "tool": "verify_text",
                        "path": criterion["path"],
                        "expected_text": criterion["expected_text"],
                    }, root, backup_root)
                except (AgentRequestError, OSError, UnicodeError) as exc:
                    observation = {"ok": False, "error": str(exc)}
                criterion_result = {
                    "criterion_id": criterion["criterion_id"],
                    "path": criterion["path"],
                    "status": "PASSED" if observation.get("ok", False) else "FAILED",
                    "observation": observation,
                }
                result["goal_verification"].append(criterion_result)
                _append_event(ledger, {
                    "event": "GOAL_CRITERION_OBSERVED",
                    "task_id": task["task_id"],
                    **criterion_result,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                if criterion_result["status"] != "PASSED":
                    criteria_passed = False
                    result["status"] = "STOPPED"
                    result["recovery"] = (
                        "Declared actions returned success, but independent goal verification failed. "
                        "No automatic retry, rollback, or corrective write was attempted."
                    )
            if criteria_passed:
                result["status"] = "COMPLETED"
        else:
            result["status"] = "COMPLETED"
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    _append_event(ledger, {"event": "TASK_FINISHED", "task_id": task["task_id"], "status": result["status"], "timestamp": result["finished_at"]})
    return result


def inspect_execution_lock(ledger_path: str | Path) -> dict:
    """Read-only inspection of the exclusive task lock beside a ledger."""
    ledger = Path(ledger_path).resolve()
    lock_path = ledger.with_name(ledger.name + ".lock")
    try:
        with lock_path.open("rb") as stream:
            raw = stream.read(MAX_READ_BYTES + 1)
    except FileNotFoundError:
        return {
            "status": "NO_LOCK",
            "lock_path": str(lock_path),
            "write_performed": False,
            "automatic_removal": False,
        }
    except OSError as exc:
        return {
            "status": "UNKNOWN",
            "lock_path": str(lock_path),
            "error": str(exc),
            "write_performed": False,
            "automatic_removal": False,
        }

    if len(raw) > MAX_READ_BYTES:
        return {
            "status": "UNKNOWN",
            "lock_path": str(lock_path),
            "error": f"lock file exceeds the {MAX_READ_BYTES}-byte inspection limit",
            "write_performed": False,
            "automatic_removal": False,
        }

    result = {
        "status": "LOCK_PRESENT",
        "lock_path": str(lock_path),
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "write_performed": False,
        "automatic_removal": False,
        "next_step": (
            "Inspect the recorded PID and confirm no matching process is active before any "
            "manual removal. Lock presence alone does not establish that the process is stale."
        ),
    }
    try:
        record = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        result["status"] = "UNKNOWN"
        result["error"] = "lock content is not valid UTF-8 JSON"
        return result
    if (
        not isinstance(record, dict)
        or not isinstance(record.get("pid"), int)
        or isinstance(record.get("pid"), bool)
        or record["pid"] <= 0
        or not isinstance(record.get("task_id"), str)
        or not record["task_id"].strip()
        or not isinstance(record.get("started_at"), str)
    ):
        result["status"] = "UNKNOWN"
        result["error"] = "lock record has an invalid shape"
        return result
    result["lock_record"] = {
        "pid": record["pid"],
        "task_id": record["task_id"],
        "started_at": record["started_at"],
    }
    return result


def inspect_task_history(task_id: str, ledger_path: str | Path) -> dict:
    """Read-only crash-recovery assessment. Never resumes or replays task actions."""
    if not isinstance(task_id, str) or not task_id.strip():
        raise AgentRequestError("task_id must be a non-empty string")
    ledger = Path(ledger_path)
    try:
        raw_lines = ledger.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        return {"task_id": task_id, "status": "UNKNOWN", "error": str(exc),
                "automatic_resume": False, "write_performed": False}
    events = []
    for line_number, line in enumerate(raw_lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return {"task_id": task_id, "status": "UNKNOWN",
                    "error": f"malformed JSONL ledger at line {line_number}",
                    "automatic_resume": False, "write_performed": False}
        if not isinstance(event, dict) or not isinstance(event.get("event"), str):
            return {"task_id": task_id, "status": "UNKNOWN",
                    "error": f"invalid event shape at line {line_number}",
                    "automatic_resume": False, "write_performed": False}
        if event.get("task_id") == task_id:
            events.append(event)
    starts = [event for event in events if event["event"] == "TASK_STARTED"]
    finishes = [event for event in events if event["event"] == "TASK_FINISHED"]
    steps = [event for event in events if event["event"] == "STEP_OBSERVED"]
    if len(starts) != 1 or len(finishes) > 1 or (finishes and not starts):
        return {"task_id": task_id, "status": "UNKNOWN",
                "error": "missing or ambiguous task lifecycle records",
                "event_count": len(events), "automatic_resume": False, "write_performed": False}
    if not starts:
        return {"task_id": task_id, "status": "UNKNOWN",
                "error": "task_id was not found in the ledger",
                "event_count": 0, "automatic_resume": False, "write_performed": False}
    if events[0].get("event") != "TASK_STARTED":
        return {"task_id": task_id, "status": "UNKNOWN",
                "error": "task event precedes TASK_STARTED",
                "event_count": len(events), "automatic_resume": False, "write_performed": False}
    if finishes and events[-1].get("event") != "TASK_FINISHED":
        return {"task_id": task_id, "status": "UNKNOWN",
                "error": "task events appear after TASK_FINISHED",
                "event_count": len(events), "automatic_resume": False, "write_performed": False}
    if finishes:
        final_status = finishes[0].get("status")
        if final_status not in {"COMPLETED", "STOPPED"}:
            return {"task_id": task_id, "status": "UNKNOWN",
                    "error": "unrecognized terminal status in ledger",
                    "event_count": len(events), "automatic_resume": False, "write_performed": False}
        if final_status == "COMPLETED":
            criteria = [
                event for event in events
                if event["event"] == "GOAL_CRITERION_OBSERVED"
            ]
            if any(event.get("status") != "SUCCEEDED" for event in steps):
                return {"task_id": task_id, "status": "UNKNOWN",
                        "error": "completed task has failed or unrecognized step observations",
                        "event_count": len(events), "automatic_resume": False, "write_performed": False}
            if any(event.get("status") != "PASSED" for event in criteria):
                return {"task_id": task_id, "status": "UNKNOWN",
                        "error": "completed task has failed or unrecognized goal criteria",
                        "event_count": len(events), "automatic_resume": False, "write_performed": False}

            start_event = starts[0]
            if "success_criteria_ids" not in start_event:
                if criteria:
                    return {
                        "task_id": task_id,
                        "status": "UNKNOWN",
                        "error": "goal criterion observations exist without a start contract",
                        "event_count": len(events),
                        "automatic_resume": False,
                        "write_performed": False,
                    }
            else:
                declared_ids = start_event.get("success_criteria_ids")
                valid_contract = (
                    isinstance(declared_ids, list)
                    and all(
                        isinstance(item, str) and item.strip()
                        for item in declared_ids
                    )
                    and len(declared_ids) == len(set(declared_ids))
                )
                observed_ids = [
                    event.get("criterion_id") for event in criteria
                ]
                if not valid_contract or observed_ids != declared_ids:
                    return {
                        "task_id": task_id,
                        "status": "UNKNOWN",
                        "error": "goal criterion observations do not exactly match the start contract",
                        "event_count": len(events),
                        "automatic_resume": False,
                        "write_performed": False,
                    }
            declared_step_ids = start_event.get("step_ids")
            observed_step_ids = [event.get("step_id") for event in steps]
            valid_step_contract = (
                isinstance(declared_step_ids, list)
                and all(
                    isinstance(item, str) and item.strip()
                    for item in declared_step_ids
                )
                and len(declared_step_ids) == len(set(declared_step_ids))
            )
            if not valid_step_contract or observed_step_ids != declared_step_ids:
                return {
                    "task_id": task_id,
                    "status": "UNKNOWN",
                    "error": "step observations do not exactly match the start contract",
                    "event_count": len(events),
                    "automatic_resume": False,
                    "write_performed": False,
                }

        status = final_status
        next_state = "NONE_TERMINAL_TASK"
    else:
        status = "INCOMPLETE"
        next_state = "UNKNOWN"
    return {
        "task_id": task_id,
        "status": status,
        "goal": starts[0].get("goal"),
        "event_count": len(events),
        "observed_steps": [
            {"step_id": event.get("step_id"), "tool": event.get("tool"),
             "status": event.get("status"), "timestamp": event.get("timestamp")}
            for event in steps
        ],
        "last_event": events[-1].get("event") if events else None,
        "next_step_state": next_state,
        "automatic_resume": False,
        "write_performed": False,
        "recovery_guidance": (
            "Task has a terminal ledger record; inspect its result before planning any new task."
            if finishes else
            "Execution may have stopped between an action and its ledger observation. Inspect actual workspace and backup state before creating a new task; never replay the old task automatically."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run or inspect a bounded Ario workspace task.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--task", help="Path to a declarative task JSON file")
    mode.add_argument("--inspect-task-id", help="Read-only recovery inspection for a task_id in the ledger")
    mode.add_argument("--inspect-lock", action="store_true", help="Read-only inspection of the execution lock beside the ledger")
    parser.add_argument("--workspace", help="Existing workspace root (required with --task)")
    parser.add_argument("--ledger", required=True, help="Append-only JSONL audit ledger path")
    args = parser.parse_args(argv)
    try:
        if args.inspect_lock:
            result = inspect_execution_lock(args.ledger)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0 if result["status"] in {"NO_LOCK", "LOCK_PRESENT"} else 2
        if args.inspect_task_id is not None:
            result = inspect_task_history(args.inspect_task_id, args.ledger)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0 if result["status"] in {"COMPLETED", "STOPPED"} else 2
        if not args.workspace:
            parser.error("--workspace is required with --task")
        payload = json.loads(Path(args.task).read_text(encoding="utf-8-sig"))
        result = run_task(payload, args.workspace, args.ledger)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "COMPLETED" else 2
    except (OSError, json.JSONDecodeError, AgentRequestError) as exc:
        print(json.dumps({"status": "UNKNOWN", "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
