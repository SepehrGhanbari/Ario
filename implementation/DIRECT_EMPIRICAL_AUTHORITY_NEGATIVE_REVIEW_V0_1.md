# Direct Empirical Authority Gap — Negative Experiment and v0.1 Design Decision Request

**DRAFT / RESEARCH_ONLY / HOLD / NOT_ADOPTED / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO**

## Exact source and reproducible RED

- Parent: Ario Draft [#267](https://github.com/SepehrGhanbari/Ario/pull/267) at `ac5b1a7191b832d118afbced81a7b092fcdddc1f` (itself based on #210).
- Test-only branch `research/pr267-direct-empirical-authority-red-20261117`, test commit `2d0f0482e63728ca67514d80e777a48b70c99ba3`.
- [GitHub Actions push run #44146155178](https://github.com/SepehrGhanbari/Ario/actions/runs/44146155178): **3 expected safety failures, 1242 passes + 121 subtests** on Linux; Windows was SKIPPED on push. Do not claim a Windows replay.
- Test file: `implementation/tests/test_direct_empirical_authority_negative_lab.py`. All tool results are fake and do **not** execute a tool, request a signer, modify production memory, or interact with real credentials.
- Controls: unauthenticated hypothesis-only and external-testimony-only attempted promotions remain denied.

Three source-reproduced counterexamples (same process):
1. A caller can invoke `SourceMonitoringGuard.record_empirical_observation(tool="file_fingerprint", exit_code=0, stdout=FAKE, execution_lock=FAKE)` for a file that **does not exist** and obtain `VeracityState.VERIFIED_EMPIRICAL`.
2. `evaluate_claim_promotion` accepts such a self-created observation as empirical evidence and marks a synthetic hypothesis `VERIFIED_EMPIRICAL`.
3. `filter_working_memory_candidates(require_verified=True)` returns that observation as a verified-only candidate.

**Precise scope:** These are genuine direct-API semantic bypasses **in the in-process research implementation**. They are **not** a demonstrated externally reachable production exploit. Whether any hostile principal can invoke the direct API in a deployed Ario process is **UNKNOWN** and must be traced before severity escalation.

## Root cause / trust distinction

`SourceMonitoringGuard.record_empirical_observation` uses allowlisted tool names, caller-supplied exit code, execution-lock text and output text. It computes hashes of the values **provided by the same caller**. Unless the expected digests are externally authenticated, equality or SHA-256 strength proves only that bytes match themselves, not that the named tool actually ran, that the source is independent, that authorization existed, or that the claim is semantically true. Expected hashes alone would not fix this if the caller supplies them too.

`evaluate_claim_promotion` checks existing `SourceAttribution.source_type` and `veracity_state` without verifying independently authorized provenance at the memory/admission sink. `filter_working_memory_candidates(require_verified=True)` has the same trust limitation.

## Required design, NOT a deployed fix

1. **Separate the event producer and verifier:** untrusted input can only produce `RECORDED/REPORTED_UNVERIFIED` records. No self-declared `COMPLETED`, self-hash, claimed tool identity or caller-supplied token is a source of `VERIFIED_EMPIRICAL`.
2. **Capture actual execution at an independently authorized boundary:** bind executable identity, action request hash, output hash, exit code, temporal ordering, event ID/nonce, and protected signer identity into a receipt **created by the executor**, not by the agent writing a JSONL.
3. **External, independently pinned key custody / permission and revocation:** store trusted public key identities and revocation state outside writer control, with explicit version, expiry, rotation and rollback tests. A second key in the same process/user is NOT independent custody; multiple signatures alone are not enough. No real Ario key is necessary for this research.
4. **Fail closed at each privileged sink:** the consumer of evidence, memory promotion, tools, and signer/trust activation should verify allowed executor identity and the exact receipt over the event, validate revocation and ancestry, and establish semantic relevance before promotion. An in-process `VERIFIED_EMPIRICAL` enum or a Python wrapper by itself must never grant privilege.
5. **Separate integrity, authenticity, independence, and truth.** A valid receipt establishes (at most) an attributable execution under a specified threat model; it does not prove semantic entailment or true real-world facts.
6. **Govern historical compatibility under #216.** No rewrite of old `ACCEPTED`/`SUPPORTED`/`VERIFIED_EMPIRICAL` records; use a versioned sidecar for new authentication state and ambiguous old records.

## Minimum red/green experimental matrix before promotion

- RED without executor receipt (current three source-based failures).
- RED with invalid/unknown/revoked/expired executor identity or receipt version.
- RED for a self-signed receipt whose key is not pinned by the independent administrator.
- RED for copy/replay/nonce collision/mismatched request/result hash, old revoked keys and substitution during verification.
- RED for same-operator "two independent witnesses", shared ancestry, forged multi-source multiplicity, and unauthorized memory sink access.
- RED for cryptographically valid but semantically irrelevant or contradictory results.
- GREEN for a **separately originated, independently authorized and source-pinned synthetic** execution receipt with correct digest binding and semantically relevant claim, without modifying history.
- GREEN for benign report retention and revoked-source UNKNOWN handling.
- Verify failures and positives under Windows and Linux; bounded sizes, persistence after crash, concurrent replay and source drift.
- To claim **real independence**, use an executor/witness process with genuinely separate OS identity, custody and administrator. A single GitHub Action signing and verifying its own test fixture only establishes **synthetic protocol behavior**.

## Decision options for independent reviewers

**Option A:** Keep old direct API *only* behind a provably authenticated executor boundary; make privilege consumers enforce external receipts. Requires call-graph and authority review, not just tests.

**Option B (preferred for research):** Introduce a v2, non-authoritative, report-only admission API and a separate external execution verifier. Leave old API behavior unchanged but do **not** treat its raw enum as an authenticated gate. This can be tested safely without importing production keys, and is consistent with issue #216's versioning HOLD.

**Not acceptable:** `trusted=True`, a static shared secret in code, hard-coded allowlisted tool names, computed hashes of the same caller's input, or a wrapper whose bypass lets the old direct method grant production authority.

## Founder's plain-language summary / خلاصه فارسی

آریو فعلاً می‌تواند از روی حرفِ برنامه‌نویسی که مستقیماً تابع «ثبت شاهد» را صدا می‌زند، برچسب «شاهد تجربی تأییدشده» بسازد. سه تست قرمز نشان داد همین برچسب روی ارتقای فرضیه و فیلتر حافظه هم اثر می‌گذارد. **این حمله به محیط تولید نیست**؛ برای اثبات خطرِ واقعی باید ببینیم چه کسی اجازهٔ صدا زدن این تابع را دارد. اصلاح معتبر نیاز دارد شاهد از مجرای اجرایی با اختیار مستقل برسد و در مقصد دوباره اعتبارسنجی شود. کلید نهایی آریو و فعال‌سازی اعتماد همچنان ممنوع است.

**No merge / no live signing / no new keys / no trust activation / no approval from synthetic CI.**
