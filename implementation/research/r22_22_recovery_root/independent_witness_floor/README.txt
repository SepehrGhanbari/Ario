R22.22I — external independent witness floor (read-only, TEST_ONLY)

Question: can an operator roll back the publisher, GitHub, and local retained floor without an independently administered witness quorum noticing?

Existing external infrastructure discovered:
The first live run verified only five individual cosignatures under the built-in sigsum-test2-2025 policy and did not satisfy its 4-of-5 grouped quorum; that failure is preserved. The follow-up therefore uses an explicit custom external-only 2-of-4 policy over the four public keys listed by sigsum-go v0.14.1: Filippo Valsorda/Geomys, Florian Larysch, Grégoire Détrez, and Tillitis AB. Glasklar is excluded entirely. This custom policy requires two distinct external witness signatures on the same head. The implementation independently verifies those signatures and reads each corresponding witness get-tree-size endpoint; it requires two external witness states at or above the same cosigned tree head.

Pinned prior observation:
R22.22H live run 45832963035: size 282808, root 6653d7a489d9988554eae8679a677f84c7a18074dbcc3a7b185773a5e83a1e4d.

Live, read-only steps:
1. Fetch current cosigned head from the Sigsum test log.
2. Verify log signature and custom external-only 2-of-4 witness policy.
3. Verify consistency from the exact retained R22.22H tree head.
4. For each of four external witnesses, verify its cosignature over this exact head and read its own get-tree-size endpoint.
5. Require at least two external witnesses to have both a valid cosignature and a stored size >= the sampled cosigned head size.
6. Treat a candidate below that floor or a same-size different root as HOLD.

No POST is sent to any witness or log. No publication, DNS change, key generation, private key, account, payment, or user resource is required.

Boundaries:
- This is a TEST witness network and a custom research policy, not the production Sigsum generic policy. Test operators can reset their test state; it is not a permanent contractual custodian.
- Witnesses retain/check monotonic tree-head state, not the underlying Ario files or all log leaves. This proves an external anti-rollback floor for the sampled Sigsum tree, not data availability.
- It does not prove that the sampled tree contains every Nostr event for the identity; global latest remains UNKNOWN.
- If fewer than three external witness readbacks pass, report HOLD and do not weaken the threshold.
- No trust activation, production, merge, or new external publication.
