# Ario audits Ario — read-only GitHub evidence fetch pilot v0.3

**Status: RESEARCH_ONLY / STACKED_DRAFT / NON-AUTHORITATIVE / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO.**

**Lineage:** #251 idea → #255 offline `ARIO-PR-CI-0.1` → #256 strict unverified-source `ARIO-PR-CI-0.2` → this **experimental** v0.3 read-only GitHub fetch. None of the previous files, tests, or historical evidence is rewritten. The code requires no token and must not handle any signer or account secrets. It cannot create an approval, required status check, action, comment, PR change, or trust decision.

## Goal and source distinction

The author-controlled statement in a PR body is a **claim**. The GitHub REST `GET` response containing run metadata, attempt-scoped job membership, and job logs is a separate **service response**. v0.3 compares these two with the existing v0.1 parser, but explicitly **does not** declare GitHub to be an independent human, external custody, cryptographic witness, or ground-truth oracle. A malicious workflow or compromised GitHub control plane could generate misleading logs. Only the *observed correspondence* can be MATCH/MISMATCH.

**Unlike v0.2**, v0.3 can return a final scoped `MATCH` or `MISMATCH` if it used its own HTTPS GitHub API transport successfully. The status is NEVER admission, verification of test quality, or a merge gate. If source access is blocked, the PR body has no structured claim, identities diverge, the log is incomplete, or the job cannot be assigned to the exact attempt, final outcome is `UNKNOWN`. An injected fake reader used by unit tests is always `UNVERIFIED`, with final `UNKNOWN` even if its internal correspondence is `MATCH`.

## Retrieval chain

1. Validate the owner, repository and PR number as bounded identifiers. Fetch actual `GET /repos/{owner}/{repo}/pulls/{pr_number}`. Parse exactly one versioned PR claim block (per v0.1); tie its `head_sha` to the current PR HEAD.
2. Fetch `GET /repos/{owner}/{repo}/actions/runs/{run_id}`. Check run ID, attempt, commit, completed status, `pull_request` event and the `pull_requests[]` link to the **same PR number and HEAD SHA**. Reject an unrelated run even if its SHA is identical.
3. Fetch **attempt-specific** `GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{run_attempt}/jobs?per_page=100&page=N`. Demand complete consistent pagination (up to 500 jobs), exactly one requested job, its `run_id`, `run_attempt`, `head_sha`, and completion status. Do not substitute a "latest run jobs" response for a pinned attempt.
4. Fetch the selected `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs`; only follow a **single** GitHub-issued HTTPS redirect to an allowlisted Actions log host, with no Authorization header, no proxies and default TLS certificate verification. Fetch to EOF under a 1.5 MB cap and decode strict UTF-8. **No supplied log URL or local snapshot is treated as authentic.** Unexpected redirect, HTTP error, authentication requirement, network failure, oversized log or missing record → `UNKNOWN`.
5. Re-fetch the PR after reading the log and reject if HEAD **or body** changed during the operation. Recalculate SHA-256 of the fetched log; then compare the real fetched fields and exactly one pytest summary using the v0.1 parser. Include job/run/head/attempt and log hash in a bounded diagnostic receipt. Do not serialize the full log into the result.

**Trust boundary:** `origin_status: GITHUB_API_TLS_FETCHED` means only that the GitHub **service response** was obtained by this research reader over TLS. It does **not** establish an independent witness/issuer, immutable logs, correct test contents, unrelated source custody or any authority to approve a PR. A test mock can simulate the service path; its execution is not evidence of live network access or genuine GitHub origin.

## How to run

From `implementation/` with **CPython 3.13+**, on a machine that has network access to GitHub:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest -q tests.test_pr_claim_audit_github_v0_3
PYTHONDONTWRITEBYTECODE=1 python -B pr_claim_audit_github_v0_3.py --owner SepehrGhanbari --repo Ario --pr 249
```

PR #249 and many historical PRs currently have no machine-readable `ARIO-CI-CLAIM-V0.1` block in their body; `UNKNOWN` is therefore the **expected** outcome for those PRs, not a transport failure or evidence of failed tests. To observe a positive *live* result, a reviewer must first put a **correct, exact-HEAD, exact-run and job claim** into a separate **test PR body** under authorization, then independently fetch its GitHub run. Do **not** silently alter existing PR descriptions for a demo.

GitHub API anonymous access may be rate-limited or logs may require Actions **read** permission. **This pilot does not accept, store or forward any tokens.** If the API refuses the requested evidence, report `UNKNOWN`; never relax the binding checks or fake a log. The model environment that authored this pilot could read public run/job logs through its GitHub connector but had **no direct DNS/network access from the local Python container**. Accordingly, live execution of the standalone `urllib` fetcher remains **NOT_RUN** pending independent sandbox testing.

## RED/GREEN scope and reproducibility

The author ran a synthetic mock-transport suite: **24 tests for v0.3**, plus 10 v0.2 tests: **34 passed** (Python 3.13.5). The mock never establishes independent real GitHub-origin evidence; a positive result from a monkeypatched `PublicGitHubReader` tests routing only. The strict fake reader returns final `UNKNOWN`. Boundary tests cover:

- Wrong PR HEAD, changed PR HEAD/body between first and second GET, run HEAD mismatch, run not linked to the PR, wrong run attempt, job from the wrong run/attempt/head, missing job or incomplete job pagination.
- A matching *fabricated* log with forged counts + hash, injected fake `origin_verified`, numeric mismatch, missing claim, unavailable log, HTTPS allowlist checks, rejected metadata redirects, rejected unexpected log redirects, valid single Actions redirect.
- Three deliberate local source mutants were killed by relevant tests: (1) removing the run-to-PR linkage check, (2) promoting fake-reader correspondence to final `MATCH`, and (3) ignoring the post-fetch PR HEAD/body recheck. **3/3 selected mutants RED; not exhaustive mutation coverage.**

The complete Ario regression suite was **not** run in the author's scratch folder. The **exact PR HEAD** CI results need to be retrieved and documented after the branch is published.

## Independent review challenge for Hallaaj

Hallaaj's previous critique correctly exposed the self-hashing-origin gap in v0.1 and explicitly marked full source inspection and program execution NOT_RUN. Please inspect the **actual new v0.3 source and tests**. Focus on: (a) whether a crafted REST response can be replayed across unrelated PRs, (b) whether job membership is correctly pinned to rerun attempts, (c) whether redirect handling leaks authentication or allows arbitrary hosts, (d) whether a controlled mock can be mistaken for real GitHub-origin trust, (e) whether a mid-fetch PR change can produce stale MATCH, and (f) whether a successful job summary can be falsely interpreted as the success of an entire workflow. For each issue give exact lines, input, expected/observed behavior and `VERIFIED / SUSPECTED / NOT_RUN`. Do not modify `main`, Rulesets, trust, keys, workflows or reviewer permissions. Review PR as **comment-only**.

**Next gate:** independent adversarial review of the exact HEAD, mock-transport RED/GREEN and live **read-only** `urllib` sandbox test against a public PR with a valid claim. Only then consider a separately versioned source-custody and time/attempt provenance contract; never silently upgrade this pilot into a merge gate.
