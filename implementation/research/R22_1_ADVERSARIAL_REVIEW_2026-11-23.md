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

## 8. Second independent pass against PR #337 — final-sample race RED, then bounded correction GREEN

### 8.1 RED: race after the previous final workflow sample

Test head `cdabf1f5ea08bdd5445a8c733bed2c7661aad9d7`; [Implementation Regression 45069759321](https://github.com/SepehrGhanbari/Ario/actions/runs/45069759321): **4 failed / 1,994 passed / 7 skipped / 273 subtests passed**. [Self Audit Research 45069759350](https://github.com/SepehrGhanbari/Ario/actions/runs/45069759350) reproduced the four failures.

The new attack starts a rerun during the second/final PR identity GET, after the previous code had already re-read Check Runs and workflow runs. The PR identity remains unchanged, so the old code returned `REPORTED_SUCCESS_BY_LINKED_PR_RUN` despite a new in-progress attempt. Three variants changed checks only, runs only, or both. This established that the previous ordering left an avoidable gap after the workflow sample.

### 8.2 RED: false UNKNOWN from raw-object equality

The same test head reordered Check Runs and workflow-run arrays and changed presentation-only fields (`output`, `updated_at`, `display_title`) while preserving the selected canonical check and run. The old whole-object comparison returned `NOT_CONFIRMED`. This was an unnecessary false UNKNOWN. It also treated a stale canonical check for an older run and a complete run for another PR/workflow as if they changed the selected evidence.

### 8.3 Bounded correction

Final code/test head: `7e35262f9e13bd3a35d3e10325d61df5baf00369`.

- Move the second PR identity read **before** the final metadata rechecks. A rerun during that PR read is now caught by the subsequent Check Runs and workflow-run samples.
- Make the Check Runs re-read compare a normalized projection of canonical checks bound to the selected latest run and selected check ID. Array order, presentation-only fields, unrelated checks, and stale canonical checks for older runs no longer cause false UNKNOWN. A new competing canonical check pointing to the selected run still changes the projection.
- Make the workflow-run re-read compare the normalized latest PR-linked run of the pinned canonical workflow. Every returned run is still validated for required fields, IDs, workflow/run-number uniqueness and PR associations; unrelated PRs/workflows and older runs do not create false drift. The latest run's ID, workflow, path, number, attempt, SHA, event, state, conclusion and PR associations remain bound.
- Keep bounded completeness checks on both final responses. Missing/incomplete collections, duplicate IDs, duplicate workflow/run-number sequences, malformed records and association mismatches fail closed as `UNKNOWN`.
- Make the workflow-run collection the **last network request**. The output now exposes `workflow_freshness: SAMPLED_NOT_ATOMIC` for a positive reported success.

### 8.4 Explicit residual boundary

A further control models a rerun that begins immediately **after** the final workflow-run GET has returned its old response. A sequential reader cannot observe a state change that occurs after its last read; the test therefore documents the residual rather than pretending to eliminate it. The result remains `status: UNKNOWN`, `merge_authorized: false`, `execution_attestation: NOT_ESTABLISHED`, and explicitly labels the positive GitHub metadata as `SAMPLED_NOT_ATOMIC`. No atomic snapshot or permanent freshness guarantee is claimed.

### 8.5 GREEN evidence on final head

[Implementation Regression 45070448595](https://github.com/SepehrGhanbari/Ario/actions/runs/45070448595): **3/3 jobs SUCCESS**.

| Environment | Passed | Skipped |
|---|---:|---:|
| Linux / Python 3.13 | 2,003 | 7 |
| Linux / Python 3.14 | 2,003 | 7 |
| Windows / Python 3.13 | 1,983 | 27 |

Each environment reported 273 passing subtests. [Ario Repo Self Audit Research 45070448681](https://github.com/SepehrGhanbari/Ario/actions/runs/45070448681) succeeded. [Published TXT Restore Security 45070448683](https://github.com/SepehrGhanbari/Ario/actions/runs/45070448683) completed **10/10 jobs SUCCESS**.

### 8.6 Final-head GitHub API cross-check

Final run `45070448595` was independently checked against GitHub API:

- canonical workflow ID `379498305`, path `.github/workflows/implementation-regression.yml`, run number `3640`, attempt `1`, event `pull_request`, PR #337 and exact head `7e35262f9e13bd3a35d3e10325d61df5baf00369`;
- attempt-specific jobs page contains 3 jobs;
- canonical `m0-regression` Job ID `137355997196`, run ID `45070448595`, attempt 1, exact head, completed/success;
- Check Run ID `137355997196`, app ID `15368`, same head, completed/success, with exact `/job/137355997196` details URL.

### 8.7 Governance

PR #337 remains open Draft/HOLD and is still stacked on #335. #335 and parent #333 remain open Draft/HOLD. No merge, main update, force-push, ruleset/required-check change, real key, signature, trust activation, Genesis, memory admission or production action occurred. Status remains `RESEARCH_ONLY / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE`.

## 9. Final residual-boundary control and final code/test head

### 9.1 PR revision after the second identity sample

A separate synthetic control changes the PR head immediately after the second PR identity GET has returned its old response, before the final Check Runs and workflow-run requests. As expected for a non-atomic sequential reader, the later requests remain pinned to the old SHA and cannot retroactively observe that PR revision. The control is intentionally **not** described as a successful freshness guarantee: `workflow_freshness` is `SAMPLED_NOT_ATOMIC`, overall `status` remains `UNKNOWN`, `merge_authorized` remains false, and `execution_attestation` remains `NOT_ESTABLISHED`. This complements the rerun-after-final-workflow-sample residual control in section 8.4.

### 9.2 Final code/test head and CI

Final code/test head: `67c480ed9becf4d57669fed6909401af1a23289c`.

[Implementation Regression 45070794094](https://github.com/SepehrGhanbari/Ario/actions/runs/45070794094): **3/3 jobs SUCCESS**.

| Environment | Passed | Skipped |
|---|---:|---:|
| Linux / Python 3.13 | 2,004 | 7 |
| Linux / Python 3.14 | 2,004 | 7 |
| Windows / Python 3.13 | 1,984 | 27 |

Each environment reported 273 passing subtests. [Ario Repo Self Audit Research 45070794130](https://github.com/SepehrGhanbari/Ario/actions/runs/45070794130) succeeded. [Published TXT Restore Security 45070794022](https://github.com/SepehrGhanbari/Ario/actions/runs/45070794022) completed **10/10 jobs SUCCESS**.

### 9.3 Final-head GitHub API cross-check

Run `45070794094` was independently checked against GitHub API: canonical workflow ID `379498305`, path `.github/workflows/implementation-regression.yml`, run number `3653`, attempt `1`, event `pull_request`, PR #337 and exact head `67c480ed9becf4d57669fed6909401af1a23289c`. Its attempt-specific jobs collection has 3 jobs. `m0-regression` Job ID `137357047100` matches Check Run ID `137357047100`, app ID `15368`, exact head/run/attempt, completed/success and exact job details URL.

### 9.4 Governance

PR #337 remains open Draft/HOLD and stacked on #335. #335 and parent #333 remain open Draft/HOLD. No merge, main update, force-push, ruleset/required-check change, key, signature, trust activation, Genesis, memory admission or production action occurred. `RESEARCH_ONLY / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE`.