# Ario Foundation Recovery — 2026-11-25

**Status:** `RESEARCH_ONLY / DRAFT / HOLD / NOT_ADOPTED / NO_MERGE`  
**Base:** PR #321 exact source commit `7365e7a9ac7febb78b34039c7b36469b3344cfff`  
**Branch:** `research/foundation-recovery-20261125`  
**Authority:** bounded owner approval for the memory resolver and snapshot-restore research changes only.

## 1. Purpose

Preserve and test two memory-foundation safeguards on an isolated child branch of #321:

1. Ambiguous historical v1 identifiers must never resolve to whichever v2 node happened to be ingested last.
2. A snapshot's historical `ACCEPTED` or `SUPPORTED` label must not become active admission merely because structural restore checks pass.

No historical source bytes, event records, or prior commits are rewritten.

## 2. Legacy identifier ambiguity

The v1 identifier is derived from the concatenation `concept + ":" + assertion`. Therefore these distinct pairs share the same v1 preimage:

- `("a:b", "c")`
- `("a", "b:c")`

Their v2 tuple-derived identifiers are distinct. The v2 resolver now rebuilds the legacy alias projection from retained nodes, maps a non-unique legacy alias to an ambiguous result (`None`), and does not trust a stale cached winner from a historical snapshot.

The focused regression file covers both ingestion orders, duplicate replay, pickle round-trip, old single-winner snapshot reindexing, unique and missing lookups, v1 compatibility, failed-batch rollback, unrelated cached-target injection, and mismatched snapshot node keys.

## 3. Snapshot admission HOLD

`ConsolidationEngine.__setstate__` now validates node status before installing snapshot state:

- A node status that is not exactly a `NodeEpistemicStatus` value is rejected with `HOLD_INVALID_SNAPSHOT_STATUS`.
- Historical `ACCEPTED` and `SUPPORTED` statuses are rejected with `HOLD_UNVERIFIED_SNAPSHOT_ADMISSION`.
- The state is not installed before these checks; an existing engine remains unchanged on refusal.
- The snapshot's serialized bytes are not rewritten, and no automatic downgrade to `RECORDED` is performed.

The tests cover both privileged labels, direct `__setstate__` refusal, the actual `pickle.loads` restoration path, malformed string statuses, and preservation of the pre-existing engine state. Existing `RECORDED` round-trip tests remain the positive control.

**Important boundary:** this is an active-state admission guard, not a safe unpickling format. Python pickle can execute code while deserializing hostile input before an object's `__setstate__` method is reached. Do not load untrusted pickle bytes. This patch also does not authenticate the snapshot's origin or provide an independently verifiable admission record.

## 4. Exact source and validation status

- Base #321 source: `7365e7a9ac7febb78b34039c7b36469b3344cfff`.
- Resolver/snapshot implementation blob after the bounded change: `c2e740fc9eef188f5022064687dd0ce0467f8849`.
- Focused test blob after the actual-pickle-path addition: `7d1e8b2d75c9948a2036c5cea98afad965f6386d`.
- Codex previously reported 7 focused alias tests passing on Windows CPython 3.13 before the two new snapshot-admission tests were added. That earlier local result is not used as current-head evidence.
- **Exact code-head CI** for `86a326c930968a5620ca1a9dcc4f7c7710918440` completed successfully:
  - [Implementation Regression run 45666289088](https://github.com/SepehrGhanbari/Ario/actions/runs/45666289088): Linux CPython 3.13 **1,953 passed, 7 skipped, 2 xfailed, 2 warnings, 279 subtests passed**; Windows CPython 3.13 **1,951 passed, 9 skipped, 2 xfailed, 2 warnings, 279 subtests passed**; CPython 3.14 differential advisory **1,953 passed, 7 skipped, 2 xfailed, 2 warnings, 279 subtests passed**. The dedicated cognitive-memory job reports **114 passed**, plus **3 seeded fuzz tests passed**.
  - [Published TXT Restore Security run 45666289144](https://github.com/SepehrGhanbari/Ario/actions/runs/45666289144): all **10 jobs succeeded**.
- The CPython 3.14 log retains an `ARIO_HTTP403_DIAGNOSTIC` warning: metadata returned HTTP 200, but a job-log download timed out; execution attestation for that diagnostic remained `NOT_ESTABLISHED`. This did not fail the test job and is not evidence of an HTTP 403.
- The two newly added snapshot tests are included in the full `pytest -q tests` run. The logs use quiet mode and do not print each test name individually. Skips, xfails, and warnings remain visible and are not relabelled as passes.

## 5. Existing ledger-boundary work — reuse, do not duplicate

The exact #321 bridge still contains the older replay behavior: `STEP_OBSERVED` calls `record_empirical_observation`, and `TASK_FINISHED` calls the mutating `ProspectiveMemoryRegistry.evaluate_cues`.

The corresponding research corrections already exist on the separate Draft/HOLD [PR #273](https://github.com/SepehrGhanbari/Ario/pull/273), current head `1063bdabcd41b4d1562984c736000cb8689cf41b`:

- replayed step lines become `LEDGER_REPORT / REPORTED_UNVERIFIED`, not empirical execution proof;
- semantic nodes remain `RECORDED`;
- untrusted task-finish reports are counted but do not consume intentions or emit action payloads;
- supporting source-monitoring changes, CLI reporting, regression tests, and two draft boundary contracts are included.

Exact-head [CI run 44573488145](https://github.com/SepehrGhanbari/Ario/actions/runs/44573488145) completed successfully on #273: Windows reported 1,343 passed + 121 subtests, and the dedicated Linux cognitive-memory job reported 86 passed. This evidence applies to #273's exact tree only, not to this branch.

A two-file transplant is insufficient: the bridge depends on `source_monitoring.py` types and API; the task-finish count is exposed by `ario_cli.py`; and the tests/contracts preserve the behavior change and its limits. No such port is made here because those additional paths have not been approved. The dependency and exact evidence are recorded in [Issue #216 comment](https://github.com/SepehrGhanbari/Ario/issues/216#issuecomment-7169591766).

## 6. Remaining limitations and safety

- No independent snapshot origin, witness, or assessment is authenticated.
- No hostile-pickle safety is claimed.
- Direct `record_empirical_observation` callers are not authenticated by the #273 replay fix.
- No semantic truth, external execution, independent source custody, or privileged action authority is established.
- Historical `ACCEPTED/SUPPORTED` bytes and event records are not rewritten.
- `main`, the #321 parent branch, signer state, keys, TPM, Genesis, governance policy, and production systems are untouched.

`RESEARCH_ONLY / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE / NO_HISTORY_REWRITE` remain in force. GENESIS, TRUST_ACTIVATION, and PRODUCTION remain `NO_GO`.

## 7. Next bounded steps

1. Run exact-head Linux and Windows tests for this branch; preserve all failures and skips.
2. Review the snapshot gate and legacy resolver against negative controls, including malformed statuses and actual pickle restoration.
3. Only after explicit approval of the complete dependency set, port the existing #273 ledger-report and task-finish boundaries. Do not copy the whole #273 branch or create a duplicate architecture.
4. Keep the branch Draft/HOLD until exact-head CI and independent review are available.

## 8. Unverified JSONL imports on the #381 parent, 2026-11-26

The source is [9f0f4929828cf188904e3edf4c78f652a4c1667e](https://github.com/SepehrGhanbari/Ario/commit/9f0f4929828cf188904e3edf4c78f652a4c1667e). Its immediate parent is `38204d103525fe6bf257c778dde78d08e5706496`, on the #321 stack. The source commit changes the bridge and its existing test file. The alias and active-restore modules/tests have the same Git blobs as the published parent. [Issue #216 checkpoint](https://github.com/SepehrGhanbari/Ario/issues/216#issuecomment-7176492123).

An imported completed step on the parent appeared as `RECORDED` in the graph but `VERIFIED_EMPIRICAL` in the source registry. Imported task goals appeared as internal hypotheses. The new path registers both as `EXTERNAL_TESTIMONY / EXTERNAL_ASSERTION`. A row naming the founder, a claimed evidence type, a permitted tool name or a repeated line provides no independent evidence. The configured tool filter still applies. The historical `ATTR-STEP-` line-hash and `ATTR-HYP-` goal identifiers keep their original formulas. Registration stops on a collision with an existing different attribution. Earlier rows of a multirow import may already have been recorded. This is a per-record boundary.

| Check on this source | Observed result |
| --- | --- |
| Two entry orders, repeated import, founder label, custom tool filter, replay into an old empirical ID | Source and graph stayed within their expected states. The old empirical record and its revision history survived the collision. Input bytes were unchanged. |
| Legacy aliases and trusted synthetic snapshots | Nine stdlib cases passed on a fresh clone, including ambiguous and unique v1 aliases, exact v2 lookup, an old single-winner index, and active restore of an elevated or malformed status. Three bridge import cases passed in the same clone. |
| Local Windows CPython 3.13.16 | Both full focused files together had 19 passes, eight passing subtests and one fixture error. Windows refused to create the test symlink (1314) before the reader ran. A second run explicitly deselected that case. Another 39 source-monitoring, consolidation and replay tests passed. |
| Exact-source GitHub regression | Linux 3.13 and advisory 3.14 each had 1,956 passed, seven skipped, two xfailed and two warnings. Windows 3.13 had 1,954 passed, nine skipped, two xfailed and two warnings. Each had 281 passing subtests. The dedicated cognitive-memory job reported 117 passed with two passing subtests, and the seeded rerun had three passes. [Run 45713995707](https://github.com/SepehrGhanbari/Ario/actions/runs/45713995707) |
| Exact-source published TXT restoration | All ten jobs succeeded. [Run 45713995700](https://github.com/SepehrGhanbari/Ario/actions/runs/45713995700) |

### Fresh checkout and offline tests

Git and Python 3.13 suffice for the following checks. Only the initial clone needs GitHub. Run in a new directory. Use only locally constructed pickle fixtures. Pickle can execute code before the engine checks the restored state.

```sh
git -c core.autocrlf=false clone --branch research/foundation-recovery-20261125 https://github.com/SepehrGhanbari/Ario.git Ario-recovery
cd Ario-recovery
git switch --detach 9f0f4929828cf188904e3edf4c78f652a4c1667e
git rev-parse HEAD
cd implementation
python -B -m unittest discover -s tests -p test_memory_legacy_resolution.py -v
python -B -m unittest discover -s tests -p test_ledger_memory_bridge.py -k import -v
```

For both full test files use `python -m pytest -q tests/test_ledger_memory_bridge.py tests/test_memory_legacy_resolution.py` after installing `requirements-research.txt`. A matching Python/platform wheel directory permits offline installation with `python -m pip install --no-index --find-links WHEEL_DIRECTORY -r requirements-research.txt`. A Windows host needs permission to create the symlink for the full local bridge suite. To compare with the original behavior in an expendable checkout, run the new bridge tests against the parent core. The parent gives empirical credit to a reported completed step, and a byte-identical historical empirical record can be reused on import. Both violate the new tests.

### Which branch to resume

| Workstream | Pinned checkpoint and remaining decision |
| --- | --- |
| Memory | #210 / #321 supply the memory engine. #261 supplies a read-only support view. #271's authority-history research is retained in #273 at `1063bdabcd41b4d1562984c736000cb8689cf41b`. #319 is a separate synthetic admission fixture. The wider #385 at `22f54103d9b1dadf2c354eac495400095633bef0` includes a different `ATTR-LEDGER-` identity and an inert task-finish path. A Git merge-tree rehearsal with the source above reported a conflict in `implementation/core/ledger_memory_bridge.py`. Before combining them, specify how both ID families resolve with collision tests. #381 still evaluates prospective cues from a finish row. A direct empirical API caller's independence and the truth of an imported report remain UNKNOWN. |
| Signer and custody | [#171](https://github.com/SepehrGhanbari/Ario/issues/171) traces the R51 test-oracle correction, R58–R60 references and disposable R62 isolation. [#198](https://github.com/SepehrGhanbari/Ario/issues/198) distinguishes an existing custody path from an exclusive final holder. [#239](https://github.com/SepehrGhanbari/Ario/issues/239) retains the G8 crash/replay run and G9 shared-admin counterexample. At G9 source `6e83d5038744b23ad91894f1bfd1f115d80c250f`, rolling back both retained histories allowed another disposable native signature. Individual R58 archive bytes were not revalidated in this pass. Independently controlled signer use, veto over a common administrator, and an independent latest floor remain UNKNOWN. |
| Cold discovery and A15 | #346 at `bfe66cbba60a25086773d1790284eb97e3a6202a` had 24 local broker tests pass, including a test expecting the joint-rollback failure. #369's historical delayed read is [run 45464974056](https://github.com/SepehrGhanbari/Ario/actions/runs/45464974056). #374's publish/discover/reveal jobs succeeded in [run 45653011056](https://github.com/SepehrGhanbari/Ario/actions/runs/45653011056). Its local offline bridge fixture on Windows refused to run with `HOLD_POSIX_REQUIRED`. #375's publish/discover/audit jobs succeeded in [run 45656683810](https://github.com/SepehrGhanbari/Ario/actions/runs/45656683810). Continue retained-range work at #379, portable recovery at #380 (`d30c8de56f4de2e63b390ff541bac8a5cc1bfd29`), and the read-only #346 adapter at #382. Recovering an authentic historical commitment leaves latestness, durable independent custody and future availability UNKNOWN. |
| Governance and recovery | On main `5ce5d4fb69a1e0fb97fd8dc4db9ea4267d377b14`, public branch rules listed code-owner review and a strict required regression check. Stale-review dismissal and last-push approval were disabled. The separate classic-protection endpoint returned HTTP 401 to the public read. #306 and #348 precede the Git-object verifier on [#386](https://github.com/SepehrGhanbari/Ario/pull/386) at `70887af4cffdb7955a16e511203d12aeb4c941e6`. Prior offline runs in this investigation passed 137 Guard V2 cases at `4ca8ba373cc687252bc06462986e5323f75a7bcc` and 28 integrity-gate tests using exact main Git-blob bytes. A Windows export with converted line endings initially failed all 28 helper-pin checks. Use original blob bytes for byte-pinned recovery. Independent reviewer control, prevention of every merge bypass and authenticated succession remain UNKNOWN. |

The existing [stewardship policy](https://github.com/SepehrGhanbari/Ario/blob/5ce5d4fb69a1e0fb97fd8dc4db9ea4267d377b14/GOVERNANCE.md) leaves official succession unadopted. A recovery copy permits continued examination. It conveys no Owner signing authority. Independent admission policy, a canonical future ID migration, independently administered latest-state retention and protected activation remain separate decisions. MEMORY ≠ TRUTH. CLAIM ≠ PROOF. REVISION ≠ ERASURE. SELF-MODEL ≠ SELF. UNKNOWN IS VALID. GENESIS = NO_GO.
