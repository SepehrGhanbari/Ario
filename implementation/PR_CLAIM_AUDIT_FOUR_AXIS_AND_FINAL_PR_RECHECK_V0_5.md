# Ario audits Ario — four-axis claim reading and final PR recheck (v0.5)

**Status:** `RESEARCH_ONLY / DRAFT / READ_ONLY / NON_AUTHORITATIVE / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO`. This additive v0.5 sidecar belongs to stacked Draft PR #257 and preserves v0.1–v0.4 source history and semantics. The code does not manage a key, write to GitHub, enable checks, or grant admission.

## Why v0.5 exists: attributed independent AI reviewer critique

On 2026-11-17, Hallaaj reviewed v0.4 source in plaintext (not an independently executed test and not a live GitHub API session). Two falsifiable concerns:

1. The v0.4 run recheck accepts *any* permitted `run.conclusion` without relating it to the run state first seen by v0.3. A `failure -> success` shift may be shown while the original job/log correspondence remains `MATCH`. Hallaaj correctly noted that **a workflow's conclusion is not the one-job claim**; the appropriate repair is an explicit `workflow_state_changed_during_recheck` flag, rather than automatically relabeling a still-correct *historical job/log correspondence* as an error.
2. v0.3 rechecks PR HEAD/body before returning, but v0.4 then fetches run/job again **without another PR read**. An intervening PR update `head A -> head B` can leave the diagnostics tied to A while B is the current PR head. This is a real missed sampling window, not a promotion of final `status` (which v0.4 always holds at `UNKNOWN`).

Both concerns were reproduced **by the author in a disposable Python mock lab**. In the test `test_final_pr_head_move_after_v03_recheck_detected`, original v0.4 retains `correspondence_status=MATCH` on a third-read-only HEAD change; v0.5 returns `UNKNOWN` for the diagnostic and `state_consistency=PR_CHANGED`. No actual repository head was changed during this experiment.

## Four independent dimensions (do not collapse)

| v0.5 field | Scope |
| --- | --- |
| `claim_correspondence` | `MATCH` / `MISMATCH` / `UNKNOWN` for the pinned PR claim vs fetched job/log; this is *not* test quality or proof of execution. Existing `correspondence_status` remains for backward-compatible diagnostics. |
| `source_delivery` | `GITHUB_API_TLS_ROUTE` only for an internally constructed GitHub reader after the scoped v0.4 diagnostic completes; `UNVERIFIED` for explicitly injected readers, missing data or errors. Even the route name is **not** independent custody evidence. |
| `state_consistency` | `STABLE_AT_SAMPLED_READS`, `WORKFLOW_CONCLUSION_CHANGED`, `PR_CHANGED`, or `UNKNOWN`. The first two reflect *sampled observations*, not atomicity. |
| `execution_attestation` | Always `NOT_ESTABLISHED`. Complete independent runner/test/source-hash attestation is **out of scope**. |
| **`status`** | Always `UNKNOWN` as the v0.4 non-attesting final contract; **never** merge/security authority. |

When run `conclusion` changes between the initial v0.3 run GET and the v0.4 reread, `claim_correspondence` remains the job-specific diagnostic, and `workflow_state_changed_during_recheck=true` warns that the overall workflow state has changed. No default claim of malice, invalid pytest, or a new rerun follows from the changed value alone.

After v0.4's run/job recheck, v0.5 issues **one additional read-only GET** for the same PR and requires the same global PR ID, PR number, HEAD SHA and exact PR body as captured at v0.3's initial read. A mismatch or failed final GET holds both `status` and the *current-head* `claim_correspondence` at `UNKNOWN`; historical job/log conclusions are not escalated. This closes the specifically demonstrated v0.3→v0.4 gap, **not all TOCTOU windows**: the PR may change immediately after the last GET.

The sidecar passes a recording wrapper to v0.4 solely to observe the first PR and run API results. The wrapper never changes the content, executes log text, or grants trust. The v0.4 subcall correctly treats that wrapper as injected and hence unverified; v0.5 distinguishes an *internally constructed* public HTTPS reader route from an *explicitly supplied* mock, without treating that distinction as cryptographic attestation.

## Exact reproducible offline controls

Within `implementation/`, with CPython 3.13+ (no API token or network needed):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python -B -m unittest -q tests.test_pr_claim_audit_origin_v0_2 tests.test_pr_claim_audit_github_v0_3 tests.test_pr_claim_audit_log_boundary_v0_4 tests.test_pr_claim_audit_state_v0_5
```

Author-side result: **64/64 passed** (10 v0.2 + 26 v0.3 + 13 v0.4 + 15 v0.5). The older v0.1 tests are retained unchanged in #255. Three deliberate mutations tested in **a temporary copy** of v0.5 (omit final HEAD comparison; omit final PR-body comparison; force workflow-change flag false) made their named targeted tests **RED (3/3)**; these were not pushed. Test inputs are mock GitHub responses, not a live, authenticated API fetch. Full exact-HEAD GitHub CI and independent reviewer test execution are separate pending evidence, not provided by local success.

## Open research issues

- v0.5 does **not** independently certify Python/pytest process execution, tests' relevance, or trustworthiness of Actions workflow code. A genuine GitHub log may contain an author-printed summary.
- The final PR read is not transactional; further changes and API races remain possible. `STABLE_AT_SAMPLED_READS` means only those specific sampled reads agreed.
- A genuinely live, network-connected execution of this standalone Python tool, its bounded redirect and actual log decode remains `NOT_RUN` in the author's scratch environment, unless independently recorded with real API references.

**Decision requested from reviewers:** Is the four-axis vocabulary unambiguous, and can a deterministic counterexample keep `claim_correspondence=MATCH` for a PR which has moved before the final PR GET? Do **not** approve/merge on the basis of this report. Preserve UNKNOWN as a valid research outcome.
