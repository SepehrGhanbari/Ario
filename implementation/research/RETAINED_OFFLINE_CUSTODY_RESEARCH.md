# Retained offline research — closed external-custody lane

Owner-directed consolidation, 2026-11-26. This retains independent reusable **offline research components**, not an operational signing or custody service. No external publication, keys, live endpoints, deployment, production or trust activation. Original closed PRs remain historical evidence, not merged PRs. The historical source snapshots below remain addressable by exact commit. No source branches or records deleted.

## Reusable components

- [R63 continuity guard](../r63_external_floor_bridge/continuity_guard/README.md): exact source, tests and readme from #369; nonce-bound witness proofs, history-loss quarantine and durable local model. Original 48 Linux tests passed and 45 Windows tests passed (3 fork-only skips). All anchors remain under common administration; expected RED joint rollback is preserved.
- [R22.25 keeper model](../r22_25_independent_keeper/RESEARCH_RECORD.md): exact protocol, contract and tests from #396; 17 test functions and race detector previously passed. In-memory interfaces and test transition verifier do not prove independently deployed keeper or source-log verification.
- [R22.23 offline frontier](../r22_23_offline_frontier/README.md): Merkle reconstruction from retained rightmost path, sequential append and final root verification; no network client or old pinned live policy. Adapted local digest/head types, identical algorithm and existing four regression functions. Historical source CI 45823916435.

Existing merged #416 and #417 retain distinct signed-checkpoint and dual-approval simulator results. This consolidation deliberately excludes live publishers, repeated relay scans, obsolete external policy pins, TSA/OS-dependent orchestration, and research code requiring a real external custody provider. These exclusions remain inspectable in the source commits below; not claims of completion.

## Archived sources

| PR | Exact source | Disposition |
|---|---|---|
| [#356](https://github.com/SepehrGhanbari/Ario/pull/356) | [814f69d546d4](https://github.com/SepehrGhanbari/Ario/tree/814f69d546d41bb1e30ceac252d215df64d049bc) | Blind discovery and older replay/floor labs; historical evidence only. |
| [#361](https://github.com/SepehrGhanbari/Ario/pull/361) | [d5f66e0dcf70](https://github.com/SepehrGhanbari/Ario/tree/d5f66e0dcf70950e3ab27c3c92781a8b4c7dcaea) | Authenticated replay/lower bound; no live authority. |
| [#362](https://github.com/SepehrGhanbari/Ario/pull/362) | [bc9b34f46629](https://github.com/SepehrGhanbari/Ario/tree/bc9b34f4662975422e753d27e9aacec821d67293) | Linked synthetic content recovery; relay retention not guaranteed. |
| [#369](https://github.com/SepehrGhanbari/Ario/pull/369) | [15b3fa6e2431](https://github.com/SepehrGhanbari/Ario/tree/15b3fa6e2431b91043613520604f8b6980de5009) | R63 continuity guard and verifier retained here; other live/experimental code archived. |
| [#372](https://github.com/SepehrGhanbari/Ario/pull/372) | [cb87988a3947](https://github.com/SepehrGhanbari/Ario/tree/cb87988a3947d36445e8c10a3731bb0fae6a597b) | Monotonic custody lab; common-root rollback RED. |
| [#373](https://github.com/SepehrGhanbari/Ario/pull/373) | [c0b38a738d7d](https://github.com/SepehrGhanbari/Ario/tree/c0b38a738d7d200a10d028acdfaeb01c55279701) | Historical nonce/time lifecycle; depends on archived TSA fixture and UID lab. |
| [#374](https://github.com/SepehrGhanbari/Ario/pull/374) | [57f78cea088c](https://github.com/SepehrGhanbari/Ario/tree/57f78cea088cd825edd3df536859f18dfad26797) | A15 commitment/transport experiment; do not repeat publication. |
| [#375](https://github.com/SepehrGhanbari/Ario/pull/375) | [4ca8ba373cc6](https://github.com/SepehrGhanbari/Ario/tree/4ca8ba373cc687252bc06462986e5323f75a7bcc) | External floor recovery; temporary content availability only. |
| [#377](https://github.com/SepehrGhanbari/Ario/pull/377) | [1013ab38bf35](https://github.com/SepehrGhanbari/Ario/tree/1013ab38bf353b42e943aaaa3cd600fb094c3701) | Lifecycle experiment; live final result unconfirmed. |
| [#378](https://github.com/SepehrGhanbari/Ario/pull/378) | [e32a29470fda](https://github.com/SepehrGhanbari/Ario/tree/e32a29470fdac4638e842052ce0caf2491fa93b1) | Third-relay and deletion readback; no permanent custody. |
| [#379](https://github.com/SepehrGhanbari/Ario/pull/379) | [6fa4f8fe8f9e](https://github.com/SepehrGhanbari/Ario/tree/6fa4f8fe8f9e8fb21a1913bee68816cee140136e) | Historical range readback; not a global latest proof. |
| [#390](https://github.com/SepehrGhanbari/Ario/pull/390) | [57f0c6e88138](https://github.com/SepehrGhanbari/Ario/tree/57f0c6e88138d88086032becb4f1cf17d725837b) | Offline Merkle frontier algorithm and regression controls retained here; old live scanner remains archived. |
| [#391](https://github.com/SepehrGhanbari/Ario/pull/391) | [4ded7d16f60f](https://github.com/SepehrGhanbari/Ario/tree/4ded7d16f60fc32d202567d2f018f1574ac5deaf) | Historical resume handoff; common-admin checkpoint pin. |
| [#395](https://github.com/SepehrGhanbari/Ario/pull/395) | [aa1c242b3816](https://github.com/SepehrGhanbari/Ario/tree/aa1c242b38167cfffca5990c72e623f0d05e6145) | Exact checkpoint capture evidence; separate #416 signed-checkpoint verifier in main, not identical. |
| [#396](https://github.com/SepehrGhanbari/Ario/pull/396) | [1634bbc3d5c7](https://github.com/SepehrGhanbari/Ario/tree/1634bbc3d5c704044b51da2ce8f2a57efd65ec0e) | Keeper protocol model and tests retained here. |

Stop after normal CI validates the retained offline components. No new research cycle.
