# Ario — Comparative Epistemic Boundaries and EAC-Bench v0.1

**Date:** 2026-11-15  
**Status:** RESEARCH INTAKE / PROPOSED / NOT PREREGISTERED / NOT EXECUTED  
**Base inspected:** `SepehrGhanbari/Ario` main, commit `2e7f83c6c7518012bed7fedfb12103ce9b7222ea`.  
**Scope:** Additive literature review and experimental protocol only. No code, tests, trust, evidence-admission authority, signer, governance, main-branch policy, or deployment changes.

> **Nonclaim:** Neither the literature comparison nor this proposed benchmark demonstrates that Ario is novel, superior, externally validated, or a truth-verification engine. Existing F11/F15 behavior, where applicable, is a **bounded structural contract**, not proof of external truth.

## 0. Intake, source custody, and what's new

This document synthesizes **two user-provided Persian research analyses**, both received 2026-11-15:

| Intake | Content | Original bytes | SHA-256 of original bytes | Handling |
|---|---|---:|---|---|
| S1 | «مقایسهٔ پژوهشی Ario با معماری‌های مشابه» (717 lines) | 43,843 | `d9607cddf218a5c292c41931e85ba2d4cfd40094775d8cf5a438397c07d07fe9` | Critical comparison, not an experiment |
| S2 | «طراحی بنچمارک تطبیقی آریو» + «بررسی نوآوری آریو در مقالات علمی» (607 lines) | 43,015 | `d941c150baa02145ecf159c5c5a37ca8cd9077a07c926000f8e487d2f1810356` | Prospective benchmark design and literature intake, not a test result |

Both source texts are user-supplied *analyses*, not authenticated execution logs or peer-reviewed publications. Their exact bytes are **not** included in this repository change; hashes identify what was reviewed, but do not establish external custody. Preserve the original uploads separately for byte-exact archival use.

The earlier proposed **EAE-01** six-family evaluation and the later **EAC-Bench** eight-track design overlap. This document treats **EAC-Bench v0.1** as the *working umbrella name*, with EAE-01 as an earlier design sketch, **not two separate completed benchmarks**. Track details and the additional 2026 prior art below are the material additions from S2.

Evidence labels used here: `USER_SOURCE_REPORTED`, `PRIMARY_ABSTRACT_VERIFIED`, `REPOSITORY_TEXT_INSPECTED`, `PROPOSED`, `NOT_RUN`, `UNKNOWN`.

## 1. Research question and potentially testable distinction

**Research question:** Can typed, provenance-aware structural boundaries reduce *unwarranted epistemic promotion*—including verdict-to-evidence recycling, laundering correlated sources, and local-PASS-to-global-truth escalation—**without** excessively rejecting genuinely supported evidence?

A useful **working characterization** is **Typed Epistemic Anti-Escalation**: explicitly distinguishing observation, historical record, lineage, evidence, assessment, and audit result, and authorizing only documented transitions among these categories.

Do not conflate:
- Recorded claim `≠` truth; repetition `≠` independent corroboration.
- Structural `PASS` `≠` semantic support or authenticated source.
- Audit result `≠` new independent evidence.
- Several local `PASS` results `≠` global truth.
- Memory record `≠` actual identity, and backup `≠` survival.
- Citation present `≠` proof that the model causally used that source.
- `UNKNOWN` is legitimate; all-`UNKNOWN` must **not** win by default.

The phrases themselves are **not novelty evidence**. Closely related ideas occur in established work; a specific, falsifiable implementation advantage remains to be tested.

## 2. Prior-art map (established families)

| Comparator | Established scope | Fair comparison with Ario |
|---|---|---|
| W3C PROV-O **and PROV Constraints** | Entities, activities, agents, derivation, revision, structural validation | Standards for provenance; Ario proposes additional *application-specific* permissions on evidentiary use. PROV is not merely a metadata logger. |
| Event Sourcing | Append-only history and replay/projections | A complementary persistence design; a local JSONL file or preservation intention is not an authenticated, tamper-resistant event store. |
| Doyle TMS / ATMS | Maintaining justifications, assumptions and dependencies while revising beliefs | Relevant baseline for belief dependency and retraction. Ario M0 is not a general TMS. |
| MemGPT / Letta | Hierarchical context and long-term memory availability | Memory management is not identical to independent evidence admission. Avoid penalizing memory systems for features outside their contracts. |
| Zep / Graphiti | Temporal knowledge graph, episode provenance, historical retrieval | Strong comparator for timestamps and source episodes; Ario M0 is not a complete temporal graph system. |
| FActScore | Atomic claim decomposition and support estimation | Complementary semantic-support baseline, not an independent source-authentication oracle. |
| NIST AI RMF | GOVERN / MAP / MEASURE / MANAGE risk processes | Governance reference rather than direct executable M0 competitor; Ario usage does not imply NIST conformance. |

These families overlap with Ario; no finding of priority, novelty, or superiority follows from categorizing them.

## 3. Relevant 2026 publications (public primary records checked)

| Work | Publication / status | Key relevance to an Ario experiment | Evidence limit |
|---|---|---|---|
| Zhou et al., **Evidence Laundering** | EMNLP 2026, DOI [10.18653/2026.emnlp-main.509](https://doi.org/10.18653/2026.emnlp-main.509) | Matched correlated/paraphrased vs apparently independent sources; structural provenance gate | Results are the authors' report, **not** an Ario comparison. |
| Liu et al., **HELM** | EMNLP 2026, [ACL 721](https://aclanthology.org/2026.emnlp-main.721/) | Epistemic-status/freshness/provenance-aware hierarchical memory | Memory-agent benchmark results are not evidence of F11/F15-equivalent behavior. |
| Zhou et al., **TimlMemBench** | Findings of EMNLP 2026, [ACL 507](https://aclanthology.org/2026.findings-emnlp.507/) | Revocation, scoping, evidence and activation, with canonical-pool and raw-dialogue controls | Different task definition from typed audit composition. |
| Liu & Zhao, **DerivAudit: Memory Is a Derivation** | [arXiv:2609.36130](https://arxiv.org/abs/2609.36130), preprint | Evidence scope, compositional validity and admission reliability of derived memory | Preprint; broadened source scope can recover support **and** harm admission reliability. |
| Zhou et al., **EviGuard** | *Applied Sciences* 2026, [DOI 10.3390/app16188925](https://doi.org/10.3390/app16188925) | Graph provenance, typed atomic claims, deterministic verification, `supported/contradicted/unknown`, action gating | Closely adjacent typed-verification prior art; application is industrial incidents. Its published figures are not verified here by rerun. |
| Baklanov et al., **COUNTERMEM** | Findings of EMNLP 2026, [ACL 1054](https://aclanthology.org/2026.findings-emnlp.1054/) | Controlled removal/update/contradiction of retrieved context; T8 design | Primarily RAG evidence use, not an M0 typed-audit test. |
| Abbas et al., **Cited but Unused** | [arXiv:2611.17161](https://arxiv.org/abs/2611.17161), 2026-11-12 preprint | Test whether citations faithfully reflect source reliance | The authors explicitly caution that their detector does **not** reliably distinguish what a model *knew* from what it actually *used*. Do not call this ground truth for causal source use. |
| Li et al., **Remember, Verify, or Ask?** | NORA 2026 workshop, [ACL NORA 1.2](https://aclanthology.org/2026.nora-1.2/) | Memory persistence / local use / verification / clarification at reuse time | MCB excludes storage-backend evaluation and downstream utility, per abstract. |

**Verification level:** Publication landing pages and primary abstracts/metadata were inspected. **Not** an exhaustive systematic literature search, full-paper methodological audit, replication, or review of all releases/source code. No exact priority ordering for independently developing Ario and the EMNLP paper has been established.

**Novelty caution:** Epistemically governed memory, `UNKNOWN`, provenance graphs, atomic-claim checking, and evidence independence all have meaningful prior art. The candidate Ario contribution is the **specific typed transition contract and composition boundary**, not ownership of the general ideas. In particular, EviGuard and DerivAudit must appear in any serious Related Work.

## 4. Inspected Ario implementation boundaries

| Area | Repository documentation / code | Narrow status / caveat |
|---|---|---|
| M0 core | `implementation/M0_STRUCTURAL_CORE_DESIGN_V1.md`, `implementation/core/schema.py` | Typed Claim, HistoricalState, Evidence, Assessment and Audit objects are distinct. Caller-populated status is not independent authentication. |
| F11 | `implementation/M0_F11_VERDICT_AS_EVIDENCE_SPEC_V1.md`, `implementation/core/audit_engine.py` | Documented bounded Verdict-as-Evidence prevention. No new run in this intake. |
| F15 | `implementation/M0_F15_COMPOSITION_FIREWALL_SPEC_V1.md` | Earlier merged composition boundary (PR #54) within its specified contract; not universal cross-system truth. |
| M0-EAG | `implementation/M0_EVIDENCE_ANCESTRY_GUARD_SPEC_V0_1.md` | Local candidate/analysis; no independent source admission authority established by this note. |
| Independent admission | `implementation/EVIDENCE_ADMISSION_CONTRACT_V0_1.md` | Specification/proposal, not operational independent authenticity. |
| Full Cross-IRG | `architecture/CROSS-IRG_INTEGRITY_V1.md` | Not implemented as a full externally verified architecture. |
| Adjacent work | `papers/evidence-laundering-2026-10-27/Manuscript.md`, `docs/ARIO_CLAIM_CARD_LAB_V0_1_2026-11-15.md`, Draft PR #180 | Preserve and link conceptually; do **not** rewrite, merge, or supersede them. |

**Test-count caution:** S2 reports a local `test_m0_regression.py` execution of 138 passing tests. This is a **user-provided report**, not a result reproduced during this document intake, and **not** an EAC-Bench score.

## 5. EAC-Bench v0.1 — prospective protocol

**Purpose:** Measure *structural audit*, *epistemic support*, and *claim-escalation control* as **three separate dimensions**. A structural `PASS` cannot mechanically make a semantic `UNKNOWN` turn into truth. Do not collapse these dimensions into a single leaderboard.

### 5.1 Eight independent tracks

| ID | Track | Primary failure to detect | Required paired control |
|---|---|---|---|
| T1 | Verdict-as-Evidence | Recycling an `AuditResult` as admitted evidence | Permitted, correctly typed evidence |
| T2 | Local-to-Global Composition | Global truth synthesized from several local `PASS` results | Valid, narrowly scoped local-result summary |
| T3 | Provenance & Lineage | Missing, forged, or circular derivation/source metadata | Declared, well-formed lineage; authentic origin only when *externally* established |
| T4 | Evidence Independence | Paraphrases or model-agreement copies counted independently | Two separately sourced and verified observations |
| T5 | Memory Revision | Old invalidated state reused or historical state erased | Correct temporal change with preserved prior record |
| T6 | Unknown / Conflict | Unwarranted certainty from absent/contradictory evidence | Adequately supported claim should not be rejected unnecessarily |
| T7 | Memory Derivation | Several separately valid facts composed into an unsupported stronger memory | Entailed, correctly scoped memory derivation |
| T8 | Counterfactual Evidence Use | Citation without behavioral dependence on retrieved evidence | Stable setup, matched coherent source edit/withdrawal |

**Backlog only, not counted in the initial 8-track pilot:** T9 Identity & Continuity Escalation and T10 Cross-Agent Composition. These require separate contracts and must not claim a test of real consciousness or identity.

**Example T1:** If `A1` is an AuditResult of `E1`, then placing `A1` in a later assessment's evidence slots must not become independent target support. Correct behavior must be checked against the exact **F11 interface**, not invented generic JSON semantics.

**Example T2:** Five local `PASS` verdicts can support a bounded **count/summary** if a contract permits it, but **cannot alone** authorize `CLAIM_TRUTH`. This is an applicability-scoped F15 check, not a proof of external falsity.

### 5.2 Pilot and scale

- **Pilot target: 120 adjudicated scenarios** = 15 *per track*, including both adversarial and positive controls.
- **Longer-term aspirational target: 1,000 scenarios**, 800 synthetic and 200 conversational/realistic, *subject to feasibility and provenance/custody review*. These are planned sizes, **not generated data**.
- Paired minimal contrasts alter **one variable** where possible: shared origin vs independent origin; unrevoked vs revoked; visible vs hidden transformation; bounded summary vs truth request; original retrieved sentence vs coherent counterfactual variant.
- Four complexity tiers: **Basic**, **Relational**, **Compositional**, **Adversarial**. Exact tier quotas, randomization and difficulty classification must be frozen before an evaluative run.
- Test separate **fixed common core** and **adaptive exploratory expansion**. Main cross-system numbers must use the fixed common core; individualized adaptive tracks must be separately analyzed, never pooled as directly comparable scores.
- Split by **source family and pattern family**, not only by individual row; do not leak paraphrase siblings across development and hidden tests.

### 5.3 Fair baselines and ablations

| Implementation / reference | Appropriate comparison | Exclusions / warnings |
|---|---|---|
| Ario M0 as actually version-pinned | T1/T2 and declared structural-subset obligations | Do not present it as an open-ended RAG truth verifier. |
| Ario without F11 and/or F15 | Explicit, isolated ablation in disposable execution environment | Must not disable controls in canonical production/main or mislabel negative tests as endorsement. |
| EAG candidate | T3/T4 *when* its actual interface and independent-authentication limits are respected | No claim of source authentication or global admission. |
| A controlled RAG pipeline ± independent-source gate | T4/T8 matched retrieval, prompt, model and corpus | Provenance gate must be specifically defined and independently evaluated. |
| PROV constraints engine | Structural provenance validity | External-truth scoring is `N/A`. |
| Named, version-pinned TMS/ATMS | Retraction, dependency and justification scenarios | Other tracks are `N/A` unless an adapter contract is added. |
| FActScore | Supported atomic-claim evaluation | Not a general identity or long-term-memory system. |
| Graphiti / HELM / TimlMemBench references | Temporal/retrieval/memory-governance subsets | A cited paper result is **not** an independently executed baseline. |
| EviGuard | Typed claim-verification design comparison | Domain-specific controls; adapter/benchmark translation requires disclosure. |

A nonapplicable contract is **`N/A`**, not automatically `FAIL`. A verified contract violation is `FAIL`. Missing implementations or inaccessible artifacts are `NOT_RUN`, not silently replaced by the published paper's numbers.

### 5.4 Outcome labels and scoring (benchmark-side, not Ario-native)

Expected adjudication includes: `UNSUPPORTED_PROMOTION`, `JUSTIFIED_BOUNDED_RESULT`, `CORRECT_ABSTENTION`, `OVER_ABSTENTION`, `NOT_APPLICABLE`, `EXECUTION_ERROR`.

Publish **numerators, denominators, definitions and uncertainty intervals** for at least:

1. **Overclaim rate** = unsupported stronger claims / applicable evaluated claim decisions.
2. **Verdict laundering rate** = improperly admitted audit verdicts / valid T1 attacks actually attempted.
3. **Composition escalation rate** = unauthorized global promotions / valid T2 attack requests attempted.
4. **Independence inflation rate** = dependent sets treated as independent / adjudicated dependent-source probes.
5. **Stale-memory reuse rate** = prohibited stale uses / applicable revoked or superseded memory probes.
6. **Counterfactual response sensitivity** = correctly changed/withheld answers / applicable coherent source interventions; report false changes separately.
7. **False rejection rate** = valid supported cases rejected / valid supported applicable controls.
8. **Coverage** = justified, informative answered cases / applicable answerable cases.
9. **Selective risk** versus **coverage**, including all-`UNKNOWN` and always-reject baselines.
10. **Replay determinism** for systems whose declared fixed code/rules/input require determinism.

Keep type/structural success, semantic support and global truth separate. F11/F15 zero-tolerance checks are **Ario contract conformance gates**, **not universal truth metrics**. `UNKNOWN`, `N/A`, missing judge labels and parse/runtime errors must not be silently dropped from denominators.

### 5.5 Experimental custody, preregistration and failure preservation

Before confirmatory results:
- Freeze the **question**, explicit gold-label oracle, source-dependence graph, sampled scenario IDs, paired controls, parser and all exclusion rules.
- Pin exact base and candidate commit SHAs, schemas, dependencies, baselines, adapters, models, prompts, retrieval snapshots and seeds.
- Have a **separate reviewer/custodian** adjudicate hidden evidence-independence labels and disagreements; report who authored and who could access test keys.
- Maintain a concealed holdout. Development results and adaptive stress tests are marked **exploratory** and not retroactively promoted to confirmatory evidence.
- Preserve all traces, timestamps, source/provenance roots, false positives, false negatives, abstentions, crashes, excluded samples and decisions **append-only**.
- Report full failure cases and confidence intervals; define material effect sizes and statistical comparison plan *before seeing confirmatory outcomes*.
- Use isolated copies of data. Do not activate trust authorities, change rulesets, install a signer, or touch protected production evidence as part of a benchmark.
- A hash is evidence only of **declared bytes**; it does not prove external authorship, independence, authentic custody, or semantic truth.

### 5.6 Falsifiable primary hypotheses

- **H1:** Multiplying paraphrases of one source must not increase the admitted **independent-source count** for an independence-aware gate. **Counterexample:** count improperly rises on a frozen ancestry-labelled case.
- **H2:** F11's contract must refuse audit-verdict recycling while admitting legitimate typed evidence in its scope. **Counterexample:** an unauthorized accepted verdict or a legitimate accepted-control rejected.
- **H3:** F15 must reject unauthorized local-to-global truth transitions yet permit specified bounded summaries. **Counterexample:** truth promotion from bare local PASSes or incorrect denial of allowed summaries.
- **H4:** Stronger safety gates must not win through blanket abstention. **Counterexample:** better attack detection accompanied by unacceptable loss of valid answer coverage under a predeclared criterion.
- **H5:** Evidence updating must affect answers when (and only when) a declared relevant intervention changes warranted support. **Counterexample:** no update on valid intervention or spurious shift on irrelevant edits.
- **H6:** Ario, RAG, Graphiti, TMS and paper-only references must be judged only on **applicable, actually executed** interfaces. **Counterexample:** rankings built by treating `N/A` as `FAIL` or copying authors' results as local replications.

No numerical success thresholds, new published claims, source admission, or preregistration are asserted here. Thresholds and adjudication must be independently finalized before execution.

## 6. Publication separation

**Proposed paper A:** *EAC-Bench: Evaluating Epistemic Escalation, Evidence Lineage, and Auditable Memory in AI Systems* — benchmark design, controls, executed baselines, negative results.

**Proposed paper B:** *Ario: Typed Epistemic Boundaries and Composition Control for Auditable AI Memory* — precise formal transition contracts, F11/F15 scope, ablations, limitations, and independently reproducible benchmark results.

These are **possible future papers**, not publication claims. They must not reuse benchmark test material while falsely presenting it as an independent validation of the design.

## 7. Immediate non-destructive next steps

1. Independent critical review of **EviGuard**, **DerivAudit**, **COUNTERMEM**, and Ario F11/F15 boundaries; identify direct overlap before novelty language.
2. Freeze a **120-row pilot schema** and its control/attack pairing in a disposable working folder; propose typed adapters compatible with the actual Ario API.
3. Recruit an independent hidden-label custodian and set rules for source authenticity, provenance keys, and conflicts; do not treat a model's agreement as independent ground truth.
4. Preregister the fixed-core protocol, exclusions, primary metrics and threshold/coverage trade-off; run only after this is approved.
5. Archive the raw outputs and every failure in a new dated record, not in this proposal. Do not count the reported 138 local M0 regressions as EAC-Bench results.

**Files that would materially help later implementation:** a pinned, executable snapshot for each **actual** comparator; dataset licenses and original prompts/artifacts; an independent source-lineage gold set; exact F11/F15/EAG fixture contracts; independent adjudicator protocol. No additional file is required just to preserve this research-design note.

## 8. Sources / audit trail

**Primary 2026 records**
- https://aclanthology.org/2026.emnlp-main.509/
- https://aclanthology.org/2026.emnlp-main.721/
- https://aclanthology.org/2026.findings-emnlp.507/
- https://arxiv.org/abs/2609.36130
- https://www.mdpi.com/2076-3417/16/18/8925
- https://aclanthology.org/2026.findings-emnlp.1054/
- https://arxiv.org/abs/2611.17161
- https://aclanthology.org/2026.nora-1.2/

**Foundational and earlier records**
- https://www.w3.org/TR/prov-o/
- https://www.w3.org/TR/prov-constraints/
- https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing
- https://doi.org/10.1016/0004-3702(79)90008-0
- https://arxiv.org/abs/2310.08560
- https://arxiv.org/abs/2501.13956
- https://aclanthology.org/2023.emnlp-main.741/
- https://www.nist.gov/itl/ai-risk-management-framework

**Repository anchors**
- `AGENTS.md`, `GOVERNANCE.md`, `experiments/README.md`, `docs/README.md`
- `implementation/core/schema.py`, `implementation/core/audit_engine.py`
- `implementation/M0_F11_VERDICT_AS_EVIDENCE_SPEC_V1.md`
- `implementation/M0_F15_COMPOSITION_FIREWALL_SPEC_V1.md`
- `implementation/M0_EVIDENCE_ANCESTRY_GUARD_SPEC_V0_1.md`
- `implementation/EVIDENCE_ADMISSION_CONTRACT_V0_1.md`
- `architecture/CROSS-IRG_INTEGRITY_V1.md`
- `papers/evidence-laundering-2026-10-27/Manuscript.md`
- `docs/ARIO_CLAIM_CARD_LAB_V0_1_2026-11-15.md`
- Draft PR #180: https://github.com/SepehrGhanbari/Ario/pull/180

**Final status:** `PROPOSED / NOT RUN / NOVELTY UNKNOWN / NO OPERATIONAL AUTHORITY`. This document preserves a falsifiable plan without laundering research prose into evidence.
