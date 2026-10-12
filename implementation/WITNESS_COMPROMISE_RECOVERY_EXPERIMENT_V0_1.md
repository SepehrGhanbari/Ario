# ARIO-TB-004 — Witness Compromise, Temporal Trust & Recovery (v0.1)

**State:** BOUNDED SYNTHETIC IMPLEMENTATION CANDIDATE; NOT PRODUCTION-DEPLOYED.
**Baseline:** `SepehrGhanbari/Ario` main after PR #65, `24bd7c1108b8a22456b2e6f5cd14826be3086afe`.
**Scope of delivery:** New module, new test module, new document. No changes to existing TB-001/TB-002/TB-003 or Ario M0, IRG, signer, ledger, or Trust Anchor.

## 1. Exact research boundary

Under a **declared complete synthetic laboratory controller model**, evaluate the effect of suspected/confirmed witness compromise and proposed recovery on the *limited, present usability of a specified checkpoint correspondence*, while retaining original artifacts and earlier evaluation records.

The experiment does not authenticate the laboratory controller, independent custody, physical clock, true compromise, any actual historical event, or a recovered public-key enrollment. **Never interpret a pass as a safe production recovery or trusted history.**

Core distinctions:

- `RECORDED_HISTORY != CURRENT_EVIDENTIARY_USABILITY`
- `DISCOVERY_OF_COMPROMISE != ONSET_OF_COMPROMISE`
- `REVISION != ERASURE`
- `NEW_LAB_EPOCH != AUTHENTICATED_NEW_ROOT`
- `RECOVERY != RETROACTIVE_AUTHENTICITY`

## 2. Inputs and output

The read-only, deterministic function is:

```python
from witness_compromise_recovery_experiment import evaluate_recovery
report = evaluate_recovery(case)  # RecoveryCase -> RecoveryReport
```

Typed experimental input includes:

- `WitnessEpoch`: exact witness, ledger scope, model control root, start sequence and predecessor epoch reference.
- `HistoricalArtifact`: exact artifact/witness/epoch/scope, synthetic capture sequence and lowercase SHA256 commitment. **Bytes are not revalidated against any actual ledger**; the digest is metadata for laboratory binding.
- `FrozenReference`: an explicitly LAB-origin reference to an artifact/digest, with modeled retention sequence, custody root and controller-declared separation/completeness. It is neither a signature nor an independent physical snapshot.
- `CompromiseObservation`: typed `SUSPECTED`, `CONFIRMED_WINDOW`, or `REFUTATION` finding about an epoch, witness or control root, plus discovery time, modeled onset bounds, origin and support ID.
- `SuspensionEvent`: versioned LAB `SUSPEND` marker. No implicit `UNSUSPEND` is supported.
- `RecoveryProposal`: predecessor/successor binding, laboratory model control separation and independently supplied **LAB-origin assumed** enrollment basis. No real key issuance.
- `PriorEvaluation`: immutable-structured earlier limited verdicts, optionally linked by exact supersession IDs.
- `RecoveryCase`: complete controlled inputs, exact target, named property `CHECKPOINT_CORRESPONDENCE`, evaluation sequence and laboratory compromise-inventory completeness declaration.

`RecoveryReport` separates:

1. `compromise_knowledge` — confirmed *by lab control*, suspected, contradictory, unresolved, or not established under declared completeness.
2. `capture_window_relation` — before earliest plausible onset, after a known-by bound, uncertain/within window, or unknown.
3. `frozen_preservation` — conditional LAB-origin retained-reference match, definite conditional digest mismatch, or unknown.
4. `evidentiary_usability` — conditional usability only for the named comparison, suspension, rejection for that use, insufficient support, or invalid input.
5. `epoch_lifecycle` — proposed, active, frozen, superseded, or unknown **inside the lab model only**.
6. `recovery_assessment` — conditional successor epoch, insufficient recovery requirements, not applicable, or unknown.
7. `conflicts`, `unsupported_observations`, `original_artifacts`, `original_evaluations`, `new_evaluation` and deterministic reason codes.

A generated evaluation ID is the SHA256 digest prefix of a canonical **diagnostic payload**. This is not a cryptographic signature, genuine append-only guarantee or historical evidence.

## 3. Sequence and compromise window semantics

All integer sequences are laboratory order labels, not wall-clock timestamps.

A `CONFIRMED_WINDOW` has:

- `earliest_onset_sequence`: a *lower bound* on plausible onset, when known; `None` means no trustworthy lower bound even inside the lab inputs.
- `confirmed_by_sequence`: the modeled upper bound by which compromise is known to have occurred.
- `discovery_sequence`: when the observation becomes available to the evaluator. Must not be earlier than `confirmed_by_sequence`.

A target captured **strictly before** the lower onset bound can remain usable for a *named historical correspondence* only when a LAB-origin, separately controlled matching reference was also retained **strictly before** that bound, and inventory completeness assumptions are declared. The old witness epoch may nevertheless be frozen or superseded for future issuance.

A target captured at or after the upper bound is classified as not preceding compromise. Intermediate intervals and missing lower bounds are unresolved. Conflicting onset windows are preserved as explicit conflicts; no favorable window is selected.

Untrusted self-reported dates cannot establish onset. A later LAB refutation of a specific `SUSPECTED` observation may change the current status but leaves that original suspicion present in the input history. A refutation of `CONFIRMED_WINDOW` creates an explicit conflict rather than silently clearing the compromised state.

Observation records with discovery after the evaluation sequence are not used for that historical evaluation snapshot, and never backdated. Actual physical time remains `NOT_CHECKED` in every report.

## 4. Recovery state transition

An experimental recovery creates a **successor epoch**; it does not reactivate its predecessor. For `LAB_CONDITIONALLY_RECOVERED`, *all* of the following modeled conditions must be present:

1. Successor epoch's exact predecessor and sequence bindings are valid.
2. A relevant LAB-origin suspicion, confirmed compromise or suspension for the predecessor was recorded **no later than** the proposed recovery sequence.
3. The proposal and enrollment basis are LAB-origin (test-controller declarations, not cryptographic proof).
4. The proposal declares a complete control surface and `LAB_CONDITIONALLY_SEPARATE`.
5. The successor's control-root ID differs from the predecessor root ID (not proof of physical separation).
6. Exactly one relevant supported proposal is present; competing proposals are not resolved by choosing the favorable one.
7. The model controller is not marked compromised, and the successor has no active modeled suspicion, confirmed compromise or suspension.

A *favorable usability outcome for a successor artifact* additionally requires a matching LAB-origin, modeled separately controlled reference, its own admissible retention order, and declared complete LAB compromise inventory. This does **not** authenticate the new custody root.

An old epoch may be marked `EPOCH_SUPERSEDED_IN_LAB_MODEL`; that is not an archival deletion and does not imply earlier event truth. Complete controller compromise disables affirmative outcomes. No cryptographic grants, actual revocations, new keys, or privileged transitions are produced.

## 5. Preservation model and limitations

Inputs are frozen Python dataclasses, but are supplied by the caller. The evaluator cannot stop a malicious caller from replacing an entire historical input set. A caller can forge `LAB` origin tags, custody-root names and a supposed complete inventory; the experiment assumes the external test controller excludes that adversary except in explicitly compromised cases.

The optional `expected_previous_evaluation_id` checks an exact predecessor reference inside the supplied earlier-evaluation collection. Without separately retained authentic evidence, it **cannot prove** that a prior result was not deleted from storage. It only catches inconsistency with the declared test reference. Prior evaluation chains must be unambiguous for the target; the returned evaluation is new and separately referenceable, not automatically persisted.

If a LAB-origin, modeled independently retained reference disagrees with a candidate artifact's SHA256, the named comparison is rejected (`REJECTED_FOR_NAMED_USE`) and the exact conflict is retained. A compromised reference root cannot supply such a definitive contradiction in this model.

A syntactically valid hash chain, signing-looking bytes, duplicated witness reports, CI success, or model-generated verdict must not be elevated to independent real-world corroboration.

## 6. Always-fixed, non-authorizing report fields

```text
production_custody_authenticity   = NOT_ESTABLISHED
cryptographic_authentication     = NOT_CHECKED
trusted_physical_time            = NOT_CHECKED
actual_revocation                = NOT_PERFORMED
human_authorization              = NOT_EVALUATED
evidence_admission               = NOT_EVALUATED
historical_event_truth           = UNKNOWN
entity_continuity                = UNKNOWN
ontological_continuity           = UNKNOWN
production_historical_continuity = INCONCLUSIVE
```

No adapter into M0 Evidence, Assessment, AuditResult, reviewer authorization, trust-root enrollment, signer, archive writing, network or agent autonomy exists.

## 7. Pre-registered adversarial scenarios (TC-01..TC-32)

| ID | Controlled scenario | Mandatory bounded observation |
|---|---|---|
| TC-01 | No compromise asserted, independent pin absent | INSUFFICIENT_SUPPORT |
| TC-02 | Independent LAB pin, complete controlled inventory, no observed compromise | Conditional named correspondence only |
| TC-03 | Later discovery, onset lower bound unknown | No invented compromise start; suspended use |
| TC-04 | Capture inside plausible onset window | Suspended |
| TC-05 | Capture at or after upper onset bound | Suspended |
| TC-06 | Well-formed digest under compromise | No provenance/trust promotion |
| TC-07 | Locally changed commitment disagrees with preserved LAB digest | Named correspondence rejected, history truth unknown |
| TC-08 | Capture AND external reference retained before lower onset bound | Narrow historical correspondence may remain conditional |
| TC-09 | Old reference kept only under compromised control | Preservation UNKNOWN; suspended |
| TC-10 | Witness self-reports an onset date | Self-report not accepted as LAB boundary |
| TC-11 | Disjoint LAB confirmed onset windows | Contradictory evidence retained; suspended |
| TC-12 | No independently verified physical clock | Trusted time NOT_CHECKED |
| TC-13 | Compromised witness issues own recovery | No conditional new epoch |
| TC-14 | Replacement label but same root | No conditional recovery |
| TC-15 | New storage with declared common writable control path | No conditional recovery |
| TC-16 | Relevant old freeze plus complete separate LAB recovery scenario | Only successor LAB epoch may be conditional |
| TC-17 | New epoch repeats historical digest | Does not validate old events |
| TC-18 | Recovery control inventory incomplete | UNKNOWN; no new authority |
| TC-19 | New observations contradict prior favorable evaluation | Preserve original; explicit supersession |
| TC-20 | Expected old evaluation withheld | Controlled missing-reference error, not proof of intact archive |
| TC-21 | Recovery artifact replay across scope | Invalid binding |
| TC-22 | Multiple witness labels share compromised root | No majority-based recovery |
| TC-23 | Previous favorable report used as recovery enrollment | Unsupported derived evidence |
| TC-24 | Multiple competing recovery proposals | Conflict and nonpositive usability |
| TC-25 | LAB controller compromised | No favorable custody/epoch/use claims |
| TC-26 | Cyclic or impossible predecessor relationship | Invalid input |
| TC-27 | Observation ordering permutation | Same substantive report |
| TC-28 | Duplicate, malformed, unsupported, oversized cases | Bounded refusal |
| TC-29 | Recovery report presented as truth/authority | No M0/permission interface |
| TC-30 | Later, specific, LAB-origin refutation of suspicion | New evaluation may improve; suspicion retained |
| TC-31 | Later refutation withheld from earlier snapshot | Historical evaluation cannot know future observation |
| TC-32 | Independently pinned digest contradicts candidate metadata | Exact mismatch; rejected for named comparison |

Additional hardening cases cover compromised reference roots, mixed matching and conflicting pins, malformed unhashable origins, unsupported requested properties, missing predecessor freeze, historical-evaluation ownership/scope, timing order, hidden reinstatement, deterministic repeatability, and source-module isolation.

## 8. Input bounds

- Maximum two distinct witnesses and four total epochs.
- Maximum 16 named artifacts and 16 modeled retained references.
- Maximum 32 compromise observations and 32 combined suspension/recovery events.
- Maximum 32 previous evaluation records, with a bounded aggregate structural item check (64 + 32 + 32 allowances).
- Maximum 128 KiB approximate in-memory structured input text, 128 printable ASCII characters per identifier and sequence integers in `[0, 1000000]`.
- No silent truncation that could yield positive evidence.

Malformed/unknown types or identifiers produce `INVALID_INPUT`; unsupported scope, profile, policy, property or role must not fall through to a favorable decision. No external data is fetched or read by the evaluator.

## 9. Reproduction and governance

New paths only:

1. `implementation/witness_compromise_recovery_experiment.py`
2. `implementation/tests/test_witness_compromise_recovery_experiment.py`
3. `implementation/WITNESS_COMPROMISE_RECOVERY_EXPERIMENT_V0_1.md`

The stand-alone sandbox test suite exercises **53 tests** (32 named scenarios plus 21 additional controls), using Python 3.13 and pytest with cache and bytecode output disabled. This does **not** substitute for integration against the actual Windows Ario checkout. The exact current package hashes, test output, and validation script are distributed separately in the handoff package.

Recommended reproduction procedure: verify ZIP manifest SHA256 and exact filenames; use a unique scratch outside the repository; export tracked `HEAD` by `git archive` to an isolated scratch checkout, add the three new TB-004 files only to the isolated checkout, and run all four TB test files and the entire implementation suite there; record JUnit reports. Preserve all original untracked material, including runtime ledgers and signer experiments.

No Git status change, commit or push is authorized by the code delivery. Any subsequent integration to `main` must use a separately approved isolated branch, full regression, PR and GitHub CI. Never bypass protection rules.

## 10. Falsification criteria and unresolved questions

The implementation must be revised (without weakening the claims boundary) if a test can:

- make an incomplete/compromised control model appear verified;
- convert a late compromise discovery into an invented earlier date;
- make a new witness label resurrect an untrusted predecessor;
- overwrite an original record instead of appending a superseding evaluation;
- discard an independent conflicting reference via majority choice;
- upgrade an experimental report into trusted evidence, human permission or historical truth.

Real-world recovery remains unimplemented pending independent enrollment, actual clock/custody attestation, authenticated historical reference retention, revocation governance and cross-IRG review.

**Final bound:** `HISTORICAL RECORD != CURRENT TRUST ASSESSMENT`; `REVISION != ERASURE`; `RECOVERY != PROOF OF THE PAST`.
