# Ario audits Ario — bounded real-log parser v0.7

**Status:** `RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO`. Additive sidecar to Draft PR #257. All v0.1–v0.6 modules, tests, and documentation remain unmodified. This is **not** an independently authenticated log reader, runner witness, verification of test quality, or policy/merge gate.

## Why: evidence and reviewer provenance

On 2026-11-17, an external AI reviewer, **Hallaaj**, reviewed *only the log excerpts and author's reported reproduction in chat*. Hallaaj could not retrieve the exact commit/PR independently, so their code/CI review was **NOT_RUN**. The reviewer recommended a **bounded, structured parser with optional warning counts** and explicit recognition of GitHub `setup-python`'s CPython version marker, plus RED/GREEN tests. That suggestion is not itself independent validation.

Author's direct GitHub-connected observations for [PR #257](https://github.com/SepehrGhanbari/Ario/pull/257) at observed HEAD `a67c63934a4a0a993fc14032ad29920cc970807f`, [run 44123481398](https://github.com/SepehrGhanbari/Ario/actions/runs/44123481398) attempt 1, Linux job `134180830525`:

- `2026-11-17T16:14:44.0507715Z Successfully set up CPython (3.13.18)`
- `2026-11-17T16:14:51.1730758Z ##[group]Run python -m pytest -q tests`
- `2026-11-17T16:14:58.5347756Z 1253 passed, 2 skipped, 2 warnings, 124 subtests passed in 6.36s`

These lines are **verbatim excerpts**, not a supplied full original job-log fixture. The existing v0.1 summary regex partially matches only `124 subtests passed`, then raises `no test outcome count`; its version regex also fails to recognize `Successfully set up CPython (3.13.18)`. v0.1's existing parser stays intact as a historical baseline. v0.7's locally tested sidecar fixes these **two bounded format incompatibilities**, without silently accepting any unknown summary field.

## What v0.7 does and does not do

- `pr_claim_audit_log_parser_v0_7.py` accepts a **supplied offline snapshot**, not live API data. The parser requires an entire stripped summary line: comma-separated integer/count pairs, exactly one complete pytest summary, a recognized and non-conflicting version, and exactly one `##[group]Run python -m pytest -q tests` marker.
- Recognized fields remain `passed`, `failed`, `skipped`, `subtests passed`; it now tolerates the **optional** `warning`/`warnings` count in any field order, without using warning counts as pass/fail evidence. Duplicate fields, unknown fields, incomplete summaries, conflicting Python versions and duplicate pytest command markers fail to `UNKNOWN`.
- The only additional version format is the exact `Successfully set up CPython (X.Y.Z)` line, retaining the v0.1 `Python X.Y.Z` case. **PyPy and arbitrary text are deliberately not guessed.**
- The public `assess(pr_text, evidence)` reads the same versioned v0.1 claim card, checks supplied run/job IDs, head, attempt, status and raw log SHA-256, then calls the bounded parser. The sidecar separately returns `claim_correspondence=MATCH/MISMATCH/UNKNOWN` and **ALWAYS** `status=UNKNOWN`, `source_delivery=UNVERIFIED`, `execution_attestation=NOT_ESTABLISHED`.
- These checks validate internal consistency of **provided data only**. A claim author can still fabricate a log and recompute its digest; v0.7 is **not** wired to the v0.6 GitHub API reader and cannot elevate the log to a trusted source.

## Exact local validation

From `implementation/` using CPython 3.13.5, with no network/token:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python -B -m unittest -q \
  tests.test_pr_claim_audit_origin_v0_2 \
  tests.test_pr_claim_audit_github_v0_3 \
  tests.test_pr_claim_audit_log_boundary_v0_4 \
  tests.test_pr_claim_audit_state_v0_5 \
  tests.test_pr_claim_audit_readback_v0_6 \
  tests.test_pr_claim_audit_log_parser_v0_7
```

Author-side local outcome: **99/99 passed** (77 prior + 22 new). These are **offline/synthetic tests with three verbatim real-log excerpts**, not independent, end-to-end live Python GitHub log retrieval. Deliberate mutations in **disposable copies**, removing warning support, removing setup-CPython recognition, or disabling the SHA-256 check, each made its corresponding targeted test RED (**3/3**).

## Decision boundaries and unresolved issues

- A matching parsed record is **not** `VERIFIED` pytest execution. GitHub's log and the test scripts can share controlling principals. Preserve final `UNKNOWN`.
- The author's earlier anonymous live reader on public GitHub Actions received `HTTP 403` for job logs, with distinct rate-limit and permission-text observations; this sidecar does **not** fix network auth/custody.
- If the production-ish audit workflow ever adopts v0.7, it needs an **independent review** of parsing ambiguities and exact SHA/run/job input binding, separate permissions review, and a controlled live read path; **do not automatically plug it into a trust gate**.
- This sidecar intentionally implements only these two observed format gaps. Unknown output structures remain `UNKNOWN`, not silently normalized to success.
