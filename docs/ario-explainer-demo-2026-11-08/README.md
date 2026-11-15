# Ario explainer demo (synthetic, standalone) — 2026-11-08

**Status: `RESEARCH_DEMO / DRAFT / NOT_DEPLOYED`.** Owner-authorized draft addressing [#104](https://github.com/SepehrGhanbari/Ario/issues/104) (public explainer demo). This folder is a proposal for review, not an admission, release, or deployment.

## Files
- `index.html` — self-contained bilingual (FA default RTL / EN toggle) static page. No automatic network requests initiated by the demo; no CDN, cookies, backend, tracking or user text input. The two GitHub footer hyperlinks make outbound requests **only if clicked**. All dynamic DOM is built with `textContent`; the only `innerHTML` use is a static, author-controlled footer string.
- `README.md` — this file.

## What the demo shows (hand-authored teaching labels, not engine verdicts)
1. `MEMORY ≠ TRUTH` — the self-citing refund → `UNSUPPORTED`.
2. `CLAIM ≠ PROOF` and independence — ten copies of one rumor → still one origin → `UNKNOWN`.
3. `REVISION ≠ ERASURE` — mistaken permission, corrected with preserved history; erase-vs-revise comparison view.
4. **New two-mode evidence exercise (2026-11-15):** same hypothetical request `REQ-204`, same time, one attributed opposing record. **Accepted independent opposing evidence → `CONTRADICTED`**; materially disputed authenticity/interpretation → **`CONTESTED`**. Switching the evidence mode and changing FA/EN preserves the selected mode and exposes button state through `aria-pressed`. This is **hardcoded teaching output**, not a live classification algorithm or M0 engine result.
Plus a legend of epistemic states (UNKNOWN, UNSUPPORTED, CONTRADICTED, CONTESTED, REVISED).

## What this does NOT claim
- NOT the M0 engine, NOT a verification oracle, NOT a user-facing AI companion.
- Verdict tokens on the page are teaching labels authored by hand; they are not outputs of `implementation/core`.
- No new epistemic semantics: the page paraphrases the repository README. If any sentence conflicts with the README or the specs, the README/specs win and this page is wrong.
- NOT deployed: `docs/` is outside the `website/` deploy root; nothing goes live by merging this draft without a separate explicit decision.

## Validation record
- Performed (author-side, static): hand review of the HTML/CSS/JS source; confirmed no automatically fetched external resources in the source; two ordinary GitHub hyperlinks exist and navigate only when clicked; confirmed no user text input; user-facing dynamic scenario content renders via `textContent`.
- Original authoring session: `NOT_EXECUTED` (no browser, screen-reader or Lighthouse audit). Follow-up correction and any observed test evidence must be recorded against the exact revised commit/PR; a passing Python CI job alone does not constitute a browser or screen-reader audit.
- Suggested reviewer checks: open `index.html` locally in Firefox and Chromium; toggle FA/EN without losing the selected answer or revision mode; test keyboard navigation, evidence-mode toggle, and screen-reader announcements of answer/evidence feedback, `aria-pressed` and old-entry labels; inspect the network tab for **zero automatic** outbound requests (manual GitHub link clicks are expected to navigate); check the Persian definitions and the corresponding Nov 3 / ۱۲ آبان ۱۴۰۵ date.

## Provenance
Drafted by Vibe (GLM via Mistral Vibe) in an owner-authorized session, 2026-11-08, after reading the repository README, AGENTS.md, GOVERNANCE.md and issue #104. Persian text originally authored by GLM; a separate independent Persian-language review remains requested. `OWNER_SIGNER=HOLD` · `M0_ADMISSION=NOT_EVALUATED` · `NOT_MERGED`.