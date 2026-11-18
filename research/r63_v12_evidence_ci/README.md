# R63 V12 — Guest witness evidence completeness and same-admin rollback

**RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO**

## Frozen source

The R63 V11 founder guest package and actual archived evidence were independently inspected. Exact original V9 `spend_chain_v2.py` SHA256: `c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd`.

- V11 operator evidence ZIP SHA256: `b4056fe822497ff459f573fc7cfd35809158d6d973673ae572d869bb474514cb`.
- The V11 archive provided **final raw V1/V2 bytes**, not raw `uncertain.flag` or paired after-crash/after-retry immutable observation snapshots; see [V11 independent audit](../r63_v11_win32_lock_ci/R63_V11_FOUNDER_GUEST_EVIDENCE_AUDIT_2026-11-18.md). It is wrong to call old evidence G1-complete.

## G1: new bounded Sandbox package (chat-only pending native guest execution)

New artifact created and locally source-checked in the assistant's isolated working environment:

`Ario-R63-V12-Witness-Evidence-Complete-Sandbox.zip`, SHA256 `881c428535327bf22ba3fcf1b50ee854385261ec3626711217fff8bbaa112bbd`, 22,389 bytes; 11 package entries with SHA256SUMS manifest verified.

The new `v12_guest.py` uses **unchanged V11** `witness_parent.py`, `witness_lab.py`, `win_exclusive.py` and the exact pinned V9 V2 sidecar; it adds:
1. Independent **local subprocess** readbacks of exact V1/V2 and `uncertain.flag` before and after each of the three parent-crash recoveries, with SHA256 and observable PID/SID (`whoami /user`) in `observer.json`. Observers are separate processes but NOT different admin custodians; parent SID is not independently attested.
2. A SHA256SUMS manifest covering all exported evidence entries; source module SHA256 in the report; no RPC token exported.
3. Two **explicit disposable clone** negative controls: deleting the original local flag may admit a new synthetic reservation; coherent same-admin V1/V2 rollback may re-admit a previously reserved nonce. Both are expected **fail-open examples**, NOT desired safe outcomes.
4. A stricter offline byte auditor `audit_evidence.py` with mandatory raw flag snapshots, chain checks, manifest and observer cross-checks. **Local auditor unit tests: 6/6 PASS**, testing a valid synthetic archive and rejecting missing/modified flag, V1 drift, stale manifest and missing manifest. The actual prior V11 ZIP is deliberately rejected as incomplete for V12 (`MISSING_SHA_MANIFEST`).

The package's Python files passed `py_compile`; ZIP integrity and included 10/10 SHA manifest entries were verified. **The complete V12 guest package is NOT YET EXECUTED in the founder's Windows Sandbox**. Windows-specific source execution must be classified `NOT_EXECUTED` until founder-provided guest logs + raw V12 evidence archive are audited. The ZIP itself has not been uploaded to GitHub, to avoid publishing user-machine mapped paths and guest evidence by default.

Its `.wsb` launch has **no auto-run**, networking/clipboard/vGPU disabled; synthetic input and runtime read-only; evidence export only into the pre-existing host Documents export directory. Manual guest runner requires `WDAGUtilityAccount`. The original frozen V9 driver/service/key are never run.

## G3: live GitHub Actions evidence — proven *negative* controls, not antirollback

[Windows and Ubuntu Actions run #44364220719](https://github.com/SepehrGhanbari/Ario/actions/runs/44364220719): **both runner jobs SUCCESS**, 7/7 unittest each, direct logs inspected. Source: `test_known_local_rollback.py`, Python 3.13, SHA256-pinned original V9 V2 sidecar.

The tests show:
- with `uncertain.flag` intact → `HOLD_UNCERTAIN`;
- delete local flag under the same admin → a **new synthetic reservation is admitted** (counterexample);
- coherently roll back V1 and V2 → previously admitted nonce can be **reserved again** (counterexample);
- V1/V2 mismatch, truncated V2 and missing V1 still produce HOLD;
- a positive new reservation is accepted, preventing an always-HOLD false pass.

These effects happen on **temporary test files** only. There is no signer, receipt, CNG, physical external anchor, independent custody, production key, or actual native V9 integration.

## G2 remains blocked: administrative access

Previous [Win32 lock CI #44354525767](https://github.com/SepehrGhanbari/Ario/actions/runs/44354525767) demonstrates real inter-process mutual exclusion for **cooperating** writers but also demonstrates a *noncooperating writer can bypass the lockfile* and alter V1. A genuine G2 test requires separately restricted guest-only OS identities and DACL denial on the **actual journal files and parent directory** with direct token/SID readback. Before running such a guest-only ACL test, the account/deletion/provenance and exact scoped permissions must be reviewed. Do not modify the physical Windows host, laptop, real Rulesets, R51 TPM or Ario keys.

## State

`V12_SOURCE_STATIC_CHECK=PASS`; `G1_OFFLINE_AUDITOR_UNIT_TESTS=6/6 PASS`; `G1_GUEST_EXECUTION=NOT_EXECUTED`; `G3_WINDOWS_LINUX_EXPECTED_NEGATIVE_CONTROLS=7/7 EACH`; `G2_REAL_RESTRICTED_WRITER=NOT_EXECUTED`; `SAME_ADMIN_ANTIROLLBACK=KNOWN_FAILURE`; `NATIVE_V9_SIGNER_RECOVERY=NOT_EXECUTED`; `INDEPENDENT_CUSTODY=NOT_ESTABLISHED`.
