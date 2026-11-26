# R63 failure-domain-aware quorum model

**RESEARCH_ONLY / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION**

This is a policy model, not a cryptographic witness implementation. It consumes receipts only after an external verifier has already validated signatures, freshness, durable persistence, continuity, and readback. Boolean flags in the tests are synthetic; they do not prove those properties in a real service.

## Why this step

A witness quorum must count independent control domains, not merely distinct public keys. The published Sigsum test policy explicitly groups three witnesses run by Glasklar employees into one group and requires a 4-of-6 policy. More importantly, Sigsum's own explanation of `sigsum-generic-2025-1` states that Glasklar Teknik, Mullvad VPN, and Tillitis are separate companies but share the same parent company and are therefore dependent in some ways. Treat these three companies as one corporate failure domain for R63.

This is not a criticism of Sigsum's generic policy; it is a stricter requirement for Ario's custody threat model.

## R63 rule

For each receipt, the pinned roster records four independently evidenced failure-domain labels:
- operator / corporate group
- administrative control
- key custody
- state / backup administration

A receipt is eligible only if the policy hash, proposal hash, exact sequence, key, signature, freshness, durability, continuity and (for reads) readback checks pass. At least three witnesses and at least three distinct labels in every required failure-domain class are required. Unknown/unresolved labels fail closed. Multiple keys under one organization, parent group, administrator, key custodian or backup controller do not create independent votes.

Read/write quorum intersection must satisfy `read_q + write_q > n_class + f` **separately for every critical failure-domain class**, where `n_class` is the number of distinct labels in that class and `f` is the maximum number of faulty domains tolerated. The receipt gate also requires the selected read/write quorum count in every class, not just distinct keys or operator names. For n_class=4, read=write=3, f=1, minimum intersection is 2 > 1. If one class has only two independent domains, the policy fails closed. This arithmetic is only meaningful if the roster's failure-domain labels are accurate and pinned outside the control of the witnesses.

## Evidence mapping (not an admitted roster)

- `poc.sigsum.org/nisse`, `rgdd.se/poc-witness`, and `witness1.smartit.nu/witness1` are explicitly grouped as one Glasklar employee group in the published `SIGSUM_TEST_2025_3` policy. They must not be counted as three independent administrative votes.
- `Glasklar Teknik AB`, `Mullvad VPN AB`, and `Tillitis AB` are described by Glasklar as sister companies. Tillitis' official FAQ says Tillitis is wholly owned by Amagicom AB and a spin-off from its sister company Mullvad VPN. Sigsum's named-policy article explicitly notes that the three witnesses in `sigsum-generic-2025-1` have the same parent company and are dependent in some ways. For R63, these are one corporate domain, not three independent votes.
- The public `SIGSUM_TEST_2025_3` policy has a top-level 4-of-6 quorum with the Glasklar employee group as one unit alongside Geomys, Florian Larysch, Mullvad and Tillitis. This is an explicit precedent for grouped counting.
- The public `SIGSUM_GENERIC_2025_1` production policy uses a 2-of-3 threshold over Glasklar, Mullvad and Tillitis, but its own explanatory note warns that they share one parent. This threshold must not be misread as 2-of-3 independent parent-company domains.
- The public Witness Network currently lists Production as unavailable and Staging as work-in-progress. No R63 operator is admitted by this model.

## Markovian rollback-floor review (2026-11-26)

Markovian's witness documentation describes an unusually relevant recovery design: it writes each per-log high-water mark hourly into its own public transparency log; that log is cosigned by a pinned 4-of-7 external witness policy and timestamped into Bitcoin. On startup it reads the latest qualifying floor, checks inclusion, and retains the higher of the restored and published marks. An empty local database is refused. For logs it can fetch, it also checks their current state; push-only logs retain up to a one-hour recovery gap. The operator explicitly notes that full control of its own server can still edit local files, so the external evidence is what makes rollback detectable.

The current 4-of-7 policy has seven witness keys but, under the conservative R63 corporate grouping, four domains: AMAGICOM (Stagemole/Mullvad, RGDD, SmartIT), Google TrustFabric (two witnesses), Geomys, and Remora. Weighted analysis shows:
- minimum corporate domains in any four-key quorum: **2**
- minimum corporate-domain intersection between two four-key quorums: **1**

Therefore this is a potentially useful recovery-floor design, but its current 4-of-7 policy does **not** meet R63's stricter requirement for an intersection greater than one independently controlled domain. A 4-of-7 key threshold is not automatically a 4-domain threshold. We have asked the operator whether a test and a more domain-diverse policy are feasible; no enrollment or log publication has occurred.

The public checkpoint was fetched read-only at tree size 14904. The anchor endpoint reported latest stamped size 14903 pending and confirmed size 14899 in Bitcoin block 977669; the endpoint reported 2686 confirmed header checks and zero mismatches at fetch time. These values are a dated observation, not a permanent status claim.

### Source-verification gap

The live `witness.markovianprotocol.com/about` page describes the hourly floor recovery, but the current public `MarkovianProtocol/log-server` `main` source does not contain that mechanism in `witness_server.py` or `witness_poller.py`. `witness_server.py` implements the C2SP per-log monotonic cosign path and commits its SQLite row before returning a cosignature; `witness_poller.py` explicitly does not write witness state. The `witness_server.py` self-test uses an in-memory SQLite database and does not test restart, disk loss, or restoration from the external floor. `log_server.py` implements Bitcoin anchoring for the log's own checkpoints, which is not by itself the witness-state recovery component. The live page also says the service is best-effort and its state may be rolled back.

Therefore the external-floor behavior is a live operational claim, **not yet source-verified against the published repository**. We asked the operator for the exact deployed commit or separate component and an offline verification path. Until that is supplied, treat the recovery mechanism as UNVERIFIED_IMPLEMENTATION and do not admit the service as an R63 custodian.

## Limitations

The test harness is synthetic. It does not cryptographically verify Ed25519/ML-DSA, authenticate operator identity, inspect cloud-account control planes, validate HSM/backup boundaries, test physical restore, or establish any real operator's willingness. Failure-domain labels must be verified from primary operator evidence and pinned by an independent policy custodian. A common administrator who can alter the roster or its evidence defeats this model. A research inquiry was sent to Markovian; no witness was configured or authorized to sign an Ario log, and no Ario log entry was published.

Next: obtain written operator answers, document independently controlled failure domains, then run only an operator-authorized low-volume synthetic test. If fewer than three distinct admin/key-custody/state-backup domains can be evidenced, HOLD.

## Primary sources

- https://witness-network.org/witness-tables/
- https://docs.rs/sigsum/latest/sigsum/policy/static.SIGSUM_TEST_2025_3.html
- https://www.glasklarteknik.se/post/named-policies-for-sigsum/
- https://www.glasklarteknik.se/about/
- https://www.tillitis.se/faq/
- https://ipng.ch/s/ct/
- https://remora.n621.de/
- https://c2sp.org/tlog-policy

- https://markovianprotocol.com/get-witnessed.html
- https://markovianprotocol.com/witness-policy.html
- https://log.markovianprotocol.com/policy
- https://log.markovianprotocol.com/checkpoint
- https://log.markovianprotocol.com/anchor
