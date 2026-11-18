# Ario R63 V10 — Synthetic RPC crash-window and receipt-control lab

**RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO**

This is an additional Windows/Linux GitHub Actions test family, NOT a replacement for the frozen V9 signer, service, guest witness, R60 authorization or native CNG. All mutable files are temporary, the server binds `127.0.0.1`, no security controls or live keys are changed.

## Frozen dependency

The fixture imports a SHA256-pinned copy of the V9 `spend_chain_v2.py` from `../r63_v10_source_gate/`, with SHA-256 `c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd`. Only that frozen sidecar—not the private V9 driver—appears in the research branch.

## 3 crash windows tested

Separate Python TCP parent processes exit with code `73`, prior to an application ACK:

| Crash point | V1 rows | V2 events | State | Expected duplicate response |
|---|---:|---:|---|---|
| before V2 append | 2 | 2 | coherent, no durable new record | HOLD_UNCERTAIN |
| after V2 fsync, before V1 | 2 | 3 | split journals | HOLD_UNCERTAIN |
| after V1 fsync, before receipt/ACK | 3 | 3 | coherent but no receipt | HOLD_UNCERTAIN |

For each scenario a second, separate **local** observer process parses and hashes actual temp V1/V2 files, before and after recovery. A new TCP recovery process handles three concurrent batches (2, 8, 16) of repeated-nonce requests; all 26 should return HOLD, with no write to either journal. **One OS executes 3 × 26 = 78 retries.** The observer is a separate process but runs under the **same OS user/storage trust domain**: this does **not** establish an independently administered witness.

## Positive receipt control

The second source file `test_structural_receipt_controls.py` provides **11 tests**, including 16 subprocess replay verifications of the same unchanged *structural receipt* bytes and negative checks for missing/mutated receipt, wrong nonce, deleted/corrupted V1, corrupt V2, changed event head and reordered rows. This prevents interpreting an unconditional always-HOLD implementation as a successful recovery oracle.

**This synthetic receipt has only local SHA256 content commitments, NOT a cryptographic signature or independently authenticated attestation.** It is NOT a V9 or R60 receipt. Tampering by an administrator with all local files remains possible.

One deliberate negative control proves a **coherent rollback of local V1 + V2 + receipt can still be accepted**; this passing test documents *failure of local-only antirollback*. Another unresolved limit is cross-process time-of-check-to-use after the last read.

## Reproducible CI evidence

- [GitHub Actions full matrix and 11 receipt tests: run 44340256705](https://github.com/SepehrGhanbari/Ario/actions/runs/44340256705), on Windows Server 2022 and Ubuntu 24.04. Both reported 3/3 crash windows and all 78 retries HOLD, then `Ran 11 tests ... OK` for positive and negative controls. Logs and JSON reports are retained as GitHub artifacts.
- [Earlier matrix-only run 44339609974](https://github.com/SepehrGhanbari/Ario/actions/runs/44339609974), both operating systems completed successfully. The earlier run did not yet have the positive controls.
- [Full V9 frozen sidecar CI: 44303352340](https://github.com/SepehrGhanbari/Ario/actions/runs/44303352340), 25/25 per OS; original Windows CRLF-hash failure is preserved separately.

## Manual gate still required

**NOT_EXECUTED**: true native V9 witness RPC parent process death/recovery, actual standard-user 2/8/16-client races against the **V9** broker/service, exact same-key NCryptSignHash enter/return and receipt public verification, crash during receipt persistence and external independent custody.

The actual frozen V9 `WitnessServer` is an RPC **thread within the driver**, not a separate restartable parent; this cannot be solved by merely killing its V8 child writer. A native experiment must first receive a separate scoped design review and a freshly prepared disposable **Windows Sandbox**, with the user's original frozen ZIP unchanged. Do not run the historical launcher in the currently mounted, read-only preflight guest; do not touch real Ario keys, host policies, laptop, Rulesets, branch `main`, or production trust.

**Verdict:** SYNTHETIC_PROCESS_MODEL=PASS; STRUCTURAL_RECEIPT_CONTROLS=PASS; NATIVE_V9_RPC_PARENT_RECOVERY=NOT_EXECUTED; INDEPENDENT_CUSTODY=NOT_ESTABLISHED; A_GOV=NOT_ESTABLISHED; USE_COMPLETENESS=NOT_ESTABLISHED.
