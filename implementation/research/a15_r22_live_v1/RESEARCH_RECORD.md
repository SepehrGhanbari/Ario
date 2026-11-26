# A15/R22 live synthetic checkpoint v1 — research experiment

RESEARCH_ONLY / DRAFT / HOLD / SYNTHETIC_ONLY / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_MERGE.

Stacked on #382 exact head 835dd9e131a63e08f8b41964114a49ea25288aa9 (offline CI 19/19 on each OS). Broker unchanged, pinned by the adapter. This branch publishes two newly generated synthetic checkpoint envelopes only, with random synthetic scope and disposable Nostr/Sigsum TEST keys; no real journal, key, choice text, request ID, or database bytes are published to relays/log. Synthetic state copies are GitHub Actions reveal artifacts, never given to discovery.

R22.20 transport functions and bootstrap adapted from fbb47a4f63c889170bdfabdadbe28dafd9812603; R22.10 scanner checked out at #375 head 4ca8ba373cc687252bc06462986e5323f75a7bcc. R63 direct-monitor helpers checked out at #369 head c4bd0dc8aa04ce0fe0bf4a7b8394b81994a81b14. New domain is A15/R22, not a reuse of R22.15B ancestry.

Three jobs: publish synthetic seq 1 and 2, then publisher exits; cold runner sees first-only artifacts, verifies first inclusion, discovers signed later leaf without the second checksum, recovers exact signed content from relays, and checks R63 direct observations (advisory, separate result). Final reveal runner checks exact bytes, official inclusion proofs, and recomputes Broker state, including joint rollback, same-seq fork and unanchored suffix. Negative network controls use unreachable loopback endpoints, not actual sabotage of relay services. Missing data and any inconsistent proofs HOLD. R63 may HOLD separately; no trusted time, independent administration, long-term retention, nonce-bound freshness or global latestness proven. GitHub artifacts are not independent custody. This experiment does not gate the Broker or establish production authority.

Workflow is intentionally push-triggered only for the new workflow file on this isolated research branch. No automatic live retries. Initial status: NOT_RUN until actual logs are checked.
## A15/R22 proof-envelope compatibility audit — 2026-11-26 (offline, retained evidence only)

New read-only compatibility workflow `.github/workflows/a15-r22-proof-compatibility.yml` is separate from the existing push-triggered live publication workflow; its path filter cannot trigger another publish. It downloads only the original A15 artifacts from run 45823494521 (FIRST-ONLY, SECOND-REVEAL-SYNTHETIC, COLD-RECOVERY), checks out exact R22.22G source #380 at `255398a8e243d3738b132dafe0fe0edcaab29679`, and runs offline. No relay calls, Sigsum publication, key generation for A15, deletion, or floor write.

New `proof_contract.py` pins the exact A15 live module and R22.20 event codec/pure BIP340 verifier blobs. It verifies both archived A15 event signatures, exact envelope/event-ID byte binding, official Sigsum TEST proofs, proof coordinates and checksums against the first-only bootstrap and cold discovery, strict leaf order, seq1→seq2 predecessor digest, and exact cold-recovered seq2 bytes. It constructs one throwaway R22.20 event with a disposable test-only key and requires both profiles to accept their own event and reject the other at envelope and event boundaries. Swapped and tampered Sigsum proofs must fail the official verifier.

The original live run's final reveal failure remains preserved. This job does not relabel run 45823494521 as wholly successful; it independently checks retained proof/envelope compatibility only. GLOBAL_LATEST and independent custody remain NOT_ESTABLISHED. No merge, new external publication, real key, trust activation, production, or evidence admission. Status remains NOT_RUN until the exact job log is inspected.

## Proof-compatibility workflow transport correction — 2026-11-26

First exact-head compatibility run `45835527574` reached the cross-run artifact fetch step but `actions/download-artifact@v4` returned `Bad credentials`; the verification script did not execute. No source evidence was changed and no publication occurred. The fetch route was changed to the same `gh api repos/$GITHUB_REPOSITORY/actions/artifacts/{id}/zip` pattern already used by the existing #380 R22.22G workflow, with exact ZIP SHA256 checks for artifact IDs 15118184755, 15118049899 and 15119226101. Added bounded ZIP extraction with exact member manifests, CRC/path/symlink/size checks. This is a workflow transport repair only; exact-head verification remains NOT_RUN until the next job completes.

## Cross-run artifact transport fallback — 2026-11-26

The exact-head compatibility run using `actions/download-artifact@v4` failed with `Bad credentials`; the attempted `gh api` retry also returned HTTP 401 in this workflow context. Neither attempt executed the compatibility verifier. Both transport failures are retained here. The three existing synthetic artifacts were already downloaded through the authenticated GitHub connector, and their ZIP SHA256 values match the original artifact API digests. Exact ZIP bytes were therefore committed as bounded test fixtures under `implementation/tests/fixtures/a15_r22_run_45823494521/`; the wrapper checks all three exact digests and member manifests before extraction. No new artifact was published and no source workflow was re-run. Exact-head compatibility CI remains NOT_RUN until the next job completes.

## Cross-run artifact transport fallback — 2026-11-26

Two attempts to fetch previous-run artifacts from inside this workflow failed with `Bad credentials` (first `actions/download-artifact@v4`, then `gh api`); neither executed the compatibility verifier. Both transport failures are retained. The two exact A15 synthetic ZIPs were already downloaded through the authenticated GitHub connector, and their SHA256 values match original artifact digests. Exact bytes are stored as test fixtures under `implementation/tests/fixtures/a15_r22_run_45823494521/`; the wrapper checks ZIP hashes, CRC, exact member manifests, path traversal, symlinks and size limits before extraction. The cold-recovery ZIP is deliberately not included in this compatibility job; its historical result remains as-is and is not re-asserted here. Exact-head compatibility CI remains NOT_RUN until the next job completes.

## Exact-head verifier source-pin correction — 2026-11-26

The first fixture-backed run `45837293507` safely verified both ZIP digests and pinned A15/R22 event-codec sources, then stopped at the R22 pure BIP340 verifier Git-blob pin. The expected hash literal contained a one-character transcription error; the exact file at pinned R22.22G commit `255398a8e243d3738b132dafe0fe0edcaab29679` reports blob `a29990a1e695b64d7611483e1e0d5f486c02c932`. Corrected only that literal. No event/proof test ran in the failed attempt; no evidence or protocol state changed.

## A15/R22 proof-envelope compatibility exact-head result — 2026-11-26

Dedicated read-only workflow 45837502441 at source head `56f2890bb14a1e25e05e891a16d52eda597c12a7` completed **22/22 checks PASS**. Exact original A15 fixture ZIP digests were verified before safe extraction. Both archived A15 Nostr events and both official Sigsum TEST proofs verified; leaf indexes 282772 and 282773, sizes 282773 and 282774. First bootstrap bound the first leaf; seq=2 checkpoint predecessor digest exactly matched seq=1 payload digest. Pinned R22.20 codec accepted its own valid throwaway synthetic event and rejected A15 envelope/event; A15 parser accepted its own archived events and rejected R22.20 envelope/event. Official Sigsum verifier rejected swapped and tampered proofs.

This is a retained-evidence compatibility result, not a new live publication or global-latest proof. The previous cold-recovery record is not re-run by this job; the original live run's final reveal failure remains unchanged. R22.22G generic successor is not a drop-in verifier for A15. A15-specific proof envelope remains required. `global_latest=UNKNOWN`, `independent_custody=NOT_ESTABLISHED`, `evidence_admission=NO_ADMISSION`; trust/production NO_GO. No merge, key, floor, policy, trust activation or production change.


## Workflow run identity correction — 2026-11-26

The preceding section cited run ID `45837502441` in error. That ID is an **Implementation Regression** run and is not the dedicated proof-compatibility workflow. The correct dedicated run is [`45837490601`](https://github.com/SepehrGhanbari/Ario/actions/runs/45837490601), workflow path `.github/workflows/a15-r22-proof-compatibility.yml`, event `push`, exact source head `56f2890bb14a1e25e05e891a16d52eda597c12a7`, conclusion `success`. Its single `compatibility` job completed successfully; the job log records **22/22 checks PASS**, including both official Sigsum TEST proof verifications, the A15 seq1→seq2 predecessor binding, both cross-profile envelope/event rejections, and swapped/tampered proof rejection.

Run `45837502441` remains a separate successful Implementation Regression run. This correction changes only the run reference; it does not change the evidence, protocol state, or historical failure disposition. The original A15 live run's reveal-job failure remains visible. No new publication, key, merge, trust activation, or production action occurred.


## A15 checkpoint anchored under the R22.22I external witness floor — 2026-11-26 (read-only)

Dedicated workflow [45841356957](https://github.com/SepehrGhanbari/Ario/actions/runs/45841356957) succeeded on exact source commit `5ecd2ca08ff1e6405dc52e00484af124bc8dab55`.

The test joined the exact retained A15 artifacts to the independently witnessed R22.22I floor without publishing or signing anything:
- Both original A15 ZIP digests and exact member manifests matched: FIRST-ONLY `f6012b78741a23992be901141fb8eb560f7010d17ecc4ccf4e71d3f917cd5f97`; SECOND-REVEAL-SYNTHETIC `4eec66aeb8036e9628094acbe815c7418e88836d064b384dcd0558ed4910f3ec`.
- Both archived A15 inclusion proofs passed the official Sigsum verifier. A15 seq=1 is tree size 282773/root `a22c530084d2f025d28102a1178048fdfde039a78eccec2602536b3a139e37af`; seq=2 is tree size 282774/root `4a75206b4b69142d1d90a284420d64cabf11ebe09931ba8e97262e2ad7baa1d5`, leaf index 282773.
- The pinned R22.22I external-floor record is from commit `2139914a255aa58b3706eaa401dc744fa82e8d56`, exact Git blob `07b1172fd77cf53d9dba9b4e06215d33f42705cb`. It identifies the same Sigsum log ID `4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d`.
- The externally witnessed floor is tree size 282813/root `748c0c608c8f691fd7e9a9b9d98e920f9a529f3dbcaf180109e5bcacb597196b`. The pinned record contains two valid external cosigners (Remora and Stagemole); Remora's status page exactly matches the signed size and root.
- A live Sigsum consistency proof from A15 size 282774 to external floor size 282813 was retrieved and verified with the official sigsum-go v0.14.1 consistency verifier. Result: `A15_HEAD_TO_EXTERNAL_WITNESS_FLOOR_CONSISTENCY PASS`.
- Separately, the same 10-node proof was checked with the pinned R63 `verify_direct.py` consistency algorithm; changing one proof node caused rejection.

This establishes that the two A15 checkpoint leaves are within the later tree head covered by the R22.22I external witness signatures. It does **not** establish global latestness, data availability, production-grade custody, or full administrative independence. The policy was custom external-only 2-of-4; the built-in Sigsum test2 4-of-5 policy remained `NOT_MET`. Remora is a test VM without HSM/redundancy; Stagemole is a best-effort test witness. `global_latest=UNKNOWN`, admission=false, trust activation=NO_GO, production=NO_GO.

The original A15 live workflow's final reveal failure remains preserved and is not relabelled as a full success. This bridge used retained artifacts only: no new relay publication, no new signing key, no floor write, no merge, no trust activation, and no production action.
