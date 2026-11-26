# R63 external operator admission review — 2026-11-26

RESEARCH_ONLY / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE / GENESIS NO_GO.

Continuation of #369 and EXTERNAL_CUSTODY_BOUNDARY_20261126.md at 4fa8fbafc641d0450ccd212778fade78c568313e. Read-only public research; no new publication, key, enrollment, fault injection, or trust-policy modification.

## Actual read-only observations

The public testing list https://testing.witness-network.org/log-list.1 contains the exact Barreleye origin sigsum.org/v1/tree/4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d. The fetched staging 10qps list https://staging.witness-network.org/log-list-10qps-4klogs.1 did not contain it. This does not rule out manual configuration. Google TrustFabric staging and dev candidate C2SP monitoring URLs redirected to public informational pages, not signed checkpoints. IPng public uptime monitor https://juf.ct.ipng.ch/ reports Kladje and Krabbel service probes; these are not direct readback of this log or evidence of durable state. Do not count them as additional direct witnesses. GDB follows the staging 10qps list, explaining a plausible reason for the earlier 404, not a verified diagnosis. The Witness Network table still lists no production tier.

## Admission evidence by administrative operator (not by number of keys)

| Operator | Documented evidence | Decision for R63 continuity role |
|---|---|---|
| SmartIT / Elias Rudberg | Explicitly anticipates resets of saved log state while retaining software key | REJECT_CURRENT_PROFILE |
| RGDD | Test database sometimes reset, losing previous states | REJECT_CURRENT_PROFILE |
| Mullvad Stagemole | Best effort, state can be rolled back | REJECT_CURRENT_PROFILE |
| Google TrustFabric Dev | Can reset or rotate keys without warning | REJECT_CURRENT_PROFILE |
| Google TrustFabric Staging | Best effort; resets/key rotation not ruled out; distinct state/key services reported but shared administration | HOLD_OPERATOR_POLICY |
| IPng Networks | Published support through 2029-12-21, annual key rollover; testing and staging count as one operator | HOLD_OPERATOR_POLICY |
| Geomys | Direct signed checkpoint verified earlier; staging, software keys | HOLD_OPERATOR_POLICY |
| Markovian | Direct signed checkpoint verified earlier; history endpoint exists; no independent reset/retirement assurance | HOLD_OPERATOR_POLICY |
| GDB Security | Operator describes push-only dependency for logs it does not poll; direct readback for this origin not established | HOLD_DIRECT_READ |
| archive.rip | Test-only service; direct readback not established | HOLD_DIRECT_READ |

REJECT_CURRENT_PROFILE means incompatible with the proposed R63 continuity requirement as documented; not a claim of misbehavior or rejection of the existing Sigsum TEST verification policy. No operator admitted. A new profile could be separately reviewed after operator agreement. Different names/keys/providers do not prove independence. No direct freshness challenge, protected monotonic state, or per-proposal durable R63 receipt observed. Direct read-only witnesses established earlier: 2; independent R63 write/read custodians enrolled: 0.

## Next actionable operator inquiry

Prepared an unsent targeted inquiry to IPng public CT operations contact about the documented direct checkpoint endpoint, identity retirement after state loss or rollback, authenticated read freshness, key rollover and feasibility of a low-volume no-cost synthetic test. No secrets or raw records in the inquiry. Await user approval to send; no duplicate mailing-list request. Earlier Witness Network inquiry remains pending moderation based on mailbox search, not an acceptance or refusal.

## Primary public sources

- https://witness-network.org/witness-tables/
- https://witness-network.org/participate/
- https://witness1.smartit.nu/witness1/about.txt
- https://www.rgdd.se/poc-witness/about
- https://witness.stagemole.eu/about
- https://transparency.dev/witnesses/
- https://ipng.ch/s/ct/
- https://geomys.org/witness/navigli
- https://witness.markovianprotocol.com/about
- https://witness.gdbsecurity.com/about
- https://wit26n0.testing.archive.rip/about.txt

Decision HOLD_EXTERNAL_CUSTODY_NOT_ESTABLISHED. Required before advancement: explicit operator agreement, independent management evidence, state-loss/key-retirement policy, fresh authenticated read, authorized durability/reset test, and 3-of-4 R63-specific durable receipt integration. Do not substitute more same-administrator databases, generic C2SP signatures, uptime, or key counts for these requirements.
