# R22.12 — replay of intact historical evidence

RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.

Parent #358 pinned to d9cd078836c25eb02d85483fec937e01855bcc39; all three parent PR checks completed SUCCESS. No new keys, publication, private data or admission. Historical input: original public synthetic [R22.10 run 45453396739](https://github.com/SepehrGhanbari/Ario/actions/runs/45453396739), artifacts FIRST-ONLY 14949671120 and SECOND-REVEAL 14948912790. ZIP SHA256s pinned in replay.py; both rechecked locally, CRC clean. Prior run recorded official verification of both receipts. Old count 2, index 281585, head 281586. New count 4, index 281586, head 281587. The previous-checksum link and scope match. The bytes and receipts are replayed intact; no counterfeit signatures.

## Local structural experiment
2026-11-24: exact archived envelope/proof fields read; 15/15 decision cases matched expectations. Source SHA256 25254e41feed8b58a5652073888318e899d9ba506912eef3af0fec249d55a32a, Git blob a957f548d19ec0fbd9370033645898db77365123. Run:
`python replay.py OLD.zip NEW.zip --structural-only`
This mode does NOT perform cryptographic verification. Local installation of sigsum-verify v0.14.1 failed because the network/DNS was unavailable. Local results are policy-model tests with historical artifacts, not new proof verification. Default mode requires the official pinned tool, checks the policy alias bytes against the archived policy, verifies old/new/old replay, rejects mismatched proof and changed content, then runs the policy cases. A separate advisory Actions workflow is supplied; its result must be inspected, not inferred from the local model.

## Decision boundary
- No retained floor: HOLD_FRESHNESS_UNKNOWN for both old and new.
- Old with retained newer floor: HOLD_ROLLBACK_BELOW_FLOOR.
- New with matching newer floor: MATCH_RETAINED_FLOOR_NOT_FRESHNESS.
- Old with rolled-back old floor: MATCH_RETAINED_FLOOR_NOT_FRESHNESS. **RED: rollback of floor defeats stale-pair differentiation.** This is a limitation, not a permission to admit.
- Candidate beyond floor: HOLD_ADVANCE_UNPROVEN; a larger count/head alone is not sufficient.
- Scope/signer/log/policy, equal-head root and equal-count checksum conflicts are held.
- No global freshness claim. Floor is a trusted-input model using archived newer evidence in memory, not independent persistent custody. This test cannot establish physical separation or a current signed head. Hypothetical field mutations exercise policy only; they are not signed external evidence. No actual network replay or full disk restore.

The old and new artifacts expire according to the R22.10 record; retain original ZIPs separately. Next: actual separately controlled retained floor and authenticated discovery handoff, then real rollback of the publisher without rollback of the floor. Also establish consistency proof for valid advancement before considering a future floor-update protocol.


## Verified execution addendum — 2026-11-24

[Run 45455849012](https://github.com/SepehrGhanbari/Ario/actions/runs/45455849012) on exact source HEAD 76ef709bffaa84e72d5546600bb9f6d5a4cba7f0 completed SUCCESS. Pinned official Sigsum v0.14.1 reverified old, new, and intact old replay (3/3 positive); wrong receipt and changed bytes rejected (2/2 negative); all 15 policy cases passed. Artifact 14949877736 ZIP SHA256 e485144d5689a5f4ccb5496f020f0c3467738adde46d283abee34282bf09377a verified against API digest and CRC; expires 2026-12-24. This is an offline replay of actual archived TEST proofs, not a fresh log query or independent floor custody. Rollback of floor itself remains RED. No keys, authority, merge, production or trust activation.
