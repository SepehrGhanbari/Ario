# Resource and mutation test results

Production source under test was `da41e6818c4bdefadb19f838a962e8fe607aa1da`. Five focused regressions were added in [test_ledger_streaming_budget_evidence.py](../../tests/test_ledger_streaming_budget_evidence.py). Existing tests already cover duplicate Task and Workflow IDs at first, middle and final records, including an unterminated final duplicate at the real entry points. Those tests also check that no action or ledger append occurs and that temporary locks are removed.

## Regression evidence

Windows x64, CPython 3.13.17, pytest 9.1.1 and cryptography 46.0.4. From `implementation/`, using the repository's Windows CI pytest plugin and the pinned dependencies:

```text
python -B -m pytest -p no:cacheprovider -p tests.test_m0_reproducibility_demo -q -rs tests/test_ledger_streaming_scan.py tests/test_ledger_streaming_v0_followup.py tests/test_ledger_budget_profile.py tests/test_ledger_streaming_budget_evidence.py
python -B -m pytest -p no:cacheprovider -p tests.test_m0_reproducibility_demo -q -rs tests
```

| Run | Passed | Failed | Skipped | Subtests passed |
|---|---:|---:|---:|---:|
| Local Windows focused | 28 | 0 | 1 | 19 |
| Local Windows full, including five new tests | 1,528 | 0 | 3 | 213 |
| Prior hosted Linux on the source pin | 1,524 | 0 | 2 | 213 |
| Prior hosted Windows on the source pin | 1,524 | 0 | 2 | 213 |

Local Windows could not create a symlink. The other two full-suite skips were PR-CI-only HTTP diagnostics. The two hosted jobs each reported two warnings. Their logs and conclusions were verified for [run 44748652470](https://github.com/SepehrGhanbari/Ario/actions/runs/44748652470). The PR evidence comment records the hosted results for the commit adding these five tests.

| Focus | Observation |
|---|---|
| Completion and count boundaries | Standalone success with eight actions and eight criteria yielded 18. Failed goal verification inside a Workflow yielded 19 records matching its Task ID. The existing failure-diagnostics test exercised 18 and STOPPED. |
| History ceiling | A synthetic STOPPED history with 128 matches was inspectable. After a 129th matching record the result was UNKNOWN with the count-limit error. |
| Text boundary | A four-byte UTF-8 payload followed by CRLF was accepted exactly at the translated character limit and rejected one character over a scaled limit. |
| Append and interrupted JSON | A writer appended an incomplete terminal JSON object after the reader consumed record one. The in-progress read returned UNKNOWN and left those bytes untouched. After the writer completed the object a fresh read returned STOPPED. An existing test covers an intact, unterminated final object in an unfinished lifecycle and returns INCOMPLETE. |
| Profiler during an append | A deterministic append between its text and binary passes produced UNKNOWN with `SOURCE_CHANGED_DURING_SCAN`. The test does not establish snapshot isolation for either reader. |
| Strict inspection | The historical comparison had a write-denying audit hook and matching hashes. Synthetic entry-point tests also checked source bytes, workspace evidence, lock cleanup, and no automatic resume. |

## Bounded allocation measurements

Windows CPython 3.13.17. Each fresh synthetic ledger had a start, N matching `STEP_OBSERVED` objects and a STOPPED finish. The reader decoded valid JSON records with one large string field per step. Fixtures were built outside the traced interval. After a warm-up and garbage collection, the driver started `tracemalloc`, called `inspect_task_history`, and sampled current and peak Python allocations with the returned history still live. Each row is a single observation. The larger record contained 1,048,576 supplementary Unicode characters, encoded as real UTF-8 with `ensure_ascii=False`.

| N | Field | Payload characters per step | Total file bytes | Live traced bytes | Peak traced bytes |
|---:|---|---:|---:|---:|---:|
| 8 | observation, ASCII | 16,384 | 131,858 | 8,511 | 115,635 |
| 32 | observation, ASCII | 16,384 | 527,114 | 20,567 | 127,800 |
| 8 | tool, ASCII | 16,384 | 131,802 | 140,103 | 200,044 |
| 32 | tool, ASCII | 16,384 | 526,890 | 545,564 | 608,982 |
| 1 | observation, four-byte UTF-8 | 262,144 | 1,048,767 | 4,056 | 3,162,327 |
| 1 | observation, four-byte UTF-8 | 1,048,576 | 4,194,495 | 3,948 | 12,599,436 |

At 32 steps the returned history retained twenty-six times as many traced bytes with the large projected tool value as with the large observation. Both variants paid for decoding the current object. The synthetic `tool` strings exercise what the historical reader accepts and retains. They do not model the small allowlisted names written by the current Agent. Process RSS, production concurrency, a near-16-Mi-character memory benchmark and an exhaustive resource bound were `NOT_EXECUTED`.

## Mutation sensitivity

Three isolated, in-memory changes were applied one at a time to the pinned function bodies. Each test passed on the unmodified implementation and became non-green under the indicated mutation. Existing function imports in the selected test were rebound to the same mutated function. The candidate files were never mutated.

| Changed behavior | Test | Observed kill |
|---|---|---|
| Reject a line at equality instead of accepting it | `test_four_byte_text_and_crlf_at_boundary` | Unexpected line-limit exception on the valid equality case |
| Reject the 128th match one event early | `test_exact_matching_event_ceiling` | The asserted valid 128-event result lost its event count |
| Omit the goal from the retained projection | `test_completed_history_projects_only_required_fields` | Returned goal failed equality |

**3 killed, 0 survived, 0 unexecuted among these three selections.** The scope is these contracts. No corpus-wide mutation score is asserted.

## Separate subprocess capture

`ario_agent._run` calls `subprocess.run(capture_output=True, text=True, ...)` before slicing stdout and stderr. A bounded child emitted 7,000 and 4,000 ASCII characters respectively, exited 0, and the wrapper returned 6,000 and 3,000. The source establishes that truncation happens after capture. The sample verifies the tails. Sustained output, process RSS and exhaustion testing were `NOT_EXECUTED`. An upstream subprocess-output memory budget is a separate open question.

## SHA-256 of tested files

| Source under implementation/ | SHA-256 |
|---|---|
| ario_agent.py | `bfed1255c0de2d139539d7283693372ea1733f48accf71fc4ec5378abdee732d` |
| ario_workflow.py | `97aa8cc59457c6dc11101e692336755a3fa7052fec11909da38a03dab358c533` |
| bounded_json.py | `bd2e88f1f1491260d84db87c2de7b3b04ffca97837c718d6c9471a25054292aa` |
| ledger_streaming.py | `ba011d2205fff13b5b594aad69ee0dc85d5725d62f6aee42b46e8abb7177141a` |
| ledger_budget_profile.py | `04197bfbd7000cf0d4fe9c372fef18110204626e1db19c0b1e5531a04f691f92` |
| tests/test_ledger_streaming_budget_evidence.py | `4f61a13e2044a783cce15771a46c0d3b7e3db35728bd74f0c6df4546ae6d6716` |
