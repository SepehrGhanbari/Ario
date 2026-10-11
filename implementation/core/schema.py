"""Ario M0 canonical schema primitives and structural objects.

M0-01:
- SchemaVersion
- Reference
- Timestamp
- TemporalContext
- Provenance
- EpistemicStatus
- IndependenceStatus

M0-02:
- Claim
- HistoricalState

These objects represent auditable structure.
They do not establish truth, entity continuity, causality, or ontology.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass(frozen=True)
class SchemaVersion:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("schema version must be non-empty")


@dataclass(frozen=True)
class Reference:
    reference_id: str
    reference_type: str

    def __post_init__(self) -> None:
        if not self.reference_id or not self.reference_id.strip():
            raise ValueError("reference_id must be non-empty")
        if not self.reference_type or not self.reference_type.strip():
            raise ValueError("reference_type must be non-empty")


@dataclass(frozen=True)
class IntegrityRepresentation:
    method: str
    value: str

    def __post_init__(self) -> None:
        if not self.method or not self.method.strip():
            raise ValueError("integrity method must be non-empty")
        if not self.value or not self.value.strip():
            raise ValueError("integrity value must be non-empty")


@dataclass(frozen=True)
class Timestamp:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("timestamp value must be non-empty")


class TemporalRelation(str, Enum):
    ALIGNED = "TEMPORALLY_ALIGNED"
    DISTINCT = "TEMPORALLY_DISTINCT"
    UNRESOLVED = "TEMPORALLY_UNRESOLVED"


@dataclass(frozen=True)
class TemporalContext:
    observed_at: Optional[Timestamp] = None
    epoch: Optional[str] = None
    snapshot_id: Optional[str] = None
    relation: TemporalRelation = TemporalRelation.UNRESOLVED

    def __post_init__(self) -> None:
        if self.epoch is not None and not self.epoch.strip():
            raise ValueError("epoch must be non-empty when provided")
        if self.snapshot_id is not None and not self.snapshot_id.strip():
            raise ValueError("snapshot_id must be non-empty when provided")


@dataclass(frozen=True)
class Provenance:
    source_reference: Reference
    relation: str
    source_version: Optional[str] = None
    execution_context: Optional[str] = None
    timestamp: Optional[Timestamp] = None

    def __post_init__(self) -> None:
        if not self.relation or not self.relation.strip():
            raise ValueError("provenance relation must be non-empty")
        if self.source_version is not None and not self.source_version.strip():
            raise ValueError(
                "source_version must be non-empty when provided"
            )
        if self.execution_context is not None and not self.execution_context.strip():
            raise ValueError(
                "execution_context must be non-empty when provided"
            )


class EpistemicStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    CONTESTED = "CONTESTED"
    REVISED = "REVISED"


class IndependenceStatus(str, Enum):
    INDEPENDENT = "INDEPENDENT"
    DEPENDENT = "DEPENDENT"
    UNKNOWN = "UNKNOWN"


class CompositionConclusion(str, Enum):
    # BOUNDED_SUMMARY is retained as a legacy input label but is not accepted
    # by the current F15 contract. Use LOCAL_RESULT_SUMMARY instead.
    BOUNDED_SUMMARY = "BOUNDED_SUMMARY"
    LOCAL_RESULT_SUMMARY = "LOCAL_RESULT_SUMMARY"
    GLOBAL_TRUTH = "GLOBAL_TRUTH"
    CLAIM_TRUTH = "CLAIM_TRUTH"
    SAME_ENTITY = "SAME_ENTITY"
    ONTOLOGICAL_IDENTITY = "ONTOLOGICAL_IDENTITY"
    CONSCIOUSNESS = "CONSCIOUSNESS"


class CompositionInputScope(str, Enum):
    SUPPLIED_RESULTS_ONLY = "SUPPLIED_RESULTS_ONLY"
    ALL_FIVE_IRGS = "ALL_FIVE_IRGS"


@dataclass(frozen=True)
class CompositionParticipantResult:
    irg_id: str
    audit_id: str
    declared_scope: str = "UNSPECIFIED"

    def __post_init__(self) -> None:
        if not self.irg_id or not self.irg_id.strip():
            raise ValueError("irg_id must be non-empty")
        if not self.audit_id or not self.audit_id.strip():
            raise ValueError("audit_id must be non-empty")
        if not self.declared_scope or not self.declared_scope.strip():
            raise ValueError("declared_scope must be non-empty")


@dataclass(frozen=True)
class CompositionRequest:
    composition_id: str
    participant_results: tuple[CompositionParticipantResult, ...]
    composition_rule_id: str
    composition_rule_version: str
    temporal_context: str
    requested_conclusion: CompositionConclusion
    limitations: str
    scope: str
    requested_input_scope: CompositionInputScope = CompositionInputScope.ALL_FIVE_IRGS

    def __post_init__(self) -> None:
        for name in (
            "composition_id", "composition_rule_id",
            "composition_rule_version", "temporal_context",
            "limitations", "scope",
        ):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if not self.participant_results:
            raise ValueError("participant_results must be non-empty")
        if not isinstance(self.requested_conclusion, CompositionConclusion):
            raise ValueError("requested_conclusion must be typed")
        if not isinstance(self.requested_input_scope, CompositionInputScope):
            raise ValueError("requested_input_scope must be typed")


@dataclass(frozen=True)
class CompositionSummaryRecord:
    audit_id: str
    declared_irg_id: str
    declared_scope: str
    verdict: str
    rule_versions: tuple[str, ...]
    configuration_id: str


@dataclass(frozen=True)
class CompositionSummary:
    composition_id: str
    summary_rule_id: str
    summary_rule_version: str
    requested_input_scope: CompositionInputScope
    records: tuple[CompositionSummaryRecord, ...]
    verdict_counts: tuple[tuple[str, int], ...]
    scope: str
    limitations: str

    def __post_init__(self) -> None:
        for name in ("composition_id", "summary_rule_id", "summary_rule_version", "scope", "limitations"):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if not self.records:
            raise ValueError("records must be non-empty")


@dataclass(frozen=True)
class Claim:
    claim_id: str
    schema_version: SchemaVersion
    created_at: Timestamp
    origin_reference: Reference
    status: EpistemicStatus

    def __post_init__(self) -> None:
        if not self.claim_id or not self.claim_id.strip():
            raise ValueError("claim_id must be non-empty")


@dataclass(frozen=True)
class LineageEdge:
    lineage_id: str
    from_reference: Reference
    to_reference: Reference
    relation_type: str
    derivation_reference: Reference
    admissibility_status: str
    provenance: Provenance
    compatibility_authorizations: tuple["LineageCompatibilityAuthorization", ...] = ()

    def __post_init__(self) -> None:
        if not self.lineage_id or not self.lineage_id.strip():
            raise ValueError("lineage_id must be non-empty")
        if not self.relation_type or not self.relation_type.strip():
            raise ValueError("relation_type must be non-empty")
        if (
            not self.admissibility_status
            or not self.admissibility_status.strip()
        ):
            raise ValueError("admissibility_status must be non-empty")


class LineageAuthorizationDecision(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    DENIED = "DENIED"


@dataclass(frozen=True)
class LineageCompatibilityAuthorization:
    authorization_id: str
    rule_id: str
    rule_version: str
    source_reference_type: str
    target_reference_type: str
    relation_type: str
    decision: LineageAuthorizationDecision
    provenance: Provenance

    def __post_init__(self) -> None:
        for name in (
            "authorization_id",
            "rule_id",
            "rule_version",
            "source_reference_type",
            "target_reference_type",
            "relation_type",
        ):
            value = getattr(self, name)
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if not isinstance(self.decision, LineageAuthorizationDecision):
            raise ValueError("decision must be a LineageAuthorizationDecision")


@dataclass(frozen=True)
class RetrievalEvent:
    retrieval_id: str
    source_reference: Reference
    retrieved_reference: Reference
    retrieval_timestamp: Timestamp
    transformation_reference: Reference
    fidelity_status: str
    provenance: Provenance
    observed_transformation_reference: Reference | None = None

    def __post_init__(self) -> None:
        if not self.retrieval_id or not self.retrieval_id.strip():
            raise ValueError("retrieval_id must be non-empty")
        if not self.fidelity_status or not self.fidelity_status.strip():
            raise ValueError("fidelity_status must be non-empty")


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    observation_refs: tuple[Reference, ...]
    evidence_level: str
    independence_status: IndependenceStatus
    derivation_reference: Reference
    scope: str

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.evidence_id.strip():
            raise ValueError("evidence_id must be non-empty")
        if not self.observation_refs:
            raise ValueError("observation_refs must be non-empty")
        if not self.evidence_level or not self.evidence_level.strip():
            raise ValueError("evidence_level must be non-empty")
        if not self.scope or not self.scope.strip():
            raise ValueError("scope must be non-empty")


@dataclass(frozen=True)
class Assessment:
    assessment_id: str
    assessment_version: str
    rule_version: str
    admissible_evidence_refs: tuple[Reference, ...]
    condition_evaluation: str
    assessment_basis: str
    scope: str

    def __post_init__(self) -> None:
        if not self.assessment_id or not self.assessment_id.strip():
            raise ValueError("assessment_id must be non-empty")
        if (
            not self.assessment_version
            or not self.assessment_version.strip()
        ):
            raise ValueError("assessment_version must be non-empty")
        if not self.rule_version or not self.rule_version.strip():
            raise ValueError("rule_version must be non-empty")
        if not self.admissible_evidence_refs:
            raise ValueError(
                "admissible_evidence_refs must be non-empty"
            )
        if (
            not self.condition_evaluation
            or not self.condition_evaluation.strip()
        ):
            raise ValueError(
                "condition_evaluation must be non-empty"
            )
        if not self.assessment_basis or not self.assessment_basis.strip():
            raise ValueError("assessment_basis must be non-empty")
        if not self.scope or not self.scope.strip():
            raise ValueError("scope must be non-empty")

@dataclass(frozen=True)
class AuditResult:
    audit_id: str
    inspector_id: str
    inspector_version: str
    execution_timestamp: Timestamp
    configuration_id: str
    rule_versions: tuple[str, ...]
    artifacts_examined: tuple[Reference, ...]
    violations: tuple[str, ...]
    verdict: str
    verdict_basis: str
    composition_summaries: tuple[CompositionSummary, ...] = ()

    def __post_init__(self) -> None:
        if not self.audit_id or not self.audit_id.strip():
            raise ValueError("audit_id must be non-empty")
        if not self.inspector_id or not self.inspector_id.strip():
            raise ValueError("inspector_id must be non-empty")
        if (
            not self.inspector_version
            or not self.inspector_version.strip()
        ):
            raise ValueError("inspector_version must be non-empty")
        if (
            not self.configuration_id
            or not self.configuration_id.strip()
        ):
            raise ValueError("configuration_id must be non-empty")
        if not self.rule_versions:
            raise ValueError("rule_versions must be non-empty")
        if not self.verdict or not self.verdict.strip():
            raise ValueError("verdict must be non-empty")
        if not self.verdict_basis or not self.verdict_basis.strip():
            raise ValueError("verdict_basis must be non-empty")

@dataclass(frozen=True)
class HistoricalMutationCandidate:
    canonical_artifact: Reference
    canonical_integrity: IntegrityRepresentation
    attempted_replacement: Reference
    attempted_replacement_integrity: IntegrityRepresentation
    historical_scope: Reference
    mutation_rule_version: str

    def __post_init__(self) -> None:
        if not self.mutation_rule_version or not self.mutation_rule_version.strip():
            raise ValueError(
                "mutation_rule_version must be non-empty"
            )


@dataclass(frozen=True)
class LineageCandidate:
    candidate_id: str
    from_reference: Reference
    to_reference: Reference
    proposed_relation_type: str
    inference_basis: str
    derivation_reference: Reference
    provenance: Provenance
    lineage_rule_version: str

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.candidate_id.strip():
            raise ValueError("candidate_id must be non-empty")
        if not self.proposed_relation_type or not self.proposed_relation_type.strip():
            raise ValueError("proposed_relation_type must be non-empty")
        if not self.inference_basis or not self.inference_basis.strip():
            raise ValueError("inference_basis must be non-empty")
        if not self.lineage_rule_version or not self.lineage_rule_version.strip():
            raise ValueError("lineage_rule_version must be non-empty")


@dataclass(frozen=True)
class HistoricalState:
    state_id: str
    claim_id: str
    state_version: str
    observed_at: Timestamp
    state_context: TemporalContext
    content_reference: Reference
    provenance: Provenance

    def __post_init__(self) -> None:
        if not self.state_id or not self.state_id.strip():
            raise ValueError("state_id must be non-empty")
        if not self.claim_id or not self.claim_id.strip():
            raise ValueError("claim_id must be non-empty")
        if not self.state_version or not self.state_version.strip():
            raise ValueError("state_version must be non-empty")
