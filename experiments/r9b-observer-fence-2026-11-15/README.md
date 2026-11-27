# Ario R9-B — observer-reserved local conditional effect (research only)

**Dated:** 2026-11-15 · **Status:** `DRAFT / RESEARCH_ONLY / NOT_DEPLOYED / NO_TRUST / NO_MERGE`  
**Scope:** one new standalone directory under `experiments/`; no changes to #185, #212, M0, signing, main, real ledgers or governance.  
**Predecessors:** R8 negative-custody findings ([#185](https://github.com/SepehrGhanbari/Ario/pull/185)); R9-A shared-admin/TOCTOU negative findings ([#212](https://github.com/SepehrGhanbari/Ario/pull/212)).

## What this actually builds

This is a deliberately disposable standard-library prototype on POSIX, with a **real observer server process** over `AF_UNIX`, a separate **real CLI action process** for each operation, two SQLite databases, HMAC-authenticated requests and operation IDs. Both databases, the test key and processes are operated by **one test administrator**. The software cannot attest that the observer is a legally, operationally or administratively independent custodian.

Only synthetic `RESEARCH_VIEW` operations may be written to the *local scratch* `effects` table. There is **no adapter** for real external HTTP, model replies, financial transactions, irreversible side effects, evidence admission, certificates, signatures, live Ario authority or key publication. **`APPLIED_LOCAL_ONLY` must never be read as a globally atomic or externally acknowledged action.**

### The R9-A T17 change: durable observer reservation before the local write

```
            sink process                         observer process
           BEGIN IMMEDIATE                       BEGIN IMMEDIATE
             HEAD  ----------------------------> current seq/hash, pending
             check local == remote
             RESERVE(op_id, intent, seq/hash) ---> checks head; PREPARED persisted
                 |                                CAS now forbidden while PREPARED
             INSERT local synthetic effect
             COMMIT local transaction
             FINALIZE(op_id, receipt) ----------> PREPARED -> COMPLETE
                 |                                CAS allowed again
             APPLIED_LOCAL_ONLY
```

**An epoch CAS is serialized with RESERVE in the same observer SQLite transaction**. The R9-A attack in which a direct authenticated observer CAS occurs *between a HEAD read and an effect write* is rejected in R9-B: if the CAS wins first, the RESERVE cannot match the observer head; if the RESERVE wins first, the CAS cannot proceed while it remains `PREPARED`. This is a **source-scoped protocol result**, not a remote distributed transaction or a guarantee under a compromised observer administrator.

**After the initial R9-B draft, an additional failure was reproduced:** a second HMAC-authenticated client could forge `FINALIZE` for the victim's pending reservation using the predictable receipt and known operation ID, then allow CAS ahead of a still-running local effect. This is a real *protocol-level* negative, separate from the stronger same-admin rollback. Initial commit `2c718a87264faef5eb6166d0f3911212074904ad` retains the vulnerable source and the initial 19-test report. In the corrected revision, each RESERVE generates a fresh 256-bit random bearer token, stores only its SHA-256 digest in the observer, returns the token only to the reserving caller, and requires it in FINALIZE. B20 rejects missing/wrong tokens even when the other client possesses the shared test HMAC key. **The same administrator can still extract the token, impersonate a caller or overwrite both databases.** This is not an independent authority or protection against a compromised observer host.

`RESERVE` also denies a simultaneous second reservation. The local SQLite `BEGIN IMMEDIATE` serializes cooperating local writers. Identical `op_id` retries after a fully completed local+observer operation return the stored receipt without a second local row. Different payloads with a recycled ID are denied.

### Crash and uncertainty rules: prefer HOLD to false affirmation

* Crash **after RESERVE but before local insert**: a pending observer reservation remains; all new actions and epoch changes are HOLD until reviewed. No automatic expiry or automatic cancellation is authorized.
* Crash **after local insert but before FINALIZE**: a local effect row **may exist**; public result cannot be claimed finished. Returns/stays `HOLD` or `HOLD_UNCERTAIN_LOCAL_EFFECT`, not false success, until a separate evidence-based reconciliation process is designed and tested.
* Crash **after observer CAS but before local epoch commit**: local and observer heads disagree; fresh actions HOLD. Manual reconciliation is *not* implemented.
* Observer unreachable or malformed/tampered response: fail closed. HMAC proves possession of the test key only; not independent custody.
* An out-of-band **admin-level direct disk edit** is outside this RPC lock. It is not made safe by the reservation protocol.

## Explicit failures and non-closure

1. **Shared-admin rollback (NEGATIVE_CAPABILITY):** If the same operator restores both databases to self-consistent old copies (including reservation/nonce history), an old epoch again looks current and a synthetic local effect is admitted. This is an observed **security failure**, even if the test expected it.
2. **No external-action atomicity:** Observer reservation and local SQLite insert are in distinct databases. A lost result after the local commit cannot be truthfully reported as `NOT_APPLIED`; it requires `HOLD_UNCERTAIN` and destination-side reconciliation. This code has no external action adapter.
3. **No independent checkpoint:** Two databases or AF_UNIX processes controlled by one administrator do not satisfy independent witness custody. An independently operated/anchored epoch and immutable remote history need independently verifiable controls and a separate adversarial test; not simulated operator identity labels.
4. **Liveness limitation:** A stale `PREPARED` record may stop all progress indefinitely. Automatic release on timeouts would reopen the very race/ambiguous-result risk this prototype refuses. A separate owner-approved reconciliation contract must define real recovery.
5. **Threat boundary:** The toy HMAC key, local SQLite files, socket and test process permissions are all under the same administrative control. Root can manipulate source, key, process, DB history and publication. Neither Git history nor this README proves that it did not.
6. **Evidence boundary:** `M0 PASS`, XERJ search IDs, a matching hash, prior model consensus and a green test do not mean data is true or independently witnessed.

## Research-only 20 control cases (including post-review B20)

| Case | Input/target | Observed category to check |
|---|---|---|
| B01–B03 | Ordinary apply, duplicate, conflicting reuse | Local effect once / conflicting reuse HOLD |
| B04 | Authorized epoch CAS before reservation | Old effect HOLD due head mismatch |
| B05–B06 | Crash after reservation; attempted direct CAS and new actions | Persistent PREPARED → CAS/action HOLD |
| B07 | Real process crash after local insert, before FINALIZE | Row exists; future calls HOLD pending reconciliation |
| B08 | Real process crash after observer CAS, before local commit | Head mismatch, no new effect |
| B09–B10 | Stale epoch and ABA replay | No new local effect |
| B11–B12 | Observer unavailable; restore only local database | HOLD |
| B13–B14 | Eight concurrent real action clients; competing action+epoch change | At most one effect; no stale post-CAS success |
| B15–B16 | Wrong HMAC; unsupported authority; boolean sequence | HOLD |
| B17 | Restore **both** DBs under one admin | **NEGATIVE_CAPABILITY** — old epoch reused |
| B18 | Privileged CAS precisely **after HEAD, before RESERVE** | RESERVE fails; no stale effect |
| B19 | Replay an identical authenticated observer nonce | Rejected |
| B20 | Other authenticated client attempts to finalize victim reservation without its fresh token | Missing/wrong token rejected; pending fence preserved |

All test fixtures, oracle expectations and labels were authored by the same developer. They are *development controls*, not blinded independent reproducibility. B17's expected test `ok` proves an **attack still succeeds**.

## Reproduction

From this directory in a disposable, authorized Linux/POSIX Python 3.10+ environment:

```sh
python3 -B -m unittest -v test_r9b_fenced_sink.py
```

The suite allocates fresh system temporary directories and `0600` ephemeral HMAC material, launches a real observer process and real subprocess CLI for each action, and deletes its own fixtures. A timeout, stderr, expected-failure observation, a mere return code, or a success label is not independent proof: review the raw log and source hashes. Do not point the prototype at any existing repo, ledger, wallet, service or production key.

## R9-C admission prerequisites — NOT MET

* **Administrative independence:** separate legal/admin root, hardware/identity key custody and independently verifiable append-only head history; external adversary exercises rollback and conflicting-head branches. Here: `UNKNOWN / NOT_ESTABLISHED`.
* **Crash recovery:** authenticated remote `PREPARED` state plus destination outcome inquiry, bounded manual or peer-governed dispute resolution; no locally fabricated COMPLETED outcomes. Here: `NOT_IMPLEMENTED`.
* **Real external sink:** conditional commit / compare-and-swap **at the destination**, or idempotency with verified result-reconciliation; network + provider ambiguity must report `HOLD_UNCERTAIN`, never asserted exactly-once. Here: `NOT_CONNECTED`.
* **Separate science and governance:** independent labels for false-positive / abstention metrics; no retroactive edits of negative histories, and no permanent signer/trust or #133/#151 activation. Here: `HOLD`.

**No source in this lab installs a trust authority, decrypts data, publishes a public page, or updates protected branches.**
