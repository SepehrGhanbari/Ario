# R63 G4 — Microsoft-signed portable PowerShell 7 Windows Sandbox handoff

**2026-11-21 · RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO**

## Why this package exists

The earlier G4 peer-token Named Pipe laboratory passed on Windows [Actions #44939990366](https://github.com/SepehrGhanbari/Ario/actions/runs/44939990366) and the **exact rewritten guest controller** passed in native PowerShell 7 [Actions #44944001478](https://github.com/SepehrGhanbari/Ario/actions/runs/44944001478), including the offline ZIP auditor. But Windows PowerShell **5.1** has a distinct unclosed compatibility issue under the guest controller; [WinPS5.1 #44943005696](https://github.com/SepehrGhanbari/Ario/actions/runs/44943005696) was cancelled after 20 minutes. Later diagnostic traces prove the four Named Pipe client interactions and server exit happened, but the full acceptance gate did not complete; **do not infer a WinPS5.1 PASS** or ask founder to rerun that unverified path. The account-name parsing defect and native source-hash module dependency were separately found and recorded; neither is evidence of a journal security bypass.

Instead of modifying the host PowerShell installation or local execution policies, create **one portable, guest-only PowerShell 7 distribution** from a verified Microsoft-signed executable in an ephemeral GitHub-hosted Windows runner and pair it with the **exact controller bytes already tested green under PowerShell 7**.

## Entire guest bundle (chat-only, not checked into GitHub)

`Ario-R63-G4-Portable-PowerShell7-Sandbox.zip`

- **119,492,978 bytes; SHA256 `6fdb090545caf22d5a60bd41e0598f7cb4dec69ae499f46b892f1dd74db79cb9`**.
- Exactly **1,117** unique ZIP entries, including `SHA256SUMS.txt` for **1,116/1,116** other entries. Every raw entry was independently SHA-256 recomputed and ZIP CRC verified. The ZIP contains **no font files**.
- Base G4 source package controller **Git blob SHA-1 `bdcbc8c9d64365435ccabfe8e00bf9791f06bafe`**, verified byte-for-byte against the exact GitHub commit in [successful pwsh7 #44944001478](https://github.com/SepehrGhanbari/Ario/actions/runs/44944001478). Original test-only `G4PipeGate.cs`, `Invoke-G4PipeActor.ps1`, frozen V9 V2 sidecar and Python evidence auditor unchanged.
- Portable runtime from Microsoft-signed executable on Windows [Actions #44945473212](https://github.com/SepehrGhanbari/Ario/actions/runs/44945473212), artifact `#14723077684`. **PowerShell version 7.6.10**, `pwsh.exe` SHA256 `e94166ed9f376559c1359bafb08bc49e463a494c330f67644ec1d9f1ffeb5ee5`; Authenticode `Valid`, signer `Microsoft Corporation`, checked by runner. All 1,107 runtime files included, no installed host component is required.
- WSB `R63-G4-Peer-NoAutoRun.wsb` has **no LogonCommand**, Networking/Clipboard/vGPU disabled, source+runtime readonly, export-only writable host folder. `R63-G4-GuestOnly.cmd` checks `USERNAME=WDAGUtilityAccount` and exact read-only mounts, launches **`C:\R63-G4-Input\pwsh7\pwsh.exe`** with **per-process guest-only** `-ExecutionPolicy Bypass`. It never edits machine policy, host registry, Windows host accounts or host ACL.
- **Founder guest run has not been executed**, and packing static checks cannot establish runtime equivalence in the founder's Windows 10 Sandbox; user-supplied matching run/report/evidence files are necessary. No real V9 signing/keys/CNG or service invoked.

## One-folder founder execution, only when ready

Unpack all members directly into this **new** physical Windows folder:

`C:\Users\xx4773\Documents\Ario-R63-G4-PWSh7-GuestLab-20261121`

Close previous Sandbox after preserving earlier exports; double-click `R63-G4-Peer-NoAutoRun.wsb` in the new folder. Inside the **fresh** Windows Sandbox, go to `C:\R63-G4-Input` and manually run `R63-G4-GuestOnly.cmd`.

All matching run-id output remains in physical host folder:

`C:\Users\xx4773\Documents\Ario-R63-V10-Manual-Exports`

Send `R63-G4-Evidence-*.zip`, `R63-G4-Report-*.json`, `R63-G4-Run-*.txt`; and launcher log if present. On HOLD or failure, no rerun or security policy change: retain and send log.

## Trust boundary

The test uses **actual Windows token/SID-based client authentication of a Named Pipe** under three synthetic local guest accounts. The dummy V1/V2 format is pinned to frozen V9 sidecar. A successful sandbox run would support the **bounded G4 identity gate** only; it cannot establish an independently administered latest `(seq,head)` holder.

Public [synthetic Sigstore Rekor history receipt #44943687610](https://github.com/SepehrGhanbari/Ario/actions/runs/44943687610) is externally administered **historical** evidence, not latest authority. G5 signed-floor simulator [#44943376732](https://github.com/SepehrGhanbari/Ario/actions/runs/44943376732) passed 14/14 per OS but under same test administrator. For a genuine independently administered latest floor, publisher cannot have reset/delete/rotate permissions on the custodian or verifier pin; an accountable separate operator/domain is still required. A separate founder-controlled device is a proposed weaker physical segregation, **not yet executed**; see [G5 separate device design](../r63_g5_floor_custody_ci/R63_G5_FOUNDER_SEPARATE_DEVICE_MIN_FLOOR_DESIGN_2026-11-21.md).

`G4_EXACT_SOURCE_PWSH7_CI=PASS` / `G4_PORTABLE_GUEST_PACKAGE_STATIC=PASS` / `G4_FOUNDER_SANDBOX=NOT_EXECUTED` / `G5_PUBLIC_SYNTHETIC_HISTORY=VERIFIED` / `G5_AUTHORITATIVE_INDEPENDENT_LATEST=NOT_ESTABLISHED` / `NATIVE_V9_SIGNER=NOT_EXECUTED` / `PRODUCTION=NO_GO`.
