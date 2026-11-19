# Ario R2 D10 — GitHub Provider Readback ≠ Independent Custody

**State:** `RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO`  
**Parent:** [Draft #270](https://github.com/SepehrGhanbari/Ario/pull/270), D9 source HEAD `277570d4f26afb4c69f58ec5426aff8b919d58e1` when inspected.  
**Research tracker:** [#251](https://github.com/SepehrGhanbari/Ario/issues/251).  
**Scope:** exactly these *new* files: `implementation/provenance_r2_d10_provider_readback.py`, `implementation/tests/test_provenance_r2_d10_provider_readback.py`, and `implementation/PROVENANCE_R2_D10_REVIEW.md`. Existing files and controls unchanged.

## Purpose and provenance of observations

D9 checked mathematical consistency of *caller-supplied*, lab-generated signed history and floor; it could not demonstrate genuine source custody or live retrieval. D10 performs a narrower, public, read-only provider-readback experiment. It samples the **specific existing public GitHub PR #270**, completed workflow run **44392429462** and the job-list page, then re-reads the PR. An injectable reader enables bounded negative testing without external calls during standard CI.

Prior to authoring D10, a connected GitHub API GET retrieved the following **real API metadata**, separately from D10's executable:

- `GET /repos/SepehrGhanbari/Ario/pulls/270`: open Draft, HEAD `277570d4f26afb4c69f58ec5426aff8b919d58e1`.
- `GET /repos/SepehrGhanbari/Ario/actions/runs/44392429462`: run `44392429462`, `run_attempt=1`, `event=pull_request`, `status=completed`, `conclusion=success`, matching HEAD and workflow `379498305`.
- `GET /repos/SepehrGhanbari/Ario/actions/runs/44392429462/jobs?per_page=100`: total 2 jobs, Linux `m0-regression` (ID `135113339427`) and Windows `windows-differential-advisory` (ID `135113338821`), each completed/success with matching HEAD/run/attempt.

The connected GitHub API read was **observed via the connector**. It is not a cryptographically signed witness receipt. The GitHub Actions run and jobs are not a demonstration that tests are semantically correct or independently executed. The source author controls test code and workflow; successful CI is not source-independent truth.

**Standalone Python live fetch:** `python -B provenance_r2_d10_provider_readback.py --public-d9-probe` was actually attempted in the current local container. It returned `INCOMPLETE_OR_UNAVAILABLE_READBACK` / final `UNKNOWN`; a separate direct URL test returned `URLError [Errno -3] Temporary failure in name resolution`. Standalone live GitHub GET is **NOT_ESTABLISHED** in this environment. The 38 tests use **fake response bytes**, not live GitHub.

## Boundaries and design

- No credentials, user-provided endpoints, arbitrary URL fetching, signing, mutable floor, production admission, or workflow permission changes. Fixed `https://api.github.com` host, four GETs (PR/run/job-list/PR), max 256 KiB per JSON response, 8-second default timeout, redirect rejection, strict JSON duplicate-key rejection.
- Fixed public PR/run/HEAD target for the optional manual probe, no dynamic retries to bypass rate limits. Jobs must be complete on one page (`total_count <= 100`), distinct, matching run ID/attempt/HEAD, including both required named jobs. Any missing/partial/error response returns `UNKNOWN`.
- This reads four samples sequentially, **not an atomic multi-resource snapshot**. A PR can move A→B→A between first and final reads without being observed; the corresponding negative control preserves `global_freshness=NOT_ESTABLISHED` even on a metadata match.
- Reader-injection means a claimant could fabricate all four response bodies. `CONSISTENT_CALLER_SUPPLIED_READBACK` means **only structural correspondence of supplied JSON bytes**, never proof of acquisition, TLS or provider identity. The direct HTTPS reader is not an attested independently enrolled witness. A proxy, trusted CA or OS administrator may alter the connection's environment.
- GitHub provider metadata cannot independently establish who controls the job command, whether a real `pytest` process ran, or whether a separate custodian retained the repository state/history. No external signed checkpoint or OOB key enrollment exists in D10.
- GitHub's published REST endpoints are documented at https://docs.github.com/en/rest/actions/workflow-runs and https://docs.github.com/en/rest/actions/workflow-jobs . Artifact provenance and execution correctness remain different propositions; see https://docs.github.com/en/actions/concepts/security/artifact-attestations .

## Measured local tests

From `implementation/`:

```shell
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -p test_provenance_r2_d10_provider_readback.py -q
```

**38/38 local tests PASS.** Test subjects include PR-head drift across reads, wrong HEAD/run/attempt/job, incomplete job pagination, duplicate/malformed/overlong JSON, 403 for each endpoint, off-host and unapproved paths, redirect refusal, caller-forged reader and silent ABA limitation. Nine deliberately unsafe mutations each produced a RED test failure in disposable same-author copies. The original redirect test initially failed to kill a mutant because it supplied `None` as both input and expected return; replacing it with a non-null sentinel corrected the test flaw. These are **author-local test observations**, not independent audit.

**Result fields never promote:** `status=UNKNOWN`, `source_control_independence=NOT_ESTABLISHED`, `github_transport_authentication=NOT_ATTESTED_BY_THIS_ADAPTER`, `pytest_execution_attestation=NOT_ESTABLISHED`, `externally_pinned_custodian=NOT_ESTABLISHED`, `independently_retained_floor=NOT_ESTABLISHED`, `global_freshness=NOT_ESTABLISHED`, `evidence_admission=NOT_EVALUATED`, `claim_truth=UNKNOWN`.

## Falsification and next external gate

**Positive structural control:** all four supplied snapshots match; diagnostic `metadata_correspondence=CONSISTENT_CALLER_SUPPLIED_READBACK`, while final `UNKNOWN` remains. This is deliberately **not** a positive control for real independent source identity or custody. A hidden fork, undisclosed revocation, compromised shared administrator, or an omitted newer provider state cannot be excluded by four GET results.

**Future independently verifiable positive control (NOT_RUN):** an external operator not controlled by the claimant enrolls/pins its key out-of-band, executes independent rerun, signs scoped attestation and publishes checkpoint to a separately retained append-only history. A verifier fetches it using an independently pinned key and checks a protected historical floor plus external consistency. Establish operator control / backup / recovery separation. Measure blind positive recall and false promotions. No automatic original GitHub-process attestation.

**Reviewer challenge (exact-HEAD, no approval implied):** attempt to make `metadata_correspondence` positive despite missing/moved PR, forged job identity, truncated pagination, redirect, or an inconsistent run attempt; attempt to cause any trusted or admitted final status. Evaluate independent source-control and ABA limitations separately; do not infer independent execution from GitHub success. Preserve `DESIGN_REVIEW` versus `SOURCE_INSPECTED` versus `ACTUALLY_RUN` and cite exact commit.

**Decision:** `D10=RESEARCH_ONLY / HOLD / NO_MERGE / SOURCE_CONTROL_INDEPENDENCE=NOT_ESTABLISHED / TRUST_ACTIVATION=NO_GO`.
