# R22.25 external keeper deployment contract

This document is an implementation contract, not a claim that a keeper has been provisioned.

## Required separation

- Keeper administrator and credentials must be distinct from GitHub repository/organization administrators and both publisher relay administrators.
- The keeper signing key must be generated and held inside the keeper control plane (HSM/KMS or equivalent non-exportable service key); never in GitHub Actions, repository secrets, developer workstations, or the publisher.
- The witness transparency log must be independently operated from the keeper and publisher. Its adapter must verify inclusion proofs and the latest quorum-cosigned tree head.
- A fresh recovery runner receives only public keeper/witness verification keys and read-only access. It must not receive write credentials.

## Minimal API semantics

1. PUT checkpoint bytes to a content-addressed object path derived from SHA-256. Existing object paths are immutable; same digest/same bytes is idempotent; same path/different bytes is a hard conflict.
2. GET the object back and verify exact length and SHA-256 before requesting a receipt.
3. POST an advance request containing scope, expected previous receipt digest, checkpoint digest, and the source-log consistency proof when target size advances.
4. Keeper atomically checks expected head (CAS), generation + 1, previous receipt link, monotonic cursor and target size, same-size root equality, append-only match manifest, and independently validates the source-log head/proofs and checkpoint structure. It signs and stores an immutable receipt. The signing key is not available to the caller.
5. Witness log appends the signed receipt digest and returns an inclusion proof under a current quorum-cosigned head. The client verifies this before treating the new generation as recoverable.
6. If a response is lost after keeper commit, read Latest and witness chain. Never create a second receipt merely because the response was lost. If keeper and witness disagree, HOLD.
7. No delete, overwrite, reset, restore-old-generation, or admin API may be callable using publisher credentials. Retention and audit logs must be enabled.

## Recovery contract

A new runner reads the complete verified receipt chain from the witness log and the keeper's Latest receipt. They must agree exactly. It fetches every referenced checkpoint by digest, validates canonical bytes and keeper signature, checks every predecessor link, and ensures prior matches remain an exact prefix. If the sampled source-log head grew while scanning was paused, the next generation must include a verified consistency proof from the prior target; the scanner continues from the preserved cursor and frontier, not from an old local copy.

Any missing service, missing object, proof gap, signature failure, fork, rollback, match removal, or unavailable current witness head returns HOLD. There is no fallback to GitHub, relays, local files, or a previous generation.

## Unresolved deployment gate

No external provider, keeper URL, independent administrator, service identity, or keeper key is configured in this repository. Before any live deployment, the project owner must identify a custodian whose administrator is outside the publisher/GitHub control domain and verify the permissions with that administrator. A second witness/gossip domain is still required to detect rollback of both keeper and witness together for a fresh client. The current R22.25 tests intentionally demonstrate that dual rollback boundary.
