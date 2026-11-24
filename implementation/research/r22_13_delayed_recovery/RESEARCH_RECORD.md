# R22.13 — delayed clean-runner recovery and relay loss/replay controls

RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.

Parent #364 at 30714f282b63caf88cbfe1f76856ecfb89aa755f. No new publication. Reuse actual R22.12 TEST log and public synthetic relay objects from run 45459689925, prior publisher job 138678543752.

Stage job fetches only pinned FIRST-ONLY ZIP (14951747944), checks SHA256 and ZIP CRC, strips Git metadata and reports, and stages old bytes and Python/Go source only. It verifies that the known later envelope checksum, floor commitment and ledger digest do not appear in staged files. No later artifact is downloaded by stage or recovery. At least 120 seconds must have elapsed since publisher job completion. A separate hosted runner with empty declared repository-token permissions and no checkout receives only the first/source artifact; it verifies actual elapsed time and uses the unchanged bounded R22.10 live scanner. A separate reveal runner alone downloads the pinned original second ZIP (14952710960) after recovery and compares exact bytes.

Recovery makes two separate live retrieval attempts: one using only nos.lol, one using only relay.primal.net. Each must independently return the exact valid envelope and floor+ledger bundle. This is client-side source exclusion, not an outage at the relay itself. Recovery then uses deterministic injected WebSocket responses to test freshly signed/retagged old envelope and floor, missing new envelope and missing new floor. Direct old substitution also must fail. Old bytes verify as a historical prefix but never as the latest observed object. Old state files remain unchanged; recovered outputs stay separate. No actual deletion, network interference, or new public events.

Limits: same repository administration, hosted runner and workflow are trusted for experimental separation; no OS sandbox or adversarial operator isolation. Public repo could be independently queried by a malicious runner; this source-only staging establishes supplied-input separation, not an information-theoretic proof. Delay is wall-clock measured using hosted runner and GitHub job metadata; no independent clock proof. The scanner has a 64-leaf bounded suffix and fails closed on incomplete scan or other live failure. Injected loss/replay is not live external deletion. No proof of permanent retention, administrative independence, globally latest state, actual event truth or physical device restore. No evidence admission, keys, merge or activation.

Execution pending at authoring; record actual results separately.

## Verified live observation (2026-11-24)

[Run 45460832762](https://github.com/SepehrGhanbari/Ario/actions/runs/45460832762), exact source/workflow HEAD 877f5bdf546f7953ea2f59c425a7daa9e761a798: all three jobs SUCCESS. Job logs read directly. No republishing or new public events.

- Stage 138682618385: prior FIRST-ONLY ZIP SHA256 and CRC verified; source-only bundle excluded reports, Git metadata and known later digests; old input staged. Recover runner had no checkout and empty declared repository-token permissions.
- Recover 138682732832: elapsed 334.848 seconds since prior publisher completion at start of discovery; cosigned tree size 281592, root b97c1a479995d391b63f504537d3b6ead07d919b2218f5d4cebe8acf9e87007b, consistency PASS. Complete sampled suffix [281590,281592); later checksum f65228cb44ea900d6d78e6465967b5ec0b4d3894946c801acb678053200c908f rediscovered. Two separate live single-relay queries (nos.lol only, relay.primal.net only) each recovered the exact envelope and floor+ledger bundle. Floor commitment e8877d476cd1fbaf4165636b865a225704994f401cdccf1cbafd1cc909acaedc; ledger SHA256 e78f44fb5fd8dca2b8a3c0066cb1eceecbddae256e4b1d3666c00a2d02222085; count 4. Four injected transport cases (old retagged signed envelope, missing envelope, old retagged signed floor, missing floor) returned HOLD_CONTENT_UNAVAILABLE or HOLD_FLOOR_PREIMAGE_UNAVAILABLE as appropriate. Direct old substitution returned HOLD for both hash and floor commitment. Old bytes still valid as prefix; never promoted as latest; all five old input files unchanged. DELAYED_RECOVERY_AND_FAULT_CONTROLS_PASS.
- Reveal 138683145753: prior SECOND-REVEAL ZIP SHA256 and CRC verified; three recovered files matched original envelope, floor and ledger byte-for-byte; R22_13_DELAYED_RECOVERY_EXACT_ORIGINAL_MATCH.

New artifact metadata verified against GitHub API and job logs; new ZIPs not separately downloaded/rehashed here. Expiration 2026-12-24.

| Artifact | ID | SHA256 | Bytes |
|---|---:|---|---:|
| FIRST-ONLY-SOURCE | 14952906736 | 676f26d265e3c367571ebdac4df4c8c17b2080e1e139efd074fbaead41f0b760 | 510195 |
| RECOVERED | 14951259501 | 0c627d33ffa8fea08d64a5406f733002224879b863cf080d6950fdfdf890579f | 3944 |

Narrow delayed recovery and fault-control PASS; research HOLD. No actual external outage/deletion, no independently administered custody proof, no global freshness, permanent availability, physical restore or event truth. Next candidate: model stale cosigned head replay after recovery with a separately retained monotonic floor; then test a later independent publication and cold restart against that floor. Keep recovered state separate from admitted memory. No merge, real keys, trust or production.
