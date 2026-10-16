# W4-D — Synthetic Multi-Party Governance and Privacy Tests (NO AUTHORITY)

**Status:** experimental test fixture, not a governance adoption, signer, reviewer, admission service, privacy control or decentralized network. All findings remain `UNKNOWN` or `REJECTED`. No real steward/controller is enrolled, no evidence is admitted, and no truth verdict is possible.

## Why here?

This folder preserves the standalone W4-D mock from the independently hashed research ZIP and tests the conservative boundary in GitHub CI. It is intentionally confined to `implementation/tests/w4d_lab/`, without runtime imports, credentials, policy adapters or changes to existing code. Historical baselines are preserved outside the repo; only *new* files are introduced here.

Original suite: **85 passed** independently re-executed. External W4-D-F01 security review found that the original mock treated a supporting vote from a *declared* proposer/source control group as usable toward `ROTATE_ROOT` or `UNFREEZE` lab recommendations. Eight new negative controls were **RED** against the original function (`8 failed, 1 passed` within the new test file). The reviewed test-only correction recognizes known declared recovery interests and holds the request with `W4D_RECOVERY_INTEREST_CONFLICT`. Candidate suite: **94 passed** (`85 + 9`), including a negative-vote control that must not be counted toward approval.

## What is actually checked?

- Syntactic mock controller group collisions for review and recovery recommendations; conditional proposed thresholds of 2/5, 3/5 and 4/5 are **not adopted governance policy**.
- Preventing self-declared valid signatures, groups, quorum and consent from elevating authentication, review authorization, evidence admission or claim truth.
- Frozen/forked registry, objections, privacy metadata/consent and local audit hash consistency in the original standalone tests.

## Important unknowns / remaining threat work

- Real controller independence, Sybil resistance and collusion, actual root compromise and recovery, trusted clocks, current revocation, canonical signed ballots, live consensus, coercion and emergency procedure governance.
- Actual appellant/panel relationship to the *proposer* and *source custodian* is not represented in the W4-D mock AppealFixture; the existing appeal negative checks only compare against the original panel. Do not use `LAB_APPEAL_FOR_INDEPENDENT_SCREENING` to claim a truly disinterested appellate body.
- Consent evidence, legally justified access despite withdrawal, storage-key erasure, retention policy, low-entropy metadata linkage and privacy impact assessments require separately authorized design and review.
- A real key/signature cannot establish historic event truth; a synthetic controller-group match cannot independently prove same-person control or its absence.

No GitHub CI success should be claimed until the **actual PR head** runs the complete suite. Existing W4-B/W4-C tests require the CI-only `cryptography` dependency already pinned on `main`.

## Reproduce

From `implementation/`:

```bash
python -m pytest -q tests
```

Or focus on this lab:

```bash
python -m pytest -p no:cacheprovider -q tests/w4d_lab
```

**Never** merge this mock into governance/trust/authorization code on the basis of tests passing. Issues #81 and #75 remain open. Preserve `OBSERVED ≠ AUTHENTICATED ≠ AUTHORIZED ≠ ADMITTED ≠ TRUE`.

## Independent second-pass repair — W4D-F02/F03/F04/F05 (2026-10-15)

The unchanged PR #87 head (`bf6df2664cc7875cb4f5ec6ea0455fb876cc3242`)
passed its original 94 W4-D tests, but a *new* 13-instance negative suite
reproduced 12 RED assertions (1 control passed). The following conservative
**test-only** v0.2 changes add no runtime permissions:

- **F02 motion/ballot binding:** `MOTION_PROFILE=W4D-LAB-0.2` (old 0.1 profile
  is explicitly rejected). A motion digest is recomputed from the typed ordered
  array `[profile, motion_id, action, candidate_scope, 'INT:'+epoch,
  proposer_group, source_group, audience, nonce, 'INT:'+valid_from_tick,
  'INT:'+valid_until_tick]`, encoded using ASCII compact JSON, with the fixed
  domain-separated SHA-256 prefix `ARIO-W4D-LAB-MOTION-0.2` + a NUL byte.
  `digest` is **excluded** from its own hash. Identifiers use the existing bounded
  ASCII token grammar and ticks are bounded exact nonnegative ints. The
  synthetic observed tick must lie within the declared validity window.
  Every *ballot* must match that recomputed digest and declared epoch.
  The tests now build typed fixtures explicitly; *no silent legacy upgrade*.
- **F03 contradictory control:** one declared control group cannot cast more
  than one ballot in one request, including mixed `SUPPORT`/`OPPOSE` in either order.
- **F04 appeal completeness:** a claimed complete original panel is required
  (at least two unique valid declared controller groups). Any missing/incomplete
  original panel yields `UNKNOWN / W4D_APPEAL_ORIGINAL_PANEL_UNRESOLVED` and `HOLD`.
  This is not proof of genuine panel completeness or independence.
- **F05 result protection:** informational `lab_step` is strictly allow-listed;
  forbidden positive authority words cannot be injected into a `Finding`.

**CRUCIAL:** This uses a **recomputable unkeyed hash over caller-declared mock
fields**, not a digital signature, trusted timestamp, independently authenticated
nonce, durable replay registry, approval or evidence admission. The same caller
can fabricate a motion and matching ballots; a `LAB_*_RECOMMENDATION` is only
syntactic behavior inside the laboratory, and always has status `UNKNOWN` and
admission `NOT_EVALUATED`. The proposed audience and validity values are only
caller declarations. Do not couple this to M0/ARP/RAC or live governance.

Independent replays before publishing: baseline **94 passed**, extra controls
on unchanged source **12 failed / 1 passed**; new candidate **151 passed**
(94 original + 13 second-pass + 44 additional binding and safety cases).
Four mutation experiments (disabled binding, declared control check, original
panel completeness, allow-listed lab step) produced expected RED. The two exact
motion hash vectors (including a >2^53 integer tick) match between Python and
Node.js. GitHub CI on the updated PR head must be independently checked before
any merge consideration. Issues #81 and #75 remain OPEN.
