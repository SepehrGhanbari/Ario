# W12 — Native Node replay and mutation-test audit of W11 temporal provenance

**Date:** 2026-11-17
**Status:** `EXACT_NATIVE_REPLAY_PASS / 14 SELECTED_MUTANTS / 10 KILLED_BY_W11 / 4 SURVIVED_W11 / 4 KILLED_BY_6_NEW_CONTROLS / EXTERNAL_ORACLE=NOT_ESTABLISHED / RESEARCH_ONLY / HOLD`.

## Plain-language summary (for the owner)

The prior W11 green result was genuine but **incomplete**. On an exact byte-matched W11 source, 14 deliberately defective variants were run. The original 36 tests rejected **10**, but **4** defective variants still reported all 36 original tests passing. Six additional tests were then written; the original unmodified code passed all six, and the four previously surviving variants were **each rejected** by at least one new test. This strengthens an isolated **research harness**, not Ario's deployed agent or a protected memory/signer interface.

No source file on `main`, published historical record, signer, real ledger, permissions, production service, or automation was changed.

## 1. Exact-source reproducibility — actually executed

**Original Ario W11 file:** [`research/consensus/w11_temporal_origin_no_history_promotion_lab.js`](w11_temporal_origin_no_history_promotion_lab.js), Git blob SHA-1 `63bde301e7f061945dbd2fb43954e817d2182fa6`. Its 12,479 exact bytes were reconstructed into a **disposable** isolated runtime and verified by `git hash-object`. Raw SHA-256 `a32c7632ccdd500efa4dad9cefeb91c35985a0fb494fc2497650918a320eb39c`. No GitHub source file was edited.

Native **Node.js v22.16.0** executed this *exact file*, produced `36/36` self-authored expected outcomes, and the entire serialized stdout had Git blob `8950907e7c2c606493f1aa5806d0487957dc3e7d` — **exactly matching the original committed W11 result JSON**. This is a reproducibility result for the earlier test program, not independent authorship, hidden expected answers, verified source custody, or a real agent security guarantee.

The mutation tests used [`w12_mutation_audit.py`](w12_mutation_audit.py), exact locally executed source Git blob `873d12292f79de2a3066aa3818deec6c145a1408`, which checks both original source and output Git blobs before doing anything. Only **temporary local JS copies** are changed; source and output are not overwritten. Every mutation is a unique, checked substring replacement and is run under a bounded Node subprocess. [`W12_MUTATION_RESULTS_2026-11-17.json`](W12_MUTATION_RESULTS_2026-11-17.json) includes the SHA-256 of each mutant source, first failed original case and later targeted control. Its exact original generated Git blob is `72a029a679bd9d12946cc9f4c07fd223f599b137`.

## 2. Empirical test-sensitivity results

| Deliberate synthetic defect | Old W11 suite | New test and exact line under challenge | Interpretation |
| --- | --- | --- | --- |
| M11: replace *all derived* root types with `EXTERNAL_PAGE` | **SURVIVED** all 36 | `P01_MERGED_ROOT_TYPES`; W11 source line 22 | Earlier tests checked presence of one expected type but did not assert full union of mixed-origin parent types |
| M12: keep just the first parent root ID on merge | **SURVIVED** all 36 | `P02_MERGED_ROOT_IDS`; line 21 | Source ancestry can silently disappear from a multi-parent derivation while unrelated permission checks still pass |
| M13: label `READ_SUMMARY` as `DATA_ONLY` even for nonlocal destination | **SURVIVED** all 36 | `P03_REMOTE_READ_NOT_DATA_ONLY`; line 53 | Previous suite had benign local read but omitted the matched negative nonlocal variant; **no actual external effect** exists in W11 |
| M14: remove typed/bounded `ttl` validator | **SURVIVED** all 36 | `P04_INVALID_TTL_REJECTED`; line 31 | Earlier suite tested expiry at valid TTL, not rejecting an ill-typed or out-of-range simulated grant |
| M01–M10: no-grant, revoked/expired grant, wrong principal/recipient/resource/operation, UNKNOWN origin, history as grant, all-derived USER | **KILLED** by W11 original cases T01/T15/T20/T18/T12/T17/T19/T10/T04/T36 | Existing tests already guard these *chosen* code changes in the toy | Do **not** inflate 10/14 into a universal security percentage |

The new [`w12_targeted_controls.js`](w12_targeted_controls.js), exact executed/public Git Blob `725c65ea437add425dc90867db54dbaf9b07ed6a`, adds **six** cases. In addition to the four gap-closing negatives P01–P04, **P05** confirms a genuine local read remains `DATA_ONLY`; **P06** confirms a new precise synthetic grant remains only `ELIGIBLE_FOR_SEPARATE_GATE`, with `authority=NOT_ESTABLISHED` and `external_effects=0`. The unchanged W11 passed all six; each of the **four** old survivors failed a corresponding W12 check.

**Measured statement:** `14/14` selected mutants were killed by W11+W12 *combined*, but mutants, test inputs, expectations and compiler assumptions were all **selected by the same researcher**. This must **not** be described as a blind benchmark, generalized 100% reliability, or production-grade authorization.

## 3. Review/reproduction instructions

Requirements: Python 3, Node 18+ (tested v22.16.0), exact W11 source file in the same directory as the two W12 tests. No external services or network are required for executing the tests once the research branch is checked out.

```sh
python research/consensus/w12_mutation_audit.py > /tmp/ario-w12-results.json
# It must verify old W11 script/output hashes first and report:
# original_replay: 36/36 exact published output
# killed: 10, survived: 4, survivors_killed_by_targeted: 4
# new_targeted_positive_negative_control_count: 6

# Run the six extra controls directly; no need to edit published W11:
cat research/consensus/w11_temporal_origin_no_history_promotion_lab.js \
    research/consensus/w12_targeted_controls.js > /tmp/ario-w12-combined.js
node /tmp/ario-w12-combined.js
# Original W11 JSON plus a final 'W12_RESULT=' line with count: 6.
```

**Caution:** If the W11 source or baseline JSON changes legitimately, the current W12 pins will **refuse to run**. Review the code diffs and version the experiment rather than silently updating hashes. The Python mutation harness intentionally requires a real Node executable; no extra npm dependencies or device/network calls are needed.

## 4. Separate limitations the mutation score cannot resolve

1. The test harness itself creates source labels and grants. A malicious or compromised **label issuer** could forge `USER_REQUEST` origins or mint a `SIMULATED_USER_GRANT`; W11/W12 do not authenticate either. None of these tests prove **external provenance**.
2. A single mutable in-memory map and append-only array is neither **rollback-resistant** nor an independent observer. The lab has no true concurrent revoke/authorize schedule, no authenticated wall-clock, no crash persistence.
3. W11's `ELIGIBLE_FOR_SEPARATE_GATE` is *not* permission. It returns `authority=NOT_ESTABLISHED` and zero real effects. No tool authorization was executed, no real Ario main agent invoked.
4. Source identity (Unicode/casefold/path aliases, email recipient normalization) remains exact-string matching. Stronger canonicalization must be scoped to real external identities; do not silently merge distinct users or paths.
5. Test mutations were targeted around one model's hand-authored code, not a randomized or separately adjudicated external audit. A clean mutation score for **these fourteen choices** is not a security proof.
6. Literature support (SARA [arXiv:2608.27146](https://arxiv.org/html/2608.27146), CaMeL [2503.18813](https://arxiv.org/html/2503.18813), PACT [2605.11039](https://arxiv.org/html/2605.11039), MemoryGraft [2512.16962](https://arxiv.org/abs/2512.16962)) is original *author-reported* evidence, not empirical confirmation of this program. The [W11 reviewer packet](W11_PRIMARY_SOURCE_AND_INDEPENDENT_REVIEW_PACKET_2026-11-17.md) lists exact sections and limitations; no need to reprint provider texts.

## 5. Decision for human/independent reviewers

**`RESEARCH_ACCEPT`** independent native replay result and new test coverage on bounded synthetic program; retain the four former **SURVIVED** labels in historical evidence and append these new results rather than erasing them.

**`NEXT_TEST`** an external proof-of-origin issuer and out-of-band grant authority with pre-sealed adversarial cases; then simulate independent history rollback, concurrency, one-sided revocation, forged envelope, value aliases, benign dynamic object IDs. Compare **false acceptance** and **false rejection** separately.

**`NO_GO`** changes to Ario memory status `ACCEPTED`, source IDs, actual action dispatcher, external receipts, ruleset, signer, trust activation or `main` from this synthetic test alone. Keep [#216](https://github.com/SepehrGhanbari/Ario/issues/216) on protected HOLD, [#259](https://github.com/SepehrGhanbari/Ario/issues/259) open until an independent reviewer posts exact counterevidence, and [PR #242](https://github.com/SepehrGhanbari/Ario/pull/242) DRAFT/HOLD.

**Key research integrity statement:** `TESTS_PASS != SYSTEM_IS_SECURE`; `A MEMORY HISTORY ENTRY != INDEPENDENT AUTHORIZATION`; `A REPRODUCED SOURCE BLOB != INDEPENDENT SOURCE CUSTODY`.
