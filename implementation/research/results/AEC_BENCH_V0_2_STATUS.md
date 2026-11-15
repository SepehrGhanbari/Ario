# AEC-Bench v0.2 — Execution status

**State:** IMPLEMENTATION COMMITTED; CI EXECUTION NOT YET VERIFIED.\n**Inspected head:** `dba181e5c0cc31a06ce467d0dd14b4f1741a0cd2`.\n**Observed check state:** GitHub combined commit status reported Vercel `pending`; the connected workflow-run listing returned no run for this SHA. Therefore pytest/Actions execution is still NOT VERIFIED.

- Version: AEC-Bench-0.2
- Public development corpus: 120 deterministic synthetic fixtures
- Families: 10, with 12 fixtures per family
- Runner: `implementation/research/aec_benchmark_v0_2.py`
- Tests: `implementation/tests/test_aec_benchmark_v0_2.py`
- Execution identity: `AEC_BENCH_FIXTURE_REFERENCE_EVALUATOR_NOT_ARIO_RUNTIME`

## What is present

The runner creates a public synthetic corpus, evaluates fixture-level reference invariants, emits per-case expected/observed records, and reports family-level fixture matches. It explicitly does not call the Ario runtime or external baseline systems.

## What is not yet established

- GitHub Actions result for the current PR head: NOT VERIFIED.
- Independent oracle review: NOT RUN.
- PROV Python and LTMS adapter source modules have been added under `implementation/research/aec_bench_v0_2_adapters/`; their optional runtime dependencies are pinned in `requirements-adapters.txt`. Their external-library tests are NOT YET VERIFIED.\n- PROV adapter is limited to provenance representation/interchange. LTMS adapter is limited to simple assumption/dependency and retraction cases; complex cases are explicitly NOT_COMPARABLE.\n- EviGuard industrial evidence-grounding target: PAPER_ONLY / REPRODUCIBLE_CODE_NOT_LOCATED in this check. EviGuard cross-modal safety-unlearning repository: NOT COMPARABLE. DerivAudit: NOT LOCATED / NOT RUN.
- Independent validation split: NOT CREATED.
- Hidden-set evaluation: NOT CREATED / NOT RUN.
- Real-world provenance, authenticity, truth, security, privacy, model behavior, or comparative superiority: NOT EVALUATED.

## Reproduction

From the `implementation` directory:

```bash
python -m research.aec_benchmark_v0_2 --output research/results/aec_bench_v0_2_development.json
python -m pytest tests/test_aec_benchmark_v0_2.py\n\n# Optional external adapters (Python >= 3.11):\npython -m pip install -r research/aec_bench_v0_2_adapters/requirements-adapters.txt\npython -m pytest tests/test_aec_bench_v0_2.py tests/test_aec_bench_v0_2_adapters.py
```

Record the exact head SHA, workflow run URL, Python version, test counts, and raw JSON artifact only after the corresponding run is observed. Do not copy fixture-match accuracy into a scientific performance claim; it measures conformance to the author-defined synthetic contract only.
