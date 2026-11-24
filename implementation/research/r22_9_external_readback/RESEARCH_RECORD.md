# R22.9 — External TEST-log readback after synthetic local rollback

**RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.**

PR #355, parent #353 at ec712929febbf45b7b66b46b7a020769c99a40c7. No new publication, signing keys, authority or live journal mutation.

## Public bootstrap and verified prior proof

The R22.8 archived ZIP (SHA256 daf75e7f65a8c40bdda9eda370b4895e1037493c45700579ea38f321fd5263a0) was reopened. Local Python/Ed25519 verification checked the submitter signature, log signature, all three configured witness cosignatures, and the Merkle inclusion path for the count-four public envelope. The prior tree has size 281317 and root 92d02e588e5f85e1b57656093290f55079ec54241859be1c770719d0d5e98a27; leaf index 281316. This verifies the archived artifact's cryptographic relationships under its pinned policy, not independent event truth.

The readback program uses a fixed public bootstrap: the log URL, policy (2 of 3), submitter public key/hash, prior tree root/size, scan lower bound 281316 and registry of two possible envelope checksums. The registry is derived from the two public R22.8 envelopes by double SHA256. It does not tell the resolver which of those candidates has been published. These surviving pins are explicit assumptions, NOT recovered solely from the log or independently managed recovery material. The prior tree root is a bootstrap pin, not reauthenticated from the archive in the online program. Sigsum leaves contain signed checksums, not recoverable original history. Unknown matching-signer checksum means HOLD; a later known lower count means HOLD. Incomplete scan means HOLD. Selection is restricted to verified entries in a bounded sampled suffix; it never asserts global latest.

## Executed experiment

Initial push 45445070980 on d4fd800b1d4f14a72727f237dc4eac5867dffc88 failed at compile because the newer documentation's Leaf.Verify API differs from v0.14.1. Fixed only the call to use the pinned version's public-key pointer and bool result.

Corrected source HEAD e41f32093a6a3e93c458ae754f408f4c11d3ae3f.
Run https://github.com/SepehrGhanbari/Ario/actions/runs/45445249129, job 138627108931: SUCCESS. The workflow copies only the Go program/test/module declaration into a fresh temporary directory, writes synthetic local count-four state, then replaces it with count two. No earlier receipt ZIP or proof is present in that working directory; the probe does not read the local state. No actual publisher database or physical host restore was performed. Existing archive remains in the repository checkout, outside the scratch directory, and the probe does not read it. This tests recovery of a known public commitment despite rolled-back synthetic state, not complete independent administrator or disaster-recovery proof.

- Six Go resolver subtests passed (older, forward, incomplete, opaque, regression, empty).
- Cosigned live head verified under fixed policy: size **281319**, root **1668feaca1e1da8b8c970e5307e746961f17ac2d89fa217897e22c6be4693b9f**.
- Merkle consistency verified from the prior pinned size 281317/root.
- All 3 leaves at indices [281316,281319) individually checked by inclusion proof and exact index against the sampled root; full *bounded sampled suffix*, not full log.
- One matching-key leaf at 281316, submitter signature verified, checksum f1c1e3f6745611636ac0ed94edc01c35be3079e5dbc0bca184388a0cbccd4d8c (count four).
- Recovered highest known candidate count 4; count-two local-state file hash unchanged.
- No later matching-key leaf in the verified suffix. No conclusion about other keys, earlier unscanned leaves, future heads, hidden newer states, or arbitrary original bytes.

Exact result from the live workflow:
```json
{"complete_sampled_suffix":true,"disposition":"KNOWN_CANDIDATE_RECOVERED_IN_BOUNDED_SAMPLED_SUFFIX_ONLY","global_latest_scope":"NOT_ESTABLISHED","highest_known_candidate_count":4,"history_truth":"UNKNOWN","independent_latest_floor":"NOT_ESTABLISHED","matching_signed_leaves":[{"index":281316,"checksum":"f1c1e3f6745611636ac0ed94edc01c35be3079e5dbc0bca184388a0cbccd4d8c"}],"merge_authorized":false,"production":"NO_GO","sampled_tree_root":"1668feaca1e1da8b8c970e5307e746961f17ac2d89fa217897e22c6be4693b9f","sampled_tree_size":281319,"scan_end_exclusive":281319,"scan_start":281316,"source_freshness":"NOT_ESTABLISHED","trust_activation":"NO_GO","verified_leaf_count":3}
```

## Residual and next real boundary

An earlier valid cosigned head at or above the surviving root pin could be replayed. A scan of a bounded authenticated tree view cannot prove freshness beyond that view. The historical R22.8 submission key was ephemeral and discarded, so the probe does not establish a persistent enrolled identity for future updates. Stable scoped identity/key enrollment and independently retained, authenticated latest index or a complete monitored inventory with externally preserved recovery bootstrap/preimages are required. Missing recovery information, opaque newer commitments, outage, gaps, identity changes and same-admin reset must HOLD. No real event origin, evidence admission, independence, signing, production or trust established.

References: https://www.sigsum.org/getting-started/ ; https://pkg.go.dev/sigsum.org/sigsum-go@v0.14.1/pkg/requests ; https://pkg.go.dev/sigsum.org/sigsum-go/pkg/client .
