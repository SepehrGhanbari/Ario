# W1 / R9 — Bounded capture completeness and independent witness architecture

**Date:** 2026-11-16. **State:** `RESEARCH_CRITIQUE / NO_INDEPENDENT_CAPTURE_ORACLE / HOLD`.
**Consensus Pro original report:** https://consensus.app/search/ario-w1-r9-second-independent-scholarly-review-wit/lWuPbcBpS9-YZwEI-netiQ/

This file is an **Ario-authored digest**, not a republication of the Consensus answer. Provider synthesis is not an independent referee, and the published papers do not certify the Ario design.

## Narrow research result

A hash-linked record or Merkle-root consensus can verify consistency *of the committed log* under its cryptographic/trust assumptions. It cannot by itself verify completeness of events never recorded, completeness of organization/controller ancestry, distinctness of human/organizational operators, or admissibility of AI evidence.

Five separate claims MUST remain disjoint:

1. **Byte consistency**: presented bytes match their committed digest.
2. **Log inclusion/append-only consistency**: captured entries are included; equivocation may be detectable with separately exposed views/gossip.
3. **Declared capture completeness**: events in a *specified observation scope* were actually captured; depends on independently auditable instrumentation/coverage assumptions.
4. **World-controller independence**: no hidden shared controller or derivation across supposed witnesses; requires genuine external information beyond the same modeled graph.
5. **Epistemic/operational authority**: admitting a claim or executing effects; no result above grants it.

## Source anchor audit

Four primary sources rechecked beyond Consensus provider snippets against public scholarly/author pages:

- [Douceur (2002), *The Sybil Attack*](https://www.microsoft.com/en-us/research/publication/the-sybil-attack/), [DOI 10.1007/3-540-45748-8_24](https://doi.org/10.1007/3-540-45748-8_24): multiple identities under one controller do not yield redundancy or trust domain independence. **No provenance inventory completeness primitive.**
- [Chuat et al. (2015), *Efficient Gossip Protocols for Verifying the Consistency of Certificate Logs*](https://doi.org/10.1109/CNS.2015.7346853): detects incompatible split-world views when non-colluding parties actually exchange/check commitments. **No guarantee of capture of arbitrary events outside log scope.**
- [Dowling et al. (2016), *Secure Logging Schemes and Certificate Transparency*](https://doi.org/10.1007/978-3-319-45741-3_8): formalizes bounded cryptographic logging properties and adversarial logs. **Cannot establish true real-world provenance or controller diversity.**
- [Dong, Berti-Équille & Srivastava (2009), *Integrating Conflicting Data: The Role of Source Dependence*](https://doi.org/10.14778/1687627.1687690): Bayesian dependence estimation from values. **Not a witness-key identity or attested custody proof.**
- [Bauer, Leucker & Schallhart (2011), *Runtime Verification for LTL and TLTL*](https://doi.org/10.1145/2000799.2000800): formal inconclusive semantics on partial traces. **Not a provenance authentication tool.**

The second Consensus output also mentioned Oxford et al. 2020 on CT gossip, Newsome et al. 2004 on sensor Sybil, Treitz & Künnemann 2026 preprint on CT accountability, and two unrelated ML/probabilistic sources. **Review these separately before using their specific claims**; a Citation or an arXiv DOI is not peer-review. In particular the provider's statement that a threshold co-signing protocol can be derived from *dependent randomization in decentralized detection* is **not adequately justified** and is marked `REJECT_ANALOGY_AS_PROOF`.

## Ario-specific comparison of architectures

| Design | What independently exists? | Legitimate finding | Fatal limitation / counterexample |
| --- | --- | --- | --- |
| A. Two processes/keys on the founder's same-user host | Process or symbolic key separation only | Lab repeatability and process fault tests | Same host administrator can modify both source and purported witness → `UNKNOWN` for independently held custody |
| B. External controller plus separately managed key, storage and authenticated receipts | One **additional** failure/custody domain, if assumptions empirically verified | Evidence of cross-domain commitment disagreement or matching logged commitments | Omissions pre-capture are still not detected. Operator may collude or lose key. Absence of disagreement is not proof of truth |
| C. Multiple independently operated append-only auditors with publicly compared heads | Multiple potential independently reachable observations | Bounded detection of split-view, subset consistency or rollback after prior cross-domain commitments | The same source can lie to all auditors; all sign the same incomplete log. Lack of honest reachable auditor causes `UNKNOWN`, not `TRUE` |

**Important correction:** multiple nodes or witnessed hashes, even 100 witnesses, do not make underlying world capture complete. A threshold only helps a *defined predicate* when enough witnesses really have separate identities/keys and a sound signing/checking protocol. Same-user laptop/desktop/phones are valuable failure test nodes, not independently authenticated human custodians. Distinguish operator diversity from online service count.

## Proposed bounded synthetic experiments: ADOPT/TEST/HOLD

1. **Negative control A — same host process:** common OS administrator rewrites source and log; expect no world-independent custody finding. `ADOPT for lab`.
2. **A/B external witness:** freeze digest of **the same scoped source event set** in two custody domains and compare both positive and intentionally contradictory commitments; detect contradiction, measure false acceptance and reachability. `TEST`.
3. **Network partition / split view:** show two valid-looking append-only branches to different auditors, then attempt reconnection and gossip. A trace with zero independently reachable honest clients must be marked `UNKNOWN`. `TEST`.
4. **Suppressed source event:** create an event outside the capture instrumentation while all receipts/checksums match. Explicitly demonstrate that log integrity can be green while world-event completeness remains `UNKNOWN`. `TEST`.
5. **Sybil witness inflation:** multiple apparent witnesses backed by one signing/custody root; measure whether a claimed independence gate ever promotes identity count to controller separation. `TEST`.
6. **Signatures consistent, root compromised:** forged-signing capability in a disposable sandbox and consistent local hashes; source authenticity remains not established without external prior commitment. `TEST`.

**Do not build real signing keys, alter Windows host privileges, enable trust or attach test results to Ario's live memory.**

## Recommendation

**ADOPT:** Source-count is not independence; independent external prior commitments and `UNKNOWN` are necessary methodological requirements; keep capture completeness separate from witness agreement.

**TEST:** Three architectures with explicit adversary capabilities; use an independent-held gold challenge and record per-step signed/verified receipt semantics, not only green CI.

**HOLD:** Claims that this architecture establishes unalterable truth, externally complete capture or production-safe human/Ario approval. Independent real-world custody is still **NOT ESTABLISHED**.

**Links:** [W1 blind protocol](W1_BLIND_INDEPENDENT_CHALLENGE_PROTOCOL_V0_1.md), [initial development rehearsal](W1_REHEARSAL_RESULTS_2026-11-16.md). **PR #199 H_E/H_S custody semantics remain separate** from W1-B omitted-source testing.

No primary result beyond the above cited publications is claimed. The provider's full 27k-character report is retained in the user's Consensus account, not mirrored here.
