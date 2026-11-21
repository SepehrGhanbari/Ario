# R63 G4 — real Windows RPC peer SID + retained floor + external calendar audit

**2026-11-21 | RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO**

## 1. Source boundary and threat model

Starting point: [G3 founder-supplied raw evidence byte audit](../r63_g3_witness_ci/R63_G3_FOUNDER_PS51_FIX_GUEST_BYTE_AUDIT_2026-11-19.md). G3 proved native distinct Windows worker/reader SIDs and synthetic V1/V2 journal crash/HOLD semantics, but **the loopback TCP peer's Windows token was NOT authenticated**. Also, a same-administrator could roll back both journal files and a local uncertainty flag.

G4 changes *only* research files under `research/r63_g4_peer_ci/` and its own GitHub Actions workflows. It never calls a real V9 signer, CNG provider, TPM, production policy or real account/keys. No change to `main`, Rulesets or trust activation.

## 2. Native Windows CI proof: actual Named Pipe token impersonation

[Green Windows native Actions #44939990366](https://github.com/SepehrGhanbari/Ario/actions/runs/44939990366) `completed/success`. Raw artifact ID `14721286721` downloaded and opened independently; ZIP SHA256 `8ee19852e7e237a37b513bd641e274196548d08a2bba92e76c95597d04623f38`, CRC clean, with `r63-g4-run.log` and `r63-g4-peer-report.json`.

**Method:** `G4PipeGate.cs` runs the server under a real nonadmin writer token, reads the *connecting Windows named-pipe client's* impersonated SID using `NamedPipeServerStream.RunAsClient` / `WindowsIdentity.GetCurrent()`. The claimed SID in the request body is not trusted as identity. Client is a separate nonadmin reader SID; a third nonadmin SID spoofing the reader's payload SID and a caller with the local administrator token spoofing the reader's payload SID are tested. DACL restricts direct journal writes and grants them only to test writer; all accounts and files exist solely in an ephemeral Windows hosted runner.

**Actual separately preserved JSON result:**
- Writer SID ends `-1003`; permitted reader SID `-1004`; rogue SID `-1005`; administrator SID `-500`. Server reports `SERVER_SID=-1003` and each actual client SID; all token IDs carry a common **ephemeral CI machine** prefix.
- Authorized reader first request `RESERVED_ONLY_NO_SIGN`; duplicate `ALREADY_RESERVED_NO_APPEND` — no duplicate journal entry.
- Rogue reader with forged legitimate SID in payload `HOLD_PEER_IDENTITY`; local administrator with forged reader SID in payload also `HOLD_PEER_IDENTITY`. Server observed `ALLOW_COUNT=2`, `DENY_COUNT=2` and distinct actual client SIDs. This does **not** prove that a malicious administrator who can alter ACL/process/code cannot bypass the gate.
- Frozen V9 V2 sidecar SHA256 `c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd`, test V1=2/V2=2 base, V1=3/V2=3 final, coherent, V2 final head `6e1d74f7860e0173b9b049487a6a89428439a987809cf363fa27503ae0b06ea1`.
- Two direct V1/V2 append attempts from the restricted SID return genuine `ACCESS_DENIED`; cleanup `true`.
- No original V9 service, actual signer, authorized use/receipt signing, complete transaction semantics, external custody or production data was touched.

**Preserved RED tests** [#44939753842](https://github.com/SepehrGhanbari/Ario/actions/runs/44939753842) too-long accidental account-name array; [#44939804356](https://github.com/SepehrGhanbari/Ario/actions/runs/44939804356) compile under wrong TEMP; [#44939956181](https://github.com/SepehrGhanbari/Ario/actions/runs/44939956181) absent DLL. Fix: explicitly distinct short account names; compile one G4 native DLL under CI synthetic owner, restricted child only loads read-only .NET Framework DLL. RED evidence not rewritten/erased.

## 3. Simulated independently retained latest-floor contract

`test_retained_external_floor.py`: **8/8 PASS** on both Windows Server 2022 and Ubuntu 24.04 [Actions #44939990366](https://github.com/SepehrGhanbari/Ario/actions/runs/44939990366). With trusted, externally retained fresh `(seq, head)`, `spend_chain_v2.review(...,external_anchor=...)` detects older prefix and same-seq fork. Missing/stale/self-declared floor gives HOLD. Unknown signer-use status gives HOLD even if journal consistency is satisfied. **Negative control:** coherently roll back journal and claimed local floor, and a local check can falsely accept; this intentionally exposes why **separate custody is required**.

**Crucial:** this was a **mock** of independent external control and a boolean `verified_external_receipt`, not an actually authenticated external floor, antirollback service or independently controlled key. No algorithm can infer a fresh, authorized last head from a single timestamp.

## 4. Actual external calendar trial: real HTTP, but quarantined evidence

A single public *synthetic digest only* was submitted via [GHA one-shot #44940290303](https://github.com/SepehrGhanbari/Ario/actions/runs/44940290303) to `https://alice.btc.calendar.opentimestamps.org/digest`. **No real Ario data, project key, machine information, or real signer history was submitted.** Reported HTTPS status 200, raw calendar response size **172 bytes**. Original publicly produced artifact `14721069513` downloaded and verified read-only:
- CI artifact ZIP SHA256 `524177b648b190c72eb89488e9f1f44a6a128f490e1aa36d01a42c3796976136`;
- `r63-g4-ots-report.json` SHA256 `e3d69e37fab96e9fd53da174d9d3eb1375c0781d3ed86f06859fc51bdf03dde7`;
- `r63-g4-ots-response.bin` 172 bytes SHA256 `ce351e06fee6666d411980e6aa7d2688fa5bd0278a82f4e3aa887bb85031697e`;
- The checkpoint object reserialized canonically reproduces the exact submitted 32-byte SHA256 digest `3798a0ae4399235d3861f17412ba801b575b4bdbaf83231a4b2150207fa55987`, includes the synthetic `seq=3, head=6e1d74...ea1`, 32 random salt bytes and a `synthetic=true` domain. This head also matches the independently reviewed G4 native CI final synthetic journal head.

**Critical independent negative finding:** Parsing all OpenTimestamps proof operations and pending-attestation tag `83dfe30d2ef90c8e` from raw bytes obtains the literal calendar URI
`-https://alice.btc.calendar.opentimestamps.org` (with a **leading hyphen**); expected allowlisted official URI is `https://alice.btc.calendar.opentimestamps.org` (without hyphen). The raw URI is **46 bytes** and differs from the whitelist. No bytes have been stripped or rewritten; the original raw response is preserved. Under strict fail-closed acceptance, mark `HOLD_UNEXPECTED_PENDING_ATTESTATION_URI`. This may be caused by provider configuration or another protocol issue, **not independently attributed**; do not assume a malicious operator or that a successful HTTP response implies an acceptable pending proof.

Independently produced audit artifact `R63-G4-External-Calendar-Forensic-Audit-20261121.json` SHA256 `605bc8ff03e4c324c42262c09ab07fda1f40151db98b2af3e8ce39ef8873bd79`. **No valid/redeemable OTS file or Bitcoin confirmation was asserted or fabricated.**

### Source hardening and tests
`g4_ots_attestation.py` is a bounded read-only strict-URI parser; `test_g4_ots_attestation.py` contains nine positive/negative tests for missing/trailing bytes, invalid tag, invalid digest, wrong URL, and **leading hyphen**, all **9/9 PASS locally**. Future `one_shot_ots_probe.py` source has been modified to validate proof bytes after HTTP and set `HOLD_EXTERNAL_PENDING_FORMAT_INVALID` for untrusted URI, not just accept HTTP 200. The one-shot public submission is **not reexecuted** on a code change. These unit tests run within Windows+Linux CI on the G4 research branch. This parser does not establish Bitcoin attestation or a last-authorized-state floor, even for a structurally acceptable response.

## 5. Security limitations and next actionable checks

1. **Peer SID authentication = pass in ephemeral Windows native CI only**; not yet measured in founder's disposable Windows Sandbox; not integrated with actual V9 signer/broker. Named Pipe client token is stronger than an unbound TCP payload but *not* proof of application authorization, approved policy, sign-use completeness, or independent operator custody.
2. **Same-admin local rollback remains feasible**: all test journals and user accounts share control of one CI runner administrator and SYSTEM. We need a truly independent holder of a fresh, source-authenticated `(seq, head)` and a verifier floor with rollback protection across its own restart. Pending calendar timestamps cannot substitute for that authorization policy.
3. The public calendar response is **quarantined** due raw URI mismatch; external latest-floor and Bitcoin attestation **NOT_ESTABLISHED**. Future independent review can use the unchanged raw artifact. Do not repair receipt bytes, repeat public submission without a new explicit research decision, or promote any trust claim.
4. Next bounded gates: preserve source-bound public-only IPC transcript, denial and native token readback; test server crash + peer token revalidation after restart; separately investigate the calendar's unexpected pending URI and obtain a verified independent checkpoint/receipt before any antirollback claims.

**Final:** `G4_OS_PEER_IDENTITY_CI=PASS` / `G4_ROLLBACK_MOCK=8/8 PASS` / `G4_OTS_EXTERNAL_HTTP=200` / `G4_OTS_PENDING_URI=UNEXPECTED_HOLD` / `BITCOIN_CONFIRMED=NO` / `INDEPENDENT_LATEST_FLOOR=NOT_ESTABLISHED` / `REAL_V9_SIGNER=NOT_EXECUTED` / `PRODUCTION=NO_GO`.
