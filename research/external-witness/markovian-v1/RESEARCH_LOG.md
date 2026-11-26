# MWTL-01 — Markovian synthetic C2SP log research record

**Scope:** RESEARCH_ONLY / SYNTHETIC_ONLY / HOLD / NO_REAL_KEYS / NO_PRODUCTION / NO_TRUST_ACTIVATION.

## 2026-11-27 — Implementation record v0.1

- Added \`implementation/research/markovian_test_log_v0_1/markovian_test_log.py\` and focused tests.
- Reuses the existing encrypted Ario Kladje research identity and origin \`github.com/SepehrGhanbari/Ario/kladje-test-v1\`; no new key is generated.
- Emits a C2SP Ed25519 vkey, signed checkpoint, synthetic-only capsule and newline-delimited entries.
- Implements RFC 6962 Merkle roots and consistency proofs, C2SP tlog-witness add-checkpoint framing, and offline verification of the Markovian operator-published witness cosignature key.
- Prepare/append commands make no network calls. Submit is explicit, one-shot, and must only be run after Markovian confirms manual origin/key pinning.
- Private key and passphrase are never printed, copied, packaged, or committed. No personal memory, production data, live witness request, Kladje request, or trust activation.

## 2026-11-27 — Validation record

- Exact tested code head: \`3bab3f7f41cd00d5a06275035ded508efe7b3089\`.
- Implementation Regression run \`45907666533\`: **2177 passed, 7 skipped, 2 xfailed, 379 subtests passed**.
- Python 3.14 differential advisory and Windows differential advisory completed successfully.
- Published TXT Restore Security run \`45907666523\`: all 10 jobs successful.
- No live witness request, public checkpoint publication, merge, or trust activation occurred. The remaining signing step uses the existing encrypted research key locally on the desktop test PC.
