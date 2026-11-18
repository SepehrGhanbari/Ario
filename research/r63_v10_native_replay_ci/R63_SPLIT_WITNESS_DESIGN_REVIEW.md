# Ario R63 — Independent-process witness separation: review gate V10→V11

**Status: RESEARCH_ONLY / DESIGN_ONLY / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO**

## 1. Verified frozen source and why a process split is not a one-line change

Actual founder-supplied V9 archive SHA-256 `db8f1b1a76795589d905fac3f52c1ec32323611585897dd9eb94b259ec6581e9` was reopened for this review. Its `Input/guest_driver_r63_v9.py` has SHA-256 `13b4526428322db3936e0dbfba36ab03925d3ecb0b6fdf0f0c7eb8090493af19`.

The V9 `WitnessHandler.handle` (around lines 141–217) uses `parent=self.server.owner`, `parent.lock`, `parent.spends`, and live `parent.witness` / `parent.actor` objects. `WitnessServer` (around lines 219–228) binds loopback and starts as a **daemon thread of the driver** (around line 449). It does not run as a separate restartable witness RPC parent.

The `spend` handler compares the historical V2 sidecar against the **in-memory** `parent.spends` and the nonce-sorted R60 digest, but does not compare the current V1 disk content before acceptance. In V9 the V2 record and then the V1 record are separately flushed and fsynced; there is no atomic two-file transaction. The V9 report explicitly attributes its witnessed crash to a **separate child append writer**, not the parent RPC process.

**A fresh process must not start with an empty `spends=[]`, silently reconstruct from a single journal, reformat/rewrite a fork, or infer that coherent V1+V2 proves no key use.**

## 2. Proposed bounded guest-only process topology

1. **Controller (guest-only)** creates a unique disposable root with the two explicitly initialized empty V1/V2 journals, a new synthetic actor, a synthetic HMAC request secret, and test-only Software KSP P-256 key. The controller records the initial source SHA and process identities before any test.
2. **Witness RPC parent (separate guest process)** starts with no access to the test broker private key. It validates authenticated operations and an exact one-to-one V1/V2/memory state using a shared agreed protocol. On restart it must verify both raw journals and the independent *R60 sorted-content digest*, in addition to the V2 append-order head. Missing, truncated, duplicated or divergent evidence means persistent `HOLD_UNCERTAIN`. There must be no implicit repair.
3. **Broker signer process (separate guest LocalService identity in the future native gate)** is the only process permitted to access the software CNG broker key. It requires the authorized synthetic policy approvals **and** an acknowledged durable reservation before one native `NCryptSignHash` call. An acknowledged witness alone is not authorization.
4. **Read-only observer** obtains independent process-level readbacks of raw V1/V2, source fingerprints, public-only receipts, process PIDs, return codes and signer-enter/return counters. This observer is still **same-admin** until a truly separately administered trust domain is added.

Transport identity and ACL claims must come from OS SID/token and key-DACL readback, not from strings or merely distinct process IDs. A TCP/HMAC secret stored in the same guest cannot establish independent administrative custody.

**Crucial concurrency rule:** a Python thread lock inside one witness parent does not prevent other processes from rewriting the files after the gate's last read. The native design must establish cross-process exclusion or a stronger append-only committed state primitive across validation → durable decision → signer use, and re-review the recovery boundary. Without that: HOLD, not PASS.

## 3. Required crash and recovery gates

| Gate | Actual event or condition | Required bounded decision |
|---|---|---|
| W00 | Clean journals, matching V1/V2/memory, current sorted R60 digest, valid synthetic approvals | Only then proceed to dedicated test-path; no automatic production activation |
| W01 | Witness parent dies before V2 fsync | Without a public-verified durable receipt/sign-use certainty: HOLD_UNCERTAIN |
| W02 | Parent dies after V2 fsync but before V1 fsync/ACK | On restart, mismatch detected, no new native signer call, HOLD_UNCERTAIN |
| W03 | Parent dies after V1 fsync but before ACK | Coherent journals alone **not** proof of a signed receipt; hold unless a verified durable receipt exists |
| W04 | Signer worker exits after provider use before receipt durability | No re-sign on retry; retain use uncertainty and evidence |
| W05 | Post-receipt signer worker exit | Replay exact stored **publicly verified** receipt bytes; verify same key public pin and nonce |
| W06 | 2 / 8 / 16 genuine standard-user guest clients with repeated nonce and crash race | Confirm one bounded native use, or HOLD. Count exact target-key NCrypt enter/return; record PIDs and token SIDs |
| W07 | Missing/corrupt V1, V2, stale RAM, malformed MAC, mismatched R60 digest | Fail closed before CNG |
| W08 | Coordinated same-administrator rollback of all local DB, V1/V2, receipt and pin | Expected **counterexample**; cannot call antirollback secure |
| W09 | Loss of separately held anchor / compromised verifier trust | UNKNOWN/HOLD; historical receipts append-only; never rewrite |

## 4. What GitHub Actions has actually established

- Frozen V9 sidecar SHA and V1/V2 compare-only candidate: 25/25 per OS on [cross-platform run 44303352340](https://github.com/SepehrGhanbari/Ario/actions/runs/44303352340).
- Synthetic *separate process* RPC crash windows: 3 per OS; 26 concurrent retries per crash point, all HOLD without new journal append, on [cross-platform run 44340534464](https://github.com/SepehrGhanbari/Ario/actions/runs/44340534464).
- Synthetic structural receipt positive/negative controls were exercised separately; an always-HOLD program is not a valid proof.
- New independent **process-level** native Windows CNG receipt pilot: test-only `NCryptSignHash` with one enter/return and explicit test-key deletion, then public-only verifier processes replay the persisted receipt. The public pin comes from an **independent input parameter but is still stored by the same runner administrator**. It does NOT establish an external root of trust.
- On-disk receipt mutation negatives and V1/V2 current-state checks must BOTH pass separately; their checks are not atomic and are not the native V9 broker.
- Power-loss durability, true witness-parent native crash, separate custody, complete sign-use audit and recovery of the actual native V9 signer remain **NOT_EXECUTED / NOT_ESTABLISHED**.

## 5. Safety and manual operator boundary

**Do NOT** run the archived `R63-Run-V9.cmd` or its `R63-V9-Integration.wsb` in the existing readonly-mount Sandbox. Those commands would create a test Windows user, install/start SCM LocalService and create machine-scope software CNG keys; they are **not read-only preflight**.

A new, separately reviewed V11 guest package must be prepared using a **fresh disposable Windows Sandbox**, synthetic identity and keys only, network/clipboard disabled, separate read-only source and write-only evidence export mounts, no original ZIP rewrite, no host or laptop security changes. A human operator must be given the SHA256 of the exact guest package and a fail-closed CMD launcher before any native process/service mutations.

## 6. Go/no-go decision

`GO` only for further **synthetic, disposable, narrowly scoped** GitHub CI or guest test development.

`HOLD` for native V9 witness-parent process split until separate-process bootstrap, complete durable-state recovery, cross-process exclusion and independent observer tests have source review and recorded failure cases.

`NO_GO` for founder real key, Ario independent key, R51 TPM, production trust, GitHub main/Rulesets and independent-custody claims.

**No PR or merge authorization implied.**
