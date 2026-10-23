# Ario — Book Publication Release Protocol (v1)

**Status:** Public operational checklist, not a book release or publication approval.
**Scope:** Future author-approved public editions of *Being With the Other* (Persian/English), Zenodo, GitHub, the official site and connected social publishing services.
**Baseline at drafting (2026-10-23):** the latest author-published book tracked in the repository is edition **0.4**, DOI [10.5281/zenodo.23376577](https://doi.org/10.5281/zenodo.23376577). The separate [AI-readable research companion](https://doi.org/10.5281/zenodo.23441596) is **not** a new book edition or an independent authenticity certificate.

## Non-negotiable gates

- [ ] Identify the exact intended **new edition/version**, date, human author, editorial contributors and reviewed *public* source files. Do not invent a title, DOI, release date, peer-review claim or file version.
- [ ] The author has designated an exact final public release set. Draft, **PRIVATE** historical audits, raw conversations, personal/family material, withheld dream details, unreleased signer/security evidence and credentials are excluded by default; treat uncertain disclosure permission as **HOLD**.
- [ ] Compare the public release against the preserved previous edition. No silent alteration of v0.2/v0.3/v0.4 files, commits, DOI records or historical evidence. New edition means a new versioned directory, with an explicit changelog.
- [ ] All significant historical or philosophical claims distinguish **documented statement**, **inference**, **contested evidence**, **UNKNOWN** and **aspiration**. A cited repository record does not authenticate upstream evidence. Do not present machine consciousness, religious propositions, AI authorship or human private experience as established by tests.
- [ ] Check third-party quotations, media, privacy, permissions and copyright. Code MIT licensing does **not** automatically govern book text; use the edition's actually authorized book license (existing editions: CC BY 4.0 for original text).
- [ ] Keep M0, signer, frozen evidence, source-authentication authority, CPU guards, issues #75/#81 and draft PR #91 outside this editorial release. A book is not a security approval.

## Stage A — Freeze and verify the public book artifacts

- [ ] Record exactly which **FA/EN PDF, DOCX, Markdown and metadata files** are approved for public release; omitted formats remain explicitly omitted, not silently fabricated.
- [ ] Render/inspect both languages, including right-to-left layout, fonts, headings, page numbering, citations, accessible text, figure/QR destinations and visible unresolved markers.
- [ ] Check chapter/appendix counts and compare prior version text. Maintain an evidence-vs-interpretation ledger for substantive new historical claims, and record any source not independently accessible.
- [ ] Compute SHA-256 of every final public file and a versioned manifest after freezing bytes. Preserve reviewer findings and failed checks in a separate **private** work area until screened for publication.
- [ ] Keep `PUBLIC`, `PRIVATE`, `DESIGN_ONLY`, `NOT_EVALUATED` and `UNKNOWN` labels unambiguous.

## Stage B — Zenodo deposit (only after Stage A)

- [ ] Select the right book record/version relation based on actual Zenodo metadata; **do not reuse** the companion DOI as the book DOI.
- [ ] Prepare verified title/subtitle, creators, AI editorial credit as an editorial role rather than human authorship, date, languages, description, keywords, license, related identifiers and version history.
- [ ] Upload only the frozen **public** files and manifest; inspect them in the Zenodo preview before final publication.
- [ ] Publish only with author-approved final content. Retrieve the **actual public DOI** after a successful deposit; verify that it resolves and shows the correct edition/files and metadata.
- [ ] If Zenodo fails or remains draft, stop outward claims that a new edition is published; keep the old official edition visible.

## Stage C — GitHub (only after confirmed final public edition)

- [ ] Create a **new append-only** edition directory under `papers/being-with-the-other/` matching the actual version (no placeholder version pushed in advance). Preserve old directories.
- [ ] Include public editions/formats that were approved, `README.md`, edition-specific citation metadata, release notes/changelog and exact checksums where practical.
- [ ] In a narrowly scoped branch/PR, update the publication listings in `papers/README.md` and root `README.md` to the **verified** new DOI while retaining older records, license distinctions and evidence limits.
- [ ] Review file list, privacy screening, Git diff, hashes, filenames, link targets and exact-head checks; no unrelated staged changes, rewrite or unreviewed lab work.
- [ ] Merge only once the branch is safe and checks pass. Record PR, merged commit SHA, public file links and verification. Never claim a merge or a published PDF before verifying GitHub's result.

## Stage D — Official bilingual website and mirrors

- [ ] Preserve the deployed **full source/configuration** before touching either site. The [Vercel site](https://ario-research-independent.vercel.app/) and [GitHub Pages mirror](https://sepehrghanbari.github.io/Ario/) may have different deploy sources; a GitHub merge is **not** proof of a Vercel deployment.
- [ ] Update publication/reading links **in both English and Persian** after the new DOI resolves; preserve the existing companion entry, previous editions and public research content.
- [ ] Inspect current deployed `research.html` and other site assets even if not mirrored in GitHub before any deployment. Avoid HTML-only partial redeployment that drops healthy files.
- [ ] When inline CSS/JavaScript changes, rederive actual CSP SHA-256 hashes from final deployed bytes; preserve strict CSP and security headers. Never use `unsafe-inline` as a shortcut.
- [ ] Preview and browser-check layout, FA RTL text, navigation, DOI links, status labels and security headers. Publish the tested artifact with a documented rollback path; independently verify production alias and mirror after deployment.

## Stage E — Metricool / connected social accounts

- [ ] Prepare **edition-specific** captions and media with correct DOI, language, author/editor roles and verified claims. QR must encode the **actual new edition DOI**, not the older research companion unless explicitly promoted as companion.
- [ ] Recheck the currently connected Metricool networks and their provider-specific requirements at execution time. As of this protocol, YouTube, TikTok, Pinterest and Bluesky are connected; Twitch connectivity alone does **not** imply video-post scheduling support.
- [ ] For video, attach a real reachable file (or supported file-picker reference); link-only or private Drive URLs do not prove uploadability. Pinterest requires a valid board ID (previously Ario AI Research).
- [ ] Observe each platform's required AI/synthetic-content flags, title, audience, privacy, length and copy limits. Do not silently bypass a Bluesky video 401/email-verification error; use a plainly described **link post** only when appropriate.
- [ ] Schedule with explicit locale/time zone and `autoPublish=true` only after the new DOI and landing page are actually live. Check for duplicates before scheduling.
- [ ] Verify **provider-level** `PUBLISHED` status and actual public URL for each network. `PENDING`, `ERROR` and `SCHEDULED` are not publication; record their causes and retry only safely.

## Stage F — Release evidence and correction

- [ ] Publish a succinct status record: edition/version, actual Zenodo DOI and published UTC time, public-file hashes, GitHub PR and merge SHA, primary and mirror site URLs, and provider-level Metricool URLs/statuses.
- [ ] Re-check that public copies contain no inadvertently exposed private material; for any suspected exposure stop further syndication, record it privately and escalate to the author before corrective action.
- [ ] Preserve previous edition references and an append-only correction log. Explain any retraction or correction without silently rewriting history.
- [ ] Keep known limitations visible: DOI ≠ peer review; citation ≠ source authenticity; signature ≠ proposition truth; test pass ≠ ontological proof.

## Operator handoff (compact)

| Field | Value required before marking release complete |
| --- | --- |
| Public book edition | Version and author-approved release manifest |
| Zenodo | Verified book DOI, metadata, public files, hashes |
| GitHub | Versioned new folder, PR URL, merged SHA, exact public asset links |
| Websites | Vercel production + Pages mirror checked; CSP and rollback verified |
| Social publishing | Network/provider-specific `PUBLISHED` links and exceptions |
| Remaining concerns | Explicit `UNKNOWN`, `NOT_EVALUATED`, or blocker log |

**No stage may silently mark a later stage complete.** This protocol is documentation only: it creates no deployment, credentials, automatic publication authority, or claims of completed review.
