# Guard V2 — PR scope and shared-SHA lab falsifier

**RESEARCH_ONLY / DRAFT / NO_MERGE / NO_APP_CREDENTIAL / NO_CHECK_POST / NO_RULESET_CHANGE / NO_TRUST_ACTIVATION / PRODUCTION=NO_GO**

## 1. Direct GitHub observation, 2026-11-21

Historical [R1i App Check 132094820201](https://github.com/SepehrGhanbari/Ario-solo-rehearsal-20261111-r0a/runs/132094820201) is a completed SUCCESS from the disposable GitHub App **5747504** under context **ario-r1d-lab-app-gate** at exact HEAD **508a6abfacf534fa01a4b97210c35b35ca965c86**. Its external ID explicitly includes **PR14**, and the Check's native pull_requests collection contains only #14 (database ID 5300854842). Sandbox ruleset **27219627** requires that exact context and App, strict, with no bypass.

Two disposable PRs with distinct identities but the **same HEAD and base** were then created: [PR #15](https://github.com/SepehrGhanbari/Ario-solo-rehearsal-20261111-r0a/pull/15) (database ID **5431302927**) and [PR #16](https://github.com/SepehrGhanbari/Ario-solo-rehearsal-20261111-r0a/pull/16) (database ID **5431303336**). On temporary Ready state, native GitHub reported **mergeable_state=clean for both**, despite the original App Check being PR14-scoped in its metadata. No new App Check was published for those PRs. After a clearly synthetic Critical-labeled comment was added to #16, native state remained clean without a HEAD change.

Both fixtures were **restored to Draft and CLOSED WITHOUT MERGE**; their records and the original PR14 Check remain. No actual merge attempt was made. Full [live findings and restrictions](https://github.com/SepehrGhanbari/Ario/pull/133#issuecomment-7067674171).

**Result:** a source-pinned GitHub required Check at a commit SHA does **not** by itself implement PR database-ID-specific authorization. GitHub's behavior is not represented as a platform defect.

## 2. This bounded experimental implementation

**implementation/research/guard_v2_pr_scope.py** is a pure, side-effect-free offline *negative classifier*. It accepts four caller-supplied JSON objects: a pinned PR identity and review digest, two snapshots of PR identity/comments/reviews/threads, and a full Check Run capture. Strict integer PR/repository IDs, exact HEAD/BASE, complete distinct review collections, unchanged pinned review digest, a success from the single pinned lab App, external ID naming the exact PR, and exactly one matching native PR association are required.

The historical cross-PR data causes **HOLD / CHECK_PR_ID_MISMATCH** for PR15 and PR16. Changed comments, changed head/base, pagination gaps, unresolved threads, wrong App, neutral/skipped status and ambiguous Check associations also cause HOLD.

Even an internally coherent PR14 fixture returns **REVIEWABLE_ONLY**, with all merge/check-publication/trust permissions false. Its CLI intentionally exits with code 1 even for a diagnostic positive, preventing accidental use as a green merge gate.

A supplied #295 Ario self-audit result reporting successful linked PR CI does **not** elevate Guard V2 authority. That existing observer is read-only and not an independent attestation.

## 3. Explicitly unproved boundaries

This code does not fetch GitHub directly; its pin, two captures and review digest are **caller-supplied and mutually forgeable**. The Check's external ID is issuer-controlled metadata, not an immutable independent signature. The result cannot establish complete evidence custody, genuine test execution, deletion before first capture, post-read mutation, independent credential custody, or atomic merge-time verification.

**Before any operational activation:** implement a separately running, source-pinned evaluator and founder-authorized PR-specific merge broker with authenticated live GitHub reads, complete raw records, protected retained observations, exact repo/PR/HEAD/BASE binding, and immediate pre-action reread with no blind retry after an uncertain write. Falsify again with same-SHA PRs, mutable reviews, crash/partition windows, and adversarial workflows. Do **not** assume another required Check alone fixes the shared-SHA problem.

**No new human reviewer is required for this synthetic research.** No change to existing Ario main rulesets, owner authority, signer, Genesis or Trust.

## 4. Append-only follow-up falsifier: App-ID numeric alias (2026-11-21)

After the initial 32/32 local PASS, an additional adversarial Python/JSON probe showed that a fake Check with float App ID **5747504.0** was incorrectly treated as the integer App ID **5747504**: original classifier yielded **REVIEWABLE_ONLY** (RED). This is a schema-type weakness, not proof an attacker can impersonate a genuine GitHub App over authenticated API. The tightened matcher now requires a *positive exact Python integer* App ID, rejecting float/string/boolean aliases. Three new parameterized tests and the original 32 checks passed locally: **35/35 GREEN**. Prior committed RED code is preserved in Git history. All authority booleans remain false; no runtime or rule activation.
