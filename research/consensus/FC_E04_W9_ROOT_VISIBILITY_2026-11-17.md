# FC-E04 — W9 source-pinned root-visibility probe (2026-11-17)

**Status:** DIRECT_W9_SYNTHETIC_TEST_EXECUTED / FULL_FC-E04_BLOCKED_MISSING_INTERFACE / DR-MEM-216=HOLD / RESEARCH_ONLY / NO_MERGE / NO_PRODUCTION / NO_TRUST_ACTIVATION.

## Exact code provenance

- Execution: disposable ChatGPT scratch, CPython **3.13.5**; no Ario real ledger, local Windows device, network tool runner, memory or keys accessed.
- Existing research W9 source: `research/consensus/w9_bounded_receipt_contract.py` pinned to PR #242 commit `f00607a44f747507940c4997ed983d5edc5f9fdc`.
- Verified W9 Git blob (actual bytes vs repository): `f795065ce06d88c2ca017270f5036eb028029220`.
- New **additive, read-only** test on this branch: [test_fc_e04_w9_root_visibility.py](./test_fc_e04_w9_root_visibility.py). Source Git blob `7aad9fa180621bbf695fe881e5334b26b1c10e5b`, SHA-256 `e077e8fe269bd8417dd7e2d9720414c7c9e8d57cbdb0bb4d8ae9b02d75e173d7`.
- Run: `cd research/consensus && python -B test_fc_e04_w9_root_visibility.py`.
- Observed local output: **16/16 explicitly hand-designed case assertions passed**, process exit 0. These are 16 tests of the present W9 **declared-receipt contract**, not 16 independent-world validation successes, or claims about deployed Ario.

## Primary differential

| Case | Reports | Primitive roots stipulated in *test-only fixture* | Actual W9 result |
| --- | ---: | ---: | --- |
| 01 | 1 | 1 | `DECLARED_MATCH` |
| 02: same root relabeled | 2 | 1 | `DECLARED_MATCH` |
| 03: two purported fresh roots | 2 | 2 | `DECLARED_MATCH` |
| 04: ancestry unavailable | 2 | UNKNOWN | `DECLARED_MATCH` |
| 05: eight report IDs, one root | 8 | 1 | `DECLARED_MATCH` |
| 06: four reports, two roots | 4 | 2 | `DECLARED_MATCH` |
| 12/13: new root/derivation key | 2 | 1 | `UNKNOWN/BAD_RECEIPT_SCHEMA` |

Other controls (07–11, 14–16) check duplicate IDs, upper bound of eight, disagreement, contradiction, cross-target scopes, relabeling, bad hash and empty receipt set. Existing W9 fail-closed guards behaved as designed.

**Important interpretation:** W9 does not accept primitive-root or derived-from metadata in its input schema. The root labels in this experiment exist only in the test harness and are NEVER passed to W9. W9 does **not** claim to determine root independence, and `DECLARED_MATCH` says only the self-reported bytes match the narrow toy `FILE_EXISTS` predicate. It does **not** mean a second independent root was credited. Thus this is an observed **capability/interface boundary**, **not a confirmed W9 security bug** or full FC-E04 RED.

## Next falsifiable gate (not implemented / not run)

Design an **explicitly versioned, read-only recognition-to-final-decision interface**, if and only if separately approved for research, so the same immutable input evidence includes: (a) source ancestry and its custody/uncertainty, (b) a pinned recognition receipt, and (c) a final per-claim evidence-independence assessment. Then test with matched single-root-vs-two-root interventions, missing/forged lineage, same-text different-root controls, and same-root different-aspect extraction. Crucially, counting unique declared IDs or hashes is NOT independent custody; common ancestry does not imply zero incremental information; proven root separation alone does NOT guarantee full statistical independence or truth.

Before an evidence `SUPPORTED_IN_SCOPE` label is allowed, require distinct authorization and adversarial review of **source custody, relevance to claim, scope and temporal validity**, preserving append-only V1 histories and `UNKNOWN`. Never automatically promote from W9 `DECLARED_MATCH`.

Relevant research: [Epistemic Sybil Resistance](https://arxiv.org/abs/2609.01873), [Replication or Corroboration?](https://arxiv.org/abs/2610.36151), [Recognizing Study Lineage Is Not Enough](https://arxiv.org/abs/2610.23721).

No independent reviewer or external blind oracle has checked the new fixtures; no production CI or exact-head end-to-end Ario behavior is claimed here. No source/memory/ruleset/signer/trust changes and no merge authorization.
