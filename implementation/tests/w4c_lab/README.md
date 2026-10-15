# W4-C / W4-B Synthetic Distributed-Trust Laboratory — Tests Only

**RESEARCH FIXTURE ONLY.** This package does not create a production trust root, real identity/custodian authentication, authorized reviewer, quorum protocol, key manager, real-time revocation service, consensus, admitted evidence or claim truth. All W4-C `Outcome`s remain `UNKNOWN` or `REJECTED`. `SYNTHETIC_REPLICAS_AGREE` describes equality of **injected data**, not authentic agreement of independent peers.

## Why these tests exist

This folder hosts the previously isolated W4-B signed-byte laboratory and W4-C injected-replica laboratory for review under Ario Issue #81. W4-B checks Ed25519 signatures against **public deterministic TEST-ONLY fixture keys**; W4-C adds structural checks for simulated registry snapshots, compromise freeze, revocation, replay, source/controller/custodian reuse and recovery. These do **not** implement positive evidence admission. There is no TB→M0 or RAC/ARP authorization bridge.

The independent pre-publication review found two **lab-only** fail-closed shape bugs: malformed unhashable `Replica.peer_id` could throw `TypeError`, and unbounded Python integers supplied as registry revisions, expiry ticks or revocation ticks could throw while serializing a snapshot fingerprint. The reviewed candidate validates peer identifier type/ASCII-token grammar and bounds all fixture revisions/ticks before hashing. The new `test_w4c_input_bounds_review.py` contains 13 targeted instances which **fail on the original 141-test archived version** (11 failed, 2 passed) and pass on this candidate. Existing W4-B and W4-C tests remain unchanged.

## Local reproduction

Requirements: Python 3.10+, `pytest`, and Python package **`cryptography`** for the **test-only** Ed25519 operations. Node.js 20+ optional for vector comparison; scripts make no network calls.

From this directory:

```bash
python -B -m pytest -p no:cacheprovider -q test_w4b_profile_lab.py test_w4c_distributed_lab.py test_w4c_input_bounds_review.py
node verify_test_vectors_node.mjs
node verify_registry_vectors_node.mjs
```

Independently replayed in an isolated workspace: **154 passed** (59 original W4-B + 82 original W4-C + 13 new negative controls). Node frozen vectors passed. Three existing mutation-sensitivity checks (fork-bypass, revocation-bypass, shared-controller-bypass) were re-run on temporary copies and correctly detected malicious changes.

**CI integration caveat / review blocker:** As inspected on 2026-10-15, `.github/workflows/implementation-regression.yml` installs `pip pytest` only. It does **not** install `cryptography`. Publishing this test folder to a draft PR without a separately approved, pinned dependency installation may cause collection to fail. A GitHub CI success claim requires actual complete test execution, not skip markers or mock replacement of the `cryptography` verifier. Do not modify workflows, introduce/pin a dependency, merge, or treat missing collection as green without owner-approved scope.

## Epistemic and security boundaries

- Snapshot fingerprints are SHA-256 hashes of canonicalized **test data**; this is not a signed registry or evidence of historical custody.
- `controller_id`, source/custodian IDs, replica rosters, wall-clock ticks and simulated recovery endorsers are **caller-supplied declarations**, not authenticated identities or independently verified observations.
- Existing `TEST_VECTORS` include a published Ed25519 demonstration seed. **NEVER** use that material to sign operational grants, evidence or Ario production artifacts.
- Matching signatures, peer snapshots, event IDs or numerous synthetic keys never produce positive `VERIFIED_FOR_REVIEW_ONLY`, `ADMITTED` or `TRUE`.
- Actual decentralized enrollment, revocation freshness, cross-party consent, governance succession, privacy and appeal remain unresolved research tracked in Issue #81.
- Only newly added files under `implementation/tests/w4c_lab/` are proposed. No existing code, contracts, governance, history or `main` branch are changed by preparing this candidate.

**Invariant:** `OBSERVED ≠ CRYPTO_VALID ≠ SOURCE_AUTHENTICATED ≠ CUSTODY_INDEPENDENT ≠ REVIEW_AUTHORIZED ≠ ADMITTED ≠ TRUE`.
