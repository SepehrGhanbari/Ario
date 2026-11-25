# A15 × R22 read-only checkpoint adapter v1

**Disposition:** RESEARCH_ONLY / OFFLINE_ONLY / SYNTHETIC_DATA_ONLY / NO_REAL_KEYS / NO_EXTERNAL_PUBLISH / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_MERGE.

## Source contract and pins

This adapter is stacked on the exact open Draft #346 Broker head:

- Broker source commit: `bfe66cbba60a25086773d1790284eb97e3a6202a`
- Broker source Git blob SHA-1: `612fa44e6eb2cb1078561bca85bb0f69f984bff9`
- Broker source path: `implementation/research/a15_custodian_broker_v0_5.py`

Before reading the ledger, the adapter verifies the exact Git blob object ID of the Broker source file. A changed source blob is HOLD, not an implicit compatibility upgrade.

## Read-only boundary

The adapter deliberately does **not** instantiate `Journal`. The #346 Journal constructor opens SQLite in read-write mode, performs journal/schema setup and may reconcile/write the local floor. The adapter instead:

1. Requires an existing, non-symlink state directory, database, floor and pinned Broker source file.
2. Opens SQLite using a `file:...?mode=ro` URI and confirms `PRAGMA query_only=1`.
3. Establishes one read transaction and requires the pinned `DELETE` journal mode, exact `events` schema, no unexpected SQLite objects/sidecars and `PRAGMA integrity_check = ok`.
4. Recomputes every Broker event hash using the exact insertion-order JSON encoding from Broker v0.5.
5. Reads the local floor before and after the snapshot; any change or mismatch with the observed `(seq, hash)` is HOLD. It never repairs, advances, provisions or rewrites the floor.
6. Emits one canonical JSON envelope to stdout. It writes no checkpoint file and makes no network call.

The Broker database and local floor are never modified by the adapter. The local floor remains a same-administrator guard, not independent custody.

## Canonical envelope

The output has exactly two top-level fields:

- `payload`: format/domain, explicit enrollment mode, opaque `journal_scope`, pinned Broker source identity, observed Broker `(seq, hash)`, and the prior external checkpoint digest.
- `payload_sha256`: SHA-256 over canonical ASCII JSON of `payload` (sorted keys, compact separators, no NaN/Infinity).

No event rows, request IDs, choices, input hashes, user text, or SQLite bytes are emitted. No wall-clock timestamp is included; the adapter cannot establish trusted freshness.

First enrollment requires explicit `--enroll-genesis` and is labelled `INITIAL_BASELINE`. It means “this is the initial externally proposed baseline at the current observed Broker head”; it does **not** prove the history before that head. Later runs require `--previous-checkpoint PATH`. The previous envelope's schema and payload digest are verified, its scope and source pins must match, and the current Broker chain must contain the previous `(seq, hash)` and be strictly ahead. A rollback, same-sequence fork, missing predecessor row or no advancement is HOLD.

The previous envelope is only integrity-checked. A plain SHA-256 digest is not a signature and does not authenticate who retained or supplied the previous checkpoint. Independent custody can be claimed only after a separately administered external source returns the prior checkpoint and the R22 witness/monitor evidence is verified.

## Hold matrix

| Condition | Result |
|---|---|
| Missing DB/floor, symlink, malformed floor, SQLite sidecar, unexpected schema | HOLD |
| SQLite integrity or any Broker event hash mismatch | HOLD |
| Floor changed during read or does not exactly match DB head | HOLD; no repair |
| Previous checkpoint from another scope/source | HOLD |
| Current DB behind prior checkpoint | HOLD rollback |
| Prior sequence exists with a different hash | HOLD fork |
| Current DB has not advanced | HOLD no new checkpoint |
| Exact prior checkpoint present and DB strictly advances | Canonical continuation envelope |

## Offline tests

`python -m unittest discover -s implementation/tests -p test_a15_r22_readonly_adapter_v1.py -v`

The GitHub workflow runs the synthetic contract tests on Ubuntu and Windows. Tests cover source pinning, explicit baseline enrollment, canonical envelope privacy, read-only byte/mtime/directory invariance, continuation, same-admin joint rollback detected only when a prior checkpoint is retained outside the rolled-back state directory, same-sequence fork, stale/tampered floor, duplicate JSON keys, tampered Broker hash chain, unexpected schema, SQLite sidecars, source mismatch and CLI behavior.

## Explicit limitations and next gate

- This is an offline adapter contract only. It does not contact Sigsum, Nostr relays or R63 monitors.
- No signature, external timestamp, trusted freshness, global latestness, independent administrator, or persistent key continuity is established.
- A prior envelope stored under the same administrator can be rolled back with the Broker. The joint rollback test demonstrates detection only when the prior checkpoint is retained outside the rolled-back local state.
- A checkpoint commitment detects divergence/rollback; it cannot reconstruct the private Broker database.
- R63 observations remain advisory consistency checks, not an independent latest-floor authority.
- The next step is separate review of this envelope contract. Only after that review should a new synthetic-only live experiment publish a test commitment through the existing R22.20 path, terminate the publisher, discover/recover from a cold runner, and compare against the independently recomputed A15 head. No real keys or production authority.
