# AEC-Bench v0.2 — Execution and comparison status

**State:** 120-case synthetic development harness, task-scoped policy comparison, and two bounded external-library adapters executed successfully on the recorded source revision.  
**PR:** [#234 — AEC-Bench v0.2](https://github.com/SepehrGhanbari/Ario/pull/234)  
**Branch:** `codex/aec-bench-v0-2-design-2026-11-15`  
**Verified source/test head:** `ae04948986d9ca82cd81303998bb4a3f9d2aa7e9`  
**Current documentation-only follow-up:** recorded in the branch; CI evidence below applies to the tested source/test head above.

## 1. Exact-head CI evidence

### Repository regression — Ubuntu

- Workflow: [Implementation Regression #1587](https://github.com/SepehrGhanbari/Ario/actions/runs/43760501198)
- Job: `m0-regression` — **SUCCESS**
- Environment: Ubuntu 24.04, CPython 3.13.18
- Result: **1203 passed, 4 skipped, 121 subtests passed** (5.76s)

### Repository regression — Windows advisory

- Same workflow: [Implementation Regression #1587](https://github.com/SepehrGhanbari/Ario/actions/runs/43760501198)
- Job: `windows-differential-advisory` — **SUCCESS**
- Environment: Windows, CPython 3.13.17
- `pip check`: no broken requirements found.
- Result: **1203 passed, 4 skipped, 121 subtests passed** (8.25s)

The Windows job is advisory; this does not claim Windows is a required branch-protection check.

### Dedicated AEC-Bench and adapter workflow

- Workflow: [AEC-Bench v0.2 Adapter Tests #35](https://github.com/SepehrGhanbari/Ario/actions/runs/43760501207)
- Job: `adapter-tests` — **SUCCESS**
- Environment: Ubuntu 24.04, CPython 3.13.18
- Dependencies: pytest 9.1.1, PROV 3.3.0, LTMS 0.1.0 from pinned commit `738161f2bdc2a938d97c40f974f51766f45d4c0c`.
- `pip check`: no broken requirements found.
- Result: **30 passed** (0.15s)
- Both public JSON reports generated and uploaded.

## 2. Public report artifact

- Artifact ID: `14180320986`
- [Download AEC-Bench v0.2 final reports](https://github.com/SepehrGhanbari/Ario/actions/runs/43760501207/artifacts/14180320986)
- ZIP size: 14,015 bytes
- ZIP SHA-256: `90ca4e269db1f402f90dc877d0ba74cc792f628f4b504f5cece40fbda9f71409`
- Retention: 90 days; recorded expiry 2027-02-13.
- Contents:
  - `aec_bench_v0_2_development.json`
  - `aec_bench_v0_2_policy_comparison.json`

## 3. Task-scoped comparison preview

Four benchmark-side policies are evaluated only on declared applicable task lanes:

| Method | Applicable cases | Not-comparable cases |
|---|---:|---:|
| Raw relay count | 24 | 96 |
| Majority vote | 12 | 108 |
| Hash-integrity-only | 12 | 108 |
| Ario typed-policy candidate | 120 | 0 |

These are not four full competing products. The first three are intentionally simple baselines. The typed-policy candidate calls the benchmark-side reference evaluator; it does **not** call the deployed Ario runtime or current AEC adapter.

### Results in the generated policy-comparison JSON

- **Raw relay count:** root-count accuracy 4/9 (44.4%) on known-root lineage cases; false-independence inflation 4/9 (44.4%); missing ancestry preserved as UNKNOWN 0/3.
- **Majority vote:** claim-disposition accuracy 6/12 (50%); macro-F1 approximately 0.425 across the four classes with nonzero support; unsupported claim promotions 4/8 (50%) on eligible UNKNOWN/CONTESTED/REJECTED cases. REJECTED has zero support in this 12-case claim sample and is explicitly reported as excluded from macro-F1.
- **Hash-integrity-only:** integrity-state accuracy 12/12 on the synthetic digest fixtures. Authentication remains **NOT COMPARABLE**, because this baseline does not inspect authentication.
- **Typed-policy candidate:** matched all 12 author-written expected labels in each of the 10 fixture families. Within these fixtures: false-independence inflation 0/9; missing ancestry preserved 3/3; unsupported promotions 0/8; scope violations detected 5/5 with 0/4 false positives on in-scope controls; composition-invalid cases detected 6/6 with 0/6 false positives on valid/incomplete controls. Temporal ordering matched 6/6 strictly evaluable cases; 6 uncertain/partial/superseded cases were excluded from strict ordering.

**Interpretation constraint:** results describe how the authored policies behave against a deterministic, author-authored synthetic fixture oracle. The typed candidate's 12/12 family matches are not an independent evaluation and do not measure Ario's deployed runtime. Fixture labels and the candidate evaluator live in the same benchmark codebase and require independent oracle review. Hash-only's 12/12 is confined to simple digest fixtures and says nothing about source authentication or truth.

No composite score or overall leaderboard is produced. NOT_COMPARABLE cases are not counted as failures.

## 4. Implementation boundaries

- Public development corpus: 120 deterministic synthetic fixtures, 10 families × 12.
- Matched counterfactual pairs: tests require one controlled input-field change per pair.
- Macro-F1 output: per-class support is disclosed; zero-support classes are explicitly listed as excluded from macro-F1 rather than silently omitted.
- PROV adapter: bounded lineage representation/interchange and PROV-N round trip only; no root authentication or truth decision.
- LTMS adapter: bounded premise dependency/retraction probe only; not a full ATMS implementation.
- EviGuard industrial evidence-grounding paper: PAPER_ONLY in this check; reproducible implementation/artifact not located.
- EviGuard cross-modal safety-unlearning repository: different task; NOT COMPARABLE to AEC lineage/claim evaluation.
- DerivAudit: canonical public target NOT LOCATED / NOT RUN in this check.

## 5. Not yet established

- Independent review/adjudication of fixture labels: **NOT RUN**.
- Independent validation split: **NOT CREATED**.
- Independently custodied hidden test set: **NOT CREATED / NOT RUN**.
- Full end-to-end external comparators across all proposed metrics: **NOT IMPLEMENTED**. PROV and LTMS adapters remain deliberately narrow.
- Real-world source independence, authenticity, truth, privacy, security, language-model behavior, or architectural superiority: **NOT EVALUATED**.

## 6. Reproduction

From the `implementation` directory:

```bash
python -m research.aec_benchmark_v0_2 --output research/results/aec_bench_v0_2_development.json
python -m research.aec_benchmark_v0_2_policy_comparison --output research/results/aec_bench_v0_2_policy_comparison.json
python -m pytest tests/test_aec_benchmark_v0_2.py tests/test_aec_benchmark_v0_2_policy_comparison.py

# Optional external adapters (Python >= 3.11)
python -m pip install pytest==9.1.1 -r research/aec_bench_v0_2_adapters/requirements-adapters.txt
python -m pytest tests/test_aec_benchmark_v0_2.py tests/test_aec_benchmark_v0_2_policy_comparison.py tests/test_aec_bench_v0_2_adapters.py
```

The exact-head CI evidence above applies to source/test head `ae04948986d9ca82cd81303998bb4a3f9d2aa7e9`. Subsequent code changes require fresh CI; this record does not automatically validate future revisions.
