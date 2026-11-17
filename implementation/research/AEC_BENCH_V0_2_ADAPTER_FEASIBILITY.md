# AEC-Bench v0.2 — Adapter feasibility register

**Research snapshot:** 2026-11-17  
**Status:** desk-researched candidates; the bounded PROV and LTMS adapter smoke tests now pass in the dedicated AEC-Bench CI workflow. No full external-system comparison or product-level equivalence is claimed.

This register distinguishes a paper, a code repository, and an executable benchmark adapter. A shared name is not enough to identify a system. Targets without a pinned, runnable implementation remain NOT RUN.

## 1. PROV Python — suitable for lineage representation and interchange

- Project: [trungdong/prov](https://github.com/trungdong/prov)
- Candidate package version: `prov==3.3.0`
- Repository snapshot inspected: `6b432eda5cfa41abb227b5dc65fbc05eaa63a126`
- License: MIT
- Runtime declared by project: Python >= 3.11
- Relevant capabilities: PROV-DM objects; PROV-N, PROV-JSON, PROV-JSONLD, PROV-XML and PROV-O serialization; derivation, attribution and graph conversion.
- Source adapter: `implementation/research/aec_bench_v0_2_adapters/prov_adapter.py`. It maps lineage fixtures into PROV entities, agents, attribution and derivation relations, and includes a PROV-N round-trip check. It rejects missing/extra source-to-root entries and malformed or empty root identifiers before graph creation. Generated local identifiers use reversible UTF-8 hex encoding, avoiding unsafe PROV QName characters.
- Runtime evidence: [AEC-Bench workflow #79](https://github.com/SepehrGhanbari/Ario/actions/runs/44082508758) at source/test head `0e7772c0085732506af6735d9cfa6d089c2754bd` — **SUCCESS, 52 passed**. With `prov==3.3.0` installed, tests cover PROV-N round-trip, incomplete-map rejection, blank-root rejection and arbitrary UTF-8 identifier round-trip.

**Boundary:** PROV is a provenance data model and implementation library. It does not authenticate source roots, decide whether claims are true, or supply Ario's claim-disposition policy. A successful serialization/round trip is a lineage-representation result only.

Sources: [project README](https://github.com/trungdong/prov/blob/6b432eda5cfa41abb227b5dc65fbc05eaa63a126/README.md), [project metadata](https://github.com/trungdong/prov/blob/6b432eda5cfa41abb227b5dc65fbc05eaa63a126/pyproject.toml), [version documentation](https://prov.readthedocs.io/en/3.3.0/).

## 2. LTMS Python — suitable for belief dependency and retraction tests

- Project: [pisanuw/ltms](https://github.com/pisanuw/ltms)
- Package version declared in project: `0.1.0`
- Repository snapshot inspected: `738161f2bdc2a938d97c40f974f51766f45d4c0c`
- License: MIT
- Runtime declared by project: Python >= 3.10
- Relevant capabilities: assumption enable/retract, Boolean constraint propagation, justifications, dependency-directed backtracking, and explanation of derived beliefs.
- Source adapter: `implementation/research/aec_bench_v0_2_adapters/ltms_adapter.py`. It maps simple conjunction-of-premises cases and includes an assumption-retraction probe. Complex scope, time, shared-dependency and composition-firewall cases are explicitly returned as NOT_COMPARABLE.
- Runtime evidence: the same [AEC-Bench workflow #79](https://github.com/SepehrGhanbari/Ario/actions/runs/44082508758) — **SUCCESS, 52 passed** with LTMS pinned to commit `738161f2bdc2a938d97c40f974f51766f45d4c0c`. Tests cover supported/missing conjunction premises, explicit non-comparability and assumption retraction.

**Boundary:** this is an LTMS/JTMS-oriented implementation, not a general implementation of every ATMS variant. It is suitable for bounded truth-maintenance comparisons, not a substitute for a provenance data model or for verifying external source authenticity.

Sources: [project README](https://github.com/pisanuw/ltms/blob/738161f2bdc2a938d97c40f974f51766f45d4c0c/README.md), [project metadata](https://github.com/pisanuw/ltms/blob/738161f2bdc2a938d97c40f974f51766f45d4c0c/pyproject.toml).

## 3. EviGuard — name collision; two different targets

### 3.1 Machine-verifiable evidence grounding

- Paper: [EviGuard: Machine-Verifiable Evidence Grounding for LLM-Based Industrial Incident Reasoning](https://doi.org/10.3390/app16188925)
- Domain: industrial incident reasoning, provenance graph, claim compiler, deterministic claim verifiers, temporal/identity/policy checks and response gate.
- Relevance: conceptually close to the AEC questions about evidence support, typed claims, UNKNOWN and action gating.
- Current adapter status: **PAPER_ONLY / REPRODUCIBLE_CODE_NOT_LOCATED** in this desk check.
- The article's Data Availability Statement says an anonymized EviCPS-Bench release will be deposited and that the DOI will be added at proof stage. Until the exact artifact, code revision, splits and configs can be pinned and reproduced, paper-reported metrics are not imported as measured results in AEC-Bench.

The paper reports 42 hardware-in-the-loop attack chains and claim/relation results. These remain author-reported paper results, not AEC-Bench replication results.

### 3.2 Cross-modal safety unlearning

- Paper: [EviGuard: Evidence-Guided Connector Intervention for Cross-Modal Safety Unlearning in Multimodal LLMs](https://doi.org/10.1145/3767308.3834945)
- Repository: [XinYi-my/EviGuard](https://github.com/XinYi-my/EviGuard)
- Domain: multimodal model safety unlearning and connector intervention.
- Current adapter status: **NOT COMPARABLE TO AEC LINEAGE/CLAIM TASKS**.
- Its repository release explicitly states that final checkpoints, complete training logs, final resolved configurations and original prediction/judgment files are unavailable, and that full benchmark reproduction has not been validated.

Do not conflate this repository with the industrial evidence-grounding paper above merely because both use the name EviGuard.

Sources: [industrial EviGuard paper](https://www.mdpi.com/2076-3417/16/18/8925), [cross-modal EviGuard repository](https://github.com/XinYi-my/EviGuard).

## 4. DerivAudit — exact target not identified

A targeted exact-name web search and GitHub repository search for `DerivAudit` / `Deriv Audit` did not identify a matching public paper-plus-code implementation that can be pinned. Status: **NOT LOCATED — NOT RUN**.

This is not a claim that no private, unpublished, differently named, or unindexed project exists. Do not create a straw-man adapter or report a comparison until the user supplies a canonical paper/repository or one is independently identified.

## 5. Adapter admission rules

Before an external target is eligible for a scored comparison, record:
1. Canonical paper/project identity and task alignment.
2. Immutable source commit or release and license.
3. Exact runtime and locked dependencies.
4. Reproducible command and configuration.
5. Input/output mapping, including every lossy or unsupported field.
6. Round-trip or behavior tests on paired fixtures.
7. Whether the adapter runs the actual project code or merely reimplements a subset of its ideas.

A package that serializes PROV records, an LTMS that maintains assumptions, and an evidence-grounding application solve different tasks. Their results must remain in separate metric lanes; do not combine them into a single ranking.

## 6. Current eligibility summary

| Target | Public code located | Fit to AEC | Status |
|---|---|---|---|
| PROV Python 3.3.0 | Yes | Provenance representation/interchange | Bounded adapter tests and PROV-N round-trip passed in AEC workflow #79 at `0e7772c`; no authenticity/truth claim |
| LTMS Python 0.1.0 | Yes | Belief dependency/retraction | Bounded conjunction/retraction tests passed in AEC workflow #79 at `0e7772c`; not a full ATMS comparison |
| EviGuard industrial evidence grounding | No reproducible code located in this check | High conceptual relevance | Paper only; not run |
| EviGuard cross-modal unlearning | Yes | Different problem | Not comparable |
| DerivAudit | No matching public target located | Unknown | Not run |

**Non-claim:** locating a codebase is not validating it; pinning a dependency is not reproducing a paper; and a successful adapter test is not evidence that Ario or the external system is generally superior. The AEC CI result validates only the declared bounded adapter checks on the recorded synthetic fixtures. It does not establish real-world root independence, source authenticity, truth, or complete PROV/LTMS feature coverage.
