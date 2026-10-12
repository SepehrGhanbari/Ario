"""ARIO-TB-004 v0.2: bounded synthetic compromise/recovery, evidence-bound evaluations.

All identities, control facts, evidence origins, sequencing and retention in this
experiment are LABORATORY DECLARATIONS, not real-world authenticated claims.
This module has no filesystem, network, signing, authority, M0 or ledger adapter.
It returns a new assessment; existing artifacts/evaluations are never mutated.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from typing import Any

PROFILE = "ARIO-WITNESS-COMPROMISE-EXPERIMENT-0.2"
POLICY = "ARIO-TB4-LAB-POLICY-0.2"
LAB = "FROZEN_TEST_CONTROLLER_REFERENCE"
CANDIDATE = "CANDIDATE_SUPPLIED"
SELF = "WITNESS_SELF_DECLARATION"
DERIVED = "DERIVED_COMPARISON_RESULT"
UNKNOWN_ORIGIN = "UNRESOLVED_ORIGIN"
ORIGINS = frozenset((LAB, CANDIDATE, SELF, DERIVED, UNKNOWN_ORIGIN))
MAX_EPOCHS = 4
MAX_ARTIFACTS = 16
MAX_REFERENCES = 16
MAX_OBSERVATIONS = 32
MAX_EVENTS = 32
MAX_EVALUATIONS = 32
MAX_DEPENDENCIES = 64
MAX_BYTES = 131072
MAX_SEQUENCE = 1000000


@dataclass(frozen=True)
class WitnessEpoch:
    epoch_id: str
    witness_id: str
    scope: str
    control_root: str
    start_sequence: int
    predecessor_epoch_id: str | None = None


@dataclass(frozen=True)
class HistoricalArtifact:
    artifact_id: str
    witness_id: str
    epoch_id: str
    scope: str
    capture_sequence: int
    checkpoint_sha256: str


@dataclass(frozen=True)
class FrozenReference:
    """LAB-DECLARED separate reference, never a cryptographic attestation."""

    reference_id: str
    artifact_id: str
    checkpoint_sha256: str
    retention_sequence: int
    custody_control_root: str
    control_relation: str  # LAB_CONDITIONALLY_SEPARATE / COMMON_CONTROL_DETECTED / UNKNOWN
    control_surface_complete: bool
    origin: str
    support_ref: str


@dataclass(frozen=True)
class CompromiseObservation:
    observation_id: str
    target_kind: str  # EPOCH / WITNESS / CONTROL_ROOT
    target_id: str
    kind: str  # SUSPECTED / CONFIRMED_WINDOW / REFUTATION
    discovery_sequence: int
    earliest_onset_sequence: int | None
    confirmed_by_sequence: int | None
    origin: str
    support_ref: str
    refutes_observation_id: str | None = None


@dataclass(frozen=True)
class SuspensionEvent:
    event_id: str
    epoch_id: str
    sequence: int
    origin: str
    support_ref: str
    kind: str = "SUSPEND"


@dataclass(frozen=True)
class RecoveryProposal:
    proposal_id: str
    predecessor_epoch_id: str
    successor_epoch_id: str
    sequence: int
    origin: str
    control_separation: str  # LAB_CONDITIONALLY_SEPARATE / COMMON_CONTROL_DETECTED / UNKNOWN
    complete_control_surface: bool
    enrollment_origin: str
    enrollment_support_ref: str
    support_ref: str


@dataclass(frozen=True)
class PriorEvaluation:
    evaluation_id: str
    artifact_id: str
    epoch_id: str
    sequence: int
    policy: str
    usability: str
    supersedes_evaluation_id: str | None
    origin: str
    support_ref: str
    evidence_digest: str  # deterministic digest of the original declared case, NOT a signature
    reason_codes: tuple[str, ...]  # declared prior assessment, needed for self-consistency check


@dataclass(frozen=True)
class RecoveryCase:
    scope: str
    epochs: tuple[WitnessEpoch, ...]
    artifacts: tuple[HistoricalArtifact, ...]
    frozen_references: tuple[FrozenReference, ...]
    observations: tuple[CompromiseObservation, ...]
    suspensions: tuple[SuspensionEvent, ...]
    recovery_proposals: tuple[RecoveryProposal, ...]
    prior_evaluations: tuple[PriorEvaluation, ...]
    target_artifact_id: str
    evaluation_sequence: int
    complete_compromise_inventory: bool = False
    completeness_origin: str = UNKNOWN_ORIGIN
    controller_compromised: bool = False
    expected_previous_evaluation_id: str | None = None  # controller-supplied lab check, not live proof
    requested_property: str = "CHECKPOINT_CORRESPONDENCE"
    profile: str = PROFILE
    policy: str = POLICY


@dataclass(frozen=True)
class Finding:
    status: str
    reason: str
    support: tuple[str, ...] = ()


@dataclass(frozen=True)
class RecoveryEvaluation:
    evaluation_id: str
    artifact_id: str
    epoch_id: str
    sequence: int
    policy: str
    usability: str
    supersedes_evaluation_id: str | None
    reason_codes: tuple[str, ...]
    evidence_digest: str  # SHA256 over the complete v0.2 synthetic input case


@dataclass(frozen=True)
class RecoveryReport:
    compromise_knowledge: Finding
    capture_window_relation: Finding
    frozen_preservation: Finding
    evidentiary_usability: Finding
    epoch_lifecycle: Finding
    recovery_assessment: Finding
    conflicts: tuple[str, ...]
    unsupported_observations: tuple[str, ...]
    original_artifacts: tuple[HistoricalArtifact, ...]
    original_evaluations: tuple[PriorEvaluation, ...]
    new_evaluation: RecoveryEvaluation | None
    reason_codes: tuple[str, ...]
    kind: str = field(default="EXPERIMENTAL_COMPROMISE_RECOVERY_V0_2", init=False)
    production_custody_authenticity: str = field(default="NOT_ESTABLISHED", init=False)
    cryptographic_authentication: str = field(default="NOT_CHECKED", init=False)
    trusted_physical_time: str = field(default="NOT_CHECKED", init=False)
    actual_revocation: str = field(default="NOT_PERFORMED", init=False)
    human_authorization: str = field(default="NOT_EVALUATED", init=False)
    evidence_admission: str = field(default="NOT_EVALUATED", init=False)
    historical_event_truth: str = field(default="UNKNOWN", init=False)
    entity_continuity: str = field(default="UNKNOWN", init=False)
    ontological_continuity: str = field(default="UNKNOWN", init=False)
    production_historical_continuity: str = field(default="INCONCLUSIVE", init=False)


def _f(status: str, reason: str, *support: str) -> Finding:
    return Finding(status, reason, tuple(sorted(set(support))))


def _id(value: Any) -> bool:
    return type(value) is str and 0 < len(value) <= 128 and all(32 <= ord(c) <= 126 for c in value)


def _seq(value: Any) -> bool:
    return type(value) is int and 0 <= value <= MAX_SEQUENCE


def _origin(value: Any) -> bool:
    return type(value) is str and value in ORIGINS


def _hex(value: Any) -> bool:
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _canonical(value: Any) -> bytes:
    """Strict deterministic bytes. These bytes do not authenticate a source."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _case_digest(case: RecoveryCase) -> str:
    """Bind every v0.2 input field, not merely the positive-looking result.

    The input collections are sets by unique declared ID. Canonical order is
    independent of input tuple permutation (as in v0.1's scenario TC-27).
    This includes unrelated-but-present declarations; a changed declared
    evidentiary *case* must produce a new assessment identity.
    """
    data = asdict(case)
    keys = {
        "epochs": "epoch_id", "artifacts": "artifact_id",
        "frozen_references": "reference_id", "observations": "observation_id",
        "suspensions": "event_id", "recovery_proposals": "proposal_id",
        "prior_evaluations": "evaluation_id",
    }
    for collection, key in keys.items():
        data[collection] = sorted(data[collection], key=lambda item: item[key])
    return sha256(_canonical({"domain": "ARIO-TB4-CASE-V0.2", "case": data})).hexdigest()


def _evaluation_id(artifact_id: str, epoch_id: str, sequence: int, policy: str,
                   usability: str, previous: str | None, reasons: tuple[str, ...],
                   evidence_digest: str) -> str:
    """Locally self-consistent identifier, not authenticated custody or history."""
    payload = {
        "domain": "ARIO-TB4-EVALUATION-V0.2", "profile": PROFILE,
        "artifact": artifact_id, "epoch": epoch_id, "sequence": sequence,
        "property": "CHECKPOINT_CORRESPONDENCE", "policy": policy,
        "usability": usability, "supersedes": previous,
        "reasons": reasons, "evidence_digest": evidence_digest,
    }
    return "TB4-V02-EVAL-" + sha256(_canonical(payload)).hexdigest()


def _prior_is_self_consistent(prior: PriorEvaluation) -> bool:
    if not _hex(prior.evidence_digest):
        return False
    if (type(prior.reason_codes) is not tuple or
        not all(type(r) is str and 0 < len(r) <= 256 and
                all(32 <= ord(ch) <= 126 for ch in r) for r in prior.reason_codes) or
        len(prior.reason_codes) != len(set(prior.reason_codes)) or
        tuple(sorted(prior.reason_codes)) != prior.reason_codes):
        return False
    return prior.evaluation_id == _evaluation_id(
        prior.artifact_id, prior.epoch_id, prior.sequence, prior.policy,
        prior.usability, prior.supersedes_evaluation_id,
        prior.reason_codes, prior.evidence_digest,
    )


def _invalid(reason: str, case: Any = None) -> RecoveryReport:
    u = _f("INVALID_INPUT", reason)
    artifacts = case.artifacts if type(case) is RecoveryCase and type(case.artifacts) is tuple else ()
    old = case.prior_evaluations if type(case) is RecoveryCase and type(case.prior_evaluations) is tuple else ()
    return RecoveryReport(u, u, u, u, u, u, (), (), artifacts, old, None, (reason,))


def _validate(case: Any) -> str | None:
    if type(case) is not RecoveryCase:
        return "INVALID_CASE_TYPE"
    if case.profile != PROFILE or case.policy != POLICY or case.requested_property != "CHECKPOINT_CORRESPONDENCE":
        return "UNSUPPORTED_PROFILE_POLICY_OR_PROPERTY"
    if not _id(case.scope) or not _id(case.target_artifact_id) or not _seq(case.evaluation_sequence):
        return "INVALID_SCOPE_TARGET_OR_TIME"
    if case.expected_previous_evaluation_id is not None and not _id(case.expected_previous_evaluation_id):
        return "INVALID_PREVIOUS_EVALUATION_REFERENCE"
    lists = (
        (case.epochs, MAX_EPOCHS, WitnessEpoch),
        (case.artifacts, MAX_ARTIFACTS, HistoricalArtifact),
        (case.frozen_references, MAX_REFERENCES, FrozenReference),
        (case.observations, MAX_OBSERVATIONS, CompromiseObservation),
        (case.suspensions, MAX_EVENTS, SuspensionEvent),
        (case.recovery_proposals, MAX_EVENTS, RecoveryProposal),
        (case.prior_evaluations, MAX_EVALUATIONS, PriorEvaluation),
    )
    if (type(case.complete_compromise_inventory) is not bool or
        type(case.controller_compromised) is not bool or not _origin(case.completeness_origin)):
        return "INVALID_CONTROL_CONFIGURATION"
    for items, maximum, cls in lists:
        if type(items) is not tuple or len(items) > maximum or any(type(x) is not cls for x in items):
            return "INVALID_COLLECTION_OR_BOUND"
    if not 1 <= len(case.epochs) <= MAX_EPOCHS or not 1 <= len(case.artifacts) <= MAX_ARTIFACTS:
        return "INVALID_EMPTY_MODEL"
    if len(case.suspensions) + len(case.recovery_proposals) > MAX_EVENTS:
        return "TOO_MANY_LIFECYCLE_EVENTS"
    # Exact declarative data only; no parser that would reinterpret user-controlled text.
    items = tuple(x for seq, _, _ in lists for x in seq)
    if sum(len(str(v)) for o in items for v in vars(o).values()) > MAX_BYTES:
        return "OVERSIZED_INPUT"
    ep: dict[str, WitnessEpoch] = {}
    for e in case.epochs:
        if (not all(_id(v) for v in (e.epoch_id, e.witness_id, e.scope, e.control_root)) or
            not _seq(e.start_sequence) or
            (e.predecessor_epoch_id is not None and not _id(e.predecessor_epoch_id)) or
            e.epoch_id in ep or e.scope != case.scope):
            return "INVALID_OR_DUPLICATE_EPOCH"
        ep[e.epoch_id] = e
    if len({e.witness_id for e in case.epochs}) > 2:
        return "TOO_MANY_WITNESSES"
    for e in case.epochs:
        if e.predecessor_epoch_id is not None:
            parent = ep.get(e.predecessor_epoch_id)
            if parent is None or parent.epoch_id == e.epoch_id or parent.start_sequence >= e.start_sequence:
                return "INVALID_EPOCH_PREDECESSOR_OR_ORDER"
    arts: dict[str, HistoricalArtifact] = {}
    for a in case.artifacts:
        if (not all(_id(v) for v in (a.artifact_id, a.witness_id, a.epoch_id, a.scope)) or
            not _seq(a.capture_sequence) or not _hex(a.checkpoint_sha256) or a.artifact_id in arts):
            return "INVALID_OR_DUPLICATE_ARTIFACT"
        parent = ep.get(a.epoch_id)
        if (parent is None or parent.witness_id != a.witness_id or a.scope != case.scope or
            a.capture_sequence < parent.start_sequence):
            return "INVALID_ARTIFACT_EPOCH_SCOPE"
        arts[a.artifact_id] = a
    if case.target_artifact_id not in arts:
        return "MISSING_TARGET_ARTIFACT"
    if case.evaluation_sequence < arts[case.target_artifact_id].capture_sequence:
        return "EVALUATION_PRECEDES_ARTIFACT"
    globalids = set(ep) | set(arts)
    if len(globalids) != len(ep) + len(arts):
        return "COLLIDING_EPOCH_ARTIFACT_ID"
    refs = set()
    for r in case.frozen_references:
        if (not all(_id(v) for v in (r.reference_id, r.artifact_id, r.custody_control_root, r.support_ref)) or
            not _hex(r.checkpoint_sha256) or not _seq(r.retention_sequence) or
            type(r.control_surface_complete) is not bool or
            not _origin(r.origin) or
            r.control_relation not in ("LAB_CONDITIONALLY_SEPARATE", "COMMON_CONTROL_DETECTED", "UNKNOWN") or
            r.artifact_id not in arts or r.reference_id in refs):
            return "INVALID_OR_DUPLICATE_REFERENCE"
        refs.add(r.reference_id)
    obids: set[str] = set()
    for o in case.observations:
        if (not all(_id(v) for v in (o.observation_id, o.target_id, o.support_ref)) or
            o.observation_id in obids or o.target_kind not in ("EPOCH", "WITNESS", "CONTROL_ROOT") or
            o.kind not in ("SUSPECTED", "CONFIRMED_WINDOW", "REFUTATION") or
            not _origin(o.origin) or not _seq(o.discovery_sequence) or
            (o.earliest_onset_sequence is not None and not _seq(o.earliest_onset_sequence)) or
            (o.confirmed_by_sequence is not None and not _seq(o.confirmed_by_sequence)) or
            (o.refutes_observation_id is not None and not _id(o.refutes_observation_id))):
            return "INVALID_OBSERVATION"
        if o.target_kind == "EPOCH" and o.target_id not in ep:
            return "UNKNOWN_OBSERVATION_EPOCH"
        if o.target_kind == "EPOCH" and o.discovery_sequence < ep[o.target_id].start_sequence:
            return "OBSERVATION_BEFORE_EPOCH"
        if o.target_kind == "WITNESS" and o.target_id not in {e.witness_id for e in case.epochs}:
            return "UNKNOWN_OBSERVATION_WITNESS"
        if o.target_kind == "CONTROL_ROOT" and o.target_id not in {e.control_root for e in case.epochs} | {r.custody_control_root for r in case.frozen_references}:
            return "UNKNOWN_OBSERVATION_ROOT"
        if o.kind == "CONFIRMED_WINDOW":
            if (o.confirmed_by_sequence is None or o.confirmed_by_sequence > o.discovery_sequence or
                (o.earliest_onset_sequence is not None and o.earliest_onset_sequence > o.confirmed_by_sequence) or
                o.refutes_observation_id is not None):
                return "INVALID_CONFIRMED_WINDOW"
        elif o.kind == "REFUTATION":
            if (o.refutes_observation_id is None or o.earliest_onset_sequence is not None or
                o.confirmed_by_sequence is not None):
                return "INVALID_REFUTATION"
        elif o.refutes_observation_id is not None:
            return "INVALID_SUSPICION"
        obids.add(o.observation_id)
    obmap = {o.observation_id:o for o in case.observations}
    for o in case.observations:
        if o.kind == "REFUTATION":
            prior = obmap.get(o.refutes_observation_id)
            if (prior is None or prior.kind not in ("SUSPECTED", "CONFIRMED_WINDOW") or
                o.discovery_sequence <= prior.discovery_sequence or
                prior.target_kind != o.target_kind or prior.target_id != o.target_id):
                return "INVALID_REFUTATION_DEPENDENCY"
    suspids, propids = set(),set()
    for s in case.suspensions:
        if (not _id(s.event_id) or not _id(s.epoch_id) or not _id(s.support_ref) or
            not _seq(s.sequence) or not _origin(s.origin) or s.kind != "SUSPEND" or
            s.epoch_id not in ep or s.sequence < ep[s.epoch_id].start_sequence or
            s.event_id in suspids):
            return "INVALID_SUSPENSION"
        suspids.add(s.event_id)
    for p in case.recovery_proposals:
        if (not all(_id(v) for v in (p.proposal_id,p.predecessor_epoch_id,p.successor_epoch_id,p.enrollment_support_ref,p.support_ref)) or
            not _seq(p.sequence) or not _origin(p.origin) or not _origin(p.enrollment_origin) or
            p.control_separation not in ("LAB_CONDITIONALLY_SEPARATE","COMMON_CONTROL_DETECTED","UNKNOWN") or
            type(p.complete_control_surface) is not bool or p.proposal_id in propids or
            p.predecessor_epoch_id not in ep or p.successor_epoch_id not in ep):
            return "INVALID_RECOVERY_PROPOSAL"
        if (ep[p.successor_epoch_id].predecessor_epoch_id != p.predecessor_epoch_id or
            ep[p.successor_epoch_id].start_sequence != p.sequence):
            return "RECOVERY_EPOCH_OR_SEQUENCE_MISMATCH"
        propids.add(p.proposal_id)
    evaluationids, evalmap = set(),{}
    for e in case.prior_evaluations:
        if (not all(_id(v) for v in (e.evaluation_id,e.artifact_id,e.epoch_id,e.policy,e.usability,e.support_ref)) or
            (e.supersedes_evaluation_id is not None and not _id(e.supersedes_evaluation_id)) or
            not _seq(e.sequence) or not _origin(e.origin) or e.evaluation_id in evaluationids or
            e.artifact_id not in arts or e.epoch_id != arts[e.artifact_id].epoch_id or
            e.sequence < arts[e.artifact_id].capture_sequence or e.policy != POLICY or e.usability not in (
                "CONDITIONALLY_USABLE_FOR_NAMED_COMPARISON","SUSPENDED","INSUFFICIENT_SUPPORT","REJECTED_FOR_NAMED_USE","NOT_EVALUATED")):
            return "INVALID_PRIOR_EVALUATION"
        if not _prior_is_self_consistent(e):
            return "PRIOR_EVALUATION_CONTENT_BINDING_MISMATCH"
        evaluationids.add(e.evaluation_id)
        evalmap[e.evaluation_id] = e
    usedparents = set()
    for e in case.prior_evaluations:
        if e.supersedes_evaluation_id:
            parent = evalmap.get(e.supersedes_evaluation_id)
            if (parent is None or parent.artifact_id != e.artifact_id or parent.sequence >= e.sequence or
                parent.evaluation_id in usedparents):
                return "INVALID_EVALUATION_CHAIN"
            usedparents.add(parent.evaluation_id)
    target_old = tuple(e for e in case.prior_evaluations if e.artifact_id == case.target_artifact_id)
    if target_old and any(e.origin != LAB for e in target_old):
        return "NON_LAB_PRIOR_CANNOT_SUPPLY_HEAD"
    if target_old and case.expected_previous_evaluation_id is None:
        return "MISSING_CONTROLLER_DECLARED_PRIOR_HEAD"
    if case.expected_previous_evaluation_id is not None:
        expected = evalmap.get(case.expected_previous_evaluation_id)
        if expected is None:
            return "EXPECTED_HISTORICAL_EVALUATION_MISSING"
        if expected.artifact_id != case.target_artifact_id or expected.sequence >= case.evaluation_sequence:
            return "EXPECTED_HISTORICAL_EVALUATION_WRONG_SCOPE_OR_TIME"
        if expected.origin != LAB:
            return "NON_LAB_PRIOR_CANNOT_SUPPLY_HEAD"
        referenced_target = {e.supersedes_evaluation_id for e in target_old if e.supersedes_evaluation_id}
        unreferenced_heads = [e for e in target_old if e.evaluation_id not in referenced_target]
        if len(unreferenced_heads) != 1 or unreferenced_heads[0].evaluation_id != expected.evaluation_id:
            return "CONTROLLER_DECLARED_HEAD_MISMATCH"
    allids = tuple(ep)+tuple(arts)+tuple(refs)+tuple(obids)+tuple(suspids)+tuple(propids)+tuple(evaluationids)
    if len(set(allids)) != len(allids):
        return "CROSS_KIND_IDENTIFIER_COLLISION"
    if sum(len(x) for x in (case.epochs,case.artifacts,case.frozen_references,case.observations,case.suspensions,case.recovery_proposals,case.prior_evaluations)) > MAX_DEPENDENCIES + MAX_OBSERVATIONS + MAX_EVENTS:
        return "EXCEEDED_DEPENDENCIES"
    return None


def _affected(o: CompromiseObservation, epoch: WitnessEpoch, *, root: str | None = None) -> bool:
    if root is not None:
        return o.target_kind == "CONTROL_ROOT" and o.target_id == root
    return ((o.target_kind == "EPOCH" and o.target_id == epoch.epoch_id) or
            (o.target_kind == "WITNESS" and o.target_id == epoch.witness_id) or
            (o.target_kind == "CONTROL_ROOT" and o.target_id == epoch.control_root))


def _new_evaluation(case: RecoveryCase, art: HistoricalArtifact, usability: Finding,
                    old: tuple[PriorEvaluation, ...], reasons: tuple[str, ...]) -> RecoveryEvaluation:
    earlier = [e for e in old if e.artifact_id == art.artifact_id and e.sequence < case.evaluation_sequence]
    referenced = {e.supersedes_evaluation_id for e in earlier if e.supersedes_evaluation_id}
    heads = [e for e in earlier if e.evaluation_id not in referenced]
    # Nonempty prior history is validated and explicitly pinned by the
    # laboratory controller; never select the "best-looking" unpinned head.
    previous = heads[0].evaluation_id if len(heads) == 1 else None
    evidence_digest = _case_digest(case)
    ident = _evaluation_id(art.artifact_id, art.epoch_id, case.evaluation_sequence,
                           case.policy, usability.status, previous, reasons, evidence_digest)
    return RecoveryEvaluation(ident, art.artifact_id, art.epoch_id,
                              case.evaluation_sequence, case.policy,
                              usability.status, previous, reasons, evidence_digest)


def evaluate_recovery(case: RecoveryCase) -> RecoveryReport:
    """Return a deterministic NEW lab assessment, preserving all supplied records."""
    invalid = _validate(case)
    if invalid:
        return _invalid(invalid,case)
    epochmap = {x.epoch_id:x for x in case.epochs}
    artmap = {x.artifact_id:x for x in case.artifacts}
    art = artmap[case.target_artifact_id]
    epoch = epochmap[art.epoch_id]
    activeobs = tuple(sorted((o for o in case.observations if o.discovery_sequence <= case.evaluation_sequence),
                             key=lambda x:x.observation_id))
    supported = tuple(o for o in activeobs if o.origin == LAB)
    unsupported = tuple(sorted(o.observation_id for o in activeobs if o.origin != LAB))
    directly_relevant = tuple(o for o in supported if _affected(o,epoch))
    refutations = {o.refutes_observation_id for o in directly_relevant if o.kind == "REFUTATION"}
    # Refutations of suspected claims are scoped; no refutation of a CONFIRMED
    # event silently restores the prior epoch or erases the historical claim.
    pending = tuple(o for o in directly_relevant if o.kind == "SUSPECTED" and o.observation_id not in refutations)
    confirmed = tuple(o for o in directly_relevant if o.kind == "CONFIRMED_WINDOW")
    confirmed_refuted = any(o.observation_id in refutations for o in confirmed)
    conflicts: set[str] = set()
    windows = [(o.earliest_onset_sequence,o.confirmed_by_sequence) for o in confirmed]
    bounded = [(a,b) for a,b in windows if a is not None]
    if len(bounded) >= 2 and max(x[0] for x in bounded) > min(x[1] for x in bounded):
        conflicts.add("INCOMPATIBLE_CONFIRMED_ONSET_WINDOWS")
    if confirmed_refuted:
        conflicts.add("CONFIRMED_COMPROMISE_REFUTATION_CONFLICT")
    multiple_refutations = [o.refutes_observation_id for o in directly_relevant if o.kind == "REFUTATION"]
    if len(multiple_refutations)!=len(set(multiple_refutations)):
        conflicts.add("MULTIPLE_REFUTATIONS_OF_SAME_OBSERVATION")
    if case.controller_compromised:
        knowledge = _f("UNKNOWN","CONTROLLER_COMPROMISED")
    elif conflicts:
        knowledge = _f("CONTRADICTORY_EVIDENCE","CONFLICTING_LAB_COMPROMISE_OBSERVATIONS",*sorted(conflicts))
    elif confirmed:
        knowledge = _f("CONFIRMED_BY_LAB_CONTROL","LAB_COMPROMISE_OBSERVATION_ONLY",*(o.observation_id for o in confirmed))
    elif pending:
        knowledge = _f("SUSPECTED","UNRESOLVED_LAB_SUSPICION",*(o.observation_id for o in pending))
    elif not case.complete_compromise_inventory or case.completeness_origin != LAB:
        knowledge = _f("UNKNOWN","INCOMPLETE_COMPROMISE_INVENTORY")
    else:
        knowledge = _f("NOT_ESTABLISHED","NO_ACTIVE_LAB_COMPROMISE_OBSERVATION")

    # Onset T is in [max(earliest), min(confirmed_by)] under intersecting LAB
    # intervals. Capture and external retention must STRICTLY predate the lower
    # bound for pre-compromise reliance. No boundary if any lower bound missing.
    earliest = max((x.earliest_onset_sequence for x in confirmed if x.earliest_onset_sequence is not None),default=None)
    latest = min((x.confirmed_by_sequence for x in confirmed),default=None)
    if confirmed and any(o.earliest_onset_sequence is None for o in confirmed):
        earliest = None
    if conflicts:
        window = _f("UNKNOWN","CONFLICTING_COMPROMISE_WINDOWS")
    elif not confirmed:
        window = _f("UNKNOWN","NO_CONFIRMED_ONSET_WINDOW")
    elif latest is not None and art.capture_sequence >= latest:
        window = _f("AFTER_CONFIRMED_ONSET","CAPTURE_NOT_BEFORE_ANY_PLAUSIBLE_ONSET")
    elif earliest is not None and art.capture_sequence < earliest:
        window = _f("BEFORE_POSSIBLE_ONSET","LAB_CAPTURE_STRICTLY_PRECEDES_EARLIEST_ONSET")
    else:
        window = _f("WITHIN_OR_UNBOUNDED_WINDOW","CAPTURE_COMPROMISE_RELATION_UNRESOLVED")

    applicable = tuple(sorted((r for r in case.frozen_references if r.artifact_id == art.artifact_id),
                              key=lambda x:x.reference_id))
    preservation_flags: set[str] = set()
    valid_refs: list[FrozenReference] = []
    for r in applicable:
        if r.origin != LAB or r.checkpoint_sha256 != art.checkpoint_sha256:
            preservation_flags.add("UNTRUSTED_OR_DIFFERENT_REFERENCE")
            continue
        if r.retention_sequence < art.capture_sequence or r.retention_sequence > case.evaluation_sequence:
            preservation_flags.add("INVALID_OR_FUTURE_RETENTION_ORDER")
            continue
        if (r.custody_control_root == epoch.control_root or not r.control_surface_complete or
            r.control_relation != "LAB_CONDITIONALLY_SEPARATE"):
            preservation_flags.add("REFERENCE_INDEPENDENCE_NOT_ESTABLISHED")
            continue
        ref_compromised = any(_affected(o,epoch,root=r.custody_control_root) and o.kind in ("SUSPECTED","CONFIRMED_WINDOW")
                              for o in supported)
        if ref_compromised:
            preservation_flags.add("REFERENCE_CUSTODIAN_COMPROMISED")
            continue
        valid_refs.append(r)
    # A frozen, controller-origin *independently retained* contradicting digest
    # is an explicit comparison mismatch. Neither matching refs nor vote counts
    # may override this bounded contradictory observation.
    conflicting_pins = [r for r in applicable if r.origin == LAB and
        r.checkpoint_sha256 != art.checkpoint_sha256 and
        r.retention_sequence >= art.capture_sequence and
        r.retention_sequence <= case.evaluation_sequence and
        r.control_surface_complete and
        r.control_relation == "LAB_CONDITIONALLY_SEPARATE" and
        r.custody_control_root != epoch.control_root and
        not any(_affected(o,epoch,root=r.custody_control_root) and
                o.kind in ("SUSPECTED","CONFIRMED_WINDOW") for o in supported)]
    if conflicting_pins:
        conflicts.add("PRESERVED_CHECKPOINT_DIGEST_CONFLICT")
    if case.controller_compromised:
        preservation = _f("UNKNOWN","CONTROLLER_COMPROMISED")
    elif conflicting_pins:
        preservation = _f("MISMATCH","PRESERVED_REFERENCE_DIFFERS",*(r.reference_id for r in conflicting_pins))
    elif valid_refs:
        preservation = _f("LAB_CONDITIONAL_REFERENCE_PRESENT","CONTROLLER_DECLARED_EXTERNAL_REFERENCE",*(r.reference_id for r in valid_refs))
    else:
        preservation = _f("UNKNOWN","NO_SUPPORTED_INDEPENDENT_LAB_REFERENCE",*sorted(preservation_flags))

    suspensions = [s for s in case.suspensions if s.epoch_id==epoch.epoch_id and s.origin==LAB
                   and s.sequence <= case.evaluation_sequence]
    # Fresh succession is considered only for the successor epoch. The old
    # epoch is NEVER revived by a recovery proposal.
    relevant_proposals = tuple(sorted((p for p in case.recovery_proposals if
                                      p.successor_epoch_id==epoch.epoch_id and p.sequence <= case.evaluation_sequence),
                                     key=lambda x:x.proposal_id))
    def predecessor_frozen_by(sequence: int, previous: WitnessEpoch) -> bool:
        return (any(s.epoch_id == previous.epoch_id and s.origin == LAB and s.sequence <= sequence
                    for s in case.suspensions) or
                any(o.origin == LAB and o.kind in ("SUSPECTED", "CONFIRMED_WINDOW") and
                    o.discovery_sequence <= sequence and _affected(o,previous)
                    for o in case.observations))

    candidates = tuple(p for p in relevant_proposals if p.origin==LAB and p.enrollment_origin==LAB
                       and p.complete_control_surface and p.control_separation=="LAB_CONDITIONALLY_SEPARATE"
                       and epoch.control_root != epochmap[p.predecessor_epoch_id].control_root
                       and predecessor_frozen_by(p.sequence,epochmap[p.predecessor_epoch_id]))
    failed_recovery = bool(relevant_proposals) and not candidates
    compromised_successor = bool(pending or confirmed or suspensions)
    if epoch.predecessor_epoch_id is None:
        recovery = _f("NOT_APPLICABLE","BOOTSTRAP_EPOCH_NO_RECOVERY")
    elif len(relevant_proposals)>1:
        recovery = _f("UNKNOWN","CONFLICTING_RECOVERY_PROPOSALS",*(p.proposal_id for p in relevant_proposals))
        conflicts.add("CONFLICTING_RECOVERY_PROPOSALS")
    elif len(candidates)==1 and not case.controller_compromised and not compromised_successor:
        parent=epochmap[epoch.predecessor_epoch_id]
        # Recovery of an untainted predecessor is permitted as a lab scenario
        # but cannot be authenticated, nor be promoted to historical authority.
        recovery = _f("LAB_CONDITIONALLY_RECOVERED","SEPARATE_SUCCESSOR_LAB_EPOCH_ONLY",candidates[0].proposal_id,parent.epoch_id)
    elif failed_recovery:
        recovery = _f("UNKNOWN","RECOVERY_REQUIREMENTS_UNSATISFIED",*(p.proposal_id for p in relevant_proposals))
    else:
        recovery = _f("UNKNOWN","NO_SUPPORTED_RECOVERY_PROPOSAL")

    successors = [e for e in case.epochs if e.predecessor_epoch_id == epoch.epoch_id]
    has_successor = any(p.predecessor_epoch_id == epoch.epoch_id and p.successor_epoch_id == e.epoch_id and
                        p.sequence <= case.evaluation_sequence and p.origin == LAB and p.enrollment_origin == LAB and
                        p.complete_control_surface and p.control_separation == "LAB_CONDITIONALLY_SEPARATE" and
                        e.control_root != epoch.control_root and predecessor_frozen_by(p.sequence,epoch)
                        for e in successors for p in case.recovery_proposals)
    if case.controller_compromised:
        lifecycle = _f("UNKNOWN","CONTROLLER_COMPROMISED")
    elif has_successor:
        lifecycle = _f("EPOCH_SUPERSEDED_IN_LAB_MODEL","SUCCESSOR_LAB_EPOCH_RECORDED")
    elif confirmed or pending or suspensions:
        lifecycle = _f("EPOCH_FROZEN_IN_LAB_MODEL","RELEVANT_COMPROMISE_OR_SUSPENSION")
    elif epoch.predecessor_epoch_id is not None and recovery.status != "LAB_CONDITIONALLY_RECOVERED":
        lifecycle = _f("EPOCH_PROPOSED","RECOVERY_NOT_CONDITIONALLY_ESTABLISHED")
    else:
        lifecycle = _f("EPOCH_ACTIVE_IN_LAB_MODEL","NO_RELEVANT_LAB_FREEZE")

    can_use = preservation.status == "LAB_CONDITIONAL_REFERENCE_PRESENT"
    inventory = case.complete_compromise_inventory and case.completeness_origin == LAB
    retention_pre_onset = any(r.retention_sequence < earliest for r in valid_refs) if earliest is not None else False
    if case.controller_compromised:
        use = _f("INSUFFICIENT_SUPPORT","CONTROLLER_COMPROMISED")
    elif "PRESERVED_CHECKPOINT_DIGEST_CONFLICT" in conflicts:
        use = _f("REJECTED_FOR_NAMED_USE","FROZEN_REFERENCE_DIGEST_DISCREPANCY")
    elif conflicts:
        use = _f("SUSPENDED","CONTRADICTORY_TRUST_EVIDENCE")
    elif confirmed:
        if window.status == "BEFORE_POSSIBLE_ONSET" and retention_pre_onset and can_use and inventory and not pending:
            use = _f("CONDITIONALLY_USABLE_FOR_NAMED_COMPARISON","PINNED_PRE_COMPROMISE_LAB_REFERENCE_ONLY")
        else:
            use = _f("SUSPENDED","CONFIRMED_COMPROMISE_AFFECTS_USE")
    elif pending or suspensions:
        use = _f("SUSPENDED","UNRESOLVED_SUSPICION_OR_SUSPENSION")
    elif epoch.predecessor_epoch_id is not None and recovery.status != "LAB_CONDITIONALLY_RECOVERED":
        use = _f("INSUFFICIENT_SUPPORT","RECOVERY_NOT_ESTABLISHED")
    elif can_use and inventory and lifecycle.status == "EPOCH_ACTIVE_IN_LAB_MODEL":
        use = _f("CONDITIONALLY_USABLE_FOR_NAMED_COMPARISON","PINNED_LAB_COMPARISON_ONLY")
    else:
        use = _f("INSUFFICIENT_SUPPORT","NO_COMPLETE_LAB_SUPPORT_FOR_AFFIRMATIVE_USE")
    if use.status == "CONDITIONALLY_USABLE_FOR_NAMED_COMPARISON" and case.controller_compromised:
        raise AssertionError("unreachable unsafe promotion")

    previous = [e for e in case.prior_evaluations if e.artifact_id == art.artifact_id and
                e.sequence < case.evaluation_sequence]
    if any(e.sequence == case.evaluation_sequence for e in case.prior_evaluations if e.artifact_id == art.artifact_id):
        return _invalid("EVALUATION_SEQUENCE_COLLISION",case)
    if len(previous)>1:
        refs={e.supersedes_evaluation_id for e in previous if e.supersedes_evaluation_id}
        tips=[e for e in previous if e.evaluation_id not in refs]
        if len(tips)!=1:
            return _invalid("AMBIGUOUS_EVALUATION_BRANCHES",case)
    reasons=tuple(sorted(set(x.reason for x in (knowledge,window,preservation,use,lifecycle,recovery)) |
                             set(conflicts) | set(preservation_flags) | {"UNSUPPORTED_OBSERVATION:"+o for o in unsupported}))
    try:
        generated=_new_evaluation(case,art,use,case.prior_evaluations,reasons)
    except (ValueError, TypeError, RecursionError, OverflowError):
        return _invalid("UNSERIALIZABLE_EVIDENCE_BASIS",case)
    return RecoveryReport(knowledge,window,preservation,use,lifecycle,recovery,
                          tuple(sorted(conflicts)),unsupported,case.artifacts,case.prior_evaluations,
                          generated,reasons)
