# A15 Floor / Operator v0.4 — temporal admission and durable nonce experiments

Date: 2026-11-24  
Status: **RESEARCH_ONLY / DRAFT_CANDIDATE / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_MERGE**  
Parent research: PR #342 pinned at `17f5e8617b7d48f5e7e2a6870c65cb6ad402602e`; supplied v0.3 ZIP SHA-256 `834f5187ea7cbf7a6eedb501dd544ce254f3b4e08667c15769041f3bbaa97873`.

This is a **local, new-version candidate** addressing the three reproduced v0.3 REDs (F1, F2, F3), not a retroactive modification of v0.3 or earlier artifacts. The source does not implement or claim a real independent administrator, actual authority key custody, native peer authentication, or trust activation. The joint-administrator rollback RED remains deliberately reproducible.

## Contract changes

### F1 — current admission versus historical verification

`openFloor(dir, serviceConfig).advance(input)` evaluates freshness using `Date.now()` inside the Floor process. It signs an `accepted_at` timestamp in the Floor event. A separate `verifyAdvance(signed, floorPublicKey, authorityPublicKey, authorityPin)` verifies canonical request/authorization binding, the pinned cryptographic signatures, and the authorization time window *as of the signed* `accepted_at`, rather than as of the verifier's current clock. Expiration of an already recorded authorization does **not** invalidate historical evidence.

**Limit:** a Floor-admin or OS-admin who controls the signer or the host clock can lie about `accepted_at`. The signed timestamp is a service claim, not an independent trusted timestamp. Recalculated current freshness for an expired new request still fails.

### F2 — untrusted clock injection

The `advance(input)` request has exactly four fields in order: `request`, `seq`, `prev`, `authorization`. It cannot contain `now`, `floorPrivateKey`, `head`, or an authority public key. The signing private key, authority pin, and current clock are not derived from transport/request input. `advance(input)` computes `request_sha` and `head` itself and refuses unsigned/expired/future/changed authorization. The user-supplied preference/authorization provenance problem outside this synthetic contract remains unknown.

**Limit:** the test fixture provisions both synthetic Ed25519 keys under one local administrator. That is **not** independently enrolled/controlled authority. A caller with the ability to modify the service constructor or the machine time is outside this limited threat boundary.

### F3 — scoped, persistent nonce consumption

Nonce namespace is `SHA256(canonical({authority_sha256, principal, scope, nonce}))`. The Floor stores a nonce-specific `intent-*.json` via exclusive-create, file fsync and directory fsync **before signing**, then durably replaces a journal containing the signed receipt. Read-back verifies the entire signed chain, nonce uniqueness, intent-to-receipt binding, and exact submission digest; replays return the identical stored signed event. A conflicting request with a previously used nonce returns `HOLD_NONCE_REUSE`. After durable intent, the Floor checks its own clock **again immediately before signing**, refusing a grant that expired during fsync or a synthetic pause and leaving the intent pending. A pending intent after a crash returns `HOLD_UNCERTAIN_PENDING_INTENT` and is not silently consumed again.

The Operator v0.4 independently verifies uniqueness of scoped nonces across its *retained historical journal* and across proposed batches of future events, without rechecking expired grants against today's clock. The Floor validates full journal state under the exclusive write lock, so simultaneous processes never mistake a currently written `.tmp` file for a completed record. Read-only status queries can conservatively HOLD while another process writes. The Operator keeps the v0.3 ownership/mode/symlink, fsync and conservative recovery restrictions. A reboot never releases a consumed nonce merely because authorization TTL expires.

**Limit:** the two local directories and synthetic keys are still under the same administrator; a coherent rewind of Floor + Operator state allows an alternate signed fork. Durability assumes a local POSIX filesystem with working fsync; there is no tested power-loss guarantee, independent storage or independently controlled minimum. A stale Floor lock is never auto-deleted. A person-controlled/ independently supervised recovery procedure is required for any real deployment; tests manually remove stale lock files **only after confirming the synthetic child process has exited**.

## New source / tests

- `implementation/research/a15_external_floor_simulator_v0_4.js`: local service core, signed admission timestamp, strict request envelope and authority verification, nonce intents, durable journal, exclusive lock, receipt replay.
- `implementation/research/a15_outside_minimum_custodian_v0_4.js`: minimum operator adaptation with historic-time validation and nonce uniqueness both on replay and on candidate admission.
- `implementation/tests/test_a15_v0_4_temporal_nonce.js`: 34 synthetic controls, including the retained joint-admin rollback RED.
- `implementation/tests/fixtures/a15_v04_floor_worker.js`: spawned child for actual process-exit and simultaneous-process probes, using disposable synthetic test keys and files only.
- `.github/workflows/a15-v04-temporal-nonce.yml`: proposed Linux Node 22 CI for v0.4; **not published or triggered** by this local package.

## Observed validation on 2026-11-24

- Node `v22.16.0`, Linux sandbox, local temporary directories and synthetic Ed25519 keys only.
- Historical v0.1/v0.2 research suite: **40/40 PASS**.
- Supplied v0.3 suite: **15/15 PASS**.
- New v0.4 temporal/nonce/fault suite: **34/34 PASS** (contains one deliberately expected RED, joint-admin rollback).
- Aggregate: **89/89 test executions passing**, but this is **not 88 security properties proved**.
- The separately supplied v0.2 RED reproducer returned `reproduced: true` for the unbound-head, shared-admin minimum reset and world-writable operator directory baseline controls.
- Actual child exits at `AFTER_DURABLE_INTENT` and `AFTER_DURABLE_RECEIPT` reproduced; post-crash lock prevents automatic reuse until explicitly removed in a controlled *test-only* cleanup. After an intent-only crash, nonce stays `HOLD_UNCERTAIN_PENDING_INTENT`; after durable receipt, replay returns identical bytes.
- Two distinct Node processes contending for identical or different nonces were run against one Floor directory; exactly one new receipt was durably accepted. All 34 new tests were repeated **five times**, each pass 34/34, to check local race stability. Tested local filesystem, not clustered or multi-host locks.

## Independent challenge obligations and blockers

1. **Independent authority enrollment is missing.** Signature verification and a matching caller-supplied pin are insufficient evidence of independent policy/key custody.
2. **OS-native peer identity is missing in this v0.4 module.** The previously separate Linux SO_PEERCRED and Windows SID research must be integrated and tested without exposing the Floor constructor/private keys to Gate.
3. **External administrative custody is missing.** The common-admin joint-rollback test is intentionally RED. Requires separately controlled account/host, independently retained minimum and backups, and out-of-band pinned key/provenance.
4. **No independent trusted clock or time witness.** `accepted_at` is Floor-signed but not externally attested; same-admin clock adjustments and host compromises remain open.
5. **Crash recovery is incomplete.** A verified supervisor/service-manager protocol must distinguish stale locks from active service instances, reconcile pending intents independently, and never clear uncertain records automatically.
6. **Durability, storage attacks and concurrency**: physical power-cut, fsync-error injection, NFS/distributed filesystem, multi-host simultaneous writers, full state restore, and filesystem TOCTOU were not proven secure.
7. **Windows is NOT_RUN**, and the Operator remains deliberately POSIX-only because its directory-fsync contract fails closed on Windows.
8. **No Broker integration**: do not describe these new modules as patching the live v0.1 Broker's IPC. The current modules remain lab-only. Gate self-claimed authorization, user intent provenance, and real signer use are not established.

## GitHub handoff (NOT AUTHORIZED BY THIS FILE)

Any prospective publication requires separate explicit approval under `AGENTS.md`: create a fresh research branch based on the current pinned #342 head, add only the six paths above, append a dated and hash-pinned section to the **current** `ENGINEERING_LOG.md` (never overwrite it with an older ZIP), run exact-head Linux CI, ask reviewers, keep Draft/HOLD, and do not merge. Preserve original v0.3 and earlier files byte-for-byte. This local ZIP is **not a published PR**.

**Disposition:** `PASS_SYNTHETIC_LOCAL / JOINT_ADMIN_ROLLBACK_RED / INDEPENDENT_CUSTODY_NOT_ESTABLISHED / HOLD`.
