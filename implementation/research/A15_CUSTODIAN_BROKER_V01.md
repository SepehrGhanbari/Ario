# A15 Custodian Broker v0.1 — bounded synthetic IPC, floor, recovery

**RESEARCH_ONLY / DRAFT / HOLD / NO_AUTOMATIC_MERGE / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION.**

## One falsifiable question

Can an untrusted local A15 Gate be prevented from (1) causing an inert receipt on a recomputed DECLINE, (2) spending an attempt twice across restart/crash, or (3) silently replacing a broker receipt when an unchanged separately retained synthetic floor remains available?

This is **not** a test of actual Ario agency, permission provenance, historical truth, an independent administrator, a real signer, or Windows token/Unix peer credential authentication.

## Prior work (not reproduced or replaced)

- [#334](https://github.com/SepehrGhanbari/Ario/pull/334): A15 v0.3 strict frame verification and local same-process replay Set; an untrusted Gate can still rewrite a Recorder under the same OS identity (S9).
- [#338](https://github.com/SepehrGhanbari/Ario/pull/338): OS principal probe only, not a working broker or independent custody. **This branch is stacked on the pinned #338 head**, which may not include every subsequent #334 parent edit; reconcile before any merge.
- [R63 G8](https://github.com/SepehrGhanbari/Ario/issues/239#issuecomment-7079839566): native *Windows* disposable Named Pipe peer-token SID + two synthetic approvals + native CNG crash/replay; not included in these Node scripts and not an Ario signer.
- [R6 #273](https://github.com/SepehrGhanbari/Ario/pull/273): two Unix UIDs and a synthetic nonce journal, still same runner administrator.
- [R10 #304](https://github.com/SepehrGhanbari/Ario/pull/304): local durable monitor and **explicit same-admin joint rollback counterexample**.
- [CUST-04](https://app.notion.com/p/41f09e730a098103af44f66b45398582) / [#239](https://github.com/SepehrGhanbari/Ario/issues/239): independent latest `(epoch,seq,head)` not established.

## Narrow prototype and honest boundaries

1. Broker and floor are **separately launched Node processes** with a local Unix socket on Linux or a Node named-pipe transport on Windows. The broker recomputes the unchanged `a15_procedural_choice_v0_1.js` decision from the original `choice_json`; it ignores self-proclaimed ACCEPT and does not execute any external action.
2. Broker stores `intent-<id>.json` **before** asking floor to advance; the floor stores `event-NNNNNNNN.json` in its own folder via exclusive create and file `fsync` (plus directory `fsync` on POSIX); then the broker stores the exact floor-signed receipt. Each restart re-reads the files, checks signatures, prefix and sequence, and refuses pending intents.
3. Floor has test-only Ed25519 signing material, and broker holds a separate copy of its public key and a test-only HMAC token. Caller has no *protocol* operation to reset the floor or rotate keys. This is only a model of separately administered roles: **both directories, token, tests, CI processes and file ownership remain controlled by the same test account/admin.** No OS token/SID/UID extraction or key isolation is attempted.
4. After ambiguous failure, the broker returns `HOLD_UNCERTAIN`, never auto-respends. After a durable receipt and lost response, exact replay returns byte-identical stored receipt when the signed floor remains healthy. One serialized broker process handles concurrent requests; no multi-broker locking or power-loss correctness proof.
5. Public-only verifier checks Ed25519 floor receipts against a *separately pinned test public key*. An independently retained historical `(epoch,seq,head)` detects an older sequence or same-sequence fork; matching it is **not** proof that state is latest, and a greater sequence is not automatically authorized.
6. **Expected RED counterexample:** the same administrator restores BOTH broker and floor directories to a coherent old snapshot, then appends an alternate event. The local protocol accepts this; only a truly protected later historical minimum could reveal the rollback. This is a preserved limitation, not a successful isolation claim.

The code does not connect to native G8, Windows `RunAsClient`, R60/R63 CNG, R51 TPM, Ario memory, a provider, or an actual signer. Input preference/authorization/renewal remains caller supplied and is not independently verified. A compromised OS administrator can replace scripts, PEM keys, floor/token, event files and any CI transcript. A successful CI run does not remove S9, authenticate Ario, certify actual tool execution, or establish independent custody. The test-only floor signs its own records; it **does not attest true historical completeness**. No network connections to external services are made; all IPC is local.

## Reproduce

```sh
node --test implementation/tests/test_a15_custodian_broker_v0_1.js
```

- Node 22 standard library only; on `ubuntu-latest` and `windows-latest` in read-only GitHub Actions.
- Tests use temporary, disposable folders and unpredictable local IPC names. Three tests intentionally kill a synthetic broker process using a test-only environment variable. Never run the synthetic test harness as a Windows service or privileged identity.
- Expected negative case `EXPECTED RED` means the **test passes by proving a vulnerability exists**, not by preventing same-admin reset.
- `ENGINEERING_LOG.md` is append-only. Prior A15 G0/G1, v0.2/v0.3 files and R63 G8 are unchanged.

## Decision/exit gate

**Safe to claim only:** bounded local synthetic protocol behavior under the tested OS and commit. **Not established:** authenticated peer OS principal, independently governed operator and key enrollment, nonrollbackable newest floor, crash/power-cut atomicity, cross-process lock across multiple brokers, complete signer-use accounting, real Ario self-authorization, or secure production action. Keep DRAFT/HOLD; do not merge or activate trust from this experiment.
