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

## Verified execution — 2026-11-25

[Final fully audited run 45656119263](https://github.com/SepehrGhanbari/Ario/actions/runs/45656119263), exact source HEAD 1735ee01a631d558826a8f59b57e08992cd6d510: publish, discover and audit jobs all SUCCESS. The cold runner verified both the prior R22.15B signed checkpoint and the first new event proof, received no second event or second checksum, scanned the live cosigned tree, discovered exactly two matching leaves from the new ephemeral Sigsum signer, and recovered seq=8 from Nostr.

- Prior R22.15B artifact 14954102679 ZIP SHA256 d3b860cc3c0167e8d709a5336a26be231e8143e188b2094250e3fbb1f71ea3db; prior envelope SHA256 331b2888e2a6910b2c731e48ddad5d9f950e5d2f66e4bc7bc378eac55c3db8d8.
- Both relays accepted and returned both events after the publisher job ended: nos.lol and relay.primal.net. The cold readback also succeeded independently from both.
- Sigsum live scan: complete suffix PASS; first leaf index 281660, checksum 21c7cfeb32d57f4904219a58083f8146f5ad029b4a4d627cf5cc46d510a39b3d; second leaf index 281661, checksum be30269b059f132780856dbec15b66e14b1faa811e99a977c7ecdb377511cd8d; sampled tree size 281662, root d90587b3caa90db6a6936507ad2dfdbd870f4c22fc08c0c623baba78e9335ac5.
- Recovered Nostr event ID 58e59d92ffe699b870574e8604450a3785d089dd5c89154df867ea2e4e3a4a77; recovered seq=8; ledger SHA256 2d6f47d5d81cef5d7a8ba295f87da1ccfca69b66e6d2afcfd2c17fb80f398fed. The reveal-stage audit compared recovered envelope, ledger and event byte-for-byte with the withheld publisher copy.
- Fault controls: forced local endpoint outage + surviving real relay => PASS; old seq=6 event replayed against seq=8 leaf => HOLD_STALE_EVENT_REPLAY; both content endpoints deliberately unavailable while Sigsum still exposed the newer leaf => HOLD_CONTENT_UNAVAILABLE / HOLD_OPAQUE_NEW_SIGNED_COMMITMENT.
- Final artifacts: FIRST-ONLY 15043430796 SHA256 6b9620ab9ecfd2c53167751d33390398696ca170f8323b659779184ab30e65ad (11365 bytes); SECOND-REVEAL 15043196552 SHA256 da9be84a51aae427c6d88b24edc4b948756258b464faa62cf2d446542c466a1e (7093 bytes); BLIND-RECOVERY 15042358395 SHA256 025778503d12accea55aac121e0290c26a48953db60a9ba0fb7ed24a7d115ca9 (6881 bytes); AUDIT-REPORT 15042936651 SHA256 c071da63fc5178e525b7da40c8bdf32e403cb3615a5e3653b0ebe07d04bf2afb (671 bytes). Artifact downloads were checksum-verified by Actions; expiry 2026-12-25.

Earlier harness attempts had implementation/orchestration failures (escaped token expression, CLI arity, directory hashing, and audit-report selection). They are not counted as evidence. Some failed attempts left synthetic public TEST events and an orphan first-leaf commitment on public test infrastructure; no private key or real user data was published. The final run above is the one used for the PASS claim.

**Disposition:** bounded external blind-recovery experiment PASS. Not proof of permanent relay availability, relay-operator administrative independence, global latest/freshness beyond the sampled witnessed head, historical truth, persistent signer continuity, production readiness, or trust activation. If both relays delete/withhold the content, only the opaque Sigsum commitment remains. R22.20 remains RESEARCH_ONLY / HOLD.

## Repeat confirmation after workflow path hardening

[Run 45656683810](https://github.com/SepehrGhanbari/Ario/actions/runs/45656683810), source HEAD ef7af73a6b02abe43f725d1d6c556520d8bfb5aa: publish, discover and audit all SUCCESS. This repeated the full blind workflow after narrowing workflow path filters to executable Python sources and the workflow file, so documentation-only changes no longer republish public test events.

- Sigsum live scan: first/second leaf indices 281662/281663, checksums accc839bc70d2c1ef672b44d532546b2ae680c4bcbd46ebe48188cbfd7e02adb and c256633ce89c63c7fc507a0e46dd9d67ed7f8224bc93cde80ae002acd6c8b679; sampled tree size 281664, root 390cb805b80935f2961f7f44aa7419e6071dfe06b97921b578673e498c0908ee.
- Both nos.lol and relay.primal.net accepted and returned the later event. Cold recovery returned seq=8; event ID adf82208b79d9bf43cd89dcdd5d898ac2be6ed48d6e6b644126ad2526cd51b1c; ledger SHA256 2f4dc31993e113e884ebdc0befd6b7e7a21b28282093b32e35f68531bcf0faa0.
- Forced one-endpoint outage fallback PASS; old event replay HOLD; both content endpoints unavailable => HOLD_OPAQUE_NEW_SIGNED_COMMITMENT. Reveal audit passed.
- Repeat artifacts: FIRST-ONLY 15043316960 SHA256 91f96a3bcb004e8d7fbd6e6b00810a9fe63f6a65d3d1ff2defcf3824ec53a83f (11400 bytes); SECOND-REVEAL 15043212139 SHA256 33e4d317a158f7c1b7b172dad5c487f2835069d339bc21d5b42820a35d8b0bbd (7127 bytes); BLIND-RECOVERY 15043806153 SHA256 a397fbf574a9244697044c34bf469124fb2e45ebcf522048f293ee5386780075 (6870 bytes); AUDIT-REPORT 15043551374 SHA256 24e2f8374dd4f7d43e4c6b45c758db7cd0ff87d6375731bc670b3e65f92eaace (671 bytes). Expires 2026-12-25.

The same boundaries remain: public TEST only, synthetic records and ephemeral keys; relay operator independence, durable availability, global latest, event truth, old signer continuity and production trust NOT_ESTABLISHED.
