# R63 G5 — Founder-controlled physically separate verifier floor (research proposal)

**2026-11-21 · RESEARCH_ONLY / DESIGN_ONLY / HOLD / NO_MERGE / PRODUCTION=NO_GO**

## Motivation and separation of authorities

The public Sigstore Rekor inclusion of an explicitly **synthetic** V9-format checkpoint is independently managed external *historical* evidence. It does **not** supply the authoritative `latest` floor. The `G5` Ed25519/SQLite floor simulator enforces monotonic `seq/head` within a single machine but cannot protect its own database and key from the common administrator.

A third-party human operator is **not essential** to the *weaker* goal of defending a verifier's **previously observed minimum floor** against a compromised publisher desktop. A physically separate, founder-controlled device can hold an **independent copy of the last accepted `(epoch,seq,head,receipt_digest)`**, provided the publisher cannot access the device's write/admin credentials or synchronization account.

The founder's phone is a **candidate trust domain**, not a deployed custodian. Do not install an app, connect the phone, provision a key, or enable trust based on this note alone. The laptop remains reserved for a future signer; this design does not require touching it.

## Minimal no-other-human two-domain experiment (NOT EXECUTED)

**Issuer/publisher (desktop / disposable Windows Sandbox):** emits only a *synthetic* V9 V2 checkpoint and valid public Rekor inclusion evidence. Has no credential that can overwrite the separate verifier minimum-floor file.

**Verifier/custodian (separate founder device):** retains its own copy of the previous accepted `(epoch,seq,head,receipt_digest)`, origin and pinned verification key(s), offline or inside a strongly segregated account. No writable filesystem mount, cloud sync, remote desktop connection or account-recovery path exposed to the desktop publisher. Displayed receipt from publisher is **untrusted until verified**. The founder human explicitly approves *any* increase of the retained floor; a decrease or same-seq different head is rejected. This is manual, not continuous unattended external freshness.

**Independent public history (Sigstore Rekor):** supplies tamper-evident historic inclusion of *synthetic* subject hash under a verified workflow identity, not a latest-status query and not authorization.

## Required experiment and evidence

1. Export the **public-only** synthetic receipt: `seq=3`, `head=6e1d74f7860e0173b9b049487a6a89428439a987809cf363fa27503ae0b06ea1`, Rekor global index `4033996846` (Actions #44943687610), plus full Sigstore bundle and verified workflow certificate. Store no key material. **This is not an Ario live floor**.
2. Before any test, copy the verified previous floor *out of publisher control*; record how the remote verifying device stores it, what credentials could overwrite it, and a hash read back at a later session. Without such proof, independence is `UNKNOWN`.
3. On a disposable publisher test machine, intentionally restore the V1+V2 bytes at seq 2 while the separate device retains seq 3. The verifier must return `HOLD_ROLLBACK` and refuse to auto-import a smaller floor.
4. Present same-seq different head; `HOLD_FORK`. Present a publisher-created replacement public key, missing Rekor bundle, old included historical receipt or an untrusted service answer; `HOLD`.
5. Demonstrate the publisher desktop cannot overwrite/read the custodian signing secret, remote verifier floor or its account-recovery mechanism. Merely showing two Windows account SIDs under the same desktop administrator is **insufficient**.
6. To establish unattended **authoritative latest**, replace manual approvals with a separately administered monotonic CAS + immutable receipts + independent signing key and a verifier pin/floor not resettable by publisher. Return `HOLD_REMOTE_LATEST_UNAVAILABLE` on outages. Do not promote mobile manual storage to an unattended/latest-authoritative custodian without these controls.

## Decision

This option aligns with the intended two-key founder + Ario separation without entrusting a third human: the founder may personally keep the verifier floor on a physically isolated device. **It only improves antirollback relative to the publisher, and does not prove independence from the founder**. There is no current proof that the phone's account/keystore, backups or restore credentials are outside publisher reach, and no real device test was run. The external Rekor log provides auditable history only.

`REAL_PUBLIC_SYNTHETIC_HISTORY=VERIFIED`; `OFFLINE_MIN_FLOOR_ON_SEPARATE_DEVICE=PROPOSED_NOT_EXECUTED`; `UNATTENDED_AUTHORITATIVE_LATEST=NOT_ESTABLISHED`; `PRODUCTION=NO_GO`.
