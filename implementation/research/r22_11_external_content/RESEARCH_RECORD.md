# R22.11 — blind external synthetic envelope recovery

RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.

Parent: #356 at 814f69d546d41bb1e30ceac252d215df64d049bc. This experiment repeats the successful R22.10 two-leaf setup with fresh synthetic envelopes and ephemeral laboratory signing keys, then adds content recovery. It does not claim to recover the specific historical R22.10 envelope.

## Protocol
The publishing runner submits both synthetic envelopes to the Sigsum TEST log and verifies both receipts. It publishes only the second envelope, in a public Nostr regular event indexed by a single-letter x tag equal to the Sigsum double-SHA256 checksum. This is an application-level content-addressed lookup, not a native CAS or a durable archive. Public relays are third-party services, not enrolled Ario custodians. A separate temporary Nostr key is used only for this public synthetic event. No actual Ario data or keys are transmitted.

The recovery runner gets only the first artifact. The existing Go scanner verifies a pinned cosigned tree head, consistency, per-leaf inclusion, and same-key signatures. Only after discovery does the recovery client query fixed external relay URLs by the discovered checksum. It verifies the relay event ID and Schnorr signature as transport structure, independently recomputes double SHA256 of exact returned bytes, checks strict canonical envelope schema, scope, previous checksum, advancing record count and changed floor digest. Nostr key identity does not establish Ario authority. The reveal runner compares recovered bytes with withheld bytes. Local state must remain unchanged.

## Controls
Unit tests cover unavailable content, byte substitution, old-content replay, wrong scope, wrong predecessor, nonadvancing count, unchanged floor digest, authority escalation, boolean count, duplicate fields, noncanonical bytes, invalid discovery and tampered relay event. These tests are synthetic controls; live run status must be read separately.

## Boundaries
A matching envelope does not recover the committed floor record itself, verify history truth, guarantee global latest, guarantee relay retention, prove physical rollback or independent latest-floor custody. A relay may delete, omit, censor or return stale content. It cannot substitute different bytes under the same verified checksum without breaking the hash assumption. Failure is HOLD; no fallback to older bytes as current. Same repository administration controls all CI jobs; relay operations and management independence have not been audited. Relay acceptance is not successful readback. Only a successful separate read plus reveal establishes this narrow observation.

## Execution status
Implementation submitted for CI. External publication, retrieval, and reveal are NOT YET VERIFIED at authoring. See exact run and job logs before assigning PASS. No merge or authority activation.

## Verified live observation (2026-11-24)

[Run 45458340278](https://github.com/SepehrGhanbari/Ario/actions/runs/45458340278), exact source/workflow HEAD 200a40e33de27771a2f8606d6c9559f1304d73cd: all three jobs completed SUCCESS. Job logs read directly.

- Publish 138673757580: both official Sigsum TEST proofs verified, both nos.lol and relay.primal.net acknowledged the same second synthetic envelope.
- Discover 138674357777: 16 Python tests passed; inherited Go discovery and complete bounded suffix verification passed. Sampled cosigned tree size 281590, root ec4f2ff9893d9eca53109b209e00576b472d59879ebbe633543c20c6430a9b3c; consistency PASS. First index 281588 checksum db532e57d5bde3ae3aa00030f0d791d467de2b58f04667dc757124849f67ebbf; second index 281589 checksum 42b102e20ba38983f6fa42e35f71de45f3cc6b7029279625baa4d21c61f0249f. Scanner initially returned HOLD_OPAQUE_NEW_SIGNED_COMMITMENT, then separate relay query by discovered checksum recovered valid exact envelope bytes from both fixed relay endpoints. Local-state SHA256 verified unchanged in both steps. RECOVERED_LINKED_SYNTHETIC_ENVELOPE_ONLY; envelope count 4; floor_preimage_recovered=false; global latest, durability, independent latest floor NOT_ESTABLISHED; history truth UNKNOWN.
- Reveal 138674813567: exact recovered bytes equal withheld original, matching discovered checksum and proof index; scope and previous checksum link correct; R22_11_EXTERNAL_BYTES_MATCH_WITHHELD_ORIGINAL. No authority admission or local state change.

Artifact IDs and SHA256 digests from GitHub API, also visible in job logs. ZIP bytes were not independently downloaded/rehashed in this turn; retention expires 2026-12-24.

| Artifact | ID | SHA256 | Bytes |
|---|---:|---|---:|
| FIRST-ONLY | 14950768154 | 893f110774ce8df5c58b29ef394d3cb6980b33b8916e812c63b8785c400573ae | 3873 |
| SECOND-REVEAL | 14950128300 | 01b1dc0ff2219cf126cddb682bda3376b71de4af276e2a9ece35fd638c0ebd1c | 3415 |
| BLIND-DISCOVERY | 14951926469 | 2882f5e99d86071583ccaa47fb63de0456d543f4262bb3643d973dcddee93dd6 | 702 |
| EXTERNAL-RECOVERED | 14951936539 | 97522a32726363d3cf7ca6f70cda9ed78423c5e8c7575387edbf6ac2ca70d9ea | 981 |

Narrow live experiment PASS; disposition remains RESEARCH_ONLY/HOLD. This is not recovery of floor bytes or demonstration of durable independently controlled storage. Next experiment: publish and retrieve the exact synthetic floor-record preimage as a separate object, recompute its commitment, verify the predecessor and floor record against the prior pinned state, and exercise missing, replay, substituted and forked object controls. No merge, real keys, trust activation or production.
