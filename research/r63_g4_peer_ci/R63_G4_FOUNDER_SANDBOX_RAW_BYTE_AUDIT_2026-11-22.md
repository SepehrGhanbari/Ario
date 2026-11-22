# R63 G4 — Founder Windows Sandbox Named Pipe identity: independent byte audit

**Date:** 2026-11-22  
**Evidence run:** `4796-e5cd1c02`  
**Status:** `RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO`

## 1. Input artifacts (reviewed privately, not uploaded to repository)

| Uploaded file | Bytes | SHA-256 |
|---|---:|---|
| `R63-G4-Evidence-4796-e5cd1c02.zip` | 2,844 | `43055b3e4c89074d39c369ee464833f7367c99b425f82a78b3cf96f41fe4c2f2` |
| `R63-G4-Report-4796-e5cd1c02.json` | 3,634 | `17d5e1971f8d1a16120913d81c18e10f4998ad23b7fa25aa7a9ce623d4ffb641` |
| `R63-G4-Run-4796-e5cd1c02.txt` | 368 | `df2149a2bb0d5daa7f55a8fe4cfa15c02679dd183e65afff477b053b96330df2` |
| `R63-G4-Launch-21732-16329.txt` | 640 | `7f2e145dcc7f510b5b3f4afe7d8e54e6081a9416341ac98b19fe4dc0331ab97c` |

Launch contains exact ZIP SHA256 and `G4_LAUNCH_EXIT=0`. Run + launch agree on `G4_VERDICT=PASS_SYNTHETIC_PEER_SID`; new evidence and report filenames share the run tag. Launch tag is separate by design.

**Distributed source package** `Ario-R63-G4-Portable-PowerShell7-Sandbox.zip` also re-opened read-only from the previous handoff: 119,492,978 bytes, SHA256 `6fdb090545caf22d5a60bd41e0598f7cb4dec69ae499f46b892f1dd74db79cb9`.

Five guest-reported `source_sha256` values independently matched exact bytes in the distributed package:
- guest controller `Invoke-G4PeerIdentityGuest.ps1`: `4d09fe409196e2d0534518d8cd6446e33fd875fb5c7e5261f7621640bb236f2d`;
- Named Pipe gate `G4PipeGate.cs`: `0c79ae50176b88f63b8e5a05ad681c06268decdb84c2408467d90e521a8884f9`;
- actor `Invoke-G4PipeActor.ps1`: `7873a9f2c6a11928e5944d8abb813233e32f43232008db993c8b2dfdc369fd17`;
- journal module `g4_journal.py`: `5678368a9ab2e8e8b6a70d91ff7ca91518169520c1c7d8d1941331eef3619989`;
- exact original frozen V9 V2 sidecar `spend_chain_v2.py`: `c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd`.
The bundled portable `pwsh.exe` matches the previously recorded Microsoft-signed build hash `e94166ed9f376559c1359bafb08bc49e463a494c330f67644ec1d9f1ffeb5ee5`. The **original user host runtime was not independently attested**; equivalence is source-package and self-reported guest evidence only.

## 2. Independent, raw-byte forensic result

A fresh standard-library-only Python audit parsed bytes of all uploaded artifacts **without executing any supplied Python, PowerShell, CMD or C# source**.

- **38/38 validation assertions PASS**, zero mismatches; ZIP CRC valid, five safe/unique entries: `report-before-cleanup.json`, `server-peer-log.txt`, `v1.jsonl`, `v2.jsonl`, `SHA256SUMS.txt`.
- Manifest covers exactly the four other ZIP entries; **4/4 SHA256 recomputed and matched**.
- Embedded `report-before-cleanup.json` agrees with separately supplied finalized JSON on **20/20 shared top-level fields**. The finalized JSON alone adds `cleanup_verified=true`; this is an **expected version difference**, not byte-identical report snapshots. Cleanup is guest-reported and was not externally OS-attested.
- Raw V1 = **408 bytes / 3 canonical ordered rows**; raw V2 = **1,485 bytes / 3 complete canonical events**. Recomputed all three V2 event hashes and domain prefix, sequential indices/predecessors, unique nonce/IDs, R60 sorted `before`/`after` content commitments, final head, and exact V1/V2 append-order coherence: **PASS**.
- SHA256 V1 = `2e1918b2c890dcf337b314692d7201a8cbdc223046322ea45953615de3144ec8`; SHA256 V2 = `9c221fa381fed4cfecc71d89e285bdb8ecc0995bfb49f8572a3177bbd4c66ac0`.
- Final V2 head = **`6e1d74f7860e0173b9b049487a6a89428439a987809cf363fa27503ae0b06ea1`**.
- Raw `server-peer-log.txt` reproduces the JSON's **all 10 log lines** (four SID/response pairs plus PID, writer SID and permit/deny totals) exactly.

The guest report records an *OS-token impersonation-gated Named Pipe*: authorized reader account SID `...-1001` obtains `RESERVED_ONLY_NO_SIGN` on first request and `ALREADY_RESERVED_NO_APPEND` on repeat. A synthetic rogue account `...-1002` claiming authorized SID and an admin token `...-504` both receive `HOLD_PEER_IDENTITY` and no new reservation. Writer's guest token `...-1000`; the three non-admin synthetic accounts have distinct SIDs. Parent-directory DACL readback shows writer Modify, reader/rogue RX, Administrators/SYSTEM Full Control. Authorized reader can read V1/V2 but two *direct* append attempts produce guest-reported `ACCESS_DENIED`; no independent external Windows event trace of denials exists.

### Independent verification boundary

**This is a real successful synthetic Windows Sandbox experiment**, not an OS credential attestation from an unrelated trusted domain. All reported OS-token and denial events ultimately originate with the same guest controller, though raw journal hashes and report consistency were independently recomputed. The Named Pipe C# source calls `pipe.RunAsClient(...WindowsIdentity.GetCurrent()...)` and checks the resulting OS SID; it deliberately ignores the claimed SID field as an authorization basis. This establishes tested peer-token gate behavior **only** in a disposable guest.

## 3. Remaining security gaps (DO NOT promote to trust)

1. **Independent administrative latest-floor custodian remains NOT_ESTABLISHED.** Admin/SYSTEM in the guest have full journal access; same-admin local V1+V2 rollback and flag deletion from prior G3/V12 tests remain relevant.
2. **No production or real frozen V9 service/signer.** No NCryptSignHash, nonextractable Ario key, real Ario signing broker, signed native receipt, original service crash/restore, or Genesis/trust activation.
3. **No independently witnessed host event trace.** ZIP and manifest were created under the test administrator. A successful local credential gate does not prove hostile-admin-resistant custody.
4. **A Rekor historical inclusion is not a latest-status oracle.** The existing synthetic public Rekor inclusion can prove a published historical checkpoint existed, but cannot by itself establish a monotonically retained newest authorized `(seq, head)`.
5. **No end-to-end production replay/race-proof.** This G4 test contains one authorized append and a duplicate attempt, not the full G3 crash windows combined with the G4 Named Pipe. Additional combined fault testing is needed.

## 4. Next G5 gate

Retain the previously verified `(epoch, seq, head, receipt digest)` on a **separately administered** domain inaccessible to the publisher; verify its source pin and independent write/delete/recovery permissions. Deliberately roll publisher V1+V2 back to a prior prefix and submit old/same-seq-fork checkpoints. Require `HOLD_ROLLBACK`, `HOLD_FORK`, `HOLD_REMOTE_LATEST_UNAVAILABLE` with **external persisted pre/post evidence**, not only same-machine signed SQLite. The optional **founder-controlled offline device** is a weaker manual minimum-floor custody experiment, not automatic independent-administrator or authoritative-latest proof.

**Verdict:** `G4_FOUNDER_SANDBOX_SYNTHETIC_PEER_SID=PASS`, `G4_RAW_BYTE_AUDIT=PASS_38_OF_38`, `G4_SOURCE_PACKAGE_SHA=MATCH`, `NATIVE_V9_SIGNER=NOT_EXECUTED`, `G5_INDEPENDENT_LATEST_FLOOR=NOT_ESTABLISHED`, `TRUST_ACTIVATION=NO_GO`, `PRODUCTION=NO_GO`.

Original user's four attachments were not uploaded to the GitHub repository; only derived metadata, checks and research conclusions were added.
