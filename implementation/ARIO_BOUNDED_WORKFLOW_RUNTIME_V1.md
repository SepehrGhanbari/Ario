# Ario Bounded Conditional Workflow Runtime V1

## Purpose

`ario_workflow.py` composes existing bounded tasks into a short, declarative workflow. It does not ask an LLM to invent new actions at runtime. Every stage and every branch is supplied in the input before execution.

## Run on Windows

Create a UTF-8 workflow JSON file, for example `$env:TEMP\ario-workflow.json`:

```json
{
  "workflow_id": "WORKFLOW-INSPECT-001",
  "goal": "Inspect a file and run a declared verification only if the first stage completes",
  "stages": [
    {
      "stage_id": "inspect",
      "task": {
        "task_id": "TASK-INSPECT-001",
        "goal": "Read the result file",
        "actions": [
          {"step_id": "read-result", "tool": "read_text", "path": "result.txt"}
        ]
      }
    },
    {
      "stage_id": "verify",
      "when": {"stage_id": "inspect", "status": "COMPLETED"},
      "task": {
        "task_id": "TASK-VERIFY-001",
        "goal": "Check the exact expected content",
        "actions": [
          {"step_id": "verify-result", "tool": "verify_text", "path": "result.txt", "expected_text": "READY"}
        ]
      }
    },
    {
      "stage_id": "diagnose",
      "when": {"stage_id": "inspect", "status": "STOPPED"},
      "task": {
        "task_id": "TASK-DIAGNOSE-001",
        "goal": "Collect read-only evidence after inspection failed",
        "actions": [
          {"step_id": "inspect-root", "tool": "inspect_directory", "path": "."}
        ]
      }
    }
  ]
}
```

From the repository root:

```powershell
python .\implementation\ario_workflow.py --workflow "$env:TEMP\ario-workflow.json" --workspace "$HOME\Ario" --ledger "$HOME\Ario\runtime\agent-events.jsonl"
```

Exit code `0` means the workflow completed; `1` means at least one executed stage stopped; `2` means the workflow request could not be safely validated or started.

## Branching and safety rules

- Maximum eight predeclared stages; each stage uses the existing strict bounded-task schema and allowlisted tools.
- A `when` condition compares one earlier stage's final status exactly against `COMPLETED` or `STOPPED`. It cannot refer to future stages or evaluate expressions/code.
- Omitting `when` declares an unconditional stage, subject to the continuation rules below. If present, `when` must be an object containing exactly `stage_id` and `status`; `null` is invalid and rejected before workflow execution or ledger/lock creation.
- A stage whose condition expects `STOPPED` is restricted to read-only actions at validation time.
- Once any stage stops, the workflow's final status remains `STOPPED`. Read-only diagnostic stages may still run when explicitly selected, but any later stage containing a write/restore action is skipped.
- A condition that does not match yields `SKIPPED`; this is recorded and is not itself a failure.
- Each stage is still executed by `ario_agent.py`, retaining its task-ID duplicate guard, exclusive task lock, append-only lifecycle events, guarded writes, postconditions, and independent goal criteria.
- The workflow has its own exclusive lock and refuses a duplicate workflow ID in the ledger. Its lock is not a security boundary against a hostile local process.
- The workflow lock does not hold the task lock across the entire multi-stage sequence; another independently launched task using the same ledger may run between stages. Use one orchestrator per workspace/ledger when cross-stage isolation matters.
- A successful workflow means its executed stages returned `COMPLETED` and no stage stopped. It does not prove semantic properties that were not encoded as explicit criteria, nor does it make the local ledger tamper-proof.
- There is no arbitrary shell, network, dynamic planning, automatic retry, automatic rollback, or automatic repair loop.

This is a bounded conditional orchestration layer: a small step toward goal-directed execution with explicit branching, not unrestricted autonomy.
