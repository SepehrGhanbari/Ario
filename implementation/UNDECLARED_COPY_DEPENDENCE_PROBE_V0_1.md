# ARIO-TB-UCD — Undeclared-Copy Dependence Probe v0.1

**State:** BOUNDED SYNTHETIC RESEARCH PROBE. Draft, not merged, no authority activated.
**Scope:** new module `undeclared_copy_dependence_probe.py`, new tests, this document. **No change to M0/core**, to existing experiments, or to any contract.
**Author note:** prepared by an AI contributor (Perplexity Computer) at the owner's open invitation. All claims below are limited to the synthetic runs reported.

## 1. Research question

M0 raises `EVIDENCE_INFLATION` when two items declared `INDEPENDENT` reach a **declared** shared root (shared observation reference or ancestry). This probe asks:

1. **Boundary:** If sources copy one another but declare disjoint roots, does M0 see the copying? (Expected: no. M0 audits declared structure.)
2. **Screen:** Can a truth-free statistical screen detect undeclared copying in synthetic data?
3. **Asymmetry:** Can such a screen be connected to Ario semantics so that it can **only weaken** declared independence (`INDEPENDENT → UNKNOWN`) and never promote it?
4. **Failure regimes:** Where does the screen mislead?

## 2. Synthetic model

- 200 items. The true value of every item is `T`. Each item has 10 false values `F0..F9`, chosen uniformly.
- `O`: original source, accuracy 0.55.
- `C1..C3`: copiers. Per item, each copies `O` with probability `copy_rate` (default 0.9); otherwise it draws independently at accuracy 0.55.
- `I1..Ik`: independent sources at `independent_accuracy`.
- Null worlds set `n_copiers = 0`. **`O` still exists there, as an ordinary independent source with accuracy 0.55.**
- Seeds are strings passed to `random.Random`, so results are stable across CPython versions (checked on 3.12, 3.13 and 3.14).

Every source declares `INDEPENDENT` and uses its own observation reference, so all roots are declared disjoint.

## 3. Screen (deliberately simple)

For two independent sources with accuracy `a` and `F` uniform false values, expected agreement is `a² + (1−a)²/F`. A pair is flagged when observed agreement exceeds that value at a **declared prior** `max_plausible_accuracy`, plus `margin` (defaults 0.8 and 0.10). Flagged pairs are merged into clusters with union-find. The screen **never reads ground truth**, and a test verifies this by corrupting the truth.

Output is labelled `INFERRED_DEPENDENCE_SIGNAL_NOT_EVIDENCE`. `downgrade_only()` maps flagged `INDEPENDENT` sources to `UNKNOWN` and leaves every other status unchanged.

"Screened vote" gives each inferred cluster total weight 1. "Oracle vote" does the same with the true clusters. Ties count as incorrect.

## 4. Results (20 seeds per world)

Default prior (0.8, margin 0.10):

| World | Naive vote | Screened vote | Oracle | Pair recall | False-positive pairs / trial |
|---|---|---|---|---|---|
| copier_majority (copy_rate 0.9) | 0.580 | **0.839** | 0.839 | 1.00 | 0.0 |
| null_no_copiers (8 independents incl. O) | 0.968 | 0.968 | 0.968 | — | 0.0 |
| null_high_accuracy (7 at 0.92 + O at 0.55) | 1.000 | **0.540** | 1.000 | — | **21.0** |
| weak_copying (copy_rate 0.5) | 0.734 | 0.738 | 0.886 | **0.01** | 0.0 |

Prior sensitivity (same seeds):

| Prior (a, margin) | copier_majority screened / recall | null_high_accuracy screened / FP per trial |
|---|---|---|
| 0.80, 0.10 | 0.839 / 1.00 | 0.540 / 21.0 |
| 0.90, 0.05 | 0.839 / 0.85 | 0.981 / 4.3 |
| 0.95, 0.05 | 0.601 / 0.07 | 1.000 / 0.0 |

M0, run read-only on item 0 of every trial: `EVIDENCE_INFLATION` was raised in **0 / 80** declared-disjoint runs. In a control with two items sharing one declared observation reference, it **was** raised.

## 5. Interpretation (inferences, not established facts)

- **Boundary confirmed in this model:** M0 does not see copying that is not declared. This is consistent with its contract ("screen only supplied declarations; never authenticate independence"). It is not a defect.
- **Undeclared copying is not harmless:** in the copier-majority world, naive counting of declared-independent sources falls to 0.58 accuracy, and the screen recovers the oracle level.
- **Agreement is not dependence:** with highly accurate independent sources the screen merges them into one cluster and **accuracy collapses (1.00 → 0.54)**. The downgrade-only rule prevents false *promotion*, but it does **not** make false positives free. They cost coverage and, in vote-based use, accuracy.
- **No prior is neutral:** a prior that removes false positives in the high-accuracy world (0.95) misses most copying in the copier world. The trade-off has to be disclosed and chosen by the owner, not hidden in a default.
- **Weak copying (50%) is essentially invisible** to an agreement-only screen.

These negative results are pinned in tests (`test_known_limitation_*`) so a future change cannot remove them silently.

## 6. Why Dong et al. matter here

Dong, Berti-Equille and Srivastava (PVLDB 2009) observe that the useful signal is **sharing the same *false* values**, especially rare ones, not agreement in general. Their algorithm alternates between estimating dependence and estimating truth, because each depends on the other. The failure in `null_high_accuracy` is exactly the case their false-value focus is meant to avoid: agreement on true values is expected from accurate independent sources.

**Proposed v0.2 (not implemented):** replace the agreement-excess heuristic with a false-value-sharing model in the spirit of Dong et al., keeping the downgrade-only contract. Pre-register the four worlds above, plus a copier-minority world, as fixed tests.

## 7. Prior-art addendum (complements `docs/research/ARIO_COMPARATIVE_EPISTEMIC_BOUNDARIES_2026-11-15.md` §2)

These families are not in the existing prior-art map. Listing them implies no priority, novelty or superiority in either direction.

| Family | Core idea | Relation to an Ario principle |
|---|---|---|
| Truth discovery with source dependence: Dong, Berti-Equille & Srivastava, PVLDB 2(1):550–561, 2009, [doi:10.14778/1687627.1687690](https://doi.org/10.14778/1687627.1687690) | A false value can spread through copying; dependence and truth are estimated together | *Copies ≠ independent witnesses* when lineage is **not** declared. This is the gap that M0's declared-lineage design leaves open. |
| Data incest / double counting in distributed fusion: e.g. survey in [Sensors, PMC5713506](https://pmc.ncbi.nlm.nih.gov/articles/PMC5713506/) | The same information reaching a fusion node through several or cyclic paths causes overconfidence. One remedy is tracking common predecessors in an information graph. | A mature engineering literature for *one rumor counted ten times*, including the failure mode of overconfident, inconsistent estimates. |
| AGM belief revision: Hansson, ["Logic of Belief Revision", SEP](https://plato.stanford.edu/entries/logic-belief-revision/) | Rational postulates for expansion, contraction and revision of belief sets and bases | AGM governs the *current* belief state. Ario's *Revision ≠ Erasure* adds a preserved history of prior states, closer to belief bases plus an append-only record. Worth stating explicitly. |
| Justification logic: Artemov & Fitting, ["Justification Logic", SEP](https://plato.stanford.edu/entries/logic-justification/) | Replaces "X is known" with an explicit term `t : X`, "X is justified by t"; justifications compose by application | A formal language for *Claim ≠ Proof*. The F15 composition firewall could be described as restricting which applications `s · t` are admissible. |
| Model collapse: Shumailov et al., *Nature* 631:755–759, 2024, [doi:10.1038/s41586-024-07566-y](https://doi.org/10.1038/s41586-024-07566-y) | Training on model-generated data causes irreversible loss of the original distribution | *Self-Claim ≠ Self-Evidence* at population and training scale. This is the macro-level analogue of verdict-as-evidence recycling (F11). |

**Verification level:** landing pages and abstracts were inspected on 2026-11-17. This is not a systematic review.

## 8. Reproduce

```bash
cd implementation
python undeclared_copy_dependence_probe.py          # summary table (20 seeds)
python -m pytest -q tests/test_undeclared_copy_dependence_probe.py
```

## 9. Explicit non-claims

No real source was examined. No independence or dependence was authenticated. No M0 behaviour was changed. The screen's output is not Evidence and must not be admitted as such. A passing test establishes only the behaviour exercised by that test under the reported conditions.
