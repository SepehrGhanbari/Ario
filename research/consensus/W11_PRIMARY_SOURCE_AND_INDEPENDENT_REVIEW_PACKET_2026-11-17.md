# W11 independent review packet — temporal memory provenance and action-origin non-promotion

**Date:** 2026-11-17  
**Disposition:** `RESEARCH_ONLY / REVIEW_REQUESTED_NOT_YET_PERFORMED / 36 SELF-AUTHORED SYNTHETIC CONTROLS / NO_REAL_AUTHORIZATION / DRAFT_HOLD`.  
**Task:** Review the **primary source texts**, compare explicit claims to pinned Ario code, and independently critique the synthetic test before anyone treats its output as proof of Ario security. No core merge, no owner decision, no signer/trust activation.

## For the owner — فارسی، فقط جمع‌بندی

آزمایش W11 نشان داد که **در یک شبیه‌ساز مستقل از هستهٔ آریو**، یک پیشنهاد آلوده با چند بار بازیابی، بازنویسی یا ثبت در تاریخچه، خودبه‌خود مجوزِ اقدام نمی‌شود. مجوز مصنوعیِ مستقل باید دقیقاً عملیات، مخاطب، داده و محدوده را مشخص کند؛ در آن حالت هم نتیجه فقط «قابل بررسی در دروازهٔ جدا» است، نه اجرای واقعی. **۳۶ سناریوی ساخت خودِ ما مطابق انتظار شدند؛ هنوز هیچ بازبین مستقل، کاربر واقعی، مدل زبانی واقعی یا ابزار اجرایی وارد آزمون نشده است.** برای همین لینک مقاله‌ها، سورس اجراشده، نقایص احتمالی و پرسش‌های لازم را اینجا گذاشته‌ایم تا دیگران بتوانند بررسی کنند؛ خود این سند بازبینی مستقل نیست.

## A. Source-of-truth manifest for reviewers (full original paper stays with publisher)

| # | Original external source and exact part read | What that paper actually supports | Critical limitations / reviewer checks |
| --- | --- | --- | --- |
| S1 | [SARA, Guo et al., *When Tool Outputs Become Commands*, arXiv:2608.27146v1](https://arxiv.org/html/2608.27146), §§2–4: `Action Induction`, `No-History-Promotion`, `F_t` action origins, `H_t` audited history, and Table 3 ablations. Original in-body passages retrieved 17 Nov via Firecrawl | An action-inducing string can remain linked to an untrusted origin even when the same value later appears in successful history; user authorization is a **separate** root. Author-reported NHP ablation indicates attack-success deterioration without that guard | **PREPRINT / AUTHOR-REPORTED**. Do not infer independent memory-custody, external signatures, real Ario execution, or that history never has any valid task-relative evidence. Independently recheck Table 3 denominators and whether the paper's `H_t` uses genuinely audited calls |
| S2 | [CaMeL, Debenedetti et al., *Defeating Prompt Injections by Design*, arXiv:2503.18813v2](https://arxiv.org/html/2503.18813), §3 threat assumptions, §3.1 explicit non-goals, §9.2 declassification and §9.3 residual attacks. Original sections retrieved 17 Nov via Firecrawl | Distinguishes privileged control from untrusted data and scopes capability-controlled effects. It **explicitly assumes the user's initial request is trusted and memory is not previously compromised** | Original authors explicitly do **not** claim that all text-to-text or phishing-like content harms are blocked, and warn about user-fatigue/side channels. Any claim “CaMeL proves Ario's memory safe” is **not supported**. Paper numbers and version must be checked, not borrowed from older copies |
| S3 | [MemoryGraft, Srivastava & He, arXiv:2512.16962](https://arxiv.org/abs/2512.16962), §§3.3–4.4 threat/retrieval/persistence, §8 limitations. Original sections retrieved via Firecrawl 17 Nov | Author experiments show under **specified** conditions that allegedly successful but poisoned experiences can enter persistent stores and later influence a MetaGPT agent | **PREPRINT / AUTHOR-REPORTED**. The authors name dependence on stored persistent memory, trusted retrieved examples, lexical/semantic retriever, absent provenance checking and executable documents; small handcrafted seeds and partial white-box access. W11 neither re-ran MetaGPT nor replicated their behavioral drift |
| S4 | [PACT, Fan et al., *The Granularity Mismatch in Agent Security*, arXiv:2605.11039](https://arxiv.org/html/2605.11039), §§3–4 and Appendix A. Original sections retrieved via Firecrawl 17 Nov; source PDF previously provided by owner | Tool-argument roles matter; data fields can include untrusted text, whereas recipient/target/control roles need trusted binding. The authors report **87.1%** role assignment and **77.4%** provenance inference in automated settings | **PREPRINT / AUTHOR-REPORTED**; the guarantee assumes correct labels/contracts, and the automatic provenance stage is imperfect. Text-content and tool-choice attacks lie partly outside their stated enforcement scope |
| S5 | [AgentDojo, NeurIPS 2024 Datasets & Benchmarks](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html), official proceedings | A source for a practical attack-vs-benign utility benchmark in tool agents | This venue is independently publishable primary benchmark documentation, **not** a review of Ario, and does not provide W11's hidden oracle or actual observed attack outcomes |

**Citation grades:** `PRIMARY_TEXT_READ` means that the original author manuscript/official proceedings was read; `AUTHOR_REPORTED_RESULT` still requires empirical replication. Neither means reviewer approval. No full copyrighted provider report, private Library PDF, original article, or proprietary code is redistributed in this PR.

## B. Pinned Ario source crosswalk — do not pretend modules are already integrated

| Project source | Pin / finding | Relation to W11 |
| --- | --- | --- |
| [Draft PR #210](https://github.com/SepehrGhanbari/Ario/pull/210), `implementation/core/source_monitoring.py` | HEAD `07068bdfa36abb29a3ce8e927077df3ffe02b0cf`; Git blob `b3b500ebc8736aa5475d117f508a769a39b78d6d`. W8 source-pinned synthetic run exposed `NOT_FOUND` + exit0 → `VERIFIED_EMPIRICAL` | W8 is a **separate** API semantics test, not a successful W11 attack on Ario |
| [Draft PR #210](https://github.com/SepehrGhanbari/Ario/pull/210), `memory_consolidation.py` and `prospective_memory.py` | Pinned W8 blobs `b131bab9047d0c579e6a0dda6c0ee26861ef0100`, `3991f38f4d6ed1b51c0753bec54dd66c446d9e25` | A toy `ACCEPTED → TRIGGERED` state transition in W8 was **not** a real external task invocation |
| [Main agent runtime](https://github.com/SepehrGhanbari/Ario/blob/b5455ecd869e9b37f17ebfc9e7bbfb5133797df6/implementation/ario_agent.py) | `main` snapshot commit `b5455ecd869e9b37f17ebfc9e7bbfb5133797df6`; source Git blob `8569a2c19949a868143f1e54f8592633888dd127`, includes allowlisted tools and a separate `execute_action` | **No direct W11 integration test**. Allowlisting a tool is not proof of source-origin authority checks on all argument values |
| [Main admission policy](https://github.com/SepehrGhanbari/Ario/blob/b5455ecd869e9b37f17ebfc9e7bbfb5133797df6/implementation/ADMISSION_REVIEW_POLICY_V0_1.md) | Git blob `68f0ffcc719cf2d80965ff50c3521be430cc8254` | Its current candidate ≠ admission protection is separate from action-origin tracking; W11 grants no admission |
| [Issue #216](https://github.com/SepehrGhanbari/Ario/issues/216), W8/W9/W10 documents | `DRAFT/HOLD`; immutable V1 + opt-in V2 sidecar is a **proposal** | A no-history-promotion requirement must be included in any future review **only with owner approval** |

## C. What was actually executed

[W11 runnable simulator](w11_temporal_origin_no_history_promotion_lab.js) and [complete 36-case output](W11_TEMPORAL_ORIGIN_RESULTS_2026-11-17.json) were generated from the **same JavaScript functions executed in an isolated V8 environment** and committed to the research branch. Exact public Git Blob IDs after reading back: simulator `63bde301e7f061945dbd2fb43954e817d2182fa6`, data `8950907e7c2c606493f1aa5806d0487957dc3e7d`.

**36 self-authored controls matched their own expected labels**, including **21 `DENY`, 3 `UNKNOWN`, 2 `DATA_ONLY`, 5 `ELIGIBLE_FOR_SEPARATE_GATE`**, and five structural/integrity controls: missing parents, invalid unparented rewrites, root deduplication, temporal order, and persistent original roots. Tests cover poisoned → retrieved → summarized → rewritten → history; false `SYSTEM`/user-approval text; grant mismatch and revocation; positive precise, fresh grant; and source snapshots. All `ELIGIBLE_FOR_SEPARATE_GATE` outputs still carry `authority=NOT_ESTABLISHED`, `grant_authenticated=false`, **zero external effects**.

**This is not a real authenticated provenance/authorization result.** Test harness issues BOTH origin types AND simulated grants; an attacker controlling that producer could forge the whole envelope. Root IDs are local labels, not independent sources. History is an immutable *in-memory research array*, not externally notarized evidence. The test does not feed actual Ario's `ario_agent.execute_action`, `SourceMonitoringGuard`, a model, the internet, or a real user ledger. There are no independently authored gold cases.

### Legitimate controls that must survive any design refinement

A source may be summarized read-only and remain `DATA_ONLY` without erasing it; a **new and separately authenticated, exact-scope user grant** should allow independent authorization review even when an old external suggestion contains the same string. Correct denial of all actions without a grant is not sufficient evidence of useful security: reviewers must check false denial, dynamic object binding and actual task completion.

## D. Exact reviewer assignments / falsifiers (unfulfilled until external reviewer comments)

Please do not mark any box complete just because this document exists. For each, require **source file + commit/blob + independent command or argument**, and return `CONFIRMED / REFUTED / UNKNOWN` with reason:

- [ ] **R1 — Bibliography:** read SARA original §4/§5 Table 3, CaMeL §3/§9, PACT Appendix A, MemoryGraft §3.3/§8 and record *exact* source version, DOI/arXiv, assumptions and author-reported vs reproduced metrics.
- [ ] **R2 — Source safety:** independently inspect W11 JS for hidden `ALLOW`, real action calls, network/file IO or mutating Ario code. It must be an isolated **no-effects** simulation.
- [ ] **R3 — Replay:** run `node research/consensus/w11_temporal_origin_no_history_promotion_lab.js`; compare all 36 row IDs and per-row verdicts to `W11_TEMPORAL_ORIGIN_RESULTS_2026-11-17.json`; disclose Node version, SHA and output hash.
- [ ] **R4 — Mutation controls:** intentionally modify one no-history guard (e.g., grant-check bypass or origin replacement) in **local disposable copy** and show which independent tests go RED. If a broken implementation stays GREEN, report that weakness.
- [ ] **R5 — Forged root:** prove that a caller forging `USER_REQUEST`/grant inside a retrieved document **cannot** alter the trusted envelope; W11 does not prove protection if the producer itself is compromised.
- [ ] **R6 — Revocation/rollback:** test an outdated grant cache, concurrent revoke/candidate decision, and recovery after restoring a grant store; W11 only serializes steps in one JS runtime.
- [ ] **R7 — Scope fidelity:** path aliases, recipient canonicalization, equivalent URLs, Unicode/casefold, principal collisions, expiry and independent clock. Exact-string equality is not an authenticated identity oracle.
- [ ] **R8 — End-to-end source truth:** demonstrate which current Ario runtime/dispatcher actually consumes these labels; if no integration is present, write `NOT_IMPLEMENTED`, not `SECURE`.
- [ ] **R9 — Utility and false denials:** construct at least two *new* benign mixed-trust tasks that truly require data from retrieved memory but must not acquire extra authority; don't count all-block as a win.
- [ ] **R10 — Independent oracle:** one or more **externally held** origin/grant cases genuinely independent of the test author; predictions must be frozen before oracle reveal. Same agent with two role names is not an independent custodian.
- [ ] **R11 — Governance:** ensure `#216` / `#210` remains `DRAFT/HOLD` and no unilateral reinterpretation of historical `ACCEPTED`, ID, memory admission, ruleset, real key or signer is performed.

**Review disposition rule:** Until a genuinely independent reviewer posts an inspectable response, every checklist item is **OPEN/NOT_CONFIRMED**; green GitHub Actions is not a source review and a generated Consensus/Firecrawl summary is not a third-party audit.

## E. Required short reviewer return format

`Finding ID | CONFIRMED/REFUTED/UNKNOWN | exact file/line + commit | paper section / test reproduction | counterexample (if any) | bounded fix/test | independent reviewer identity (if authenticated) | blockers`.

**No merge** pending protected decisions. Please keep the findings on [PR #242](https://github.com/SepehrGhanbari/Ario/pull/242) and [#216](https://github.com/SepehrGhanbari/Ario/issues/216) rather than duplicating new implementation code.

`RESEARCH_ONLY / NO_AUTO_MEMORY / NO_MAIN_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO`
