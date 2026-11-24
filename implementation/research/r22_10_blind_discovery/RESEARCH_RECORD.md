# R22.10 — Blind discovery of a later same-key TEST-log commitment

**RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.** PR #356, parent #355 at 626c8da2d25a5836bb4202018bcd24990fa4dab9.

## Experiment and result

[Actual external TEST-log run 45453396739](https://github.com/SepehrGhanbari/Ario/actions/runs/45453396739), exact workflow/source HEAD 94b61f70362adc9606add344956ba85964018e61, all three jobs SUCCESS:
- publish job 138656254871: generated two PUBLIC synthetic envelopes binding existing R22.7 floor commitments, same randomly chosen lab scope and one ephemeral submitter key, distinct random nonces. Submitted sequentially to Sigsum TEST; official v0.14.1 CLI verified each proof offline. No real Ario keys/data; ephemeral private key not exported. First proof index 281585 / tree size 281586, second proof index 281586 / tree size 281587.
- discover job 138656999683: separate fresh hosted runner downloaded only FIRST-ONLY artifact. Scratch input was first bootstrap JSON and simulated old local state, plus program and Go module. No second artifact, checksum, leaf index or preimage passed to scanner. It verifies cosigned live head under pinned 2-of-3 policy, Merkle consistency from first bootstrap root, individual inclusion proofs and exact positions for every leaf in bounded sampled suffix [281585,281587), and matching-key leaf signatures. Six resolver subtests passed (blind, missing, incomplete, old-only, repeat, order). The live result found one additional opaque signed commitment. Local state checksum remained unchanged.
- reveal job 138657419611: downloaded first, second and discovery artifacts only after discovery completed. The previously withheld second envelope double SHA256 exactly equals discovered checksum and proof index. Scope and previous checksum link match; counts 2 and 4. This is independent of the scanner's pre-known candidate registry, NOT independent administration or independent reviewer validation.

First checksum: 179f5692b4273c5daaa17706f7b9fb7d326337ffe36f9f3b86378f288fe8077e
Second checksum (learned by scanner from live log): a0ac8945297132b7c869c79b7d08f4b303ee49599112269428013fc83bde3905
Signer hash: 32c199644b404b666091e142334a932293920b59a1e3143ae058759e2b19409d
First tree root: 85ce1600bef1ac2eac853c1185b9264c44517ae2258061de1dca44c5f375cc25
Sampled cosigned tree root: 9a78d2f669bc0ff5300cc3944411856d7e22a228a23ad13cd2082e67ce70ab44
First and second floor commitment digests: 24d48d5c6ee05f67f2c56150124946a21530e44ae9aaa6dfcf55f6bd4f456aa1 and 335b594a7d3db58beb4836749a935bd387b58eafbf771e9b14797c2e7a0408f7.

Scanner output:
```json
{"complete_sampled_suffix":true,"disposition":"HOLD_OPAQUE_NEW_SIGNED_COMMITMENT","global_latest_scope":"NOT_ESTABLISHED","history_truth":"UNKNOWN","independent_latest_floor":"NOT_ESTABLISHED","matching_signed_leaves":[{"index":281585,"checksum":"179f5692b4273c5daaa17706f7b9fb7d326337ffe36f9f3b86378f288fe8077e"},{"index":281586,"checksum":"a0ac8945297132b7c869c79b7d08f4b303ee49599112269428013fc83bde3905"}],"merge_authorized":false,"new_opaque_signed_commitments":1,"production":"NO_GO","recovered_content":false,"sampled_tree_root":"9a78d2f669bc0ff5300cc3944411856d7e22a228a23ad13cd2082e67ce70ab44","sampled_tree_size":281587,"scan_end_exclusive":281587,"scan_start":281585,"source_freshness":"NOT_ESTABLISHED","trust_activation":"NO_GO","verified_leaf_count":2,"verified_scope_sequence":"UNKNOWN"}
```

Reveal result: WITHHELD_BYTES_MATCH_DISCOVERED_CHECKSUM. Second index 281586, count 4. The Go resolver treats a new matching-key checksum as opaque, and returns HOLD rather than claiming a scope or count. No automatic adoption.

## Original public artifacts

All three original ZIPs were downloaded, SHA256 checked against GitHub API digests, and ZIP CRC checks passed. No private key files in their inventories. Artifact retention 30 days (until Dec 24, 2026). Exact evidence hashes:
| Artifact | ID | SHA256 | bytes |
|---|---:|---|---:|
| FIRST-ONLY | 14949671120 | 337fc0e36441c0eb3d4ebeb1736cb83bbea8cb958dd8b5aba846a8c1230fc16d | 3875 |
| SECOND-REVEAL | 14948912790 | 652ff3f19ce4470b82aaf70acf9c2f6e4b0f3aa00a7f7c17a0adc916ba0fd56e | 3381 |
| BLIND-DISCOVERY | 14947504418 | 41a272ef710a28efff482161d023a352f117727f66ef2964f01134a1d3c23303 | 702 |

The downloaded originals were bundled without modifying them, with a SHA256SUMS manifest, as R22_10_PUBLIC_EVIDENCE.zip (8035 bytes; SHA256 507c3a8a721d9d81f028e17da30bdc26d0845e78311e326cc161f554dfcb87ac). This bundle is supplied to the owner separately; the recorded artifact links themselves expire. Hash/CRC checks of downloads are not a second execution of the official verifier.

## Explicit limits and next boundary

- The scanner trusts a supplied first bootstrap produced by the publisher after official proof verification; no independent bootstrap enrollment or physical device restore. Jobs are separate hosted runners under the same repository administration, not separate authorities. The publisher's first root and key survive the simulated rollback. The scanner can access the public log, not second preimage; the reveal artifact is intentionally available to the evaluator, not a claim that access to it is impossible for a privileged repository operator.
- One ephemeral key spans two submissions and is discarded. This does not establish persistent identity or key rotation continuity. The scanner does not establish the second scope/sequence before reveal. Counts 2 and 4 are known by experiment design, but neither second index nor random checksum/preimage is supplied to the scanner.
- A complete bounded suffix of the sampled signed head is not global current completeness. Replayed cosigned heads at/above bootstrap, unseen later entries, unknown keys, shared-admin reset, bounded scan exhaustion and unavailable preimages remain limits.
- Next experiment: content-addressed public recovery of the exact synthetic envelope from a separately controlled store, with unavailable/modified content, wrong scope/previous link, and replayed older valid content tests. The hash log by itself does not recover original bytes. An independently protected latest-floor pointer remains a separate unmet prerequisite.
- No merge, signer, production, trust activation or evidence admission. No actual source of event truth claimed.
