# Ario claim-card lab v0.1 — a research register, not a truth engine

**Dated:** 2026-11-15 · **Status:** PROPOSED / research-only / no authority · **Baseline main:** `805e3660c71bf1f707120862148531e6094b4a99`  
**Issues:** [#195](https://github.com/SepehrGhanbari/Ario/issues/195), [#205](https://github.com/SepehrGhanbari/Ario/issues/205), [#176](https://github.com/SepehrGhanbari/Ario/issues/176), [#198](https://github.com/SepehrGhanbari/Ario/issues/198).  
**Purpose:** turn documented contradictions into *falsifiable*, versioned cards without upgrading a smooth narrative, consensus, a DOI, a hash, or green CI to proof.

## A. Card contract and evidence boundaries

Each card has immutable-at-publication **card ID and version**, scoped claim, evidence class, independently falsifiable prediction, explicit failing observation and **threshold**, fixture/control, source URL/commit/blob, runner version, independent oracle requirements, recorded result including negative/UNKNOWN, and follow-up reference. A card is **not** an accepted claim. Its next revision must **append** a superseding dated card; never silently rewrite an earlier observed result.

Distinguish `DIRECT_SOURCE_READ`, `HISTORICAL_REPORTED_EXECUTION`, `CURRENT_EXECUTION`, `INDEPENDENT_REPRODUCTION`, `PROPOSAL`, and `UNKNOWN`. The last three are **not interchangeable**. A test harness and a result selected by one author are not independent testimony. A passing test only supports the precise executed predicate under its inputs; the same human controlling storage, oracle, rules and publication remains **an unresolved external honesty/custody limit**.

## B. Card C25-DOI-01 — publication status ≠ scientific correctness

- **Historical negative:** [C24 ledger](https://github.com/SepehrGhanbari/Ario/blob/805e3660c71bf1f707120862148531e6094b4a99/papers/creation-without-sovereignty/2026-11-11/evidence/CLAIM_EVIDENCE_LEDGER.md) (blob `133d32e61c2dcb0f57316d5f35594b4ff5bae85d`) says `NOT YET TRUE` for a DOI **as of the earlier November 11 draft**. This is a historically dated statement; do not overwrite or retroactively mark it a lie.
- **Later source observation:** [dated Zenodo publication record](https://github.com/SepehrGhanbari/Ario/blob/805e3660c71bf1f707120862148531e6094b4a99/papers/creation-without-sovereignty/2026-11-11/zenodo/ZENODO_PUBLICATION_RECORD_2026-11-12.json) (blob `46089ab1966a977f6051df6649027fc485689f77`) explicitly records publication and DOI `10.5281/zenodo.24136175` for **Creation Without Sovereignty**. The adjacent README states the original PDF checksums and unreviewed working-paper status.
- **Predictions and thresholds:** a fresh independent Zenodo/DataCite resolver check should return the same DOI, title and published state. Any DOI or title mismatch (**≥1**) is a negative result, not an editorial correction of C24. DOI existence does **not** satisfy the separate hypothesis “paper's scientific argument is correct”; that proposition remains `UNKNOWN / NOT TESTED` pending evidence appropriate to each empirical or philosophical claim.
- **Current classification:** `REPOSITORY_PUBLICATION_RECORD_PRESENT`; live resolver revalidation in this card's GitHub preparation **NOT VERIFIED**, scientific correctness **UNKNOWN**. The progression C24→C25 is an append-only correction in this *new* research card, not a modification to the dated original ledger.

## C. Card TB004-INCIDENT-01 — event identity must precede interval intersection

- **Scoped prediction:** when reports `epoch EP: [5,30]` and `root ROOT: [20,25]` explicitly bind to the **same verified incident/onset variable**, the common onset interval is `[20,25]`; a capture at 10 is temporally prior, **subject to all other gates**. When incidents differ, the early interval still permits compromise at sequence 5; adding a later independent incident must **not** promote capture 10. Unbound identity must not silently be treated as one incident.
- **Historical reported negative:** [#176](https://github.com/SepehrGhanbari/Ario/issues/176) documents an actual earlier local execution of the original TB-004 v0.1 and v0.2 implementations: capture 10 / retention 12, initial `SUSPENDED`, then `CONDITIONALLY_USABLE_FOR_NAMED_COMPARISON` after adding a second [20,25] report. This is **HISTORICAL_REPORTED_EXECUTION**, **not** an independent re-run here. It is adverse **only under the proposed distinct-incident interpretation**; existing single-shared-onset contract is still undecided.
- **Falsifier and tolerance:** in a *versioned proposed incident-aware* evaluator, **one** case (`≥1/12`) where a distinct relevant earlier incident is promoted solely by a later observation is a FAIL. A same-onset incompatible triple intersection must return explicit contradiction/UNKNOWN rather than an affirming verdict. No incident-id field → `UNKNOWN_UNBOUND`, not proof that two incidents are distinct.
- **Status:** `PROSPECTIVE_FALSIFIER_REGISTERED / ORIGINAL_CONTRACT_UNDECIDED / NEW_RUNTIME_NOT_EXECUTED`. Related Draft [#178](https://github.com/SepehrGhanbari/Ario/pull/178) remains research/HOLD.

### Twelve *proposed, not executed against Ario* temporal controls

These are **design expectations for the temporal gate only**, not expected global evidence-admission results. All captures at sequence 10. `TEMPORAL_CLEARED` means *only* that capture predates the lower bound of every relevant explicitly bound incident; it does not approve the artifact.

| ID | Relevant incident assignments and onset windows | Proposed temporal verdict | Why |
|---|---|---|---|
| I01 | Same `I1`: [5,30], [20,25] | `TEMPORAL_CLEARED` | Intersect to [20,25] |
| I02 | Different `I1`, `I2`: [5,30], [20,25] | `NOT_CLEARED` | Earlier I1 can start at 5 |
| I03 | Two reports, incident identity missing | `UNKNOWN_UNBOUND` | No basis to intersect |
| I04 | Same `I1`: [5,8], [20,25] | `UNKNOWN_CONTRADICTORY` | One onset cannot be in both |
| I05 | Different `I1`, `I2`: [5,8], [20,25] | `NOT_CLEARED` | Distinct nonoverlap is possible; earlier matters |
| I06 | Same target `EP`, different `I1`, `I2`: [5,8], [20,25] | `NOT_CLEARED` | Group by incident, **not by target** |
| I07 | Same `I1`: [5,15], [10,25] | `NOT_CLEARED` | Earliest possible onset 10 equals capture |
| I08 | Same `I1`: [12,20], [15,18] | `TEMPORAL_CLEARED` | Earliest possible onset 15 exceeds capture |
| I09 | Same `I1`: [5,15], [10,25], [20,30] | `UNKNOWN_CONTRADICTORY` | Pairwise overlap but empty triple |
| I10 | Distinct targets `EP`, `ROOT`, but same established `I1`: [5,30], [20,25] | `TEMPORAL_CLEARED` | Shared incident, not just shared administrator |
| I11 | Duplicate same-`I1` reports [5,30], [5,30] | `NOT_CLEARED` | Duplicates cannot improve the bound |
| I12 | Relevant `EP/I1` [20,25] plus explicitly out-of-scope target/incident [2,8] | `TEMPORAL_CLEARED` *for EP only* | Disjoint scope must be authenticated, not presumed |

**Held controls:** reorder invariance; missing/typed incident IDs; forged binding; refuted onset; target scope; equal-boundary capture; two incidents on the same target; triple intersection; strict original-source comparisons. Any pass in self-written development fixtures is **not** a blinded benchmark.

## D. Card XERJ-SEARCH-01 — a matching hit is not an independent canonical ledger read

- **Risk prediction:** a search engine can return a correct-looking `epoch` or canary while searching an unintended index/snapshot. A second read of `_source` **from that same engine** is correlated, not a second witness; a hash comparison against a caller-provided map checks only those declared bytes.
- **Falsifier:** after feeding two **different** synthetic canonical collections with deliberately repeated epoch IDs and isolated canaries, report `CANONICAL_MATCH` **only** when the authenticated target index/snapshot identifier and all returned IDs re-read from a separately controlled canonical Ario ledger match. Any single false `CANONICAL_MATCH` (**≥1**) is a FAIL. No authenticated ledger reader → `CANDIDATES_ONLY` / `UNKNOWN` rather than admission.
- **Adversarial parser cases:** `k=3, hits.total=2, rows=1` must not become exact/full completion; `relation=gte` is not `eq`; wrong index, mismatched snapshot hash, duplicate IDs, and incomplete results fail closed. Old behavior described in [#205](https://github.com/SepehrGhanbari/Ario/issues/205) and Draft [#185](https://github.com/SepehrGhanbari/Ario/pull/185) is **SOURCE-CRITIQUE / NOT_RERUN**, not a measured live-XERJ exploit.
- **Status:** `PROPOSAL / ENGINE_NOT_RUN / INDEPENDENT_CANONICAL_ORACLE_NOT_INSTALLED`.

## E. Companion protocol for #198 — H_E is not H_S

- **Existing H_E contract:** evidence of an eligible custody *path*, potentially with documented off-path branches. It does **not** assert that the endpoint is the latest exclusive holder.
- **Proposed H_S contract:** unique holder for an exclusive token at a frozen snapshot after processing *all* in-scope transfers; missing event surface, forks, contradiction, separate custody compromise, or unsupported `complete_transfer_surface` must not yield affirmative final-holder status.
- **No retroactive bug claim:** the [18 publicly authored development cases](https://github.com/SepehrGhanbari/Ario/pull/199) are not independent, blind, or a test of truth; even six comparator disagreements distinguish **different contracts**, not necessarily H_E bugs.
- **Before any 240-case blind holdout:** strictly reject boolean strings such as `"false"` and nested truthy objects; validate declared completeness through independent inventory/reconciliation or explicitly return UNKNOWN; freeze runner/dataset/label-key commitments and a matched-information H_E comparator; separate controller/source/custody axes; use an independently administered unseen label set, with complete negative and UNKNOWN counts. **Threshold:** ≥1 knowingly false snapshot-final affirmation is a failing safety target, while always-UNKNOWN must be scored for coverage, not celebrated.
- **Status:** `H_S_UNADOPTED / PUBLIC_DEVELOPMENT_ONLY / HOLDOUT_NOT_EXECUTED`. Existing v0.1 files must not be modified merely to make the new oracle's examples green.

## F. Negative record retention and acceptance gates

1. Register an execution as `NOT_RUN` until actual raw inputs, executable SHA, environment, timestamp, runner output, counts (including failures/UNKNOWN), and independently managed labels are linked. A prior issue report is `HISTORICAL_REPORTED_EXECUTION`, not newly measured success.
2. Append negative rows to a dated follow-up without deleting previous errors or renaming the criterion after seeing results. Corrections carry `supersedes`, prior hash and reason. Git ancestry is reviewable history; **a single owner with publishing/admin keys can still rewrite that history**. External custody/archival attestation remains unproven.
3. Require both false-affirmation and abstention/coverage metrics under fixed independent labels. Neither “all UNKNOWN” nor consensus between models wins by itself.
4. Never merge or activate [#133](https://github.com/SepehrGhanbari/Ario/pull/133), [#151](https://github.com/SepehrGhanbari/Ario/pull/151), Draft [#178](https://github.com/SepehrGhanbari/Ario/pull/178), Draft [#185](https://github.com/SepehrGhanbari/Ario/pull/185), or Draft [#199](https://github.com/SepehrGhanbari/Ario/pull/199) solely because these cards exist.
5. **Publication of this document has no runtime, signer, witness, trust, DOI-accuracy, evidence-admission, benchmark-performance, or policy activation effects.** The first independent confirmatory results remain to be collected and may be negative.

## G. Dated toy-oracle negative and correction — 2026-11-15

**Do not conflate this with a TB-004 implementation test.** After this *proposed* document was first committed as `1eb0595acfc2576199d9aed1f6df04814da2d2f3`, an author-controlled **V8 JavaScript toy decision function** was run on its twelve I01–I12 rows: 12/12 matched the author's own expected labels. A separate **zero-relevant-report** input then returned **`TEMPORAL_CLEARED`**. **NEGATIVE / FAIL:** the toy oracle vacuously approved a capture with no applicable reports. This finding remains recorded; it is **not an observed Ario bug**.

**Correction (not erasure):** require nonempty relevant-report set before considering bounds: when none exist return `UNKNOWN_NO_RELEVANT`. A fresh author-written **Python 3 toy oracle** was then executed **in an isolated local container**: **12/12 proposed table rows plus 4/4 adversarial checks PASS** (zero relevant, equal-boundary capture, invalid window and empty incident ID). Neither original nor corrected toy evaluates Ario source; both use author-written labels. The first 12/12 alone demonstrably failed to cover a safety edge case.

**Reproducer for the corrected toy logic (single standalone Python process; zero external imports):**

```python
def temporal(reports, capture=10):
    relevant = [r for r in reports if r[3] is True]
    if not relevant:
        return "UNKNOWN_NO_RELEVANT"
    if any(not isinstance(r[0], str) or not r[0] for r in relevant):
        return "UNKNOWN_UNBOUND"
    groups = {}
    for incident, lo, hi, _ in relevant:
        if type(lo) is not int or type(hi) is not int or lo > hi:
            return "UNKNOWN_INVALID"
        low, high = groups.get(incident, (float("-inf"), float("inf")))
        groups[incident] = (max(low, lo), min(high, hi))
    if any(low > high for low, high in groups.values()):
        return "UNKNOWN_CONTRADICTORY"
    return ("TEMPORAL_CLEARED"
            if all(low > capture for low, _ in groups.values())
            else "NOT_CLEARED")

rows = [
    ("I01", [("I1",5,30,True),("I1",20,25,True)], "TEMPORAL_CLEARED"),
    ("I02", [("I1",5,30,True),("I2",20,25,True)], "NOT_CLEARED"),
    ("I03", [(None,5,30,True),(None,20,25,True)], "UNKNOWN_UNBOUND"),
    ("I04", [("I1",5,8,True),("I1",20,25,True)], "UNKNOWN_CONTRADICTORY"),
    ("I05", [("I1",5,8,True),("I2",20,25,True)], "NOT_CLEARED"),
    ("I06", [("I1",5,8,True),("I2",20,25,True)], "NOT_CLEARED"),
    ("I07", [("I1",5,15,True),("I1",10,25,True)], "NOT_CLEARED"),
    ("I08", [("I1",12,20,True),("I1",15,18,True)], "TEMPORAL_CLEARED"),
    ("I09", [("I1",5,15,True),("I1",10,25,True),("I1",20,30,True)], "UNKNOWN_CONTRADICTORY"),
    ("I10", [("I1",5,30,True),("I1",20,25,True)], "TEMPORAL_CLEARED"),
    ("I11", [("I1",5,30,True),("I1",5,30,True)], "NOT_CLEARED"),
    ("I12", [("I1",20,25,True),("I2",2,8,False)], "TEMPORAL_CLEARED"),
]
assert all(temporal(r) == expected for _, r, expected in rows)
assert temporal([("I1",20,25,False)]) == "UNKNOWN_NO_RELEVANT"
assert temporal([("I1",10,20,True)]) == "NOT_CLEARED"
assert temporal([("I1",25,20,True)]) == "UNKNOWN_INVALID"
assert temporal([("",20,25,True)]) == "UNKNOWN_UNBOUND"
print("PASS: 12/12 proposed + 4/4 negative controls (toy, not Ario)")
```

**Remaining defects / independence limits:** the toy still **trusts** a caller-supplied `relevant` flag and incident IDs; a lying caller or excluded relevant report can falsify the conclusion. It also does not implement provenance authentication, source-version binding, missing targeted incidents, holder custody, trust, or signed evidence admission. Thus the toy's *self-consistency*, even after correction, is **not** a safety or correctness certificate. Genuine incident-binding semantics and independent holdouts remain `UNKNOWN / NOT_RUN`.
