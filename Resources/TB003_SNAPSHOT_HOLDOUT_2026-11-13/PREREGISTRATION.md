# ARIO TB-003 | Prospective H_S snapshot-final custody benchmark — preregistration PROPOSAL 0.1

**Draft date 2026-11-13. NOT an already preregistered independent experiment. No confirmatory results.**
**Scope:** exclusively synthetic evidence structures; old v0.1 TB-003 stays authoritative for what it presently claims.

## 1. Hypotheses that must not be conflated

**H_E (status quo interpretation):** LAB_CHAIN_PRESENT demonstrates a specified supported custody path in a controller-declared graph, not necessarily the *latest* custodian. The existing short-fanout test [lines 612–625](https://github.com/SepehrGhanbari/Ario/blob/972a4199e5c52e1bdab559be623949c7d7a24b69/implementation/tests/test_witness_provenance_experiment.py#L612-L625) deliberately accepts small noncyclic off-path transfers. A mismatch to H_S is not by itself a defect in H_E.

**H_S (new candidate):** every case supplies snapshot_sequence T and a separately declared complete_transfer_surface. Transfer means moving one **exclusive synthetic custody token**, not copying it or granting joint custody. Valid event edges identify the named artifact, originate with the LAB controller, follow strictly increasing sequence after capture, begin at the current endpoint, and end at an unvisited custodian. Only events with sequence <= T affect the snapshot. Consume *every* in-scope event: disconnected edges, forks, same-sequence ties, unsupported edges, cycles, or incomplete inventory => UNKNOWN. The terminal node (or capture custodian without transfers) is final_holder(T). A unique terminal node different from the nominated HELD_BY => MISMATCH. This does **not** establish a trusted real-world timestamp or authentic event.

**Independent custody chain at T:** requires BOTH nominated witnesses to have valid known paths to the snapshot; the nominated holder must match each endpoint; declared-complete transfer and control inventories; no compromised relevant actors anywhere on either valid path; no common custody actor, shared administrator/root, shared writable/restorable store, or unresolved mutability. Shared control => COMMON_CONTROL_DETECTED, scenario-declared compromise => COMPROMISED_BY_SCENARIO, otherwise incomplete => UNKNOWN. A success is only LAB_CONDITIONALLY_SEPARATE.

**Source distinctness:** a *separate* property. Complete source-surface and no declared shared origin can be LAB_CONDITIONALLY_DISTINCT; explicit shared origin yields COMMON_SOURCE_DETECTED; incomplete/unsupported => UNKNOWN. Alias transitive-ancestry rules remain undecided in [#129](https://github.com/SepehrGhanbari/Ario/issues/129); the bounded public reference procedure intentionally does not resolve them. A future version must distinguish immutable version identity from mutable name.

**Scope limitation of public oracle:** two fixtures with one intentionally clean witness B and constrained control/source flags; no general-purpose arbitrary custody graph checker. The baseline TB-003 and new oracle answer different questions, and label collisions must never be presented as external proof of correctness.

## 2. Predicted discriminators

- A: no transfer, capture and HELD_BY same -> H_S MATCH.
- B: transfer P1→P3 by T, HELD_BY remains P1 -> H_S MISMATCH, even if H_E still reports LAB_CHAIN_PRESENT.
- C: transfer P1→P3, HELD_BY=P3, relevant P3 compromised -> H_S COMPROMISED_BY_SCENARIO.
- D: P1→P3→P4, HELD_BY=P3 -> H_S MISMATCH. P4 is not witness B's actor.
- E: one actor has two incompatible outbound transfers, invalid/disconnected route or simultaneous moves -> H_S UNKNOWN.
- F: declared-complete source and control surfaces are NOT proof of complete transfer history. If complete_transfer_surface=false => H_S UNKNOWN.
- G: an event after T does not update final_holder(T), and a compromised actor from witness B must still be counted as relevant to both-witness independence.
- H: shared mutable control / storage or shared source should block the corresponding *separate* positive property.

## 3. Public development controls

Exactly 18 openly authored cases are provided for smoke and metamorphic testing. Fixed assertions check their new-semantics reference outcomes. These examples were designed after inspecting old results, so they MUST NOT be counted in a confirmatory benchmark or described as blind. Their expected outcomes are **proposed operational labels**, not judgments by an independent empirical authority.

## 4. Future independent holdout (NOT YET EXECUTED)

1. Freeze accepted semantics, adapter, and competitor configurations with hashes *before* generating holdout data. Any change reopens a new numbered preregistration; preserve the older one.
2. An independent challenge steward (not the implementing coder) creates 240 never-before-seen synthetic cases: 8 strata × 30 (clean custody; valid multi-hop; departed/mismatched holder; branches/disconnected chronology; compromised relevant and irrelevant actors incl witness B; shared administration/storage/source; unsupported/incomplete evidence; time-boundary and node/edge-order variants). Set >=80 affirmative and >=80 non-affirmative target labels overall, or disclose a deviation before outcomes are viewed.
3. Two independent labelers who cannot see evaluated outputs adjudicate against the *pre-frozen H_S contract*; preserve individual labels and disagreements. A third adjudicator resolves disputed cases; unknown disputes remain UNRESOLVED and counted, not silently deleted. Do not call a self-critique by one model an independent review.
4. Separately seal unlabeled challenge JSON and private labels file using canonical SHA-256 commitments with custody and creation timing stated. The evaluated runner receives unlabeled cases **only**, and logs dataset hash, pinned source SHA, raw predictions and environment prior to labels being unsealed. Hashes prove byte continuity relative to a commitment, not historical authenticity or reviewer independence.
5. Compare original frozen TB-003 evaluator, naive artifact-name distinctness, and a declared strong graph/path baseline under the same inputs. **This is an evaluation of H_S capability**, not a test of the original TB-003 author's intended H_E behavior.
6. **Primary metric:** critical over-affirmation = (H_S label is non-affirmative AND method outputs unqualified LAB_CONDITIONALLY_SEPARATE) / (number of adjudicated non-affirmative H_S examples). Report numerator and denominator, Wilson 95% confidence interval, case-level error, abstentions. Secondary: affirmative recall, error by stratum, source/admin cross-axis confusion, record permutation, runtime and independent-labeler agreement.
7. **Proposed acceptance gate:** 0 critical over-affirmations and >=90% affirmative recall on the synthetic H_S holdout. One critical false affirmative fails this stringent criterion. Zero of 240 does not prove general correctness, and this threshold is not a sample-size power analysis.
8. Publish positive, negative, ambiguous and failed runs with prompt/seed/procedure/fixture version, hashes, expected and observed labels; preserve every earlier result and preregistration deviation. Exploratory post-hoc cases are labeled EXPLORATORY and cannot improve the primary holdout score.

## 5. Ways this proposed protocol could itself be wrong

- Show that an apparently departing transfer is legitimately a **copy** or shared custody, violating the exclusive-token assumption; revise the event ontology in a *new* version instead of calling existing code defective.
- Show a trace that the oracle marks MATCH despite an unconsumed in-scope custody event; or a permitted permutation/renaming that changes a reference verdict.
- Show that the blind runner imports a gold label or leaks answers, that the comparator changes source version, or that a candidate can silently overwrite frozen history.
- Show the new semantics lacks any claim made by old TB-003; then report a *new target task* only, not a regression finding.
- Find a fair, stronger baseline that performs as well or better; publish that negative result.

**NO GO:** no real source authentication, signature/trust enrollment, evidence admission, consciousness/identity conclusions, main merge, or changes to protected engineering/governance records.
