"""RERE-01 v0.2: bounded read-only comparator for typed M0 Assessment records.

A RESEARCH HARNESS, NOT a new Ario memory engine or evidence-admission API.
The synthetic controller policy is an explicit fixture assumption. Caller-held
ids, hashes, successful assertions or multiple aliases DO NOT verify custody.
Never import this into production, signer, source guard or live memory.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from core.schema import Assessment, Reference, SupportTarget

PROFILE = "RERE-LAB-CONTROLLER-v0.2"
EVENT_ID = "LAB-E101"
MAX_RECORDS = 64


class LabContractError(ValueError):
    """A supplied history is incomplete, ambiguous or out of the lab contract."""


@dataclass(frozen=True)
class LabObservation:
    seq: int
    record_id: str
    source_id: str
    origin_root: str
    reported_value: str
    observed_at: str
    event_id: str
    target_record_id: str = ""
    declared_receipt: str = ""  # NEVER authenticates provenance


@dataclass(frozen=True)
class LabAssessment:
    seq: int
    assessment: Assessment
    reason_code: str

    @property
    def record_id(self) -> str:
        return self.assessment.assessment_id


@dataclass(frozen=True)
class SyntheticPolicy:
    """Externally defined toy controller assumptions, NOT a credential."""
    profile: str
    event_id: str
    event_time: str
    pinned_roots: tuple[tuple[str, str], ...]
    calibration_pairs: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Projection:
    event_outcome: str
    assessment_reliability: tuple[tuple[str, str], ...]
    historical_record_ids: tuple[str, ...]
    active_reasons: tuple[str, ...]
    evidence_authorized_for_real_memory: bool = False


Record = Union[LabObservation, LabAssessment]


def _validated(observation: LabObservation, roots: dict[str, str]) -> bool:
    """Declared ID/root equality under a synthetic fixture; NOT real verification."""
    return roots.get(observation.source_id) == observation.origin_root and bool(
        observation.origin_root
    )


def _single_lab_evidence(assessment: Assessment) -> str | None:
    refs = assessment.admissible_evidence_refs
    if len(refs) != 1:
        return None
    ref = refs[0]
    if not isinstance(ref, Reference) or ref.reference_type != "LAB_OBSERVATION":
        return None
    return ref.reference_id


def _check_policy(policy: SyntheticPolicy) -> dict[str, str]:
    if not isinstance(policy, SyntheticPolicy) or policy.profile != PROFILE:
        raise LabContractError("unsupported or missing synthetic policy")
    if policy.event_id != EVENT_ID or not policy.event_time:
        raise LabContractError("wrong event scope")
    roots: dict[str, str] = {}
    for source_id, root in policy.pinned_roots:
        if not isinstance(source_id, str) or not source_id or not isinstance(root, str) or not root:
            raise LabContractError("invalid synthetic root pin")
        if source_id in roots:
            raise LabContractError("ambiguous synthetic root pin")
        roots[source_id] = root
    return roots


def _deduplicate(records: tuple[Record, ...]) -> tuple[Record, ...]:
    if len(records) > MAX_RECORDS:
        raise LabContractError("bounded record count exceeded")
    seen: dict[str, Record] = {}
    for rec in records:
        if type(rec) not in (LabObservation, LabAssessment):
            raise LabContractError("unknown record type")
        if type(rec.seq) is not int or not 1 <= rec.seq <= MAX_RECORDS:
            raise LabContractError("non-canonical sequence number")
        if not isinstance(rec.record_id, str) or not rec.record_id or len(rec.record_id) > 128:
            raise LabContractError("invalid record id")
        if isinstance(rec, LabAssessment):
            if not isinstance(rec.assessment, Assessment):
                raise LabContractError("untyped assessment")
            if not isinstance(rec.assessment.target, SupportTarget):
                raise LabContractError("untyped assessment target")
            if rec.assessment.scope != EVENT_ID or rec.assessment.rule_version != PROFILE:
                raise LabContractError("assessment scope or rule mismatch")
        previous = seen.get(rec.record_id)
        if previous is not None:
            if previous != rec:
                raise LabContractError("record ID reused with altered content")
            continue  # idempotent projection, NOT a durable writer guarantee
        seen[rec.record_id] = rec
    ordered = tuple(sorted(seen.values(), key=lambda item: item.seq))
    if [r.seq for r in ordered] != list(range(1, len(ordered) + 1)):
        raise LabContractError("sequence missing, duplicated or reordered by ID")
    return ordered


def project(records: tuple[Record, ...], policy: SyntheticPolicy) -> Projection:
    """Evaluate only the synthetic lab's narrow T1→T4 contract, no I/O/writes.

    Historical Assessment objects remain intact. Current reliability is a
    *derived* view; historic as-of views can be recomputed from prefixes.
    """
    roots = _check_policy(policy)
    ordered = _deduplicate(records)
    observed: dict[str, LabObservation] = {}
    reviewed: dict[str, LabAssessment] = {}
    reliability: dict[str, str] = {}
    outcome = "UNKNOWN"
    reasons: tuple[str, ...] = ("NO_AUTHENTICATED_OBJECT_LEVEL_JUDGMENT",)

    for rec in ordered:
        if isinstance(rec, LabObservation):
            if rec.event_id != policy.event_id:
                raise LabContractError("witness event scope mismatch")
            observed[rec.record_id] = rec
            continue

        a = rec.assessment
        target = a.target.subject_reference
        if target.reference_id == rec.record_id:
            raise LabContractError("self-directed assessment cycle")
        if target.reference_type not in ("CLAIM", "ASSESSMENT"):
            raise LabContractError("invalid typed review target")

        evidence_id = _single_lab_evidence(a)
        source = observed.get(evidence_id) if evidence_id is not None else None
        if target.reference_type == "CLAIM":
            if target.reference_id != policy.event_id or a.target.property_id != "DOOR_OPEN":
                raise LabContractError("object claim target mismatch")
            # This is NOT generalized belief revision or source authentication.
            is_warranted = (
                rec.reason_code == "C_CONTRADICTS_OPEN"
                and a.condition_evaluation == "OPEN_REFUTED"
                and source is not None
                and source.source_id == "C"
                and source.reported_value == "CLOSED"
                and source.observed_at == policy.event_time
                and _validated(source, roots)
            )
            reliability[rec.record_id] = (
                "CONDITIONALLY_WARRANTED_IN_LAB" if is_warranted else "NOT_WARRANTED"
            )
            if is_warranted:
                outcome = "CONDITIONALLY_REFUTED_IN_LAB"
                reasons = ("C_MATCHED_FROZEN_SYNTHETIC_CONTROLLER",)
            else:
                reasons = ("OBJECT_REVIEW_NOT_WARRANTED",)
            reviewed[rec.record_id] = rec
            continue

        previous = reviewed.get(target.reference_id)
        if previous is None:
            raise LabContractError("prior assessment absent or forward reference")
        if a.target.property_id != "PRIOR_JUSTIFICATION_RELIABILITY":
            raise LabContractError("wrong assessment property")
        if previous.assessment.target.subject_reference.reference_type != "CLAIM":
            raise LabContractError("review-of-review recursion beyond v0.2 bounds")

        c_id = _single_lab_evidence(previous.assessment)
        old_source = observed.get(c_id) if c_id else None
        is_valid_calibration = (
            rec.reason_code == "CALIBRATION_REVOKES_C"
            and a.condition_evaluation == "T3_BASIS_UNRELIABLE"
            and source is not None
            and old_source is not None
            and source.source_id == "CAL"
            and old_source.source_id == "C"
            and source.reported_value == "CLOCK_MISMATCH"
            and source.target_record_id == old_source.record_id
            and (source.source_id, old_source.source_id) in policy.calibration_pairs
            and _validated(source, roots)
            and _validated(old_source, roots)
            and source.origin_root != old_source.origin_root
        )
        reliability[rec.record_id] = (
            "CONDITIONALLY_WARRANTED_IN_LAB" if is_valid_calibration else "NOT_WARRANTED"
        )
        if is_valid_calibration:
            reliability[previous.record_id] = "CHALLENGED_BY_LATER_CALIBRATION"
            outcome = "UNKNOWN"
            reasons = ("C_TIME_BINDING_CHALLENGED", "T3_JUSTIFICATION_NO_LONGER_RELIABLE")
        reviewed[rec.record_id] = rec

    return Projection(
        event_outcome=outcome,
        assessment_reliability=tuple(sorted(reliability.items())),
        historical_record_ids=tuple(rec.record_id for rec in ordered),
        active_reasons=reasons,
        evidence_authorized_for_real_memory=False,
    )
