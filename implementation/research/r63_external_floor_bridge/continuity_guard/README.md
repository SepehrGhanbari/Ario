# R63 witness continuity guard — research lab

**Status:** `RESEARCH_ONLY / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE / GENESIS NO_GO`.

## Problem

A witness signing key can survive while its durable checkpoint database is lost or rolled back. A key signature alone therefore cannot establish that the witness still remembers the history it previously certified.

## Protocol model

- Four separately identified anchor roles are configured; three matching authenticated reads and three durable writes are required.
- Each anchor has its own SQLite file and ephemeral Ed25519 key in this laboratory model. The anchor persists its checkpoint before returning its signed commit receipt.
- The witness's genesis initialization is consumed by a 3-of-4 marker **before** the local witness database is created. A crash after marker quorum but before local database creation retires/quarantines that identity rather than permitting same-key reinitialization.
- Startup uses a fresh nonce and requires at least three authenticated anchor replies for the same checkpoint. A higher unquorummed head, same-sequence fork, insufficient read quorum, or missing initialization marker produces `HOLD`.
- Local missing, corrupt, or older-than-anchor state produces `QUARANTINED`; the same identity/key cannot initialize again after the external initialization marker has been consumed.
- Each transition is first written as a local pending intent, then accepted by at least three anchors with a witness signature. Only after the anchor write quorum does the local checkpoint advance. Recovery is idempotent.
- Identity continuity proofs carry the witness signature and the raw nonce-bound signed anchor read responses so a verifier can inspect the evidence.
- Replacement after loss requires a new witness identity and a new key. The old identity remains quarantined.

## Results

`python -B -m py_compile continuity_guard.py test_continuity_guard.py` — PASS.

`python -B -m unittest -v test_continuity_guard.py` — **30/30 tests PASS**, including three real child-process exits at pending, after anchor quorum, and after local commit. The process tests emit a Python `fork()` warning because the runner is multithreaded; the child-exit/recovery assertions passed.

Two deliberate RED controls reproduced the limit of the model:

1. Joint rollback of all four anchor stores and the local witness database to the same old snapshot is undetectable.
2. Rollback of three anchor stores plus loss of the fourth, together with local rollback, can also make the old state appear current.

These REDs exceed the stated one-fault anchor assumption, but they matter because all four anchor SQLite files in this test run are on one machine and under one administrator. **They are not independent external custody.** This code proves a protocol shape and fail-closed behavior in a local simulation; it does not establish independent administration, hardware monotonicity, resistance to provider-level rollback, or production readiness.

## Operational precedent and standards boundary

C2SP `tlog-witness` requires the witness to persist the new checkpoint before responding and to make the consistency check plus state update atomic: <https://github.com/C2SP/C2SP/blob/main/tlog-witness.md>.

The `aics-witness` operational guidance says a witness whose database is lost or rolled back must be retired rather than continued with the same identity; its `serve` command refuses to create a missing database: <https://pypi.org/project/aics-witness/>.

This R63 lab is not an implementation of the C2SP HTTP protocol and does not enroll the four local anchors as real operators. The next meaningful test is deployment of the anchor interface across genuinely separate administrative domains, with an out-of-band pinned roster and independently protected monotonic state. Until then, no authority is activated.

## 2026-11-26 — roster and nonce-replay hardening; cross-platform CI

The quorum constructor now rejects: non-exact/duplicate anchor identities, duplicate anchor signing keys, duplicate enrollment keys, and duplicate resolved storage paths. This prevents a nominal 3-of-4 from counting repeated cryptographic identities or the same path more than once. It does not prove different administrators, hosts, cloud accounts, or storage providers.

Seven additional adversarial controls:
- duplicate anchor signing key rejected;
- duplicate enrollment key rejected;
- duplicate store path rejected;
- duplicate anchor identity rejected;
- one old nonce-bound response is excluded while the remaining three current anchors still form quorum;
- two old nonce-bound responses cannot form quorum;
- one rolled-back anchor is outvoted by three current anchors.

GitHub Actions run 45826456385, exact source head 78938af150a542df639bec1e3ed743cdfb186a0a, dedicated workflow with contents:read only and no network/publication:
- Ubuntu Python 3.11: 37 tests PASS.
- Ubuntu Python 3.13: 37 tests PASS, including all three real child-process crash/recovery tests.
- Windows Python 3.11: 37 tests discovered, 34 PASS, 3 fork-only tests skipped (process API unavailable).
- Windows Python 3.13: same 34 PASS, 3 fork-only tests skipped.

Original two RED controls remain unchanged. These tests strengthen only the local protocol model. All four anchor stores remain under one host/admin in the lab; independent custody, protected hardware monotonicity, provider-level rollback resistance, operator admission and production integration remain NOT_ESTABLISHED. RESEARCH_ONLY / HOLD / GENESIS NO_GO.

## 2026-11-26 — independent continuity-proof verifier

Added verify_identity_proof(...) for a third party that already has an out-of-band pinned four-anchor public-key roster, expected witness identity/key, policy hash, and the challenge nonce. It does not learn trust roots from the proof. It verifies the witness signature, every included anchor read signature, every anchor commit signature, exact nonce/scope, distinct responding anchors, initialization-marker quorum, checkpoint hashes, and a single matching 3-of-4 checkpoint. It rejects a replayed nonce, duplicate response, insufficient quorum, modified anchor response, wrong pinned roster, wrong witness key, and same-sequence fork.

Eight new tests (38–45) cover valid third-party verification and these negative cases. GitHub Actions run 45827479141, source HEAD c02c7045b720eab4066e4908e6287ac4fa50c899:
- Ubuntu Python 3.11: 45/45 PASS.
- Ubuntu Python 3.13: 45/45 PASS.
- Windows Python 3.11: 45 tests discovered, 42 PASS, 3 fork-only process tests skipped.
- Windows Python 3.13: same 42 PASS, 3 fork-only process tests skipped.

The proof is independently verifiable only relative to the caller-supplied pinned roster and expected nonce. The nonce proves response binding, not that the four anchor operators are independent or that their state is outside a common administrator's rollback domain. No real operators, real keys, external enrollment, hardware monotonicity, trust activation or production integration. The original two RED controls remain.

## 2026-11-26 — 3-of-4 proof boundary and initialization quorum controls

Three further controls extend the independent verifier suite:
- exactly three of four signed anchor reads are sufficient when the fourth is unavailable;
- an invalid anchor commit signature is rejected even when its read response is re-signed;
- fewer than three initialization markers is rejected.

[CI run 45828036041](https://github.com/SepehrGhanbari/Ario/actions/runs/45828036041), source HEAD e44e95632b58d75fdf34c371a8b9ed5e04cb134d:
- Ubuntu Python 3.11: 48/48 PASS.
- Ubuntu Python 3.13: 48/48 PASS.
- Windows Python 3.11: 48 tests discovered, 45 PASS, 3 fork-only tests skipped.
- Windows Python 3.13: same 45 PASS, 3 fork-only tests skipped.

The verifier is a research function. Its security still depends on the caller retaining the correct four-key roster and the fresh challenge nonce outside the witness's control. The local lab cannot establish independent anchor administration or resist rollback of all four stores under a common administrator.
