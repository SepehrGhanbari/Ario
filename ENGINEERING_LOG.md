# Ario Engineering Log

## ARIO-WF-NULL-20261011-01 — 2026-10-11

This is the manually dispatched first bounded engineering task under the owner-approved standing policy, authorized by Ava Work. It is not an unattended scheduled run.

Policy and starting checkpoint: main at bfef90bd9db5589f964ebf0256ab949a80f37a29, "docs: establish standing authority for bounded engineering". AGENTS.md SHA256: 21081fcea4dc091139f24c01a400c925c1c41453e5f706736f9b3912fc0decb1. Preflight confirmed no tracked unstaged or staged changes and recorded the path list and SHA256 hashes of 68 existing untracked files. The authorized backup/scratch directories were unused; ENGINEERING_LOG.md did not exist.

Exact repository scope:
- C:\Users\xx4773\Ario\implementation\ario_workflow.py
- C:\Users\xx4773\Ario\implementation\tests\test_workflow_runtime.py
- C:\Users\xx4773\Ario\implementation\ARIO_BOUNDED_WORKFLOW_RUNTIME_V1.md
- C:\Users\xx4773\Ario\ENGINEERING_LOG.md

Defect and reproduction: parse_workflow used stage.get("when") and validated only non-null values. A parser-only pre-fix reproduction with an explicitly present "when": null returned a normalized stage without when; exit code 0. It called only parse_workflow and executed no actions. The workflow contract already defines a when object with stage_id and status.

Changes: validate when whenever its key is present, reusing the existing object-shape error. Add explicit-null parser coverage and first/middle/last-stage regressions proving rejection before run_task, event append, lock opening, or ledger-directory creation. Clarify omission versus explicit null in the existing workflow contract. Valid conditional and omitted-condition behavior is covered by the existing workflow tests. No allowed tools, trust authorities, core invariants, or other security boundaries were changed; no foundational decision was needed.

Verified retained backups, created before editing and compared byte-for-byte and by SHA256:
- C:\Users\xx4773\AppData\Local\Ario\engineering-backups\workflow-null-condition-20261011-01\backups\ario_workflow.py — 8d5070671944ff3671a1f788f2cbbb9944f3761ee0e0d9e39d06feebbd1528de
- C:\Users\xx4773\AppData\Local\Ario\engineering-backups\workflow-null-condition-20261011-01\backups\test_workflow_runtime.py — d47fdfe4dd17a749e080141cc0d6682637136ce88e472e61d96ada2cbd659637
- C:\Users\xx4773\AppData\Local\Ario\engineering-backups\workflow-null-condition-20261011-01\backups\ARIO_BOUNDED_WORKFLOW_RUNTIME_V1.md — e9928f5d573fecf93739d7be81fc53bcca70ff5f2a5f5c8be89c6c379e98ee23

There was no prior log to back up. Original implementation newline styles were preserved. Disposable fixtures, CLI input/output, and the task-only edit helper are confined to C:\Users\xx4773\AppData\Local\Ario\engineering-backups\workflow-null-condition-20261011-01\scratch\. Retained backups are separate.

Actual validation:
- Python: C:\Users\xx4773\AppData\Local\Ario\venvs\ario-tests-py313\Scripts\python.exe. Every Python process used -B and process-local PYTHONDONTWRITEBYTECODE=1, with TMP and TEMP set to the authorized scratch directory and inherited by CLI subprocesses. tempfile.gettempdir() confinement was confirmed.
- From implementation: python -B -m pytest -p no:cacheprovider -q tests/test_workflow_runtime.py — exit code 0; 13 passed, 3 subtests passed in 0.80s.
- Actual ario_workflow.py CLI, null at first and later stage: each returned exit code 2 and UNKNOWN with the existing stage-indexed object-shape error. Scratch target bytes remained unchanged despite valid declared replace_text actions; ledger directories, ledger files, task/workflow locks, and action backups were absent. CLI validation harness exit code 0.
- git diff --check — exit code 0; complete implementation diff reviewed and confined to the three approved implementation paths. This log is the fourth authorized repository path. Staging, staged checks, commit, and final preservation checks follow this entry; their actual results are reported in the task final response.

Execution failures and recovery: one oversized shell invocation was rejected before process launch with Windows os error 206 (command line too long); no actions ran. A shorter command reading originals directly from disk with SHA256 preconditions successfully created and verified backups and ran the parser-only reproduction. A later functions.exec code string had a SyntaxError caused by embedded Markdown backticks, also before execution. A small task-only helper under scratch then applied the exact edits successfully. Platform approval gates were respected throughout; no permissions or Git configuration were changed.

Limitations: only the focused workflow module and two invalid-input CLI cases were validated after this change. The earlier 178 passing tests / 18 passing subtests are historical evidence and were not rerun. These results do not establish whole-system correctness or philosophical claims. Preservation hashing covers the existing Git-reported untracked path list; ignored artifacts were not exhaustively fingerprinted. No existing historical records, backups, runtime logs, caches, or unrelated files were intentionally modified.

Planned local commit message: fix: reject explicit null workflow conditions
Task commit reference: the commit containing this task entry, discoverable with git log --format=%H -- ENGINEERING_LOG.md. The actual full commit hash is reported in the final task result, avoiding a self-referential hash in this entry.