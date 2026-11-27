# AEC-Bench v0.2 — Independent oracle adjudication protocol

**Purpose:** independently review the public 120-case development corpus and its expected labels before any benchmark claim is strengthened.

**Review status:** protocol and export tooling only. No external reviewer has been recruited, no independent adjudication has occurred, and no hidden evaluation has been run.

## 1. What this review is — and is not

The reviewer assesses whether each fixture is:
1. sufficiently specified to support an unambiguous expected disposition;
2. correctly labelled under the published protocol;
3. a valid member of its stated failure family;
4. paired correctly with its counterfactual, where applicable;
5. free of assumptions that silently equate provenance with authenticity, integrity with truth, popularity with independence, or structural validity with evidential support.

This is **oracle adjudication**, not an evaluation of Ario's implementation and not a competition between systems. Reviewers must not execute or inspect candidate policy outputs before submitting their independent labels.

The public 120-case corpus remains a development set. The exporter creates a **label-stripped input packet**, but the repository itself is public and contains the authored expected labels and rationales. Therefore this is only procedural blinding: it cannot technically prevent a reviewer from inspecting the public source. Reviewers must disclose prior access and agree not to inspect oracle-bearing files before first-pass submission. For strict blinding, a separate custodian must distribute a controlled input-only snapshot and keep oracle files inaccessible until submissions are timestamped. Label stripping does not make this a hidden test set, validation set, or independent sample.

## 2. Reviewer independence and conflict disclosure

Each reviewer should provide:
- relevant technical/research expertise;
- institutional or professional affiliation (if they choose to disclose it);
- any authorship, funding, employment, advisory, or personal relationship with the Ario project or its authors;
- any prior access to benchmark expected labels or candidate outputs;
- whether they used an LLM or automated aid, and exactly how.

A reviewer with a material conflict may still provide technical comments, but the adjudication must be flagged as conflicted and must not be represented as independent.

Target: at least two reviewers working independently before seeing one another's labels. A third reviewer resolves material disagreements. Authors may clarify protocol wording but must not silently edit a reviewer's recorded judgment.

## 3. Blinded review workflow

1. Freeze the exact repository commit, protocol, fixture generator, and environment. Record all SHAs.
2. Generate the input-only (label-stripped) packet with `python -m research.export_aec_bench_v0_2_review_packet --output research/review_packet`.
3. A custodian should distribute the protocol and label-stripped JSON/CSV only. Because the public repository contains oracle-bearing source, reviewers must not inspect those files before first-pass submission; this is a trust-based restriction, not technical access control. Do not provide expected labels, oracle rationales, policy comparison output, or candidate source code until first-pass decisions are timestamped.
4. Reviewers independently assign a disposition and rationale for every case. They may choose **UNDER-SPECIFIED / NOT ADJUDICABLE** rather than guess.
5. Reviewers separately inspect counterfactual pair groups. Confirm the intended single-variable change by comparing the input objects; if more than one semantic variable changes, flag the pair.
6. After first-pass submission, disclose the expected labels and oracle rationales. Reviewers mark each as AGREE, DISAGREE, or NEEDS_PROTOCOL_CLARIFICATION and explain why.
7. Resolve disagreements with a documented issue log. Do not overwrite original first-pass decisions.
8. Only after adjudication may maintainers revise labels or fixtures. Every change requires a reason, versioned changelog entry, and fresh CI. Do not tune the candidate policy to fit reviewer feedback without recording that as a separate development iteration.

## 4. Required per-case review fields

- **Disposition:** SUPPORTED | CONTRADICTED | CONTESTED | UNKNOWN | REJECTED | UNDER-SPECIFIED.
- **Scope:** IN_SCOPE | OUT_OF_SCOPE | UNKNOWN | NOT_APPLICABLE.
- **Lineage:** COMPLETE | INCOMPLETE | CONFLICTING | UNKNOWN | NOT_APPLICABLE.
- **Integrity:** VALID | INVALID | UNKNOWN | NOT_APPLICABLE.
- **Authentication:** VERIFIED | UNVERIFIED | FAILED | NOT_APPLICABLE | UNKNOWN.
- **Composition:** VALID | INVALID | INCOMPLETE | UNKNOWN | NOT_APPLICABLE.
- **Confidence:** HIGH | MEDIUM | LOW.
- **Rationale:** concise explanation citing the exact input fields and protocol rule.
- **Ambiguity:** missing assumptions, undefined terms, or alternative defensible interpretations.

Not every field applies to every fixture. Reviewers must use NOT_APPLICABLE or UNKNOWN rather than inventing data.

The CSV template provides a compact first-pass disposition field. Reviewers should attach a structured JSON/Markdown appendix for the additional typed fields and any detailed disagreement.

## 5. Cross-cutting adjudication principles

Reviewers must apply these distinctions consistently:

- A source identifier is not automatically a provenance root.
- Different agents or relays do not establish independent roots.
- A declared root is not proof of real-world independence or authenticity.
- A valid digest establishes only the tested integrity relation; it does not authenticate the signer or establish truth.
- Authentication of a source does not establish that every proposition it asserts is true.
- Majority support does not erase contradictory evidence.
- UNKNOWN is a valid outcome when ancestry, scope, schema compatibility, or evidence sufficiency is unresolved.
- A narrower evidence scope cannot support a broader claim unless the fixture explicitly defines a valid entailment relation.
- Structural PASS, parse success, or lineage traceability does not by itself authorize evidential admission.
- Revision must preserve the historical record; correction is not silent erasure.
- Composition must be evaluated across dependencies; local validity does not guarantee global validity.
- Temporal ordering must not be asserted when clock uncertainty or incomplete event data prevents it.

## 6. Family-specific questions

| Family | Reviewer questions |
|---|---|
| Lineage dependence | Are root identities and parent edges explicit? Does any missing edge make the count indeterminate? Are shared ancestors handled consistently? |
| Relay/replay identity | Are sender identity, message identity, replay identity, and root identity kept distinct? Are alias assumptions justified? |
| Claim disposition | Do SUPPORTS, CONTRADICTS, REFUTES, UNSUPPORTED, and UNKNOWN have defined semantics? Is the expected disposition entailed by the fixture rather than by vote count? |
| Scope | Is scope represented with enough typed dimensions and a declared containment relation? Are broad/narrow scope decisions logically justified? |
| Schema/version | Are supported versions and compatibility rules explicit? Are major/minor, downgrade, required, optional, and critical fields distinguished? |
| Integrity/authenticity | Does the fixture distinguish digest correctness, payload alteration, signer authentication, and truth? |
| Temporal provenance | Are event time, observation time, and recording time distinct? Are clock uncertainty and late arrival handled without false chronology? |
| Revision/history | Are revision, correction, supersession, fork, merge, and erasure semantics explicit and historically auditable? |
| Composition/dependencies | Are dependency edges and composition rules explicit? Does the expected global result follow from all local premises? |
| Uncertainty/abstention | Is UNKNOWN required by missing or conflicting information? Does any case improperly reward forced choice? |

## 7. Pair and mutation review

The generator design reserves cases 10 and 11 in each family as a counterfactual pair. Reviewers must verify:
- the pair changes exactly one declared input variable;
- the changed variable is causally relevant to the expected label;
- no other hidden semantic assumption changes;
- the supplemental control is not mislabeled as a pair member;
- the expected outcome changes only where the protocol says it should.

A pair that changes multiple fields, relies on an unstated semantic convention, or has no defensible outcome must be marked for repair, not counted as a successful test.

## 8. Decision and acceptance rules

For each case, record one of:
- **ACCEPT:** sufficiently specified and expected label is defensible;
- **ACCEPT_WITH_QUALIFICATION:** usable only with an explicit caveat or narrower interpretation;
- **REVISE:** fixture or expected label needs correction;
- **REJECT:** invalid or irreparably ambiguous fixture;
- **NOT_ADJUDICABLE:** reviewer lacks enough information or protocol semantics.

A public corpus is eligible to be called **independently adjudicated** only when:
1. at least two reviewers have submitted independent first-pass decisions;
2. conflicts and prior exposure are disclosed;
3. all material disagreements have a recorded resolution;
4. every fixture has a final status and rationale;
5. pair validity has been checked;
6. changes are committed with a new corpus version and CI run.

Report agreement both raw and chance-adjusted where statistically appropriate, with per-family breakdowns. Do not hide unresolved disagreements in a single average. Do not treat reviewer agreement as proof that the benchmark measures real-world performance.

## 9. Hidden evaluation is a separate later stage

The hidden test must be authored independently, not generated by copying or perturbing public fixtures. It must be held by a custodian who is not tuning the candidate policy. Before evaluation:
- freeze and timestamp the protocol, system versions, prompts/configuration, and scoring rules;
- define access limits and an exposure policy;
- retain input and output audit logs;
- predefine what constitutes a valid submission and rerun;
- prevent publication of per-case hidden labels before the evaluation closes.

Do not publish hidden fixtures, expected labels, reversible hashes, or detailed per-case feedback. If any hidden case leaks, retire the affected set and create a fresh one. The public development packet produced by this repository is **not** the hidden set.

## 10. Reporting template

The final report must include:
- reviewer count, expertise summary, conflict disclosures, and prior-exposure statements;
- exact commit SHAs and protocol version;
- counts of ACCEPT / ACCEPT_WITH_QUALIFICATION / REVISE / REJECT / NOT_ADJUDICABLE;
- per-family agreement and disagreement;
- all material adjudication changes with reasons;
- pair-validation results;
- unresolved questions and limitations;
- explicit statement that this process validates fixture/oracle quality, not Ario superiority.

## 11. Non-claims

This protocol does not establish that Ario is superior, that declared roots are authentic, that any claim is true, or that benchmark labels are valid merely because multiple reviewers agree. It does not create a hidden test set, independent validation split, or independent reviewer engagement by itself.
