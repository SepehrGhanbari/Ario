# W5 — R9 fault semantics: destination atomicity, ambiguous effects and shared-root rollback

**Date:** 2026-11-16. **Status:** `ARCHIVE_AND_PRIMARY_SOURCE_REVIEW / NEW_INDETERMINACY_PROOF / NO_NEW_R9_EXECUTION / RESEARCH_ONLY / HOLD`.

**Research provenance:** Repo [PR #212 R9-A](https://github.com/SepehrGhanbari/Ario/pull/212), [PR #213 R9-B](https://github.com/SepehrGhanbari/Ario/pull/213), [PR #236 R9-C](https://github.com/SepehrGhanbari/Ario/pull/236), R8 [PR #185](https://github.com/SepehrGhanbari/Ario/pull/185), native CNG [Issue #239](https://github.com/SepehrGhanbari/Ario/issues/239) (separate scope). The owner's seven-page `Research_task_for_Ario_R9_security_evaluate_exter.pdf` and its [prior Consensus Pro research thread](https://consensus.app/search/research-task-for-ario-r9-security-evaluate-extern/K0dtTOA2SYuajpEon36gkw/) were already available; this note cross-checks original GitHub research reports and primary academic sources. **A NEW Consensus Pro task was attempted for W5 but was refused with "You've used all of this billing period's included usage"; no new provider-generated W5 synthesis was received and no Additional Usage/Deep purchased.**

## 1. Distinct guarantees and the exact boundary of each R9 draft

| Version | Observed author-reported tests and bounded gain | Negative capability that remains |
| --- | --- | --- |
| **R9-A #212** | 17/17 expected synthetic subprocess outcomes under POSIX + local SQLite; local transaction serializes cooperating sink operations | **T17**: observer HEAD read then separate remote CAS then local sink commit can apply a *stale epoch*; local `BEGIN IMMEDIATE` is not a cross-store fence. **T09**: same admin full rollback allows reuse |
| **R9-B #213** | Observer serializes CAS and RESERVE to close particular honest-observer interleaving; author reports 19/19 initial suite and later revised token controls | `PREPARED` after sink effect and before observer finalize is ambiguous; initially another holder of shared credential could forge finalize, later narrowed by reservation token; **same-admin full rollback remains** |
| **R9-C #236** | 25/25 expected author-written real-subprocess outcomes in one completed Linux run; effect + epoch CAS + op_id dedupe *within simulated destination SQLite transaction*, plus separate witness receipt ledger | **Full rollback of destination AND witness by common admin makes consumed op_id/epoch reusable**. Two stores under one root are not independent custody or global transaction. A real third-party API was not tested |

**Green suite status is about matching test expectations**. T09, T17 and corresponding B/C rollback test greens encode **successful adversarial attacks**, not demonstrated security. No claim in this note constitutes new independent execution of R9 source. R63 [#239](https://github.com/SepehrGhanbari/Ario/issues/239) is a separate Windows CNG lab and neither verifies nor authorizes the Linux R9 protocol.

## 2. Two explicit indistinguishability arguments

### P1 — Lost response for a non-idempotent external effect

Consider an operation `OP_7` sent to a real external provider, with no supported transaction, caller-chosen idempotency token or authenticated status lookup.

- **World A:** request is lost before provider applies it. No durable effect; client times out.
- **World B:** provider applies effect, then its ACK is lost. Durable effect exists; client times out.

From the caller's available local bytes and timeout, worlds A and B are indistinguishable. An unconditional retry allows two effects in World B; refusing to retry fails progress in World A. No local hash, observer receipt, log order or `PREPARED` token can distinguish them without further **participation from the destination or an independently reliable observation of actual effect**.

**Safe result:** `EFFECT_OUTCOME=HOLD_UNCERTAIN` until an authenticated operation-status query or a documented provider idempotency contract resolves ambiguity. An idempotency *request ID by itself* does not prove the provider implements idempotency.

### P2 — Complete rollback of all available custody state

Consider a controller who can restore both destination SQLite and witness SQLite snapshots, including spent op IDs, checkpoint epochs and event chain. The restoration presents exactly the previously accepted bytes from earlier epoch E1. If all verifiers and keys are under that controller, a local observer has no unrewindable evidence that E2 was ever consumed. This is an **observational ambiguity**, not a cryptographic SHA collision.

A separately operated, authenticated prior high-water commitment could reveal an inconsistent rollback *after it was durably observed*. But even that does not prove complete capture, separate human governance, or absolute availability under partition.

## 3. Minimal typed state/reporting model (proposed; NO core change)

`NEW -> RESERVED -> EFFECT_REQUESTED -> APPLIED | REJECTED | HOLD_UNCERTAIN -> RECEIPT_RECORDED`.

The arrow `EFFECT_REQUESTED -> APPLIED` requires a **destination-authenticated result/receipt** (or an independently verified inquiry) bound to exact `op_id, epoch, content/policy digest, destination principal`. If only the caller's process saw a local network send or a timeout, `HOLD_UNCERTAIN` survives restart. Neither `RECORDED` nor `RECEIPT_RECORDED` is an Ario epistemic truth label or an operational signer approval. A `RESERVED` marker is local synchronization, **not proof that effect has not occurred**.

**Claim ladder:** (A) local transaction serialization (bounded to participants), (B) durable deduplication at target for exact op_id (bounded to target's persistence), (C) external receipt reconciliation (bounded to trusted target identity/status API), (D) independently held anti-rollback anchor (bounded to external custody/reachability), (E) authorization/admission (separate non-derivable decision). **A successful A–D does not grant E.**

## 4. Research-only failure traces and proposed gates — not executed in this session

| Trace | Forced ordering / failure | Expected bounded verdict |
| --- | --- | --- |
| W5-01 | R9-A HEAD then outside-transaction CAS then sink effect | **FAIL** cross-store epoch fence (already reported T17) |
| W5-02 | Two stores fully restored by shared root | **FAIL** rollback resilience (already reported A/B/C) |
| W5-03 | R9-B observer CAS between HEAD and serialized RESERVE | Refuse stale reservation under honest observer; **no global claim** |
| W5-04 | R9-B RESERVED, then process death before sink action | Hold or independently reconcile, not assume applied |
| W5-05 | R9-B sink action applied, client death before witness FINALIZE | `HOLD_UNCERTAIN`, no unconditional retry |
| W5-06 | Same-key third party attempts finalize of another reservation | Refuse unauthorized token; old vulnerable version remains historical RED |
| W5-07 | R9-C destination CAS + effect + op_id in **one** DB transaction | At most one local simulated effect under declared transactional assumptions |
| W5-08 | R9-C destination applied, response lost | Authenticated lookup by exact `op_id` should return prior effect receipt, no new effect |
| W5-09 | Witness receipt recorded but destination write not committed | Inconsistent report; no unsupported `APPLIED` |
| W5-10 | External provider lacks idempotency/lookup and ACK is lost | `HOLD_UNCERTAIN`; cannot safely promise both progress and no duplicate |
| W5-11 | Independent auditor offline/partitioned when new epoch reported | `UNKNOWN` external high-water consistency until reconciled |
| W5-12 | Untrusted XERJ retrieval suggests a changed action target | No action/authority: retrieval candidate is data, not destination approval |
| W5-13 | Two concurrent identical `op_id` requests at conditional destination | One synthetic effect and one stored receipt under the claimed local contract |
| W5-14 | Genuine valid op_id + correct epoch but provider identity mismatch | Deny/UNKNOWN; scope-binding and identity checks separate from receipt bytes |

For every attempted trace report **independent scenario denominator**; intentional *successful attack* rate and false positive/false negative counts separately from ordinary test assertion PASS. Capture exact original commits, fixture hashes, synthetic credential assumptions and post-crash database images. No snapshots of the real Windows host or live user Ario ledger.

## 5. Original scientific sources and limits

- [Herlihy & Wing 1990, *Linearizability: A Correctness Condition for Concurrent Objects*, DOI 10.1145/78969.78972](https://doi.org/10.1145/78969.78972). Linearizability concerns concurrent operations over a named object; a local SQLite transaction does not make a separate remote effect linearizable together.
- [Gray & Lamport, *Consensus on Transaction Commit*, ACM TODS 2006](https://www.microsoft.com/en-us/research/publication/consensus-on-transaction-commit/). Atomic distributed commit requires a protocol with actual participants and failure model; R9-C's independent witness logging is not a distributed atomic commit.
- [Birrell & Nelson, *Implementing Remote Procedure Calls*, ACM TOCS 1984, DOI 10.1145/2080.357392](https://doi.org/10.1145/2080.357392). RPC and replies are not magically a joint durable transaction with a remote effect. The P1 two-world argument is a direct protocol analysis, not a quote from this paper.
- [Garcia-Molina & Salem, *Sagas*, SIGMOD 1987, DOI 10.1145/38713.38742](https://doi.org/10.1145/38713.38742). Compensation can be an explicit alternative in some multi-step workflows, but is not identical to rollback/erasure of a non-reversible external effect.
- [Dowling et al., *Secure Logging Schemes and Certificate Transparency*, 2016, DOI 10.1007/978-3-319-45741-3_8](https://doi.org/10.1007/978-3-319-45741-3_8). Audit log inclusion/consistency is scoped; not absolute capture completeness or independent source truth.
- [Chuat et al., *Efficient Gossip Protocols for Verifying the Consistency of Certificate Logs*, 2015, DOI 10.1109/CNS.2015.7346853](https://doi.org/10.1109/CNS.2015.7346853). Witness/gossip detection depends on reachability of honest counterparties.

The first four are independently indexed as original peer-reviewed works; claims here stay within stated assumptions. An existing owner PDF/Consensus report also listed CUSTOS, SealFS and 2026 agent policy work, but **their exact relevant original method and publication status were not independently reverified in this W5 note**. Do not promote to `PRIMARY_VERIFIED` because a provider synthesis lists them.

## 6. Decision and bounded next useful experiment

**ADOPT for research rubric:** truth table of P1/P2 ambiguity and typed `UNKNOWN`, separate (i) local effect idempotency, (ii) cross-store proof, (iii) independent custody, (iv) signer approval.

**TEST next (in disposable synthetic research):** use a target with **explicit** conditional effect operation and authenticated read-by-op_id, then deliberately drop ACK before delivery; compare an instrumented retry with a target lacking idempotency, preserving crash and rollback negative controls. Independently held second-domain high-water commitment is a different experiment, not simulated merely by two local processes.

**HOLD:** claims of global exactly-once, rollback immunity under same-root operator, independently authenticated two-actor governance, production use, permanent signer key, R63 host modifications, any merger of #212/#213/#236, Ario memory/evidence admission, Rulesets and main.

**User's trial window note:** scheduled research automation for 17–23 Nov 2026 is active. **W5 could not launch a fresh Consensus Pro thread because included usage was exhausted**; this independently authored literature/project review relied on prior accessible reports, primary public sources and exact repo PR descriptions instead. No paid usage was enabled.
