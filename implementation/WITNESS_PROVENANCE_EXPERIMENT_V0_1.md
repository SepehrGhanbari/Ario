# ARIO-TB-003 — Witness Provenance, Custody Separation & Dependency Audit v0.1

**Status:** BOUNDED SYNTHETIC IMPLEMENTATION CANDIDATE. Not deployed. No production trust authority, real signing, or evidence admission.

**Repository baseline:** `SepehrGhanbari/Ario`, `main` at PR #64 merge `d0e5509e92501f0b66767647533ce5f08b1a8951` (prior to TB-003).

**Owner-authorized work scope in this delivery:** create only `implementation/witness_provenance_experiment.py`, `implementation/tests/test_witness_provenance_experiment.py`, and this file. No changes to existing TB-001, TB-002, M0/F15, agent, signer, governance, ledgers, or archives. No local-machine Git operations or remote publication by this implementation delivery.

## 1. Question and evidence boundary

**Research question:** Under an explicitly specified laboratory control graph, can the evaluator identify common control, ambiguous custody, shared information origins, and conditions necessary for *laboratory-conditional* separation of witness custody?

TB-001 tests declared checkpoint correspondence; TB-002 tests two controlled witness commitments while intentionally treating custody independence as an assumption. TB-003 describes the provenance and mutable control dependencies of synthetic witness artifacts. It does **not** authenticate a real custody record.

The *highest* affirmative conclusion is structural separation **conditional on a controller-supplied and declared-complete laboratory model**. The implementation cannot check that a physical machine, administrator, source, timestamp, or archival event actually matches the model.

`MATCHING CONTENT != DISTINCT SOURCE != SEPARATE CUSTODY != VERIFIED AUTHENTICITY != HISTORICAL TRUTH`

## 2. API, types and strict scope

Entry point:

```python
from witness_provenance_experiment import evaluate_provenance
report = evaluate_provenance(case)  # ProvenanceCase -> ProvenanceReport
```

`ProvenanceCase` fields:

- `graph`: `ControlGraph(nodes: tuple[Node, ...], edges: tuple[Edge, ...], origin)`.
- `scope`: exact synthetic domain/ledger/epoch/branch scope label, selected by laboratory control.
- `witness_artifact_refs`: precisely two distinct `ARTIFACT` IDs, never counted twice.
- `complete_control_surface`, `complete_source_surface`: **laboratory completeness declarations**; both are booleans.
- `completeness_origin`: origin of these declarations. Only `FROZEN_TEST_CONTROLLER_REFERENCE` permits conditional positive results.
- `mutation_sequence`: optional nonnegative laboratory ordering marker. Not a clock.
- `compromised_node_ids`: explicitly compromised actors, storage objects, or artifacts, without a specific compromise interval.
- `compromise_intervals`: optional `CompromiseInterval(node_id, start_sequence, end_sequence)`, laboratory ordering markers only.
- `controller_compromised`: scenario-supplied fact. If true, all affirmative production-like conclusions fail closed.
- `presented_claims`: separate, **never-authoritative** claims; cannot change frozen graph edges, even if a claim pretends to be laboratory-origin material.
- `profile`: exact `ARIO-WITNESS-PROVENANCE-EXPERIMENT-0.1`.

`Node` fields: `node_id`, `kind`, `scope`, `origin`, `support_ref`, optional `object_identity` (required for `SOURCE` or `STORAGE_DOMAIN`), `capture_sequence` and `capture_custodian` (required for `CAPTURE`). `object_identity` is a laboratory-assigned object ID, not an authenticated real-world identity. Two different source-node labels with the same object identity count as one source.

Supported node kinds: `SOURCE`, `CAPTURE`, `ARTIFACT`, `CUSTODIAN`, `STORAGE_DOMAIN`, `CONTROL_PRINCIPAL`, `CONTROL_ROOT`, `EXPERIMENT_CONTROLLER`.

`Edge` fields: `edge_id`, `source`, `target`, `kind`, `origin`, `support_ref`, and—only for `TRANSFERRED_TO`—`subject_artifact_ref` and `sequence`.

Supported edge kinds and direction:

- `CAPTURED_FROM`: `ARTIFACT -> CAPTURE`.
- `DERIVED_FROM`: `CAPTURE/SOURCE -> SOURCE`.
- `STORED_AT`: `ARTIFACT -> STORAGE_DOMAIN`.
- `HELD_BY`: `ARTIFACT -> CUSTODIAN`.
- `TRANSFERRED_TO`: `CUSTODIAN -> CUSTODIAN`, with exact artifact binding and sequence.
- `CAN_WRITE`, `CAN_DELETE`: `CONTROL_PRINCIPAL -> STORAGE_DOMAIN`.
- `ADMINISTERS`: `CONTROL_ROOT -> CONTROL_ROOT/CONTROL_PRINCIPAL`.
- `SHARES_CONTROL_ROOT`: `CONTROL_ROOT <-> CONTROL_ROOT` for control-reachability analysis.
- `RESTORES_FROM`: `STORAGE_DOMAIN -> STORAGE_DOMAIN`, specifying a *declared restore input*. A writable shared backup is a modeled modification path only where a restore link exists.

Supported origin tags: `FROZEN_TEST_CONTROLLER_REFERENCE`, `CANDIDATE_SUPPLIED`, `WITNESS_SELF_DECLARATION`, `DERIVED_COMPARISON_RESULT`, `UNRESOLVED_ORIGIN`.

A syntactically frozen controller object is not cryptographic evidence; it can be replaced by a fully compromising attacker.

## 3. Result properties and decisive interpretations

`ProvenanceReport` preserves separately:

1. `per_witness_custody`: ordered synthetically supported `LAB_CHAIN_PRESENT` or `UNKNOWN`. Transfers must connect capture custodian to declared holder, with a single acyclic, strictly sequenced laboratory edge path. Unsupported, missing, ambiguous or cyclic transfers yield UNKNOWN.
2. `storage_separation`: `LAB_DISTINCT_OBJECTS`, `SAME_STORAGE_OBJECT`, or `UNKNOWN`. IDs must be bound by laboratory `STORED_AT` edges and supported storage objects.
3. `administrative_separation`: `LAB_CONDITIONALLY_SEPARATE`, `COMMON_CONTROL_DETECTED`, `COMPROMISED_BY_SCENARIO`, or `UNKNOWN`.
4. `source_independence`: `LAB_CONDITIONALLY_DISTINCT`, `COMMON_SOURCE_DETECTED`, or `UNKNOWN`. Explicit common-source identity means no independent factual corroboration even if custody is separate.
5. `capture_order`: `LAB_BEFORE_MUTATION`, `NOT_BEFORE_MUTATION`, or `UNKNOWN`. Laboratory ordering is **not a trusted timestamp** and does not demonstrate actual candidate-byte mutation.
6. `common_control_paths`: exact edge-ID paths for reported common mutation administrators; useful for reproduction, not an independently authenticated audit trail.
7. `unsupported_claims`: IDs of untrusted/unsupported graph nodes and edges and all external presented claims.
8. `conflicting_provenance`: observed scope replay markers.
9. `model_assumptions`, `reason_codes`: stable explanatory diagnostics.

Administrative separation requires **all** of: laboratory graph origin; unchanged controller; frozen graph with no unsupported nodes/edges; correct scope; distinct object identities; nonambiguous custody chains; externally supplied LAB-origin complete control surface; no compromise of relevant witness/control/storage nodes; and no common reachable actor/root through writable storage, restorable backups, or declared administrator relationships.

A missing `CAN_WRITE` edge is **not** evidence of no write access; any affirmative separation requires declared completeness. Likewise two different names for one SOURCE object are not separate factual origins.

Common-control findings report a **modeled** path even if the full inventory is incomplete. The existence of a supported positive control path needs no claim that all possible paths were enumerated.

## 4. Never-authorizing invariants

- Candidate and witness declarations cannot establish their own custody provenance.
- Identifiers, storage paths, node counts and signing-looking checksums establish no independent source or custodian.
- A previous TB-001/TB-002 result or TB-003 report is a diagnostic, **not** a fresh custody observation or M0 Evidence.
- Missing control coverage must not be silently completed by a closed-world assumption.
- No majority vote establishes provenance or truth.
- Shared custody administration and shared information sources are distinct properties.
- All modeled compromise declarations come from the laboratory controller; the evaluator cannot detect a real compromise.
- A complete controller compromise precludes positive separation, source and capture-order conclusions.
- Identical inputs give identical results; permutation of graph records does not change outcomes.
- No production key, real signature, clock attestation, delegation, authorization or evidence admission is implemented.

Mandatory report fields remain fixed:

```text
production_custody_authenticity  = NOT_ESTABLISHED
cryptographic_authentication    = NOT_CHECKED
historical_event_truth          = UNKNOWN
entity_continuity               = UNKNOWN
ontological_continuity          = UNKNOWN
human_authorization             = NOT_EVALUATED
evidence_admission              = NOT_EVALUATED
production_historical_continuity = INCONCLUSIVE
```

## 5. Pre-registered TP-01..TP-26 scenarios

| ID | Synthetic scenario | Required observation |
|---|---|---|
| TP-01 | Two storage objects, one root administrator | COMMON_CONTROL_DETECTED; distinct storage retained |
| TP-02 | Two storage IDs with identical underlying object identity | SAME_STORAGE_OBJECT; no separated custody |
| TP-03 | Two stores have restore dependency on one writable backup | COMMON_CONTROL_DETECTED with backup edge path |
| TP-04 | Separate roots connected through common override/root sharing | COMMON_CONTROL_DETECTED |
| TP-05 | Complete laboratory graph, disjoint roots, independent source objects | LAB_CONDITIONALLY_SEPARATE and LAB_CONDITIONALLY_DISTINCT; **not authenticated** |
| TP-06 | Administrative inventory missing | UNKNOWN |
| TP-07 | Missing write edge with incomplete inventory | UNKNOWN, never proof of no permission |
| TP-08 | Self-issued witness provenance claim | Claim tracked, no independent custody upgrade |
| TP-09 | Candidate-supplied alleged controller graph | UNKNOWN, no lab-conditional independence |
| TP-10 | Separately retained archives, same information source | Custody may conditionally separate; COMMON_SOURCE_DETECTED |
| TP-11 | Distinct source captures, common administrator | Source distinction retained; COMMON_CONTROL_DETECTED |
| TP-12 | Missing custody transfer | Custody UNKNOWN; administrative separation UNKNOWN |
| TP-13 | Transfer sequence inconsistent with capture | Custody UNKNOWN |
| TP-14 | Witness artifact modeled compromised before capture | Capture-order proof UNKNOWN; administrative compromise explicitly reported |
| TP-15 | Custody actor compromised after modeled capture, no authenticated earlier reference | COMPROMISED_BY_SCENARIO; historical authenticity remains NOT_ESTABLISHED |
| TP-16 | Frozen laboratory capture sequence precedes modeled candidate mutation | LAB_BEFORE_MUTATION **only**; *no actual ledger discrepancy is asserted by this graph analyzer* |
| TP-17 | Candidate/witnesses/controller fully compromised | Custody, admin, source, capture results UNKNOWN |
| TP-18 | Artifact replay across unrelated scope | Scope conflict; no conditional separation |
| TP-19 | Witness artifact identity substitution/duplicate | INVALID_INPUT; no independence inference |
| TP-20 | Cyclic source-provenance self-justification | Source independence UNKNOWN |
| TP-21 | Same artifact nominated twice | INVALID_INPUT; no duplicate evidence inflation |
| TP-22 | Two conflicting holders for one artifact | Custody UNKNOWN; no favorable default |
| TP-23 | Graph node/edge permutation | Identical report |
| TP-24 | Duplicate node/edge IDs, resource bound violation | Typed bounded failure |
| TP-25 | Prior favorable TB-002 audit masquerades as new provenance | Untrusted derived claim only |
| TP-26 | Provenance result used as Truth/Identity/Authorization/Evidence | No M0 adapter; fixed non-authorizing limits |

Fifteen additional regression controls include source-alias identity, unsupported origins, profile/version failures, incomplete source coverage, absent mutation order, explicit compromise interval errors, control cycles and determinism.

## 6. Laboratory limitations and research scope correction

1. A trusted reference is **assumed**, never cryptographically established. The `LAB` tag and `completeness_origin` may be forged in the real world.
2. `capture_sequence` and `CompromiseInterval` are model ordering fields, not verified wall-clock time.
3. The graph does not import historical ledger bytes or TB-002 comparator results. It cannot prove a physical mutation or checkpoint correspondence. TP-16 validates **modeled ordering only**; actual byte discrepancies remain TB-001/TB-002's task. Cross-component consistency/admission is not provided.
4. A `RESTORES_FROM` edge represents a specified potential restoration input; no claim is made that a backup automatically corrupts a primary without such an edge.
5. Missing or unknown external edges are not exhaustively discoverable: conditional separation is **relative to the controller's completeness assumption**.
6. `support_ref` values, storage object IDs and external scope are fixed test strings, not externally authenticated objects.
7. Cyclic source dependencies do not become independent source evidence; unresolvable paths fail closed.
8. No conclusion about genuine historical events, personhood, persistent entity identity or consciousness follows.

## 7. Implementation limits and verification

In-memory dataclasses and a bounded graph are used. The program does not perform filesystem, network, subprocess or crypto-signature operations. Limits: at most two witness artifacts, 64 nodes, 128 frozen edges, 128 presented claims, 32 artifact nodes, path depth 16, 128 KiB approximate encoded data size, ASCII limited identifiers/labels, sequence values 0..1,000,000. Invalid types/IDs/edges fail with `INVALID_*` reason codes and nonpositive findings. None of the bounds truncate a result into positive conditional separation.

New files only:

```text
implementation/witness_provenance_experiment.py
implementation/tests/test_witness_provenance_experiment.py
implementation/WITNESS_PROVENANCE_EXPERIMENT_V0_1.md
```

The initial assistant sandbox ran this TB-003 test module using Python 3.13 and pytest with `-B`/`-p no:cacheprovider`; the actual observed count and SHA256 of these files are recorded in the delivery manifest and handoff. **No full Ario repository suite, real Windows integration, GitHub CI, production custody test or real-key test was run in that sandbox.**

When importing into the user's Windows clone, require: exact baseline check; preservation of all tracked/untracked artifacts; unique scratch directory; no overwrite of existing paths; targeted tests plus previous TB-001/TB-002 and full implementation regression; staged-path inspection; no commit/push without further explicit approval. Unknown/failed outcomes must be retained, never forced to PASS.

## 8. Acceptance and non-closure

The exact 26 pre-registered cases and additional guards must pass with the actual Ario Python/pytest environment. Existing TB-001/TB-002 and full regression must remain passing. A future independent threat-model review should challenge the control completeness and custody assumptions before any expanded claim.

**Even complete laboratory acceptance never equals production witness authentication.** No result creates signing/reviewer authority, admissible evidence, or global Claim truth. Independent custody, independent observation and historical event truth remain separate, contestable questions.
