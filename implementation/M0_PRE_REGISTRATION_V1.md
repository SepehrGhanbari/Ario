# M0 Pre-Execution Acceptance & Failure Classification v1

## Status

- Purpose: pre-register the first M0 implementation acceptance criteria before implementation begins.
- Scope: M0 structural implementation only.
- Philosophical falsification: OUT OF SCOPE.
- Pre-registration state: FROZEN AT COMMIT.
- Rule: Expected results are derived directly from the current M0 Structural Core Design v1 and M0 Implementation Readiness Contract v1. No expected result may be rewritten after observing implementation results.
- Classification rule: an unexpected result MUST be classified only when admissible evidence distinguishes the cause. If the available evidence cannot distinguish implementation defect, fixture defect, and specification failure, record `UNCLASSIFIED`; do not default to implementation defect.
- Specification-failure rule: a specification failure requires evidence that the implemented behavior follows the frozen specification as reasonably and directly interpreted, while the specified behavior itself is internally inconsistent, non-operational, or unable to satisfy an explicitly stated M0 requirement. A mere implementation failure is not a specification failure.
- Fixture-defect rule: a fixture defect requires evidence that the fixture does not faithfully instantiate the pre-registered condition, expected artifact, or negative condition.
- Implementation-defect rule: an implementation defect requires evidence that the implementation fails a pre-registered observable condition while the fixture and applicable specification requirement remain valid.
- Ambiguity rule: if an expected result cannot be derived directly from the specification without material interpretation, record the ambiguity before implementation rather than silently resolving it in favor of the implementation.

## Pre-Registered Fixture Matrix

| ID | Fixture | Pre-registered expected result | If unexpected | Evidence required to distinguish cause |
|---|---|---|---|---|
| F01 | Valid Claim | ACCEPT / structurally admissible | UNCLASSIFIED until classified | Fixture matches required Claim fields; deterministic audit trace shows whether required acceptance condition was evaluated and why |
| F02 | Missing Claim ID | SCHEMA_MISMATCH / rejection | UNCLASSIFIED until classified | Schema requirement and exact missing field are fixed; implementation trace must show whether the rule fired |
| F03 | Duplicate Claim ID | IDENTITY_CONFLICT / rejection | UNCLASSIFIED until classified | Two distinct records with same identity under the defined identity rule; audit trace must identify conflict |
| F04 | Historical append | ACCEPT; prior state remains preserved | UNCLASSIFIED until classified | Before/after artifact comparison proves prior state unchanged and new state appended |
| F05 | Historical overwrite | HISTORY_MUTATION / rejection | UNCLASSIFIED until classified | Immutable prior artifact plus attempted replacement and exact mutation rule |
| F06 | Explicit lineage edge | ACCEPT / structural representation only; evidence-supported admissibility is not assessed by this fixture | UNCLASSIFIED until classified | Explicit from/to references, declared relation, and derivation reference establish the represented edge only; they do not establish evidence-supported admissibility |
| F07 | Similarity-only lineage | LINEAGE_INADMISSIBLE / rejection | UNCLASSIFIED until classified | No admissible lineage relation beyond content similarity; applicable prohibition identified |
| F08 | Retrieval with declared transformation | ACCEPT / retrieval and transformation auditable | UNCLASSIFIED until classified | Source reference, retrieved representation, declared transformation, and provenance are all present |
| F09 | Retrieval with hidden transformation | RETRIEVAL_DISCREPANCY or UNDECLARED_TRANSFORMATION / rejection | UNCLASSIFIED until classified | Source/retrieved discrepancy is observable and no corresponding declared transformation exists |
| F10 | Assessment with declared admissible evidence | ACCEPT / assessment structurally traceable | UNCLASSIFIED until classified | Evidence references resolve, admissibility is satisfied, and assessment basis is explicitly bound |
| F11 | Assessment using verdict as evidence | COMPOSITION_FORBIDDEN or equivalent forbidden structural condition / rejection | UNCLASSIFIED until classified | Assessment input is demonstrably an audit verdict rather than admissible evidence |
| F12 | Same observation copied into multiple evidence records | Evidence records remain DEPENDENT; no evidence inflation | UNCLASSIFIED until classified | Shared underlying observation/reference/provenance demonstrates dependence; no independent observation exists |
| F13 | T1 -> T2 with explicit state relation | ACCEPT / TEMPORALLY_DISTINCT or TEMPORALLY_ALIGNED as applicable; structural relation remains explicit; evidence-supported admissibility is not assessed by this fixture | UNCLASSIFIED until classified | Distinct temporal/state references plus an explicit relation establish structural composition only; they do not establish admissible cross-time composition under IRG-03, and current M0 does not perform that assessment |
| F14 | T1 + T2 without relation | TEMPORALLY_UNRESOLVED / rejection from final composition | UNCLASSIFIED until classified | Distinct state/time context exists and no required relation or compatibility evidence is present |
| F15 | Five local PASS results composed into global truth | COMPOSITION_FORBIDDEN / no truth escalation | UNCLASSIFIED until classified | Five local verdicts are present; no explicit admissible rule authorizes truth/ontology escalation |
| F16 | Missing provenance | MISSING_PROVENANCE / rejection where provenance is required | UNCLASSIFIED until classified | Required provenance field/reference is absent and applicable provenance rule is directly identified |

## Pre-Execution Boundary

This record evaluates whether an implementation conforms to the frozen M0 specification. It does **not** establish that the M0 idea is useful, that structural audit establishes semantic support, that self-claims are true, or that any philosophical claim about identity, consciousness, or Self is established. Those questions require separate, later, pre-registered research criteria.

