# R9-C — conditional action at destination + checkpoint receipt (research only)

**Date:** 2026-11-15 · **Status:** `DRAFT / NOT_DEPLOYED / NO_TRUST / NO_MERGE`  
**Purpose:** adversarially test two independent *functions* (conditional action and checkpoint recording) without claiming two independent *administrators*.

## Scope and authority

This is a **disposable, POSIX AF_UNIX + Python standard-library + SQLite simulation** with real destination and witness processes, ephemeral test-only HMAC keys and synthetic `RESEARCH_VIEW_ONLY` database rows. It has **no actual external API calls, no production endpoints, no signing-key activation, no M0 evidence admission, and no Ario chain authority**. The same container/root administrator owns both databases, keys and process instances. Two service processes or two keys **do not establish independent ownership**.

### Tested vs untested security property

| Property | Mechanism | Evidence boundary |
|---|---|---|
| In-destination conditional action | Destination `BEGIN IMMEDIATE`: validate epoch/head and `op_id` then insert a synthetic effect and append event in **one SQLite commit** | Scoped to this single destination SQLite database and its honest process; not real network service or multi-host transaction |
| Deduplication | Destination `effects.op_id` is unique; same fingerprint returns original signed receipt, conflicting fingerprint returns HOLD | Identity key and payload hash are chosen by client; no claim of external message origin or user consent |
| Concurrent epoch change | Epoch CAS and APPLY take the **same destination transaction lock**; stale expected epoch rejects at destination | Confirms *in-destination* safety, not atomicity with separate checkpoint DB |
| Witness log | Destination-specific event receipt has event index, previous hash, epoch, scope and test HMAC; independent witness DB validates contiguous receipt | Test HMAC shared with destination and retained under the **same test administrator**. An HMAC is not proof of third-party independence or immutable custody |
| Lost acknowledgement | After destination commit but before client receives ACK / before witness records, return `HOLD_UNCERTAIN_*`. `DEST_LOOKUP` and explicit `WIT_RECORD` allow bounded recovery from destination-authenticated receipt | `UNKNOWN` remains valid; no assumption that failed network means an effect was not applied |
| Root rollback | Restore only one DB -> mismatch, HOLD. Restore **both** under same root -> history can appear consistent again | The latter is an intentionally preserved **NEGATIVE_CAPABILITY**, not protection |

### Protocol outline

```
   research client                      simulated destination            checkpoint witness
          |                                     |                                |
   HEAD (dest, witness)  ----------------->  compare public event heads  <--  HEAD
          |                                     |                                |
   DEST_APPLY(expected epoch, op_id)  ---->  BEGIN IMMEDIATE
                                                epoch/CAS check
                                                dedupe op_id
                                                INSERT synthetic effect
                                                append signed event receipt
                                                COMMIT          
          |           signed receipt <-----------|                                |
   WIT_RECORD(receipt) -------------------------------------------------------> verify HMAC + prev/index
          |                                                                  append + COMMIT
          +--------- simulated "checkpointed", NOT independent authority ------+
```

`DEST_ADVANCE` updates epoch and appends event in the **same destination commit**. A direct privileged destination CAS cannot slip between admission and the *local simulated effect*. Two actual, independent, ACID systems remain **non-atomic as a pair**, and the prototype deliberately does not try to hide that.

### Threat tests and adverse observations

The suite exercises real subprocess service crashes after destination commit and after witness commit; concurrent client processes using the same `op_id`; direct epoch CAS race; stale epoch/payload conflict; forged/invalid test receipts, nonces, protocol-shape and credentials; lost checkpoint, replay and missing event. It also restores snapshots of just one or **both** databases under its shared root (the latter intentionally bypasses the claimed custody guarantee).

The author controls source, fixtures, test keys and expected outputs. Thus a green run is self-consistency evidence only. In particular, the negative **shared-admin rollback** cannot be repaired by adding another service using that same root, another HMAC, or one more Git check.

### Independence requirements **not yet satisfied**

A real independently operated checkpoint would require: mutually independent operators and credential custody, separately controlled immutable/high-water storage, independently recorded external anchors for sequence monotonicity, adversarial restore exercises performed by an operator who **cannot modify both stores**, and auditable incident/dispute procedures. Until independently verified, declare `EXTERNAL_ADMIN_INDEPENDENCE = NOT_ESTABLISHED` and `TRUST_ACTIVATION = NO_GO`.

For a *real* external action destination, demand authenticated destination-implemented conditional idempotent commit or an equivalent transaction API, deterministic query-by-`op_id` recovery, well-defined completion semantics, and direct read-after-write reconciliation. When the destination cannot prove the result, return `HOLD_UNCERTAIN` rather than automatically retrying an irreversible action.

### Reproduction

On a disposable Linux system with POSIX Unix-domain sockets, SQLite and Python >=3.10:

```sh
python3 -B -m unittest -v test_r9c_conditional_destination.py
```

No network requests are made. The test allocates temporary directories and new 32-byte keys, launches real service processes, and uses synthetic SQLite rows only. Do not use genuine Ario keys, databases, OpenRouter credentials or production credentials. See `R9C_EXECUTION_RECORD_2026-11-15.md` for the exact observed pass/fail counts, including any early negative runs and unverified assumptions.

**This PR must remain DRAFT/HOLD**. The tests do not establish third-party witness independence, global exactly-once semantics, rollback resistance under common root, or any new evidence/signer authority.
