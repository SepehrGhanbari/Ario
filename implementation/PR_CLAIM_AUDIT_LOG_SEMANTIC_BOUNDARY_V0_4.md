# Ario audits Ario — CI log semantics and origin distinction (v0.4 HOLD)

**Status:** `RESEARCH_ONLY / DRAFT / READ_ONLY / NO_MERGE / NO_TRUST_ACTIVATION / PRODUCTION=NO_GO / EXECUTION_ATTESTATION_NOT_ESTABLISHED`.

**Lineage and reviewers:** [Issue #251](https://github.com/SepehrGhanbari/Ario/issues/251) → Draft [#255](https://github.com/SepehrGhanbari/Ario/pull/255) v0.1 supplied snapshot → Draft [#256](https://github.com/SepehrGhanbari/Ario/pull/256) v0.2 source-origin HOLD → Draft [#257](https://github.com/SepehrGhanbari/Ario/pull/257) v0.3 GitHub API fetch. This v0.4 sidecar is *added to the existing Draft #257* so a further active PR is not created. v0.1, v0.2 and v0.3 source/test blobs remain unchanged.

## Reviewer challenge / falsifiable claim

Hallaaj (a separate AI collaborator) provided a **static/source review** dated 2026-11-17. The reviewer read the handoff source and tests, **did not run Python or a real GitHub workflow**, and raised this example: a PR-controlled workflow can print `##[group]Run python -m pytest -q tests` and an arbitrary pytest-shaped summary using `echo` inside a genuine GitHub Actions job. API-origin verification then says the log came from GitHub, but **does not** establish that pytest ran or produced those counts. The reviewer noted additional run/job TOCTOU and the single-job-versus-workflow distinction.

**Author-side reproducibility (not an external attestation):** The original `v0.3` implementation was executed in a disposable local environment using an **internally constructed reader patched with synthetic responses**. A fabricated log and matching claim for `9999 passed` yielded `status=MATCH`, with `origin_status=GITHUB_API_TLS_FETCHED`, despite no live GitHub call. This is an adversarial *branch-behavior reproduction* only. **No workflow was actually created, and no GitHub log was fabricated in the repository.** It does not establish a live attack or a TLS/GitHub compromise.

### Threat boundary

- **Correspondence:** Parsed numbers and metadata in one log agree with a PR claim. This is neither test coverage nor true execution.
- **Source delivery:** The response is retrieved through the GitHub API on TLS. A real GitHub log can still contain author-controlled output.
- **Execution attestation:** No independent runner receipt, trusted execution transcript, isolated test runner, or independent witness is available. The contents are **not attested**.
- **Authority:** No positive test-quality, PR acceptance, trust activation, signer authority, or merge decision may be inferred.

### v0.4 conservative contract

`implementation/pr_claim_audit_log_boundary_v0_4.py` composes v0.3 **without changing its historical code**. It returns:

| Output field | Meaning |
|---|---|
| `correspondence_status` | Diagnostic `MATCH / MISMATCH / UNKNOWN` inherited from the bounded v0.3 comparison |
| `source_transport_status` | `GITHUB_API_TLS_FETCHED` **only if the v0.3 internal reader fetched**, or `UNVERIFIED` for injected readers; this is NOT execution evidence |
| `log_execution_attestation` | Always `NOT_ESTABLISHED` in this version; no claimant-controlled override |
| `workflow_overall_conclusion` | Read back separately from the same pinned run, or `UNKNOWN` if inconsistent/unavailable |
| `scope` | `ONE_JOB_ONLY` — the claim is not about every job in a workflow |
| **`status`** | Always `UNKNOWN` until a separately reviewed execution-attestation mechanism is implemented |

The additional bounded readback GETs recheck the **same run, attempt and selected job** and require their metadata to stay consistent with the v0.3 binding, including job conclusion and name. A concurrent rerun or changed job metadata downgrades `correspondence_status` to `UNKNOWN` rather than trusting an earlier read. The readbacks are not atomic, cannot prevent every TOCTOU window, and do not certify the log. No signer or token is used.

The v0.4 semantics are intentionally **stricter than v0.3**: one genuine delivered log may still produce diagnostic `correspondence_status=MATCH`, but cannot produce a final `MATCH` because test execution has not been independently attested. Avoid replacing the v0.3 contract silently; preserve both for comparative research.

## RED/GREEN scenarios

Tests are synthetic and **must not be relabelled as a live GitHub exploit**:

1. **RED for v0.3, HOLD for v0.4:** mock a runner-produced log that contains a *printed* pytest command marker and `9999 passed` (not actual pytest). Force the mocked internal transport path for v0.3 and observe `MATCH`; v0.4 retains `correspondence_status=MATCH` but sets `status=UNKNOWN`, `log_execution_attestation=NOT_ESTABLISHED`.
2. Claim/result disagreement: `correspondence_status=MISMATCH` stays a diagnostic, while unattested final remains `UNKNOWN`.
3. A selected job marked `success` inside a run marked `failure` is reported as two distinct observations; never call the entire workflow successful just because that job passed.
4. Run attempt or selected job conclusion changes between initial fetch and second readback → diagnostic `UNKNOWN`.
5. Caller-supplied `origin_verified` or fake attestation fields cannot promote the verdict.
6. Missing source/log, invalid pagination, and CLI exit `0` are not approvals.

**Local author-side test observation:** 13 v0.4 tests plus 26 existing v0.3 and 10 v0.2 tests = **49/49 passed** in disposable local Python. Exact-HEAD repository CI and independent review are separate obligations. No standalone live Python/GitHub API test is claimed; connected GitHub metadata examined by Ava is a separate observation, not proof that this script fetched successfully.

## Open / prior to any stronger conclusion

- Independently test real GitHub API log redirect, rate limits, tokenless access and replay on a disposable public repository without changing Ario workflows.
- Investigate attestable execution evidence (e.g., separately controlled job/workflow, pinned workflow provenance, immutable runner receipts), explicitly recognising limits of shared GitHub custody. A step's success and a source-file hash still do **not** prove meaningful test execution.
- Agree a versioned policy for what narrower-than-security semantics can ever produce a positive final state. Never turn this research probe into a required check or merge authorization without independent review and a separate owner decision.

**Decision:** `HOLD / NO_MERGE / SOURCE_AUTHENTICITY != EXECUTION_ATTESTATION / CLAIM != PROOF / UNKNOWN_VALID`.
