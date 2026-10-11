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

## ARIO-AGENT-UTF8-20261011-01 — 2026-10-11

Trigger: first actual scheduled heartbeat of ario-bounded-engineering-continuation, delivered at 2026-10-11T17:00:04.849Z (20:30:04.849 Asia/Tehran). This is scheduled engineering execution, separately authorized by Ava Work for one task. The prior ARIO-WF-NULL-20261011-01 task was manually dispatched and completed in c83e0c3afff119bd0704cb0dcd8d09419dd1e989.

Policy commit: bfef90bd9db5589f964ebf0256ab949a80f37a29. Starting checkpoint: main at c83e0c3afff119bd0704cb0dcd8d09419dd1e989, no tracked unstaged or staged changes; 68 existing untracked paths and SHA256 hashes recorded. AGENTS.md and all three workflow files were separately fingerprinted for preservation. The authorized backup and scratch directories were unused.

Exact repository scope:

- C:\Users\xx4773\Ario\implementation\ario_agent.py
- C:\Users\xx4773\Ario\implementation\tests\test_agent_runtime.py
- C:\Users\xx4773\Ario\implementation\ARIO_BOUNDED_AGENT_RUNTIME_V1.md
- C:\Users\xx4773\Ario\ENGINEERING_LOG.md (append only)

Defect and pre-fix evidence: the task contract requires UTF-8 input and main reads the task with utf-8-sig, but its existing invalid-request exception tuple omitted UnicodeDecodeError. One real CLI reproduction used a scratch input containing byte 0xff and no valid actions. Actual CLI exit code was 1, stdout empty, stderr a traceback ending "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte". No ledger directory/file or lock was created. The reproduction harness exited 0. Raw input/output and evidence.json are retained under scratch\pre-fix\.

Changes: add only UnicodeDecodeError to main's existing exception boundary; retain JSON UNKNOWN on stderr, exit 2, and empty stdout. Add real CLI invalid-UTF-8 and malformed-JSON regressions, plus valid UTF-8/BOM controls. Narrowly document the input-error response. No schema fields, tools, dependencies, trust authorities, security mechanisms, core invariants, or foundational decisions were added or changed.

All four originals were backed up before editing and verified byte-for-byte and by SHA256. Retained backup root: C:\Users\xx4773\AppData\Local\Ario\engineering-backups\agent-cli-utf8-20261011-01\backups\.

- ario_agent.py — eef49b10b36177046e461b8b7deacd4572b64d15a8c6bb110dccc24905eb2f5c
- test_agent_runtime.py — efe80707308a4de5f6bdd23d53d115a72c72896bf6dded13737dde57e168d819
- ARIO_BOUNDED_AGENT_RUNTIME_V1.md — b1254d59a6a0430586c198a0fbe2f863a8dadc60be636e3d03ca5b16b82b5967
- ENGINEERING_LOG.md — 67e7afe83cfafe4295a74a9096827a7c3751c6f0f26c75e8c13b21e4cb8e23f7 (5498 original bytes)

A small manifest.json records the four backup paths/hashes. Implementation newline styles are preserved, and this log entry is appended after the original byte prefix. Scratch fixtures/helpers/output are confined to C:\Users\xx4773\AppData\Local\Ario\engineering-backups\agent-cli-utf8-20261011-01\scratch\, separate from retained backups.

Actual validation and recovery:

- Used C:\Users\xx4773\AppData\Local\Ario\venvs\ario-tests-py313\Scripts\python.exe with -B and process-local PYTHONDONTWRITEBYTECODE=1. TMP/TEMP were set to the authorized scratch directory and inherited by CLI subprocesses; tempfile confinement was confirmed.
- Ran the authorized module once from implementation: python -B -m pytest -p no:cacheprovider -q tests/test_agent_runtime.py. Exit 1: 47 passed, 15 subtests passed, 2 failed subcases and 2 warnings in 2.28s. The invalid-UTF-8 and malformed-JSON real-CLI cases passed. Both new valid-input BOM controls failed in the test harness because Windows child stdout emitted the non-ASCII goal using its default code page while the harness requested UTF-8 decoding.
- Corrected only the two new test subprocess commands to pin child UTF-8 mode with -X utf8, preserving bytecode suppression. Production behavior was not broadened. Reran only test_cli_rejects_invalid_task_input_before_execution and test_cli_accepts_valid_utf8_task_input_with_or_without_bom: exit 0; 2 passed, 4 subtests passed in 1.19s, with no warnings reported.
- Those subprocess assertions establish actual post-fix CLI exit 2, parseable stderr JSON containing status UNKNOWN and a nonempty error, empty stdout, unchanged target bytes, and absent ledger directory/file/lock for invalid UTF-8 and malformed JSON. Valid UTF-8 with and without BOM returned exit 0 and COMPLETED; read-only action ledgers were confined to disposable scratch fixtures.
- git diff --check exited 0 and the three implementation-file diff was reviewed. Full staged scope/diff checks, commit, final log-prefix and artifact verification follow this entry; their actual results are reported in the final task response.

Limitations: the complete agent module was not rerun after the isolated test-harness correction, and no full suite ran. Earlier 178 tests / 18 subtests and the prior workflow-module result remain historical evidence. Post-change evidence consists of the single module run and the focused passing CLI rerun. Default Windows stream encoding remains unchanged; the tests explicitly pin UTF-8 for captured non-ASCII output. Ignored artifacts were not exhaustively fingerprinted. Platform approval gates were respected; no permission/configuration, remote, scheduler, governance, or workflow changes were authorized.

Planned local commit message: fix: report invalid UTF-8 task input as unknown
Task commit reference: the commit containing this task entry, discoverable through git log --format=%H -- ENGINEERING_LOG.md. Report the actual full hash in the task final result; do not insert a self-referential hash here.