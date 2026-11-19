# R63 G2 — Founder Sandbox package handoff (2026-11-19)

**RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO**

## Tested baseline
[GitHub-hosted Windows CI run #44522716821](https://github.com/SepehrGhanbari/Ario/actions/runs/44522716821) completed/success on disposable Windows Server 2022. Its artifact contains the **exact tested controller and restricted-token PowerShell probe source**, plus the bounded actual report. [Prior complete acceptance report](R63_G2_WINDOWS_DACL_CI_ACCEPTANCE_2026-11-19.md) records tested writer and reader token SIDs, DACL readbacks and 5/5 denied direct writes.

The CI raw controller SHA-256 inside its action artifact is `f71dbc30a3ea65d88519225eab3fdca0d2fd4e646c2aac72badbd4ab3c4b3b32` and the raw restricted-token probe SHA-256 is `52f3b5c88ba75a9a92d8ac227e1364b22a265513d8dda2d1779ac6d29cf35bb3`.

## Bounded private guest package

Created user-facing archive in this ChatGPT conversation only, NOT uploaded to this public repository:
- `Ario-R63-G2-Restricted-Writer-Windows-Sandbox.zip`
- **SHA-256 `64a17a2f1c4efb6ff965e9728c8b94f70f65317fb4d7706f2fa0afb436150627`**
- 9,065 bytes, 7 ZIP members, 6/6 internal SHA256SUMS checks, CRC clean; WSB XML parsed statically.
- Guest controller is adapted directly from the CI-proven code. It changes only environment gates, export/run-ID paths, Windows PowerShell 5.1 random byte generation, and makes cleanup failure cause HOLD. The direct-token child probe is byte-for-byte the same content as the tested script after normalizing line endings.
- `.wsb` has networking/clipboard/vGPU **disabled**, readonly source folder, writable evidence-only output folder, **no LogonCommand or auto-run**. It contains a machine-specific host path, which is the reason the WSB is not published in the repository. The host folder mapping is a file mount, not an OS account/ACL change.
- New guest controller refuses all non-`WDAGUtilityAccount` contexts and wrong source mounts, requires an **already-elevated** guest token for local test-user creation, and operates solely in a uniquely named temporary directory under the disposable guest `C:\Users\Public`.
- Two new synthetic local account passwords are randomly generated in memory for the disposable guest. No passwords, live Ario secrets or signing keys are written to user evidence, the host or GitHub.
- The test writes permission-only fixture files named `v1.jsonl`, `v2.jsonl`, and `uncertain.flag` in the **new test directory**. It never reads/writes the actual founder V9/V12 journal directories. On successful completion it deletes both test accounts and test data, checks for their absence, and writes a JSON report plus console log with a **matching run tag**.

### Verification / claim boundary
**Static guest ZIP integrity and source review: PASS.**  
**Founder Windows Sandbox run: NOT EXECUTED.** There is **no** user-supplied native guest result yet for this exact ZIP. The earlier Windows CI success must not be transferred to this guest version without execution.

Real old V9 witness, signer, service, policy, actual native journal transactions, PowerShell execution policy changes, host ACL modifications and production keys remain out of scope. G2 **does not establish** independence against guest administrators or guarantee atomic V1/V2 writes. The next gate after founder report must protect the *actual synthetic witness-writer process* and preserve true evidence of authorized writer vs unauthenticated writer in a fresh guest.

`G2_CI_SID_AND_DACL=PASS` / `G2_SANDBOX_SOURCE_STATIC_CHECK=PASS` / `G2_SANDBOX_RUN=NOT_EXECUTED` / `INDEPENDENT_CUSTODY=NOT_ESTABLISHED` / `PRODUCTION=NO_GO`.
