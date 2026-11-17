# AEC-Bench v0.2 — Execution and comparison status

**State:** 120-case synthetic development harness, task-scoped policy comparison, two bounded external-library adapters, and a separate direct M0-EAG runtime probe suite executed successfully.  
**PR:** [#234 — AEC-Bench v0.2](https://github.com/SepehrGhanbari/Ario/pull/234)  
**Branch:** `codex/aec-bench-v0-2-design-2026-11-15`  
**Initial v0.2 source/test head (historical CI record):** `052f8a518352d147cb8cc31fd5ae8d2255c51ac2`

## 1. Exact-head CI evidence

### Repository regression — Ubuntu

- Workflow: [Implementation Regression #1595](https://github.com/SepehrGhanbari/Ario/actions/runs/43760899621)
- Job: `m0-regression` — **SUCCESS**
- Environment: Ubuntu 24.04, CPython 3.13.18
- Result: **1208 passed, 4 skipped, 121 subtests passed** (6.69s)

### Repository regression — Windows advisory

- Same workflow: [Implementation Regression #1595](https://github.com/SepehrGhanbari/Ario/actions/runs/43760899621)
- Job: `windows-differential-advisory` — **SUCCESS**
- Environment: Windows, CPython 3.13.17
- `pip check`: no broken requirements found.
- Result: **1208 passed, 4 skipped, 121 subtests passed** (8.40s)

The Windows job is advisory, not a claim that Windows is a required branch-protection check.

### Dedicated AEC-Bench and adapter workflow

- Workflow: [AEC-Bench v0.2 Adapter Tests #41](https://github.com/SepehrGhanbari/Ario/actions/runs/43760899668)
- Job: `adapter-tests` — **SUCCESS**
- Environment: Ubuntu 24.04, CPython 3.13.18
- Dependencies: pytest 9.1.1, PROV 3.3.0, LTMS 0.1.0 from pinned commit `738161f2bdc2a938d97c40f974f51766f45d4c0c`.
- `pip check`: no broken requirements found.
- Result: **35 passed** (0.28s)
- All three public JSON reports generated and uploaded.

## 2. Public report artifact

- Artifact ID: `14180635543`
- [Download AEC-Bench v0.2 runtime reports](https://github.com/SepehrGhanbari/Ario/actions/runs/43760899668/artifacts/14180635543)
- ZIP size: 15,621 bytes
- ZIP SHA-256: `513b4afa705e49f8da2e3a0373ee53c35f2abd15113795a13e960cc0c9ee771b`
- Retention: 90 days; recorded expiry 2027-02-13.
- Contents:
  - `aec_bench_v0_2_development.json`
  - `aec_bench_v0_2_policy_comparison.json`
  - `aec_bench_v0_2_ario_m0_eag.json`

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

**Interpretation constraint:** results describe how the authored policies behave against a deterministic, author-authored synthetic fixture oracle. The typed candidate's 12/12 family matches are not an independent evaluation and do not measure Ario's deployed runtime. Fixture labels and candidate evaluator live in the same benchmark codebase and require independent oracle review. Hash-only's 12/12 is confined to simple digest fixtures and says nothing about source authentication or truth.

No composite score or overall leaderboard is produced. NOT_COMPARABLE cases are not counted as failures.

## 4. Direct probes against the actual Ario M0 runtime

New module: `implementation/research/aec_bench_v0_2_adapters/ario_m0_eag_adapter.py`. It imports and directly invokes the repository's `core.audit_engine.AuditEngine` and parses engine-owned `M0-EAG-0.1` findings. It does not reimplement the guard.

- Actual inspector version: `M0-1.2`.
- Mandatory EAG profile: `M0-EAG-0.1`.
- Probe cases: **12**.
- Expected predicates matched: **12/12**.
- Test file: `implementation/tests/test_aec_bench_v0_2_ario_m0_adapter.py`.

The 12 probes exercise:
1. Exact supplied-record-presence positive predicate.
2. Traceable ancestry without independent-admission authority.
3. Exact self-confirmation as known inadmissibility.
4. Distinct-claim ancestry without support promotion.
5. Shared source root across fresh observation/evidence wrappers and inflation detection.
6. Missing ancestor remains UNKNOWN.
7. Forbidden plus missing branches both retained.
8. Known prior audit-result ancestry remains forbidden.
9. Candidate-only inspection has use NOT_EVALUATED despite structural PASS.
10. Duplicate same-typed Observation identity is unresolved.
11. Unsupported Observation record version is unresolved.
12. Description-to-independent-support replay is rejected as UNKNOWN.

This is materially different from the benchmark-side typed-policy candidate above: these 12 probes call the actual repository M0-1.2 engine. However, they are still author-authored synthetic probes, not an independent evaluation of real external sources or language-model behavior. They do not create a separate-root count, authenticate sources, determine proposition truth, or authorize independent admission. M0-EAG's boundaries are retained rather than stretched to cover unrelated fixture families.

## 5. Third-party adapter boundaries

- **PROV adapter:** bounded lineage representation/interchange and PROV-N round trip only; it does not authenticate roots or determine truth.
- **LTMS adapter:** bounded premise dependency/retraction probe only; not a full ATMS implementation.
- **EviGuard industrial evidence-grounding paper:** PAPER_ONLY in this check; reproducible implementation/artifact not located.
- **EviGuard cross-modal safety-unlearning repository:** different task; NOT_COMPARABLE to AEC lineage/claim evaluation.
- **DerivAudit:** canonical public target NOT LOCATED / NOT RUN in this check.

## 6. Not yet established

- Independent review/adjudication of fixture and probe labels: **NOT RUN**.
- Independent validation split: **NOT CREATED**.
- Independently custodied hidden test set: **NOT CREATED / NOT RUN**.
- Full end-to-end external comparators across all proposed metrics: **NOT IMPLEMENTED**. PROV and LTMS adapters remain deliberately narrow.
- Real-world source independence, authenticity, truth, privacy, security, language-model behavior, or architectural superiority: **NOT EVALUATED**.

## 7. Reproduction

From the `implementation` directory:

```bash
python -m research.aec_benchmark_v0_2 --output research/results/aec_bench_v0_2_development.json
python -m research.aec_benchmark_v0_2_policy_comparison --output research/results/aec_bench_v0_2_policy_comparison.json
python -m pytest tests/test_aec_benchmark_v0_2.py tests/test_aec_benchmark_v0_2_policy_comparison.py

# Optional external adapters and actual M0 runtime probes (Python >= 3.11)
python -m pip install pytest==9.1.1 -r research/aec_bench_v0_2_adapters/requirements-adapters.txt
python -m pytest tests/test_aec_benchmark_v0_2.py tests/test_aec_benchmark_v0_2_policy_comparison.py tests/test_aec_bench_v0_2_adapters.py tests/test_aec_bench_v0_2_ario_m0_adapter.py
python -c "import json; from pathlib import Path; from research.aec_bench_v0_2_adapters.ario_m0_eag_adapter import build_m0_probe_report; Path('research/results/aec_bench_v0_2_ario_m0_eag.json').write_text(json.dumps(build_m0_probe_report(), indent=2, sort_keys=True) + '\\n', encoding='utf-8')"
```

The exact-head CI evidence above applies to source/test head `052f8a518352d147cb8cc31fd5ae8d2255c51ac2`. Subsequent code changes require fresh CI; this record does not automatically validate future revisions.


## 8. Independent oracle-review package — latest head

**Package state:** prepared and committed; independent adjudication has **NOT RUN**.

- Protocol: `implementation/research/AEC_BENCH_V0_2_INDEPENDENT_REVIEW_PROTOCOL.md`
- Exporter: `implementation/research/export_aec_bench_v0_2_review_packet.py`
- Test: `implementation/tests/test_aec_bench_v0_2_review_packet.py`
- Latest tested head: `f3eab39883d6709775732bfff40ff78ab7b8d721`
- Latest [AEC-Bench workflow #52](https://github.com/SepehrGhanbari/Ario/actions/runs/43915549574): **SUCCESS**, **37 passed**; generated the label-stripped JSON and CSV adjudication template and uploaded them with the three benchmark reports.
- Latest [Implementation Regression #1629](https://github.com/SepehrGhanbari/Ario/actions/runs/43915549637): Ubuntu **1210 passed, 4 skipped, 121 subtests passed**; Windows advisory **1210 passed, 4 skipped, 121 subtests passed**. Both jobs SUCCESS.
- Latest artifact ID: `14249776774`
- [Download latest benchmark and reviewer packet artifact](https://github.com/SepehrGhanbari/Ario/actions/runs/43915549574/artifacts/14249776774)
- Artifact SHA-256: `cc99154e05ceb99fc02a6e724c2a2fb89847f381071483dc10cab29d2016f15e`
- Artifact expires 2027-02-14.

### Blinding limitation

The JSON packet omits expected labels and rationales, but the repository is public and contains the oracle-bearing generator. Therefore blinding is **procedural only**, not technically enforced. A genuinely access-controlled blind review requires a separate custodian to distribute the input-only snapshot and withhold oracle-bearing files until timestamped first-pass decisions are received. The public packet is not a hidden test set.

### Reviewer governance

The protocol asks for at least two independent first-pass reviewers, conflict/prior-exposure/LLM-use disclosure, preserved original judgments, explicit per-case rationale, counterfactual pair checks, and a third reviewer for material disagreements. No reviewer has yet been recruited or has submitted a judgment.


## 9. Counterfactual-pair audit hardening — pending CI

A follow-on change was committed to the same research branch after the latest successful code/test run:

- Current branch head at the time of this status update: `db4108a6ff0ae6fe86252c048dcd7fa752a5eee1` (later documentation commits may advance the branch without changing this source/test revision).
- Added recursive JSON-like input-difference paths so a paired fixture is not counted as a one-variable counterfactual merely because multiple nested values sit under one changed top-level key.
- Added a structural audit of pair membership, same-family membership, duplicate case IDs within a pair, and exactly one atomic input change.
- Exposed the pair audit as a separate field in both the fixture-contract report and task-scoped policy-comparison report; it is not a performance score.
- Added regression tests that verify all ten authored pairs and reject a synthetic pair with two nested changes.

**Verification state:** **NOT YET CI-VERIFIED.** The last successful code/test head remains `f3eab39883d6709775732bfff40ff78ab7b8d721`. No successful workflow run has yet been observed for `db4108a6ff0ae6fe86252c048dcd7fa752a5eee1`. Do not treat earlier CI runs as validating this follow-on change.

**Interpretation limit:** a structurally single-field pair is not proof that the changed field is causally relevant, semantically isolated, or correctly labelled. Independent oracle review remains NOT RUN.


## 9. Input-completeness and temporal-provenance hardening — 2026-11-17

A targeted adversarial review identified two fail-open/robustness gaps in the benchmark-side reference evaluator. These changes harden the synthetic reference evaluator only; they do not alter the deployed M0 runtime or the 120 authored fixture labels.

### 9.1 Lineage source-to-root completeness

The evaluator previously could return a determinate root count when a declared source had no corresponding entry in the source-to-roots map. That could turn incomplete ancestry into a seemingly complete count.

The lineage evaluator now returns `root_count: null` and `status: UNKNOWN` when:
- the declared source list is missing, empty, duplicated, or contains a blank/non-string identifier;
- the root map is missing, malformed, or its keys do not exactly match the declared source list (including undeclared extra entries);
- any source has an empty/malformed root list or a blank/non-string root identifier;
- unresolved-parent, missing-edge, or hidden-root conditions apply.

Four out-of-corpus mutation regressions cover missing source mapping, undeclared extra mapping, duplicate source declaration, and blank root identifier.

### 9.2 Temporal record completeness and validity

The evaluator previously accessed temporal fields directly and could raise an exception when event or recording time was missing. It could also treat non-finite numeric values as apparently ordered.

The evaluator now applies these conservative outcomes:
- missing event, observation, or recording time → `PARTIAL`;
- malformed or non-finite timestamp → `UNKNOWN`;
- explicit clock uncertainty or timestamp conflict → `UNCERTAIN`;
- contradictory time ordering → `ANOMALY`;
- only complete, finite, ordered timestamps can be classified as `ORDERED` or `STALE`.

Four out-of-corpus mutation regressions cover missing event time, missing recording time, malformed timestamp, and non-finite timestamp.

### Exact source/test head and CI

- Source/test head: `60cf133b7c131b265903b6be5cbda974c3ce7e7a`
- [AEC-Bench v0.2 Adapter Tests #70](https://github.com/SepehrGhanbari/Ario/actions/runs/44081800110): **SUCCESS — 49 passed**. Fixture, comparison, M0 runtime, and public reviewer-packet reports were regenerated.
- [Implementation Regression #1929](https://github.com/SepehrGhanbari/Ario/actions/runs/44081799868): **SUCCESS — 1222 passed, 4 skipped, 121 subtests passed** (Ubuntu). The Windows advisory job was skipped.
- [AEC-Bench reports and reviewer packet artifact](https://github.com/SepehrGhanbari/Ario/actions/runs/44081800110/artifacts/14328021370), SHA-256 `11871400852ee5fe499c396d6d8deb2ebc306921a69db187590004cd1154aae3`.

These runs verify the exact source/test head above. This status-file revision is documentation-only and does not alter that source/test head. The corpus remains synthetic and public. No independent oracle adjudication, hidden validation set, or real-world source truth/authenticity evaluation has been completed.
