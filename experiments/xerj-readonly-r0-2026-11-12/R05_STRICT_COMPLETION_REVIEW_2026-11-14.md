# R05 — XERJ research-only strict completion gate (14 November 2026)

**Status: IMPLEMENTED IN DRAFT PR #185; NOT MERGED, NOT PRODUCTION.**

## Authorization and preservation

This entry updates the original R4 proposal after the owner's explicit authorization to record exactly three files in PR #185. The base HEAD was `89ec8be96e15123ab75f98afd2a3ebb5cf3cdb20`. Before writing, the branch `backup/xerj-pr185-pre-r4-20261114-g185` was created at that exact commit and independently checked to have identical Git blob SHAs for the original adapter and both existing tests:

- `ario_xerj_readonly.py`: `c29f9fe8c6679a75f0f1d37948892fbb48554db5`
- `test_ario_xerj_readonly.py`: `5f4049602bc95a18050100e493e8c301f145f267`
- `test_wire_contract.py`: `e09ad85bf20f4f51b8bb5ef5355c2d167f75f53f`

The actual scope of this revision is restricted to:
1. `experiments/xerj-readonly-r0-2026-11-12/ario_xerj_readonly.py` — narrow fail-closed completion metadata validation under `require_completion_metadata=True`.
2. `experiments/xerj-readonly-r0-2026-11-12/test_r4_strict_completion.py` — new public synthetic negative controls.
3. This **new**, append-only review record.

No historical R0–R4 files are overwritten, no `main` merge, no changes to keys, trust, memory or any original epistemic contract. The earlier R4 research package and negative findings remain separately preserved.

## Implemented bounded behavior

The strict completion path applies **only** to the declared *one concrete index, one participating shard* XERJ rc.102 experiment:
- Zero shards with **or without hits**, nonexact expected shard configuration, failed/skipped shards, and early termination produce `RETRIEVAL_INCOMPLETE` with zero candidates and zero root labels.
- An exact `hits.total` smaller than the returned hit list is inconsistent and rejected. A `gte` lower bound of zero is not treated as an exact zero. An absent `hits.total` is not silently assumed to be zero; rc.102 may omit it under some request options.
- Other existing checks still reject missing/malformed metadata, unknown or foreign IDs, repeated IDs, local hash inconsistencies, incomplete searches, and invalid responses.
- The direct fixture parser without strict metadata is retained for historical test compatibility only; it is not the live-wire contract.
- All outputs remain `answer_authorized=false`, `trust_activated=false`, `source_independence=NOT_ESTABLISHED`.

The patch does NOT add or trust returned `_source`, nor does it add an index snapshot/epoch or a new provenance authority.

## Validation boundaries

Before commit, the exact patch source SHA-256 `7967b408192951c20b609a73ca5c67ce5ff74995b5ae56fb8a3e520a14e8baad` passed **41/41** original mock HTTP tests in a disposable Windows scratch and **7/7** new strict-completion unit tests in a separate development run. A separate, uncommitted version/epoch *toy* passed **10/10** synthetic tests. The historical **18/18** R3 offline cases were reproduced on the **unchanged original** adapter, not as post-commit integration evidence. New-head regression and GitHub CI are to be reported separately with their actual observed results.

Known earlier wrapper failures during scratch tests (PowerShell string anchor and stderr reporting) remain preserved in the research record. They were not failing Python test assertions.

**Not shown:** verification of actual indexed bytes, a trusted build manifest, a monotonic protected index epoch, defence against an engine that reports false but self-consistent search metadata, relevance of an otherwise valid retrieved record to a user's claim, or an independent hidden holdout. A provider GET or `_source` read from XERJ cannot independently attest XERJ's own searched bytes. The version/epoch design remains HOLD, outside this authorized patch.

## Reviewer disposition

The single-shard restriction is an explicit **study precondition**, not a general ES-compatible search contract. A healthy multishard response may legitimately be refused as outside the study's supported domain. The amended parser must not be called a production security certification.

For the latest CodeRabbit reasoning on zero shards, early termination, `hits.total`, frozen snapshot and the quarantine interface, see [CodeRabbit's R3 reply](https://github.com/SepehrGhanbari/Ario/pull/185#issuecomment-6878362730). Negative or contradictory CI evidence after this document is committed must be appended to the PR discussion, not rewritten here as though the gate passed.

**Disposition:** PR #185 DRAFT/HOLD. No merge, production activation, source independence inference, evidence admission, signer, Genesis, or trust activation.
