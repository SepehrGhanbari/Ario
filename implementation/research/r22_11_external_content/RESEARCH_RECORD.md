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
