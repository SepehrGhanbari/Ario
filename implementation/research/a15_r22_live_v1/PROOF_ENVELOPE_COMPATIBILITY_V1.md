# A15/R22 proof-envelope compatibility v1 — offline retained-evidence audit

RESEARCH_ONLY / DRAFT / HOLD / SYNTHETIC_ARCHIVED_EVIDENCE_ONLY / NO_REAL_KEYS / NO_NEW_PUBLICATION / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_MERGE.

## Existing work reused — no parallel custodian prototype
- A15 v0.5 Broker source is the exact pinned blob `612fa44e6eb2cb1078561bca85bb0f69f984bff9` from #346.
- #382 read-only adapter pins that Broker and emits only the A15 checkpoint envelope.
- #389's existing synthetic live run 45823494521 published two A15 checkpoints and verified Sigsum TEST leaves 282772/282773 at tree size 282774. The original run's final reveal job failed because a disposable extracted directory lacked exclusive permissions. The historical cold-recovery record remains unchanged; this compatibility job does not relabel that run as wholly successful.
- #380 R22.22G exact source is pinned at commit `255398a8e243d3738b132dafe0fe0edcaab29679`; its event codec is a distinct R22.20 profile.

## Exact wire profiles
A15 checkpoint outer envelope: `payload`, `payload_sha256`. Its payload includes `format=ario-a15-r22-readonly-checkpoint-v1`, `domain=ARIO/A15/R22`, `enrollment`, `journal_scope`, pinned `broker_source`, `broker_head`, and `previous_external_checkpoint_sha256`. It intentionally contains no Broker rows or database bytes. A15 Nostr topic/prefix are `ario-a15-r22-synthetic-v1` and `ARIO A15/R22 synthetic TEST checkpoint (no personal data): `.

R22.20 outer envelope uses `profile/scope/seq/previous_checksum/previous_event_id/previous_ledger_sha256/prior_checkpoint_sha256/prior_ledger_sha256/ledger_sha256/head_sha256/synthetic/authoritative/historical_event_truth/trust_activation/production`, with a separate embedded ledger. R22.20 topic/prefix are `ario-r22-20` and `ARIO R22.20 public synthetic floor (no personal data): `.

These are intentionally incompatible protocols. Do not feed A15 events to R22.22G's generic-successor verifier, or R22.20 envelopes to the A15 adapter. A future bridge must be an explicitly versioned A15-specific proof contract, not schema coercion.

## What this read-only job verifies
- Uses exact byte copies of the original public synthetic A15 artifacts from run 45823494521, stored as fixtures in this branch and SHA256-pinned in the bounded extraction wrapper:
  - artifact 15118184755 / FIRST-ONLY: `f6012b78741a23992be901141fb8eb560f7010d17ecc4ccf4e71d3f917cd5f97`
  - artifact 15118049899 / SECOND-REVEAL-SYNTHETIC: `4eec66aeb8036e9628094acbe815c7418e88836d064b384dcd0558ed4910f3ec`
- ZIP wrapper verifies CRC, exact member manifests, path traversal, symlinks, member bounds and total expanded size before extracting to a disposable directory.
- Verify both A15 Nostr event IDs/signatures, exact checkpoint bytes, exact event-id message and Sigsum TEST inclusion proof using pinned Sigsum verifier.
- Bind first proof to the bootstrap; enforce strict leaf order and exact seq1→seq2 checkpoint predecessor digest.
- Construct a throwaway R22.20 event with a test-only key and synthetic one-row ledger, verify its own profile, then prove both parsers reject the other profile at envelope and event boundaries.
- Tampered and cross-substituted Sigsum proofs must fail the official verifier.

## Limits
This is an offline verification of two retained synthetic checkpoints. The fixture ZIPs are stored in the same repository/administrative domain as the verifier, so they are not independent custody. Sigsum TEST inclusion proves that the exact event-ID message is in the sampled test log under the pinned policy; it does not establish trusted current time, global latestness, long-term availability, independent administration of GitHub/relays/witnesses, A15 custodian admission, actual Ario memory truth, or production authority. This job makes no relay calls or new publication. The test-only R22 key is ephemeral and not exported. The old A15 live run's final reveal failure remains visible; its previous cold-recovery claim is not re-run by this compatibility job. No merge, key, floor, policy, trust or production state is changed.
