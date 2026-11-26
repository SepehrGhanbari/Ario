# A15 External Payload Custody Contract v1

**Disposition:** `RESEARCH_ONLY / GAP / NOT_IMPLEMENTED / NO_PUBLICATION / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION`

**Purpose:** distinguish proof that a checkpoint is included in an append-only log from proof that the checkpoint's underlying Broker state can actually be recovered.

## 1. Verified boundary today

The archived A15 checkpoint payload contains:

- `broker_head` (sequence and hash)
- `broker_source` (source commit, blob, and path)
- A15 domain, journal scope, format, enrollment, and previous external checkpoint digest

It does **not** contain the Broker rows or the SQLite database bytes. The Nostr event carries the checkpoint envelope, not the Broker database. The `matched-state/custodian.sqlite3` file in the original CI artifact is test evidence; it is not part of the published A15 event or the external witness floor.

R22.22I verifies a TEST Sigsum tree head using a custom external-only 2-of-4 witness policy and a Remora status readback. Those witnesses attest the tree head. They do not attest that Broker rows or snapshot bytes are stored or retrievable.

Therefore the current result is:

- A15 inclusion and prefix under the external witness floor: **VERIFIED**
- Broker payload availability from an independently administered custodian: **NOT_ESTABLISHED**
- Global latestness: **UNKNOWN**
- Trust activation / production: **NO_GO**

A valid tree-head proof must never be reported as successful Broker-state recovery.

## 2. Required custody object

A future payload-custody stage must define one canonical, bounded snapshot object and a separate manifest. The manifest must bind at least:

- A15 journal scope and checkpoint payload SHA-256
- Broker sequence and Broker head hash
- Snapshot schema/version and canonical serialization format
- Exact uncompressed byte length and SHA-256 of the snapshot bytes
- Compression and chunking metadata, if used
- Snapshot creation sequence and previous manifest digest
- A content identifier that is stable across independent custodians

The Broker head must be recomputed from the recovered snapshot and match the manifest. Merely returning the manifest or its hash is not payload recovery.

## 3. Custodian receipt contract

Each storage custodian must return a verifiable receipt binding:

- Custodian identity and independently pinned public-key fingerprint
- Object identifier and immutable object version
- Manifest digest, payload digest, and exact byte length
- Custodian-local monotonic sequence and previous receipt digest
- Retention commitment / expiry and receipt timestamp
- The exact A15 checkpoint digest and Broker head to which the object belongs

A successful HTTP response, object URL, provider-generated ETag, or witness cosignature alone is not a custody receipt.

The custodian's administrative and credential plane must be separate from the A15 publisher, GitHub repository administrators, and the Sigsum witness operators. A repository-controlled key or GitHub Actions secret is not independent custody.

## 4. Quorum and recovery rules

Proposed research policy, subject to later review:

- **Write quorum:** 2 of 3 independently administered custodians must durably acknowledge the same manifest and payload digest before the custody record can advance.
- **Read quorum:** a cold recovery runner must retrieve byte-identical payloads from at least 2 of 3 custodians and independently verify the manifest, byte length, SHA-256, schema, and Broker head.
- One unavailable custodian may be tolerated; fewer than two matching readbacks is **HOLD**.
- A same-sequence/different-digest receipt is a fork and must be **HOLD**.
- A stale receipt, lower custodian sequence, expired retention, missing receipt chain, or payload/manifest mismatch must be **HOLD**.
- The latest accepted custodian floor must be retained outside GitHub and outside the publisher's control. GitHub artifacts may be mirrors, never the sole floor.

The exact quorum may be revised only through a recorded research decision. The witness quorum and payload-storage quorum are distinct policies and must not be conflated.

## 5. Required cold-recovery acceptance cases

The implementation stage must demonstrate, from a fresh runner with no publisher credentials:

1. Both Nostr relays unavailable and GitHub artifact access denied; recover the full snapshot from two independent custodians.
2. One custodian unavailable; two matching custodians still recover.
3. One custodian returns altered bytes, wrong length, or wrong manifest; reject it and retain the valid quorum.
4. Only one custodian is reachable; return HOLD, not RECOVERED.
5. Same sequence with a different payload digest; detect a fork.
6. Older receipt replay after a newer external floor; reject rollback.
7. Custodian deletion or retention expiry; do not silently fall back to a GitHub artifact.
8. Crash after durable write but before receipt delivery; retry must not create a conflicting object or falsely claim success.
9. Delayed cold readback after the publisher has exited, with no local cache or previous-run workspace.
10. Recompute the Broker head from recovered rows and compare it to the A15 checkpoint.

A test that only retrieves a tree head, manifest, or payload hash does not satisfy these cases.

## 6. Explicit non-goals and current hold

This contract does not authorize or perform a new external upload, key creation, policy activation, merge, or production deployment. It does not treat Remora or Stagemole as payload stores. It does not change A15 or R22 wire formats.

Until a separately administered content custodian exists and the cold-recovery cases pass, report the state as:

`CHECKPOINT_INCLUSION=VERIFIED`
`EXTERNAL_WITNESS_FLOOR=VERIFIED_TEST_ONLY`
`BROKER_PAYLOAD_CUSTODY=NOT_ESTABLISHED`
`GLOBAL_LATEST=UNKNOWN`
`TRUST_ACTIVATION=NO_GO`
`PRODUCTION=NO_GO`
