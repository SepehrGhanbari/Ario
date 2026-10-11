# Ario Bounded Workspace Agent Runtime V1

## Purpose

`ario_agent.py` is a first executable, bounded workspace agent. It is deliberately not an unrestricted shell agent and does not claim general autonomy. A task declares a goal and a short sequence of allowlisted actions; the runtime records observations and stops on the first failed step.

## Run on Windows

Create a UTF-8 task file such as `$env:TEMP\ario-task.json`:

```json
{
  "task_id": "WORKSPACE-INSPECTION-001",
  "goal": "Inspect the Ario implementation and confirm the working tree state",
  "actions": [
    {"step_id": "s1", "tool": "git_status"},
    {"step_id": "s2", "tool": "inspect_directory", "path": "implementation"},
    {"step_id": "s3", "tool": "read_text", "path": "implementation/M0_JSON_RUNTIME_V1.md"}
  ]
}
```

From the repository root, run:

```powershell
python .\implementation\ario_agent.py --task "$env:TEMP\ario-task.json" --workspace "$HOME\Ario" --ledger "$HOME\Ario\runtime\agent-events.jsonl"
```

The ledger is append-only JSONL. Keep it in a trusted directory and protect it with normal filesystem permissions.

## Read-only execution-lock inspection

If task execution stops unexpectedly, inspect the lock record without changing it:

```powershell
python .\implementation\ario_agent.py --inspect-lock --ledger "$HOME\Ario\runtime\agent-events.jsonl"
```

The command reports `NO_LOCK`, `LOCK_PRESENT`, or `UNKNOWN` and never removes a lock. A valid record includes the process ID, task ID, start time, byte count, and SHA-256. A present lock is not proof of a stale process. Before manual removal, check whether the recorded process is still active; malformed records remain `UNKNOWN` and require human inspection.

## Guarded multi-step workflow

The runtime can combine a hash-preconditioned write, an exact postcondition, and a read-back in one task. The hash must be computed from the actual starting file at task creation time; do not guess or reuse a stale hash.

```json
{
  "task_id": "GUARDED-CHANGE-001",
  "goal": "Change one known text file and verify its declared result",
  "actions": [
    {
      "step_id": "s1-replace",
      "tool": "replace_text",
      "path": "notes.txt",
      "expected_sha256": "<64-character SHA-256 of the current file bytes>",
      "content": "EXPECTED RESULT"
    },
    {
      "step_id": "s2-postcondition",
      "tool": "verify_text",
      "path": "notes.txt",
      "expected_text": "EXPECTED RESULT"
    },
    {
      "step_id": "s3-readback",
      "tool": "read_text",
      "path": "notes.txt"
    }
  ]
}
```

The placeholder hash is illustrative, not executable. If the precondition fails, the write is refused. If the postcondition fails, the task stops before read-back or any later action. The runtime does not automatically undo a completed write just because a later independent verification fails; use `restore_backup` as a separate guarded action after reviewing the failure. This limitation is intentional and must remain visible in the audit trail.

## Allowlisted tools

- `inspect_directory`: list a directory (maximum 200 entries).
- `read_text`: read UTF-8 text under the workspace in line-aligned chunks capped at 20,000 bytes per action. An optional positive integer `start_line` reads a later chunk; results include `start_line`, `next_start_line`, `bytes`, and `truncated` so callers can continue without overlapping or skipping lines. A single line larger than the cap fails closed. This permits bounded inspection of larger source files without loading the whole file into memory.
- `file_fingerprint`: read-only SHA-256 and byte count for an existing workspace file; it does not expose file contents or modify the file.
- `inspect_backup`: read-only SHA-256 and byte count for an existing backup selected by a relative path under the external backup directory; it rejects traversal and symbolic-link paths.
- `git_status`: run fixed `git status --short --branch`.
- `compile_python`: compile one existing `.py` file.
- `run_tests`: run the fixed `python -B -m pytest -p no:cacheprovider -q tests` command from `implementation/`. `-B` and the disabled pytest cache provider prevent the runner from writing Python bytecode or pytest cache files; they do not sandbox side effects implemented by the test code itself.
- `replace_text`: replace an existing UTF-8 text file only when its current SHA-256 matches the task's expected hash. It writes a byte-for-byte backup outside the workspace (under the ledger directory's `backups/` folder), atomically replaces the file, and verifies the resulting hash. Original and replacement content are capped at 20,000 bytes.
- `restore_backup`: restore a backup selected by a relative path beneath the external `backups/` folder, only when the current target's SHA-256 matches the task's expected hash. Before restoration, it preserves the current target as a new backup and verifies the restored hash. A backup path cannot escape the backup folder.
- `verify_text`: compare an existing UTF-8 text file against an explicitly declared `expected_text` postcondition. A mismatch fails the step and stops the task, preventing later steps from running. This is exact text verification, not proof of broader semantic success.

There is no arbitrary shell, arbitrary command, network, delete-file, or privilege-escalation tool. The sole write capability is `replace_text`, which requires a precondition hash and an external backup. It must not be used for critical files without a separate review. Paths must be relative and remain within the resolved workspace. Each subprocess uses `shell=False` and a timeout.

## Control and recovery

- Read-only crash recovery inspection is available with `python .\\implementation\\ario_agent.py --inspect-task-id TASK-ID --ledger PATH`. It classifies a task with a terminal `TASK_FINISHED` event as `COMPLETED` or `STOPPED`; a started task without a terminal event is `INCOMPLETE`, with the next execution state explicitly `UNKNOWN`. Missing, malformed, or ambiguous lifecycle evidence returns `UNKNOWN`. It never resumes, retries, restores, or writes. Before starting a new task after an interruption, compare the ledger with actual workspace and backup evidence; an operation may have occurred before its observation was appended.

- The full task schema and allowlist are validated before execution. Task IDs must be unique within a ledger: the runtime rejects a duplicate ID before any action or append, preventing accidental replay under an already-used identity. If an existing ledger is malformed or cannot be read, task execution fails closed before writing.
- Task execution acquires an exclusive lock beside the ledger before checking task-ID uniqueness and holds it through the terminal ledger event. A second process using the same ledger fails closed while the lock exists. If a process crashes and leaves a stale lock, inspect the recorded PID/task ID and confirm no matching process is active before manually removing the lock; Ario never removes an existing lock automatically. This serializes cooperating runtime invocations that use the same ledger path, but is not a security boundary against a hostile local process.
- Each step produces an observation recorded to the JSONL ledger.
- A failed step stops the task; no automatic retry or corrective write is attempted.
- Recovery preflight can use `file_fingerprint` to obtain the target's current hash and `inspect_backup` to confirm the candidate backup's hash. A subsequent `restore_backup` task must explicitly supply the observed current hash; inspection never triggers a write or chooses a backup automatically.
- `recovery_preflight` combines target and selected-backup fingerprinting into one read-only, ledger-recorded step. It records both SHA-256 hashes, byte counts, and whether the bytes are identical. `DIFFERENT_CONTENT` is evidence of difference, not evidence that either version is correct. The tool never selects a backup, restores, retries, or writes; a separate task must explicitly request `restore_backup` with the observed current-target hash.
- `COMPLETED` means all declared steps returned success. It does **not** prove the natural-language goal was semantically achieved.
- The event ledger is an audit aid, not tamper-proof storage. A local administrator can modify it; cryptographic integrity, OS-level isolation, approvals for writes, and independent goal verification remain future work.
- Rollback is itself a guarded write, not magic undo: it requires a known backup-relative path and the exact current-file hash, and preserves the replaced current version before restoration.

## Goal contract and independent final verification

Tasks may declare an optional `success_criteria` list. When present, every criterion must contain exactly `criterion_id`, `path`, and `expected_text`. After all declared actions succeed, Ario re-reads each target file and checks the exact text independently of the action sequence. Each result is recorded as a `GOAL_CRITERION_OBSERVED` event. A failed or unreadable criterion changes the final task status to `STOPPED`; no automatic retry, rollback, or corrective write is attempted. Criterion paths are checked for workspace escape and symbolic links before any action runs.

Example task fragment:

```json
{
  "task_id": "GOAL-CHECK-001",
  "goal": "Ensure the declared result file contains the expected text",
  "actions": [
    {"step_id": "inspect", "tool": "read_text", "path": "result.txt"}
  ],
  "success_criteria": [
    {
      "criterion_id": "result-content",
      "path": "result.txt",
      "expected_text": "EXPECTED RESULT"
    }
  ]
}
```

Without `success_criteria`, legacy behavior remains unchanged and `COMPLETED` means only that every declared action returned success. With criteria, `COMPLETED` means all declared criteria passed exact file-content checks; this still does not establish unmodeled semantic properties or make the ledger tamper-proof. This is a deterministic goal contract, not an LLM planner and not unrestricted autonomy.

## Bounded failure diagnostics

A task may declare an optional `failure_diagnostics` list. If a normal action fails, the task remains `STOPPED`; Ario may then execute only the explicitly declared read-only diagnostic actions and records each result as a `FAILURE_DIAGNOSTIC_OBSERVED` event. Allowed diagnostic tools are `inspect_directory`, `read_text`, `file_fingerprint`, `inspect_backup`, `recovery_preflight`, `git_status`, `compile_python`, `run_tests`, and `verify_text`. Write and restore tools are rejected during preflight, before any task action or ledger append. Diagnostic failures are recorded but do not trigger retries or further corrective actions.

Example:

```json
{
  "task_id": "DIAGNOSE-FAILED-STEP-001",
  "goal": "Read a known file and gather evidence if the read fails",
  "actions": [
    {"step_id": "read-target", "tool": "read_text", "path": "result.txt"}
  ],
  "failure_diagnostics": [
    {"step_id": "inspect-parent", "tool": "inspect_directory", "path": "."},
    {"step_id": "fingerprint-target", "tool": "file_fingerprint", "path": "result.txt"}
  ]
}
```

This adds a bounded observe-and-decide branch, not an automatic repair loop: failure diagnostics can explain state but cannot modify it or change the failed task to `COMPLETED`.
