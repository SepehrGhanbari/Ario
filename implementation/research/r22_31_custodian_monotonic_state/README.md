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
- Byte-level record tampering and an incomplete final record are rejected.
- Complete-tail deletion / rollback to a valid earlier prefix is reproduced as an expected RED; this local prototype does not prevent it.
- The receipt does not overclaim TPM evidence provenance.

See RESEARCH_RECORD.md for exact source, tests, and CI evidence.


## Exact regression reproduction

The dedicated CI also extracts and runs the exact embedded gate from R22.30. It demonstrates that two different nonces can both obtain an epoch-8 approval from the same unchanged epoch-7 anchor. The earlier path-alias run [45853154583](https://github.com/SepehrGhanbari/Ario/actions/runs/45853154583) passed 12/12 tests. The latest strict-ledger run [45854444069](https://github.com/SepehrGhanbari/Ario/actions/runs/45854444069) passed **18/18 tests** on CPython 3.13.18 / OpenSSL 3.0.13. It includes the exact-source R22.30 reproduction, expected-RED valid-prefix rollback reproduction, path-alias regressions, and strict JSON/canonicalization/type regressions. Expected-RED tests pass by reproducing documented weaknesses, not by preventing them.


## Strict JSON ledger parsing — 2026-11-26

A source audit found that Python's default JSON decoder silently accepts duplicate object keys. The journal loader also validated a record hash over the decoded dictionary without requiring the stored JSONL line itself to be canonical. This creates parser ambiguity across implementations even when the decoded dictionary appears valid.

The research prototype now:
- rejects duplicate JSON keys at every nesting level for signed anchors, requests and journal records;
- requires the signed anchor bytes to equal the canonical serialization of the decoded anchor;
- requires each journal record to be exactly one canonical JSON object followed by one newline;
- requires `sequence` to be an integer and explicitly rejects booleans and floats (Python otherwise treats `8.0 == 8` as true).

Six new regressions cover duplicate keys in anchor/request/journal, noncanonical signed anchors and journal records, and a float sequence whose record hash has been recomputed. The latter confirms the type check is not merely relying on the record hash.

Latest dedicated CI: [run 45854444069](https://github.com/SepehrGhanbari/Ario/actions/runs/45854444069), exact tested head `0229727e6b297a1fd13e598f79940c32c2524ca0`, **18/18 PASS** on CPython 3.13.18 / OpenSSL 3.0.13. Artifact `r22-31-custodian-monotonic-state-evidence`, ID `15135810639` (702 bytes).

This does not close same-domain journal rollback: a valid older prefix can still be restored without an independently retained authenticated floor. The prototype remains RESEARCH_ONLY; no external custodian, TPM attestation, real key, trust activation, production or merge is established.


## 2026-11-26 — owner-admin rollback threat-model disposition

**Disposition: ACCEPTED_RISK / OUT_OF_SCOPE under the owner's declared current operating model.**

The owner reports that they are the only trusted administrator of the Ario repository and its associated research environment. This is an owner-provided assumption, not an independently verified access-control inventory. Under that model, deliberate rewriting of every local state source by the same trusted owner is not treated as an adversarial security requirement. We will not create additional same-domain processes, files, mock custodians, or repeat the Sigsum test merely to simulate independence.

The expected-RED valid-prefix rollback test remains in the suite as an explicit boundary demonstration. It is not a blocker for the narrow R22.30 duplicate-epoch correction, and it is not evidence that the prototype resists a hostile administrator.

**Still NOT CLOSED:** compromise or theft of the owner's GitHub account, credentials, or execution device; compromise by another administrator not included in the declared model; and any deployment that requires resistance to a hostile owner. Those threats require a genuinely out-of-band owner-held floor or an independently administered custodian. They cannot be solved by another file or process under the same authority.

The existing R22.22I 2-of-4 external test-witness floor is not a floor for R22.31: its signed tree head predates this R22.31 state and does not commit to this journal or branch. Reusing it as though it did would be a false binding. No new Sigsum publication, witness test, external call, key, merge, trust activation, or production action was performed.

The R22.31 valid-prefix rollback finding is therefore **closed as an accepted scope limitation for the current owner-operated research prototype**, not as a cryptographic fix. The original same-epoch defect remains addressed by the R22.31 state-machine correction; PR #411 remains open/Draft pending its normal integration path.
