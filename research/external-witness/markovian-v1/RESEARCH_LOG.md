# MWTL-01 — Markovian synthetic C2SP log research record

**Scope:** RESEARCH_ONLY / SYNTHETIC_ONLY / HOLD / NO_REAL_KEYS / NO_PRODUCTION / NO_TRUST_ACTIVATION.

## 2026-11-27 — Implementation record v0.1

- Added `implementation/research/markovian_test_log_v0_1/markovian_test_log.py` and focused tests.
- Reuses the existing encrypted Ario Kladje research identity and origin `github.com/SepehrGhanbari/Ario/kladje-test-v1`; no new key is generated.
- Emits a C2SP Ed25519 vkey, signed checkpoint, synthetic-only capsule and newline-delimited entries.
- Implements RFC 6962 Merkle roots and consistency proofs, C2SP tlog-witness add-checkpoint framing, and offline verification of the Markovian operator-published witness cosignature key.
- Prepare/append commands make no network calls. Submit is explicit, one-shot, and must only be run after Markovian confirms manual origin/key pinning.
- Private key and passphrase are never printed, copied, packaged, or committed. No personal memory, production data, live witness request, Kladje request, or trust activation.

## 2026-11-27 — Validation record

- Exact tested code head: `3bab3f7f41cd00d5a06275035ded508efe7b3089`.
- Implementation Regression run `45907666533`: **2177 passed, 7 skipped, 2 xfailed, 379 subtests passed**.
- Python 3.14 differential advisory and Windows differential advisory completed successfully.
- Published TXT Restore Security run `45907666523`: all 10 jobs successful.

## 2026-11-27 — Public synthetic checkpoint prepared and independently verified

- Received `Ario-Markovian-Test-v1.zip` from the local desktop signing ceremony.
- Archive contains exactly five public artifacts: `capsule.json`, `entries`, `checkpoint`, `vkey.txt`, and `manifest.json`; no private key or passphrase.
- Independently recomputed the capsule and entries hashes, Merkle root, vkey key ID, and manifest bindings.
- Verified the Ed25519 signature over the exact C2SP checkpoint note text using the public key embedded in the vkey.
- Origin: `github.com/SepehrGhanbari/Ario/kladje-test-v1`; tree size: 1.
- Checkpoint SHA-256: `84ef0c4abc6e06033219f3a34b12c5d4b3893e0a8bd3f082bc7fed1d6e5047cd`.
- Published public artifacts in this research branch only. Markovian manual pinning and witness cosignature remain pending; no add-checkpoint request has been sent.

## 2026-11-27 — MWTL-01 first authorized external cosignature

- Markovian explicitly confirmed manual pinning of origin/key ID 50e6b45c before submission.
- GitHub Actions run 45981121161, job 140444972429, head 26abdbed0612e86075b6a82a0ab5dbc4fad6511e.
- Direct precheck HTTP 404; exactly one POST; HTTP 200; witness cosignature verified using pinned Ed25519 witness key ID 41b8827f. Direct readback HTTP 200 and cryptographic verification succeeded.
- Signed timestamp 2026-11-27T10:19:37Z. Checkpoint size 1, same synthetic leaf. Cosigned note SHA-256: 979b57d71dbf0793d3daab94a82fcb23e03588fc950c04fb90e6e48fdad4d4c2. The returned cosignature was independently reverified offline using cryptography, separate from the runner's OpenSSL verification.
- Public artifact 15189501785; retained exact cosigned checkpoint bytes in cosigned-checkpoint-size-1.txt. Direct readback URL: https://witness.markovianprotocol.com/70f424d9059d85ac8d4f3f18834cad609f29e1caf60dd9250a0099d81c494702/checkpoint
- Scope: RESEARCH_ONLY, one synthetic commitment. This is not a proof of full memory recovery, freshness after rollback, administrative quorum independence, payload custody, or production/Genesis/trust readiness. No additional POST authorized by this record.
