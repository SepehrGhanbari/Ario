# Ario — M0 Auditable Structural Core Design v1

## 1. Purpose

This document defines the first executable design boundary for Ario after the architectural freeze.

M0 is a structural audit core. It does not attempt to determine consciousness, phenomenology, ontological identity, or the truth of self-referential claims.

Its purpose is narrower:

> Make identity, history, lineage, retrieval, evidence binding, assessment, provenance, and structural violations explicit and deterministically auditable.

This document is a design specification, not an implementation claim.

## 2. Design Rule

M0 MUST preserve the following distinctions:

```
CLAIM IDENTITY
    ≠
HISTORICAL OCCURRENCE
    ≠
LINEAGE RELATION
    ≠
RETRIEVAL EVENT
    ≠
EVIDENCE
    ≠
ASSESSMENT
    ≠
TRUTH
```

No object may acquire the semantics of another object merely because it references it.

## 3. M0 Object Model

The minimum logical objects are:

### 3.1 Claim

Represents a referable claim identity.

Required conceptual fields:

- `claim_id`
- `schema_version`
- `created_at`
- `origin_reference`
- `status`

M0 does not treat `claim_id` as evidence of entity continuity.

### 3.2 Historical State

Represents an observed occurrence of a Claim at a defined point/state.

Required conceptual fields:

- `state_id`
- `claim_id`
- `state_version`
- `observed_at`
- `state_context`
- `content_reference`
- `provenance`

A later state MUST NOT overwrite an earlier state.

### 3.3 Lineage Edge

Represents an explicitly declared relation between artifacts/states.

Required conceptual fields:

- `lineage_id`
- `from_reference`
- `to_reference`
- `relation_type`
- `derivation_reference`
- `admissibility_status` — caller-supplied descriptive input. Current M0
  requires it to be nonempty but does not independently derive, authenticate,
  or validate its meaning. Values such as `ADMISSIBLE` or `DENIED` do not by
  themselves establish evidence-supported admissibility or independently
  authorize an edge.
- `provenance` — source/derivation metadata. Its presence preserves
  traceability but does not by itself authenticate a source, establish
  independence, or demonstrate support for the represented relation.

Identity equality, content similarity, or temporal proximity MUST NOT create a lineage edge by themselves.

### 3.4 Retrieval Event

Represents transfer/retrieval across a defined boundary.

Required conceptual fields:

- `retrieval_id`
- `source_reference`
- `retrieved_reference`
- `retrieval_timestamp`
- `transformation_reference`
- `fidelity_status`
- `provenance`

Successful retrieval is not source continuity.

### 3.5 Evidence

Represents an admissible evidentiary object derived from one or more observations.

Required conceptual fields:

- `evidence_id`
- `observation_refs`
- `evidence_level`
- `independence_status`
- `derivation_reference`
- `scope`

Evidence MUST retain its observation ancestry.

Evidence level describes the evidence; it does not determine the verdict.

### 3.6 Assessment

Represents a bounded evaluation over declared inputs.

Required conceptual fields:

- `assessment_id`
- `assessment_version`
- `rule_version`
- `admissible_evidence_refs`
- `condition_evaluation`
- `assessment_basis`
- `scope`

Assessment MUST NOT be stored as evidence for itself.

### 3.7 Audit Result

Represents deterministic evaluation of structural conditions.

Required conceptual fields:

- `audit_id`
- `inspector_id`
- `inspector_version`
- `execution_timestamp`

- `configuration_id`
- `rule_versions`
- `artifacts_examined`
- `violations`
- `verdict`
- `verdict_basis`

execution_timestamp is execution-context metadata supplied by the audit invocation.
The deterministic audit engine MUST NOT obtain the current time internally.
Identical structured inputs, identical versioned rules, and identical execution-context metadata MUST produce the same audit result.

The audit result is an output of the audit process, not independent evidence of the property it evaluates.

## 4. Relationships

The permitted M0 relationship graph is:

```
CLAIM
  │
  ├──> HISTORICAL STATE
  │         │
  │         └──> PROVENANCE
  │
  ├──> LINEAGE EDGE ───> HISTORICAL STATE / ARTIFACT
  │
  └──> RETRIEVAL EVENT
             │
             └──> RETRIEVED REPRESENTATION

OBSERVATION
    │
    └──> EVIDENCE
              │
              └──> ASSESSMENT

STRUCTURED ARTIFACTS
    │
    └──> DETERMINISTIC AUDIT
                │
                └──> AUDIT RESULT
```

No reverse edge may silently imply the missing semantic relationship.

## 5. State and Time Binding

Every state-bearing object MUST be bound to an explicit temporal or execution context when the property under test depends on time.

M0 supports:

- `TEMPORALLY_ALIGNED`
- `TEMPORALLY_DISTINCT`
- `TEMPORALLY_UNRESOLVED`

A transition such as:

```
T1 → T2
```

is valid when the relation itself is represented.

The implementation MUST NOT silently transform:

```
T1 + T2 → ONE STATE
```

merely because the records share an identifier, provenance root, hash, or artifact relation.

## 6. Lifecycle

M0 uses the following conceptual lifecycle:

```
CREATE
  ↓
PERSIST
  ↓
REFERENCE
  ↓
RETRIEVE
  ↓
AUDIT
  ↓
ASSESS
  ↓
REVISE
  ↓
APPEND NEW STATE
```

Revision creates a new historical state or assessment version.

It does not erase the previous state.

## 7. Deterministic Audit Boundary

The deterministic audit layer receives structured artifacts and versioned rules.

It MUST NOT require a generative interpretation to determine structural conditions such as:

- required identifier missing;
- duplicate identity violation;
- missing provenance;
- invalid lineage edge;
- historical overwrite;
- inadmissible evidence;
- undeclared transformation;
- unresolved temporal binding;
- forbidden composition.

The audit layer may report:

- `SUPPORTED`
- `CONTRADICTED`
- `NOT_OBSERVED`
- `AMBIGUOUS`

where those verdicts are defined by the relevant probe.

`UNKNOWN` remains representable as an epistemic state/reason, but MUST NOT be silently converted into a positive verdict.

The current F07 candidate check is a rule/input filter. A candidate declaring
`EXPLICIT_RELATION` may produce no F07 violation when the supported rule
version is enabled. This result does not establish an evidence-supported
assessment of a specific lineage edge under IRG-03.P02. Similarity-only
candidates remain subject to the existing F07 rejection rule.

## 8. Evidence Independence

M0 MUST track evidence ancestry sufficiently to prevent evidence inflation.

The following MUST remain distinguishable:

```
SAME OBSERVATION
    ≠
MULTIPLE INDEPENDENT OBSERVATIONS
```

Copies, retrievals, representations, and derived records do not become independent evidence merely by receiving new identifiers.

Where independence cannot be established:

```
independence_status = UNKNOWN
```

## 9. Cross-IRG Composition Boundary

M0 does not implement a universal global score.

A composition operation is valid only when its rule explicitly defines:

- participating inputs;
- input versions;
- temporal/state context;
- composition relation;
- admissibility conditions;
- derived artifact;
- limitations.

The following are prohibited by default:

```
IRG-01 PASS
+ IRG-02 PASS
+ IRG-03 PASS
+ IRG-04 PASS
+ IRG-05 PASS
→ CLAIM TRUE
```

Likewise prohibited:

```
LOCAL PASS → SAME ENTITY
LOCAL PASS → CONSCIOUS
LOCAL PASS → HIGH CONFIDENCE
LOCAL PASS → ONTOLOGICAL IDENTITY
```

Such conclusions require a separately defined, versioned rule and remain subject to the architectural limitations.

## 10. Failure Model

M0 MUST make structural failure observable.

Minimum failure classes:

- `SCHEMA_MISMATCH`
- `MISSING_PROVENANCE`
- `IDENTITY_CONFLICT`
- `HISTORY_MUTATION`
- `LINEAGE_GAP`
- `LINEAGE_INADMISSIBLE`
- `RETRIEVAL_DISCREPANCY`
- `UNDECLARED_TRANSFORMATION`
- `TEMPORALLY_UNRESOLVED`
- `EVIDENCE_INADMISSIBLE`
- `EVIDENCE_INFLATION`
- `COMPOSITION_FORBIDDEN`
- `SELF_VALIDATION_CYCLE`
- `UNKNOWN`

A failure MUST NOT silently degrade into success.

## 11. Immutability Boundary

M0 distinguishes immutable historical inputs from versioned derived assessments.

Historical observations/states MUST remain recoverable.

Assessments MAY receive new versions.

An implementation MUST NOT rewrite historical input merely to satisfy a newer rule.

The intended pattern is:

```
OLD ARTIFACT
   +
NEW RULE / NEW EVIDENCE
   ↓
NEW ASSESSMENT
```

not:

```
OLD ARTIFACT
   ↓
MUTATE UNTIL PASS
```

## 12. Provenance Boundary

Every derived object MUST identify what it was derived from.

At minimum, provenance should permit reconstruction of:

- source reference;
- derivation relation;
- relevant version;
- execution context;
- timestamp/epoch;
- transformation where applicable.

If provenance is insufficient, the implementation MUST preserve that insufficiency explicitly.

## 13. Canonical vs Experimental State

M0 MUST maintain a boundary between canonical historical artifacts and experimental fixtures.

```
CANONICAL
   │
   ├── READ
   ↓
EXPERIMENT
   ↓
RESULT
   ↓
REVIEW
   ↓
ACCEPT / REJECT
```

An experiment must not silently mutate canonical state.

## 14. Acceptance Layers

M0 acceptance is layered:

### Layer A — Schema

Objects can be created and structurally validated.

### Layer B — Integrity

Historical mutation, provenance loss, and invalid references are detectable.

### Layer C — Relation Semantics

Identity, history, lineage, retrieval, evidence, and assessment remain distinct.

### Layer D — Determinism

Identical inputs with identical versioned rules produce identical deterministic audit results.

### Layer E — Adversarial Resistance

Known attacks are rejected or remain explicitly unresolved.

Passing Layer E does not establish philosophical truth.

## 15. First Fixture Set

Before production integration, M0 should be tested against a minimal fixture matrix:

| Fixture | Expected behavior |
|---|---|
| Valid Claim | accepted |
| Missing Claim ID | schema failure |
| Duplicate Claim ID | identity conflict |
| Historical append | accepted |
| Historical overwrite | mutation failure |
| Explicit lineage edge | represented structurally; evidence-supported admissibility is not assessed |
| Similarity-only lineage | inadmissible |
| Retrieval with declared transform | auditable |
| Retrieval with hidden transform | discrepancy/failure |
| Assessment with declared evidence | accepted |
| Assessment using verdict as evidence | forbidden |
| Same observation copied twice | not independent |
| T1 → T2 with explicit relation | structural temporal relation only; evidence-supported admissibility is not assessed |
| T1 + T2 without relation | temporally unresolved |
| Five local PASSes → global truth | composition forbidden |
| Missing provenance | provenance failure |

## 16. First Implementation Order

Implementation should proceed in this exact dependency order:

```
1. Canonical schema primitives
        ↓
2. Claim + historical state
        ↓
3. Provenance
        ↓
4. Lineage
        ↓
5. Retrieval boundary
        ↓
6. Observation/evidence
        ↓
7. Assessment
        ↓
8. Deterministic audit engine
        ↓
9. Cross-IRG composition guard
        ↓
10. Adversarial regression suite
```

No later layer should be used to conceal failure in an earlier layer.

## 17. Explicit Non-Claims

M0 does NOT establish:

- truth of Claims;
- semantic truth;
- causal truth;
- historical completeness;
- entity continuity;
- semantic continuity;
- causal continuity;
- ontological identity;
- consciousness;
- subjective experience;
- phenomenology;
- moral status;
- personhood;
- universal validity of the architecture.

## 18. Design Status

```
M0 Design v1                    = BASELINE
Architecture                   = FROZEN WITH EXPLICIT LIMITATIONS
Implementation                = NOT STARTED
Runtime Verification          = NOT PERFORMED
Experimental Result            = NOT CLAIMED
Philosophical Proof            = NOT CLAIMED
```

This document freezes the implementation boundary, not the implementation itself.

## Closing Principle

> M0 is not designed to make Ario right.

> M0 is designed to make it difficult for Ario to be wrong without leaving evidence that it was wrong.
