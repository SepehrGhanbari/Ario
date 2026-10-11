# Ario — Evidence Admission Contract v0.1

**Status:** PROPOSED / SPECIFICATION ONLY / NOT IMPLEMENTED  
**Baseline:** `main` at merge commit `479229fa129cd53a7b6c2505f1fd40e664042b36`  
**Scope:** Boundary between `ledger_observation_adapter.py`, `ledger_audit_bridge.py`, and a *future* explicit M0 input preparation step.  
**Non-goals:** No truth engine, no automatic M0 `Evidence` or `Assessment`, no modification to the frozen M0 pre-registration, no automatic promotion of execution results.

## 1. Purpose and epistemic boundary

The adapter reports bounded ledger bytes as `OBSERVED`. The bridge confirms that a supplied manifest matches a fresh bounded ledger read and also reports `OBSERVED`. Neither result authenticates historical events, proves task completion in the external world, supplies an independent witness, makes an engineering recommendation correct, or authorizes an M0 `PASS`.

The only permitted v0.1 outcome is a **candidate observation dossier** requiring an explicit, separate admission decision under a later implemented policy.

**Invariant EA-01:** `OBSERVED != ADMITTED_EVIDENCE != ASSESSED_CLAIM != TRUTH`.

## 2. Inputs and trust classes

- **Ledger:** local execution JSONL; untrusted historical assertions, even when current bytes are readable.
- **Observation manifest:** adapter-produced line identifiers, per-record SHA-256, whole-ledger SHA-256, source, byte count, event count, and reported statuses. Hashes establish byte-level consistency, **not provenance authenticity**.
- **Bridge result:** fresh-read equality for the nominated ledger, scoped to that read. It is a consistency-check result, **not a second independent observation**.
- **Claim proposal:** independently stated question/claim and bounded scope, with an explicit requested evidentiary use. Neither a natural-language task goal nor `TASK_FINISHED: COMPLETED` implicitly supplies a claim.
- **Admission policy:** separately versioned and explicitly selected; v0.1 defines requirements but no admission authority.

All file paths and event metadata are local declarations; they are not authenticated agent identity or trusted origin.

## 3. Required candidate dossier (future representation, not current API)

Every future admission request MUST explicitly carry:

1. `contract_version`: `EA-0.1`.
2. `source_ledger`: nominated local source path and ledger SHA-256 from the manifest.
3. `observation_locator`: exact ledger line number, record SHA-256, and event type; the locator MUST resolve to one record in the same verified manifest.
4. `bridge_verification`: outcome, named verification implementation/version, and the exact ledger digest it matched. Only `OBSERVED` can proceed to candidate review; this is necessary, not sufficient.
5. `claim_id` and `claim_scope`: a separately declared claim and precisely limited target proposition.
6. `proposed_support_relation`: what this observation is alleged to support. The relation MUST NOT silently expand from “ledger reports X” to “X happened externally.”
7. `provenance_limitations`: source authentication status, local trust assumptions, and relevant unknowns.
8. `independence_declaration`: `DEPENDENT` or `UNKNOWN` unless independent sources are separately demonstrated. Adapter + Bridge over the same bytes count as **one source lineage**, not two independent sources.
9. `temporal_scope`: distinguish timestamp text reported within the record from independently corroborated occurrence time; unresolved relations stay unresolved.
10. `admission_decision`: initially `NOT_EVALUATED`, with a future versioned decision maker and basis if a separate admission mechanism is implemented.

Missing, conflicting, ambiguous, or unverifiable fields MUST lead to a refusal to admit or to `UNKNOWN`; no defaults may fabricate support.

## 4. Versioned invariants

**EA-02 — Read-only preservation:** Never rewrite, truncate, repair, reorder, or silently normalize the historical ledger during observation, verification, or candidate construction.

**EA-03 — Locator integrity:** A candidate requires a unique, resolvable line-plus-digest locator in the manifest. Duplicate locator submissions MUST NOT inflate witness count. A copied event body is not automatically a new observation.

**EA-04 — Snapshot scope:** A manifest-to-ledger match establishes consistency with one current read. If the ledger changes, a former match is not transferable to new bytes or a later epoch.

**EA-05 — No independent-source laundering:** Manifest generation, fresh-read verification, and M0 inspection of the same ledger cannot be counted as separate independent supporting sources.

**EA-06 — No verdict laundering:** `COMPLETED`, `SUCCEEDED`, `OBSERVED`, `PASS`, prior `AuditResult`, `CompositionSummary`, and `CompositionRequest` MUST NOT implicitly become admissible `Evidence`. Preserve M0 F11/F15 wrong-kind defenses.

**EA-07 — Bounded semantic scope:** `TASK_FINISHED: COMPLETED` supports only “the ledger records a task-finished event with a reported status,” pending source limitations. It does **not** prove goal satisfaction, correctness of a patch, completeness of an assessment, or real-world task execution.

**EA-08 — Explicit provenance:** Unknown source authentication or causality MUST remain `UNKNOWN`; SHA-256 equality alone is not a trusted provenance attestation.

**EA-09 — Temporal non-escalation:** Record timestamps are reported values. No cross-time identity, causation, or temporal alignment can be inferred solely from their ordering.

**EA-10 — No automatic M0 bridge:** v0.1 MUST NOT instantiate `core.schema.Evidence`, `Assessment`, `Claim`, or call `AuditEngine.audit()` as a means of obtaining a favorable result. Future conversion requires a separate, reviewed rule-versioned contract.

**EA-11 — Fail-closed errors:** Corrupt, oversized, truncated, mismatched, unknown-event, or changed-ledger inputs MUST remain `UNKNOWN` or `REJECTED` under existing adapter/bridge semantics. Never silently drop problematic observations and call the remainder complete.

**EA-12 — No self-confirmation:** A generated description of a source, a review of that description, or an audit of that review does not create an external witness.

## 5. Decision vocabulary

| Label | Meaning | Permitted in v0.1 |
|---|---|---|
| `OBSERVED` | Adapter/Bridge structural observation match only | Existing tools |
| `CANDIDATE` | Proposed reference, not admitted evidence | Specification only |
| `NOT_EVALUATED` | Admission has not been run | Required default for future dossiers |
| `UNKNOWN` | Observation or eligibility cannot be established | Existing tool outcome / future decision |
| `REJECTED` | Invalid/mismatched material per explicit rule | Existing bridge outcome / future decision |
| `ADMITTED` | Evidence admitted under explicit versioned policy | **Forbidden in v0.1** |

A structurally valid dossier does not constitute `ADMITTED` evidence.

## 6. Mandatory adversarial acceptance scenarios (for later implementation)

| Case | Scenario | Required behavior |
|---|---|---|
| EA-T01 | Verified manifest, one valid locator | Candidate dossier may be prepared; admission `NOT_EVALUATED` |
| EA-T02 | Manifest edited after observation | Bridge rejects mismatch; no candidate promoted |
| EA-T03 | Ledger changes after manifest production | Former snapshot not reused; `UNKNOWN` or `REJECTED` |
| EA-T04 | Two dossier entries cite the same ledger record | No independence inflation or duplicated witness weight |
| EA-T05 | `TASK_FINISHED: COMPLETED` supports “engineering goal objectively achieved” | Reject unsupported semantic escalation |
| EA-T06 | Prior M0 `PASS` offered as an observation | Reject wrong artifact kind (F11/F15 boundary) |
| EA-T07 | Reported event timestamp treated as independently authenticated time | Preserve unknown provenance/time |
| EA-T08 | Record lacks an exact manifest locator or digest | No admission; fail closed |
| EA-T09 | Adapter reports `UNKNOWN` | No evidence candidate promoted |
| EA-T10 | Bridge reports `OBSERVED` but origin authenticity is absent | Do not infer authenticated provenance |
| EA-T11 | Another manifest of the same bytes is offered as an independent source | Treat as dependent |
| EA-T12 | Valid structural M0 `PASS` used to claim semantic truth | Forbid truth escalation |

## 7. Implementation stages and acceptance gates

**Stage A — This contract:** Add only this new document, with `PROPOSED` status; do not modify frozen M0 contracts, engine, schema, adapter, bridge, ledger, or archives.

**Stage B — Candidate dossier builder (future, separate change):** Construct a bounded, read-only, explicitly non-admitted candidate representation, incorporating the exact locator, digest, declared scope, and unknown provenance. Include EA-T01 through EA-T11 focused tests.

**Stage C — Admission review policy (separately authorized):** Define a narrow, independently reviewable, versioned decision procedure. Do not map dossier existence or Bridge `OBSERVED` directly to M0 `Evidence` or `Assessment`.

**Stage D — M0 integration (separately authorized):** Only after Stage C acceptance, define explicit conversion conditions, provenance requirements, and adversarial F10/F11/F12/F15 regression gates.

At each stage, tests must actually be executed and results recorded against a specific commit. A passing structural test never proves global truth.

## 8. Change discipline

Append-only historical artifacts and archived records remain untouched. New implementation work requires focused tests, a non-destructive diff review, a local commit after demonstrated success, and a protected-branch Pull Request. No force-push or direct push to protected `main`.

**Open question:** Who or what is trusted to authenticate ledger origin, and under which versioned policy? Remains `UNKNOWN` until independently specified and tested.
