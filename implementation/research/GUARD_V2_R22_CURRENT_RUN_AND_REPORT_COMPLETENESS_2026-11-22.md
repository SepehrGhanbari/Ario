# R22 — Guard V2 current-run selection and complete success report

**Date:** 2026-11-22  
**Scope:** two reproduced false-green defects in the #295 research branch  
**Disposition:** \`R22_FIXES_CI_PASS / RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE\`

## Exact source and branch boundary

- Starting #295 research HEAD: \`14f9da37673b04f7fce90b720a94c27144c15667\`.
- R22 branch: \`research/r22-guard-v2-current-run-and-report-completeness-20261122\`.
- Final R22 source head for this report: \`22a18b9cee00dbab2d86a8e5c4df62256fcfc30b\`.
- Draft PR: [#333](https://github.com/SepehrGhanbari/Ario/pull/333), stacked directly on the #295 research branch, not on main.
- At final verification, #295 research branch remained at \`14f9da3…\`; main was \`15ebc65ca97f26396c152811a94646f86cbbfffe\`. R22 did not update either ref. No merge, required-check publication, ruleset, credential, signer, Trust, Genesis or production change.

## Finding 1 — older green workflow run masked a newer same-head run

**Reproduction:** test-only commit \`1d3577a49217fb6a4bc522158cf786541a08a951\`. Hosted RED [run #45063527252, job #137334506693](https://github.com/SepehrGhanbari/Ario/actions/runs/45063527252/job/137334506693): three controls showed that a completed green run was reported as \`REPORTED_SUCCESS_BY_LINKED_PR_RUN\` while a newer same-workflow, same-head PR run was queued, in progress, or completed with failure. The baseline also accepted missing workflow identity/sequence metadata.

**Correction in \`implementation/ario_repo_self_audit.py\`:**

- Require positive integer \`workflow_id\`, \`run_number\`, and \`run_attempt\` for each returned workflow run.
- Require a nonempty, structurally valid \`pull_requests\` association list. Missing/empty lists, malformed links, and a partial or mismatched identity/head for the requested PR now fail closed as UNKNOWN.
- Reject duplicate \`(workflow_id, run_number)\` metadata.
- For the exact requested PR identity and head, rank linked runs within each workflow by \`(run_number, run_attempt)\`.
- A named \`m0-regression\` check qualifies only when its details URL maps to a job on that workflow's newest linked run. The newest workflow run and the named check must both be completed with success.
- A newer run from a different workflow does not suppress the target workflow's check; this positive control is retained.

The tests cover newer queued/in-progress/failed runs, a latest successful run, a different workflow, missing run metadata, missing/empty PR associations, and a mismatched target-PR link.

## Finding 2 — success validator supplied a missing graph reason

**Reproduction:** the new R20 manual-report regression test removes \`review_graph_reason\` from actual successful reader output and supplies reader exit 0. The old validator returned exit 0 because it used \`value.get("review_graph_reason", SUCCESS_GRAPH_REASON)\`.

**Correction in \`implementation/research/guard_v2_manual_report.py\`:**

- A successful reader exit now requires the field to be present and exactly equal to \`TWO_COMPLETE_GRAPH_SAMPLES_MATCH\`.
- The nonzero/incomplete HOLD path may still omit \`review_graph_reason\` when the reader failed before graph sampling. This preserves legitimate early-failure output rather than forcing a fabricated success-shaped field.

The R20 tests cover actual reader-shaped success with the field, success with the field removed (reject), and a legitimate \`MISSING_READ_ONLY_TOKEN\` HOLD without the field (accept on nonzero exit). The complete staged-workflow success fixture was updated to include the field explicitly.

## Preserved RED and intermediate corrections

- RED run [#45063527252](https://github.com/SepehrGhanbari/Ario/actions/runs/45063527252): **5 expected new failures / 1,959 passed / 7 skipped / 273 subtests passed**.
- First implementation attempt [#45063802822](https://github.com/SepehrGhanbari/Ario/actions/runs/45063802822) exposed 22 compatibility failures because existing live-link fixtures lacked the newly required GitHub \`workflow_id\`/\`run_number\`, and the staged workflow's complete-success fixture omitted the now-required graph reason. Those fixtures were updated; the source contract was not relaxed.
- The stricter association check then exposed one stale test expectation: a same-number/different-ID PR link is an identity mismatch, not an unrelated PR. The test now expects UNKNOWN / NOT_CONFIRMED. These intermediate failures remain in Actions history.

## Final exact-head validation

Final head \`22a18b9cee00dbab2d86a8e5c4df62256fcfc30b\`:

- Push Linux regression [#45064901740](https://github.com/SepehrGhanbari/Ario/actions/runs/45064901740): **1/1 success**, 1,968 passed / 7 skipped / 273 subtests.
- PR Implementation Regression [#45064906338](https://github.com/SepehrGhanbari/Ario/actions/runs/45064906338): **3/3 success**.
  - Linux CPython 3.13: **1,968 passed / 7 skipped / 2 warnings / 273 subtests**.
  - Linux CPython 3.14: **1,968 passed / 7 skipped / 2 warnings / 273 subtests**.
  - Windows CPython 3.13: **1,948 passed / 27 skipped / 2 warnings / 273 subtests**.
- Published TXT Restore Security [#45064906383](https://github.com/SepehrGhanbari/Ario/actions/runs/45064906383): **10/10 jobs success**.
- Read-only self-audit advisory [#45064906350](https://github.com/SepehrGhanbari/Ario/actions/runs/45064906350): success; advisory only, not independent attestation.

The Windows run executes a different test subset (27 skips versus 7 on Linux); counts are not identical coverage. The two Python/test warnings and Node 20 → 24 action deprecation warnings remain disclosed.

## Remaining boundaries / not proved

1. The workflow-run and check-run API reads are separate, non-atomic observations. A new run can appear after the final sampled list; this code does not establish a permanent freshness guarantee.
2. Selection is limited to the API's returned PR-linked run set (at most 100, otherwise the source already fails closed). It cannot prove GitHub provider provenance or that the returned API history is immutable.
3. \`run_attempt\` participates in latest-run ordering, but the check/job association is not separately fetched from the Actions job endpoint to independently bind the individual job to that attempt. Treat exact per-job rerun-attempt provenance as **NOT_ESTABLISHED**.
4. A reported completed green run is still GitHub metadata, not independent proof that tests ran honestly or that the source is safe. No merge permission, trust activation, evidence admission, signer or production authority follows.
5. The manual validator checks report shape and required explicit fields; it does not authenticate the report, recompute digests from independent history, or attest the caller-supplied reader exit code.

**Final verdict:** both reported false-green paths now have source fixes and exact-head Linux/Windows regression coverage. The result is **research CI pass only**. #333 remains Draft; #295 remains Draft/HOLD; main remains untouched.
