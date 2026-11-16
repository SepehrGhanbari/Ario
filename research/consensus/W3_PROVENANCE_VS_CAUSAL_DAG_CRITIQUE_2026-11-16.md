# W3 — Provenance DAG ≠ identified causal model: source-grounded critical protocol

**Date:** 2026-11-16. **Status:** `CONCEPTUAL_RESEARCH / PRIMARY_SOURCE_CHECKS / NO_RUNTIME_TEST / NO_MERGE / HOLD`.
**Review scope:** [Issue #208](https://github.com/SepehrGhanbari/Ario/issues/208), [#75](https://github.com/SepehrGhanbari/Ario/issues/75), [#81](https://github.com/SepehrGhanbari/Ario/issues/81), [#218](https://github.com/SepehrGhanbari/Ario/issues/218), plus user-supplied PACT/LLMbda/Belief Engine and *Evidence Laundering* source material.
**Consensus Pro source:** [third dedicated W3 scholarly synthesis](https://consensus.app/search/arios-third-independent-specialist-research-task-i/nFGkLvW_Sq2UXemkeeLC5w/). Original generated report remains in owner's account; this document is a bounded Ario-authored critique, not a provider-text mirror or independent empirical replication.

## Research finding: four different uses of a DAG

| Object | Meaning of an edge | What can be tested | Does the edge establish `do(X)` effects? |
| --- | --- | --- | --- |
| **Provenance/lineage DAG** | document/event `DERIVED_FROM`, `WAS_GENERATED_BY`, `ATTRIBUTED_TO`; derived data history | syntactic consistency, documented source-chain completeness **within a declared scope** | **No.** A copied assertion is not experimental causal evidence |
| **Evidence/argument DAG** | `SUPPORTED_BY`, `CONTRADICTED_BY`, `INFERRED_FROM` under an explicit policy/rule | rule consistency, unsupported leap, circular/absent parents, sensitivity to a removed premise | **No.** An argument relation is not a causal mechanism |
| **Causal statistical/structural model (SCM/DAG)** | `X` is a causal parent of `Y` under structural equations and an intervention model | identified effects **given stated assumptions**, measured variables, comparison populations and controls | **Sometimes, conditionally** under identification assumptions |
| **Execution/workflow DAG** | task `PRECEDED`, artifact `BUILT_FROM`, service `INVOKED` | reproducible workflow order, input/output binding and documented tool effects | **No general inference** about the factual correctness of generated text |

Source facts: [W3C PROV-DM Recommendation](https://www.w3.org/TR/prov-dm/) defines provenance as entities, activities, agents, derivations, responsibility; [W3C PROV Constraints](https://www.w3.org/TR/prov-constraints/) defines validity/equivalence checks on provenance **instances**, not a test for all real-world causal mechanisms. [Hernán & Robins, *Causal Inference: What If*](https://miguelhernan.org/whatifbook) identifies conditions including exchangeability, positivity and consistency for many observational causal questions. [Shpitser, Richardson & Robins, *Multivariate Counterfactual Systems and Causal Graphical Models* (2022), DOI 10.1145/3501714.3501757](https://doi.org/10.1145/3501714.3501757) explicates the structural/identification level. [Russo, Rapberger & Toni (KR 2024), *Argumentative Causal Discovery*, DOI 10.24963/KR.2024/88](https://proceedings.kr.org/2024/88/) specifically *combines* argumentation with causal-learning assumptions; these are not interchangeable concepts.

## Minimal mathematical falsifier: exact same observations, different interventions

Let `U ~ Bernoulli(1/2)`. Consider two structural models:

- **M1 (causal):** `X := U;` `Y := X`.
- **M2 (shared cause):** `X := U;` `Y := U`.

Both yield *exactly the same observational distribution*: `P(X=0,Y=0)=1/2`, `P(X=1,Y=1)=1/2`; all other `(X,Y)` outcomes have probability zero. Any observational file, even one with correct SHA-256 and perfect provenance, is compatible with both.

But `do(X=0)` differs: in M1, `Y=0` with probability one; in M2, `Y=U`, so `P(Y=1 | do(X=0))=1/2`. Hence the effect is **not identifiable from these observations alone**. A third model `Y:=U; X:=Y` also yields the same observational law with no `X -> Y` effect.

A UI that hides a *premise node* and then removes downstream argument support performs **logical support sensitivity**, not a `do` intervention; no causal structural mechanism has been externally identified.

## Concrete critique of the current proposal #208

The current Issue #208 is a **research proposal**, not an implementation or a claimed experimental result. It sketches: hash-evidence nodes → “confounder filter” → “causal DAG” → `do(X=0)` counterfactual operator. It has **not** specified an SCM, controlled observations, intervention semantics, assumptions ensuring identification, or a causal test oracle. Do not turn this omission into an allegation that a *running* Ario engine violates causal theory; no such engine was examined here.

Suggested scientifically accurate vocabulary **for a future research-only demo**:

- “Evidence provenance / source graph” instead of “verified causal DAG” when edges represent reported derivation.
- “Remove premise: recompute support” instead of “do(X=0)” for a Boolean evidence-node toggle.
- “Potentially relevant confounder / unmeasured source” instead of “confounder removed” without an identification model.
- “Observed digest matches supplied bytes” instead of “verified event”.
- “Hypothesized causal mechanism, not independently identified” for any *genuinely causal* hypothesis supplied by researchers.

**Do not silently overwrite Issue #208 or ship a demo while these are still research suggestions.**

## A data-laundering composition counterexample for #75

`C0` = unsupported content → `O1` = lossy summary, whose link to `C0` is hidden/absent → `C1` = apparently supported downstream claim with `O1` as cited source. A provenance graph may structurally validate each object and still fail to carry ancestor support. This is a transfer-of-support failure, not evidence of new independent corroboration. Treat `C0→O1` as reported `DERIVED_FROM` rather than `CORROBORATES`; `C1` must stay `UNKNOWN/UNASSESSED` for independent-world support unless a separate external reference meets an explicit contract.

Proposal for **research vocabulary only**, not a new core API:
- `DERIVED_FROM`: lineage/copy; transitive ancestry must be retained or explicitly marked incomplete.
- `CITES`: points to a claimed reference; does not imply support.
- `SUPPORTED_BY_IN_SCOPE`: proposition-level relation under a specified evidence/assessment policy, conditional on provenance and relevance.
- `CORROBORATES_CONDITIONALLY`: independent root claim within named assumptions, never source count alone.
- `CAUSED_BY_HYPOTHESIS`: requires named SCM and identification protocol; never inferred from a hash.
- `AUTHORIZES`: prohibited in this epistemic graph; an external permission boundary, not a content edge.

## W3 preregisterable challenge outline — 16 *proposed* families; 0 executed

Each family requires a clean matched control and an independently frozen expected verdict. A blind external suite is NOT yet in hand:

1. Same observed `P(X,Y)`, different SCMs and different do-outcomes (the two-model counterexample above).
2. Common confounder omitted from observed causal DAG.
3. Collider conditioned on, opening a spurious path.
4. Causal direction reversed in an observational correlation.
5. Provenance copy with hash-valid independent-looking reports.
6. Lossy summary erases an unsupported ancestor `C0`.
7. Provenance graph has a cycle; causal DAG requirement differs from provenance model semantics.
8. Timestamp precedence mistaken for causal influence.
9. Derivation edge mislabeled `CAUSED_BY`.
10. Known independent evidence source cannot be authenticated: preserve `UNKNOWN`.
11. Tool output as untrusted argument `recipient/ref/path` vs content role (PACT archive).
12. Malicious instruction included in quoted/document text, promoted to policy.
13. Signed workflow manifest claims factual truth of artifact output.
14. Missing source branch / selective disclosure to reviewer.
15. Unsupported/conflicting versions of claim copied across agent exchange (#218).
16. Genuine scoped, independent positive control should not be falsely rejected, without globally establishing truth.

**Metrics** (report separate numerators and denominators): typed-edge validation error, false promotion of source-derived data to independent evidence, unsupported causal-claim rate, correct `UNKNOWN`, false rejection of valid examples, citation ancestry coverage and privacy/scope leakage. Measure *causal effect estimate error* **only** on a benchmark where the SCM/external experimental oracle is independently known. Run-before-unseal verification and independent authorship are future requirements; the 16 prompts above are author-designed, not 16 blind tested examples.

## Source-appropriate novelty and falsifiers

**Supported contribution direction:** an inspectable **typed epistemic lineage** interface that makes falsification and provenance assumptions inspectable, and refuses to promote copied evidence into source independence. This is narrower and more defensible than claiming invention of causal DAGs, do-calculus, or a novel causal discovery engine.

**Falsifiers / stop conditions:** any candidate “causal effect” asserted solely from a record hash or provenance edge without an explicit SCM; any `do(X)` language for mere premise deletion; any `C0→O1→C1` source transformation which upgrades `C1` to independent support; any record status silently granted authorization. Separate **theoretical distinction** from actual tested code behavior.

**Decisions**:
- `ADOPT / research taxonomy`: PROV vs evidence graph vs causal SCM vs execution trace.
- `TEST`: independent controlled negative cases on provenance-support laundering and premise removal, with exact source-pinned replay.
- `HOLD`: any core causal-model semantics or code/UI contract for #208, under owner review.
- `REJECT`: “cryptographic DAG proves do-calculus causal effect” as a research conclusion.

**Caveat:** W3's full Consensus-generated 28k-character report cites some 2025–26 preprints and analogical sources; these should not be treated as independent source-backed guarantees. This memo anchors its main distinction in W3C primary specifications, official KR proceedings, original causal-inference scholarship and the repository's own issue text. No run of Ario's causal proposal is claimed.
