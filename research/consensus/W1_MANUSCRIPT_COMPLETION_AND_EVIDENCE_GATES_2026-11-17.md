# W1 — Article-completion map and evidence gates (2026-11-17)

**Research status:** `RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO`.  
**Target:** strengthen the science in *Independence Is Not Multiplicity* while preserving the **already archived / editorially shared first article**. This planning document does not update SSRN, Zenodo, journal publication terms, source files outside `research/consensus/`, or any production behavior. The user has previously authorized the publisher to continue its original review/publication under fee-free, author-rights-preserving conditions; **do not turn this research extension into an unapproved substitute manuscript**.

## 1. Freeze the edition before editing a sentence

- **Original public 5 Nov 2026 article**: `papers/zenodo-published-research/24041161/Independence_Is_Not_Multiplicity_Extracted_Text.txt` (8-page PDF-derived text; original PDF hash in its header); public SSRN DOI `10.2139/ssrn.7686572`. Treat as a historical edition, never silently rewrite.
- **Additional 7 Nov author-review draft:** distinct 11-page manuscript described in the file library; four paired hidden-dependency cases already existed in that draft. Its exact public publication status and hash/availability must be checked before using as an official edition.
- **New 17 Nov paper extension:** `W1_INDEPENDENCE_ADVERSARIAL_SUPPLEMENT_DRAFT_2026-11-17.md`, plus pinned and executed `w1_adversarial_input_sensitivity_v1.py` and named result/evidence files.
- **Paper packaging choice (not taken):** (A) standalone follow-up paper (preferred if first article proceeds unchanged); (B) explicitly numbered, author-controlled revised version; or (C) supplementary methods appendix shared with journal by *separate* clear authorization. No automatic option selection.
- **Source register:** [W1_SOURCE_PRESERVATION_REGISTER_2026-11-17.md](W1_SOURCE_PRESERVATION_REGISTER_2026-11-17.md); pin the exact primary artifact and external references at the time of any later submission.

## 2. What is already established (and exactly at which scope)?

| Work | Actual evidence and scope | Paper wording permitted | Forbidden promotion |
| --- | --- | --- | --- |
| Original 16 fixtures | A1, author-defined labels; 4/16 deliberately weak storage baseline vs 16/16 gate | "On sixteen constructed cases, the rules matched the co-designed labels at the observed counts." | Independent accuracy, realistic baseline superiority, zero false-positive rate |
| 5 original test modules | Historical 280-case selected local re-run | "The selected deterministic tests passed in the stated pinned environment." | All regressions / native custody / production |
| Nov17 negative cases | [results](W1_SENSITIVITY_RESULTS_2026-11-17.json): 16 development rows, 3 intentionally constructed false-completeness rows with CONDITIONAL, 192 order permutations; [test log](W1_SENSITIVITY_TESTLOG_2026-11-17.txt): 15 tests; [CI receipt](W1_CI_RED_GREEN_RECEIPT_2026-11-17.md): 4 green matrix jobs after Windows CRLF fix | "A reported graph can be indistinguishable under different latent laboratory dependence states; classifier output is correspondingly the same." | Real-world attack success rate / actual witness separation / blinded validation |
| Authorship/source integrity | W1 source blob pin, original GitHub spot-check, SHA256SUMS and CI URLs | "The declared byte-image and selected tests are reproducible under stated assumptions." | Authorship, clock integrity, no hidden controller, trusted third-party custody |
| Theories and literature | [register](W1_SOURCE_PRESERVATION_REGISTER_2026-11-17.md), primary DOI/arXiv/standards | "Related research distinguishes source dependence, secure provenance, graph tampering and measurement validity." | 'World's first' or 'previous research proves Ario secure' |

## 3. Scientific improvements before any new manuscript submission

### Claim and novelty
- Retitle/position as **a transparent source-pinned input-trust sensitivity study** of a specific experimental evaluator, not a broad security guarantee. Avoid "first", "novel discovery of Sybil", "established independent provenance", and categorical claims about AI consciousness or agency.
- Formally distinguish: (a) number of reports; (b) distinct storage objects; (c) underlying evidence roots; (d) capture/administrative controllers; (e) authenticated custody; (f) informative content under correlated extraction. Shared roots need not imply zero incremental information; distinct reports do not mint independent roots.

### Stronger methodology
- Freeze the **observable input schema** `O(L)` and latent truth `L`. Define the equivalence pair explicitly: `L_sep != L_hidden`, `O(L_sep) == O(L_hidden)`, therefore every deterministic `f` on just `O` returns the same verdict for both.
- State the theorem's scope: a logical fact *conditional on identical inputs* in the synthetic model; no algorithm can infer absent hidden information from that input without extra assumptions or evidence. Not a theorem of real attack capability.
- Require positive reported shared-control/source controls, honest `UNKNOWN` controls, plus **no new authority promotion** of `CONDITIONAL`.
- Include a **nontrivial matched baseline** (an independently sourced provenance check or fully specified rule with equivalent observation privileges) before presenting a credible comparative performance claim. Preserve the original weak baseline as didactic, not competitive.
- Build genuinely new challenge families; separate developer cases from held-out cases, disclose what reviewers/model assistants saw, explicitly prevent expected labels from leaking into filenames/fixtures/code.
- Standardize per-axis labels and outcomes. Counts for `UNKNOWN` must be reported alongside wrong positives/wrong negatives; abstention is not automatically success. Exact denominator: logical family vs deterministic permutations vs separately generated trials.
- Avoid adopting an unverifiable "source independence" oracle. The *external* truth of source/controller cannot be inferred from graph author assertions, trusted strings, hashes or more files.

### Reproduction and validity
- Pin all Git blobs and primary paper editions; verify implementation source by readback from GitHub, not only internal checksums.
- Reproduce work with exact commands in `W1_SENSITIVITY_REPRODUCE_2026-11-17.md`; freeze code commit, OS/Python, result JSON hashes, stdout/stderr, and red-to-green CI URLs. Native CI 4/4 demonstrates the named author-constructed tests only.
- Demand test-harness mutation negatives: UNKNOWN->CONDITIONAL, dropped shared-root edge, duplicated artifact, inconsistent completeness flags, alias collision, source loader TOCTOU, LF/CRLF; treat inability to reproduce as a blocking finding rather than a silently successful run.
- If actual masked independent data become available later, preregister an adjudication and freeze protocol before exposure. The current [W1-B protocol](W1_BLIND_INDEPENDENT_CHALLENGE_PROTOCOL_V0_1.md) is only a draft; cannot claim sealed independent blinding while labels and code are visible to all reviewers.

### Ethics and rights
- Distinguish original human author from AI-assisted drafting, test harness, retrieval and review. Claude / Trae reviews are **AI-assisted critiques** and not human editorial peer review, third-party custody, or independent experimental replication.
- Preserve copyright and project code licenses. Do not upload entire copyrighted third-party papers; archive primary URLs, metadata, selected notes and a limitation matrix.
- No DOI assignment by the potential journal is established; existing SSRN DOI must be attributed accurately to SSRN.
- No manuscript submission/revision to publishers, no editorial contact and no authorization to publish a changed text is created by this document.

## 4. Required review outputs and closure criteria

| Gate | Ready when | Current state |
| --- | --- | --- |
| G0 Identity | Current online SSRN PDF, A1 archive PDF and A2 author-review draft are differentiated by exact byte hash and a version decision. | **PARTIAL** — A1 archived text exists; online SSRN current PDF not freshly rehashed here. |
| G1 Primary citations | Each scientific proposition linked to primary exact version/DOI/page; peer-review status distinguished from arXiv preprints. | **PARTIAL** — external source register and original paper links pinned, full citation audit pending. |
| G2 Transparent methods | Complete source pin, fixture generator, evaluation wiring, red/green notes and all raw outputs archived and replayable. | **LOCAL_PASS + CI_SCOPE_PASS** — study-specific tests only; challenge reviewer must reproduce independently. |
| G3 Competing hypotheses | At least one serious alternative explanation / counterexample recorded for each key success claim, with author rebuttal. | **PENDING** — proposed for Claude; not yet received. |
| G4 Adversarial code review | Separate Trae report with exact bytes/commands, at least one mutation family and verified negative controls. | **PENDING** — no report received yet. |
| G5 Independence | An actually independent source / custodian and blinded holdout with sealed oracle and reproducible score. | **NOT_ESTABLISHED** — no human independent investigator or attested custody. Does not block publication of a clearly *exploratory* paper if honestly disclosed; blocks independent-performance claims. |
| G6 Research ethics | Author inspects/corrects AI assistance, cites exact sources, and checks meaningful scope/rights of any publication package. | **PENDING** for any new/updated edition. |
| G7 Version/publication | Old article remains intact, journal is not sent changed text without explicit author instruction, final manuscript contains only supported claims. | **HOLD** pending version choice and review. |

## 5. Suggested section-level next manuscript structure (new version only)

1. Title + honest abstract: research hypothesis, 16-case historical didactic result, new input-trust negative cases, limitations and no field inference.
2. Introduction: copy count vs evidence roots vs authenticated control; practical motivation, scope and testable research question.
3. Prior work and originality matrix: Pan (2023), Faraj (2025), Sang (2025 preprint), Bara (2026 preprint), Li/Fan/Zhuang (2026 preprint), W3C, RFC 9162, NIST AU-9; explicitly delimit overlapping claims.
4. Threat model: source actor, graph reporter, graph collector, reviewer, trusted/untrusted inputs, adversarial omissions, observation equivalence.
5. Methods and auditability: pinned TB-003 SHA, authored fixtures, comparator code, positive controls, false completeness, oracle leakage, reproducible commands, raw outputs.
6. Results: original 16-case pedagogical baseline; new sixteen **distinct development** conditions (not conflated with old 16); 3 hidden cases, 192 permutations, unit tests and CI matrix with no inflated denominator.
7. Discussion: why 3/3 false-completeness is neither production failure rate nor proof of any authenticated witness; what a trusted capture chain needs.
8. Limitations and open questions: withheld independent oracle, nontrivial baseline, untrusted graph, lack of real custody and independent peer review.
9. Ethics/reproducibility, AI declaration, code/data, version history, rights and precise bibliography.
10. Appendices: positive/negative test matrix, full raw JSON hash, shell commands, Windows CRLF correction, failed-attempt log, proposed sealed-holdout protocol.

**Owner-readable status (فارسی):** منابع اصلی و لینک ثابت نسخه‌ها در گیت‌هاب ثبت شد. آزمایش فعلی توسعه‌ای و قابل‌بازتولید است، اما هنوز آزمایش کور مستقل یا شاهد واقعی نداریم. کلاود و Trae برای نقد علمی و شکستن آزمون‌ها دو مأموریت جداگانه دارند؛ تا وقتی گزارش واقعی‌شان نرسیده ادعای بازبینی انجام‌شده نمی‌کنیم. مقالهٔ قبلی و شرایط انتشارش دست‌نخورده می‌ماند؛ نسخهٔ جدید فقط در شاخهٔ پژوهشی آماده می‌شود.

**Next actionable step:** dispatch [separate review briefs](W1_CLAUDE_TRAE_SEPARATE_REVIEW_BRIEFS_2026-11-17.md), archive verbatim reports when actually received, adjudicate findings, then prepare a dated standalone follow-up draft and reproduce evidence. Not a future-work promise; these are explicit remaining gates.
