# R22.14 — retained signed tree floor and cold restart

RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.

Parent #368 at abc5281b9235f94e850cfb93376836e575c8d9e0. No new publication. Reuse genuine earlier and later Sigsum TEST receipts from R22.12 and recovered bytes from R22.13. Official pinned sigsum-verify v0.14.1 verifies both exact receipts under the same supplied public key and pinned TEST policy. Verify floor and ledger preimage correspondence with existing R22.12 verifier. Before transferring a proposed retained pin, scan live from both roots and require the same sampled cosigned head and exact retained leaf.

Separate runner restores old local files and receives retained pin through artifact transfer; independently verifies authentic old receipt and later control receipt (later history bytes not extracted). The post-authentication gate binds log, signer, scope, tree size/root, leaf index and envelope commitment. The retained record includes sequence, floor commitment and ledger digest. Gate rejects old signed head, same-size conflicting root, same-sequence conflict, wrong signer/scope, old scope in larger tree, newer tree without consistency, invalid floor. Missing/corrupt/replayed pin with original expected digest and tampered envelope are negative controls. Old local inputs and retained pin unchanged. Live scan from retained root checks cosigned tree and leaf inclusion; no advancement or adoption. A deliberately reset-both control must show that restoring old pin as well as local state defeats this comparison.

Boundary: post-authentication hypothetical root/sequence conflicts are injected data, not actual signed log equivocation. Authentic old proof is real but presented offline, not a demonstrated live log attack. The pin and its digest travel together under common repo administration; no independent custody or external monotonic storage proven, no recovery if both reset. Newer heads require consistency and further scope/semantic checks; no general advancement contract here. Same-head match is not freshness. No physical restore or durable availability claim. No new keys, trust or merge.

Execution pending; record observed result separately.

## Verified live observation (2026-11-24)

[Run 45462102110](https://github.com/SepehrGhanbari/Ario/actions/runs/45462102110), exact source/workflow HEAD a28933a3da53825245370175b89dee1dc29ee56e: both jobs SUCCESS. Job logs read directly. No new publication.

- Retain 138687172492: three prior artifact ZIPs checked against pinned SHA256 and CRC. Both genuine R22.12 receipts independently verified with official sigsum-verify and pinned TEST policy. Exact R22.13 recovered floor and ledger matched R22.12 originals and existing floor verifier. Retained seq 4, leaf index 281591, tree size 281592, root b97c1a479995d391b63f504537d3b6ead07d919b2218f5d4cebe8acf9e87007b, envelope checksum f65228cb44ea900d6d78e6465967b5ec0b4d3894946c801acb678053200c908f, floor digest e8877d476cd1fbaf4165636b865a225704994f401cdccf1cbafd1cc909acaedc, ledger SHA256 e78f44fb5fd8dca2b8a3c0066cb1eceecbddae256e4b1d3666c00a2d02222085. Retained pin SHA256 185a154389c15704a5a462aa3ff0c08a0c6f102163e36c31af55054a1c5da99e. Both historical roots verified consistent with same live cosigned tree size 281594, root ed25f4a5c1a6e78be8864eaf565762ed4f8138238f697b8e18ef3731d4722de8; exact retained leaf confirmed.
- Cold 138687789062: genuine old proof and retained proof both cryptographically verified. 14 reported cases: 12 HOLD (actual stale signed tree, corrupt pin, invalid size, missing pin, newer tree without consistency, older scope in newer tree, rolled-back pin with original expected digest, same sequence conflict, same size root conflict, tampered envelope, wrong scope, wrong signer); retained proof MATCH_RETAINED_NOT_FRESHNESS; deliberate reset-both residual MATCH_RETAINED_NOT_FRESHNESS. The last result is a demonstrated limit, not rollback resistance. All 12 old input and pin files unchanged before and after resampling. Live cold scan from retained root verified consistency to size 281594 and exact retained leaf. R22_14_COLD_LIVE_RETAINED_FLOOR_MATCH_NOT_FRESHNESS. No automatic advancement or admission.

New artifact metadata from GitHub API/job logs; new ZIPs not independently downloaded/rehashed here.

| Artifact | ID | SHA256 | Bytes |
|---|---:|---|---:|
| RETAINED-PIN | 14952419565 | c964ff95237783a251d9d95a8e15512d151f6f18e25325bf1b4fec3354cfa793 | 2081 |
| COLD-OBSERVATION | 14954171048 | 97f085811370f74202d73dec23a5a6eebe8e9e2fc51bed772b5f5e7076635849 | 1579 |

Narrow authentic stale-proof rejection and cold-restart experiment PASS; research HOLD. Actual old proof was presented offline; synthetic conflicts do not establish live signed equivocation. Retained pin and expected digest have common administrative control. Resetting both defeats the comparison; no independent monotonic custody. Global freshness, permanent availability, event truth, physical restore and admission remain unproved. Next: test separately controlled monotonic retention and authentic forward advancement across a later publication, followed by restart and rollback controls, without real keys or trust activation.
