# W1 — Durable source preservation and claims register (2026-11-17)

**Status:** `RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / NOT_SUBMITTED`  
**Scope:** *Independence Is Not Multiplicity* (witness provenance) only. This is a **new append-only source register**, not a rewrite of published SSRN/Zenodo material. Keep under `research/consensus/`, never `Resources/`. Authored with AI tool assistance; not independently peer reviewed.

## A. Exact Ario anchor: do not conflate manuscript versions

| ID | Canonical item | Identity / verification | Allowed inference |
| --- | --- | --- | --- |
| A1 | Original 8-page *Independence Is Not Multiplicity: A Reproducible Sixteen-Scenario Study of Witness Provenance in Audit Logs*, dated 2026-11-05, author-review preprint | SSRN public record https://ssrn.com/abstract=7686572 ; SSRN DOI https://doi.org/10.2139/ssrn.7686572 . A text extraction of the **Zenodo 8-page PDF** is committed at [source text](../../papers/zenodo-published-research/24041161/Independence_Is_Not_Multiplicity_Extracted_Text.txt); Zenodo DOI https://doi.org/10.5281/zenodo.24041161 ; source PDF SHA-256 `2398144dfae874761f1f5358ea7b9493f6f199f6af48019b36a12ffacbb3db9a` as declared by that extraction. | The 5 Nov draft reports 16 authored synthetic cases: weak storage baseline 4/16 label agreement and provenance gate 16/16; 280 selected tests passed, 148 internal text matches, three pinned blob matches. These are **in-sample authored fixture outcomes**. |
| A2 | 7 Nov author-review draft with four paired hidden-dependency counterexamples | `Ario_SSRN_Experimental_Preprint_v2_2_AUTHOR_REVIEW.pdf` from project conversation/file library. **Different draft**; not claimed to be the current SSRN version, not asserted uploaded into this PR. | Historical recognition that hidden-dependency failures were described **before** the Nov 17 extension. Do not claim novelty for re-discovering this phenomenon. |
| A3 | Fixed underlying TB-003 experiment | `implementation/witness_provenance_experiment.py`, reviewed on W1 research branch at Git blob SHA-1 `4faf010d73219af63c254097e9c135da68d60078`; SHA-256 `71912958bad6db97218ac630cadee6c34c04b286aec99b3f7cda071f8d79f567`; 26,726 bytes. Exact file path and Git blob are important; HEAD labels are mutable. | Diagnostic only; synthetic `LAB` labels do not establish source/custody authenticity, human permission or production security. |
| A4 | Nov 17 new author-built negative extension | [manuscript extension](W1_INDEPENDENCE_ADVERSARIAL_SUPPLEMENT_DRAFT_2026-11-17.md), [test code](w1_adversarial_input_sensitivity_v1.py), [unit tests](test_w1_adversarial_input_sensitivity_v1.py), [raw result](W1_SENSITIVITY_RESULTS_2026-11-17.json), [test log](W1_SENSITIVITY_TESTLOG_2026-11-17.txt), [reproduce](W1_SENSITIVITY_REPRODUCE_2026-11-17.md), [CI receipt](W1_CI_RED_GREEN_RECEIPT_2026-11-17.md). | Sixteen **development** cases, 3/3 selected hidden-dependency cases giving CONDITIONAL on falsely complete reported graphs, 192 **order permutations** (not independent cases), 15/15 local tests and later 4/4 CI matrix jobs. **No blinded holdout**, independent oracle or real witnessed event. |
| A5 | Standalone blind study protocol draft | [W1-B protocol](W1_BLIND_INDEPENDENT_CHALLENGE_PROTOCOL_V0_1.md) | Protocol alone is not execution; no independent challenge/oracle custody established. |

**Freeze rule:** Keep the published or submitted version untouched while extending the research. Before any manuscript revision or new submission, fetch the **actual current SSRN PDF** and compare its text/sha/metadata with A1 and A2. No inference that a local author-review draft is identical to what a journal is evaluating. If the author later authorizes an update, label it a new version/addendum and retain historic files.

## B. External primary scientific sources — independently locatable

Sources were located using **Consensus, Firecrawl research-paper lookup / in-body passages, and primary publication or official records**. Search snippets alone are not validation. Each is cited as an input to study design, **not** a certification of Ario.

| ID | Title / bibliographic identity | Primary source / fixed identifier | Source status and relevance |
| --- | --- | --- | --- |
| R1 | Pan, B., Stakhanova, N., & Ray, S. (2023). *Data Provenance in Security and Privacy*. **ACM Computing Surveys** 55(14s) | https://doi.org/10.1145/3593294 ; author's accessible PDF https://cyberlab.usask.ca/papers/ACMSurvey23.pdf | Peer-reviewed survey; provenance integrity, authenticity and collection/security threats are **separate requirements**. Does not test this Ario implementation. Retrieved via Consensus `w:46d02003-58f2-4958-a466-a8f6214514ff` and primary DOI. |
| R2 | Faraj, O., Megías, D., & García-Alfaro, J. (2025). *Security Approaches for Data Provenance in the Internet of Things: A Systematic Literature Review*. **ACM Computing Surveys** 57(10), Article 261 | https://doi.org/10.1145/3718735 ; publisher/affiliation record https://researchportal.ip-paris.fr/en/publications/security-approaches-for-data-provenance-in-the-internet-of-things/ | Peer-reviewed IoT survey; collection integrity and trustworthy provenance challenges, but **not** a field validation of our witness-control model. Consensus `w:a34f2a15-bc67-41a7-9148-c79d6adeda25`. |
| R3 | Sang et al. (2025). *MirGuard: Towards a Robust Provenance-based Intrusion Detection System Against Graph Manipulation Attacks* | https://arxiv.org/abs/2508.10639 ; arXiv:2508.10639v1 | **Preprint**, graph-manipulation threat; assumes a trusted computing base and protected audit output. Use for threat-model contrast, not equivalence of methodology/results. Firecrawl inspected metadata and selected in-body passages. |
| R4 | Bara, M. (2026). *Epistemic Sybil Resistance: Multiplying AI Agents Without Multiplying Evidence* | https://arxiv.org/abs/2609.01873 ; arXiv:2609.01873 | **Preprint** with prior non-identifiability framing and empirical multi-agent tests. The number of reports is not the number of evidence roots; multiple noisy extractions of a shared root **may add information**, without minting an independent root. Avoid priority/novelty claim or "all duplicated reports carry zero new information". Firecrawl inspected metadata and in-body argument. |
| R5 | Li, Y., Fan, Z., & Zhuang, Z. (2026). *Auditing the Audit: Five Failure Modes in Benchmark-Validity Audits* | https://arxiv.org/abs/2607.02586 ; arXiv:2607.02586 | **Preprint**; illustrates that the harness, oracle, data perturbation and scoring pipeline also need adversarial examination. NOT a validation of our scores. |
| R6 | W3C, *PROV-DM: The PROV Data Model* (2013) | https://www.w3.org/TR/prov-dm/ | Standard vocabulary for representing provenance, **not** a mechanism that authenticates the graph. |
| R7 | RFC 9162, *Certificate Transparency Version 2.0* (2021) | https://www.rfc-editor.org/rfc/rfc9162.html | Integrity/transparency structures rely on explicit monitoring and trust assumptions; not a proof of witness independence. |
| R8 | NIST SP 800-53 Rev.5, *AU-9 Protection of Audit Information* | https://doi.org/10.6028/NIST.SP.800-53r5 | Audit protection guidance, not a result about Ario. |
| R9 | National Academies (2019), *Reproducibility and Replicability in Science* | https://doi.org/10.17226/25303 | Re-running selected tests is computational reproduction, **not** independent empirical replication. |

## C. Claim-to-evidence matrix and explicit open questions

| Candidate paper claim | Strongest current support | Must NOT claim |
| --- | --- | --- |
| Storage-object multiplicity can overstate evidence independence in these selected cases | A1 reproducible, author-defined 16-case comparison | Deployed-system false-positive probability, superiority to state of the art |
| Reported source/control dependencies change the TB-003 classification | A3+A4 pinned source and constructed controls | That all actual dependencies are discovered |
| False completeness of the **reported** graph can allow a CONDITIONAL verdict despite concealed laboratory dependence | A4 three purpose-chosen rows and exact observation equivalence | An authenticated live witness has been defeated; 3/3 is a real-world rate |
| One observed input image can map to different hidden laboratory states | A4 generated identical observed graph SHA-256 with distinct *latent* metadata | Independently proved universal model limitation beyond assumptions; evidence of an actual attacker |
| 15 local tests / 4 CI matrix jobs pass | A4 CI receipt including original Windows RED and subsequent checkout fix | Separate blind reviewer, cross-custodian witness, production readiness |
| External literature motivates better models | R1-R9 | Literature endorsements of Ario or claim of novelty |

**Unknowns requiring future evidence:** current SSRN artifact exact version; fully traceable supplement deposit; independent external challenge cases and sealed label commitment; independent cross-operator custody; fair comparison to nontrivial baselines; sensitivity and abstention under unknown truth; editorial rights/license agreement for any revision. Never fill UNKNOWN with invented attestations.

## D. Archival and review policy

- **Preservation:** public stable DOI/arXiv links and Git blob identities, plus exact repo paths. This source register is not a full copyrighted-paper copy. Do not redistribute downloaded copyrighted PDFs into Ario without rights review.
- **Source promotion:** every new reference needs original title, authors, version, URL/DOI, accessed date, status (peer-reviewed/preprint/standard/self-origin), supported *specific* claim and limitations; source claims do not become accepted project truth automatically.
- **Independent review:** Claude and Trae may provide **separate AI-assisted adversarial critiques**, but must not be called human reviewers, statistically independent evidence sources, or proof of third-party custody. Preserve verbatim critiques and author response as new additive files. A second LLM running the same source is not a second physical source of truth.
- **Hard boundary:** no changes to `main`, `Resources/`, actual Ario keys, signer, identity, memory state, production permission, repository rulesets or witness trust activation. No merge from these tasks.
