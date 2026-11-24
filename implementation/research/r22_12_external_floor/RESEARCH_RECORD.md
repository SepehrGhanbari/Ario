# R22.12 — external synthetic floor and ledger preimages

RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.

Parent #362 at bc9b34f4662975422e753d27e9aacec821d67293. Fresh experiment, not recovery of the specific old R22.11 floor. Publisher creates two synthetic event values containing independent random 256-bit nonces so recovery cannot derive the new ledger from the fixed fixture source. The old two-record prefix is retained. Existing R22.7 floor_record and R22.8 commitment are reused unchanged.

Publisher verifies two public Sigsum TEST proofs and publishes the second envelope via existing R22.11 relay transport. A second public Nostr event contains a canonical bundle of the exact floor JSON bytes and exact ledger JSONL bytes, indexed by the R22.8 domain-separated floor commitment. No actual Ario history or keys. The runner receives only old floor, old ledger, first envelope and bootstrap. It discovers the later signed checksum, retrieves the envelope, then uses only the floor commitment therein to retrieve the separate bundle. It verifies canonical bounded structure, existing retained-floor parser, old pinned commitment, new commitment, same scope, advancing sequence, exact parent checkpoint links, exact old ledger prefix, full ledger hash/count and R22.7 conditional correspondence. Existing R22.7 parser has bounded lab counts 2 and 4; no general runtime support. A separate reveal job compares exact new bytes with withheld originals. Old state hashes must remain unchanged.

16 new authored unit controls include missing content, replay, substitution, same-count fork, recommitted wrong prefix, wrong scope, wrong count, tampered transport, duplicate fields and malformed bundle. No PASS until actual run logs are checked.

Boundary: two external relay endpoints are not demonstrated independent administrative custodians. The floor and ledger are synthetic and witness identity/authenticity is not established. Global latest, permanent availability, independently protected latest pointer, full physical rollback, persistent key enrollment, event completeness and event truth are not established. Recovering data is not authorizing its adoption. No real keys, merge, trust activation, production or evidence admission.

## Verified live observation (2026-11-24)

[Run 45459689925](https://github.com/SepehrGhanbari/Ario/actions/runs/45459689925), exact source/workflow HEAD 5e861f6c465d626740cd919f0de512bf6813e80a: all three jobs SUCCESS. Job logs read directly.

- Publish 138678543752: fresh random synthetic event values generated; two official Sigsum TEST proofs verified; both fixed Nostr relay endpoints accepted the second envelope and the 6868-byte separate floor+ledger bundle.
- Discover 138679311463: 16 inherited Python envelope controls and 16 new floor controls passed. Existing Go scan verified sampled cosigned tree size 281592, root b97c1a479995d391b63f504537d3b6ead07d919b2218f5d4cebe8acf9e87007b, consistency PASS, first index 281590 checksum 00d79ee0bb823184a48463ac432e8e8c24f42f6d4b49ad50b2ffb00d6b4644b6; second index 281591 checksum f65228cb44ea900d6d78e6465967b5ec0b4d3894946c801acb678053200c908f. Same-key opaque commitment discovered without later preimage. Envelope recovered from both relays; then separate bundle recovered from both by committed floor digest e8877d476cd1fbaf4165636b865a225704994f401cdccf1cbafd1cc909acaedc. Exact old prefix, scope, advancing sequence, predecessor checkpoints and ledger correspondence validated. Recovered ledger SHA256 e78f44fb5fd8dca2b8a3c0066cb1eceecbddae256e4b1d3666c00a2d02222085. RECOVERED_LINKED_SYNTHETIC_FLOOR_AND_LEDGER_ONLY; verified record count 4, both preimages recovered; old local-state.json, floor.json and ledger.jsonl checksums unchanged.
- Reveal 138679755085: exact recovered floor and ledger bytes matched withheld originals and old prefix; R22_12_EXTERNAL_FLOOR_AND_LEDGER_MATCH_WITHHELD_BYTES. Exact envelope and index also matched. No admission, trust activation or merge.

Artifact IDs and digests from GitHub API and job logs (ZIPs not independently downloaded or rehashed here). Retention expires 2026-12-24.

| Artifact | ID | SHA256 | Bytes |
|---|---:|---|---:|
| FIRST-ONLY | 14951747944 | 22f79e186ff93a3fe2b00e58af5ff3870baf0aad954cac1de883dbfb91cf5422 | 5110 |
| SECOND-REVEAL | 14952710960 | 5ad28bffae50600ddba9363a82a75f1a4d3b1ef748ea1f1ddee5cf3b24f62549 | 5069 |
| EXTERNAL-RECOVERED | 14951792869 | 943151fe5a4765819d37c6015c49fc6153b01624895f9b7b4b0d8a5ceb2fa5be | 3139 |
| BLIND-DISCOVERY | 14951698138 | c01b7cc4f2b4f160b7c4162e97b0db4856b2bfae125c0524c3ecf50afa5ccad3 | 700 |

Narrow synthetic experiment PASS; research disposition HOLD. The two relays returned matching content in this observation; independent administration, durable retention, global latest, actual historical event truth, physical machine restore and authority remain unproved. Next candidate: delayed clean-room recovery after publisher exit using only first bootstrap plus old floor and ledger, with replayed/missing relay response and loss-of-source controls. Keep any recovered state separate from admitted memory; no automatic promotion.
