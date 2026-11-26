# R63 failure-domain-aware quorum model

**RESEARCH_ONLY / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION**

This is a policy model, not a cryptographic witness implementation. It consumes receipts only after an external verifier has already validated signatures, freshness, durable persistence, continuity, and readback. Boolean flags in the tests are synthetic; they do not prove those properties in a real service.

## Why this step

A witness quorum must count independent control domains, not merely distinct public keys. The published Sigsum test policy explicitly groups three witnesses run by Glasklar employees into one group and requires a 4-of-6 policy. More importantly, Sigsum's own explanation of \`sigsum-generic-2025-1\` states that Glasklar Teknik, Mullvad VPN, and Tillitis are separate companies but share the same parent company and are therefore dependent in some ways. Treat these three companies as one corporate failure domain for R63.

This is not a criticism of Sigsum's generic policy; it is a stricter requirement for Ario's custody threat model.

## R63 rule

For each receipt, the pinned roster records four independently evidenced failure-domain labels:
- operator / corporate group
- administrative control
- key custody
- state / backup administration

A receipt is eligible only if the policy hash, proposal hash, exact sequence, key, signature, freshness, durability, continuity and (for reads) readback checks pass. At least three witnesses and at least three distinct labels in every required failure-domain class are required. Unknown/unresolved labels fail closed. Multiple keys under one organization, parent group, administrator, key custodian or backup controller do not create independent votes.

Read/write quorum intersection must satisfy \`read_q + write_q > n + f\`, where \`n\` is the number of independent operator domains and \`f\` is the maximum number of faulty domains tolerated. For n=4, read=write=3, f=1, minimum intersection is 2 > 1. This arithmetic is only meaningful if the roster's failure-domain labels are accurate and pinned outside the control of the witnesses.

## Evidence mapping (not an admitted roster)

- \`poc.sigsum.org/nisse\`, \`rgdd.se/poc-witness\`, and \`witness1.smartit.nu/witness1\` are explicitly grouped as one Glasklar employee group in the published \`SIGSUM_TEST_2025_3\` policy. They must not be counted as three independent administrative votes.
- \`Glasklar Teknik AB\`, \`Mullvad VPN AB\`, and \`Tillitis AB\` are described by Glasklar as sister companies. Tillitis' official FAQ says Tillitis is wholly owned by Amagicom AB and a spin-off from its sister company Mullvad VPN. Sigsum's named-policy article explicitly notes that the three witnesses in \`sigsum-generic-2025-1\` have the same parent company and are dependent in some ways. For R63, these are one corporate domain, not three independent votes.
- The public \`SIGSUM_TEST_2025_3\` policy has a top-level 4-of-6 quorum with the Glasklar employee group as one unit alongside Geomys, Florian Larysch, Mullvad and Tillitis. This is an explicit precedent for grouped counting.
- The public \`SIGSUM_GENERIC_2025_1\` production policy uses a 2-of-3 threshold over Glasklar, Mullvad and Tillitis, but its own explanatory note warns that they share one parent. This threshold must not be misread as 2-of-3 independent parent-company domains.
- The public Witness Network currently lists Production as unavailable and Staging as work-in-progress. No R63 operator is admitted by this model.

## Limitations

The test harness is synthetic. It does not cryptographically verify Ed25519/ML-DSA, authenticate operator identity, inspect cloud-account control planes, validate HSM/backup boundaries, test physical restore, or establish any real operator's willingness. Failure-domain labels must be verified from primary operator evidence and pinned by an independent policy custodian. A common administrator who can alter the roster or its evidence defeats this model. No witness was contacted or configured and no log entry was published.

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
