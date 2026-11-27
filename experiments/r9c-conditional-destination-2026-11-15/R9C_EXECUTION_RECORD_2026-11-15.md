# Ario R9-C — dated execution and failure ledger

**2026-11-15** · **RESEARCH_ONLY / DRAFT / HOLD / PROD=NO_GO / TRUST=NO_GO**

## What was actually built

Two real POSIX AF_UNIX services, both under the **same local container/root administrator**: (1) a simulated *destination* which atomically executes `DEST_ADVANCE` or conditional `DEST_APPLY` and stores a synthetic `RESEARCH_VIEW_ONLY` effect in its **own SQLite transaction**, and (2) a checkpoint process which verifies an HMAC-protected destination-origin event receipt and stores a monotonic local digest chain in a **different SQLite database**. A coordinator queries both; it never assumes a lost ACK means an effect did not happen. All inputs, keys, result labels and tests are author-controlled. No external service or real Ario evidence or identity authority is connected.

## Historical negative / correction register (never erase)

| Stage | Actual observation | Interpretation |
|---|---|---|
| Initial broad harness run | 25 tests attempted; original log retained as `test_run_initial.log`; failures/errors occurred, including an incorrect test expectation for how a rejected HMAC request should appear to a client holding the **wrong** key. | **Negative/test harness error**. This is *not* a demonstrated security flaw in destination CAS. |
| Next broad harness run | 25 tests, **3 errors** due to intermittent disposable service startup unavailable within a ~1.8s watchdog. Log `test_run_full.log` retained. | Startup-harness limitation, not a successful regression. |
| Bounded correction | Extended startup polling to up to ~10s, explicitly cleaned child services when `setUp()` fails, closed SQLite count connections, and corrected wrong-key expected outcome to fail **response** HMAC verification. Added explicit lookup `op_id`/`kind` check. | Revised self-authored harness; no prior logs or source tests erased. |
| Full corrected run | `python -u -B -m unittest -v test_r9c_conditional_destination.py`, Python 3.13.5, Linux ephemeral container; **25/25 PASS**, exit 0, **71.250s**; log `test_run_corrected.log`. | One green run of exactly these author-authored functional/negative assertions; **not** proof of third-party independence or a global transaction. |
| Extra racing | Two additional standalone runs of tests 22 and 23 each printed **2/2 PASS** in `race_repeat.log`. The enclosing command was interrupted/time-limited before the third repeat could produce a result. | Preserve incompleteness. Two runs only, **not** three; no assumed result for the interrupted repetition. |

No user-owned Ario repo, original R9-A/B files, live key, production service, witness identity, GitHub ruleset or trust state was changed by these local tests. Test-only orphan services from interrupted runs were killed by matching their exact R9-C executable path. All test databases and HMAC key material were generated under isolated temporary directories.

## Selected positive bounded observations

- **In-destination guard:** A directly authenticated epoch change before `DEST_APPLY` caused `STALE_EPOCH_AT_DESTINATION`; no synthetic effect was inserted. If APPLY wins first, it is valid at its then-current epoch; an epoch change afterwards does not retroactively invalidate the earlier commit. Tests 06 and 23.
- **Idempotency:** Eight real subprocess clients raced on the **same** `op_id` and fingerprint. Destination stored **one** synthetic effect row and signed receipt; duplicates did not reapply. Test 22.
- **Protocol:** Bad HMAC, nonce replay, boolean-as-integer epoch, unauthorized scope, altered receipt and noncontiguous event numbering rejected under tested assumptions. Tests 07–14.
- **Uncertain crash semantics:** Actual destination process crash after database COMMIT but before reply yielded `HOLD_UNCERTAIN_DESTINATION`; explicit query-by-ID plus witness proof recording reconciled. Actual witness crash after checkpoint COMMIT but before reply yielded `HOLD_UNCERTAIN_CHECKPOINT`, later resolved idempotently. Tests 15–18.
- **Partial rollback:** Restoring only destination DB or only witness DB produced a mismatch and HOLD when both were queried. Tests 19–20.
- **Missing intermediate receipt:** Witness did not skip events and did not invent a confirmation for missing evidence. Test 24.

## Persisted adverse observation — NEGATIVE_CAPABILITY

**R9C-NEGATIVE-01 / shared-root two-database rollback.** Before a simulated effect, snapshot both independent-looking SQLite databases. Record a synthetic effect and its witness receipt. Terminate both services; restore **both** snapshots using the same root privileges. Restart. Both services now report mutually consistent **older** event heads, and the supposedly prior `op_id` can again be recorded as if new. This was actually reproduced in **test 21**. The fact that the test *expected* this demonstrates a successful **attack/limitation**, not an effective rollback defense.

**R9C-LIMIT-02 / missing atomic transaction across stores.** The destination SQLite effect COMMIT and witness checkpoint COMMIT are not atomic together. The code correctly reports `HOLD_UNCERTAIN` in tested lost-ACK cases and can query back a destination receipt, but it has **not** implemented a real distributed transaction, remote service, or exactly-once semantics.

**R9C-LIMIT-03 / independence.** Both services, DBs and HMAC keys are created and managed by **one test administrator**; HMAC possession only authenticates that test key. Independent operator, independent host/security admin, immutable external high-water anchors and adversarial separate-party attestation remain **NOT_ESTABLISHED**. Neither an additional SQLite database nor extra process proves this property.

**R9C-LIMIT-04 / production.** The only effect is a synthetic row in a disposable SQLite DB. No model, XERJ engine, OpenRouter provider, real endpoint, user authority, key, payment, filesystem target or external action was invoked. All expected verdicts were chosen by this author; no independent blinded benchmark or safety certification occurred. `M0 PASS` does not establish truth or authority.

## Reproducibility & provenance

Source pin: self-contained R9-C research proposal, no production import. All byte checksums are included in `MANIFEST_SHA256.json` in the accompanying ZIP. `test_run_corrected.log` is the exact raw successful-run output. Prior failed logs remain in the ZIP with SHA hashes, instead of being rewritten. The repository PR is a *new* folder only under `experiments/r9c-conditional-destination-2026-11-15/` and must stay DRAFT/HOLD pending independent review.

**Proposed next independent falsifier:** run destination under one administrative domain and checkpoint under another domain which the destination owner demonstrably cannot rewrite, with separately generated keys and out-of-band high-water anchor. Have independent parties attempt rollback of their own storage and both stores; assess false affirmatives and UNKNOWN/coverage, not merely unit-test success. Until then: `EXTERNAL_ADMIN_INDEPENDENCE=NOT_ESTABLISHED`, `REAL_EXTERNAL_SINK=NOT_CONNECTED`, `TRUST_ACTIVATION=NO_GO`.
