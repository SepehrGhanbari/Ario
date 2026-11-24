# R22.8 — Retained CI floor, receipt reconciliation, and external publication boundary

**RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.** PR #353, parent #352 pinned bb5ff1f88e10e6284e6e7edc7bf2715d614a08c3.

## Reuse, not a new production witness

The prior R9-C #236 source at 709ed2eace327eee20196118ab6bda2687c7f60e is copied at its original path, experiments/r9c-conditional-destination-2026-11-15/r9c_conditional_destination.py. Git blob 8cfaa04e948c12fbc7a7c0d64d219d4a2146ab7f verified identical after copying. R22.7's floor comparator, retained records and synthetic observer are unchanged. The test-only adapter commits a domain-separated digest of the complete canonical retained floor, including scope and two anchors, to R9-C's separately persisted witness checkpoint chain. Journal counts 2 and 4 correspond to protocol event indices 2 and 3 following a fixed scope/epoch record at index 1. These counters have different meanings.

The verifier checks candidate correspondence against the R22.7 floor, destination/witness head agreement, lookup by the exact floor operation ID, receipt MAC, exact expected epoch/index/payload and event digest. A positive result is MATCH_LAB_RECEIPT_TIP_ONLY, never authorization or historical truth. The service processes use synthetic ephemeral HMAC material and independent local SQLite files, not independent administrators or a remote service. The verifier shares lab keys. Neither symmetric MACs nor the test harness establish public verifiability or sender independence.

## Executed evidence

Source/test head 239bd20344fc20984fe556907ca3f710912ed8af. [Implementation Regression 45440113189](https://github.com/SepehrGhanbari/Ario/actions/runs/45440113189) 3/3 successful. Linux 3.13 and 3.14 each 2097 passed / 8 skipped; Windows 2067 passed / 29 skipped (Linux POSIX lab is skipped at module collection), 273 subtests and two warnings in each environment. [Self Audit 45440113398](https://github.com/SepehrGhanbari/Ario/actions/runs/45440113398) and [TXT Restore 45440113657](https://github.com/SepehrGhanbari/Ario/actions/runs/45440113657) success.

Ten Linux cases pass: current tip positive and unrecorded extension HOLD; actual publisher DB + local floor rollback with witness DB retained; deliberate shared-admin reset of both DBs and floor; unavailable witness and recovery; witness process exits 76 after SQLite commit before reply, and destination exits 75 after commit before reply; both reconcile using existing read-by-operation-ID path and idempotent witness checkpoint; authentic stale proof refused; old correctly MACed response fails fresh nonce; resealed same-count floor cannot reuse original commitment receipt; duplicate retry has exactly two destination effects and three witness checkpoint rows, no new effect. Joint-admin rollback remains an intentional residual. The response-replay test injects captured response at the client reader, not an observed compromise of socket transport.

## Real external TEST-log attempt — separate from local recovery

The existing W36 proof is pinned to W35 bytes and cannot authenticate this different R22.7 floor. The prior actual Sigsum R6 #273 test-log protocol is reused in a new narrowly scoped advisory push workflow, .github/workflows/r22-8-synthetic-external-floor.yml, head 7ddbc9b823d4ebde90663fdd72e85634ba0cd268. It deterministically generates two public synthetic envelopes, containing only count, scope digest, complete floor commitment digest, and explicit non-authority fields. Only the count-four envelope is submitted to the external Sigsum TEST log; the count-two envelope is a distinct negative input for offline verification against the count-four proof. Ephemeral synthetic signing key is deleted and never archived. No private Ario data, original keys, private journal or real event inventory. The public test submission, if successful, is irreversible.

The workflow requests a proof under sigsum-test1-2025 and version-pinned v0.14.1 tools, verifies inclusion offline, rejects the older different bytes using the same proof, and archives public artifacts only. It does not replace W36's existing pins, automatically adopt a new trusted key or prove the current latest external floor. Submission and verification must be observed before claiming success; the artifact has 30-day retention. A successful proof only shows a commitment was published, not that any publisher or client has no ability to replay an older valid proof. Independent current high-water retention and authenticated coverage remain NOT_ESTABLISHED. No new production authority or deployment.

## Remaining blockers

- Shared administrator controls the local services, HMAC keys and all local storage. R9-C provisioning can create a new journal when local storage disappears; the preserved other head exposes a difference, not a guarantee against joint resets.
- The caller is a synthetic oracle, not an authenticated GitHub event feed. Missed events cannot be recovered from hashes.
- A separately administered, independently retained latest floor and pinned verifier policy still must be established. External inclusion, nonce responsiveness and idempotent reconciliation do not establish global freshness or a lease.
- No real action, signer, trust activation, production, M0 admission or merge. Later CI must be tied to exact HEAD, not inferred from prior source/test run.
