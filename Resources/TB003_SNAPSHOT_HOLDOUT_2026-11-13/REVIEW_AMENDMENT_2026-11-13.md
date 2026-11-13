# ARIO TB-003 / PR #199 — adversarial review amendment (2026-11-13)

**Status:** authorized research-only input-validation correction. **NOT** an independent blinded benchmark, NOT production security certification, NOT a modification of existing TB-003 H_E semantics, and NOT an approval to merge PR #199.

## Scope, authorization and preservation

Owner authorization in the 2026-11-13 conversation explicitly covered:
- `Resources/TB003_SNAPSHOT_HOLDOUT_2026-11-13/blind_runner.py`: strict input parsing and validation before graph construction/evaluation;
- `Resources/TB003_SNAPSHOT_HOLDOUT_2026-11-13/test_reference_oracle.py`: public negative and integration-style regression tests;
- **new** `Resources/TB003_SNAPSHOT_HOLDOUT_2026-11-13/REVIEW_AMENDMENT_2026-11-13.md`: append-only explanatory evidence and limitations.

Historical backup branch: `backup/tb003-pr199-pre-value-schema-20261113-r1` at `2702869923b51444e04f3e068283e6a4b8d9bb8c`. Before modification, the two original blobs were compared byte-for-byte by Git blob SHA with the backup:
- runner: `8cc16112284c6742e590ca391f973f0f6649558c`
- public test: `008e621e2ea4418c538a15b629b1eccce2c15e82`

All previous commits and original issue/review comments remain preserved. `main`, `implementation/`, `reference_oracle.py`, `PREREGISTRATION.md`, `public_controls.json`, keys, trust policies, and governance remain unchanged.

## Primary failure (reproduced before this change)

The previous runner checked top-level and nested *key names* but did not enforce scalar value types. In Python, a non-empty dictionary such as `{"gold": false}` or string `"false"` is truthy, so supplying it as `common_control` could silently insert `CAN_WRITE` edges and change a verdict. Other malformed boolean, sequence, actor-ID and origin fields were also not fail-closed. This is a **defect in an experimental runner**, not a demonstrated live exploit or a defect in the original H_E evaluator.

Evidence records retained:
- [CodeRabbit finding](https://github.com/SepehrGhanbari/Ario/pull/199#discussion_r4565056037)
- [Adversarial follow-up and negative F1 result](https://github.com/SepehrGhanbari/Ario/pull/199#issuecomment-6859688587)
- [Issue #198 evidence update](https://github.com/SepehrGhanbari/Ario/issues/198#issuecomment-6859696092)

## Narrow remediation

The runner now validates each *unlabeled* challenge record **before loading the pinned baseline evaluator**, including:
- a bounded exact-schema JSON envelope, rejecting duplicate JSON keys and unexpected `gold` / `label` / `expected` fields;
- strict `type(value) is bool` for all six boolean flags, and bounded integer sequences excluding Python booleans/floats;
- valid bounded ASCII actor identifiers, rejecting all nine reserved graph-node IDs;
- exact `other_witness_custodians=["P2"]` within the expressly narrow fixed-B experiment;
- bounded, correctly typed transfer events and supported LAB/SELF origins;
- no repeated case IDs or compromised custodian IDs;
- 1–240 examples, bounded numbers of actors and transfer events; 240 is an **input-capacity limit**, not evidence that 240 independent cases were tested;
- fail-closed errors before passing malformed cases into `make_case`.

A regression in the existing `test_reference_oracle.py` checks negative mutations, duplicate JSON keys, ID collisions, the 240/241 boundary and whether malformed inputs are refused **before** loading the baseline evaluator. The original 18 public H_S assertions are retained, without changing their expected labels.

## What this does NOT solve

1. **Reference oracle orthogonal negatives:** the `reference_oracle.py` early returns may still obscure explicit common administrative control, shared storage or a compromised witness when final-holder state is MISMATCH/UNKNOWN. This is a separate semantic decision, not modified under the authorization.
2. **Baseline input parity:** H_S can use `complete_transfer_surface`, but original H_E's `ProvenanceCase` has no equivalent field; judging this asymmetry as a baseline bug is an experimental confound. A fair comparison needs revised, prospectively approved evaluation rules.
3. **Completeness is assumed, not authenticated:** `complete_transfer_surface=true` is an author/declarer premise. A hash of recorded fields does not establish that no relevant event was omitted.
4. **Witness-B limitation:** this v0.1 harness only permits a static direct-custody B held at P2. It cannot validate arbitrary two-witness histories.
5. **Blind validation NOT RUN:** the 18 public fixtures, mutation cases and repeated capacity inputs are developer-visible controls. No independent 240-case holdout, external adjudication or scientific performance conclusion is claimed.
6. **Prior negative result retained:** the F1 four-way direct-vs-one-hop fixture did not show the proposed custody-mode split. It remains a negative, limited result.

## Evidence interpretation and next gate

Record test commands, their actual exit statuses, current head SHA and CI separately in a follow-up PR comment; never backdate this file to claim a test was run before commit. Independent reviewers should reproduce *invalid-value rejection* and *clean/valid-case acceptance*, then inspect the other unresolved semantic and protocol gaps before any new holdout.

**HOLD:** no merge, no signing/trust activation, no main or implementation mutation. Preserve failure and revision history.
