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
- Codex previously reported 7 focused alias tests passing on Windows CPython 3.13 before the two new snapshot-admission tests were added. That earlier local result is not a result for the current head.
- **Current exact-head test status: NOT YET RUN.** A PR-triggered Linux/Windows CI run is required before any PASS claim.

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
