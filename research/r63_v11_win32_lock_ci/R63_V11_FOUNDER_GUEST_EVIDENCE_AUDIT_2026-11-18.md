# R63 V11 — Founder-supplied Windows Sandbox witness evidence: independent byte audit

**Date:** 2026-11-18  
**Original operator evidence:** `R63-V11-Witness-Evidence-20976-124.zip` (user-uploaded privately to chat; **not** published to GitHub)  
**Evidence ZIP SHA-256:** `b4056fe822497ff459f573fc7cfd35809158d6d973673ae572d869bb474514cb`  
**ZIP size:** 4,888 bytes; 11 entries; ZIP CRC/testzip clean; one `report.json` plus ten raw V1/V2 journal files.  
**Guest source package SHA-256:** `08139480300ac9d98b068d64aa10eb238b9718a17cc1b65b4a36f4090fdbadc9` (original source was independently reviewed, *not* re-executed on host).  
**Frozen source V2 byte SHA-256:** `c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd` (matches actual original source embedded in founder's source package).

## Independent read-only forensic check of the uploaded ZIP

The audit opened the original user-supplied ZIP without executing its Python sources or native guest executables. It recomputed SHA-256 for every archived V1/V2 raw file and independently recomputed **all** V2 event hashes using exact domain `ARIO-R63/spend/v2\0`, canonical JSON, predecessor chains, monotonic sequence, nonce/ID uniqueness, and R60 nonce-sorted `before`/`after` content commitments. It then compared final V2 head and legacy V1 append order/byte equality to the uploaded `report.json`.

**Result:** All 5 raw V1/V2 pairs parse correctly (concurrent, pre-V2, post-V2, post-V1, empty lock test); every archived raw V1/V2 SHA-256 matches report fields where available; all relevant V2 event counts, heads, and V1/V2 coherence decisions match report values. **No mismatch found among the supplied archived final-state bytes.**

| Scenario | Archive V1 lines | Archive V2 events | Independently recomputed coherence | Reported parent death/retry |
|---|---:|---:|---|---|
| concurrent 2+8+16 clients | 3 | 3 | equal | exactly 1 reservation per batch, 1+7+15 duplicate-only replies |
| `crash_pre_v2` | 2 | 2 | equal | PID 4244→4288, exit 73, HOLD_UNCERTAIN |
| `crash_post_v2` | 2 | 3 | **divergent** | PID 3884→4076, exit 73, HOLD_UNCERTAIN |
| `crash_post_v1` | 3 | 3 | equal | PID 4720→4412, exit 73, HOLD_UNCERTAIN |
| lock-test baseline | 0 | 0 | equal | holder PID 4996, lock blocked/reacquired (per report) |

All crash cases report unchanged SHA256, V2 head, event count and same-nonce replay state across crash→retry. **The ZIP only contains the final raw snapshot** per case. Thus the final raw hashes can be cross-verified; the separate pre-restart and post-restart observations, process PIDs/return codes and OS lock contention are **supported by founder-operated guest report but not independently corroborated by an external process trace**.

The guest laboratory source itself has a separate `witness_parent.py` TCP process, client subprocesses, Win32 `CreateFileW` lockfile exclusivity, a bounded V1/V2 gate, and a persistent `uncertain.flag` written/flush/fsync **before** injected exit. Three crash points inject `os._exit(73)`. A new process rejects operations if that flag remains present.

## Important proof gaps / refusal to upgrade claims

1. **Uncertainty flag absent from evidence archive.** Only `report.json` contains `uncertainty_marker=true`. The raw exported evidence omits `uncertain.flag`, sign-use intent/receipt (none expected in signerless lab), crash parent stdout/stderr, process identity/token SID, lock contention probe logs, and independent observer timestamped receipts. Do not present those as independently byte-verified.
2. **Cooperative lockfile only.** Win32 file share=0 blocks other processes which open the **same lockfile**. Previous CI showed a noncooperating same-user writer can directly edit a journal file despite the lock. No mandatory V1/V2 file write protection, cross-user SID proof or independent administrator custody is established.
3. **Latch durability and rollback.** An `uncertain.flag` written/flush/fsync in the same temp directory is not externally anchored; deletion or coherent same-admin rollback can remove the uncertainty history. The source does not validate an externally held last-confirmed checkpoint. Power failure, directory metadata persistence and future admission after a deleted flag remain untested.
4. **No signer exists in this guest lab.** `new_signatures=0` is true by construction and does **not** prove any V9/R60/NCrypt key-use completeness, no-resign guarantee on the actual broker, or original V9 production behavior.
5. **Separate process is not separate authority.** Guest report names `NATIVE_WINDOWS_SEPARATE_WITNESS_RPC_PARENT` and shows changed PIDs. Same guest user, same admin/storage authority and shared synthetic token remain. Real Ario independent witness security cannot be claimed.
6. **Not a cryptographic origin attestation.** ZIP SHA and chain consistency bind a supplied file's own contents; a same-admin controller could create internally coherent alternate historical files. The ZIP lacks an external independently controlled signature/checkpoint for the evidence report.

## Follow-on measurable gates

**G1 — evidence completeness:** retain exact bytes and SHA256 for `uncertain.flag` and companion launch/exit records before/after recovery, plus source SHA, SID/token readback, journal file IDs and handle/share flags. Preserve raw difference and independent observer process evidence; never overwrite previous trials.

**G2 — adversarial admission:** while a cooperative lock is held, demonstrate direct V1/V2 edit via non-cooperating process (expected unauthorized write under same-user ACL); then test a *separately restricted writer identity* in a disposable Sandbox so untrusted clients cannot bypass journal writes. Verify ACL/DACL and deny statuses from independent process tokens. Test a crash-held lock and no implicit repair.

**G3 — rollback counterexamples:** delete `uncertain.flag`, truncate V1, roll back V1+V2+receipt+local pin and compare against an independently retained **read-only external** checkpoint with different administrative control. If no genuinely independent holder is available, maintain `INDEPENDENT_CUSTODY=NOT_ESTABLISHED`, and treat case as HOLD rather than pretending an independent witness.

**G4 — eventual V9 native integration:** only after G1–G3 source review, design an actual isolated broker/witness service test with synthetic keys, one-use receipts, exact native NCryptSignHash enter/return evidence, and bounded recovery. Frozen V9 ZIP, `main`, production trust, real Ario keys and host settings remain unchanged.

## Decision

`SYNTHETIC_SEPARATE_WITNESS_GUEST=PASS_AS_OPERATOR_REPORTED`; `ARCHIVED_V1_V2_BYTE_AND_CHAIN_RECOMPUTE=PASS`; `WIN32_COOPERATIVE_LOCK=REPORTED_PASS_AND_CI_PASS`; `UNCERTAINTY_FLAG_BYTE_ATTESTATION=NOT_INCLUDED`; `ORIGINAL_V9_WITNESS_RPC_CRASH=NOT_EXECUTED`; `USE_COMPLETENESS=NOT_ESTABLISHED`; `INDEPENDENT_CUSTODY=NOT_ESTABLISHED`; `PRODUCTION=NO_GO`; `TRUST_ACTIVATION=NO_GO`; `GENESIS=NO_GO`.

**No main merge / no real key / no Ruleset changes.** The user's private ZIP was **not** uploaded to the repository.
