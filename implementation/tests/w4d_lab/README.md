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
