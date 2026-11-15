# AEC-Bench v0.2 — Execution and comparison status

**State:** 120-case synthetic development harness, task-scoped policy comparison, and two bounded external-library adapters executed successfully on the recorded PR revision.  
**PR:** [#234 — AEC-Bench v0.2](https://github.com/SepehrGhanbari/Ario/pull/234)  
**Branch:** `codex/aec-bench-v0-2-design-2026-11-15`  
**Verified source/workflow head:** `7d4b7fcdea23f95d650529fb73fdc37105be6449`

## 1. Exact-head CI evidence

### Repository regression — Ubuntu

- Workflow run: [Implementation Regression #1581](https://github.com/SepehrGhanbari/Ario/actions/runs/43760151467)
- Job: `m0-regression` — **SUCCESS**
- Environment: Ubuntu 24.04, CPython 3.13.18
- Result: **1202 passed, 4 skipped, 121 subtests passed** (5.45s)

### Repository regression — Windows advisory

- Same workflow run: [Implementation Regression #1581](https://github.com/SepehrGhanbari/Ario/actions/runs/43760151467)
- Job: `windows-differential-advisory` — **SUCCESS**
- Environment: Windows, CPython 3.13.17
- `pip check`: no broken requirements found.
- Result: **1202 passed, 4 skipped, 121 subtests passed** (10.85s)

The Windows job is advisory, not a claim that Windows is a required branch-protection check.

### Dedicated AEC-Bench and adapter workflow

- Workflow run: [AEC-Bench v0.2 Adapter Tests #30](https://github.com/SepehrGhanbari/Ario/actions/runs/43760151499)
- Job: `adapter-tests` — **SUCCESS**
- Environment: Ubuntu 24.04, CPython 3.13.18
- Installed dependencies: pytest 9.1.1, PROV 3.3.0, LTMS 0.1.0 from pinned commit `738161f2bdc2a938d97c40f974f51766f45d4c0c`.
- `pip check`: no broken requirements found.
- Result: **29 passed** (0.21s)
- Both the fixture-contract JSON and task-scoped policy-comparison JSON were generated and uploaded.

## 2. Public report artifact

- Artifact ID: `14179882908`
- [Download AEC-Bench v0.2 reports from GitHub Actions](https://github.com/SepehrGhanbari/Ario/actions/runs/43760151499/artifacts/14179882908)
- ZIP size: 13,944 bytes
- ZIP SHA-256: `4f7898b07c32d46faa7039eedf05d352b86e3cb27ba0965c17d22bbef862d728`
- Retention: 90 days; recorded expiry 2027-02-13.
- Contents:
  - `aec_bench_v0_2_development.json`
  - `aec_bench_v0_2_policy_comparison.json`

## 3. Task-scoped comparison preview

Four benchmark-side policies are evaluated only on their declared applicable task lanes:

| Method | Applicable cases | Not-comparable cases |
|---|---:|---:|
| Raw relay count | 24 | 96 |
| Majority vote | 12 | 108 |
| Hash-integrity-only | 12 | 108 |
| Ario typed-policy candidate | 120 | 0 |

These are not four full competing products. Raw relay count, majority vote, and hash-integrity-only are intentionally simple baselines. The typed-policy candidate calls the benchmark-side reference evaluator; it does **not** call the deployed Ario runtime or current AEC adapter.

### Results visible in the generated JSON

- **Raw relay count:** root-count accuracy 4/9 (44.4%) on known-root lineage cases; false-independence inflation 4/9 (44.4%); missing ancestry preserved as unknown 0/3.
- **Majority vote:** claim-disposition accuracy 6/12 (50%); macro-F1 approximately 0.425 over classes present in the fixture sample; unsupported claim promotions 4/8 (50%) on eligible UNKNOWN/CONTESTED/REJECTED cases.
- **Hash-integrity-only:** integrity-state accuracy 12/12 on the synthetic digest fixtures. Authentication remains **NOT COMPARABLE**, because this baseline does not inspect authentication.
- **Typed-policy candidate:** it matched all 12 author-written expected labels in each of the 10 fixture families. Within these fixtures it showed zero false-independence inflation (0/9), preserved missing ancestry (3/3), made zero unsupported promotions (0/8), detected all 5 scope-violation fixtures with 0/4 false positives on in-scope controls, and detected all 6 composition-invalid fixtures with 0/6 false positives on valid/incomplete controls. Its temporal ordering lane used 6 strictly evaluable cases and excluded 6 uncertain/partial/superseded cases.

**Interpretation constraint:** these values describe how the authored policies behave against a small, deterministic, author-authored fixture oracle. In particular, the typed candidate's 12/12 family matches are not an independent evaluation and do not measure Ario's deployed runtime. The labels and evaluator are maintained in the same benchmark codebase and require independent oracle review. Hash-only's 12/12 integrity score is also confined to these simple digest fixtures and says nothing about authenticating sources or truth.

No composite score or overall leaderboard is produced. A metric marked NOT COMPARABLE is not counted as a failure.

## 4. Implementation boundaries

- Public development corpus: 120 deterministic synthetic fixtures, 10 families × 12.
- Counterfactual pairs: tests require a matched pair to change exactly one input field per family.
- PROV adapter: bounded lineage representation/interchange and PROV-N round trip only; it does not authenticate roots or determine truth.
- LTMS adapter: bounded premise dependency/retraction probe only; it is not a full ATMS implementation.
- EviGuard industrial evidence-grounding paper: PAPER_ONLY in this check; a reproducible implementation/artifact was not located.
- EviGuard cross-modal safety-unlearning repository: a different task and NOT COMPARABLE to AEC lineage/claim evaluation.
- DerivAudit: canonical public target NOT LOCATED / NOT RUN in this check.

## 5. Not yet established

- Independent review/adjudication of fixture labels: **NOT RUN**.
- Independent validation split: **NOT CREATED**.
- Independently custodied hidden test set: **NOT CREATED / NOT RUN**.
- Full end-to-end external comparators across all 12 research metrics: **NOT IMPLEMENTED**. PROV and LTMS adapters remain deliberately narrow.
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

The exact-head CI evidence above applies to source/workflow head `7d4b7fcdea23f95d650529fb73fdc37105be6449`. Later commits require their own tests; this status file must not be read as automatic validation of future revisions.
