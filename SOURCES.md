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

## Update 2026-10-15 (website-only; gh-pages index.html and SOURCES.md)

Sources read at `main` c4af4d4 (Merge PR #80), before this update; upstream gh-pages was at 895532f.

| Added or changed | Source |
| --- | --- |
| Status wording (implementation with automated tests; test-scope limit) | README.md → Current Status |
| M0 Evidence Ancestry Guard v0.1, status as stated in its own spec | implementation/M0_EVIDENCE_ANCESTRY_GUARD_SPEC_V0_1.md (header) |
| Book editions 0.4, 0.3, 0.2 with DOIs, page counts, credits, non-claims | papers/README.md; papers/being-with-the-other/v0.4/README.md; papers/being-with-the-other/v0.3/README.md |
| Related records 23376521 and 23375401 | papers/README.md; papers/being-with-the-other/v0.4/README.md |

Verification limits: Zenodo record pages were not accessible to this reviewer (HTTP 429), so DOIs, titles, versions and dates are repository-reported and not independently confirmed on Zenodo. The content of records 23376521 and 23375401 is deliberately not described, since the repository states it was not inspected. The Evidence Ancestry Guard is described only by the status line in its spec.
Persian date for edition 0.4 (22 Mehr 1405) is a calendar conversion of the repository's 14 October 2026.
