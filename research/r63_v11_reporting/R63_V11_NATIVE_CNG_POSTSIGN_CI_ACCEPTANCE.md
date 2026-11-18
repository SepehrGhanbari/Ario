# R63 V11 — Native disposable CNG post-sign forced-exit acceptance record

**Date:** 2026-11-18  
**Scope:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE  
**Controls:** GENESIS=NO_GO / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO

## 1. Inputs and provenance

- Frozen founder-supplied V9 ZIP SHA256: `db8f1b1a76795589d905fac3f52c1ec32323611585897dd9eb94b259ec6581e9`.
- Frozen extracted `Input/spend_chain_v2.py` SHA256: `c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd`; test fixture requires this exact byte hash.
- All tests ran on GitHub-hosted disposable **Windows Server 2022**. No V9 signer service, V9 RPC handler, LocalService account, real Ario key, TPM R51, host security policy or live trust authority was accessed.
- New CI-only sources: `research/r63_v10_native_replay_ci/Invoke-DisposableCrashSigner.ps1`, `test_native_postsign_recovery.py`, existing public-only `Invoke-NativePublicReceipt.ps1`, `verify_durable_snapshot.py`, and synthetic payload generator. CI workflow: `.github/workflows/r63-v11-native-postsign-crash.yml`.

## 2. Exact test conditions

Two distinct disposable Microsoft Software KSP ECDSA-P256 test keys, one per scenario. Each producer records a bounded fsynced sign-use intent before direct `NCryptSignHash`, records call return, verifies public signature, explicitly deletes the test key and checks it is absent; then **deliberately exits with code 73 after key cleanup**. This is not a power cut, mid-crypto process kill, native V9 broker or independent witness.

| Scenario | New signature made in producer | Durable public receipt | New process recovery | 2+8+16 replay requests |
|---|---|---|---|---:|
| `AfterSignBeforeReceipt` | observed `ENTER=1, RETURN=1` | absent by design | `HOLD_UNCERTAIN`, no retry sign | 26/26 |
| `AfterReceiptBeforeAck` | observed `ENTER=1, RETURN=1` | present, flush+fsync before forced exit | verify with public SPKI plus expected local pin; replay **identical receipt bytes** without new signing | 26/26 |

The second recovery path also checks **current canonical V1/V2 event chain and signed payload metadata**, plus fsynced use-entered/returned marker consistency, before and after signature validation. These are *process-level checks*, not an atomic lock or independent custody.

## 3. CI run history (preserved RED and GREEN)

- [Initial positive split recovery — PASS: #44348963935](https://github.com/SepehrGhanbari/Ario/actions/runs/44348963935). The experiment originally verified signature but did **not** recheck the live V1/V2 state on each replay.
- [Deliberate current-V1 staleness regression — RED: #44349371399](https://github.com/SepehrGhanbari/Ario/actions/runs/44349371399). Error `STALENESS_BUG: valid receipt replayed over changed V1`. This **demonstrated a defect in the research replay candidate**, NOT in the actual V9 signer.
- [Recheck V1/V2 + markers on each replay — GREEN: #44349718404](https://github.com/SepehrGhanbari/Ario/actions/runs/44349718404). Expected `HOLD` for changed V1, with unchanged positive receipt replay.
- [Stricter evidence-format control — RED: #44350010157](https://github.com/SepehrGhanbari/Ario/actions/runs/44350010157). `metadata.json` truncated by only its final newline still parsed to the same JSON object; this was a **byte-format ambiguity**, not proof of semantic forgery. Required an explicit canonical metadata format and exact LF behavior on Windows.
- [Final V11 test suite — GREEN: #44350627029](https://github.com/SepehrGhanbari/Ario/actions/runs/44350627029), after a *single batch commit* `d8ee9790577bc88ad4468efefb1322c9fd5933b6` pinned exact canonical metadata encoding, sign-use marker LF and expected pin bytes. Job completed successfully: `AfterSignBeforeReceipt`: exit 73, 26 `HOLD_UNCERTAIN`; `AfterReceiptBeforeAck`: exit 73, 26 exact publicly verified receipt replays. Total **52/52 bounded synthetic post-sign recovery requests**.
- [Complementary V10 public-only CNG run — GREEN: #44350626897](https://github.com/SepehrGhanbari/Ario/actions/runs/44350626897): observed `NCryptSignHash` enter/return = 1/1 and disposal of ephemeral key; `CURRENT_JOURNAL_AND_PAYLOAD_BINDING=PASS`; **15/15 snapshot tests** and **7/7 stored-receipt mutation controls**, with positive receipt replay preserved.

Logs and bounded non-secret artifacts are attached to those GitHub Actions runs (30-day retention). The original failures were not erased.

## 4. Negative-controls interpretation

- Valid P256 signature plus a self-embedded public key is insufficient to establish authority. Passing the **expected public pin as a separate argument** reduces accidental self-trust but **does not create administrative independence**, because the test pin originates from the same runner and is stored alongside the receipt.
- V1/V2 post-check edits can still occur after the final reread; the test has no atomic filesystem snapshot, enforced cross-process exclusion, or external antirollback anchor.
- Coherent same-admin rollback of V1+V2+receipt+pin is a known counterexample, previously demonstrated separately.
- `NCRYPT_ENTER=1 / RETURN=1` counts *instrumented calls in this test producer only*, not all possible uses of a target key across OS processes. The forced exit occurs **after** explicit key deletion; it cannot establish that a real signer crash during crypto does not leak a key or double sign.

## 5. Remaining native acceptance gate

**Not executed:** separate actual V9 witness RPC process (V9 originally runs RPC as a thread), LocalService broker authority and standard-user client races; actual post-crypto crash before cleanup/receipt durability; exact V9 signed receipt recovery; OS-level complete key-use telemetry; external independent signer/witness custody; hard power-loss and filesystem rollback checks.

**Required for a future disposable Windows Sandbox test:** source-reviewed process split with explicit inter-process locking or durable transaction boundary; synthetic key only; distinct token SIDs, complete deterministic process/PID evidence; no silent journal repair; fail-closed uncertainty and public-only receipts. Historical V9 ZIP remains frozen. No real keys, host/laptop security changes or GitHub main/Ruleset edits are allowed.

**Verdict:** `SYNTHETIC_POSTSIGN_ABORT_WINDOWS=PASS`; `STALENESS_REGRESSION=RED_THEN_GREEN`; `FORMAT_CANONICALIZATION=RED_THEN_GREEN`; `NATIVE_V9_WITNESS_CRASH=NOT_EXECUTED`; `USE_COMPLETENESS=NOT_ESTABLISHED`; `INDEPENDENT_CUSTODY=NOT_ESTABLISHED`.
