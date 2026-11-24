# R22.7 — Durable retained witness floor under publisher-only rollback

**RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.**

Baseline: #350 at a07afd368a6f89f5962a7e9467b2bb8ea994471a. Separate PR #352.

## Reuse and scope

- R22.6 real prefix and two-witness comparators and actual synthetic REST-observer test harness are unchanged.
- R10 #304 at fae07e8e3453d946a2e7928d2e67de0e8663cdd5: exact byte-identical module implementation/research/r10_durable_monitor/monitor.py, Git blob 61e649ec0bb6adfa3c0dc2a95bbf8675edd69dec. Only its existing canonical serializer and atomic fsync/replace floor writer are used by the new integration. Its pinned Sigsum receipt semantics remain unchanged and are not applied to GitHub evidence.
- R6 #273 and A15 #346 provide the prior distinct-UID isolation design and explicit common-administrator rollback limitation. This lab does not transplant A15 procedural-choice policy into the CI observer.

A laboratory controller constructs an initial two-record floor and separately observed four-record extension from R22.6. The durable record binds fixed scope, record count, head hash, full prefix SHA256 and the two exact witness checkpoint declarations (and parents). Reopening reconstructs the witness comparator control from retained bytes, not candidate-supplied declarations. A forward transition requires prior prefix correspondence and exact parent checkpoint correspondence. A same-checkpoint retry is not freshness proof. A newer candidate without a retained checkpoint is HOLD. The reader is bounded and reuses the existing strict checkpoint parser.

## Executable test plan

The new 12-case test module runs the real R22.6 observation/checkpoint path plus file persistence. Portable controls: publisher rollback only; unobserved extension; idempotent retry and same-count fork; incorrect predecessor; missing/truncated/inconsistent retained floor (six mutations); common-admin joint rollback residual.

A dedicated advisory GitHub-hosted Linux job executes the UID test under a disposable root test supervisor, using two unprivileged numeric UIDs (65534 publisher and 65533 witness), separate mode-0700 directories and no supplementary groups. Both principals must successfully write their own synthetic files. The witness subprocess imports the byte-identical R10 persistence module from a supervisor-owned read-only copy and writes its floor at counts two and four. The publisher restores its old journal and attempts six operations against the protected witness path: read, overwrite, replace, unlink, chmod, and directory rename. Each must be denied; the retained bytes must remain equal to the count-four floor, and the real comparator must flag the publisher's old prefix. The supervisor then deliberately rewinds the floor to demonstrate the common-root residual.

The supervisor selects the synthetic input records and performs comparison; the UID case tests OS filesystem access, not an authenticated IPC protocol or a independently running observation service. The dedicated job is scoped to this same-repository research branch, uses read-only contents permissions, does not persist checkout credentials and is not a required authorization check. Windows runs the portable cases, not Linux UID isolation.

## Deliberate limits

- The two witness declarations in the floor file are synthetic, not two actual independent administrators. Distinct UIDs establish a specific filesystem boundary only; root, host administrator, VM snapshot operator and custodian compromise remain outside that boundary.
- The same administrator can restore both old publisher and witness bytes, reproducing a conditional match; that assertion is an intended residual test, not evidence of anti-rollback protection.
- The controller has a modelled event view. Events it never saw cannot be recovered by retention. Neither conditional match nor stored sequence establishes event truth, complete history, freshness, cryptographic authenticity or evidence admission.
- The adapter is test-only, supports exactly two/four records, uses sequential advancement and does not implement multiprocess concurrent floor writers, authenticated requests, replay-resistant remote receipt exchange, physical power-loss guarantees, or independent deployment.
- R10 has earlier crash/recovery controls in #304; this integration does not claim those were rerun against new floor semantics.

Next research: verify the exact transition protocol across an independently managed endpoint, with independently retained scope/sequence/digest and nonce-bound receipts, outage and lost-response recovery. No need to invent another witness format before testing the existing custody designs. Real administration independence remains NOT_ESTABLISHED.

## Reproduction

Portable: from implementation, python -m pytest -q tests/test_r22_7_retained_witness_floor.py (UID case skipped unless disposable Linux root supervisor).
Dedicated Linux: the isolated advisory workflow executes the named UID test. Do not run it on a production or signer machine.

Initial source/test/workflow head 53c1d04a2e38145dc84c2764d1734c451f83c2cb. Actual CI results are recorded on the PR after exact-head verification.
