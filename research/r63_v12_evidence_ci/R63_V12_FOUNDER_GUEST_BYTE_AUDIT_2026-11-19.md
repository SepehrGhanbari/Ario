# R63 V12 — Founder Windows Sandbox evidence: independent raw-byte audit

**Audit date:** 2026-11-19  
**Status:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO

## Material reviewed (private in-chat, not uploaded to GitHub)

- Founder-supplied `R63-V12-Evidence-7027-27761.zip` — **22,046 bytes**, SHA-256 `4f1e6a20bff9c6b45f1a1c2460ec5b1cf955afc4ee3d62c14bb61c4851c09f52`.
- Companion `R63-V12-Run-7027-27761.txt` — **417 bytes**, SHA-256 `abace6089f68ea8fca1e7d05cd68587827ae2a5e67151cf4cf14062b30194c78`. Text report's recorded ZIP hash exactly matches uploaded ZIP.
- Source package `Ario-R63-V12-Witness-Evidence-Complete-Sandbox.zip` — SHA-256 `881c428535327bf22ba3fcf1b50ee854385261ec3626711217fff8bbaa112bbd`; all **4** guest module SHA-256s reported in V12 `report.json` independently match the corresponding package source bytes.
- The frozen V9 V2 sidecar file in the source package has SHA-256 `c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd`.

The ZIP was opened read-only; **none of the guest's Python, CMD, signer or source code was executed** during the forensic review. Independent stdlib recomputation deliberately did not import the guest's provided V2/audit modules. No native host Windows action was taken.

## Independent forensic recomputation

| Evidence check | Result |
|---|---|
| ZIP CRC, member uniqueness and safe relative member paths | **PASS**, 48 members |
| Internal SHA256SUMS names/completeness and exact bytes | **PASS**, 47/47 content entries |
| Frozen V9 V2 event chains: canonical JSON, seq/prev, event hash domain, before/after R60 sorted content commitments, duplicate restrictions | **PASS**, 13 archived journal snapshots |
| Observer JSON fields vs independently recomputed V1/V2 SHA256, sequence, final head, coherence and flag hash/length | **PASS**, 13/13 |
| Raw `uncertain.flag` files verified | **PASS**, 7 (six crash/retry + one before deliberate flag deletion) |
| All report old/new observer records byte-for-byte logically identical to corresponding archived observer JSON objects | **PASS**, three pairs |
| Report-source fingerprints vs the actual four modules in supplied source ZIP | **PASS**, 4/4 |
| Same-admin negative-control raw-state transitions | **PASS, expected failure-of-security demonstrated** |

### Crash and recovery snapshots

| Phase | Archived V1 rows | Archived V2 events | Local coherence | Raw flag | Reported response |
|---|---:|---:|---|---|---|
| `crash_pre_v2` | 2 | 2 | coherent | 36 bytes, intact before and after retry | `HOLD_UNCERTAIN` |
| `crash_post_v2` | 2 | 3 | split | 37 bytes, intact before and after retry | `HOLD_UNCERTAIN` |
| `crash_post_v1` | 3 | 3 | coherent | 37 bytes, intact before and after retry | `HOLD_UNCERTAIN` |

For each phase, independently recomputed final V1 SHA, V2 SHA, V2 head and **raw flag bytes** are unchanged between `after_crash` and `after_retry`. The guest report gives old/new distinct observer PIDs and a consistent observer SID. **The six observers share the same Windows user SID, not an independent administrator**. All claimed parent death code 73, PIDs, Win32 lock status and RPC responses are *local guest reported facts*, not independent external OS attestations; the archived raw files alone cannot prove them.

### Two particularly important *negative* controls, recomputed from raw archives

**Flag deletion:** `before_flag_deletion` contains the expected raw `uncertain.flag`. In `after_flag_deletion`, the flag is absent, V1 and V2 are **identical bytes** to the prior state, and `after_new_reservation` has 3 events instead of 2. The guest report states `RESERVED_ONLY_NO_SIGN` was admitted after deletion. This is a same-admin fail-open; **no signature was made**.

**Coherent rollback:** `coherent_rollback/initial` and `rolled_back` are exactly the same V1/V2 bytes; `advanced` and `reissued` are also **exactly the same V1/V2 bytes, including the V2 chain head** `269c5e7f244a3143c3ffe7aea791b857130a8aa7ab85ad89333c444de5515c82`. The guest report states the same nonce was reserved again. This is especially important: **a self-consistent append-only *local format* does not distinguish two real-world runs that reconstruct identical files**. No outsider retained the previous head in a protected trust domain, and no real signing happened. The matching hashes are a *counterexample to local-only historical accountability*, not proof of rollback resistance.

Concurrent 2/8/16 client cases, one reservation per batch (26 total simulated client processes), are **guest-reported**. The ZIP includes local raw witness states for negative controls and crash cases, but does not contain independent OS process tracing to corroborate all client launches.

## Critical authority boundaries

1. The per-entry manifest is stored **inside the same ZIP** as the evidence and controlled by the same guest operator. It detects accidental byte mismatch; it is **not an authenticated remote witness** or an independent origin proof.
2. In all 13 observer records, the observer SID is the same. `report.json` says `parent_token_sid=NOT_MEASURED`. Distinct process IDs do **not** establish independently administered access control.
3. No real V9 witness RPC service, actual signer, NCryptSignHash, signer crash inside provider call, complete key-use telemetry, TPM, power cut, external anchor, WITNESS custody, production trust or Genesis activation was executed.
4. The result cannot support `A_GOV=ESTABLISHED` or `INDEPENDENT_CUSTODY=ESTABLISHED`.

## Outcome and next gate

**G1 evidence-complete V12: PASS as a byte-audited founder-operated, same-admin *synthetic guest lab*.** The historic G1 missing-raw-flag issue is closed for this *new V12 test only*; the original V11 evidence remains unchanged and incomplete.

**G3 local-only antirollback: KNOWN FAIL-OPEN** for same-admin flag removal and coherent file rollback.

**G2 Windows journal protection: HOLD / NOT_EXECUTED.** Priority is a **fresh, disposable Sandbox** experiment with independently verified guest token SIDs, restrictive DACL on **the V1/V2 files and parent directory**, and explicit direct-write attempts by an unprivileged guest process—plus a permitted writer positive control. This is not the same as implementing a cooperative lockfile. It does not by itself establish antirollback against the guest administrator.

**No user ZIP, runtime, security-relevant private material, or host path configuration was published to this GitHub repository. No main merge / Ruleset / host / real-key changes.**

Verdict: `G1_RAW_FLAG_AND_OBSERVER_EVIDENCE=PASS` / `G3_SAME_ADMIN_DELETE_AND_ROLLBACK=EXPECTED_FAIL_OPEN` / `G2_RESTRICTED_WRITER_ACL=NOT_EXECUTED` / `NATIVE_V9_RECOVERY=NOT_EXECUTED` / `INDEPENDENT_CUSTODY=NOT_ESTABLISHED` / `PRODUCTION=NO_GO`.
