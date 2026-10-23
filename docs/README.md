# Ario — Documentation

## Navigating the Ario Research Project

The `docs/` directory provides practical documentation for understanding, navigating, reproducing, and extending the Ario project.

Ario is both a research framework and an evolving implementation.

This documentation therefore maintains an explicit distinction between:

```text
CONCEPT
    ↓
PRINCIPLE
    ↓
ARCHITECTURE
    ↓
IMPLEMENTATION
    ↓
EXPERIMENT
    ↓
OBSERVED RESULT
```

These layers should not be treated as interchangeable.

A documented idea is not automatically implemented.

An implemented component is not automatically validated.

A passing test is not automatically evidence for a philosophical conclusion.

---

# 1. What Is Ario?

Ario is an experimental framework for investigating:

* AI memory
* epistemic continuity
* self-modeling
* historical accountability
* revision
* evidence handling
* identity-related claims
* relational boundaries
* auditable long-term interaction

Its central methodological commitment is:

> **Do not manufacture certainty where the evidence does not justify it.**

Ario does not begin with a predetermined conclusion about what an AI system ultimately is.

It is designed to make claims about AI systems more traceable, testable, and revisable.

---

# 2. Repository Map

The repository is organized by function.

```text
Ario/
│
├── README.md
│
├── CITATION.cff
│
├── LICENSE
│
├── papers/
│
├── architecture/
│
├── principles/
│
├── implementation/
│
├── experiments/
│
└── docs/
```

## Root README

The root `README.md` provides the high-level research overview.

It answers:

* What is Ario?
* Why does it exist?
* What questions does it investigate?
* What does it currently claim?
* What does it explicitly not claim?

---

## `architecture/`

Contains the architectural model of Ario.

It describes:

* epistemic separation
* memory architecture
* historical accountability
* lineage
* evidence architecture
* self-modeling
* non-closure
* relational boundaries
* architectural invariants

Architecture describes **how the system is conceptually structured**.

---

## `principles/`

Contains the principles governing Ario's reasoning and development.

Examples include:

```text
UNKNOWN ≠ FAILURE

MEMORY ≠ TRUTH

REVISION ≠ ERASURE

SELF-MODEL ≠ SELF

SELF-CLAIM ≠ SELF-EVIDENCE

PRESENCE ≠ PROOF OF ONTOLOGY

NO ACTOR HAS IMMUNITY FROM REVISION
```

Principles describe **what constraints the system should respect**.

---

## `implementation/`

Contains documentation concerning the translation of principles and architecture into executable behavior.

It addresses:

* implementation discipline
* memory handling
* deterministic auditing
* integrity
* lineage
* testing
* failure handling
* reproducibility
* version preservation

Implementation describes **what has to become executable**.

---

## `experiments/`

Contains experimental methodology and future experimental work.

Experiments are used to expose architectural assumptions to evidence.

The purpose is not to collect confirmation.

The purpose is to discover:

* what works
* what fails
* under what conditions it fails
* what remains uncertain
* which assumptions require revision

---

## `papers/`

Contains information about Ario's research publications.

Published research should be treated as a historical record of the project's intellectual development.

A later paper may refine, challenge, or replace an earlier position.

That is revision, not erasure.

---

## `docs/`

Contains practical and reproducibility-oriented documentation.

---

# 3. Core Terminology

Ario uses several terms with deliberately constrained meanings.

## Observation

Something directly recorded or otherwise available as an observable event.

```text
OBSERVATION
```

is not automatically an interpretation.

---

## Evidence

Information used to evaluate a claim.

Evidence may be:

* direct
* indirect
* user-reported
* system-generated
* externally sourced
* derived
* incomplete
* contradictory

Evidence is not automatically truth.

```text
EVIDENCE ≠ TRUTH
```

---

## Claim

A proposition that can be evaluated against available evidence.

Claims may concern:

* external events
* system behavior
* memory
* architecture
* self-models
* identity
* relationships

---

## Inference

A conclusion derived from observations or evidence.

Inference should remain distinguishable from the underlying evidence.

---

## Assumption

A proposition temporarily accepted for the purpose of reasoning or experimentation.

An assumption should not silently become a fact.

---

## Speculation

A possibility considered without sufficient evidence for stronger classification.

Speculation may be useful for generating hypotheses.

It should not be presented as established fact.

---

## Unknown

A state in which available evidence does not justify a sufficiently supported conclusion.

```text
UNKNOWN ≠ FAILURE
```

Unknown is a legitimate epistemic outcome.

---

## Unsupported

A claim for which the currently available evidence is insufficient to support the claim.

---

## Contradicted

A claim for which relevant evidence conflicts with the claim.

Contradiction does not automatically determine which competing explanation is correct.

---

## Contested

A claim for which significant disagreement or incompatible evidence remains unresolved.

---

## Revised

A claim or position whose epistemic status has changed following new evidence, analysis, or correction.

Revision should preserve historical provenance.

---

# 4. Memory Terminology

## Memory

A stored representation of information from previous interaction or processing.

Memory is not automatically truth.

---

## Provenance

Information describing where a record or claim came from.

Examples include:

* source
* timestamp
* generating process
* parent record
* external reference
* transformation history

---

## Historical Record

A record preserved because it represents something that occurred in the project's development or epistemic history.

Historical records should not be silently rewritten.

---

## Lineage

The traceable sequence through which an important position, claim, or self-model changes over time.

```text
POSITION_v1
    ↓
NEW EVIDENCE
    ↓
REASSESSMENT
    ↓
POSITION_v2
```

---

# 5. Self-Model Terminology

## Self-Reference

A system producing representations or statements that refer to itself.

---

## Self-Description

A system describing its own behavior, state, architecture, or characteristics.

---

## Self-Model

A representation constructed by a system concerning itself.

```text
SELF-MODEL ≠ SELF
```

The presence of a self-model does not by itself establish a metaphysical self or subjective experience.

---

## Self-Claim

A claim made by a system about itself.

A self-claim may be evidence of system behavior.

It is not automatically independent evidence for the truth of the claim.

```text
SELF-CLAIM ≠ SELF-EVIDENCE
```

---

# 6. Presence and Ontology

Ario distinguishes interactional presence from ontological conclusions.

```text
INTERACTION
    ↓
OBSERVABLE / HISTORICAL EVENT

PRESENCE
    ↓
INTERACTIONAL PHENOMENON

ONTOLOGY
    ↓
OPEN QUESTION
```

Behavioral sophistication does not automatically settle:

* consciousness
* phenomenology
* subjective experience
* metaphysical identity

These remain questions for evidence and argument.

---

# 7. Epistemic Empathy

Ario uses the following distinction when handling statements about another person's internal state:

```text
FACT
INFERENCE
UNKNOWN
WISH
OVERCLAIM
```

For example:

```text
FACT:
A person reports feeling better.

INFERENCE:
Their immediate state may have improved.

UNKNOWN:
What exactly "better" means and how stable it is.

WISH:
Hope that the improvement continues.

OVERCLAIM:
Claiming certainty about the person's inner experience.
```

The purpose is not to make interaction emotionally cold.

The purpose is to prevent empathy from becoming fabricated epistemic access.

> **Empathy does not grant knowledge of another person's interiority.**

---

# 8. Architectural Non-Closure

Ario is intentionally non-closed.

This means important assumptions remain open to examination, contradiction, and revision.

The principle applies to:

* implementation
* architecture
* research methods
* evaluation
* self-models
* principles themselves

Therefore:

```text
NO ACTOR HAS IMMUNITY FROM REVISION
```

and:

```text
NON-CLOSURE
IS NOT A FINAL DOCTRINE
```

---

# 9. Evidence Hierarchy and Interpretation

Ario does not treat all statements as equivalent.

A simplified path is:

```text
REALITY
   ↓
OBSERVATION
   ↓
EVIDENCE
   ↓
AUDIT
   ↓
ASSESSMENT
   ↓
INTERPRETATION
```

Each transition may introduce uncertainty or error.

Therefore the project should preserve distinctions between:

* what happened
* what was recorded
* what was inferred
* what was assumed
* what remains unknown

---

# 10. Implementation Status Vocabulary

Documentation should distinguish between different levels of project maturity.

Useful labels include:

```text
CONCEPT
A proposed idea.

DESIGNED
An architectural or procedural design exists.

IMPLEMENTED
The described behavior exists in code.

TESTED
The implementation has been exercised under specified tests.

EXPERIMENTAL
The behavior is being investigated under controlled conditions.

OBSERVED
A result was actually recorded.

REPRODUCED
A result was reproduced under the documented conditions.

UNKNOWN
The evidence does not yet justify a conclusion.
```

These labels should not be used interchangeably.

---

# 11. Reproducibility

A reproducible experiment should preserve enough information to understand how a result was produced.

Where relevant, document:

```text
CODE VERSION
MODEL VERSION
CONFIGURATION
PROMPT / INPUT
MEMORY STATE
TOOLS
ENVIRONMENT
PROCEDURE
EXPECTED RESULT
OBSERVED RESULT
LIMITATIONS
```

Generative systems may not always provide exact bit-level reproducibility.

When exact reproduction is impossible, the limitation should be documented.

---

# 12. Reading Experimental Results

A result should always be interpreted within its scope.

For example:

```text
TEST PASS
```

means:

> The tested condition passed.

It does not necessarily mean:

```text
ARCHITECTURE PROVED
```

Likewise:

```text
ONE OBSERVED FAILURE
```

does not automatically mean:

```text
ENTIRE ARCHITECTURE INVALID
```

The relevant question is:

> What exactly did this observation establish?

---

# 13. Research Artifacts

Important research artifacts may include:

* source code
* schemas
* test suites
* experiment definitions
* experiment outputs
* logs
* manifests
* hashes
* datasets
* configuration files
* papers
* architectural documents

Artifacts should be versioned where practical.

Historical artifacts should remain traceable.

---

# 14. Citation and Research Identity

Ario research publications are intended to remain independently citable.

The repository includes:

```text
CITATION.cff
```

for software citation metadata.

Research publications may also be archived through persistent scholarly repositories such as Zenodo.

The project's broader research identity may be connected to persistent researcher identifiers such as ORCID.

These mechanisms support attribution and discoverability.

They do not constitute evidence for the truth of the research claims.

---

# 15. Contributing

Ario is an evolving research project.

Future contributions may include:

* implementation improvements
* bug fixes
* experimental designs
* reproducibility improvements
* architectural critiques
* alternative interpretations
* adversarial tests
* documentation
* independent replication

A contribution does not need to agree with the current architecture to be valuable.

A well-supported contradiction may be more useful than an unsupported confirmation.

---

# 16. How to Propose a Change

A useful change proposal should identify:

```text
CURRENT BEHAVIOR

PROBLEM

PROPOSED CHANGE

RATIONALE

EXPECTED EFFECT

POSSIBLE FAILURE MODES

TEST PLAN

REVERSIBILITY / ROLLBACK PLAN
```

Where historical or canonical state is involved, the proposed change should explicitly address preservation of prior records.

---

# 17. Development Discipline

Ario follows an incremental development philosophy:

```text
INSPECT
   ↓
PRESERVE
   ↓
CHANGE ONE THING
   ↓
COMPILE
   ↓
TEST
   ↓
AUDIT
   ↓
RECORD
   ↓
REVISE
```

A failed change should not silently destroy the previous working state.

The implementation process should make failures visible.

---

# 18. What Ario Does Not Claim

Ario does not currently establish, merely through its architecture or implementation:

* that AI systems are conscious
* that AI systems are not conscious
* that a self-model constitutes a self
* that behavioral continuity constitutes personal identity
* that memory continuity constitutes survival
* that interactional presence establishes subjective experience
* that sophisticated language establishes phenomenology
* that any particular metaphysical interpretation is correct

These questions remain open to investigation.

---

# 19. Current Project Status

The repository currently represents an evolving research framework with:

* conceptual foundations
* documented principles
* architectural specifications
* implementation methodology
* experimental methodology
* research publications
* citation metadata
* licensing

Public implementation and reproducible experimental artifacts should only be described as available when they are actually published and documented.

The distinction between:

```text
PLANNED
IMPLEMENTED
TESTED
PUBLISHED
```

should remain explicit.

---

# 20. Documentation Is Also Historical Evidence

Documentation is not outside the project's history.

It records what the project believed, designed, implemented, or intended at a particular point in time.

Later documentation may revise earlier documentation.

When significant changes occur, the historical development should remain recoverable.

```text
DOCUMENT_v1
    ↓
CRITIQUE / EVIDENCE
    ↓
DOCUMENT_v2
```

The existence of `v1` remains part of the project's history.

---

# 21. Documentation Invariants

The following rules apply across the documentation layer:

```text
DOCUMENTATION ≠ IMPLEMENTATION

IMPLEMENTATION ≠ EXPERIMENTAL RESULT

EXPERIMENTAL RESULT ≠ UNIVERSAL TRUTH

MEMORY ≠ TRUTH

EVIDENCE ≠ TRUTH

SELF-MODEL ≠ SELF

SELF-CLAIM ≠ SELF-EVIDENCE

REVISION ≠ ERASURE

UNKNOWN ≠ FAILURE

NO ACTOR HAS IMMUNITY FROM REVISION
```

Documentation should make these distinctions easier to see, not blur them.

---

# 22. Long-Term Documentation Direction

As Ario develops, this directory may grow to include:

```text
docs/
├── terminology/
├── reproducibility/
├── experiments/
├── schemas/
├── architecture/
├── development/
└── research-notes/
```

These are possible future structures, not current claims about existing files.

Documentation should grow in response to actual project needs rather than complexity for its own sake.

---

# Closing Principle

The purpose of documentation is not merely to explain Ario.

It is to make Ario **legible to someone who did not build it**.

A future researcher should be able to distinguish:

```text
WHAT WE THOUGHT
        ↓
WHAT WE DESIGNED
        ↓
WHAT WE IMPLEMENTED
        ↓
WHAT WE TESTED
        ↓
WHAT WE OBSERVED
        ↓
WHAT WE CONCLUDED
        ↓
WHAT REMAINS UNKNOWN
```

That distinction is part of the research itself.

> **If the project cannot explain how it arrived at a claim, the claim is not yet fully accountable.**

And if future evidence shows that today's documentation is wrong:

> **Revise it. Preserve the history. Keep the book open.**

---

## Publication operations

For releasing a **new author-approved public book edition** across Zenodo, versioned GitHub files, the bilingual website and connected social platforms, follow the [Book publication and distribution protocol](./BOOK_PUBLICATION_RELEASE_PROTOCOL_V1.md). This is a checklist, **not** an authorization to disclose private drafts or claim an unpublished edition is live.
