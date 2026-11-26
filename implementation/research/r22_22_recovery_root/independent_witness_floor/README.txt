R22.22I — external independent witness floor (read-only, TEST_ONLY)

Question: can an operator roll back the publisher, GitHub, and local retained floor without an independently administered witness quorum noticing?

Existing external infrastructure discovered:
The exact sigsum-go v0.14.1 built-in sigsum-test2-2025 policy uses https://test.sigsum.org/barreleye and a 4-of-5 quorum. One logical member is a 2-of-3 group of witnesses operated by Glasklar employees. The other four members are outside operators: Filippo Valsorda/Geomys, Florian Larysch, Grégoire Détrez, and Tillitis AB. Therefore every valid 4-of-5 quorum necessarily contains at least three of those four external witnesses. The implementation verifies each external cosignature and reads each corresponding witness get-tree-size endpoint. It requires three external witness states at or above the same cosigned tree head.

Pinned prior observation:
R22.22H live run 45832963035: size 282808, root 6653d7a489d9988554eae8679a677f84c7a18074dbcc3a7b185773a5e83a1e4d.

Live, read-only steps:
1. Fetch current cosigned head from the Sigsum test log.
2. Verify log signature and exact built-in sigsum-test2-2025 4-of-5 witness policy.
3. Verify consistency from the exact retained R22.22H tree head.
4. For each of four external witnesses, verify its cosignature over this exact head and read its own get-tree-size endpoint.
5. Require at least three external witnesses to have both a valid cosignature and a stored size >= the sampled cosigned head size.
6. Treat a candidate below that floor or a same-size different root as HOLD.

No POST is sent to any witness or log. No publication, DNS change, key generation, private key, account, payment, or user resource is required.

Boundaries:
- This is a TEST witness network, not the production Sigsum generic policy. Test operators can reset their test state; it is not a permanent contractual custodian.
- Witnesses retain/check monotonic tree-head state, not the underlying Ario files or all log leaves. This proves an external anti-rollback floor for the sampled Sigsum tree, not data availability.
- It does not prove that the sampled tree contains every Nostr event for the identity; global latest remains UNKNOWN.
- If fewer than three external witness readbacks pass, report HOLD and do not weaken the threshold.
- No trust activation, production, merge, or new external publication.
