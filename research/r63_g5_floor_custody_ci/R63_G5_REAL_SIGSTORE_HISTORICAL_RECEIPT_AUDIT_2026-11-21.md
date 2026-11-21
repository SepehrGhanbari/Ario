# R63 G5 — First independently administered public historical commitment (synthetic only)

**Date:** 2026-11-21  
**Trust status:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO  
**This is NOT an independently authoritative latest accepted floor for Ario.**

## What actually happened

A GitHub Actions job on the *isolated research branch* created a **one-shot synthetic-only checkpoint** with the exact bytes:

- Repository path: `research/r63_g5_floor_custody_ci/G5_SYNTHETIC_PUBLIC_CHECKPOINT.json`.
- Exact checkpoint SHA256: `e218d3d05a613024eb26a8e67052aeb61d77d14d6be8ecdede2ed5c27c1a78db`, 377 bytes.
- Synthetic `seq=3` and head `6e1d74f7860e0173b9b049487a6a89428439a987809cf363fa27503ae0b06ea1` generated from initial frozen V9 V2 `a/1,b/2,c/3` *test* reservations.
- Explicit content flags: `test_only=true`, `no_real_ario_keys=true`, `production=NO_GO`, `authority=NO_TRUST_ACTIVATION`.

[GitHub Actions success #44943687610](https://github.com/SepehrGhanbari/Ario/actions/runs/44943687610): Sigstore Cosign **v3.1.4**, pinned installer commit `756fe2d284c7292c4e9b62c8a28f1e5629c59532`, used GitHub Actions ephemeral OIDC identity to sign the **synthetic checkpoint only**. It uploaded a signed transparency entry to public Sigstore Rekor and saved a standard `*.sigstore.json` bundle. Within this run, `cosign verify-blob` returned exactly `Verified OK` with the expected GitHub workflow certificate identity and issuer `https://token.actions.githubusercontent.com`. The same bundle was rejected for a deliberately modified artifact (invalid signature). No real Ario key, signer, TPM, Windows Service, or journal was touched.

Public action artifact [#14722866714](https://github.com/SepehrGhanbari/Ario/actions/runs/44943687610/artifacts/14722866714) downloaded and **independently read as bytes** in this ChatGPT research environment:

- Artifact ZIP 9,081 bytes, SHA256 `234bf1196340a73b5875ecfd456d77718f8e9147e60528c24ca319c9a130b212`; ZIP CRC valid, 5 distinct entries.
- Sigstore bundle 11,583 bytes, SHA256 `c9c6425d4dc217fcf634076c3c7485708011c5bffa3f0aede30e84ce0737cacb`.
- Bundle Rekor **global index** `4033996846`; internal shard proof log index `3912092584`; tree size `3912092591`; one `hashedrekord` inclusion-proof entry.
- **RFC6962 leaf and Merkle inclusion path independently recomputed** from `canonicalizedBody` and twenty sibling hashes; computed root exactly matched `DFzZK4XIwxQC9ZCsiPnho/tPFzvyGM+BUE9KsJcni6g=`.
- Certificate SAN URI exactly `https://github.com/SepehrGhanbari/Ario/.github/workflows/r63-g5-synthetic-rekor.yml@refs/heads/research/r63-g4-guest-external-floor-20261121`, issuer `CN=sigstore-intermediate,O=sigstore.dev`, valid 2026-11-21 19:57:44 UTC to 20:07:44 UTC. `integratedTime` 2026-11-21 19:57:44 UTC.
- No credential/private key was exported from Cosign.

**Cryptographic nuance:** this offline byte audit recomputed the Merkle path against the root in the bundle and inspected the X.509 SAN but did **not independently verify the log's checkpoint signature or X.509 certification chain** using a separately pinned TUF trusted root. The official Cosign verification **in GitHub Actions** did perform verification via Sigstore trusted roots. Do not claim two fully independent root-chain verifiers were run.

## What the public log actually establishes

The Sigstore **transparency log operator is administratively separate from Ario's publisher**. Hence an authenticated, included historical **synthetic** signing event now exists outside Ario's local journal and GitHub repository. This is a real improvement over having only self-administered JSON files. Sigstore's official architecture, however, says the service *witnesses* events and is **not an authoritative business-state storage provider**. A valid historical entry DOES NOT prove that no later valid head or epoch exists. Its index is not a cryptographic guarantee of query completeness. The log's consistency still needs witness-gossip/checkpoint checking for split-view resistance.

Therefore:
- `EXTERNAL_HISTORICAL_COMMITMENT_FOR_SYNTHETIC_CHECKPOINT=ESTABLISHED`;
- `EXTERNAL_LATEST_APPROVED_FLOOR=NOT_ESTABLISHED`;
- `VERIFIER_MIN_FLOOR_OUTSIDE_PUBLISHER_ADMIN=NOT_ESTABLISHED`;
- `LIVE_ARIO_CHECKPOINT_CUSTODY=NOT_ESTABLISHED`.

A future genuine custodian needs a strictly monotonic update API controlled by **a separate administrative trust domain**, an issuer/approval policy not resettable by publisher, a tamper-evident append-only audit history, its own private signing key and an independently retrievable, freshest, signed `(epoch,seq,head,prev_receipt)`. A verifier needs a pinned custodian key and previously retained floor beyond publisher access. Publishing another Rekor entry does not meet those requirements by itself.

## G5 signed-floor simulator CI

[Actions run #44943376732](https://github.com/SepehrGhanbari/Ario/actions/runs/44943376732): **14/14 pass in Windows and 14/14 pass in Linux** on synthetic Ed25519-signed monotonic SQLite custody. Includes forced rollback, fork, gap, stale receipt, absent remote latest, modified data and an intentionally **unsafe** same-admin rollback counterexample. Windows CRLF source pin failure in earlier RED [#44943292265](https://github.com/SepehrGhanbari/Ario/actions/runs/44943292265) was fixed by scoped `.gitattributes`, without weakening the V9 SHA lock.

This is an API/contract simulator: SQLite and signing keys remain under the test runner's admin, **NOT** a real independent custodian.

## G4 fresh founder guest

A separate synthetic Named Pipe G4 **Sandbox candidate** was packaged, with `WDAGUtilityAccount` guard, no autorun/network/clipboard/vGPU, read-only source and runtime, evidence-only writable host mapping and raw proof ZIP. Native WinPS5.1 CI for the new guest controller is still a **distinct acceptance gate** from earlier successful PowerShell 7 G4. Until that native CI completes successfully and the founder executes the exact new guest package, `G4_FOUNDER_SANDBOX=NOT_EXECUTED`. Do not silently upgrade an old CI result to founder guest PASS.

## Do not activate

No real signer/keys, merged code, main/Rulesets, independent custody, production key use or Ario trust activation occurred. The public Rekor record is permanent **synthetic proof-of-existence**, not a record authorizing signatures.

**Final:** `G5_PUBLIC_REKOR_SYNTHETIC_HISTORY=VERIFIED`; `G5_MONOTONIC_SIMULATOR=28/28_DUAL_OS_PASS`; `G5_INDEPENDENT_LATEST=NOT_ESTABLISHED`; `G4_FOUNDER_GUEST=NOT_EXECUTED`; `NATIVE_V9_SIGNER=NOT_EXECUTED`; `PRODUCTION=NO_GO`.
