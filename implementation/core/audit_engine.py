from __future__ import annotations

import json

from dataclasses import dataclass
from typing import Iterable

from .schema import (
    Assessment,
    AuditResult,
    Claim,
    CompositionConclusion,
    CompositionInputScope,
    CompositionRequest,
    CompositionSummary,
    CompositionSummaryRecord,
    Evidence,
    EvidenceUse,
    ObservationRecord,
    HistoricalState,
    HistoricalMutationCandidate,
    IndependenceStatus,
    LineageCandidate,
    LineageAuthorizationDecision,
    LineageCompatibilityAuthorization,
    LineageEdge,
    RetrievalEvent,
    Reference,
    TemporalRelation,
    Timestamp,
)



EAG_FINDINGS_BEGIN = "\nEvidence ancestry findings: "
EAG_FINDINGS_END = "\nM0-EAG-0.1-FINDINGS-END"


def parse_evidence_ancestry_findings(basis: str) -> dict:
    """Parse the engine-owned, canonical findings tail; this is no credential."""
    if not isinstance(basis, str) or basis.count(EAG_FINDINGS_BEGIN) != 1:
        raise ValueError("M0 ancestry findings framing missing or ambiguous")
    _, encoded = basis.split(EAG_FINDINGS_BEGIN, 1)
    if not encoded.endswith(EAG_FINDINGS_END):
        raise ValueError("M0 ancestry findings end marker missing")
    encoded = encoded[:-len(EAG_FINDINGS_END)]
    if len((EAG_FINDINGS_BEGIN + encoded + EAG_FINDINGS_END).encode("utf-8")) > 65536:
        raise ValueError("M0 ancestry findings exceed report limit")
    try:
        data = json.loads(encoded)
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=True, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise ValueError("M0 ancestry findings invalid JSON") from exc
    if encoded != canonical or not isinstance(data, dict):
        raise ValueError("M0 ancestry findings not canonical")
    if (data.get("profile") != "M0-EAG-0.1"
            or data.get("mandatory_guards") != ["M0-REF-GUARD-1.0", "M0-EAG-0.1"]
            or data.get("independent_admission_authority") != "NONE"
            or data.get("candidate_use") != "NOT_EVALUATED"
            or data.get("claim_truth") != "UNKNOWN"
            or data.get("entity_continuity") != "UNKNOWN"
            or not isinstance(data.get("assessments"), list)
            or type(data.get("report_complete")) is not bool):
        raise ValueError("M0 ancestry findings profile invalid")
    ancestry_states = {"UNKNOWN", "TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT"}
    candidate_ancestry = data.get("candidate_ancestry")
    if (not isinstance(candidate_ancestry, str)
            or candidate_ancestry not in ancestry_states | {"NOT_EVALUATED"}):
        raise ValueError("M0 ancestry candidate state invalid")
    expected_row_keys = {
        "assessment_id", "target", "property_id", "requested_use", "ancestry",
        "record_presence", "use_disposition", "source_authentication", "reasons",
    }
    def valid_identifier(value):
        return value is None or _EvidenceAncestryGuard.report_id(value) is not None
    for row in data["assessments"]:
        if not isinstance(row, dict) or set(row) != expected_row_keys:
            raise ValueError("M0 ancestry assessment fields invalid")
        if (not valid_identifier(row["assessment_id"])
                or not valid_identifier(row["property_id"])
                or row["requested_use"] not in (None, "RECORD_DESCRIPTION", "INDEPENDENT_TARGET_SUPPORT")
                or row["ancestry"] not in ("UNKNOWN", "TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT")
                or row["record_presence"] not in ("MATCH", "NOT_EVALUATED", "UNKNOWN")
                or row["use_disposition"] not in ("NOT_EVALUATED", "RECORD_DESCRIPTION_ONLY", "KNOWN_INADMISSIBLE", "UNKNOWN")
                or row["source_authentication"] != "UNKNOWN"
                or not isinstance(row["reasons"], list)
                or not all(isinstance(reason, str) for reason in row["reasons"])):
            raise ValueError("M0 ancestry assessment state invalid")
        target = row["target"]
        if target is not None and (
                not isinstance(target, dict)
                or set(target) != {"reference_id", "reference_type"}
                or target["reference_id"] is None or target["reference_type"] is None
                or not valid_identifier(target["reference_id"])
                or not valid_identifier(target["reference_type"])):
            raise ValueError("M0 ancestry target invalid")
        if row["record_presence"] == "MATCH" or row["use_disposition"] == "RECORD_DESCRIPTION_ONLY":
            if (row["requested_use"] != "RECORD_DESCRIPTION"
                    or row["property_id"] != "SUPPLIED_RECORD_PRESENT"
                    or target is None or target["reference_type"] not in ("CLAIM", "OBSERVATION")):
                raise ValueError("M0 ancestry presence binding invalid")
    if "use_disposition" in data and data["use_disposition"] != "UNKNOWN":
        raise ValueError("M0 ancestry fallback state invalid")
    return data


# Engine-owned allowlist: request declarations and edge authorizations are claims,
# and cannot add rules or type/relation bindings to this policy.
TRUSTED_LINEAGE_COMPATIBILITY_POLICIES = frozenset(
    {
        (
            "M0-LRT01-XTYPE",
            "1.0",
            "STATE_CONTENT",
            "EVENT_RECORD",
            "EXPLICIT_RELATION",
        ),
    }
)
SUPPORTED_LINEAGE_AUTHORIZATION_RULES = frozenset(
    (rule_id, rule_version)
    for rule_id, rule_version, _, _, _
    in TRUSTED_LINEAGE_COMPATIBILITY_POLICIES
)


@dataclass(frozen=True)
class AuditInput:
    claims: tuple[Claim, ...] = ()
    historical_states: tuple[HistoricalState, ...] = ()
    lineage_edges: tuple[LineageEdge, ...] = ()
    retrieval_events: tuple[RetrievalEvent, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    assessments: tuple[Assessment, ...] = ()
    prior_audit_results: tuple[AuditResult, ...] = ()
    historical_mutation_candidates: tuple[
        HistoricalMutationCandidate, ...
    ] = ()
    lineage_candidates: tuple[LineageCandidate, ...] = ()
    composition_requests: tuple[CompositionRequest, ...] = ()
    observations: tuple[ObservationRecord, ...] = ()

    @property
    def artifacts_examined(self) -> tuple:
        references = []

        for claim in self.claims:
            references.append(claim.origin_reference)

        for state in self.historical_states:
            references.append(state.content_reference)

        for edge in self.lineage_edges:
            references.extend(
                (
                    edge.from_reference,
                    edge.to_reference,
                    edge.derivation_reference,
                )
            )
            references.extend(
                authorization.provenance.source_reference
                for authorization in edge.compatibility_authorizations
                if (
                    authorization.provenance is not None
                    and authorization.provenance.source_reference is not None
                )
            )

        for event in self.retrieval_events:
            references.extend(
                (
                    event.source_reference,
                    event.retrieved_reference,
                    event.transformation_reference,
                    *((
                        event.observed_transformation_reference,
                    ) if event.observed_transformation_reference is not None else ()),
                )
            )

        for evidence_item in self.evidence:
            references.extend(
                (
                    evidence_item.derivation_reference,
                    *evidence_item.observation_refs,
                )
            )

        for assessment in self.assessments:
            references.extend(assessment.admissible_evidence_refs)

        # Prior audit results remain a distinct artifact kind. Recording one
        # does not make its verdict admissible evidence for an assessment.
        for result in self.prior_audit_results:
            references.append(Reference(result.audit_id, "AUDIT_RESULT"))

        for request in self.composition_requests:
            references.append(
                Reference(request.composition_id, "COMPOSITION_REQUEST")
            )
            for participant in request.participant_results:
                references.append(
                    Reference(participant.audit_id, "AUDIT_RESULT")
                )

        for candidate in self.historical_mutation_candidates:
            references.extend(
                (
                    candidate.canonical_artifact,
                    candidate.attempted_replacement,
                    candidate.historical_scope,
                )
            )

        for candidate in self.lineage_candidates:
            references.extend(
                (
                    candidate.from_reference,
                    candidate.to_reference,
                    candidate.derivation_reference,
                )
            )


        # Canonical guard identities and endpoints supplement the legacy trace.
        for claim in self.claims:
            references.append(Reference(claim.claim_id, "CLAIM"))
        for item in self.evidence:
            references.append(Reference(item.evidence_id, "EVIDENCE"))
        for assessment in self.assessments:
            references.append(Reference(assessment.assessment_id, "ASSESSMENT"))
            if assessment.target is not None:
                references.append(assessment.target.subject_reference)
        for observation in self.observations:
            references.append(Reference(observation.observation_id, "OBSERVATION"))
            references.extend(observation.provenance_refs)
            if observation.target is not None:
                references.append(observation.target.subject_reference)

        return tuple(references)


class AuditEngine:
    INSPECTOR_ID = "ARIO_M0_DETERMINISTIC_AUDIT"
    INSPECTOR_VERSION = "M0-1.2"
    ALWAYS_ON_FIREWALL_VERSION = "M0-REF-GUARD-1.0"
    ALWAYS_ON_ANCESTRY_VERSION = "M0-EAG-0.1"
    MAX_ANCESTRY_OBJECTS = 4096
    MAX_ANCESTRY_EDGES = 16384
    MAX_ANCESTRY_DEPTH = 64
    MAX_ANCESTRY_REPORT_BYTES = 65536

    def audit(
        self,
        artifacts: AuditInput,
        *,
        rule_versions: tuple[str, ...],
        configuration_id: str,
        execution_timestamp: Timestamp,
        audit_id: str,
    ) -> AuditResult:
        if not rule_versions:
            raise ValueError("rule_versions must be non-empty")

        violations: list[str] = []

        has_primary_artifacts = any(
            (
                artifacts.claims,
                artifacts.historical_states,
                artifacts.lineage_edges,
                artifacts.retrieval_events,
                artifacts.evidence,
                artifacts.assessments,
                artifacts.observations,
                artifacts.historical_mutation_candidates,
                artifacts.lineage_candidates,
                artifacts.composition_requests,
            )
        )
        if not has_primary_artifacts:
            verdict = "UNKNOWN"
            verdict_basis = (
                "No primary artifacts for a new audit were supplied; "
                "prior audit results alone do not support a new verdict."
            )
        else:
            violations.extend(
                self._check_claim_identity(artifacts.claims)
            )
            violations.extend(
                self._check_lineage_candidates(
                    artifacts.lineage_candidates,
                    rule_versions,
                )
            )
            violations.extend(
                self._check_provenance(
                    artifacts.historical_states,
                    artifacts.lineage_edges,
                    artifacts.retrieval_events,
                )
            )
            violations.extend(
                self._check_lineage(artifacts.lineage_edges)
            )
            violations.extend(
                self._check_retrieval(artifacts.retrieval_events)
            )
            violations.extend(
                self._check_evidence(
                    artifacts.evidence,
                    prior_audit_results=artifacts.prior_audit_results,
                    composition_requests=artifacts.composition_requests,
                    rule_versions=rule_versions,
                )
            )
            violations.extend(
                self._check_temporal_relations(
                    artifacts.historical_states,
                    artifacts.lineage_edges,
                    rule_versions,
                )
            )
            violations.extend(
                self._check_assessments(
                    artifacts.assessments,
                    artifacts.evidence,
                    artifacts.prior_audit_results,
                    rule_versions,
                    composition_requests=artifacts.composition_requests,
                )
            )
            composition_violations, composition_summaries = (
                self._evaluate_composition_requests(
                    artifacts.composition_requests,
                    artifacts.prior_audit_results,
                    rule_versions,
                )
            )
            violations.extend(composition_violations)
            violations.extend(
                self._check_historical_mutations(
                    artifacts.historical_mutation_candidates,
                    rule_versions,
                )
            )

            verdict = "FAIL" if violations else "PASS"

            verdict_basis = (
                "One or more implemented M0 structural rules "
                "reported violations."
                if violations
                else
                "All implemented M0 structural rules "
                "completed without an observed violation."
            )


        guard_violations, guard_report = _EvidenceAncestryGuard(artifacts, self).evaluate()
        violations.extend(code for code in guard_violations if code not in violations)
        appendix, report_overflow = _serialize_ancestry_report(
            guard_report, violations, self.MAX_ANCESTRY_REPORT_BYTES)
        if report_overflow and "UNKNOWN" not in violations:
            violations.append("UNKNOWN")
        if has_primary_artifacts:
            verdict = "FAIL" if violations else "PASS"
            verdict_basis = (
                "One or more implemented M0 structural rules reported violations."
                if violations else
                "All implemented M0 structural rules completed without an observed violation."
            )

        # Version-aware report: declared rule packs differ from engine-owned
        # nonoptional invariants; never present an unqualified structural PASS.
        verdict_basis = (
            f"{verdict_basis} Declared rule versions: {rule_versions!r}. "
            f"Engine-enforced reference firewall: {self.ALWAYS_ON_FIREWALL_VERSION}. "
            f"Engine-enforced ancestry guard: {self.ALWAYS_ON_ANCESTRY_VERSION}. "
            "PASS, if any, is limited to implemented structural checks and "
            "does not establish truth, identity, or independent provenance."
            f"{appendix}"
        )

        return AuditResult(
            audit_id=audit_id,
            inspector_id=self.INSPECTOR_ID,
            inspector_version=self.INSPECTOR_VERSION,
            execution_timestamp=execution_timestamp,
            configuration_id=configuration_id,
            rule_versions=rule_versions,
            artifacts_examined=artifacts.artifacts_examined,
            violations=tuple(violations),
            verdict=verdict,
            verdict_basis=verdict_basis,
            composition_summaries=composition_summaries if has_primary_artifacts else (),
        )

    @staticmethod
    def _evaluate_composition_requests(
        requests: Iterable[CompositionRequest],
        prior_audit_results: Iterable[AuditResult],
        rule_versions: tuple[str, ...],
    ) -> tuple[list[str], tuple[CompositionSummary, ...]]:
        violations: list[str] = []
        summaries: list[CompositionSummary] = []
        firewall_version = "M0-F15-1.0"
        summary_rule_id = "M0-F15-LOCAL-SUMMARY"
        summary_rule_version = "1.0"
        canonical_irg_ids = {f"IRG-{index:02d}" for index in range(1, 6)}
        results_by_id: dict[str, list[AuditResult]] = {}
        request_list = tuple(requests)
        request_id_counts: dict[str, int] = {}

        for result in prior_audit_results:
            results_by_id.setdefault(result.audit_id, []).append(result)
        for request in request_list:
            request_id_counts[request.composition_id] = (
                request_id_counts.get(request.composition_id, 0) + 1
            )

        forbidden = {
            CompositionConclusion.GLOBAL_TRUTH,
            CompositionConclusion.CLAIM_TRUTH,
            CompositionConclusion.SAME_ENTITY,
            CompositionConclusion.ONTOLOGICAL_IDENTITY,
            CompositionConclusion.CONSCIOUSNESS,
        }

        for request in request_list:
            participants = request.participant_results
            irg_ids = [p.irg_id for p in participants]
            audit_ids = [p.audit_id for p in participants]

            if (
                not participants
                or len(participants) > 5
                or len(set(irg_ids)) != len(irg_ids)
                or not set(irg_ids).issubset(canonical_irg_ids)
                or len(set(audit_ids)) != len(audit_ids)
                or request_id_counts[request.composition_id] != 1
                or request.composition_id in results_by_id
            ):
                violations.append("UNKNOWN")
                continue

            if request.requested_input_scope == CompositionInputScope.ALL_FIVE_IRGS:
                if len(participants) != 5 or set(irg_ids) != canonical_irg_ids:
                    violations.append("UNKNOWN")
                    continue

            if any(len(results_by_id.get(aid, [])) != 1 for aid in audit_ids):
                violations.append("UNKNOWN")
                continue

            if firewall_version not in rule_versions:
                violations.append("UNKNOWN")
                continue

            # F15-I1: a structurally unambiguous truth-escalation request
            # cannot be downgraded by caller-controlled summary-rule fields.
            if request.requested_conclusion == CompositionConclusion.CLAIM_TRUTH:
                violations.append("COMPOSITION_FORBIDDEN")
                continue

            if request.requested_conclusion in forbidden:
                if (
                    request.composition_rule_id == "M0-F15"
                    and request.composition_rule_version == firewall_version
                ):
                    violations.append("COMPOSITION_FORBIDDEN")
                else:
                    violations.append("UNKNOWN")
                continue

            # Legacy BOUNDED_SUMMARY is deliberately not an accepted output
            # semantic. The canonical, observable output is LOCAL_RESULT_SUMMARY.
            if request.requested_conclusion != CompositionConclusion.LOCAL_RESULT_SUMMARY:
                violations.append("UNKNOWN")
                continue

            if (
                request.composition_rule_id != summary_rule_id
                or request.composition_rule_version != summary_rule_version
            ):
                violations.append("UNKNOWN")
                continue

            records = tuple(
                CompositionSummaryRecord(
                    audit_id=participant.audit_id,
                    declared_irg_id=participant.irg_id,
                    declared_scope=participant.declared_scope,
                    verdict=results_by_id[participant.audit_id][0].verdict,
                    rule_versions=results_by_id[participant.audit_id][0].rule_versions,
                    configuration_id=results_by_id[participant.audit_id][0].configuration_id,
                )
                for participant in participants
            )
            observed_verdicts = sorted({record.verdict for record in records})
            verdict_counts = tuple(
                (verdict, sum(record.verdict == verdict for record in records))
                for verdict in observed_verdicts
            )
            summaries.append(
                CompositionSummary(
                    composition_id=request.composition_id,
                    summary_rule_id=summary_rule_id,
                    summary_rule_version=summary_rule_version,
                    requested_input_scope=request.requested_input_scope,
                    records=records,
                    verdict_counts=verdict_counts,
                    scope=request.scope,
                    limitations=(
                        request.limitations
                        + " Declared IRG labels and per-record scopes are caller-supplied and are not independently authenticated."
                        + " This summary describes supplied audit-result records only; it does not establish Claim truth."
                    ),
                )
            )

        return violations, tuple(summaries)

    @staticmethod
    def _check_claim_identity(
        claims: Iterable[Claim],
    ) -> list[str]:
        seen: set[str] = set()
        violations: list[str] = []

        for claim in claims:
            if claim.claim_id in seen:
                violations.append("IDENTITY_CONFLICT")
            else:
                seen.add(claim.claim_id)

        return violations

    @staticmethod
    def _check_provenance(
        historical_states: Iterable[HistoricalState],
        lineage_edges: Iterable[LineageEdge],
        retrieval_events: Iterable[RetrievalEvent],
    ) -> list[str]:
        violations: list[str] = []

        for state in historical_states:
            if state.provenance is None:
                violations.append("MISSING_PROVENANCE")

        for edge in lineage_edges:
            if edge.provenance is None:
                violations.append("MISSING_PROVENANCE")
            if any(
                authorization.provenance is None
                or authorization.provenance.source_reference is None
                for authorization in edge.compatibility_authorizations
            ):
                violations.append("MISSING_PROVENANCE")

        for event in retrieval_events:
            if event.provenance is None:
                violations.append("MISSING_PROVENANCE")

        return violations

    @staticmethod
    def _check_lineage(
        lineage_edges: Iterable[LineageEdge],
    ) -> list[str]:
        violations: list[str] = []

        for edge in lineage_edges:
            if not edge.relation_type.strip():
                violations.append("LINEAGE_INADMISSIBLE")

            if not edge.admissibility_status.strip():
                violations.append("LINEAGE_INADMISSIBLE")

        return violations

    @staticmethod
    def _check_retrieval(
        retrieval_events: Iterable[RetrievalEvent],
    ) -> list[str]:
        violations: list[str] = []

        for event in retrieval_events:
            if not event.fidelity_status.strip():
                violations.append("RETRIEVAL_DISCREPANCY")

            declared = event.transformation_reference
            observed = event.observed_transformation_reference

            if declared is None and observed is not None:
                violations.append("UNDECLARED_TRANSFORMATION")
            elif declared is not None and observed is not None:
                if declared != observed:
                    violations.append("RETRIEVAL_DISCREPANCY")

        return violations

    @staticmethod
    def _check_evidence(
        evidence: Iterable[Evidence],
        *,
        prior_audit_results: Iterable[AuditResult] = (),
        composition_requests: Iterable[CompositionRequest] = (),
        rule_versions: tuple[str, ...] = (),
    ) -> list[str]:
        evidence_items = tuple(evidence)
        violations: list[str] = []
        # Nonoptional M0-REF-GUARD-1.0: caller rule-version selection
        # cannot authorize composition artifacts to masquerade as evidence.
        prior_results = tuple(prior_audit_results)
        summary_ids = {
            summary.composition_id
            for result in prior_results
            for summary in result.composition_summaries
        }
        audit_result_ids = {result.audit_id for result in prior_results}
        request_ids = {request.composition_id for request in composition_requests}
        forbidden_reference_types = {
            "AUDIT_RESULT",
            "COMPOSITION_REQUEST",
            "COMPOSITION_SUMMARY",
        }

        observation_owners: dict[str, list[Evidence]] = {}

        for item in evidence_items:
            seen_in_item: set[str] = set()

            # F15 applies to every typed reference carried by an evidence
            # wrapper, not only observation_refs. Otherwise a composition
            # artifact can be smuggled through derivation_reference and the
            # wrapper can then be cited as ordinary evidence.
            if item.derivation_reference is not None:
                reference = item.derivation_reference
                reference_id = reference.reference_id
                if (
                    reference.reference_type in forbidden_reference_types
                    or reference_id in summary_ids
                    or reference_id in audit_result_ids
                    or reference_id in request_ids
                ):
                    violations.append("COMPOSITION_FORBIDDEN")

            for reference in item.observation_refs:
                observation_id = reference.reference_id

                if (
                    reference.reference_type in forbidden_reference_types
                    or observation_id in summary_ids
                    or observation_id in audit_result_ids
                    or observation_id in request_ids
                ):
                    violations.append("COMPOSITION_FORBIDDEN")
                    continue

                if observation_id in seen_in_item:
                    continue

                seen_in_item.add(observation_id)

                observation_owners.setdefault(
                    observation_id,
                    [],
                ).append(item)

        for owners in observation_owners.values():
            if len(owners) < 2:
                continue

            if all(
                item.independence_status == IndependenceStatus.INDEPENDENT
                for item in owners
            ):
                violations.append("EVIDENCE_INFLATION")

        return violations

    @staticmethod
    def _check_temporal_relations(
        historical_states: Iterable[HistoricalState],
        lineage_edges: Iterable[LineageEdge],
        rule_versions: tuple[str, ...],
    ) -> list[str]:
        states = tuple(historical_states)
        state_references = [
            (
                state.content_reference.reference_id,
                state.content_reference.reference_type,
            )
            for state in states
        ]
        has_duplicate_references = (
            len(set(state_references)) != len(state_references)
        )
        state_reference_set = set(state_references)
        related_state_pairs, violations = AuditEngine._collect_temporal_pairs(
            state_reference_set,
            lineage_edges,
            rule_versions,
        )

        if has_duplicate_references:
            # Resolve every supplied edge, but never use candidate pairs when a
            # typed content reference names multiple state occurrences.
            return ["UNKNOWN", *violations]

        if violations:
            return violations

        if len(states) < 2:
            return []

        if len(states) == 2:
            first, second = states
            pair = frozenset(state_references)

            if pair not in related_state_pairs:
                return ["TEMPORALLY_UNRESOLVED"]

            return []

        adjacency: dict[tuple[str, str], set[tuple[str, str]]] = {
            reference: set() for reference in state_references
        }

        for pair in related_state_pairs:
            first, second = tuple(pair)
            adjacency[first].add(second)
            adjacency[second].add(first)

        start = state_references[0]
        visited: set[tuple[str, str]] = {start}
        frontier = [start]

        while frontier:
            current = frontier.pop()

            for neighbor in adjacency[current]:
                if neighbor in visited:
                    continue

                visited.add(neighbor)
                frontier.append(neighbor)

        if len(visited) != len(states):
            return ["TEMPORALLY_UNRESOLVED"]

        return []

    @staticmethod
    def _collect_temporal_pairs(
        state_reference_set: set[tuple[str, str]],
        lineage_edges: Iterable[LineageEdge],
        rule_versions: tuple[str, ...],
    ) -> tuple[set[frozenset[tuple[str, str]]], list[str]]:
        """Resolve and collect only temporally admissible typed edge pairs."""
        related_state_pairs: set[frozenset[tuple[str, str]]] = set()

        violations: list[str] = []
        for edge in lineage_edges:
            source = (
                edge.from_reference.reference_id,
                edge.from_reference.reference_type,
            )
            target = (
                edge.to_reference.reference_id,
                edge.to_reference.reference_type,
            )

            # Resolve both typed endpoints before evaluating the relationship.
            if (
                source not in state_reference_set
                or target not in state_reference_set
            ):
                violations.append("TEMPORALLY_UNRESOLVED")
                continue

            if source[1] != target[1]:
                authorized, violation = AuditEngine._authorize_cross_type_edge(
                    edge, rule_versions
                )
                if violation is not None:
                    violations.append(violation)
                if not authorized:
                    continue

            if source != target:
                related_state_pairs.add(frozenset((source, target)))

        return related_state_pairs, violations

    @staticmethod
    def _authorize_cross_type_edge(
        edge: LineageEdge,
        rule_versions: tuple[str, ...],
    ) -> tuple[bool, str | None]:
        authorizations = edge.compatibility_authorizations
        if not authorizations:
            return False, None

        applicable: list[LineageCompatibilityAuthorization] = []
        for authorization in authorizations:
            if (
                authorization.provenance is None
                or authorization.provenance.source_reference is None
            ):
                return False, "UNKNOWN"
            rule = (authorization.rule_id, authorization.rule_version)
            if (
                rule not in SUPPORTED_LINEAGE_AUTHORIZATION_RULES
                or f"{authorization.rule_id}-{authorization.rule_version}"
                not in rule_versions
            ):
                return False, "UNKNOWN"

            if (
                authorization.source_reference_type
                == edge.from_reference.reference_type
                and authorization.target_reference_type
                == edge.to_reference.reference_type
                and authorization.relation_type == edge.relation_type
            ):
                applicable.append(authorization)

        if not applicable:
            return False, None
        if len(applicable) != 1:
            return False, "UNKNOWN"

        authorization = applicable[0]
        trusted_policy = (
            authorization.rule_id,
            authorization.rule_version,
            authorization.source_reference_type,
            authorization.target_reference_type,
            authorization.relation_type,
        )
        if trusted_policy not in TRUSTED_LINEAGE_COMPATIBILITY_POLICIES:
            return False, "UNKNOWN"

        if authorization.decision is LineageAuthorizationDecision.DENIED:
            return False, "LINEAGE_INADMISSIBLE"

        # The request's AUTHORIZED record is only a claim. No independent
        # per-edge authorization source exists, so preserve UNKNOWN and fail
        # closed even when the claim matches the engine compatibility policy.
        return False, "UNKNOWN"

    @staticmethod
    def _check_lineage_candidates(
        candidates: Iterable[LineageCandidate],
        rule_versions: tuple[str, ...],
    ) -> list[str]:
        violations: list[str] = []
        supported_rule = "M0-F07-1.0"

        for candidate in candidates:
            if candidate.lineage_rule_version != supported_rule:
                violations.append("UNKNOWN")
                continue

            if candidate.lineage_rule_version not in rule_versions:
                violations.append("UNKNOWN")
                continue

            basis = candidate.inference_basis.strip()

            if basis == "SIMILARITY":
                violations.append("LINEAGE_INADMISSIBLE")
            elif basis == "EXPLICIT_RELATION":
                continue
            else:
                violations.append("UNKNOWN")

        return violations

    @staticmethod
    def _check_historical_mutations(
        candidates: Iterable[HistoricalMutationCandidate],
        rule_versions: tuple[str, ...],
    ) -> list[str]:
        violations: list[str] = []
        supported_rule = "M0-F05-1.0"

        for candidate in candidates:
            if candidate.mutation_rule_version != supported_rule:
                violations.append("UNKNOWN")
                continue

            if candidate.mutation_rule_version not in rule_versions:
                violations.append("UNKNOWN")
                continue

            canonical = candidate.canonical_integrity
            replacement = candidate.attempted_replacement_integrity

            if canonical is None or replacement is None:
                violations.append("UNKNOWN")
                continue

            if canonical.method != replacement.method:
                violations.append("UNKNOWN")
                continue

            if canonical.value != replacement.value:
                violations.append("HISTORY_MUTATION")

        return violations

    @staticmethod
    def _check_assessments(
        assessments: Iterable[Assessment],
        evidence: Iterable[Evidence],
        prior_audit_results: Iterable[AuditResult] = (),
        rule_versions: tuple[str, ...] = (),
        *,
        composition_requests: Iterable[CompositionRequest] = (),
    ) -> list[str]:
        evidence_by_id: dict[str, list[Evidence]] = {}
        for item in evidence:
            evidence_by_id.setdefault(item.evidence_id, []).append(item)

        # F11 is opt-in by declared rule version, matching the engine's
        # versioned F05/F07 behavior. Without F11, legacy assessment resolution
        # remains unchanged and an audit-result-only ID is simply inadmissible.
        f11_enabled = "M0-F11-1.0" in rule_versions
        f15_enabled = "M0-F15-1.0" in rule_versions
        # Always-on collision detection uses the entire supplied record set,
        # without declaring an optional F11/F15 rule to be active.
        supplied_prior_results = tuple(prior_audit_results)
        supplied_requests = tuple(composition_requests)
        forbidden_source_ids = {item.audit_id for item in supplied_prior_results}
        forbidden_source_ids.update(
            summary.composition_id
            for item in supplied_prior_results
            for summary in item.composition_summaries
        )
        forbidden_source_ids.update(request.composition_id for request in supplied_requests)
        audit_results_by_id: dict[str, list[AuditResult]] = {}
        summary_ids: dict[str, int] = {}
        request_ids: dict[str, int] = {}
        for request in supplied_requests:
            request_ids[request.composition_id] = (
                request_ids.get(request.composition_id, 0) + 1
            )
        if f11_enabled or f15_enabled:
            for result in supplied_prior_results:
                audit_results_by_id.setdefault(result.audit_id, []).append(result)
                for summary in result.composition_summaries:
                    summary_ids[summary.composition_id] = (
                        summary_ids.get(summary.composition_id, 0) + 1
                    )

        violations: list[str] = []

        for assessment in assessments:
            for reference in assessment.admissible_evidence_refs:
                reference_id = reference.reference_id
                matches = evidence_by_id.get(reference_id, [])

                # Always-on typed reference firewall (v1.1).
                if reference.reference_type in {
                    "AUDIT_RESULT",
                    "COMPOSITION_REQUEST",
                    "COMPOSITION_SUMMARY",
                }:
                    violations.append("COMPOSITION_FORBIDDEN")
                    continue

                if f15_enabled:
                    result_matches = audit_results_by_id.get(reference_id, [])
                    summary_count = summary_ids.get(reference_id, 0)
                    request_count = request_ids.get(reference_id, 0)
                    if (result_matches or summary_count or request_count) and matches:
                        violations.append("UNKNOWN")
                        continue
                    if (
                        len(result_matches) > 1
                        or summary_count > 1
                        or request_count > 1
                    ):
                        violations.append("UNKNOWN")
                        continue
                    if (
                        len(result_matches) == 1
                        or summary_count == 1
                        or request_count == 1
                    ):
                        violations.append("COMPOSITION_FORBIDDEN")
                        continue

                # A caller cannot manufacture an accepted Evidence ID by
                # reusing the ID of a supplied result/summary/request. The
                # collision remains UNKNOWN, not inferred as evidence.
                if not f15_enabled and matches and reference_id in forbidden_source_ids:
                    violations.append("UNKNOWN")
                    continue

                if f11_enabled:
                    result_matches = audit_results_by_id.get(reference_id, [])
                    if result_matches and matches:
                        # Cross-kind ID collision is ambiguous; neither kind
                        # may silently override the other.
                        violations.append("UNKNOWN")
                        continue
                    if len(result_matches) > 1:
                        # Duplicate audit-result IDs are ambiguous too.
                        violations.append("UNKNOWN")
                        continue
                    if len(result_matches) == 1:
                        violations.append("COMPOSITION_FORBIDDEN")
                        continue

                if len(matches) == 1:
                    continue
                if len(matches) > 1:
                    # Duplicate evidence IDs make the reference ambiguous.
                    violations.append("UNKNOWN")
                else:
                    violations.append("EVIDENCE_INADMISSIBLE")

        return violations



class _EvidenceAncestryGuard:
    """Screen only supplied declarations; never authenticate independence."""

    FORBIDDEN = frozenset({"AUDIT_RESULT", "COMPOSITION_REQUEST", "COMPOSITION_SUMMARY"})
    CONTENT_KINDS = frozenset({"CLAIM", "OBSERVATION", "EVIDENCE", "ASSESSMENT"})

    def __init__(self, artifacts: AuditInput, engine: AuditEngine) -> None:
        self.artifacts = artifacts
        self.engine = engine
        self.index: dict[tuple[str, str], list] = {}
        self.edges: dict[tuple[str, str], list[Reference]] = {}
        self.cache: dict[tuple[str, str], dict] = {}
        self.forbidden_ids: set[str] = set()
        self.global_unknown = False
        self.violation_codes: set[str] = set()
        groups = (
            ("CLAIM", "claim_id", artifacts.claims),
            ("OBSERVATION", "observation_id", artifacts.observations),
            ("EVIDENCE", "evidence_id", artifacts.evidence),
            ("ASSESSMENT", "assessment_id", artifacts.assessments),
            ("AUDIT_RESULT", "audit_id", artifacts.prior_audit_results),
            ("COMPOSITION_REQUEST", "composition_id", artifacts.composition_requests),
        )
        # Participant bindings refer to results; they do not define more results.
        summaries = tuple(s for r in artifacts.prior_audit_results
                          for s in r.composition_summaries)
        groups += (("COMPOSITION_SUMMARY", "composition_id", summaries),)
        object_count = sum(len(items) for _, _, items in groups)
        edge_count = (
            sum(len(o.provenance_refs) for o in artifacts.observations)
            + sum(len(e.observation_refs) + 1 for e in artifacts.evidence)
            + sum(len(a.admissible_evidence_refs) for a in artifacts.assessments)
            + len(artifacts.retrieval_events)
        )
        if (object_count > engine.MAX_ANCESTRY_OBJECTS
                or edge_count > engine.MAX_ANCESTRY_EDGES):
            self.global_unknown = True
            self.violation_codes.add("UNKNOWN")
            return
        for kind, field, items in groups:
            for item in items:
                key = (kind, getattr(item, field))
                self.index.setdefault(key, []).append(item)
                if kind in self.FORBIDDEN:
                    self.forbidden_ids.add(key[1])
        for item in artifacts.observations:
            self.edges.setdefault(("OBSERVATION", item.observation_id), []).extend(
                item.provenance_refs)
        for item in artifacts.evidence:
            key = ("EVIDENCE", item.evidence_id)
            self.edges.setdefault(key, []).extend(item.observation_refs)
            reference = item.derivation_reference
            if reference is not None and (
                    reference.reference_type != "TRANSFORMATION"
                    or reference.reference_id in self.forbidden_ids):
                self.edges[key].append(reference)
        for item in artifacts.assessments:
            self.edges.setdefault(("ASSESSMENT", item.assessment_id), []).extend(
                item.admissible_evidence_refs)
        for event in artifacts.retrieval_events:
            # Different typed keys with the same text ID are separate endpoints.
            self.edges.setdefault(self.key(event.retrieved_reference), []).append(
                event.source_reference)

    @staticmethod
    def key(reference: Reference) -> tuple[str, str]:
        return (reference.reference_type, reference.reference_id)

    @staticmethod
    def report_id(value) -> str | None:
        try:
            if isinstance(value, str) and value.strip() and len(value.encode("utf-8")) <= 128:
                return value
        except UnicodeError:
            pass
        return None

    def unique(self, key: tuple[str, str]):
        matches = self.index.get(key, ())
        return matches[0] if len(matches) == 1 else None

    def facts(self, root: tuple[str, str]) -> dict:
        """Memoize intrinsic graph facts, never a target-specific disposition."""
        if root in self.cache:
            return self.cache[root]
        unknown = self.global_unknown
        codes: set[str] = set()
        reached: set[tuple[str, str]] = set()
        active: set[tuple[str, str]] = set()
        complete: set[tuple[str, str]] = set()
        heights: dict[tuple[str, str], int] = {}
        stack = [] if self.global_unknown else [(root, False)]
        while stack:
            key, leaving = stack.pop()
            if leaving:
                active.remove(key)
                complete.add(key)
                heights[key] = max((1 + heights.get(self.key(r), 0)
                                   for r in self.edges.get(key, ())), default=0)
                continue
            # Evidence root-ID collision uses the existing Assessment UNKNOWN
            # rule. Ancestor references retain the stricter result-ID firewall.
            root_evidence = key == root and key[0] == "EVIDENCE" and key not in active
            if key[0] in self.FORBIDDEN or (key[1] in self.forbidden_ids and not root_evidence):
                codes.add("COMPOSITION_FORBIDDEN")
                if self.unique(key) is None:
                    unknown = True
                continue
            if key in active:
                unknown = True
                continue
            if key in complete:
                continue
            obj = self.unique(key)
            if key[0] not in self.CONTENT_KINDS or obj is None:
                unknown = True
                continue
            reached.add(key)
            if (key[0] == "OBSERVATION"
                    and obj.record_version != "M0-EAG-OBSERVATION-0.1"):
                unknown = True
            active.add(key)
            stack.append((key, True))
            children = sorted(set(self.key(r) for r in self.edges.get(key, ())))
            stack.extend((child, False) for child in reversed(children))
        # Longest DAG path, not first-visit depth: a shortcut cannot hide depth.
        # Cycles already make resolution UNKNOWN.
        if heights.get(root, 0) > self.engine.MAX_ANCESTRY_DEPTH:
            unknown = True
        result = {"unknown": unknown, "codes": codes, "reached": reached}
        self.cache[root] = result
        return result

    @staticmethod
    def base_report() -> dict:
        return {
            "profile": "M0-EAG-0.1",
            "mandatory_guards": ["M0-REF-GUARD-1.0", "M0-EAG-0.1"],
            "independent_admission_authority": "NONE",
            "candidate_use": "NOT_EVALUATED",
            "candidate_ancestry": "NOT_EVALUATED",
            "assessments": [], "report_complete": True,
            "claim_truth": "UNKNOWN", "entity_continuity": "UNKNOWN",
        }

    def evaluate(self) -> tuple[list[str], dict]:
        report = self.base_report()
        if self.global_unknown:
            report.update(candidate_ancestry="UNKNOWN", report_complete=False,
                          guard_limit_exceeded=True, use_disposition="UNKNOWN")
            return ["UNKNOWN"], report
        roots = [("EVIDENCE", e.evidence_id) for e in self.artifacts.evidence]
        roots += [("OBSERVATION", o.observation_id) for o in self.artifacts.observations]
        candidate_unknown = False
        for root in roots:
            fact = self.facts(root)
            candidate_unknown |= fact["unknown"]
            self.violation_codes.update(fact["codes"])
        source_owners: dict[tuple[str, str], set[str]] = {}
        for item in self.artifacts.evidence:
            if (item.independence_status != IndependenceStatus.INDEPENDENT
                    or self.unique(("EVIDENCE", item.evidence_id)) is not item):
                continue
            for key in self.facts(("EVIDENCE", item.evidence_id))["reached"]:
                if key != ("EVIDENCE", item.evidence_id):
                    source_owners.setdefault(key, set()).add(item.evidence_id)
        if any(len(owners) > 1 for owners in source_owners.values()):
            self.violation_codes.add("EVIDENCE_INFLATION")
        findings = []
        for assessment in sorted(self.artifacts.assessments,
                                 key=lambda a: (a.assessment_id, a.assessment_version)):
            target = assessment.target
            use = assessment.requested_use
            reasons: set[str] = set()
            unknown = False
            codes: set[str] = set()
            reached: set[tuple[str, str]] = set()
            target_key = self.key(target.subject_reference) if target is not None else None
            target_obj = self.unique(target_key) if target_key is not None else None
            safe_id = self.report_id(assessment.assessment_id)
            if safe_id is None or target is None or use is None:
                unknown = True
                reasons.add("MISSING_OR_UNREPORTABLE_TARGET_USE")
            if target is not None and target_obj is None:
                unknown = True
                reasons.add("TARGET_UNRESOLVED")
            if self.unique(("ASSESSMENT", assessment.assessment_id)) is None:
                unknown = True
                reasons.add("ASSESSMENT_ID_AMBIGUOUS")
            ancestry_unknown = False
            for reference in assessment.admissible_evidence_refs:
                item = self.unique(self.key(reference))
                if reference.reference_type != "EVIDENCE" or not isinstance(item, Evidence):
                    unknown = True
                    ancestry_unknown = True
                    reasons.add("EVIDENCE_UNRESOLVED")
                    # Preserve existing direct F11/F15 specialized diagnostics.
                    continue
                if reference.reference_id in self.forbidden_ids:
                    unknown = True
                    reasons.add("PROTECTED_RESULT_ID_COLLISION")
                fact = self.facts(self.key(reference))
                ancestry_unknown |= fact["unknown"]
                codes.update(fact["codes"])
                reached.update(fact["reached"])
                for observation_ref in item.observation_refs:
                    observation = self.unique(self.key(observation_ref))
                    if (observation_ref.reference_type != "OBSERVATION"
                            or not isinstance(observation, ObservationRecord)
                            or observation.target != target
                            or observation.declared_use != use):
                        unknown = True
                        reasons.add("OBSERVATION_BINDING_UNRESOLVED")
            # Bind every relied-on reachable Observation, not only wrappers.
            # Intrinsic cached graph facts remain independent of target/use.
            for key in sorted(reached):
                if key[0] == "OBSERVATION":
                    observation = self.unique(key)
                    if observation.target != target or observation.declared_use != use:
                        unknown = True
                        reasons.add("OBSERVATION_BINDING_UNRESOLVED")
            unknown |= ancestry_unknown
            if ancestry_unknown:
                reasons.add("ANCESTRY_UNRESOLVED")
            presence = "NOT_EVALUATED"
            disposition = "UNKNOWN"
            if use == EvidenceUse.RECORD_DESCRIPTION:
                exact = (
                    target is not None
                    and target.property_id == "SUPPLIED_RECORD_PRESENT"
                    and target.subject_reference.reference_type in {"CLAIM", "OBSERVATION"}
                    and assessment.rule_version == "M0-EAG-RECORD-PRESENCE-0.1"
                    and assessment.scope == "SUPPLIED_INPUT_RECORDS_ONLY"
                )
                if exact and target_obj is not None:
                    presence = "MATCH"
                else:
                    unknown = True
                    reasons.add("UNSUPPORTED_DESCRIPTION_BINDING")
                if not unknown and not codes:
                    disposition = "RECORD_DESCRIPTION_ONLY"
            elif use == EvidenceUse.INDEPENDENT_TARGET_SUPPORT:
                if target is None or target.subject_reference.reference_type != "CLAIM":
                    unknown = True
                    reasons.add("SUPPORT_TARGET_UNRESOLVED")
                if (target_key in reached
                        or ("ASSESSMENT", assessment.assessment_id) in reached):
                    codes.add("EVIDENCE_INADMISSIBLE")
                    disposition = "KNOWN_INADMISSIBLE"
                    reasons.add("EXACT_SELF_CONFIRMATION")
                else:
                    unknown = True
                    reasons.add("NO_INDEPENDENT_ADMISSION_AUTHORITY")
            else:
                unknown = True
                reasons.add("USE_NOT_DECLARED")
            if unknown:
                codes.add("UNKNOWN")
            if "COMPOSITION_FORBIDDEN" in codes:
                disposition = "KNOWN_INADMISSIBLE"
            self.violation_codes.update(codes)
            findings.append({
                "assessment_id": safe_id,
                "target": ({"reference_id": target.subject_reference.reference_id,
                            "reference_type": target.subject_reference.reference_type}
                           if target is not None else None),
                "property_id": target.property_id if target is not None else None,
                "requested_use": use.value if use is not None else None,
                "ancestry": "UNKNOWN" if ancestry_unknown else "TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT",
                "record_presence": presence,
                "use_disposition": disposition,
                "source_authentication": "UNKNOWN", "reasons": sorted(reasons),
            })
        report.update(
            candidate_ancestry=("UNKNOWN" if candidate_unknown else
                               "TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT" if roots else "NOT_EVALUATED"),
            assessments=findings)
        return sorted(self.violation_codes), report


def _serialize_ancestry_report(report: dict, violations: list[str],
                               limit: int) -> tuple[str, bool]:
    def encode(value):
        return (EAG_FINDINGS_BEGIN
                + json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False)
                + EAG_FINDINGS_END)
    appendix = encode(report)
    if len(appendix.encode("utf-8")) <= limit:
        return appendix, False
    fallback = dict(report, assessments=[], report_complete=False,
                    report_limit_exceeded=True, use_disposition="UNKNOWN",
                    candidate_ancestry="UNKNOWN",
                    retained_violation_codes=sorted(set(violations) | {"UNKNOWN"}))
    return encode(fallback), True
