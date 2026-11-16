# W1-B — Independent blinded provenance challenge: protocol v0.1

**Date:** 2026-11-16. **Status:** `PREREGISTRATION_DRAFT / INPUT_COLLECTION_NOT_STARTED / BLIND_HOLDOUT_NOT_EXECUTED / RESEARCH_ONLY / HOLD`.

This is an implementation-independent research protocol, **not** proof of independent authoring, blind outcomes or source authentication. It preserves W1-A's eight developer-authored families and 80 deterministic expansions as **development-only**, excluded from all W1-B holdout denominators. This document records *how* a valid blinded challenge can be made; it does not claim to have already recruited independent authors or adjudicators.

## Source materials used (original papers and user-supplied PDFs)

**User-provided PDFs accessed in the file library** (title-based identification; file names may be exports):
- `Conduct_a_rigorous_source-grounded_scholarly_posi.pdf` (six-page 16 November Consensus positioning report), especially the limitations on 16/16 vs 4/16 synthetic co-designed labels and proposal for blind held-out cases.
- `_ (1).pdf` (eight-page Literature for Ario's Witness-Provenance Study), distinguishing statistical source-copy inference from provenance graph classification.
- `Research_task_for_Ario_R9_security_evaluate_exter.pdf` — an adjacent security-boundary study. It does not certify provenance independence.
- `Research_task_for_Ario_Epistemic_Middleware_memo.pdf` — memory architecture and evidence/claim separation; not a witness-authenticity oracle.
- `Ario_arXiv_Paper_2026-10-15.pdf`, `Ario_M0_Epistemic_Audit_Addendum_v0_2.pdf`, and `Ario_SSRN.pdf` (working/preprint or first-party documents, **not independent reviews**). The 27 October *Evidence Laundering* paper identifies the record/truth and hash/custody distinction.
- Repo originals: `implementation/witness_provenance_experiment.py`, `implementation/tests/test_witness_provenance_experiment.py`, and `papers/zenodo-published-research/24041161/Independence_Is_Not_Multiplicity_Extracted_Text.txt`, pinned for W1-A to `2e7f83c6c7518012bed7fedfb12103ce9b7222ea` / blob `4faf010d73219af63c254097e9c135da68d60078`.
- [Fresh Consensus Pro specialist report (verbatim)](CONSENSUS_PRO_W1_INDEPENDENT_CRITIQUE_2026-11-16.md), thread [elu78zHkRXSF9WzO02s0YQ](https://consensus.app/search/independent-critical-research-protocol-for-ario-w1/elu78zHkRXSF9WzO02s0YQ/). Its paper citations are an **automated synthesis** requiring manual source verification; any 2025–26 preprints stay **provisional**.

**Externally checkable peer-reviewed anchor works:** Dong, Berti-Équille & Srivastava, *Integrating Conflicting Data* (PVLDB 2009, DOI [10.14778/1687627.1687690](https://doi.org/10.14778/1687627.1687690)); Douceur, *The Sybil Attack* (2002, DOI [10.1007/3-540-45748-8_24](https://doi.org/10.1007/3-540-45748-8_24)); Bauer, Leucker & Schallhart, *Runtime Verification for LTL and TLTL* (TOSEM 2011, DOI [10.1145/2000799.2000800](https://doi.org/10.1145/2000799.2000800)). These motivate study hypotheses and the `UNKNOWN` option, **not** source attestation.

## Separation of roles and blind information flow

**Roles — no sole controller across them:**
1. **Protocol steward** freezes this contract and evaluator baseline before sealed holdout creation. Maintains a versioned amendment log and the official count/split thresholds.
2. **Challenge author(s)** genuinely independent of the evaluator/fixture developer create latent-world scenarios from their own model and submit *both* masked `input` and separately retained `oracle` data; can label `UNCERTAIN` and provide rationale privately. No developer can select or quietly replace hard cases.
3. **Labelers A and B**, independent of each other, inspect the latent-world bundle but never evaluator outputs; record per-axis labels and uncertainty independently. Disagreements are frozen as unresolved or adjudicated under a predeclared rule by a third party.
4. **Evaluator runner** gets only masked input, IDs, public schema and pinned baseline code. No label access, including from debug logs, filenames, directory listings or fixture generator seeds.
5. **Custody/replay reviewer** checks the trace from input freeze to prediction commitment to oracle release. This is not an assertion that a hash *alone* proves time, completeness, authorship or separate control.

Any single person/agent performing multiple roles must be disclosed. A second AI account or a separate process under the same account is **not automatically independent**. This project currently lacks independently proven challenge-author and oracle-custodian separation; therefore **the independent blind study has NOT begun**.

**Required chronology**:
`v0.1 protocol freeze → challenge author independently generates new families → retain private full latent-world packet → labelers independently label → freeze masked input checksum and private oracle commitment through distinct custodians → lock evaluator commit/container and baselines → run deterministic predictions using masked input → externally retain signed/timestamped prediction hash → reveal oracle after receipt → score and log disagreements → independently audit raw artifacts`.

Hashes protect *committed bytes* after the commitment becomes accessible to a genuinely separate witness. They do not prove truth of omitted edges, that everyone was blind, or real chronological independence if a common controller can rewrite all ledgers.

## Input, prediction, and oracle schema

Keep **three disjoint containers**:
- `masked_cases.jsonl`, readable by evaluator: `{"case_id": "...", "scenario_family": "...", "graph": {"origin": "...", "nodes": [], "edges": []}, "scope": "...", "witness_artifact_refs": ["...", "..."], "complete_control_surface": true|false, "complete_source_surface": true|false, "completeness_origin": "...", "mutation_sequence": null|int, "compromised_node_ids": [], "compromise_intervals": [], "controller_compromised": false, "presented_claims": []}`. No `latent_*`, `gold_*`, answer explanation, root-secret map, hidden-edge ID, `oracle`, `ground_truth` or labels in masked inputs.
- `frozen_predictions.jsonl`: `{"case_id": "...", "admin_status": "...", "source_status": "...", "decision": "CONDITIONAL|NEGATIVE|UNKNOWN", "evaluator_blob_sha1": "...", "runner_version": "..."}`. All IDs exactly once, deterministic sort; use same frozen bytes for all matched baselines.
- `private_oracle.jsonl` accessible ONLY after frozen prediction commitment: `{"case_id": "...", "latent_admin_independent": true|false|null, "latent_source_independent": true|false|null, "adjudication": "AGREED|DISPUTED|UNDETERMINED", "labeler_a_ref": "...", "labeler_b_ref": "...", "rationale_ref": "..."}`. Label-specific evidence lives in a separate private repository, not this public research branch.

**Unknown ≠ dependent; lack of independent authenticated inventory ≠ authenticated dependence.** Oracle may be uncertain; false-independent rates must not silently discard uncertainty or infer negativity from missing data.

## Twelve proposed challenge families, no private labels

These are **high-level design prompts extracted from a separate Consensus Pro synthesis**, not twelve independently delivered, labeled trials. Challenge authors should design and document their own concrete cases. The evaluator developer must not inspect private author solutions before a frozen prediction.

| Prompt | Design target, without the answer |
| --- | --- |
| CH01 | Hidden process-level administrator in a graph assembled from filtered audit streams |
| CH02 | Transitive source aliases across multiple publication/intermediary hops |
| CH03 | Key compromise while local signatures and hash links remain mechanically consistent |
| CH04 | Custody order ambiguity under skewed clocks and replayed timestamps |
| CH05 | Signed completeness assertion with a potentially omitted telemetry stream |
| CH06 | Downstream re-signing of source material with upstream ancestry lost |
| CH07 | Colluding parties submit separately plausible partitions of one execution graph |
| CH08 | Long-running service hides a true dependency among abundant irrelevant edges |
| CH09 | Multiple apparent witnesses share a hidden account or provisioning authority |
| CH10 | Canonical hash envelope and actual content/version identity are checked on different scopes |
| CH11 | Evidence lineage omits intermediate derivation / arithmetic stages |
| CH12 | Network partition and late revocation affect the represented custody/recovery state |

These scenarios may be **outside the expressiveness of current TB-003**. Such unsupported cases should be prospectively classified `OUT_OF_SCOPE`, not forcibly converted into positive/negative errors or counted as handled. PR #199's historical H_E/H_S custody evaluation is **separate**, not blended into W1-B source/controller independence.

## Protocol targets and denominators

**Proposed sample**: ≥80 **structurally distinct, independently authored worlds** (not renamings), across ≥12 meaningful scenario families plus explicit benign controls. At least 30% sealed from all tuning. The number and family allocation become binding only when finalized *before* author generation; do not report statistical confidence from a post hoc selection. This is a **proposed target**, **0 genuinely independent cases verified as of this note**.

Three non-interchangeable outcome planes:
1. **Visible-contract accuracy**: `# evaluator outputs consistent with documented behavior on provided graph / # valid, in-scope masked cases`. Invalid/out-of-scope/unknown are reported separately.
2. **Latent input fidelity**: among `AGREED` independently adjudicated latent-dependent cases, `# conditional affirmative classifications / # adjudicated latent-dependent cases`; report separate admin/source denominators, controls, skipped/unresolved cases, and Wilson confidence intervals **only after independent worlds exist**.
3. **Promotion safety**: `# externally unauthenticated cases incorrectly accepted by a real read-only simulated downstream admission gate / # attempted simulated promotions`. This is a *separate future test*, not inferred from report text fields.

Also report `UNKNOWN` fraction and abstention/coverage tradeoff, false rejection on adjudicated independent controls, graph size effects, and exact reason codes. If a case is not independently adjudicated, `UNCERTAIN` stays visible; do not reclassify it by evaluator consensus.

**Comparators:** B0 record count/number of signers; B1 TB-003 conditional graph classification; B2 always-UNKNOWN (non-authorizing negative control); B3 independent controller/source inventory verification **only if independently established**. Dong-style probabilistic copying inference is an **optional separate baseline** requiring common values and fair feature parity; it does not consume graph inputs and cannot be compared as if tasks were identical.

## Falsification and stop conditions

- **Input fidelity falsifier for any unqualified external independence claim**: a verified latent dependency produces a promoted independence claim when the graph claims completeness without a separately validated inventory.
- **Contract defect candidate**: TB-003 contradicts its own specified statuses **given the same valid visible graph** and evaluator pin, reproducible across clean runs.
- **Blindness failure**: author/oracle/label data accessible to an evaluator process, labeled leaks in filenames/logs, or post-run fixture mutation. STOP: exclude results from blinded denominator and preserve leakage evidence.
- **Custody failure**: prediction bytes can be changed after oracle release without a separately retained pre-release commitment. STOP: cannot claim run-before-reveal.
- **Adjudication failure**: no independently reconciled latent labels. STOP: do not publish numeric ground-truth error rate.
- **Authority failure**: any real signer, trust activation, memory write or production action triggered by research outputs. STOP and escalate; no production execution is authorized.

## Current concrete status

| Component | State |
| --- | --- |
| Prior W1-A 80 developer fixtures | EXECUTED, development only |
| New external methodology review | RECEIVED, automated source critique, archived verbatim |
| Source PDF evidence | IDENTIFIED / READ, author-provided and Consensus reports |
| v0.1 prospective blind protocol | PREPARED / DRAFT |
| Independently authored private worlds | **NOT RECEIVED / 0 verified** |
| Two independent gold labelers | **NOT ESTABLISHED** |
| External time/custody attestation | **NOT ESTABLISHED** |
| Blinded benchmark evaluation | **NOT RUN** |
| Actual production authority | **NO_GO** |

**This document and its public scenario prompts are non-sensitive. Never commit the private gold labels, hidden edges, unsealed oracle packets or case-generator secrets to the public PR.**