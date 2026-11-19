# R63 G3 — Founder Windows Sandbox repaired PS5.1 run: independently recomputed evidence

**Audit date:** 2026-11-19  
**Run ID:** `4496-a2f29c2`  
**Standing:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO

## Private source material; not published
The founder supplied these three files privately in ChatGPT; the originals were opened read-only and **no Python, CMD or PowerShell in the ZIP was executed** during the audit:

| File | Exact byte SHA-256 | Size |
|---|---|---:|
| `R63-G3-Evidence-4496-a2f29c2(1).zip` | `20a7f0ac8aa600887a268af3af894561aa956d227e7ae46f3e13524ce814634a` | 14,949 bytes |
| `R63-G3-Report-4496-a2f29c2(1).json` | `4348337dd4267a83cb96fcd6c787f711e8d37747e833d28964fbc8bf4eb25107` | 35,826 bytes |
| `R63-G3-Launch-5951-17755(1).txt` | `c6253ff7c6f61227bb2d126e5df7246e07119e43aa6e29607a2a383e53a89367` | 646 bytes |

Source distribution previously prepared for this trial:
`Ario-R63-G3-PS51-ExitCode-Fix-Sandbox.zip`, SHA256 `aac27c465f7a8596e651479cd4b625f49459d3ccd4c34bd23c58716e400d740a`, 25,669 bytes. Source hashes from guest report match **the actual modules** inside that ZIP:
- frozen V9 `spend_chain_v2.py`: `c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd`;
- `witness_g3.py`: `38fa8b7bd1e6492e9f448b4ed30d1d31e590a7569495252e0898affa7d6a4a56`;
- fixed `Invoke-G3-WitnessLab.ps1`: `767ad5dd753dc1e0b4f2b0e45024f744788045beff335af09d56331e8d493faa`.

The guest `runtime_python` hash is reported as `31fe10b4ed82a2f960af0ef9931f46a4b84ff286f8b6ffd9dee098cf4f10f17f` but was **not re-read from the founder's guest runtime** by this audit.

## Independently recomputed from evidence ZIP bytes

- ZIP CRC/testzip clean, **36 distinct safe member names**, 35 content files plus `SHA256SUMS.txt`; SHA manifest covers every content file exactly once and **35/35 SHA256 match**.
- The full embedded `report.json` and separately supplied external JSON agree on all **14 shared top-level fields**. The external report additionally has `cleanup_verified=true`, `final_verdict=PASS_SYNTHETIC_G3` and `custody=SAME_GUEST_ADMIN_NOT_INDEPENDENT`. The ZIP was evidently assembled before those last three report fields were added, so **the two report objects are not byte-identical or object-identical**; this is a provenance/timing limitation, not suppressed or silently merged.
- **Seven archived V1/V2 snapshots** were independently parsed and SHA256-rehashed, with **21 V2 event records revalidated** from first principles: exact canonical JSON, version, sequential event index, predecessor, SHA256 of domain `ARIO-R63/spend/v2\0` plus canonical body, unique nonce/ID and sorted-content `before`/`after` R60 commitments.
- Each of the **seven raw snapshots** matches its stored `inspect.json` for V1/V2 hash, row count, event count, append-order coherence, V2 head, flag presence and flag hash/size. **Six raw `uncertain.flag` snapshots** were independently checked.
- All three pairs of `after-crash` and `after-recovery` have **byte-identical** raw V1, V2, flag and `inspect.json`; recovery does not appear to rewrite those archived files.
- Six archived `writer-identity.json` records agree with report writer SID/PIDs; the reported writer SID ends `-1000`, reader SID ends `-1001` (both same guest machine authority).

| Scenario | Raw V1 rows | Raw V2 events | Coherent | Raw flag | Guest reported behavior |
|---|---:|---:|---|---|---|
| Normal 2/8/16 | 5 | 5 | yes | absent | exactly 1 new synthetic reservation per batch; 26 requests |
| Pre-V2 crash | 2 | 2 | yes | present | parent exit 73, new PID, HOLD_UNCERTAIN |
| Post-V2 crash | 2 | 3 | **no** | present | parent exit 73, new PID, HOLD_UNCERTAIN |
| Post-V1 crash | 3 | 3 | yes | present | parent exit 73, new PID, HOLD_UNCERTAIN |

For normal requests, each group contained **one** `RESERVED_ONLY_NO_SIGN` and remaining `ALREADY_RESERVED_NO_APPEND`: 26 replies total, three new reservations. The guest report indicates **8** direct-write denials across `direct` and `direct_live` normal probes, and **15** direct-write/flag-deletion denials across three crash probes, or **23 guest-reported denied operations** total. The exported DACL snapshots show writer Modify, reader Read/Execute, Administrators and SYSTEM Full control.

Launch log reports `G3_NORMAL_WRITER_RPC_V1_V2_CANONICAL=PASS`, `G3_2_8_16_SEPARATE_READER_CLIENTS=PASS`, `G3_DIRECT_NONCOOPERATIVE_WRITES_DENIED=4/4` for the normal probe, all three injected exit-73/retry-HOLD phases, `EVIDENCE_ZIP_MEMBERS=36`, `G3_TEMPORARY_CLEANUP=PASS`, `G3_VERDICT=PASS_SYNTHETIC_G3`, `G3_LAUNCH_EXIT=0`. Note that the evidence contains independently checkable *final state bytes* but **not external OS tracing of each process, denial or cleanup**.

## Critical limitations

1. **No genuine independent administrative custodian.** Writer and reader have different non-admin SIDs but Administrators and SYSTEM retain Full Control. Same-admin coherent rollback, flag deletion, ACL changes and historical replacement are not blocked.
2. **RPC caller OS-token authorization NOT_ESTABLISHED.** Reading an authenticated child token in the test does not establish that each TCP request is bound to an authenticated Windows peer token.
3. **No V9 signer or CNG in this package.** `RESERVED_ONLY_NO_SIGN` is a synthetic journal result, not a signature or real broker approval. Exact-once provider use, receipt replay, signer crypto-crash and use-completeness remain untested.
4. **No atomic cross-file durability / true power-loss proof.** V1 and V2 are separate fsynced files with a recovery HOLD; loss of the local flag and same-admin rollback remain dangerous. Guest-controller-provided process exit code and OS AccessDenied are self-reported.
5. The embedded report omits the three final top-level fields described above; preserve both original artifacts rather than rewriting one to match the other.

## Evidence verdict and next gate

`G3_FOUNDER_SANDBOX_OPERATOR_REPORTED=PASS_SYNTHETIC_G3`  
`G3_ARCHIVED_V1_V2_BYTE_RECOMPUTATION=PASS`  
`G3_ARCHIVED_FLAG_AND_MANIFEST_RECOMPUTATION=PASS`  
`G3_PS51_EXITCODE_FIX=GREEN_IN_CI_AND_FOUNDER_GUEST`  
`NATIVE_V9_WITNESS/SIGNER=NOT_EXECUTED`  
`RPC_PEER_TOKEN_AUTH=NOT_ESTABLISHED`  
`EXTERNAL_CUSTODY_AND_NONROLLBACK=NOT_ESTABLISHED`  
`PRODUCTION=NO_GO`.

**Next:** test a bounded authenticated IPC or named pipe with explicit peer token/SID binding instead of assuming TCP peer identity; test administrative file rollback/flag-loss against an externally retained checkpoint; only then consider combining an actual guest-only V9-derived signer/broker with synthetic keys and exhaustive CNG call evidence.

Historical failed G3 `4824-b28df79` run and WinPS5.1 RED CI remain separate, unmodified evidence. No user ZIP/private guest paths were published; no `main`, Ruleset, host policy, real key or trust status changed.
