# R63 G3 — Native Windows restricted-writer witness acceptance (2026-11-19)

**Status:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO

## Scope and exact source

The G3 test connects a **separate loopback TCP witness process under a disposable nonadministrator writer SID** to actual *synthetic valid V9-sidecar* V1/V2 journals, while reader-SID clients can make requests but cannot directly modify the journals, `uncertain.flag` or their parent directory. The run also exercises Win32 cooperating lockfile exclusion, three deliberately injected death windows, and fail-closed restart.

- Research-only source folder: [research/r63_g3_witness_ci](https://github.com/SepehrGhanbari/Ario/tree/research/r63-g3-restricted-witness-20261119/research/r63_g3_witness_ci).
- Git blob: `witness_g3.py = 6c8c51d03d42128f2a7ba00a506f7ab890e9a845`, `Invoke-G3-WitnessLab.ps1 = db5f775d165be6aa948bfbc25fe200a0d8940715`. These exact blob SHA values were independently matched to the final user-facing guest ZIP.
- Frozen original V9 `spend_chain_v2.py` SHA-256: `c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd`; pinned and checked before test. The source is a *copy of frozen actual source*, not an altered v2 implementation.
- The old frozen V9 driver / service / CNG signer is **not** executed. No real Ario key, host ACL, Ruleset, TPM or production/trust action.

## Observed CI results (NOT founder guest execution)

**[GitHub Actions #44571016096](https://github.com/SepehrGhanbari/Ario/actions/runs/44571016096) — Windows native job SUCCESS, Windows model-audit job SUCCESS and Ubuntu model-audit job SUCCESS.** Exact native job `135725742835` stdout was retrieved and inspected.

- A separate Windows writer process under actual SID ending `-1003` and reader client/batch processes under separate SID ending `-1004`; synthetic parent directory and files explicitly grant writer Modify, reader Read/Execute, admins/SYSTEM Full Control.
- For separate-client concurrency groups of **2, 8 and 16** (26 request processes), exactly one `RESERVED_ONLY_NO_SIGN` per group, all others `ALREADY_RESERVED_NO_APPEND`. Final noncrash V1/V2 journals are canonical and coherent, with **5** total records (2 initial + 3 newly reserved).
- **23/23 direct filesystem write/delete attempts reported ACCESS_DENIED** under reader SID: four while witness is online, four after concurrent work, and five after each of three crashes. They do **not** use the cooperative lockfile. The test rejects generic sharing/I/O exceptions as ambiguous instead of treating them as ACL denials.
- `pre_v2`: parent exits with `73`, V1=2/V2=2, uncertainty flag present, restart returns `HOLD_UNCERTAIN` with no raw file changes.
- `post_v2`: parent exits with `73`, V1=2/V2=3 (split), flag present, restart HOLD with no raw changes.
- `post_v1`: parent exits with `73`, V1=3/V2=3 (coherent but still uncertain), flag present, restart HOLD with no raw changes.
- Parent and restarted witness PIDs differ. Synthetic user and directory cleanup reports PASS; there is no independent external cleanup witness.
- **No new signature exists by construction**; V9 use-completeness is not proven.

### Evidence was independently audited, not inferred solely from PASS strings

Github Actions artifact [#14553877615](https://github.com/SepehrGhanbari/Ario/actions/runs/44571016096/artifacts/14553877615) was downloaded and inspected as a ZIP: outer artifact **11,425 bytes**, SHA-256 `288ca0bb72bcda398f9037ce7a24b24ecbe53d6c81555b3195d94f1214d14bf5`. It contains a unique run-matched native JSON report, run log and guest evidence ZIP.

Inner `R63-G3-Evidence-7372-f7b44ac.zip`, SHA-256 `58a220818e6637e9c05e352e1d69f3fdbc02f14c6ae25c22df78fca58db415b2`: **35 evidence members + 1 SHA manifest**, CRC/manifest clean. A new independent Python forensic reader (not importing source from the ZIP) recomputed canonical V1 append-order bytes, all frozen V9 V2 chain/hash/seq/prev/before-after commitments, three raw uncertainty flags before/after restart, reporter/observer final hashes, process IDs, and the exact expected 2/8/16 response counts. Verdict: `PASS_INTERNAL_BYTES_ONLY`. **The internal manifest and reported OS events are still same-admin evidence, not cryptographically authenticated external attestations.**

## Preserved RED→GREEN lineage

- [#44570458600 — RED](https://github.com/SepehrGhanbari/Ario/actions/runs/44570458600): PowerShell strict-mode object property `Count` misread in the test harness; not a DACL bypass. Fixed with explicit enumeration of denial property names.
- [#44570731301 — RED](https://github.com/SepehrGhanbari/Ario/actions/runs/44570731301): client readiness check opened `port.txt` while writer still had the file open; Win32 sharing failure, not a permission bypass. Fixed by flush/fsync to a temporary port file and atomic replace of the published readiness file.
- [#44571016096 — GREEN](https://github.com/SepehrGhanbari/Ario/actions/runs/44571016096): all 3 workflow jobs success; prior failures are preserved.

## Founder handoff / hash

The source-reviewed founder **no-autorun** Windows Sandbox package is supplied **in this private chat, not in public GitHub** due a machine-specific WSB mapped-folder path:

`Ario-R63-G3-Restricted-Witness-Sandbox.zip`; **25,120 bytes**, SHA-256 `993484f39ab3f607f1de55f9d226c1d0dba8251008117b6bd076d2645fc74459`, **11 ZIP entries** comprising 10 manifest-verified files and SHA256SUMS; CRC clean. Networking/Clipboard/vGPU disabled, readonly source and embedded synthetic V9 Python runtime mapped into disposable guest, only evidence output mapped writable; no autorun. CMD refuses non-`WDAGUtilityAccount` and invokes PowerShell per-process execution policy in disposable guest only.

**Founder execution of this exact package: NOT_EXECUTED yet.** CI's Windows Server 2022 account/policy environment is not a substitute for the founder's Windows Sandbox environment.

## What G3 still cannot establish

1. **No independent administrative custody:** same machine Administrators/SYSTEM still have Full Control and can reset local file ACLs, replace journals or coherently roll back both V1/V2 plus the flag.
2. **No authenticated RPC caller SID / authorization:** loopback TCP accepts syntactically valid requests from any caller able to connect; filesystem DACL denial is not equivalent to permission to request a reservation via RPC.
3. **No atomic V1/V2 transaction or power-loss guarantee:** two files are fsynced separately and a cooperative lockfile controls only cooperating writers. The persistent local `uncertain.flag` is not externally anchored.
4. **No original native V9 signer integration:** no real V9 witness, CNG, target-key use-completeness, signer crash or approved receipt recovery.
5. **No independently witnessed OS event log:** log PIDs/SIDs come from the disposable-runner process and are cross-checked with its own archived records; they are not external attestations.

**Next gated work:** after founder guest evidence is received and audited, consider a *restricted writer service/IPC authorization boundary* with actual client identity and a separately administered external checkpoint. Maintain `GENESIS=NO_GO`, `TRUST_ACTIVATION=NO_GO`, `PRODUCTION=NO_GO`.

**Decision:** `G3_WINDOWS_SYNTHETIC_NATIVE_CI=PASS`; `G3_FOUNDER_SANDBOX=NOT_EXECUTED`; `G3_REAL_V9=NOT_EXECUTED`; `INDEPENDENT_CUSTODY=NOT_ESTABLISHED`; `A_GOV=NOT_ESTABLISHED`; `USE_COMPLETENESS=NOT_ESTABLISHED`.
