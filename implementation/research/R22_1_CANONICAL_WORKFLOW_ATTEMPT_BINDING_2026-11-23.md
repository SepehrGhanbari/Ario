# R22.1 — Canonical Workflow Identity and Exact Attempt Binding

**Status:** RESEARCH_ONLY / DRAFT / HOLD
**Parent:** PR #333 (R22, unchanged)
**Child:** PR #335
**Branch:** `research/r22-1-canonical-workflow-attempt-binding-20261123`
**Code/test verification head:** `501733937f26d68e96c4f4708ab259c3cdd337dc`

## Scope

This bounded follow-up addresses only the two independent findings from the exact-head adversarial review of R22:

1. A successful `m0-regression` check from a different workflow could be mistaken for the canonical Implementation Regression result.
2. The check was correlated to a workflow run ID but not to the job belonging to that run's exact latest `run_attempt`.

No signer, key, trust root, production gate, required-check setting, merge authority, or write-capable runtime behavior was added.

## RED evidence — unchanged R22

Test-only commit: `9334c1baa664712d261210ad0966a050ed412c85`.

[Implementation Regression RED run 45067690679](https://github.com/SepehrGhanbari/Ario/actions/runs/45067690679) reproduced all three new negative controls on all three environments:

| Environment | Targeted failures | Other passed | Skipped |
|---|---:|---:|---:|
| Linux / Python 3.13 | 3 | 1,968 | 7 |
| Linux / Python 3.14 | 3 | 1,968 | 7 |
| Windows / Python 3.13 | 3 | 1,948 | 27 |

Each run also reported 273 passing subtests. The three failures were: different workflow with a same-named green job; canonical workflow ID with a wrong path; and a check still pointing to an attempt-1 job while attempt 2 owned a different job ID.

## Implementation

`implementation/ario_repo_self_audit.py` now pins:

- Workflow ID: `379498305`
- Workflow path: `.github/workflows/implementation-regression.yml`
- Canonical job: `m0-regression`
- GitHub Actions app ID: `15368`

The observer retains latest-run ordering by `(run_number, run_attempt)` per workflow. A candidate is eligible only when both the workflow ID and path match the canonical workflow. The latest run is selected before the path check, so a newer run under the same workflow ID cannot leave an older green eligible if its path no longer matches.

For one unique candidate, the observer now reads the attempt-specific endpoint:

`GET /repos/SepehrGhanbari/Ario/actions/runs/{run_id}/attempts/{run_attempt}/jobs?per_page=100`

The read-only URL allowlist permits only this exact endpoint shape. The response must be complete (at most 100 jobs, with `total_count == len(jobs)`) and contain unique positive job IDs. Exactly one `m0-regression` job must bind to the selected check by job/check ID, run ID, run attempt, head SHA, status, and conclusion. A missing, ambiguous, incomplete, or mismatched job cannot produce `REPORTED_SUCCESS_BY_LINKED_PR_RUN`.

The diagnostic now exposes `canonical_workflow_observation` and `attempt_binding_observation`; neither is an authority signal. The existing `UNKNOWN`, `merge_authorized=false`, and non-attestation boundaries remain.

## Regression coverage

Added independent controls for:

- wrong workflow ID even with the canonical path;
- correct workflow ID with a noncanonical path;
- different workflow plus same-named successful job;
- prior-attempt check ID versus the latest attempt's job;
- exact attempt-specific jobs URL;
- mismatched job ID, run ID, attempt, head SHA, name, status, or conclusion;
- incomplete jobs collection, duplicate canonical jobs, and missing workflow path.

The Guard V2 live-link test fixture was updated to use the actual canonical workflow identity and an attempt-bound job. This was fixture compatibility work only; Guard V2's authority model was not changed.

## GREEN evidence — source and tests

Code/test head: `501733937f26d68e96c4f4708ab259c3cdd337dc`.

[Implementation Regression GREEN run 45068021771](https://github.com/SepehrGhanbari/Ario/actions/runs/45068021771):

| Environment | Passed | Skipped |
|---|---:|---:|
| Linux / Python 3.13 | 1,983 | 7 |
| Linux / Python 3.14 | 1,983 | 7 |
| Windows / Python 3.13 | 1,963 | 27 |

Each environment reported 273 passing subtests and 2 warnings. The separate Ario Repo Self Audit Research advisory run `45068021805` also succeeded.

## Live GitHub API binding check

On the exact code/test head, the actual run `45068021771` was independently read from GitHub's public API:

- Workflow ID `379498305`, path `.github/workflows/implementation-regression.yml`;
- event `pull_request`, run attempt `1`, conclusion `success`;
- linked PR #335 and exact head `501733937f26d68e96c4f4708ab259c3cdd337dc`;
- attempt-specific jobs response: 3 jobs;
- canonical `m0-regression` job ID `137348454243`, run ID `45068021771`, attempt `1`, matching head SHA, completed/success;
- the corresponding Check Run ID was also `137348454243`, app ID `15368`, completed/success, with a details URL ending in `/job/137348454243`.

Thus the exact-attempt binding was checked against an actual GitHub run/job/check response, not only a synthetic fixture.

## Limitations retained

- GitHub API reads are not an atomic or permanent snapshot; two PR reads do not establish freshness after the final sample.
- GitHub Actions metadata is not independent attestation of test execution or test correctness.
- The repository owner may control source, tests, workflow definitions, and the read process.
- The new endpoint and fields bind a check to an observed attempt; they do not prove independent custody or resist a maliciously controlled GitHub source.
- The report validator and self-audit remain diagnostics, not an authorization path.

## Governance and disposition

`RESEARCH_ONLY / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE`.

PR #335 remains Draft/HOLD and targets the R22 branch in PR #333. PR #333 remains Draft/HOLD. `main` was not targeted or changed. No merge, force-push, ruleset change, required-check change, key use, signature, trust activation, Genesis activation, memory admission, or production action occurred.

R22's earlier log entry is preserved as history: `22a18b9…` is the earlier implementation-source head; `638507c…` is the final R22 PR head after its report/log commit. This R22.1 entry records the subsequent child-PR work without rewriting that history.