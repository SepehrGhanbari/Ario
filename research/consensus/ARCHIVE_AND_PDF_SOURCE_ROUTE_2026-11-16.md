# Ario research-source and review-route inventory — 2026-11-16

**Purpose:** Locate user-supplied PDF/source material, distinguish origins and permissions, and avoid reading the wrong archive copy in later research sessions. `RESEARCH_ONLY`; no authority transfer; no full-content publication of private/provider PDFs.

## A. What was actually inspected

On 2026-11-16 the authenticated repository `SepehrGhanbari/Ario` main tree was enumerated (338 tree items in the observed response). **No repository root directory named `Resources/` was visible in that tree.** This is not evidence that no such folder exists on the user's local PC or a separate branch. The user's files are also available through their ChatGPT file Library; Library references do **not** establish GitHub paths.

### User Library/source PDFs and related report files

| Library title / original title | Source type | Observed applicability | Verification caution |
| --- | --- | --- | --- |
| `2605.30771v1.pdf` — *Eywa: Provenance-Grounded Long-Term Memory for AI Agents*, Joshi 2026 | Author preprint PDF (29 pages in library) | Memory evidence-before-belief, retrieval/answer separation | [Original arXiv](https://arxiv.org/abs/2605.30771), claimed metrics remain author-reported |
| `Research_task_for_Ario_Epistemic_Middleware_memo.pdf` | Consensus output (10 pages, Library) | Memory lab comparisons, XERJ/FTS5, 20 hard negatives | [Original owner thread](https://consensus.app/search/research-task-for-ario-epistemic-middleware-memory/UfhwzQC9ShuHrUDnFlQ5Uw/), AI synthesis not peer review |
| `Conduct_a_rigorous_source-grounded_scholarly_posi.pdf` | Consensus output (6 pages, Library) | Provenance manuscript critique, source independence | [Original owner thread](https://consensus.app/search/conduct-a-rigorous-source-grounded-scholarly-posit/Y9Kv3vnbSiCY_jNNKA4Ylw/) |
| `_ (1).pdf` — *Literature for Ario's Witness-Provenance Study* | Consensus output (8 pages, Library) | Copying, source dependency, provenance completeness | [Original owner thread](https://consensus.app/search/کاربرد-و-عملکرد-موتور-جستجوی-consensus/RCNEghQ5R_m1lGLxf-PMwQ/) |
| `Research_task_for_Ario_R9_security_evaluate_exter.pdf` | Consensus output (7 pages, Library) | Rollback/epoch/effect fencing | [Original owner thread](https://consensus.app/search/research-task-for-ario-r9-security-evaluate-extern/K0dtTOA2SYuajpEon36gkw/) |
| `Ario_arXiv_Paper_2026-10-15.pdf` — *Evidence Cannot Authenticate Itself* | First-party Ario preprint | Audit and evidence admissibility claims | Not peer review; version-specific |
| `Ario_M0_Epistemic_Audit_Addendum_v0_2.pdf` | First-party Ario supplement | M0 source / policy limits | Not peer review |
| `Ario_SSRN.pdf` — *Evidence Laundering in Auditable AI Systems* (27 Oct 2026) | First-party Ario working paper | Hash/source/authorization separation | Do not treat printed 'test pass' as new run |
| `ARIO_FOUR_PAPER_EVIDENCE_REVIEW_2026-11-10.md` | Prior authored evidence review (Library) | Four source papers below and source hashes | Prior research interpretation, not primary artifact itself |
| `2605.12978v2.pdf`, `2605.11039v1.pdf`, `2605.15343v1.pdf`, `2602.20064v2.pdf` | User-supplied 2026 arXiv papers (documented in above review) | Memory overwrite, argument-level provenance PACT, belief engine, LLMbda information flow | The review summarizes paper metrics; inspect original PDFs before reusing precise numeric claims |

### First-party archival paths visible on `main`

- `papers/zenodo-published-research/23259916/`: preliminary Ario design, extracted text + published PDF + provenance.
- `papers/zenodo-published-research/24041161/`: *Independence Is Not Multiplicity*, extracted text + published PDF + provenance.
- `papers/zenodo-published-research/24054535/`: *Provenance-Aware Auditing of AI Claims*, extracted text + published PDF + provenance.
- `papers/evidence-laundering-2026-10-27/Manuscript.md`: direct manuscript source.
- `papers/RESEARCH_SOURCE_COMPLETENESS_AUDIT_2026-11-14.json`: source-inventory record; no assertion here that its findings were independently rechecked.
- `releases/complete-research-2026-11-14-a39ac06e/`: historical Ario research export, SHA256SUMS and manifests; **historical**, not always current.
- `implementation/witness_provenance_experiment.py`, `implementation/ledger_observation_adapter.py` and tests: implementation sources for specific research questions.
- `AGENTS.md`/reviewer rules constrain protected code/merge operations.

### Current research / review route

- [Existing seven-day plan](CONSENSUS_7_DAY_PLAN_2026-11-16.md) and [current append-only status](CONSENSUS_7_DAY_STATUS_APPEND_2026-11-16.md).
- W1 source dependency, W1-B blind challenge: [W1 protocol](W1_BLIND_INDEPENDENT_CHALLENGE_PROTOCOL_V0_1.md).
- W2 memory source/status: [W2 source-supported vs executed](W2_MEMORY_EPISTEMIC_STATUS_AND_SOURCE_SUPPORT_2026-11-16.md), Draft #210, Issues #209/#216/#223/#227.
- W3 source-evidence vs causal-model DAG: [Consensus Pro research thread](https://consensus.app/search/arios-third-independent-specialist-research-task-i/nFGkLvW_Sq2UXemkeeLC5w/); Issue #208 and Issues #75/#81/#218. At inventory creation, this new thread was **running**, not completed.
- Retrieval candidate baseline: PR #185 mock-only, real XERJ **NOT_TESTED**.
- Explicit rights rule: **do not upload/rehost whole private Library PDFs or full Consensus provider exports** merely because text can be read; use brief authored digests with link/DOI and verify redistribution rights separately.

## B. Source evidence grades

- `PRIMARY_VERIFIED`: bibliographic data/source text checked against publisher, PubMed, primary author or original specification. This does not independently replicate paper results.
- `PREPRINT_OR_AUTHOR_REPORTED`: primary manuscript but its claimed results not independently reproduced.
- `CONSENSUS_ONLY`: cited/aggregated in provider AI research; independent bibliographic check pending.
- `PROJECT_FIRST_PARTY`: Ario source/issue/PR evidence; code source or test report must be pinned by exact blob and commit for reproduced claims.
- `REPRODUCED_SYNTHETIC`: test actually run on pinned code with recorded input, output, environment and limitations.
- `PROPOSED_NOT_TESTED`: protocol or fixture only, not evidence for success.

## C. References independently checked during this sprint

- [Johnson, Hashtroudi & Lindsay (1993), *Source Monitoring*](https://pubmed.ncbi.nlm.nih.gov/8346328/), DOI 10.1037/0033-2909.114.1.3.
- [McClelland, McNaughton & O'Reilly (1995), *Complementary Learning Systems*](https://pubmed.ncbi.nlm.nih.gov/7624455/), DOI 10.1037/0033-295X.102.3.419.
- [ICLR 2025 LongMemEval original proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/d813d324dbf0598bbdc9c8e79740ed01-Abstract-Conference.html).
- [W3C PROV-DM Recommendation 30 April 2013](https://www.w3.org/TR/prov-dm/): describes provenance records, not a sufficient causal identification model.
- [Hernán & Robins *Causal Inference: What If*](https://miguelhernan.org/whatifbook): exchangeability/positivity/consistency are identification assumptions, not guarantees from hashed edges.
- Other citations in provider reports require original-source review before assigning `PRIMARY_VERIFIED`.

No real source files or history were overwritten in this inventory.
