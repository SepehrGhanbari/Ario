# Ario explainer demo (synthetic, standalone) — 2026-11-08

**Status: `RESEARCH_DEMO / DRAFT / NOT_DEPLOYED`.** Owner-authorized draft addressing [#104](https://github.com/SepehrGhanbari/Ario/issues/104) (public explainer demo). This folder is a proposal for review, not an admission, release, or deployment.

## Files
- `index.html` — self-contained bilingual (FA default RTL / EN toggle) static page. Zero external requests, no CDN, no cookies, no backend, no tracking, no user text input. All dynamic DOM is built with `textContent`; the only `innerHTML` use is a static, author-controlled footer string.
- `README.md` — this file.

## What the demo shows (hand-authored teaching labels, not engine verdicts)
1. `MEMORY ≠ TRUTH` — the self-citing refund → `UNSUPPORTED`.
2. `CLAIM ≠ PROOF` and independence — ten copies of one rumor → still one origin → `UNKNOWN`.
3. `REVISION ≠ ERASURE` — mistaken permission, corrected with preserved history; erase-vs-revise comparison view.
Plus a legend of epistemic states (UNKNOWN, UNSUPPORTED, CONTRADICTED, CONTESTED, REVISED).

## What this does NOT claim
- NOT the M0 engine, NOT a verification oracle, NOT a user-facing AI companion.
- Verdict tokens on the page are teaching labels authored by hand; they are not outputs of `implementation/core`.
- No new epistemic semantics: the page paraphrases the repository README. If any sentence conflicts with the README or the specs, the README/specs win and this page is wrong.
- NOT deployed: `docs/` is outside the `website/` deploy root; nothing goes live by merging this draft without a separate explicit decision.

## Validation record
- Performed (author-side, static): hand review of the HTML/CSS/JS source; confirmed no external network references; confirmed no user text input anywhere; interactive states render via `textContent` assignments.
- `NOT_EXECUTED`: the page was not rendered in a browser by the authoring session; no accessibility audit; no hosted-CI verdict claimed for this page.
- Suggested reviewer checks: open `index.html` locally in Firefox and Chromium; toggle FA/EN; keyboard-only pass; confirm zero outbound requests in the devtools network tab; check the Persian text against the README's bilingual wording.

## Provenance
Drafted by Vibe (GLM via Mistral Vibe) in an owner-authorized session, 2026-11-08, after reading the repository README, AGENTS.md, GOVERNANCE.md and issue #104. Persian text authored by GLM; independent Persian review is requested. `OWNER_SIGNER=HOLD` · `M0_ADMISSION=NOT_EVALUATED` · `NOT_MERGED`.