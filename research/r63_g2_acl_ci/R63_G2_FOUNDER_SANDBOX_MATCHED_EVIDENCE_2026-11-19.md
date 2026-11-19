# R63 G2 — Matched founder Windows Sandbox run and evidence (2026-11-19)

**Status:** RESEARCH_ONLY / EVIDENCE_AUDIT / HOLD / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO

## Provenance: both founder-uploaded files independently read

- `R63-G2-Evidence-26933-24068.json`: **4,696 bytes**, SHA-256 `d8fda4a74ebbda273835d5328590c43c189edea641caedf7cedbef8fe536accd`.
- `R63-G2-Run-26933-24068.txt`: **342 bytes**, SHA-256 `b45130fd137b258790e9a917675fe00e517252ea0a098103b70e54defbee343b`.
- The **new** run log explicitly references `C:\R63-G2-Exports\R63-G2-Evidence-26933-24068.json`, and both filenames carry the same `26933-24068` run ID.
- A different, older `R63-G2-Run-25016-6209(1).txt` is a prior execution-policy error from a separate, unsuccessful trial. **It is not the log of this successful run** and must remain a separate historical record.
- The private original files remain attached in the user's conversation; their full contents have **not** been published on GitHub.

## Matched positive/negative permission results

Guest evidence JSON identifies itself as `R63_G2_NATIVE_WINDOWS_ACL_DIRECT_WRITER_DENIAL`, `FOUNDER_WINDOWS_SANDBOX_GUEST_EPHEMERAL_ONLY`.

- Non-admin authorized writer SID: `S-1-5-21-2047949552-857980807-821054962-1000`.
- Non-admin restricted reader SID: `S-1-5-21-2047949552-857980807-821054962-1001`.
- `distinct_token_sids=true`, `writer_is_admin=false`, `reader_is_admin=false`.
- Reported guest `icacls` snapshot for disposable `journal\` directory and `v1.jsonl`, `v2.jsonl`, `uncertain.flag`: writer `(M)`, reader `(RX)`, built-in Administrators `(F)` and SYSTEM `(F)`. These are synthetic ACL-only fixtures, not actual frozen V9 records.
- Actual reported permitted operations: `append_v1=ALLOWED`, `append_v2=ALLOWED`, `create_sibling=ALLOWED` (**3/3**).
- Restricted direct filesystem operations: `append_v1=ACCESS_DENIED`, `append_v2=ACCESS_DENIED`, `overwrite_v1=ACCESS_DENIED`, `delete_flag=ACCESS_DENIED`, `create_sibling=ACCESS_DENIED` (**5/5**).
- `sha_before == sha_after` for each of `v1.jsonl`, `v2.jsonl`, `uncertain.flag`, independently checked by parsing the received JSON. This verifies **internal consistency of the reported hashes**, not raw guest-file authenticity.
- Matched log confirms `G2_TEMPORARY_ACCOUNT_AND_DATA_CLEANUP=PASS`; no separate post-cleanup OS token or external state trace was provided, so treat this as a **guest-reported result**.
- Both sources explicitly state `G2_REAL_V9_SERVICE=NOT_EXECUTED` / `real_v9_witness=NOT_EXECUTED` and `G2_INDEPENDENT_ADMIN_CUSTODY=NOT_ESTABLISHED` / `same_admin_rollback_defense=NOT_ESTABLISHED`. No real signer or key was touched.

## Method and limits

The matched pair was read directly and compared against each other and the expected schema; it was not independently replayed inside the founder's Windows Sandbox. It corroborates earlier [GitHub-hosted Windows native SID-DACL CI PASS](https://github.com/SepehrGhanbari/Ario/actions/runs/44521958306), which used synthetic temporary accounts/files and preserved raw CI step logs.

**What is demonstrated:** a limited Windows filesystem permission boundary for a writer and a restricted reader under distinct nonadmin guest identities, independent of the cooperative lockfile protocol.

**What is still missing:** actual V9 witness/signer integration, atomic V1/V2 transactions, cross-process signer authorization and use completeness, external administration, resilience against a local Administrator or SYSTEM replacing files/DACL, same-admin coherent rollback, hard power cut and cryptographic independent checkpointing.

## Decision / next gate

`G2_FOUNDER_SANDBOX_REPORTED=PASS_WITH_MATCHED_LOG_AND_JSON`, `G2_CI=PASS`, `G2_REAL_V9=NOT_EXECUTED`, `INDEPENDENT_CUSTODY=NOT_ESTABLISHED`, `PRODUCTION=NO_GO`.

**Next experiment:** run a *new, disposable synthetic witness server* under the restricted writer identity, restrict the actual synthetic V1/V2 and parent directory, and prove cross-identity denied direct writes with correct append, crash and fail-closed replay semantics. Require independent guest output, token SID/DACL readback and fresh raw bytes; no main merge, no real keys or Ruleset edits.
