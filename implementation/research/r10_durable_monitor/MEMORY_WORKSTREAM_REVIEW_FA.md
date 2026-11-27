# Ario memory-workstream review / Lovable provenance (21 Nov 2026)

**Review state:** RESEARCH_ONLY / HOLD / NO_MERGE. Source-verified branch/PR metadata, not a claim that any Lovable agent authored a branch or finished integration.

## What was actually visible

Connected Lovable workspace aa34915dfa39c28d8439 currently lists only two projects: “بررسی امنیتی آریو” (security review; last edited 6 Nov) and “Pixel Perfect Replica” (9 Nov). No separate cognitive-memory Lovable project or relevant active draft was discoverable in that workspace. A different Lovable workspace or unpublished project remains UNKNOWN. Do not attribute the owner-authored GitHub branch to Lovable without a concrete project/commit link.

## Memory research dependency map

| Component | Canonical research artifact | Observed status |
| --- | --- | --- |
| Modules 1–3: source monitoring, consolidation, retrieval | https://github.com/SepehrGhanbari/Ario/pull/210 | Draft, unmerged. Issue #216 remains relevant to RECORDED vs ACCEPTED semantics |
| Module 4: bounded WorkingMemoryBuffer, attention, decay, metacognition | https://github.com/SepehrGhanbari/Ario/pull/288 | Draft, unmerged; new head 0b0010715a2501cf3c4ea5cfa4df011c99931279; its working_memory.py blob f80858dee96b5f3671d7c8ffc9af697415a0d276 is still missing the guard integration |
| R07 corrections: source admission, defensive snapshots, non-amplifying rehearsal, RECORDED | https://github.com/SepehrGhanbari/Ario/pull/292 | Draft, unmerged; head 39ff752e7c650741676b0529a0a35e2d6a481285. Original base was older #288 head 14cdde7eea6d3993236e64f0e165a2ca778d4eab. Latest #288 needs reconciliation before merge |
| Transparency and checkpoint anti-rollback research | https://github.com/SepehrGhanbari/Ario/issues/280 | R08–R09 proved synthetic Sigsum receipts and actual monitor discovery; R10 only experiments with local recovery, not a separately controlled witness |

## Next narrow integration gates

1. Review the latest #288 commit against the R07 base; never assume green CI for an older commit covers a new head. Pin exact source SHA before final validation.
2. Keep the 13 R07 source-boundary regression tests, and require an authenticated/provenanced SourceMonitoringGuard record before an empirical readiness claim. Mutable snapshots must not let an external caller rewrite evidence.
3. Consolidating a recollection is not verifying it: structural LTM admission should remain RECORDED/UNKNOWN, not silently ACCEPTED as truth. One event must not turn into several independent sources by repeated flush, rehearsal or re-instantiation.
4. The working-memory attention score is distinct from independent witness verification; never pass the R10 diagnostic statuses into a production signer or memory admission gate.
5. Avoid additional overlapping memory PRs for each experiment. Track Modules 1–3 in #210, Module 4 in #288, existing repairs in #292, and witness recovery in R10/#280. Do not close branches, rewrite historical files or merge before confirming dependencies.

**Still UNKNOWN:** whether an inaccessible Lovable workspace made further changes, how #216 should be resolved architecturally, and whether fully external administrator-controlled custody for the latest checkpoint can be established.

**No repository production code, memory state, signer, Genesis, keys, branch protection or ruleset was modified by this report.**
