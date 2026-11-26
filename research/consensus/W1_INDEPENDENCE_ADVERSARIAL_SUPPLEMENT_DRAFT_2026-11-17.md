# Independence Is Not Multiplicity: Observed Provenance and Hidden Common Causes

**Exploratory research extension to the 5 November 2026 sixteen-scenario Ario study — working draft, 17 November 2026**  
**Status:** RESEARCH_ONLY / AUTHOR-REVIEW DRAFT / NOT PEER REVIEWED / NO MERGE / NOT SUBMITTED  
**Researcher / project:** Sepehr Ghanbari, independent researcher and creator of Ario  
**Scope:** a pinned, pure-Python witness-provenance laboratory component; **no actual custodians, event authentication, signing, memory admission, financial-service data, external authority or production deployment.**

## Abstract

A distinct log file is not necessarily an independent evidence source. A prior sixteen-scenario exploratory Ario manuscript compared a deliberately weak storage-identity rule with a three-outcome provenance-derived gate, obtaining 4/16 versus 16/16 agreement with labels designed in the same research workflow. We retain that bounded historical observation but identify a more important inferential boundary: a provenance-aware classifier cannot recover a common source or shared control if that dependency is omitted from its input while purported graph completeness is treated as a laboratory fact. This extension reuses **the pinned Ario TB-003 implementation**, Git blob `4faf010d73219af63c254097e9c135da68d60078` (SHA-256 `71912958bad6db97218ac630cadee6c34c04b286aec99b3f7cda071f8d79f567`), without modifying it. Sixteen **newly authored development trial rows** include honest controls, concealed shared sources/administrators, false completeness claims, incomplete disclosure, candidate-controlled graphs, source identity aliases, duplicate artifacts and missing custody. The result is 16/16 agreement with the author's development expectations, **three out of three explicitly selected concealed-dependency trials producing CONDITIONAL**, and 192 order-permutation consistency checks, with fifteen standard-library unit tests passing on CPython 3.13.5. Crucially, reported observations in one modeled separate-source case are byte-for-byte identical to observations in three constructed cases with different hidden relations. This constitutes a deterministic input non-identifiability counterexample **within the authored model**, not a field attack prevalence estimate, an independent or blinded security evaluation, nor proof of any real incident. A safe path to substantive claims requires independent authentication of source and control evidence, external challenge fixtures, honest or adversarial completeness testing, preregistered outcomes and a downstream action gate that refuses to convert diagnosis into authorization.

**Keywords:** evidence lineage; witness provenance; common-source dependence; epistemic Sybil; source authenticity; falsified completeness; graph manipulation; open-science reproducibility; non-identifiability; audit uncertainty.

## 1. Context and contribution boundary

The companion preprint, *Independence Is Not Multiplicity: A Reproducible Sixteen-Scenario Study of Witness Provenance in Audit Logs* (public SSRN record https://ssrn.com/abstract=7686572; existing SSRN DOI https://doi.org/10.2139/ssrn.7686572), reports a source snapshot, selected 280-test rerun, and 16 synthetic constructed scenarios. Its baseline is deliberately weak and does **not** represent the strongest scientific alternative. A later **author-review-only**, 7 November PDF in the user's research files also describes four paired hidden-dependency examples; this extension therefore **does not claim to invent this failure mode**. Instead, it re-tests and documents the source-faithful observation with a small standalone, executable, checksum-pinned, reviewable harness, plus development tests and metamorphic ordering checks.

We seek a professional correction to a tempting but invalid narrative: 16/16 on self-constructed fixtures does **not** mean the classifier is accurate on genuine independent witnesses; even an honest graph classifier cannot see a shared administrator that has been removed from the submitted graph. Likewise, reporting many LLM answers from one evidence root does not mint another *independent root*, although multiple noisy extracts from one root may carry some additional information about that root. Roots, reports, custodians and storage replicas are different counting units [R3].

## 2. Related scientific context and precise transfer limits

- **Secure versus threat provenance:** Pan, Stakhanova and Ray [R1], an ACM Computing Surveys review, distinguish protecting provenance collection/manipulation from using provenance for detection. Hash integrity does not by itself authenticate the producer. **Transfer:** separately report raw-byte integrity, collector authenticity, completeness and third-party custody rather than one universal "verified" bit. A survey is not evidence that this particular Ario component achieves any of those properties.
- **Graph manipulation:** Sang et al. [R2, arXiv preprint] examine graph-structure manipulations for provenance-based intrusion-detection models. Their threat model assumes a functioning trusted computing base and protected auditing output; our model specifically challenges completeness/authenticity of the reported witness graph. **Transfer:** metamorphic and concealment tests, but **not** a direct comparison of scores or threat models.
- **Epistemic Sybil resistance:** Bara [R3, arXiv preprint] formalizes how report multiplicity, independent evidence roots and extraction correlation differ. Shared ancestry does not imply zero possible incremental information from repeated noisy extraction. **Transfer:** do not infer number of independent evidence roots from report count or text similarity; do not assert all repeated analysis is informationally worthless.
- **Audit of the audit:** Li, Fan and Zhuang [R4, arXiv preprint] discuss how evaluation pipelines can silently create reassuring benchmark conclusions. **Transfer:** validate harness wiring, pinned source images, mutation sensitivity, oracle separation, and what a score actually measures.
- **PROV-DM [R5], NIST AU-9 [R6], reproducibility [R7]:** notation of lineage, audit-record protection and independent empirical replication are separate goals; none substitutes for a genuinely independent custody witness.

The above references motivate experiment design. They do **not** imply that independent researchers have assessed this extension, nor that any preprint has peer-reviewed validation.

## 3. Explicit model and non-identifiability

Let the **latent laboratory state** `L` include true modeled source roots, control relationships and admitted evidence. Let `O(L)` denote only the provenance case **reported to** the evaluator, and `f(O(L))` the deterministic three-valued verdict. For two distinct latent states `L_sep` (separate modeled sources) and `L_shared` (shared source concealed), the harness constructs:

`O(L_sep) == O(L_shared)` **byte-for-byte**, while the author-declared latent relations differ. Consequently `f(O(L_sep)) == f(O(L_shared))` for any deterministic `f`. This is an *indistinguishability of observations* statement, not a proof that an attacker can forge authenticated inputs or that a real attack happened. To distinguish the two states requires authenticated evidence not included in `O` (or an external refusal to trust asserted completeness).

### Evaluator verdict semantics

- `DEPENDENT`: a validated **reported** graph explicitly exposes common source, common admin/control, or same storage object.
- `CONDITIONAL`: complete-as-declared laboratory graph passes all five field checks (source, admin, storage, capture order, two custody chains). It is **not** an external-world proof of independence.
- `UNKNOWN`: needed information, support/origin, identity or chain is incomplete/unsupported. Missing dependency assertions are not evidence of absent dependency.

A reported provenance graph is not an independently authenticated graph simply because it has `LAB` origin tags. Those tags are **synthetic fixture labels** in this study.

## 4. Methods

**Source pin.** `implementation/witness_provenance_experiment.py` from the visible Ario source snapshot exported on 12 November 2026 has 26,726 bytes, Git blob SHA-1 `4faf010d73219af63c254097e9c135da68d60078`, SHA-256 `71912958bad6db97218ac630cadee6c34c04b286aec99b3f7cda071f8d79f567`. The current research PR branch's file blob was separately read via GitHub and matched. The harness reads no more than 65,537 bytes, checks exact byte length, SHA-256 and Git blob **before executing the identical in-memory byte image**, avoiding a check/open/use race. It refuses altered sources.

**Fixtures.** The stand-alone builder follows the published test module's documented graph structure but authors its own complete synthetic cases. There are 16 **development cases**, some repeating conceptual risks from the original paper. The declared latent relations are metadata *outside* the evaluator input. Three intentionally selected concealments assert graph completeness and present exactly the same observed graph as the separate-source control. Honest incomplete control/source disclosures are paired controls. No real witness is involved; neither the categories nor the oracle were independently blinded.

**Comparators.** This extension tests the same **one pinned Ario component** and a separately coded explicit three-valued report wrapper. It does not benchmark against modern external provenance systems. Historic baseline counts from the original paper are background, not newly measured here.

**Metamorphic checks.** For each of 16 authored trial rows, perform 12 deterministic permutations of node and edge ordering, checking output *classification* invariance: 192 total permutations. These are repeated representations of 16 logical cases, **not 192 independent cases**. Fifteen standard-library tests separately verify pinning, source tamper and size rejection, positive/negative controls, source aliases, duplicate artifacts, unknown handling, observation equivalence, safety statuses, order invariance and a deliberate mutant that must fail a development expectation.

## 5. Reproducible observations, 17 November 2026

Execution environment: local Linux container, CPython 3.13.5, Python standard library only. All code is offline and signer-free; no key material was loaded or requested. See `w1_adversarial_input_sensitivity_v1.py`, `test_w1_adversarial_input_sensitivity_v1.py`, `W1_SENSITIVITY_RESULTS_2026-11-17.json`, and `W1_SENSITIVITY_TESTLOG_2026-11-17.txt`.

| Row | Reported alteration / laboratory condition | Declared latent relation | Engine-wrapper outcome |
|---|---|---|---|
| honest-separate | complete distinct observations | separate modeled | CONDITIONAL |
| honest-shared-source | report common source | shared source | DEPENDENT |
| hidden-source-false-complete | remove common-source edge; assert complete | shared source *outside reported graph* | **CONDITIONAL** |
| hidden-source-incomplete | same edited graph, source inventory incomplete | shared source | UNKNOWN |
| honest-shared-admin | report common administrator | shared administrator | DEPENDENT |
| hidden-admin-false-complete | hide administrator overlap; assert complete | shared administrator | **CONDITIONAL** |
| hidden-admin-incomplete | same edited graph, control inventory incomplete | shared administrator | UNKNOWN |
| candidate-claims-complete | candidate-supplied graph origin | shared source | UNKNOWN |
| source-alias-identity | distinct source node names, same canonical source-object ID | shared source identity | DEPENDENT |
| duplicate-witness | one witness artifact referenced twice | duplicate | UNKNOWN |
| missing-custody-transfer | one transfer edge removed | custody unknown | UNKNOWN |
| hidden-source-admin-false-complete | both common links hidden; assert complete | source + admin shared | **CONDITIONAL** |
| honest-shared-source-and-admin | both common links reported | source + admin shared | DEPENDENT |
| untrusted-self-certification | self-reported extra admin claim | modeled separate; unsupported extra claim | CONDITIONAL + unsupported-claim marker |
| separate-incomplete-control | no complete control inventory claim | modeled separate | UNKNOWN |
| separate-incomplete-source | no complete source inventory claim | modeled separate | UNKNOWN |

**Mechanical results:** 16/16 development expectations, three of three deliberately selected hidden-dependency scenarios emitted CONDITIONAL, 192/192 deterministic ordering checks, 15/15 unit tests PASS. A deliberately weakened evaluator wrapper that promotes UNKNOWN to CONDITIONAL was caught by the test harness (expected RED): this is a **test sensitivity check**, not a new security exploit. Every run retained non-authorizing statuses: `production_custody_authenticity=NOT_ESTABLISHED`, `human_authorization=NOT_EVALUATED`, `evidence_admission=NOT_EVALUATED`.

**What these denominators are not:** not false-positive rates for real adversaries, not general accuracy, not independent field measurements, not a blinded test set, and not measures of real-world probability. The 3/3 concealment fraction is an *author-chosen illustrative counterexample set*. This is a failure of claiming externally verified independence from unverified completeness, **not a claim that the implementation misclassifies correctly represented inputs**.

## 6. Open-science and author-review limitations

1. Both the new cases and their expected categories were designed by the present AI-assisted workflow; no independent oracle or hidden holdout exists.
2. The self-contained builder is author-written, so common design errors between the builder and classifier remain possible. Reviewer should independently inspect the source bytes, helper functions, and sample cases.
3. `LAB` and `complete_*=True` are synthetic *assertions*, not real attestations. The exercise cannot validate signatures, witnesses, clock synchronization, or controller identities.
4. Tests use a pinned source (not current operational authority); new hypothetical code in the repo may change later and must be separately reviewed, not silently imported.
5. The original study's 4/16 and 16/16 counts are a comparison against a deliberately weak baseline constructed with the same categories; they cannot serve as a peer-reviewed benchmark claiming superiority over the state of the art.
6. Repetition/permutations are not statistically independent. No confidence intervals or p-values should be attached to these constructed deterministic outcomes.
7. The study does not test key custody, human authorization, signer behavior, production logging, or identity/consciousness. `UNKNOWN` is a genuine outcome, not failure to produce a score.
8. No author approval for manuscript submission or scientific acceptance should be inferred from publishing this draft in a GitHub research PR; any later journal correspondence is a separate process.

## 7. Preregisterable independent follow-up (NOT PERFORMED)

**Objective**: estimate error conditional on independently verified graph origin and evaluate false-completeness attacks separately from recognized incomplete graphs.

- **Sampling unit**: one independently specified **causal graph family**, not its file permutations or agent response paraphrases. At minimum include hidden shared controller, common publisher/source, source identity alias, deceptive backup restore, simultaneous graph rewrite, selective log deletion, false lab labels, corrupted independent reference, and true independence controls. Use matched honest and adversarial disclosures per family; hold scenario family out from the evaluator designer.
- **Ground truth**: independent two-person adjudication with disclosed disagreements and a separately stored source-of-truth manifest. If actual custody is tested, require independently administrated infrastructure and explicit scope-limited consent; never use production Ario keys.
- **Preregistration**: freeze experiment protocol, classifier source hash, complete set of outcomes, primary metric definitions, and exclusion rules **before collecting blinded test outputs**. Commit externally verifiable preregistration hashes and reveal holdout only after evaluation.
- **Metrics**: report `CONDITIONAL` under *externally certified* dependence, `UNKNOWN` under lack of evidence, false rejections of independently verified separate controls, and abstention rate, each with raw denominators and family-level intervals **only when the sampling design warrants it**. Include other fair baselines, not just storage-only counting.
- **Failure gate**: any conditional independence under an independently verified hidden shared-root case **blocks claims of real-world independence under that threat model**. If the external graph cannot be authenticated or completeness attested, mark classification as informational with trust `NOT_ESTABLISHED` and do not promote to evidence admission or authorization.
- **Review**: separate experimental implementer, oracle author, and blinded adjudicator; publish raw inputs and test-run evidence, including failures, negative runs and known unknowns, before requesting an interpretation review.

Nothing in this proposal authorizes changing Ario production memory, signer, trust rules, key custody, or main branch. Status remains `RESEARCH_ONLY / HOLD / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO`.

## 8. Conclusion

The original small synthetic comparison usefully distinguishes storage-object multiplicity from source/control-aware diagnostics. This follow-up demonstrates the adjacent limit: when an adversary or incomplete reporter can remove decisive source/control edges and still have the resulting graph presented as complete and trusted, distinct latent states become observationally indistinguishable and the pinned evaluator can return the same conditional diagnosis. That result is deterministic and inspectable, but **not** proof of exploitation, real witness independence or a production failure. Professional advancement of this line of work should therefore focus on authenticated observation, independently authored challenges and honest uncertainty rather than increasing the raw number of favorable synthetic classifications.

## Sources and verification anchors

- [R0] Ghanbari (2026), *Independence Is Not Multiplicity: A Reproducible Sixteen-Scenario Study of Witness Provenance in Audit Logs*, SSRN DOI https://doi.org/10.2139/ssrn.7686572; pinned Ario source `f562e14cd8ca7f8723ad0b94eec005025f07a9a6`; the 5 November local 8-page PDF is the author's historical draft used for exact numerical quotations.
- [R1] Pan, B., Stakhanova, N., & Ray, S. (2023). *Data Provenance in Security and Privacy*. **ACM Computing Surveys** 55(14s). https://doi.org/10.1145/3593294 . Identified through Consensus; bibliographic record checked, full text not re-licensed or redistributed here.
- [R2] Sang, A., et al. (2025). *MirGuard: Towards a Robust Provenance-based Intrusion Detection System Against Graph Manipulation Attacks*. **arXiv preprint**, https://arxiv.org/abs/2508.10639 . Research text passages accessed through Firecrawl; threat-model differences explicitly recorded.
- [R3] Bara, M. (2026). *Epistemic Sybil Resistance: Multiplying AI Agents Without Multiplying Evidence*. **arXiv preprint**, https://arxiv.org/abs/2609.01873 . Research passages accessed through Firecrawl; shared evidence roots do not automatically imply identical/no incremental information in all extraction models.
- [R4] Li, Y., Fan, Z., & Zhuang, Z. (2026). *Auditing the Audit: Five Failure Modes in Benchmark-Validity Audits*. **arXiv preprint**, https://arxiv.org/abs/2607.02586 . Methodological relevance, not an Ario assessment.
- [R5] Moreau, L., & Missier, P. (eds.) (2013). *PROV-DM: The PROV Data Model*. W3C Recommendation, https://www.w3.org/TR/prov-dm/ .
- [R6] NIST. *Security and Privacy Controls for Information Systems and Organizations*, SP 800-53 Rev. 5, AU-9, https://doi.org/10.6028/NIST.SP.800-53r5 .
- [R7] National Academies of Sciences, Engineering, and Medicine (2019), *Reproducibility and Replicability in Science*. https://doi.org/10.17226/25303 .

**Disclosure:** GPT-6 materially assisted literature discovery, source-to-source comparison, research framing, code generation, execution and writing. Human authorship, independent verification of all claims and any public manuscript submission require explicit human review. AI is not a coauthor.
