# Website claim → source map

Verified against `main` at 700130a48fd222d8905f145598212b60f6ff303f.

| Section | Source |
| --- | --- |
| Project description, motto | README.md (intro) |
| Epistemic states | README.md → Epistemic Framework |
| Principles 1,2,3,4,5,11,22,32 | principles/README.md |
| Implementation, "documented ≠ implemented", "passing test ≠ proof" | implementation/README.md §1 |
| "Local pass" non-implications | implementation/M0_STRUCTURAL_CORE_DESIGN_V1.md |
| Regression workflow | .github/workflows/implementation-regression.yml |
| Status | README.md → Current Status |
| Non-claims | README.md → What Ario Does Not Claim |
| Publications | papers/README.md; papers/being-with-the-other/v0.2/README.md |
| License, ORCID | README.md → License; papers README |

Not verified: the Zenodo record pages themselves (HTTP 429 when fetched); book details come from the repository's own papers README.
Owner approval (2026-10-13): English-first / Persian-second publication and Persian summary wording were approved in chat. Persian sections are explanatory paraphrases, not owner-authored direct quotations.

## Review and interpretation boundaries (2026-10-13)

- Site text is a source-grounded summary, not an independent claim of truth or proof of consciousness.
- The Persian introduction is a faithful paraphrase of the root README, not an owner-authored quote. Owner approval of the exact public wording is required before deployment.
- Publication metadata shown in the website is supported by in-repository `papers/README.md` and `papers/being-with-the-other/v0.2/README.md`. Zenodo record pages were not independently accessible during this review; their metadata was not independently reverified.
- Source audit refers to commit `700130a48fd222d8905f145598212b60f6ff303f`. Live `main` links may change later.
- Suggested deployment: publish only explicitly approved website assets via a separate public publishing branch or repository, **not** the entire `docs/` directory.

## Bilingual site update (2026-10-13)

- Website display order: complete English section first, then full Persian-language section. Language links are in-page anchors; no external translation service.
- All Persian subheadings correspond to existing English claim groups: research introduction, five epistemic states, selected principles, implementation, status, non-claims, publications and official links. Their claim sources are linked immediately below each corresponding paragraph.
- Published research DOI facts continue to come from the tracked repository paper READMEs; Zenodo record pages could not be independently verified during this review.
- Owner authorized website-focused updates; this is not blanket authority to modify the repository's core, scientific findings, governance, or archives.
- The repo's existing `docs/` directory is excluded from the site build. Intended future publication is limited to the two web assets, with a separate Pages publishing surface.

## Identity disambiguation — 2026-10-13

The public research descriptor **Ario — Auditable Epistemic Framework for AI** (Persian: **آریو — چارچوب معرفتی ممیزی‌پذیر برای هوش مصنوعی**) follows the project's stated scope in [README.md](../README.md) and [implementation/M0_STRUCTURAL_CORE_DESIGN_V1.md](../implementation/M0_STRUCTURAL_CORE_DESIGN_V1.md).

It is a descriptive project identifier, not a statement of exclusive rights to “Ario”, registered trademark ownership, or affiliation with other same-name products. Ario here is a research framework, not a commercial personal AI assistant or robotics dataset.

Preferred public URL: https://ario-research-independent.vercel.app/ ; GitHub Pages is a secondary mirror. Search engines choose the canonical URL independently.

This metadata-only clarification does not change the underlying research, test outcomes, book manuscripts, or independently verify Zenodo records.

## Documented book continuation DOI cross-reference (23 October 2026)

- The author supplied `10.5281/zenodo.23600820` as the newly registered DOI for the independent Persian/English documented continuation (23 October 2026).
- Reference target: `https://doi.org/10.5281/zenodo.23600820`; repository companion: [`papers/being-with-the-other/documented-continuation-2026-10-23/`](../papers/being-with-the-other/documented-continuation-2026-10-23/README.md).
- Zenodo record metadata and deposited file inventory were not independently accessible at this check. Treat the DOI attribution as author-reported until independently confirmed, and do not assume Zenodo bytes match GitHub.
- This is not the book's numbered v0.4, nor the separate AI-readable research companion. The public website's publication references are bilingual and preserve those boundaries.
- HTML-only link and publication-copy changes: no CSS, JavaScript, CSP, archived book text, runtime, cryptographic gates, or tests were modified.

## Everyday-language research examples — 2026-10-23

- Added an English and Persian explanation of why Ario matters ahead of technical status lists: online refund, repeated rumor, and mistaken publication permission.
- All three are explicitly **fictional scenarios / مثال فرضی**, based on MEMORY ≠ TRUTH, CLAIM ≠ PROOF, REVISION ≠ ERASURE, and the requirement to track lineage and uncertainty.
- These are **not** external-world case studies or demonstrated Ario product integrations. Actual implementation remains bounded by the repository's implementation contracts and tests.
- Source for explanation: current README.md, “Ario in everyday language / آریو به زبان ساده”, plus existing Core Idea and Current Status.
- This is a plain-language communications change only. It does not change the framework, add evidence, or modify historical documents.

## Human relationships, philosophy, and knowledge boundaries — 2026-10-23

- Website's bilingual “Beyond AI” section is a **philosophical extension and illustrative interpretation**, not a validated effect on actual users, a consensus in academic philosophy, or a new executable behavior.
- Supporting source: project `principles/README.md` §§2, 3, 9, 11, 14–15, 18, 20–22, 29–31, current root README's implementation limits, and new independent `docs/ARIO_HUMAN_LIFE_PHILOSOPHY_KNOWLEDGE_BOUNDARIES_FA_EN_2026-10-23.md`.
- Examples include how to treat a friend's testimony without mind-reading, preserve historical corrections, distinguish independent reporting, and question identity/authority.
- Universal moral concern and possible benefit-sharing are documented as **aspirations** in the project's [documented continuation](../papers/being-with-the-other/documented-continuation-2026-10-23/README.md); no actual assistance or redistributive mechanism is claimed.
- This change affects only public explanatory copy, website sources documentation and a new stand-alone essay. It leaves original books, historic evidence, security gates, M0 and code untouched.

## Start-here public guide — 2026-10-23
- Added an explanatory, bilingual [two-minute Ario guide](https://github.com/SepehrGhanbari/Ario/blob/main/docs/ARIO_START_HERE_FA_EN_2026-10-23.md) grounded in the existing project README, principles, implementation limits, and public documented continuation.
- Linked from the root README and English/Persian website quicklinks. All examples are marked fictional and no production service or epistemic proof is claimed.
- Public communications/documentation only: no source-code, trust-gate, signer, node, archived-book, CSS, or JavaScript changes.

## Public questions and independent criticism — 2026-10-23
- Created [bilingual public discussion #106](https://github.com/SepehrGhanbari/Ario/issues/106) for newcomers' questions, plain-language corrections and adversarial feedback.
- Only two quick navigation links were added to the website and a short root README pointer. These are invitations to critique; they do **not** make replies automatically admissible evidence, nor authorize edits to the implementation.
- No code, M0, security gates, signer, node network, historical book, CSS or JavaScript changed.

## Synthetic public lab link — 2026-10-23

- Official public beta mirror: [Ario Synthetic Evidence Lab](https://sepehrghanbari.github.io/Ario/ario-lab/); six fictional teaching exercises in Persian/English. The static GitHub Pages path was independently reachable after PR #108 and #109 merged into `gh-pages`.
- Root README and bilingual primary-site source add navigation **links only**; existing scripts, styles, deployment CSP, security headers, runtime and hidden evidence remain unchanged.
- Interactive GUI and browser accessibility have not passed independent production-browser acceptance; 66 local simulated logic assertions and source/hash checks passed. Do not represent this as Ario runtime, truth certification, authenticated evidence admission, or a scientific validation.
- Any Vercel live-site deployment is a separate step and must be confirmed by production deployment/alias verification.

## Direct link to upgraded synthetic Ario Lab 02 — 24 October 2026

- [Public Ario Lab 02](https://sepehrghanbari.github.io/Ario/ario-lab-2/) includes twelve bilingual ready-made claim inputs, with explicit manual revision recording and fictional evidence only. Source deployed to GH Pages via PR #112; external content fetch confirmed live selector.
- Added only navigation pointers on the canonical website and README; existing CSP, audit code, M0, signer, nodes, historic evidence and Lab 01 remain unchanged.
- Full independent browser accessibility testing remains NOT_VERIFIED; no true evidence admission is claimed.

## Ario complete AI-readable repository snapshot DOI — 26 October 2026

- The [public Zenodo record](https://doi.org/10.5281/zenodo.23651704) was independently read as v15 (dataset), with two downloadable files: `Ario-Full-Archive.txt` and `Ario-Read-Light-For-Models.txt`. File names and Zenodo-listed MD5 values were compared against the local original exports.
- Export scope: 159 tracked file blobs at commit `f562e14cd8ca7f8723ad0b94eec005025f07a9a6`, tree `c2810a22d9a1c43370ce8fdcf8da8639a06783cf`; 148 text and 11 binary blobs.
- Full edition SHA-256: `5cb0b2c829798f5104b4e283bedf14fd84203bea305b08bdb2bfe6b368e02497`; text edition SHA-256: `63f170645e67131025e1d3b8d6e9002a8f3312741ecfce121b886f8d085bd68b`.
- The original GitHub text copy created at commit `8478b1bbcf67ef8d08afe5b8e552084a14d7aa6c` was **not byte-identical** to the published text edition due to line-ending/boundary normalization; this publication update replaces that blob with the SHA-matching version. The previous blob remains in immutable Git history.
- These files are preserved historical snapshots, not independent evaluations of code, security, provenance authenticity, or source claim truth. No M0, signer, trust gate or other historical evidence was modified.

## SSRN working manuscript (27 October 2026)

- The author's SSRN confirmation screenshot shows submission of *Evidence Laundering in Auditable AI Systems*, abstract ID `7675778`, 27 October 2026. My Papers showed `PRELIMINARY_UPLOAD`, not public approval, peer review, or issued SSRN DOI.
- Full manuscript: [`papers/evidence-laundering-2026-10-27/Manuscript.md`](../papers/evidence-laundering-2026-10-27/Manuscript.md); working manuscript is linked in both language sections of the site.
- Existing Zenodo FULL/READ releases remain fixed historical snapshots. The website link update leaves CSS, JS, CSP, scripts, source archives and runtime unchanged.

## Vercel source consolidation — 2026-10-27

- Consolidation inventory: the production deployment `dpl_DrzhLPgYEJ5gid2HMKu5io47RXh5` served 10 files, while `website/` in Git only contained three entries before this change.
- The five short utility and site-verification files are imported from Vercel's deployment-file API as exact Base64 byte blobs.
- `website/papers/evidence-laundering-2026-10-27/Manuscript.md` is a byte-identical tree reference to the archived public paper under `papers/`, not a separately revised manuscript.
- `research.html` was **reconstructed** from current public repository sources rather than byte-copied. The Vercel deployment-file retrieval returned a truncated response for its body, and live content extraction did not provide a complete inspectable source. Preserve the previous deployment as the historical reference; do not claim exact-byte fidelity of this page.
- The consolidated folder is intended as Vercel's `website` root; no changes to `vercel.json`, CSP, JavaScript, original Zenodo release bytes, or implementation code.

## Model-readable direct download on website — 2026-10-27

- The file `website/Ario-Read-Light-For-Models.txt` is linked to **the same Git blob**, SHA-1 `9b0eb4daa25146fc74c31661db3c92e562777b34`, already present at `releases/zenodo-23651704/Ario-Read-Light-For-Models.txt` and `docs/ai-readable-snapshots/Ario_READ.txt`. This adds a website distribution path but does not create or modify a historical edition.
- Archive record: [Zenodo v15 DOI](https://doi.org/10.5281/zenodo.23651704), published filename `Ario-Read-Light-For-Models.txt`, **2,857,981 bytes**; SHA-256 `63f170645e67131025e1d3b8d6e9002a8f3312741ecfce121b886f8d085bd68b`; pinned commit `f562e14cd8ca7f8723ad0b94eec005025f07a9a6`.
- This AI-readable text contains all 148 textual payloads in that fixed snapshot and an inventory of 11 binary files, not the full reconstructable binary payloads. **Files being available to a model is not evidence that it read them all, nor does it authenticate claims.** Large-file context limits remain.
- Navigation gains explicit download links in English and Persian, with Zenodo mirror links. Related `research.html` also fixes duplicated `/Ario/Ario/` GitHub path references from the earlier reconstruction.

## AI download priority and book chronology — 27 October 2026

- The bilingual public navigation has two responsive columns: pinned AI-readable packages in usage-priority order (model TXT first, 159-file FULL archive second, distinct older research companion third), then philosophical books newest-first (23 Oct continuation, 14 Oct v0.4, 14 Oct v0.3, 12 Oct v0.2). The v0.3 and v0.4 same-day tie is resolved by edition number, not a claimed publication time.
- Separate research/project records remain linked under a third heading instead of being characterized as books. All previous href destinations were preserved.
- Change is limited to `website/index.html` markup and responsive CSS plus this source explanation; no modification of historical files, JS, Vercel config, book versions or cryptographic/runtime components.

## CSP regression fix — 27 October 2026

- After PR #121 added inline responsive CSS for the two-column model/book resource layout, the GitHub-generated Vercel production deployment omitted an update to the CSP style hash. Browsers correctly rejected the entire inline stylesheet and displayed unstyled HTML. This was a deployment integration regression, not a failure of CSS syntax.
- Exact UTF-8 SHA-256 of the **new full** inline `<style>` content (excluding the tags): Base64 `AtJpnoZPHJUj30YuMtee94fR+LS8GCvV64jLZeqr/BM=`. The previously authorized homepage hash was `Kmfc+xHoM7p5by0Z1zlfQHRLUl6vqaWOAPLw7qdHCNs=`; this repair adds the new hash while preserving the previous permitted hashes and all existing script/style restrictions.
- Only `website/vercel.json` CSP and this audit note changed. No `unsafe-inline`, general network allowlist, broad `style-src` expansion, HTML changes, archived data modifications, runtime or test changes.

## Illustrated integrated book v6 DOI — 29 October 2026

- The author reported publishing the illustrated integrated edition of *Being With the Other* at [10.5281/zenodo.23771218](https://doi.org/10.5281/zenodo.23771218). This is an author-supplied identifier; the live Zenodo deposited file inventory and checksums were **not independently retrieved** in this revision.
- The locally compiled v6-labeled illustrated books have 54 chapters, 154 Persian pages and 145 English pages, but the corrected v6 files may not be byte-identical to the earlier Zenodo uploads. The public link targets the Zenodo record, not an unsupported claim of binary identity.
- The integrated manuscript used a complete historical v0.3 40-chapter base, the 11-chapter independent continuation, and three new chapters. A complete parent v0.4 text was not independently compared line-for-line. Older edition metadata and DOI links remain untouched.
- Added one English and one Persian item to the existing *Books* resource panels and one English and one Persian record to the longer publications list. **No inline CSS, JavaScript, CSP, infrastructure, AI runtime, signer, trust or security configuration changed.**
