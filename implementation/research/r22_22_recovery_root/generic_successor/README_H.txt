R22.22H — atomic verified successor (RESEARCH_ONLY)

Purpose
Combine R22.22G's unpinned successor verification with R22.22F's atomic retained-floor CAS in one process. The candidate archive is read once. Its Nostr signature, canonical envelope, ledger prefix/predecessor, two official Sigsum inclusion proofs, and common witnessed-head consistency are checked against that exact byte snapshot. Only the exact validated candidate ledger bytes held in memory can then be committed.

Local run
The local 27-control transaction run uses the official sigsum-verify v0.14.1 binary and a pure-Python BIP340 shim. Its live-head helper is a TEST FIXTURE that returns the already verified historical coordinates; it does NOT make a live network request. The GitHub Actions workflow builds and runs the unchanged R22.22G Go helper against the live Sigsum TEST log and is the authoritative live consistency check for H.

Important boundaries
- Historical archived transition only: sequence 6 -> 8, leaf 281662 -> 281663.
- The candidate archive hash is not pinned; the first retained anchor archive remains pinned.
- The commit writes only into a disposable temp directory owned by a separate Linux UID. It fsyncs the pending file and directory entry before rename, then fsyncs the directory again after atomic replacement.
- Same-root/root-admin rollback is deliberately reproduced as RED; UID separation is not independent administration.
- Global latest remains UNKNOWN. The live proof verifies the sampled witnessed head and consistency, not completeness of all Nostr events for this identity.
- The Python in-memory Prepared seal is a research-process guard, not a cryptographic authority boundary.
- No new Sigsum/Nostr publication, real keys, persistent production floor, trust activation, production enablement, or merge.
