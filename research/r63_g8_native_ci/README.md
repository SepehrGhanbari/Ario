# R63 G8 — Integrated native synthetic broker crash/replay

**RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / NO REAL KEYS / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO**

## Goal and scope

Unlike separate G4 peer-SID, G6 historic minimum, and G7 CNG tests, G8 exercises a **single native Windows CI-only broker process** that must: read a peer's actual Windows Named Pipe impersonated SID; verify two distinct synthetic public actor signatures (FOUNDER=ALLOW, ARIO=ALLOW or signed VETO), reject revoked grants; fsync a per-case durable use-intent; call actual Win32 `NCryptSignHash` once with a disposable named Software KSP P-256 key; fsync a public-only receipt; recover after process death without a second CNG call. Candidate payload is produced only after the exact frozen G4→G6 seq3→seq4 check from G7. This candidate has **no signer authority**.

This is **not** the original V9 driver/broker, production signer, independent Ario identity, independent custody, atomic multi-file transaction, real key permission, authoritative external floor, or proof against same-administrator rollback. The two synthetic actor signatures are generated under one CI administrator, so independent control over the actor keys is **not established**. `NCryptSignHash` native P/Invoke enter/return logs are durable observations in the same administrator's root, not external instrumentation. The native key exists across controlled broker process death; it is deleted after all tests and the identity of the disposable account is removed.

## Bounded Windows test cases

- Normal legitimate signed dual approval from allowed real OS SID: exactly one `SIGNED_` public receipt; repeat exact request returns byte-identical receipt with no new provider entry; rogue actual SID claiming authority returns HOLD.
- Synthetic Ario signed VETO, invalid founder signature and revoked policy: HOLD before durable intent or native call.
- Crash after durable intent **before** CNG: exit 73; replay through a **new broker process** returns `HOLD_UNCERTAIN`, with zero recorded native entry.
- Crash after one real **CNG return** before receipt: exit 73, both one-time enter/return records exist, receipt absent; repeat returns `HOLD_UNCERTAIN` and no second `NCryptSignHash`.
- Crash after durable receipt before answer: exit 73; replay returns exactly the stored *verified public* receipt, without another `NCryptSignHash` call.
- Public-only verification is performed in a **separate admin child** that reads the receipt, pinned public CNG blob and candidate digest but opens no private key. This is a process separation, not separate administrative custody.

The experiment runs on fresh GitHub-hosted Windows Server 2022 runners ONLY with disposable Windows local users. No founder Sandbox launcher is supplied; the founder's desktop/laptop must not run this script. The script checks GitHub repo, OS and elevated disposable runner; it refuses other environments. No GitHub token is persisted by checkout; workflow permission is `contents: read`.

## Explicit limitations and next acceptance boundary

The broker serializes requests within one parent; it doesn't prove a concurrent distributed 2/8/16-client race, external latest head, two genuinely independently controlled approval keys, OS-admin resistance or all uncontrolled power-loss points. It does not touch the founder's retained iPhone minimum (`seq=3`). Conservative durable-intent loss, coherent same-admin rollback, signing-use completeness and native V9 signer behavior remain **HOLD / NOT ESTABLISHED** until separately tested.

**No merge, Ruleset modification, laptop use, host accounts, permanent keys or production activation.**
