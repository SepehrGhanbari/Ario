# R63 G3 — Windows PowerShell 5.1 founder HOLD, reproduced RED and fixed GREEN

**Date:** 2026-11-19  
**Status:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO

## 1. Original founder evidence — original bytes examined, not published

Three founder-supplied files were inspected, with SHA-256 recomputed from the original uploads:

| Original file | SHA-256 |
|---|---|
| `R63-G3-Report-4824-b28df79.json` | `4a08686d8b42bb3b2d83585eaf941fa072955355f73dd9112672c2d6e8d948ea` |
| `R63-G3-Run-4824-b28df79.txt` | `fc403e03b9f6b77d08f1ba97375b1a83ea6518ba1c75dfeabc754b379106f67c` |
| `R63-G3-Launch-2218-20326.txt` | `dad0917b499c85c64d9cbdcb7ebf91657857558e84017fdb48f8e08f7a931c04` |

Run and report agree: `G3_HOLD=System.Management.Automation.RuntimeException WITNESS_EXIT_WRONG__EXPECTED_0_`, `G3_VERDICT=HOLD`; cleanup `PASS`. The launch log reports the same error and exit 1. `report.results={}`, so **none of the normal-case/three-crash-case final acceptance records exist**. There is no G3 evidence ZIP from this attempt.

The recorded guest source SHA256s match the original distributed package: `witness_g3.py` `38fa8b7bd1e6492e9f448b4ed30d1d31e590a7569495252e0898affa7d6a4a56` and original `Invoke-G3-WitnessLab.ps1` `ff3d3368e89b75643884c419a437ef2b325649c1868ed31d359fc81f7a9b2463`. Frozen V9-sidecar SHA `c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd` matches. No V9 signer/service, real key or crypto operation occurred.

## 2. Exact reproducible tooling defect

`Invoke-G3-WitnessLab.ps1` starts the witness with `Start-Process -Credential ... -PassThru -RedirectStandard*`, then after 26 synthetic client requests does `$job.process.WaitForExit(...)` and compares `$job.process.ExitCode` with integer `0` in `AwaitExit`. The observed error has an **empty numeric slot** before `_EXPECTED_0_`, consistent with PowerShell returning `$null` rather than an OS-reported nonzero exit.

The issue is known upstream: https://github.com/PowerShell/PowerShell/issues/19411 and https://github.com/PowerShell/PowerShell/issues/5421 discuss `Start-Process` losing `ExitCode` when different credentials, redirection or process-handle caching are involved. This does **not** demonstrate failure of witness journal integrity or DACL; it demonstrates missing process-exit telemetry in the controller.

**Controlled RED reproduction:** [GitHub Actions #44573475573](https://github.com/SepehrGhanbari/Ario/actions/runs/44573475573), Windows Server 2022, invokes controller with native Windows PowerShell **5.1** and reproduces precisely `WITNESS_EXIT_WRONG__EXPECTED_0_` (HOLD), even though previous pwsh7 G3 CI was green.

## 3. Minimal fail-closed fix verified on both PowerShell generations

Changed only the research-only controller `research/r63_g3_witness_ci/Invoke-G3-WitnessLab.ps1`: immediately after starting a long-lived alternate-user witness process, cache its `$p.Handle` **before** waiting for exit. If the handle is unavailable/null, fail closed rather than treating missing `ExitCode` as zero.

**Exact tested Git blob:** `654ccb13cea8e96edad51415e0058aa6a208d39e` (commit `efd2a78db315e88ea345d8e84d02870cbcd626eb`).

**Controlled GREEN verification:**
- [Windows PowerShell 5.1 — Actions #44573871211](https://github.com/SepehrGhanbari/Ario/actions/runs/44573871211): completed SUCCESS, native guest-compatible Windows PowerShell 5.1 runner. Direct job log shows `G3_NORMAL_WRITER_RPC_V1_V2_CANONICAL=PASS`, 2/8/16 independent client processes PASS, 4/4 initial direct DACL denials, all three `PRE_V2/POST_V2/POST_V1_EXIT73_RETRY_HOLD=PASS`, `G3_TEMPORARY_CLEANUP=PASS`, `G3_VERDICT=PASS_SYNTHETIC_G3`.
- [PowerShell 7 — Actions #44573871166](https://github.com/SepehrGhanbari/Ario/actions/runs/44573871166): native G3 witness and both pure-auditor jobs completed SUCCESS; analogous exit-73/HOLD verdicts confirmed from logs.

Old failing runs and evidence remain untouched.

## 4. New founder-only, non-autorun, fresh Sandbox package

Created locally; **not publicly uploaded to GitHub** because it contains a host-specific `.wsb` mapped-folder path:

- `Ario-R63-G3-PS51-ExitCode-Fix-Sandbox.zip`
- **SHA256:** `aac27c465f7a8596e651479cd4b625f49459d3ccd4c34bd23c58716e400d740a`
- **25,669 bytes; 11 members; 10/10 SHA256SUMS matches; ZIP CRC clean.**
- Controller is byte-for-byte the tested Git blob `654ccb13cea8e96edad51415e0058aa6a208d39e`. Witness module, frozen V9 V2 module, auditor and launcher CMD were unchanged from original package. All pure-Python checks: `witness_g3.py --test` PASS, `test_audit_g3.py` **7/7 PASS**, `audit_g3.py --self-test` PASS.
- WSB now expects a **new extracted host directory** `C:\Users\xx4773\Documents\Ario-R63-G3-GuestLab-PS51Fix`; guest still mounts source `C:\R63-G3-Input`. Windows Sandbox networking, clipboard and vGPU disabled, no LogonCommand/autorun, readonly source/runtime maps and evidence-only writable map into `C:\Users\xx4773\Documents\Ario-R63-V10-Manual-Exports`.
- User must start a **fresh** disposable Sandbox and invoke the guest-only CMD manually, never on the host. If HOLD, submit log and do not alter host policy or repeat without review.

## 5. Limits / decision

**GREEN in CI:** test-only Windows SID restricted writer and reader, valid synthetic V9-format V1/V2 chains, cooperative lock, direct access denial, recovery HOLD, correct parent exit code collection under PowerShell 5.1 and 7.

**NOT EXECUTED:** exact revised ZIP in founder Windows Sandbox; the actual original V9 witness parent, actual signed receipts, independent custodian, administrator-resistant rollback, true atomic two-file transactions and power-loss resilience.

`G3_OLD_FOUNDER_SANDBOX=HOLD`, `G3_PS51_CI_FIX=PASS`, `G3_PS7_REGRESSION=PASS`, `G3_FIXED_FOUNDER_SANDBOX=NOT_EXECUTED`, `NATIVE_V9_RECOVERY=NOT_EXECUTED`, `INDEPENDENT_CUSTODY=NOT_ESTABLISHED`, `PRODUCTION=NO_GO`. No real Ario keys, host DACL or security policy, Ruleset or main changes.
