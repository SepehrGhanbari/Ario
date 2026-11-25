# R22.20 — external lifecycle checkpoint after joint local rollback
RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.

Parent #373 c0b38a738d7d200a10d028acdfaeb01c55279701, all three final checks SUCCESS. No duplicate R22.20 found. R22.19 lifecycle.py blob 42c6d0eed5711b629ff9f9ab62b8b5ac5427f1ba and nonce_ledger.py blob 2fdf68750ce7a0015fe3c8b51b97693b9346140c copied unchanged. Exact original public synthetic R22.17 TSA capture pinned, no additional TSA requests. R22.14 scanner reused unchanged. The only new external publications are two PUBLIC synthetic lifecycle commitments using an ephemeral test key, never a real Ario key. No private or personal data.

Actual local Linux disposable experiment: separate publisher and custodian UIDs, real SQLite lifecycle, issue historical A at epoch1; rotate to epoch2, A abandoned, B enrolled and consumed with actual archived RFC3161 response. Canonical state includes epoch, nonce, query hash, terminal state and response hash; second envelope links first via Sigsum double SHA256. Supervisor restored both actual old files (publisher JSON and SQLite), validated exact old state. 10/10 expected comparator cases passed with locally computed second checksum; this local run does NOT authenticate external evidence. Source SHA256 e7dbe69416a7ac32c0ab0f0685a386087bad7cfb332fb5ba41e77b6b5398c807, Git blob 2d0aedd06c2a276e8393d15fb59c99b0a6aa6a97. The comparator assumes authenticated inputs from the workflow; mutated cases are policy controls only, not signed evidence.

Dedicated three-job workflow: produce states; publish both with official pinned Sigsum v0.14.1 TEST policy; verify both; actually restore local files AFTER publication; first-only scanner in a separate runner (no checkout, second hash/bytes withheld); later job reveals second bytes, verifies original proofs and matches discovered leaf index/checksum, tests comparator. CI pending at authoring. The scan cap of eight leaves may fail under intervening traffic; fail closed, no automatic resubmission. No independent content custody: second bytes via GitHub artifact, not a separately administered store. Recovery assumes surviving authentic first bootstrap and scanner. Replay of historical signed head, loss of bootstrap, same-admin CI tamper and global freshness remain unresolved. No admission, actual whole-device rollback, independent administration, production, trust or merge. Original TSA capture expires 2026-12-24.


## CI failure and correction — 2026-11-25

Initial [run 45652466329](https://github.com/SepehrGhanbari/Ario/actions/runs/45652466329) failed before publication: distinct UID could not traverse private /home/runner/work/_temp (Permission denied opening lifecycle.py). All publication/discovery/reveal steps skipped; no external commitment published. Corrected only workflow lab location: random dedicated /tmp parent (0755), root creates lab child, unchanged lifecycle/verifier code and publisher/custodian 0700 directories. No permission change to runner home or private workspace. Corrected execution pending.


## Verified external execution — 2026-11-25

[Corrected run 45662110776](https://github.com/SepehrGhanbari/Ario/actions/runs/45662110776) SUCCESS on exact source 764d535efa9a96a9f4457fd1fd20230bad36dbde; all three jobs (publish, discover, reveal) SUCCESS. The earlier run 45652466329 failed before any publication due to private Runner temp-directory traversal; the /tmp correction is effective.

### External publication and blind recovery
- Reused exact pinned R22.17 historical TSA capture SHA256 b7f1702b88241f6062c6e9c3975e5969620e98b6fc47321ca7e91956c7500f8e; no new TSA requests or real keys.
- Published exactly two public synthetic lifecycle checkpoints to Sigsum TEST policy sigsum-test1-2025 with a newly generated ephemeral test key. Official sigsum-verify validated both proofs in reveal job.
- Verified cosigned tree head size 281668, root 9c7044a6046a110de263e507f9b461028baf82c526ac711fb162360732949f20; consistency from first checkpoint bootstrap PASS.
- First checkpoint leaf index 281666, checksum 076c693d756d29d2a90215831ff80ca3661cdc6f1f13facf19456b46d1b8d7f8. Second checkpoint leaf index 281667, checksum 873df176f5c17d14f43d869bcb10ec12c44efaf7007f730eb786d6f9c9e87e13.
- Discovery runner received only first checkpoint bootstrap and scanner code, not second bytes or checksum. It independently read the live Sigsum TEST log and returned HOLD_LATER_SIGNED_COMMITMENT, two matching same-key signed leaves, old_state_admissible=false. Global latest, source freshness and independent latest floor remain NOT_ESTABLISHED.
- After publication, publisher JSON and custodian SQLite were both actually restored to epoch 1 / request A ISSUED. Fresh runner's externally discovered later leaf was compared with that restored state. 10/10 expected controls PASS: joint rollback below external evidence detected; matching later content returns MATCH_EXTERNAL_EVIDENCE_NOT_FRESHNESS; missing evidence, old replay, wrong checksum, scope/link mutation, terminal-state mutation, authority mutation and split local state all HOLD.
- Downloaded artifacts were independently cross-checked locally: identical ephemeral public key across proofs; envelope double-SHA256 values match the two discovered leaves; proof leaf indices match 281666/281667; restored publisher and ledger agree on the old state. Local check: ALL_ARTIFACT_CROSS_CHECKS_PASS. Official proof verification is the successful reveal job, not this local structural check.

### Retained GitHub Actions artifact hashes
- first-restored ZIP: fa3170516398cbd15e9d7df7c02149ba10b3d0bbd9b973b6275c48fe80c2ae55
- withheld-second ZIP: e102d585e98b371e4bc00bd833b6e7a4c87bea988acef12afdf80642ffec3c38
- scanner-first-only ZIP: 019616f7fd1d4b52e5bdb43b50e53fb5c442b3c69782b1e21b9659fd0c4a842d
- live-discovery ZIP: d6cde2c9034ea5f11e4d2bd12ec5fc7de2432c905e96b9509352c5133b7a3dfe
- rollback-results ZIP: c1d5533e571640f3b77a8bf4f9b3396ec3d6303983fd3146a4185c28c5d95672

### Limits / decision
This demonstrates detection of joint rollback of the two local state files relative to a surviving first checkpoint and later signed entry in Sigsum TEST. It does NOT prove global freshness, historical truth, production availability, independent latest-floor custody or protection if the first bootstrap and recovery material are also replaced/lost. Sigsum stores commitments, not the committed content; the second envelope is retained in GitHub Actions artifacts under the same broad platform administration, not an independent content custodian. A new ephemeral test key proves only continuity within this synthetic run. Test log and test policy only. R22.20 result: EXTERNAL_ROLLBACK_DETECTION=PASS (bounded); GLOBAL_FRESHNESS=UNKNOWN; INDEPENDENT_CUSTODY=NOT_ESTABLISHED; TRUST_ACTIVATION=NO_GO; PRODUCTION=NO_GO; MERGE=NOT_AUTHORIZED. PR #377 remains draft and unmerged. Workflow artifacts have 30-day retention.
