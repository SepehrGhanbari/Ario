# R22.20 — externally retained monotonic floor: Nostr content + Sigsum witness log

RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.

Parent: #372 (R22.15B), head cb87988a3947d36445e8c10a3731bb0fae6a597b. R22.16–R22.19 are already used by parallel research PRs, so this external-custody continuation is numbered R22.20.

## Question

Can a fresh runner, after the publisher has exited and without receiving the later floor bytes or checksum, discover a later monotonic commitment from an externally witnessed append-only log, recover the actual floor content from public relays, and reject stale replay or content loss?

## Architecture

- Re-fetch the exact R22.15B public synthetic artifact (14954102679), pin its ZIP SHA256 and CRC, and verify its six-record Sigsum TEST proof with the archived public key.
- Bind the new session to the exact prior R22.15B envelope hash, ledger hash, and scope. The prior proof and preimage are included in the cold first-only package and reverified there.
- Create synthetic seq=6 anchor and seq=8 successor. The successor contains two new synthetic ledger rows, the exact six-row prefix, previous envelope checksum, previous Nostr event ID and prior ledger digest.
- A fresh ephemeral Nostr Schnorr key signs both content events. Publish them to the public relays nos.lol and relay.primal.net. Relays are untrusted retrieval sources only.
- Submit only each Nostr event identifier (with a newline) to the public Sigsum TEST log using one fresh ephemeral submitter key. The log's cosigned tree head and pinned policy establish witnessed append-only order; the leaf checksum commits to the exact Nostr event ID, whose signature commits to the envelope and ledger.
- The first-only artifact contains the seq=6 event, proof, bootstrap, public keys and prior anchor. It deliberately omits the seq=8 event, its ID and its content. The publisher runner terminates; a separate cold runner scans the live cosigned tree from the first leaf, discovers the second leaf checksum, and only then queries the relays.
- The cold runner verifies the Nostr event ID and Schnorr signature, exact log-leaf checksum, same signer, prior checkpoint, previous event, sequence 6->8, full ledger hash and byte-identical six-row prefix.
- Fault controls: one endpoint is deliberately made unreachable while a real relay is queried; authentic seq=6 event is replayed against the seq=8 leaf; both content endpoints are made unavailable while the witnessed log still exposes the later commitment. Expected behavior is recover via the remaining relay, reject stale event, and HOLD opaque when all content sources are unavailable.

Protocol references: Sigsum proof format and witness cosignatures https://github.com/sigsum/sigsum-go/blob/main/doc/sigsum-proof.md ; Sigsum getting-started and witness/monitor assumptions https://www.sigsum.org/getting-started/ ; Nostr NIP-01 EVENT/REQ/OK/EOSE relay protocol https://nips.nostr.com/1 .

## Security boundaries

Sigsum witnesses protect consistency of the witnessed log under the pinned TEST policy; they do not store the full floor content. Nostr relays store and serve the signed content, but can censor, delete, replay, or withhold it. The client therefore never trusts relay order or relay timestamps; it accepts only the event ID discovered from the witnessed log. If the log reveals a new commitment but no relay returns its preimage, result must remain HOLD_OPAQUE_NEW_SIGNED_COMMITMENT.

The forced one-relay outage is a controlled loopback failure injection, not evidence that a public provider suffered an outage. The both-relays-unavailable case is likewise a controlled client-side outage simulation. Actual relay acceptance and readback, if successful, are recorded separately.

This is still a public TEST log, public relays, synthetic content and ephemeral keys. No permanent private key, durable operator enrollment, real Ario record, production service, admission or trust activation. Public relay operator independence is NOT_ESTABLISHED; Sigsum witness quorum is policy-verified test evidence, not a legal/administrative independence audit. Global latest/freshness beyond the sampled witnessed tree head is NOT_ESTABLISHED. Relay durability and recovery after permanent deletion are NOT_ESTABLISHED. If both relays lose the preimage, only an opaque commitment remains. A new ephemeral signer does not establish continuity of the old R22.15B signer. No physical power-loss or common-root attack is needed for this experiment; the external service boundary is tested, but the publisher/repo cannot control external service operators by assumption alone.

## Expected dispositions

- Valid seq=8 event discovered in Sigsum and recovered from at least one external relay: RECOVERED_LINKED_SYNTHETIC_EXTERNAL_FLOOR_ONLY.
- Only seq=6 event returned for the seq=8 leaf: HOLD_STALE_EVENT_REPLAY.
- Sigsum reveals seq=8 but all content relays unavailable: HOLD_OPAQUE_NEW_SIGNED_COMMITMENT.
- Wrong event signature, checksum, scope, predecessor, prior checkpoint, sequence or ledger prefix: HOLD.
- No authority or production transition is possible.

Execution pending. Record actual run, per-relay acknowledgements/readbacks, Sigsum leaf indices and artifact hashes in a separate addendum.
