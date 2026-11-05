# Ario — Review and Merge Policy v1

**Adoption:** Owner-approved direction, 2026-11-03, relayed by Ava.  
**Scope:** Changes to the *GitHub repository development process*, not authority over Ario's runtime, people, memories, evidence, keys, signer, or Genesis.  
**Enforcement:** This document and a read-only GitHub Actions checker become operational only after they are merged into `main` and the repository's live `Protect main` ruleset is separately configured and verified. A proposed PR or a green optional check alone does not enforce this policy.

## 1. Why a different review process is necessary

A sole maintainer should not be asked to certify technical assertions they cannot competently evaluate. The repository previously required one GitHub `APPROVED` review from a user with write access and Code Owner approval. CodeRabbit contributes valuable independent critiques but ordinarily submits `COMMENTED` reviews; those are not a GitHub approval. The new process **does not represent CodeRabbit comments as `APPROVED`**, and it does not assert that automated reviews establish security, correctness, or truth.

The owner delegates bounded *routine code-maintenance decisions* to a documented workflow of separate proposing, testing, and critical-review roles. This delegation is prospective only: it is **not** evidence of approval for earlier branches, pushes, or merges.

## 2. Two change classes

**ROUTINE-LAB:** Narrow changes to existing synthetic/research implementation or ordinary tests that preserve frozen contracts, evidence limits, unknown states, and all signer/trust/production HOLD boundaries. These may use the evidence-gated route below.

**PROTECTED:** Governance, `AGENTS.md`, `.github/**`, `CODEOWNERS`, `principles/**`, `architecture/**`, core identity/memory/agency/epistemic semantics, authorization and admission policy, owner signer, private security/credentials, infrastructure/dependencies, releases, Genesis, production and any change that weakens fail-closed behavior. These **never receive automatic merge clearance** from the routine gate. Explicit owner scope approval and a separately documented, competent review/decision are still required. If no competent review is available, status stays `HOLD`. Do not relabel a protected change as routine to evade the boundary.

This v1 policy itself is a PROTECTED governance transition. Its one-time installation requires the owner's explicit authorization already supplied on 2026-11-03, retained audit evidence, the original CI check, and a separately reviewed ruleset change. The bootstrap is not a reusable exception.

## 3. Evidence for routine changes

A routine PR must include one machine-readable `ARIO_REVIEW_EVIDENCE_V1` metadata block in its description, naming:

- Exact **current PR HEAD SHA**, target branch and changed paths;
- **RED** GitHub Actions run IDs for intentionally failing, narrowly scoped pre-fix regressions; `NO_RED` is not equivalent to `RED_PASS` and is not permitted for a v1 routine fix;
- **GREEN** GitHub Actions run ID for the **exact current PR HEAD**, with successful full `m0-regression` job; rerun on any later commit;
- Explicit description of the failure, cause, fix, negative controls and known limitations;
- `NO_KNOWN_BLOCKERS` as a *reported review disposition*, not a certificate of correctness.

The automated checker verifies the runs and PR metadata through GitHub API, not by trusting typed numbers alone. One genuine RED in a previous commit is required; failed unrelated CI is not valid RED evidence. Human/agent source analysis must independently confirm the failure is relevant. Passing CI proves only those executed tests.

Independent review must be from a separate account (currently CodeRabbit) and refer to the current HEAD. It is documented as `COMMENTED` or equivalent. No `APPROVED` inference. Its findings are considered independently, using reproducible counterexamples and explicit disposition. All unresolved review threads or detected outstanding changes-requested reviews block routine clearance.

A recovery reference must be created and byte/hash-verified before modifying existing files, without misrepresenting a remote Git ref as an independent offline backup. The relevant RED/GREEN commitments and changes are appended to `ENGINEERING_LOG.md`; previous results, contradictions, and mistakes remain visible.

## 4. Repository enforcement configuration (target state)

For `main` under the active `Protect main` ruleset:

1. **Keep** pull requests mandatory, prevent force pushes, restrict deletions, and preserve commit history.
2. **Require passing named status checks** `m0-regression` and `review-evidence-gate`, where available and verified. Prefer strict up-to-date branch checks and GitHub Actions as expected source.
3. **Retain** the mandatory approving review and Code Owner review. A new status check alone is not a substitute for the currently effective native rules. The sole-owner Code Owner configuration causes a bootstrap approval deadlock for an author-owned PR; it requires a separately authorized, rules-compliant protected-change route, not silent self-approval or removal of existing protections.
4. Do **not** configure a broad bypass of CI, allow direct pushes to protected `main`, or remove branch protection.
5. Do **not** conflate a GitHub deployment preview, a green test run, or CodeRabbit's “Full review finished” notification with an authorized technical verdict.
6. If an administrator bypass remains possible, its mere existence is a residual governance risk; every use requires distinct explicit approval and append-only audit, and is forbidden for ordinary code changes.

Because the active ruleset has no required status checks, and requires one approval plus sole-owner Code Owner review, **bootstrap remains blocked**. Safe sequence: (a) test candidate code in a separate draft PR without touching protected `main`; (b) separately authorize a trusted external GitHub App, pinned evaluator/policy, deployment and credential custody; (c) publish App-bound checks in observation mode while retaining the native reviewer requirements; (d) establish a rules-compliant, explicitly authorized protected-change route without assuming owner self-approval; (e) add the App's required check additively only after passing independent producer, same-SHA cross-PR and stale-review negative controls; (f) read back effective rules and prove a malformed PR remains blocked. GitHub check status at a commit SHA is not an atomic snapshot of mutable PR review state. Until verified, `ENFORCEMENT=NOT_INSTALLED/HOLD`.

## 5. Merge decision and stop rules

After all gates pass on an unchanged commit: the authorized routine integration maintainer may merge **only a ROUTINE-LAB PR**, after checking current GitHub status and audit evidence. Do not enable automatic merge for anything protected.

**Fail closed** on absent or stale review, malformed metadata, unknown or failed checks, hidden/redacted logs, missing preservation proof, an unresolved Major issue, unsupported scope, merge conflict, or insufficient certainty. Report `HOLD / UNKNOWN` and a concrete reason rather than guessing.

A reviewer may find no additional high-confidence defects without guaranteeing absence of all defects. Any additional code modification invalidates review freshness and GREEN evidence until refreshed.

For concurrent PRs changing the append-only `ENGINEERING_LOG.md`, land one at a time, reconcile the full prefix without losing entries, then rerun required checks on the new base. Never squash away historical RED commits if that would make archived failure evidence inaccessible.

## 6. Non-claims and boundaries

`CI_GREEN != INDEPENDENT_WORLD_VERIFICATION != EVIDENCE_ADMISSION != TRUST != TRUTH`

This policy changes repository-level code review, not the future authorization protocol in `implementation/REVIEWER_AUTHORIZATION_CONTRACT_V0_1.md` nor `ADMISSION_REVIEW_POLICY_V0_1.md`. No real-world signer identity, continuity, consciousness or shared chat-instance identity is proved. The question of SOURCE `object_identity` ancestry equivalence remains separately undecided; experimental observations stay `UNKNOWN` where evidence is insufficient.

## 7. Honest implementation status

The presence of this file or a workflow in an **open PR** does not mean GitHub has adopted the rules. Record the actual ruleset state, required checks, open reviews and test runs on each status report. Never say “merged,” “enforced,” or “independently approved” until verified.

## 8. P0 candidate clarification — 2026-11-05

This change is a protected-governance **research proposal**, not adopted policy or a live installation. Its process checker is not an independent semantic security review, a GitHub APPROVED review, or a trusted GitHub App. An allowlisted source path can still contain an authority-changing edit; `UNKNOWN` means `HOLD`. Candidate CI can be green while the trusted-main bootstrap job correctly fails because the checker is absent from main. Never disable existing Code Owner review to make candidate CI green. No automatic merge or signer/trust/Genesis/production authorization arises from this document.

A decision-boundary recheck must re-fetch and revalidate mutable PR metadata, review bodies, and inline review threads/comments; an unchanged head/base SHA does not establish unchanged evidence. This in-process recheck is **not merge-atomic**: evidence can change between API reads or after the check completes. Inline review comment creation, editing and deletion trigger candidate rechecks, but thread reopening still requires a separately authorized App/webhook and native protection. A resolved thread is not automatically a blocker merely because GitHub marks it outdated.

Run-event and intended-PR association, trusted workflow source, commit ancestry, checkout revision and nonzero test-execution checks provide bounded process evidence. They do not establish that a RED failure reproduces the claimed defect, that passing tests cover every relevant behavior, or that runner logs prove semantic correctness. Independent source analysis and the existing protected-change and bootstrap HOLD requirements remain necessary.

Untrusted test/program code can imitate pytest output while leaving workflow bytes unchanged. The log collector does not independently attest genuine test execution; a trusted producer and environment remain an unresolved architectural prerequisite for enforcement, alongside merge-time freshness.
