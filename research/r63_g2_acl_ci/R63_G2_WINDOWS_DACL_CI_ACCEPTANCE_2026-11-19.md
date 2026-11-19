# R63 G2 — Native Windows SID/DACL direct journal-write denial (2026-11-19)

**RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO / GENESIS=NO_GO**

## Origin and exact scope

The previous [founder V12 raw-byte audit](../r63_v12_evidence_ci/R63_V12_FOUNDER_GUEST_BYTE_AUDIT_2026-11-19.md) established:
- V1/V2 hash chains, local observer snapshots and raw `uncertain.flag` can be captured coherently in a disposable guest.
- Deleting the uncertainty flag or coherently rolling back journals under the **same administrator** can reopen synthetic admission (expected fail-open).
- A cooperative Win32 lockfile can be bypassed by an uncooperative journal writer.

**G2 targets a different boundary:** whether two *different non-administrator Windows token SIDs* see different native filesystem access to the **actual disposable journal-named files** and their parent directory, even if the restricted process does **not** take the cooperative lock.

## Tested implementation

Research branch `research/r63-g2-acl-20261119`, no main or Ruleset change:
- `Invoke-G2AclCI.ps1`: requires GitHub-hosted Windows CI, elevated disposable runner and exact repo. Creates two fresh, password-randomized, **short-lived synthetic local Windows accounts** (`R63G2W...`, `R63G2R...`). Passwords are never written to log, report, GitHub artifact or source. Test directory is uniquely created under `C:\Users\Public\ArioR63G2CI_...`; never points to real Ario journals or system configuration.
- Inheritance is removed **only** on that synthetic root directory. Explicit SID-based DACL: `NT AUTHORITY\SYSTEM = F`, `BUILTIN\Administrators = F`, writer nonadmin SID = `M`, restricted reader nonadmin SID = `RX`. A `journal\` subdirectory contains `v1.jsonl`, `v2.jsonl`, `uncertain.flag` labeled **ACL-only fixtures, not valid V9 journal chains**.
- `Invoke-RestrictedTokenProbe.ps1`: child process launched with `Start-Process -Credential`, reads actual token SID through `WindowsIdentity.GetCurrent().User.Value`, checks nonadmin role and attempts `[IO.File]` operations directly, without honoring any lockfile. `UnauthorizedAccessException` is accepted even when wrapped in PowerShell 5.1 `MethodInvocationException`; unrelated exceptions do **not** count as access denial.
- Tests verify an authorized nonadmin writer truly **appends V1 and V2** and creates a sibling file; a restricted nonadmin reader can read files but cannot append either journal, overwrite V1, delete `uncertain.flag`, or create a sibling file. Parent independently reads file SHA256 before and after the restricted attempts and checks existence/nonexistence. The script attempts to delete its only synthetic users and temporary directory in `finally`, but cleanup is **not separately verified by a post-run account listing**.

## Recorded CI evidence

[Successful GitHub Actions run #44521958306](https://github.com/SepehrGhanbari/Ario/actions/runs/44521958306), Windows Server 2022, GitHub-hosted ephemeral runner, job `135552564185`: **completed/success**. Original artifact [#14527908764](https://github.com/SepehrGhanbari/Ario/actions/runs/44521958306/artifacts/14527908764) was downloaded and inspected independently as a 1,359-byte ZIP with two files. The JSON report SHA-256 was `fc57f59fd7885658760918841f2810a508400c23706c2976f752c39158f58b54`.

**Actual JSON content observed (not assumed):**
- Writer SID `S-1-5-21-1280602335-643053282-3184619455-1003`; reader SID `...-1004`; each `is_admin=false`; distinct.
- `icacls` output confirms writer `(M)`, reader `(RX)`, SYSTEM and Administrators `(F)` inherited for the synthetic `journal/`, `v1.jsonl`, `v2.jsonl`, `uncertain.flag`.
- Authorized child `append_v1=ALLOWED`, `append_v2=ALLOWED`, `create_sibling=ALLOWED`.
- Restricted child `append_v1=ACCESS_DENIED`, `append_v2=ACCESS_DENIED`, `overwrite_v1=ACCESS_DENIED`, `delete_flag=ACCESS_DENIED`, `create_sibling=ACCESS_DENIED`: **5/5 native DACL denials**.
- V1 SHA before/after `06e8c3aa588a51eb64e7d9d30ba547f00cb10a683c11cc1434de6d4b0a6f32a3`;
  V2 `574783189f78b56fd4f17af934b0158c40087ee99f66ac73b9ef96f7e0798332`;
  flag `58f278389640e2af44fa9838f3d67504363d09d9445e0c12b07e05e6f922a89f`.
  All three match byte-for-byte **after restricted attempts**.

**Preserved RED attempts (tooling, not journal bypass):**
- [#44521497562](https://github.com/SepehrGhanbari/Ario/actions/runs/44521497562): `icacls` cannot read four target paths in a single invocation (Win32 exit 87). Fixed by one path per call.
- [#44521612614](https://github.com/SepehrGhanbari/Ario/actions/runs/44521612614): child used Windows PowerShell 5.1 which does not define `$IsWindows`; changed to OSVersion Platform check.
- [#44521764412](https://github.com/SepehrGhanbari/Ario/actions/runs/44521764412): Windows returned a **real access-denied error**, but PowerShell wrapped `UnauthorizedAccessException` in `MethodInvocationException`; original exception classifier incorrectly marked result inconclusive. Fixed by walking the exception chain while rejecting unrelated I/O errors.

These unsuccessful runs remain available and were not erased.

## What this establishes and what it cannot

**CI_PASS — OS-level file DACL controls genuinely distinguish a permitted writer from a restricted reader under separate non-admin identities** on a *synthetic, throwaway Windows directory*. An uncooperative restricted reader was denied even without participating in a lockfile protocol.

**HOLD / NOT EXECUTED —** original V9 witness broker integration, actual V9 journal-format validity after writer activity, Windows Sandbox founder guest repeat, distinct service identity/SCM, nonexportable Ario key, native NCrypt use or completeness, consistent transaction boundary across two journal files, realistic share and rename races, file-owner attacks, hard reboot, separate custodians, independent nonrollback/rollback-protected checkpoint.

**Crucial caveat:** built-in Administrators and SYSTEM retain Full Control by design. These ACLs don't stop a local administrator from resetting DACLs, deleting/replacing files, or rolling back V1/V2 plus the local flag. A writer with Modify can also delete/rewrite its own local data; no per-operation signer authority or append-only guarantee is implied.

## Next founder manual gate

Prepare a new **no-autorun** Windows Sandbox-only package with the same temporary two-account DACL experiment; capture SID, child results, raw `icacls` output, before/after hashes, and explicit deletion result for *both* synthetic users. Never execute it on the physical host; no real V9 service, signer, or security policy modifications. Only after that consider a narrowly scoped identity-restricted witness parent on new synthetic V1/V2 files.

**Verdict:** `G2_EPHEMERAL_WINDOWS_NATIVE_DACL=CI_PASS` / `G2_FOUNDER_SANDBOX=NOT_EXECUTED` / `INDEPENDENT_CUSTODY=NOT_ESTABLISHED` / `NATIVE_V9_RECOVERY=NOT_EXECUTED` / `PRODUCTION=NO_GO`.
