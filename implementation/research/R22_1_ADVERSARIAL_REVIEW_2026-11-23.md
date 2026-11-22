# R22.1 — Independent Adversarial Review: Rerun Freshness, Duplicate Jobs, and Incomplete Evidence

**Disposition:** bounded correction GREEN on Linux and Windows; PR remains DRAFT / HOLD / RESEARCH_ONLY.
**Target under review:** PR #335, exact head `205ede3307608aadf36937b5af1b0a6c9cdc58f7`.
**Independent review/fix branch:** `research/r22-1-independent-adversarial-review-20261123`.
**Review/fix PR:** #337, stacked on #335; code/test head `2b0604988600007fcbc21c5aba65c038cd63b3e9`.

## 1. Finding: rerun TOCTOU false-green reproduced

Test-only review head: `32074a39c6ca07cb681560831f9632c295623829`.

[Implementation Regression RED run 45068723310](https://github.com/SepehrGhanbari/Ario/actions/runs/45068723310) reproduced the same targeted failure on all three environments:

| Environment | Passed | Failed | Skipped |
|---|---:|---:|---:|
| Linux / Python 3.13 | 1,992 | 1 | 7 |
| Linux / Python 3.14 | 1,992 | 1 | 7 |
| Windows / Python 3.13 | 1,972 | 1 | 27 |

Each run also reported 273 passing subtests. The failing control was `test_rerun_started_after_initial_run_read_cannot_leave_attempt_one_green`.

Attack sequence:

1. Initial workflow-run collection reports canonical run 100, attempt 1, completed/success.
2. Initial Check Runs collection reports the matching successful job/check ID for attempt 1.
3. A rerun begins while the attempt-specific jobs request is in flight; current state changes to attempt 2, in-progress, with a different Job/Check ID.
4. GitHub still returns the completed Job collection for explicitly requested attempt 1.
5. PR #335 does not re-read Check Runs or workflow runs after the jobs response and returns `REPORTED_SUCCESS_BY_LINKED_PR_RUN`.

This is a reproduced time-of-check/time-of-use gap. The failure was not inferred from source inspection alone.

[Self Audit Research RED run 45068723289](https://github.com/SepehrGhanbari/Ario/actions/runs/45068723289) also failed only on the same race control: 1 failed / 194 passed. [TXT Restore Security 45068723326](https://github.com/SepehrGhanbari/Ario/actions/runs/45068723326) completed 10/10 success.

## 2. Test-quality gap corrected

The prior-attempt test in #335 did not isolate the `run_attempt` comparison: its check ID remained the default attempt-1 ID while the supplied attempt-2 job used a different ID. The test therefore failed on job/check ID mismatch before exercising the attempt field.

The corrected control sets the selected check ID and job ID equal, binds both to the same run ID and SHA, and makes only the job's `run_attempt` differ from the selected workflow attempt. It must return `NOT_CONFIRMED`.

## 3. Bounded correction on #337

`implementation/ario_repo_self_audit.py` now, only after a candidate would otherwise be confirmed green:

1. Re-reads the exact Check Runs collection after the attempt-specific jobs response.
2. Requires a complete bounded response (`total_count == len(check_runs) <= 100`).
3. Requires the re-read Check Runs object to equal the original sample; any drift returns `UNKNOWN` with `CHECKS_CHANGED_DURING_OBSERVATION`.
4. Re-reads the workflow-run collection **last**, immediately before the final PR identity read.
5. Requires a complete bounded response (`total_count == len(workflow_runs) <= 100`) and exact equality with the original sample; any drift returns `UNKNOWN` with `RUNS_CHANGED_DURING_OBSERVATION`.

Three independent race variants mutate only checks, only workflow runs, or both between the initial metadata reads and the attempt-job response. Each must now return `UNKNOWN` / `NOT_CONFIRMED`.

Additional controls verify: same-ID prior-attempt job rejection; absent required attempt-job fields; duplicate workflow/run-number sequence; more than 100 attempt jobs; duplicate job IDs; and the already-existing duplicate canonical job-name rejection. Incomplete or ambiguous evidence never produces a positive observation.

## 4. GREEN evidence on code/test head

Code/test head: `2b0604988600007fcbc21c5aba65c038cd63b3e9`.

[Implementation Regression 45069047655](https://github.com/SepehrGhanbari/Ario/actions/runs/45069047655): **3/3 jobs SUCCESS**.

| Environment | Passed | Skipped |
|---|---:|---:|
| Linux / Python 3.13 | 1,994 | 7 |
| Linux / Python 3.14 | 1,994 | 7 |
| Windows / Python 3.13 | 1,974 | 27 |

Each environment reported 273 passing subtests and 2 warnings. [Ario Repo Self Audit Research 45069047692](https://github.com/SepehrGhanbari/Ario/actions/runs/45069047692) succeeded. [Published TXT Restore Security 45069047656](https://github.com/SepehrGhanbari/Ario/actions/runs/45069047656) completed **10/10 jobs SUCCESS**.

## 5. Actual GitHub API cross-check

Final code/test PR run `45069047655` was independently read from GitHub's API:

- Workflow ID `379498305`, path `.github/workflows/implementation-regression.yml`;
- event `pull_request`, run attempt `1`, conclusion `success`;
- PR #337 association and exact head `2b0604988600007fcbc21c5aba65c038cd63b3e9`;
- attempt-specific jobs collection contains 3 jobs;
- canonical `m0-regression` job ID `137351648715`, run ID `45069047655`, attempt 1, exact head SHA, completed/success;
- Check Run ID is also `137351648715`, app ID `15368`, completed/success, with matching `/job/137351648715` details URL.

## 6. Residual limitations

- Re-reading checks and workflow runs after the job lookup narrows the race window; it does **not** make GitHub API reads atomic. A rerun or newer run can still start after the last workflow-run sample. The diagnostic must remain a sampled observation, not a freshness guarantee.
- Exact full-object equality is intentionally conservative. Unrelated check/run metadata changes can cause `UNKNOWN`; this is an availability trade-off to avoid accepting stale evidence.
- GitHub Actions metadata is not independent attestation of test execution or test correctness. The repository owner may control source, tests, workflow definitions, and read logic.
- This remains read-only diagnostic evidence. It does not establish independent custody, historical truth, memory admission, trust, signer authority, Genesis, or production readiness.

## 7. Governance and disposition

`RESEARCH_ONLY / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE`.

PR #337 is Draft/HOLD and targets the R22.1 branch in PR #335. PR #335 and parent PR #333 remain open Draft/HOLD. `main` was not targeted or changed. No merge, force-push, ruleset/required-check change, key use, signature, trust activation, Genesis activation, memory admission, or production action occurred.