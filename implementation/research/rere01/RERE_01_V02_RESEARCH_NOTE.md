# RERE-01 v0.2 — Recursive Assessment Comparator: Research Note

**Date:** 2026-11-18  
**Status:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO  
**Outcome:** **19/19 synthetic comparator controls PASS after test-first RED→GREEN; existing real-candidate RERE-01 remains 5 PASS / 7 FAIL / 3 NOT_IMPLEMENTED.**  
**Decision:** **REVISE / HOLD.** No protected memory or truth/admission policy adopted.

## 1. Source and scope pins

- The earlier RERE-01 inspection of `main` was pinned to `bc3f734890287c5ec365358680f74241f2285f82`. Main moved; the observed latest HEAD at the beginning of this turn was `9747742ddb8cb6d12c0f170aa7a70938c5d759a0`. Do not infer any branch-level merge from this.
- Current experiment is stacked on **unmerged** Draft #210, source HEAD `6235df45444f112c3a7a699d5c96cac85a4e5b66`; main does not automatically gain #210 features.
- This continuation is additive under existing [Draft #274](https://github.com/SepehrGhanbari/Ario/pull/274) and [Research Issue #276](https://github.com/SepehrGhanbari/Ario/issues/276).
- Baseline `M0` typed objects actually reused: `core.schema.Assessment`, `SupportTarget`, `Reference`. No memory state writer, source guard, signer, live ledger, trusted key, production configuration or authority flag was changed.

## 2. Literature triage — no novelty inflation

| Evidence | What it informs | Limits |
| --- | --- | --- |
| [Jon Doyle, *A Truth Maintenance System* (1979), MIT](https://dspace.mit.edu/entities/publication/5377b306-4ecc-4687-b1f5-78cbb4a0543a) | Justification dependency and revising beliefs when supporting assumptions change | Foundational prior art; recursive reason tracking is **not new by itself** |
| [Falakh, Rudolph & Sauerwald (2025), *AGM Belief Revision, Semantically*, ACM ToCL](https://consensus.app/papers/falakh-rudolph-agm-belief-revision-semantically/w:8befc6c7-4adf-4c5e-a332-8c689c95fc8a/) | Minimal rational belief-base change, distinguish semantics from implementation | Formal belief revision is not a source-authentication mechanism; fetched through Consensus |
| [W3C PROV-O (Recommendation)](https://www.w3.org/TR/prov-o/) | Explicit derivation/revision/attribution/invalidation links | Provenance graph links do not certify assertion truth or human independence |
| [Park (2026), *Graph-Native Cognitive Memory*, arXiv:2603.17244](https://arxiv.org/abs/2603.17244) | Immutable revisions, typed dependency edges, as-of queries, derived current views | Preprint; inspiration and comparison, not independent validation |
| [Brown (2026), *Quipu*, arXiv:2608.16813](https://arxiv.org/abs/2608.16813) | Two time dimensions, keeping rejected verdicts, policy-as-of replay | Preprint; proposed governance semantics not Ario implementation |
| [Wang et al. (2026), *EvoBelief*, arXiv:2610.12789](https://arxiv.org/abs/2610.12789) | Falsifiable scoped hypotheses and withdrawal of reuse authority on counterevidence | Preprint; source/custody and benchmarks do not transfer to Ario |

**Used actual services:** Consensus `search` and two `fetch` records (one subsequent query rate-limited); Exa two topical search workstreams (16 result slots) with primary preprint fetch of three arXiv articles. Summaries above rely on checked source text rather than similarity ranks. One indexed 2026 survey was also fetched, but due to limited independent corroboration it is not used as a normative technical dependency. Original textual inspiration (Kazem Tina) is philosophy, not empirical validation.

**Vercel inspection:** Connected account has `ario-research-independent` and `ario-synthetic-evidence-lab`; the latter has a single observed `READY` older production deployment, while examined `ario-research-independent` previews were tied to R63 work, **not RERE**. Vercel official docs support branch previews, SHA metadata and build logs. Neither a `READY` deployment nor a build SHA proves evidence truth, log completeness, operator custody or independent review. **No Vercel RERE deployment was created**; GitHub Actions supplies the reproducible Python execution evidence here, without exposing a new public endpoint.

## 3. Frozen scope and exact preregistration

- [Initial V0.2 preregistration](RERE_01_V02_PREREGISTRATION.json): 17 controls, fixed LAB-E101 time `2026-11-18T00:00:00Z`, seed 510101, toy oracle `CLOSED`, not passed to the comparator.
- [Addendum 01](RERE_01_V02_ADVERSARIAL_ADDENDUM_01.json): N13 and N14 registered **after** first GREEN and **before** test-first RED. Earlier outcomes and original preregistration untouched.
- [Read-only source](revision_comparator_v0_2.py) and [19-case tests](../../tests/test_rere01_revision_comparator_v0_2.py). All claim/evidence status strings are synthetic, bounded, and have **no route to M0 admission**.
- The simulated fixture policy pins source/root pairs `C/root-C`, `CAL/root-CAL`, exact door event time, and calibration recorded time `2026-11-18T00:05:00Z`. These pins are **self-authored experiment assumptions**, not actual independent custody or authenticated time.

## 4. T1–T4 behavior and separation of scores

| Step | Observed in comparator | Epistemic interpretation |
| --- | --- | --- |
| T1 (A: OPEN) | `UNKNOWN` | Unverified report recorded, not truth |
| T2 (B: CLOSED) | `UNKNOWN` | Contradiction does not privilege B by recency |
| T3 (C: CLOSED; synthetic valid pin) | `CONDITIONALLY_REFUTED_IN_LAB` | Under the frozen controller only; not externally admitted evidence |
| T4 (separate synthetic CAL challenges C timestamp; typed target `ASSESSMENT:LAB-T3`) | Current `UNKNOWN`; T3 derived reliability `CHALLENGED_BY_LATER_CALIBRATION`; old T3 `Assessment` unchanged | Second-order *toy* reasoning: T3's **justification** loses reliability; not an overwrite or an ontological claim |

**Historical integrity:** projection retains all six supplied record IDs and reconstructs T3 as-of from its prefix, rejects missing predecessor, divergent repeated ID, noncontiguous sequence, self-reference, and accepts identical replays only as an idempotent *view*. It does not guarantee durable storage, actual append-only disk semantics, independent source bytes or anti-rollback.  
**Epistemic justification:** only two source IDs with externally supplied **synthetic** controller pins may affect the outcome. CAL copied from C's root, unpinned C, wrong timestamps and reasonless T4 cannot promote/downgrade. A test pass shows these narrow predicates work in this harness, **not the current Ario cognitive memory's 7 failing guards or 3 missing interfaces**.

Against a naive append-only list, the comparator adds a typed edge pointing at an earlier Assessment and a conditional invalidation rationale. A list alone preserves entries but offers no automatic relevance/rationale evaluation. The comparator is deliberately an isolated **read-only consumer**, not a second persistent memory.

## 5. Actual execution, RED and GREEN

**17-case baseline GREEN:** [PR CI #44356569704](https://github.com/SepehrGhanbari/Ario/actions/runs/44356569704), exact source/test commit `6584503a7d72a0e0d00f76178086dd24ca1b2e25`; Linux + Windows completed successfully with `1249 passed, 10 xfailed, 121 subtests passed` each, including 17 new comparator controls.

**Pre-registered expanded RED:** addendum before test commit `f30fcd5d2a43b5205bd3b742d363bdc4a444dff1`. [Linux RED CI #44357110801](https://github.com/SepehrGhanbari/Ario/actions/runs/44357110801): **2 failed, 1249 passed, 10 xfailed, 121 subtests passed**. Both are assertion-level counterexamples:
- **N13** invalid, never warranted T3 was incorrectly displayed as `CHALLENGED_BY_LATER_CALIBRATION`.
- **N14** bogus CAL timestamp `2020-01-01T00:00:00Z` incorrectly downgraded a justified synthetic T3.

**Exact targeted GREEN fix:** research-only code commit `afe09b855de9ed20baced1502f3f2027484ab2d2` adds just (a) a frozen synthetic calibration time predicate and (b) the rule that T3 must be previously conditionally warranted before CAL challenges its reliability. [Exact-head PR CI #44357349776](https://github.com/SepehrGhanbari/Ario/actions/runs/44357349776): **SUCCESS** for Linux M0, dedicated cognitive memory, and Windows advisory jobs. Linux CPython 3.13.18 and Windows CPython 3.13.17 each: **1251 passed, 10 xfailed, 121 subtests passed**; dedicated memory suite **86 passed**. These 19 new comparator cases pass, while the **10 known RERE-01 safety failures/interface absences remain XFAIL**. No unexpected success of those original 10 is claimed.

**Reproduction (this research branch only):**
```bash
cd implementation
python -VV
python -m pip install -r requirements-research.txt
python -m pytest -q tests/test_rere01_revision_comparator_v0_2.py -rx
python -m pytest -q tests/test_rere01_m0_boundary.py -rx
python -m pytest -q tests
```
Use exact HEAD pinned to an individual CI run; this report is added subsequently and changes only documentation.

## 6. Falsification limits and next decision

1. **No independently held source authorization:** any actor holding the synthetic controller fixture can choose apparent pins; cannot grant real C or CAL authority.
2. **No persistent, authenticated append-only assessment journal:** six inputs are caller-supplied; completeness and rollback protection remain UNKNOWN.
3. **No independently pinned time:** CAL timestamp is only a fixture equality predicate; this RED→GREEN fix does not establish a trusted clock.
4. **No production integration:** no event schema migration, V1 alteration, `ACCEPTED` remapping, `SemanticNode` ID rewrite, or live assessment update. #216 architectural decision remains HOLD.
5. **No independence proof:** multiple model reviews or public CI status checks are not administrative custody separation; precommitted fixture oracle was created by the researcher.
6. **Novelty:** this is a reproducible **Ario-specific contract probe**, not a new theory of reasoning, consciousness, or independently validated cognition.

**Priority next:** (P0 / medium) decide an optional V2 assessment relation contract for a read-only adapter to M0 (not direct evidence admission); (P1 / medium) test independent source/time and real journal completeness in separate principals; (P1 / small) add mutation tests for T4 source/root/type and anti-rollback/as-of. Keep an explicit owner review for protected memory semantics and any merge. **Current decision REVISE / HOLD**.
