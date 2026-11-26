# R22.31 — monotonic custodian state machine

**RESEARCH_ONLY / SYNTHETIC_KEYS / NO_REAL_TPM / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_MERGE.**

## Why this exists

A source audit of R22.30 at parent commit fba551689eacd686380c54104fbe8452fc7830e1 found that its embedded custodian gate appended consumed nonces but did not advance durable epoch/head/storage-root state. After one valid 7→8 recovery, a second request with a different nonce could still be checked against the unchanged epoch-7 anchor and approved as another 7→8 transition. The nonce ledger only prevented replay of the exact nonce.

The old result remains historically valid for the specific 27 assertions it ran. This follow-up adds the missing state-machine question; it does not rewrite the prior evidence.

## Prototype behavior

custodian_state.py is a separate, standard-library Python prototype using OpenSSL for RSA signatures and Linux flock for inter-process serialization.

- Verifies the signed initial anchor and every signed receipt in the journal.
- Replays an append-only, hash-chained transition journal to derive the current state.
- Requires exactly one epoch step, the current previous head, the enrolled EK fingerprint, and a changed storage-root claim.
- Commits the transition and signed receipt in one fsynced journal record while holding an exclusive process lock.
- Rejects a second distinct request for an already-consumed epoch.
- Returns the original signed receipt for an exact retry after a simulated post-commit/lost-response crash; it does not sign again.
- Rejects a nonce reused with a different request and detects record tampering or an incomplete final record. It cannot detect deletion of complete tail records or rollback to an earlier valid journal prefix without an external rollback floor.
- Serializes concurrent requests so only one request can consume a given epoch.

## Important limitation: evidence provenance

The new receipt explicitly labels storage_root_provenance=CALLER_SUPPLIED_UNATTESTED. The prototype proves state-machine behavior over the supplied request; it does **not** prove that the claimed storage-root fingerprint was measured from a real TPM. There is no TPM quote, AK-to-EK credential activation, EK certificate validation, PCR policy, firmware/secure-boot evidence, or physical hardware in this experiment.

The journal is also stored on the same research runner. A runner administrator can read the custodian key and replace/rollback the journal. This is not independent custody or rollback-resistant storage. External witness-floor integration remains separate work.

A complete-record rollback is specifically undetectable here: deleting the journal or restoring any earlier valid prefix causes replay to derive that older state from the unchanged signed initial anchor. The local prototype cannot distinguish that rollback from a genuinely shorter history. Only an independently retained, authenticated floor (outside this runner's administrative domain) can detect it; this is an expected RED boundary, not a passing anti-rollback property.

## Acceptance criteria

- One valid synthetic 7→8 transition is accepted and durably recorded.
- A second distinct request attempting 7→8 is rejected as stale.
- Exact retry returns byte-identical receipt and signature without appending a second record.
- A post-commit process crash is recoverable from the journal.
- Concurrent distinct requests for the same epoch yield exactly one winner.
- Tampered journal data is rejected.
- The receipt does not overclaim TPM evidence provenance.

See RESEARCH_RECORD.md for exact source, tests, and CI evidence.


## Exact regression reproduction

The dedicated CI also extracts and runs the exact embedded gate from R22.30. It demonstrates that two different nonces can both obtain an epoch-8 approval from the same unchanged epoch-7 anchor. The final run passed all 8 tests (7 prototype controls plus this exact-source reproduction): https://github.com/SepehrGhanbari/Ario/actions/runs/45848502455.
