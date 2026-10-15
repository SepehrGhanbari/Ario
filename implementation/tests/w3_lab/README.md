# W3: Synthetic Custody and Event-Comparability Laboratory (TESTS ONLY)

**Experimental research fixture, not a production witness verifier.**

This directory vendors the offline W2/W3 *mock verifier and pytest probes* reviewed on 2026-10-15 for Ario Issue #81. It does not modify the real M0, EA-0.1, ARP-0.1, RAC-0.1, TA-0.1, custody policy, trust anchor, evidence admission, or production source loader. `w2_lab_verifier.py` is a **deliberately test-only implementation** with **injected assumptions**, not an authenticated source and not a viable authority. No real private keys or trust root is accepted. Actual RAC-0.1 is imported directly from `implementation/reviewer_authorization_preflight.py` during tests; that file is **not** copied here.

## Scope, status and limits

- W2 inherited tests check exact raw payload bytes and a self-declared SHA-256 digest in a synthetic pre-enrolled *test oracle*; duplicate lineage, split reads, missing ancestry, wrong audience, revoked or expired mock grants and invalid metadata cannot create admission authority.
- W3-F03 (two declared witness labels, distinct roots, same declared custodian): `UNKNOWN / SHARED_CUSTODIAN_NOT_INDEPENDENT`.
- W3-F04 (reviewer is an exact source custodian): `REJECTED / REVIEWER_SOURCE_CONFLICT`.
- W3-F05 (identical status label but different declared event types): `UNKNOWN / EVENT_TYPE_MISMATCH`.
- Diagnostic precedence: known shared ancestry is reported before repeated custodian, preserving earlier controls. In injected synthetic tests, a valid-looking mock outcome is **only** `LAB_REVIEWABLE_ONLY / MOCK_ONLY_NO_AUTHORITY`, always with `admission_decision=NOT_EVALUATED`, `claim_truth=UNKNOWN`, `source_authentication=NOT_ESTABLISHED_IN_PRODUCTION`.
- The *real* Ario RAC preflight remains non-authorizing: `UNKNOWN` or `REJECTED`. There is no native TB→M0 evidence bridge or production admission implementation in this directory.
- **No historical witness independence can be inferred from equal/different mock names.** The offline oracle is specified by the test itself; it is not externally authentic or independent. Matching `event` values describe event *types*, not necessarily one event instance.

## Verification and provenance

Source lab archive: `Ario_W3_Custody_Conflict_Lab_2026-10-15.zip`; independently checked SHA-256 `f9cf9fbb0c9ff50d1ec5a7acb5d38cd305a19569ff03343ac431a918afae4523` (local artifact, **not** a GitHub release or a signed independent attestation). The complete archive retained the original RED logs (`3 failed, 3 passed`), intermediate diagnostic priority regression (`2 failed, 31 passed`) and GREEN run (`39 passed`). These records verify the *mock lab* behavior within the stated boundaries only.

Original six laboratory source/test files are reproduced here byte-for-byte except for the two-sentence module docstring in `test_w2_rac_crosslayer.py` explaining that this PR uses the actual repository RAC module rather than vendoring a copy.

Run from `implementation/`:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -p no:cacheprovider -q tests/w3_lab
PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -p no:cacheprovider -q tests
```

Test output is a local/CI result, **not** validation of unobserved attackers, positive real-world authenticity, independently governed source enrollment, genuine external clocks/revocation, or claim truth.

## Review gate

Keep this work as a separate test-only draft PR until independent adversarial review of the copied mock implementation, injected-oracle boundary, actual RAC import, test assertion sensitivity, unexpected file writes, and GitHub CI on its exact head. Issue #81 must remain open after merge; positive evidence admission and trust root activation require entirely separate security and governance approval.
