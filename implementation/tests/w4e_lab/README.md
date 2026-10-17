# W4-E — Offline independent-steward and witness-origin preflight lab

**STATUS: RESEARCH / SYNTHETIC / TESTS ONLY.** This is not a production enrollment, a decentralized quorum, trust-root authorization, an independently authenticated source, evidence admission, or a historical truth service. It neither creates keys nor signs data. There is no M0, RAC, ARP or runtime bridge.

## Provenance and bounded scope

This candidate is based on the author's independent W4-E design archive `Ario_W4E_Independent_Governance_Design_And_Offline_Probe_2026-10-16.zip`, verified SHA-256 `5f62b76842c8bc143ada4e1c6c8706cbbcfcfbfc47d591eab50e8b6f4b36679d`. The archive's internal SHA256SUMS verified all ten files. Its original `w4e_structural_probe.py` and `test_w4e_structural_probe.py` were preserved as an unchanged RED baseline outside the GitHub PR, with **36 original unittest methods passing**.

A second-pass adversarial test independently demonstrated that **13 / 14 new cases FAILED (RED) against the unchanged source; one benign control PASSED**. This concerns *non-authorizing `LAB_PACKET_READY_FOR_EXTERNAL_REVIEW` hints* and does not show a live exploit. The additional controls cover:

1. A single declared steward or witness (no declared plurality for an independence-oriented lab).
2. Issuer labels exactly overlapping with declared steward principals, governing controllers, proposer/reviewer IDs or witness controllers.
3. Proposer/reviewer labels exactly overlapping with declared steward or witness-controller labels.

The minimal **offline-only** repair emits `UNKNOWN/HOLD` for these *declared label collisions* or insufficient declared plurality. **It does not claim that lexical equality proves a real person's identity**; it errs conservatively on a packet-readiness hint. A distinct label likewise never proves independence. Re-run after repair: **50 unittest methods PASS (36 originals + 14 additional cases)**. Four isolated scratch-only guard bypasses were caught, producing respectively 5, 2, 4 and 2 failed controls.

## Reproduce

From repository `implementation/`:

```sh
python -B -m pytest -p no:cacheprovider -q tests/w4e_lab
```

Alternatively, from `implementation/tests/w4e_lab/`:

```sh
python -B -m unittest discover -s . -p 'test_w4e_*.py' -q
```

Expected on this candidate: 50 tests PASS. CI on a PR/head must be separately verified; no GitHub-wide test result is asserted by this package.

## The required epistemic boundary

`OBSERVED ≠ CRYPTO_VALID ≠ SOURCE_AUTHENTICATED ≠ CUSTODY_INDEPENDENT ≠ REVIEW_AUTHORIZED ≠ ADMITTED ≠ TRUE`.

Every returned finding remains `UNKNOWN` or `REJECTED`, and the six identity/independence/authorization/admission/truth dimensions never produce a positive credential, consent grant, reviewer authority, admitted evidence or claim truth. Every principal, issuer, controller, key ID, event/root/registry digest, observed time/nonce, consent and revocation datum is an **untrusted caller-controlled declaration**. Positive syntax flags cannot authenticate a subject, origin, custody, plurality or legal consent. `LAB_PACKET_READY_FOR_EXTERNAL_REVIEW` is merely a shape-oriented suggestion about a mocked dossier, **not approval to share private data**.

## Explicit unresolved questions

- Hidden common ultimate control, Sybil/collusion, issuer-proofing independence and temporal controller relationships remain UNKNOWN. Equality/mismatch of labels is no authentication.
- Claimed upstream observation pointers cannot establish complete multi-hop provenance or disjoint historical capture; hashes cannot prove observations occurred.
- Current/presented registry digest equality is not independent signed checkpoint continuity, authenticated revocation freshness or real consensus.
- `identity_binding_claimed` and `clock_freshness_claimed` are **not** real identity bindings or verified clocks.
- Consent/right to withdraw/appeal, confidential witness custody, disclosure/erasure exceptions and safe independent adjudicators require separate policy and implementation review.
- The illustrative two-record lower bound is **not** an adopted minimum number of governing authorities or witnesses. Real eligibility must define purpose-specific quorum/assurance requirements and allow benign single-witness cases to be processed without claiming independent corroboration.

No existing Ario files, audit ledgers, keys, production rules, signed roots or workflow are modified by adding this independent test directory. Do **not** merge without the separate owner/security gate; Issues #81/#75 remain open. A future real verification path requires separately approved trust anchor, external proofing, cryptographic profile, subject binding, fresh authoritative revocation, anti-replay, control-graph assurance and privacy.
