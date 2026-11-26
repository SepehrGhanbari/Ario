# A15/R22 proof-envelope compatibility v1 — offline retained-evidence audit

RESEARCH_ONLY / DRAFT / HOLD / SYNTHETIC_ARCHIVED_EVIDENCE_ONLY / NO_REAL_KEYS / NO_NEW_PUBLICATION / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_MERGE.

## Existing work reused — no parallel custodian prototype
- A15 v0.5 Broker source is the exact pinned blob `612fa44e6eb2cb1078561bca85bb0f69f984bff9` from #346.
- #382 read-only adapter pins that Broker and emits only the A15 checkpoint envelope.
- #389's existing synthetic live run 45823494521 published two A15 checkpoints, verified Sigsum TEST leaves 282772/282773 at tree size 282774, and cold-discovered/recovered seq=2. The original run failed in its final reveal job because a disposable extracted directory lacked exclusive permissions. That historical failure is preserved; this compatibility job does not overwrite or relabel it.
- #380 R22.22G exact source is pinned at commit `255398a8e243d3738b132dafe0fe0edcaab29679`; its event codec is a distinct R22.20 profile.

## Exact wire profiles
A15 checkpoint outer envelope: `payload`, `payload_sha256`. Its payload includes `format=ario-a15-r22-readonly-checkpoint-v1`, `domain=ARIO/A15/R22`, `enrollment`, `journal_scope`, pinned `broker_source`, `broker_head`, and `previous_external_checkpoint_sha256`. It intentionally contains no Broker rows or database bytes. A15 Nostr topic/prefix are `ario-a15-r22-synthetic-v1` and `ARIO A15/R22 synthetic TEST checkpoint (no personal data): `.

R22.20 outer envelope uses `profile/scope/seq/previous_checksum/previous_event_id/previous_ledger_sha256/prior_checkpoint_sha256/prior_ledger_sha256/ledger_sha256/head_sha256/synthetic/authoritative/historical_event_truth/trust_activation/production`, with a separate embedded ledger. R22.20 topic/prefix are `ario-r22-20` and `ARIO R22.20 public synthetic floor (no personal data): `.

These are intentionally incompatible protocols. Do not feed A15 events to R22.22G's generic-successor verifier, or R22.20 envelopes to the A15 adapter. A future bridge must be an explicitly versioned A15-specific proof contract, not schema coercion.

## What this read-only job verifies
- Re-fetch the three existing A15 artifacts from original workflow run 45823494521; no new publication, relay call, signing or deletion.
- Verify both A15 Nostr event IDs/signatures, exact checkpoint bytes, exact event-id message and Sigsum TEST inclusion proof using pinned Sigsum verifier.
- Bind each proof leaf index/checksum to the original cold discovery report and bootstrap; enforce strict leaf order and exact seq1→seq2 checkpoint predecessor digest.
- Compare cold-recovered checkpoint/event bytes to the original seq2 reveal bytes.
- Construct a throwaway R22.20 event with a test-only key and synthetic one-row ledger, verify its own profile, then prove both parsers reject the other profile at envelope and event boundaries.
- Tampered and cross-substituted Sigsum proofs must fail the official verifier.
- Assert advisory/global-latest and independent-custody fields remain NOT_ESTABLISHED.

## Limits
This is an offline verification of already-retained synthetic evidence. Sigsum TEST inclusion proves that the exact event-ID message is in the sampled test log under the pinned policy; it does not establish trusted current time, global latestness, long-term availability, independent administration of GitHub/relays/witnesses, A15 custodian admission, actual Ario memory truth, or production authority. The workflow reads artifacts from GitHub Actions, so it is not an independent administrative domain. The test-only R22 key is ephemeral and not exported. The old A15 live run's reveal failure remains visible. No merge, key, floor, policy, trust or production state is changed.
