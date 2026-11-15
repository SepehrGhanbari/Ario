# AEC-Bench v0.2 — Execution status

**State:** PUBLIC DEVELOPMENT HARNESS AND PINNED ADAPTER TESTS EXECUTED SUCCESSFULLY ON THE RECORDED PR HEAD.  
**PR:** [#234 — AEC-Bench v0.2](https://github.com/SepehrGhanbari/Ario/pull/234)  
**Branch:** `codex/aec-bench-v0-2-design-2026-11-15)  
**Verified PR head:** `bec49522b5d88f7c542e6b6142d1e7f99b0e4ab3`  
**Workflow merge ref used by Actions:** `96cf328e284639f95f05ed34d71471c14a9f8d78`

## Exact-head CI evidence

### 1. Repository implementation regression

- Workflow: `Implementation Regression`
- Run ID: `43759836996` (run #1571)
- Ubuntu job: `m0-regression` — **SUCCESS**
- Environment: Ubuntu 24.04; CPython 3.13.18; pytest 9.1.1
- Result: **1194 passed, 4 skipped, 121 subtests passed** in 6.16s.

### 2. Windows differential advisory

- Same workflow run: `43759836996`
- Job: `windows-differential-advisory` — **SUCCESS**
- Environment: Windows Server 2022; CPython 3.13.17; pytest 9.1.1
- `pip check`: no broken requirements found.
- Result: **1194 passed, 4 skipped, 121 subtests passed** in 8.26s.

This is an informational/advisory Windows job, not a required branch-protection check.

### 3. Dedicated AEC-Bench v0.2 adapter workflow

- Workflow: `AEC-Bench v0.2 Adapter Tests`
- Run ID: `43759837055` (run #24)
- Job: `adapter-tests` — **SUCCESS**
- Environment: Ubuntu 24.04; CPython 3.13.18
- Installed: pytest 9.1.1, PROV 3.3.0, LTMS 0.1.0 from pinned Git commit `738161f2bdc2a938d97c40f974f51766f45d4c0c`.
- `pip check`: no broken requirements found.
- Result: **21 passed** in 0.10s.
- The job generated and uploaded the public fixture-contract JSON artifact.

### 4. Public development artifact

- Artifact ID: `14179298378`
- [Download the AEC-Bench v0.2 Actions artifact](https://github.com/SepehrGhanbari/Ario/actions/runs/43759837055/artifacts/14179298378)
- ZIP SHA-256: `babe90550d174024c73277ba80904b0f3195e4bdcba354a2da5731baf8655576`
- ZIP size: 4,890 bytes
- Included JSON: `aec_bench_v0_2_development.json` (51,303 bytes)
- Artifact retention: 90 days; recorded expiry 2027-02-13.

The JSON reports **12/12 fixture-contract matches within each of 10 families** for the in-repository reference evaluator. This is an internal synthetic conformance check against author-written expected labels only. It is **not** a measured performance result for Ario, PROV, LTMS, a model, or any external system.

## What is implemented

- Public development corpus: 120 deterministic synthetic fixtures.
- Family structure: 10 families × 12 fixtures each.
- Matched counterfactual pairs change one controlled input field; automated tests check this property.
- Runner emits per-case expected/observed records and per-family fixture-contract conformance.
- PROV adapter: bounded representation/interchange and PROV-N round-trip validation.
- LTMS adapter: bounded conjunction-of-premises and assumption-retraction probe; unsupported semantics explicitly return `NOT_COMPARABLE`.
- No aggregate/composite benchmark score is emitted.

## Execution identity and limitations

The reference evaluator identity is `AEC_BENCH_FIXTURE_REFERENCE_EVALUATOR_NOT_ARIO_RUNTIME`. It does not call the Ario production/runtime AEC path or any external system.

PROV is used only for provenance representation/interchange. It does not authenticate roots or determine truth. LTMS is used only for bounded belief dependency/retraction tasks; it is not presented as a full ATMS implementation.

The synthetic expected labels are authored fixture-oracle premises. Passing tests establish reproducibility and conformance to those labels, not the correctness of the labels themselves, real-world provenance independence, source authenticity, truth, security, privacy, or comparative superiority.

## Not yet established

- Independent review/adjudication of the 120-case oracle: **NOT RUN**.
- Separate public validation split: **NOT CREATED**.
- Independently custodied hidden set: **NOT CREATED / NOT RUN**.
- Full external comparators for PROV/TMS/RAG/EviGuard/DerivAudit across every metric: **NOT IMPLEMENTED**. The current PROV and LTMS adapters are deliberately narrow.
- EviGuard industrial evidence-grounding paper: paper identified; reproducible code/artifact not located in this check.
- EviGuard cross-modal safety-unlearning repository: not comparable to this AEC task.
- DerivAudit: canonical public target not located; not run.
- The 12 proposed research outcome metrics as comparative system-level reports: **NOT IMPLEMENTED**.
- Real-world model behavior or architectural superiority: **NOT EVALUATED**.

## Reproduction

From the `implementation` directory:

```bash
python -m research.aec_benchmark_v0_2 --output research/results/aec_bench_v0_2_development.json
python -m pytest tests/test_aec_benchmark_v0_2.py

# Optional external adapters (Python >= 3.11)
python -m pip install pytest==9.1.1 -r research/aec_bench_v0_2_adapters/requirements-adapters.txt
python -m pytest tests/test_aec_benchmark_v0_2.py tests/test_aec_bench_v0_2_adapters.py
```

The exact PR head and workflow merge ref above are the authoritative execution record. Subsequent commits require fresh CI and do not inherit this pass status.
