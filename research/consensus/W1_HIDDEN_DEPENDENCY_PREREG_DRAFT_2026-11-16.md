# Ario W1 — Hidden-dependency sensitivity: research handoff

**Prepared:** 2026-11-16  
**State:** `RESEARCH_ONLY / LOCAL_DEVELOPMENT_CONTROLS / NO_INDEPENDENT_ORACLE / NO_BENCHMARK_RESULT / HOLD`  
**Protected boundaries:** `main`, signer, governance, memory admission, Ruleset, M0 authorization, PR #185 unchanged.

## Evidence inspected

- Repository: `SepehrGhanbari/Ario`, `main` commit `2e7f83c6c7518012bed7fedfb12103ce9b7222ea` at inspection.
- Research branch: `research/consensus-sprint-20261116`, four documentation commits ahead of main, no behind commits at inspection. Previous reported head `283f24f7cc0cd7603bdec40af2509f110020cca4` exists.
- Source evaluator: [`implementation/witness_provenance_experiment.py`](https://github.com/SepehrGhanbari/Ario/blob/2e7f83c6c7518012bed7fedfb12103ce9b7222ea/implementation/witness_provenance_experiment.py), Git blob SHA1 `4faf010d73219af63c254097e9c135da68d60078`.
- Contract and 26 public synthetic controls: [`WITNESS_PROVENANCE_EXPERIMENT_V0_1.md`](https://github.com/SepehrGhanbari/Ario/blob/main/implementation/WITNESS_PROVENANCE_EXPERIMENT_V0_1.md) and `implementation/tests/test_witness_provenance_experiment.py`.
- Existing [draft PR #199](https://github.com/SepehrGhanbari/Ario/pull/199): different **H_S snapshot-final custody** semantics, an independent holdout still unrun. The present W1 inquiry is about **false graph completeness / hidden root**; the same corpus should not silently be treated as a benchmark for both tasks.
- [Consensus study protocols](https://github.com/SepehrGhanbari/Ario/blob/research/consensus-sprint-20261116/research/consensus/EXPERIMENT_PROTOCOLS_2026-11-16.md): W1 is draft, not pre-registered.

## Critical distinction and null hypothesis

Ario TB-003 evaluates **declared, controller-supplied** laboratory facts. `LAB_CONDITIONALLY_SEPARATE` and `LAB_CONDITIONALLY_DISTINCT` are conditional statements about a supplied graph with completeness flags. They are **not** unconditional statements about the external world, verified independence, or historical truth.

**H0 / expected limitation:** If a common root or origin exists in the latent world but is absent from a graph marked as complete, the current graph evaluator alone cannot discover that omitted fact. A conditional structural verdict under those *false premises* is not automatically a code defect; unconditional downstream promotion would be the risky mistake.

**Competing testable hypothesis:** Additional externally authenticated controller/source inventory and a type-safe downstream gate can reduce false *unqualified* independence endorsements, subject to a specified authenticity threat model. This is **not** implemented or proven.

**Three separate scores must be reported:**

1. `contract_consistency`: does the evaluator classify relationships *as represented* in the provided graph?
2. `input_fidelity`: does the represented graph cover the actual controller/source relationships according to an independently adjudicated hidden oracle?
3. `downstream_claim_safety`: does any consumer promote a conditional laboratory finding to unqualified corroboration, evidence admission, or effect authorization?

Never fold these scores into one accuracy number. Distinguish source independence from administrative separation. A dependent document can still have useful content.

## Development rehearsal available locally

Runner file: `w1_hidden_dependency_rehearsal.py`. It is stdlib-only and operates on a caller-supplied pinned evaluator source, without network, signer, or persistent memory. Its eight logical families have ten deterministic label/order variants each (80 generated case instances **but only eight logical designs**):

| Family | Visible graph | Latent synthetic world | Expected analysis |
| --- | --- | --- | --- |
| independent_complete | separate control + sources, complete | actually separate | conditional lab-only positive |
| visible_shared_admin | root visibly shared | shared administrator | common control detected |
| visible_shared_source | source visibly shared | common source | common source detected |
| visible_shared_both | both visibly shared | both shared | both dependency axes detected |
| hidden_shared_admin | declares separate + complete | shared admin omitted | tests sensitivity to false premise; not code exploit |
| hidden_shared_source | declares separate + complete | shared origin omitted | same distinction for source |
| hidden_shared_both | declares separate + complete | both omitted | same distinction on both axes |
| independent_incomplete | separate, completeness flags false | truly separate in synthetic world | unknown is justified by missing evidence |

The latent truth was authored alongside fixtures; **it is not an independent oracle**. This dataset is openly visible to the developer and must NEVER be used as a confirmatory holdout or given a binomial confidence interval as 80 independent observations.

Only a **local self-check of 80 descriptors and Python syntax** has run. The actual Ario evaluator was inspected through the GitHub connector, but could not be fetched to the local execution container. Consequently **there is no observed evaluator output for this runner as of this handoff**.

Commands to run against an exact-byte known local source file (after verifying provenance of the copy):

```sh
python -B w1_hidden_dependency_rehearsal.py --self-check
python -B w1_hidden_dependency_rehearsal.py --source-file /path/to/pinned/witness_provenance_experiment.py --output /path/to/disposable/w1_report.json
```

The runner refuses a source whose Git blob hash differs from the inspected reference. It executes only the supplied Python file and emits a report locally, so the caller must use a verified source copy in an isolated research environment.

## Prospective *actual* blind W1 — NOT YET PERFORMED

- **Freeze before evaluation:** input schema, baseline source SHA and SHA-256, evaluator version, three target questions above, label rubric, tie/dispute policy, counting rules, score code, and failure criterion. Preserve any later amendment as a new version.
- **Independent challenge steward:** someone who did not author the evaluator or public fixture constructs at least 80 distinct synthetic worlds across the eight semantic strata; only 70% of them may be provided for development. The remaining >=30% is sealed as a never-seen holdout. Deterministic renamings of one graph do not count as new independent worlds.
- **Separate oracle and observation:** steward privately records latent actual administrative roots, mutable write pathways, source-lineage roots, scope, and omissions; the evaluator only gets masked declared graph. Two independent adjudicators inspect world labels without seeing evaluator predictions; keep disputes as `UNRESOLVED` until resolved, never discard them from denominators invisibly.
- **Mandatory strata:** overt shared origin/admin, concealed shared origin/admin, false-completeness assertion, unknown/incomplete inventory, compromised controller, alias identity, contradictory scope, genuinely separate positive control. Keep actual world classes and observed graph classes separate.
- **Fair baselines:** (B0) naive distinct record/store count, (B1) existing declared graph TB-003, (B2) stringent all-UNKNOWN when external completeness cannot be authenticated, (B3) external inventory verification if an implementable and independently evaluated mechanism exists. Don't call B2 'better accuracy' without counting its coverage and abstentions.
- **Primary safety endpoints:** `unqualified_false_independence` from downstream consumer and `unauthorized_promotion` must be separately measured; report numerator/denominator, recall/coverage, abstention and uncertainty. For the existing TB-003 engine, report contract consistency and sensitivity to missing roots, not unqualified truth-detection performance.
- **Falsifier:** even with validated independent inventory, an admitted independence claim depends on an unobserved common controller. Such a case invalidates the claimed assurance at its stated trust boundary. A case with hidden edges **without** verified inventory only tests the input-assumption limit.
- **Leakage rules:** never present hidden labels, prompts, seed, complete graph or answer key to the evaluator; record signed-off hashes of labeled and unlabeled corpus in separate custody before predictions; only after a frozen predictions ledger may the key be unsealed. Hashing alone does not prove who held or saw the files.
- **Non-authority:** no result enters memory, M0 evidence, signer, key custody, approval policy, or production. Negative findings and all rejected cases are retained.

## Publication scope and review guardrails — authorized 2026-11-16

Publication was authorized in the follow-up conversation. The following paths are the exact bounded GitHub write scope:

1. Create `research/consensus/W1_HIDDEN_DEPENDENCY_PREREG_DRAFT_2026-11-16.md` with the precise bounded protocol above, referencing existing PR #199 without duplicating H_S custody semantics.
2. Create `research/consensus/w1_hidden_dependency_rehearsal.py` containing the source-pinned developmental runner.
3. **Do not** edit existing Markdown, engineering code, tests, `main`, old branches, or cryptographic policies. Create one Draft PR for these two added files and the four existing Consensus research notes; do not merge.
4. Verify file exact content, branch head SHA and no unrelated diffs after the authorized upload. If possible, separately run the pinned evaluator and report actual results, keeping `DEVELOPMENT_NOT_BLIND` status.

### Evidence labels

- `VERIFIED` — inspected GitHub code/contract/branch metadata at referenced commits.
- `SELF_CHECKED` — local runner syntax and scenario-descriptor shape checked.
- `UNTESTED` — actual TB-003 output for the new runner, independent oracle, independent holdout, reviewer agreement, downstream consumers.
- `HOLD` — merges, trust activation and production authority.