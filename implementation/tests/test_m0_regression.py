from dataclasses import replace

from core.audit_engine import AuditEngine, AuditInput
from core.schema import (
    Evidence,
    HistoricalMutationCandidate,
    IntegrityRepresentation,
    HistoricalState,
    IndependenceStatus,
    LineageAuthorizationDecision,
    LineageCompatibilityAuthorization,
    LineageEdge,
    LineageCandidate,
    Provenance,
    Reference,
    TemporalContext,
    Timestamp,
)


ENGINE = AuditEngine()
TS = Timestamp("M0-14J")


def ref(i):
    return Reference(i, "TEST")


def prov(i):
    return Provenance(
        source_reference=ref(i),
        relation="TEST_DERIVATION",
    )


def evidence(eid, obs, independence):
    return Evidence(
        evidence_id=eid,
        observation_refs=tuple(ref(x) for x in obs),
        evidence_level="OBSERVATION",
        independence_status=independence,
        derivation_reference=ref(f"DER-{eid}"),
        scope="M0-14J regression",
    )


def state(sid, *, state_id=None, content_reference=None):
    return HistoricalState(
        state_id=state_id or f"STATE-{sid}",
        claim_id="CLAIM-M0-14J",
        state_version=sid,
        observed_at=TS,
        state_context=TemporalContext(snapshot_id=sid),
        content_reference=content_reference or ref(sid),
        provenance=prov(f"PROV-{sid}"),
    )


def edge(a, b, *, from_reference=None, to_reference=None):
    return LineageEdge(
        lineage_id=f"EDGE-{a}-{b}",
        from_reference=from_reference or ref(a),
        to_reference=to_reference or ref(b),
        relation_type="EXPLICIT_RELATION",
        derivation_reference=ref(f"DER-{a}-{b}"),
        admissibility_status="ADMISSIBLE",
        provenance=prov(f"PROV-{a}-{b}"),
    )


def lineage_authorization(
    authorization_id,
    source_type,
    target_type,
    decision=LineageAuthorizationDecision.AUTHORIZED,
    *,
    rule_id="M0-LRT01-XTYPE",
    rule_version="1.0",
    relation_type="EXPLICIT_RELATION",
):
    return LineageCompatibilityAuthorization(
        authorization_id=authorization_id,
        rule_id=rule_id,
        rule_version=rule_version,
        source_reference_type=source_type,
        target_reference_type=target_type,
        relation_type=relation_type,
        decision=decision,
        provenance=prov(f"PROV-{authorization_id}"),
    )


def run(name, artifacts, rule_versions=("M0-1.0",)):
    return ENGINE.audit(
        artifacts,
        rule_versions=rule_versions,
        configuration_id="M0-14J",
        execution_timestamp=TS,
        audit_id=name,
    )


def test_d01_single_record_duplicate_observation():
    r = run(
        "D01",
        AuditInput(
            evidence=(
                evidence(
                    "E1",
                    ("OBS-1", "OBS-1"),
                    IndependenceStatus.INDEPENDENT,
                ),
            )
        ),
    )

    assert "EVIDENCE_INFLATION" not in r.violations


def test_d02_mixed_independence():
    r = run(
        "D02",
        AuditInput(
            evidence=(
                evidence(
                    "E1",
                    ("OBS-1",),
                    IndependenceStatus.INDEPENDENT,
                ),
                evidence(
                    "E2",
                    ("OBS-1",),
                    IndependenceStatus.DEPENDENT,
                ),
            )
        ),
    )

    assert "EVIDENCE_INFLATION" not in r.violations


def test_d03_three_state_chain():
    r = run(
        "D03",
        AuditInput(
            historical_states=(
                state("T1"),
                state("T2"),
                state("T3"),
            ),
            lineage_edges=(
                edge("T1", "T2"),
                edge("T2", "T3"),
            ),
        ),
    )

    assert "TEMPORALLY_UNRESOLVED" not in r.violations


def test_d04_three_state_disconnected():
    r = run(
        "D04",
        AuditInput(
            historical_states=(
                state("T1"),
                state("T2"),
                state("T3"),
            ),
            lineage_edges=(
                edge("T1", "T2"),
            ),
        ),
    )

    assert "TEMPORALLY_UNRESOLVED" in r.violations


def test_d05_distinct_observations():
    r = run(
        "D05",
        AuditInput(
            evidence=(
                evidence(
                    "E1",
                    ("OBS-1",),
                    IndependenceStatus.INDEPENDENT,
                ),
                evidence(
                    "E2",
                    ("OBS-2",),
                    IndependenceStatus.INDEPENDENT,
                ),
            )
        ),
    )

    assert "EVIDENCE_INFLATION" not in r.violations


def test_d06_two_state_relation():
    r = run(
        "D06",
        AuditInput(
            historical_states=(
                state("T1"),
                state("T2"),
            ),
            lineage_edges=(
                edge("T1", "T2"),
            ),
        ),
    )

    assert "TEMPORALLY_UNRESOLVED" not in r.violations


def test_lrt01_same_type_temporal_edge_connects_states():
    reference_a = Reference("CONTENT-LRT01-A", "STATE_CONTENT")
    reference_b = Reference("CONTENT-LRT01-B", "STATE_CONTENT")
    same_type_edge = edge(
        "A",
        "B",
        from_reference=reference_a,
        to_reference=reference_b,
    )
    related_pairs, authorization_violations = AuditEngine._collect_temporal_pairs(
        {
            (reference_a.reference_id, reference_a.reference_type),
            (reference_b.reference_id, reference_b.reference_type),
        },
        (same_type_edge,),
        ("M0-1.0",),
    )
    typed_pair = frozenset(
        {
            (reference_a.reference_id, reference_a.reference_type),
            (reference_b.reference_id, reference_b.reference_type),
        }
    )

    assert typed_pair in related_pairs
    assert authorization_violations == []

    r = run(
        "LRT01-SAME-TYPE",
        AuditInput(
            historical_states=(
                state("A", content_reference=reference_a),
                state("B", content_reference=reference_b),
            ),
            lineage_edges=(same_type_edge,),
        ),
    )

    assert "TEMPORALLY_UNRESOLVED" not in r.violations
    assert r.verdict == "PASS"


def test_same_type_caller_denied_status_does_not_gate_structural_connectivity():
    reference_a = Reference("CONTENT-DENIED-STATUS-A", "STATE_CONTENT")
    reference_b = Reference("CONTENT-DENIED-STATUS-B", "STATE_CONTENT")
    claimed_denial = replace(
        edge(
            "DENIED-STATUS-A",
            "DENIED-STATUS-B",
            from_reference=reference_a,
            to_reference=reference_b,
        ),
        admissibility_status="DENIED",
    )
    typed_pair = frozenset(
        {
            (reference_a.reference_id, reference_a.reference_type),
            (reference_b.reference_id, reference_b.reference_type),
        }
    )

    related_pairs, authorization_violations = AuditEngine._collect_temporal_pairs(
        {
            (reference_a.reference_id, reference_a.reference_type),
            (reference_b.reference_id, reference_b.reference_type),
        },
        (claimed_denial,),
        ("M0-1.0",),
    )

    assert typed_pair in related_pairs
    assert authorization_violations == []

    result = run(
        "LRT01-SAME-TYPE-DENIAL-CLAIM",
        AuditInput(
            historical_states=(
                state("DENIED-STATUS-A", content_reference=reference_a),
                state("DENIED-STATUS-B", content_reference=reference_b),
            ),
            lineage_edges=(claimed_denial,),
        ),
    )

    assert "LINEAGE_INADMISSIBLE" not in result.violations
    assert "TEMPORALLY_UNRESOLVED" not in result.violations
    assert result.verdict == "PASS"


def test_lrt01_matching_ids_with_mismatched_endpoint_type_do_not_connect():
    reference_a = Reference("CONTENT-LRT01-MISMATCH-A", "STATE_CONTENT")
    reference_b = Reference("CONTENT-LRT01-MISMATCH-B", "STATE_CONTENT")
    r = run(
        "LRT01-TYPE-MISMATCH",
        AuditInput(
            historical_states=(
                state("A", content_reference=reference_a),
                state("B", content_reference=reference_b),
            ),
            lineage_edges=(
                edge(
                    "A",
                    "B",
                    from_reference=Reference(
                        reference_a.reference_id, "OTHER_KIND"
                    ),
                    to_reference=reference_b,
                ),
            ),
        ),
    )

    assert "TEMPORALLY_UNRESOLVED" in r.violations
    assert r.verdict == "FAIL"


def test_lrt01_duplicate_typed_content_references_are_unknown():
    shared_reference = Reference("CONTENT-LRT01-SHARED", "STATE_CONTENT")
    r = run(
        "LRT01-DUPLICATE-TYPED-REFERENCE",
        AuditInput(
            historical_states=(
                state(
                    "A",
                    state_id="STATE-LRT01-A",
                    content_reference=shared_reference,
                ),
                state(
                    "B",
                    state_id="STATE-LRT01-B",
                    content_reference=shared_reference,
                ),
            ),
        ),
    )

    assert "UNKNOWN" in r.violations
    assert r.verdict == "FAIL"


def test_lrt01_distinct_state_ids_and_content_references_keep_edge_semantics():
    references = (
        Reference("CONTENT-LRT01-CHAIN-A", "STATE_CONTENT"),
        Reference("CONTENT-LRT01-CHAIN-B", "STATE_CONTENT"),
        Reference("CONTENT-LRT01-CHAIN-C", "STATE_CONTENT"),
    )
    r = run(
        "LRT01-DISTINCT-STATE-AND-CONTENT-IDS",
        AuditInput(
            historical_states=(
                state(
                    "VERSION-A",
                    state_id="STATE-INSTANCE-A",
                    content_reference=references[0],
                ),
                state(
                    "VERSION-B",
                    state_id="STATE-INSTANCE-B",
                    content_reference=references[1],
                ),
                state(
                    "VERSION-C",
                    state_id="STATE-INSTANCE-C",
                    content_reference=references[2],
                ),
            ),
            lineage_edges=(
                edge(
                    "CHAIN-A",
                    "CHAIN-B",
                    from_reference=references[0],
                    to_reference=references[1],
                ),
                edge(
                    "CHAIN-B",
                    "CHAIN-C",
                    from_reference=references[1],
                    to_reference=references[2],
                ),
            ),
        ),
    )

    assert "TEMPORALLY_UNRESOLVED" not in r.violations
    assert r.verdict == "PASS"


def test_lrt01_zero_states_with_unresolved_edge_fails():
    unresolved_edge = edge(
        "LRT01-ZERO-MISSING-A",
        "LRT01-ZERO-MISSING-B",
    )

    related_pairs, collection_violations = AuditEngine._collect_temporal_pairs(
        set(),
        (unresolved_edge,),
        ("M0-1.0",),
    )
    result = run(
        "LRT01-ZERO-STATES-UNRESOLVED-EDGE",
        AuditInput(lineage_edges=(unresolved_edge,)),
    )

    assert related_pairs == set()
    assert collection_violations == ["TEMPORALLY_UNRESOLVED"]
    assert "TEMPORALLY_UNRESOLVED" in result.violations
    assert result.verdict == "FAIL"


def test_lrt01_zero_states_without_edges_remains_temporally_clear():
    assert AuditEngine._check_temporal_relations((), (), ("M0-1.0",)) == []

    # With no primary artifacts, audit() preserves its existing aggregate
    # UNKNOWN result; its no-primary-artifact path does not run the checkers.
    result = run("LRT01-ZERO-STATES-NO-EDGES", AuditInput())
    assert result.violations == ()
    assert result.verdict == "UNKNOWN"


def test_lrt01_one_state_without_edges_remains_temporally_clear():
    only_state = state("LRT01-ONLY-STATE")

    assert AuditEngine._check_temporal_relations(
        (only_state,), (), ("M0-1.0",)
    ) == []

    result = run(
        "LRT01-ONE-STATE-NO-EDGES",
        AuditInput(historical_states=(only_state,)),
    )
    assert "TEMPORALLY_UNRESOLVED" not in result.violations
    assert result.verdict == "PASS"


def test_lrt01_one_state_with_unknown_edge_endpoint_fails():
    only_reference = ref("LRT01-ONE-STATE-KNOWN")
    missing_reference = ref("LRT01-ONE-STATE-MISSING")
    unresolved_edge = edge(
        "LRT01-ONE-STATE-KNOWN",
        "LRT01-ONE-STATE-MISSING",
        from_reference=only_reference,
        to_reference=missing_reference,
    )

    result = run(
        "LRT01-ONE-STATE-UNKNOWN-ENDPOINT",
        AuditInput(
            historical_states=(
                state("LRT01-ONE-STATE", content_reference=only_reference),
            ),
            lineage_edges=(unresolved_edge,),
        ),
    )

    assert "TEMPORALLY_UNRESOLVED" in result.violations
    assert result.verdict == "FAIL"


def test_lrt01_one_state_with_type_mismatched_edge_endpoint_fails():
    only_reference = Reference("LRT01-ONE-TYPE-KNOWN", "STATE_CONTENT")
    mismatched_reference = Reference("LRT01-ONE-TYPE-KNOWN", "OTHER_KIND")
    unresolved_edge = edge(
        "LRT01-ONE-TYPE-KNOWN",
        "LRT01-ONE-TYPE-TARGET",
        from_reference=mismatched_reference,
        to_reference=only_reference,
    )

    result = run(
        "LRT01-ONE-STATE-TYPE-MISMATCH",
        AuditInput(
            historical_states=(
                state("LRT01-ONE-TYPE", content_reference=only_reference),
            ),
            lineage_edges=(unresolved_edge,),
        ),
    )

    assert "TEMPORALLY_UNRESOLVED" in result.violations
    assert result.verdict == "FAIL"


def test_lrt01_connected_chain_with_unresolved_extra_edge_fails():
    references = tuple(
        ref(name)
        for name in ("LRT01-EXTRA-A", "LRT01-EXTRA-B", "LRT01-EXTRA-C")
    )
    states = tuple(
        state(name, content_reference=reference)
        for name, reference in zip(("A", "B", "C"), references)
    )
    unresolved_endpoint = ref("LRT01-EXTRA-MISSING")
    valid_edges = (
        edge("A", "B", from_reference=references[0], to_reference=references[1]),
        edge("B", "C", from_reference=references[1], to_reference=references[2]),
    )
    unresolved_edge = edge(
        "C", "MISSING", from_reference=references[2], to_reference=unresolved_endpoint
    )
    state_reference_set = {
        (reference.reference_id, reference.reference_type)
        for reference in references
    }

    related_pairs, collection_violations = AuditEngine._collect_temporal_pairs(
        state_reference_set,
        (*valid_edges, unresolved_edge),
        ("M0-1.0",),
    )
    unresolved_pair = frozenset(
        {
            (references[2].reference_id, references[2].reference_type),
            (unresolved_endpoint.reference_id, unresolved_endpoint.reference_type),
        }
    )
    result = run(
        "LRT01-CONNECTED-PLUS-UNRESOLVED-EDGE",
        AuditInput(historical_states=states, lineage_edges=(*valid_edges, unresolved_edge)),
    )

    assert unresolved_pair not in related_pairs
    assert collection_violations == ["TEMPORALLY_UNRESOLVED"]
    assert "TEMPORALLY_UNRESOLVED" in result.violations
    assert result.verdict == "FAIL"


def test_lrt01_unknown_endpoint_is_reported_and_not_connected():
    source = ref("LRT01-UNKNOWN-A")
    target = ref("LRT01-UNKNOWN-B")
    missing = ref("LRT01-UNKNOWN-ENDPOINT")
    unresolved_edge = edge(
        "A", "MISSING", from_reference=source, to_reference=missing
    )
    related_pairs, collection_violations = AuditEngine._collect_temporal_pairs(
        {
            (source.reference_id, source.reference_type),
            (target.reference_id, target.reference_type),
        },
        (unresolved_edge,),
        ("M0-1.0",),
    )
    result = run(
        "LRT01-UNKNOWN-ENDPOINT",
        AuditInput(
            historical_states=(
                state("A", content_reference=source),
                state("B", content_reference=target),
            ),
            lineage_edges=(unresolved_edge,),
        ),
    )

    assert related_pairs == set()
    assert collection_violations == ["TEMPORALLY_UNRESOLVED"]
    assert "TEMPORALLY_UNRESOLVED" in result.violations
    assert result.verdict == "FAIL"


def test_lrt01_mismatched_endpoint_type_is_reported_and_not_connected():
    source = Reference("LRT01-MISMATCH-A", "STATE_CONTENT")
    mismatched_source = Reference("LRT01-MISMATCH-A", "OTHER_KIND")
    target = Reference("LRT01-MISMATCH-B", "STATE_CONTENT")
    unresolved_edge = edge(
        "A", "B", from_reference=mismatched_source, to_reference=target
    )
    related_pairs, collection_violations = AuditEngine._collect_temporal_pairs(
        {
            (source.reference_id, source.reference_type),
            (target.reference_id, target.reference_type),
        },
        (unresolved_edge,),
        ("M0-1.0",),
    )
    result = run(
        "LRT01-MISMATCHED-ENDPOINT-TYPE",
        AuditInput(
            historical_states=(
                state("A", content_reference=source),
                state("B", content_reference=target),
            ),
            lineage_edges=(unresolved_edge,),
        ),
    )

    assert related_pairs == set()
    assert collection_violations == ["TEMPORALLY_UNRESOLVED"]
    assert "TEMPORALLY_UNRESOLVED" in result.violations
    assert result.verdict == "FAIL"


def test_lrt01_caller_authorized_cross_type_edge_remains_unknown():
    source = Reference("CONTENT-LRT01-CROSS-SHARED", "STATE_CONTENT")
    target = Reference("CONTENT-LRT01-CROSS-SHARED", "EVENT_RECORD")
    cross_edge = edge(
        "A",
        "B",
        from_reference=source,
        to_reference=target,
    )

    cross_edge = replace(
        cross_edge,
        compatibility_authorizations=(
            lineage_authorization("AUTH-A-B", "STATE_CONTENT", "EVENT_RECORD"),
        ),
    )
    typed_pair = frozenset(
        {
            (source.reference_id, source.reference_type),
            (target.reference_id, target.reference_type),
        }
    )
    related_pairs, temporal_violations = AuditEngine._collect_temporal_pairs(
        {
            (source.reference_id, source.reference_type),
            (target.reference_id, target.reference_type),
        },
        (cross_edge,),
        ("M0-1.0", "M0-LRT01-XTYPE-1.0"),
    )

    assert typed_pair not in related_pairs
    assert temporal_violations == ["UNKNOWN"]

    r = run(
        "LRT01-AUTHORIZED-CROSS-TYPE",
        AuditInput(
            historical_states=(
                state("A", content_reference=source),
                state("B", content_reference=target),
            ),
            lineage_edges=(cross_edge,),
        ),
        rule_versions=("M0-1.0", "M0-LRT01-XTYPE-1.0"),
    )

    assert "UNKNOWN" in r.violations
    assert r.verdict == "FAIL"


def test_lrt01_cross_type_edge_without_authorization_is_unresolved():
    source = Reference("CONTENT-LRT01-NOAUTH-SHARED", "STATE_CONTENT")
    target = Reference("CONTENT-LRT01-NOAUTH-SHARED", "EVENT_RECORD")
    unresolved_edge = edge(
        "A", "B", from_reference=source, to_reference=target
    )
    typed_pair = frozenset(
        {
            (source.reference_id, source.reference_type),
            (target.reference_id, target.reference_type),
        }
    )
    related_pairs, authorization_violations = AuditEngine._collect_temporal_pairs(
        {
            (source.reference_id, source.reference_type),
            (target.reference_id, target.reference_type),
        },
        (unresolved_edge,),
        ("M0-1.0",),
    )

    assert typed_pair not in related_pairs
    assert authorization_violations == []

    r = run(
        "LRT01-CROSS-TYPE-NO-AUTHORIZATION",
        AuditInput(
            historical_states=(
                state("A", content_reference=source),
                state("B", content_reference=target),
            ),
            lineage_edges=(unresolved_edge,),
        ),
    )

    assert "TEMPORALLY_UNRESOLVED" in r.violations
    assert r.verdict == "FAIL"


def test_lrt01_cross_type_authorization_is_directional():
    source = Reference("CONTENT-LRT01-DIRECTION-A", "STATE_CONTENT")
    target = Reference("CONTENT-LRT01-DIRECTION-B", "EVENT_RECORD")
    cross_edge = edge(
        "A", "B", from_reference=source, to_reference=target
    )

    cross_edge = replace(
        cross_edge,
        compatibility_authorizations=(
            lineage_authorization("AUTH-REVERSED", "EVENT_RECORD", "STATE_CONTENT"),
        ),
    )
    r = run(
        "LRT01-CROSS-TYPE-REVERSED-AUTHORIZATION",
        AuditInput(
            historical_states=(
                state("A", content_reference=source),
                state("B", content_reference=target),
            ),
            lineage_edges=(cross_edge,),
        ),
        rule_versions=("M0-1.0", "M0-LRT01-XTYPE-1.0"),
    )

    assert "TEMPORALLY_UNRESOLVED" in r.violations


def test_lrt01_explicit_cross_type_denial_is_inadmissible():
    source = Reference("CONTENT-LRT01-DENIED-A", "STATE_CONTENT")
    target = Reference("CONTENT-LRT01-DENIED-B", "EVENT_RECORD")
    cross_edge = edge(
        "A", "B", from_reference=source, to_reference=target
    )

    cross_edge = replace(
        cross_edge,
        compatibility_authorizations=(
            lineage_authorization(
                "AUTH-DENIED",
                "STATE_CONTENT",
                "EVENT_RECORD",
                LineageAuthorizationDecision.DENIED,
            ),
        ),
    )
    typed_pair = frozenset(
        {
            (source.reference_id, source.reference_type),
            (target.reference_id, target.reference_type),
        }
    )
    related_pairs, temporal_violations = AuditEngine._collect_temporal_pairs(
        {
            (source.reference_id, source.reference_type),
            (target.reference_id, target.reference_type),
        },
        (cross_edge,),
        ("M0-1.0", "M0-LRT01-XTYPE-1.0"),
    )

    assert typed_pair not in related_pairs
    assert temporal_violations == ["LINEAGE_INADMISSIBLE"]

    r = run(
        "LRT01-CROSS-TYPE-DENIED",
        AuditInput(
            historical_states=(
                state("A", content_reference=source),
                state("B", content_reference=target),
            ),
            lineage_edges=(cross_edge,),
        ),
        rule_versions=("M0-1.0", "M0-LRT01-XTYPE-1.0"),
    )

    assert "LINEAGE_INADMISSIBLE" in r.violations
    assert r.verdict == "FAIL"


def test_lrt01_unsupported_or_conflicting_authorization_is_unknown():
    source = Reference("CONTENT-LRT01-CONFLICT-A", "STATE_CONTENT")
    target = Reference("CONTENT-LRT01-CONFLICT-B", "EVENT_RECORD")
    cross_edge = edge(
        "A", "B", from_reference=source, to_reference=target
    )

    unsupported = replace(
        cross_edge,
        compatibility_authorizations=(
            lineage_authorization(
                "AUTH-UNSUPPORTED", "STATE_CONTENT", "EVENT_RECORD",
                rule_version="9.9",
            ),
        ),
    )
    conflicting = replace(
        cross_edge,
        compatibility_authorizations=(
            lineage_authorization("AUTH-ALLOW", "STATE_CONTENT", "EVENT_RECORD"),
            lineage_authorization(
                "AUTH-DENY", "STATE_CONTENT", "EVENT_RECORD",
                LineageAuthorizationDecision.DENIED,
            ),
        ),
    )
    states = (
        state("A", content_reference=source),
        state("B", content_reference=target),
    )

    unsupported_result = run(
        "LRT01-UNSUPPORTED-AUTHORIZATION",
        AuditInput(historical_states=states, lineage_edges=(unsupported,)),
        rule_versions=("M0-1.0", "M0-LRT01-XTYPE-9.9"),
    )
    conflicting_result = run(
        "LRT01-CONFLICTING-AUTHORIZATION",
        AuditInput(historical_states=states, lineage_edges=(conflicting,)),
        rule_versions=("M0-1.0", "M0-LRT01-XTYPE-1.0"),
    )
    undeclared_result = run(
        "LRT01-UNDECLARED-AUTHORIZATION",
        AuditInput(
            historical_states=states,
            lineage_edges=(replace(
                cross_edge,
                compatibility_authorizations=(
                    lineage_authorization(
                        "AUTH-UNDECLARED", "STATE_CONTENT", "EVENT_RECORD"
                    ),
                ),
            ),),
        ),
        rule_versions=("M0-1.0",),
    )

    assert "UNKNOWN" in unsupported_result.violations
    assert "UNKNOWN" in conflicting_result.violations
    assert "UNKNOWN" in undeclared_result.violations
    assert unsupported_result.verdict == "FAIL"
    assert conflicting_result.verdict == "FAIL"
    assert undeclared_result.verdict == "FAIL"


def test_r01_two_independent_evidence_records():
    r = run(
        "R01",
        AuditInput(
            evidence=(
                evidence(
                    "E1",
                    ("OBS-1",),
                    IndependenceStatus.INDEPENDENT,
                ),
                evidence(
                    "E2",
                    ("OBS-1",),
                    IndependenceStatus.INDEPENDENT,
                ),
            )
        ),
    )

    assert "EVIDENCE_INFLATION" in r.violations


def test_r02_four_state_chain():
    r = run(
        "R02",
        AuditInput(
            historical_states=(
                state("T1"),
                state("T2"),
                state("T3"),
                state("T4"),
            ),
            lineage_edges=(
                edge("T1", "T2"),
                edge("T2", "T3"),
                edge("T3", "T4"),
            ),
        ),
    )

    assert "TEMPORALLY_UNRESOLVED" not in r.violations


def test_r03_four_state_disconnected():
    r = run(
        "R03",
        AuditInput(
            historical_states=(
                state("T1"),
                state("T2"),
                state("T3"),
                state("T4"),
            ),
            lineage_edges=(
                edge("T1", "T2"),
                edge("T3", "T4"),
            ),
        ),
    )

    assert "TEMPORALLY_UNRESOLVED" in r.violations
def test_f01_valid_claim():
    from core.schema import Claim, EpistemicStatus, SchemaVersion, Timestamp

    claim = Claim(
        claim_id="CLAIM-F01",
        schema_version=SchemaVersion("M0-1.0"),
        created_at=Timestamp("M0-27"),
        origin_reference=ref("ORIGIN-F01"),
        status=EpistemicStatus.UNKNOWN,
    )

    r = run("F01", AuditInput(claims=(claim,)))
    assert "IDENTITY_CONFLICT" not in r.violations


def test_f06_explicit_lineage_edge():
    r = run("F06", AuditInput(
        lineage_edges=(edge("STATE-A", "STATE-B"),),
    ))
    assert "LINEAGE_INADMISSIBLE" not in r.violations


def test_f08_retrieval_with_declared_transformation():
    from core.schema import RetrievalEvent

    event = RetrievalEvent(
        retrieval_id="RETRIEVAL-F08",
        source_reference=ref("SOURCE-F08"),
        retrieved_reference=ref("RETRIEVED-F08"),
        retrieval_timestamp=TS,
        transformation_reference=ref("TRANSFORM-F08"),
        fidelity_status="FAITHFUL",
        provenance=prov("PROV-F08"),
    )

    r = run("F08", AuditInput(retrieval_events=(event,)))
    assert "RETRIEVAL_DISCREPANCY" not in r.violations



def test_f08_retrieval_with_matching_observed_transformation():
    from core.schema import RetrievalEvent

    event = RetrievalEvent(
        retrieval_id="RETRIEVAL-F08-MATCHING",
        source_reference=ref("SOURCE-F08-MATCHING"),
        retrieved_reference=ref("RETRIEVED-F08-MATCHING"),
        retrieval_timestamp=TS,
        transformation_reference=ref("TRANSFORM-F08-MATCHING"),
        fidelity_status="FAITHFUL",
        provenance=prov("PROV-F08-MATCHING"),
        observed_transformation_reference=ref("TRANSFORM-F08-MATCHING"),
    )

    r = run("F08", AuditInput(retrieval_events=(event,)))
    assert "RETRIEVAL_DISCREPANCY" not in r.violations
    assert "UNDECLARED_TRANSFORMATION" not in r.violations


def test_f09_retrieval_with_hidden_transformation():
    from core.schema import RetrievalEvent

    event = RetrievalEvent(
        retrieval_id="RETRIEVAL-F09-HIDDEN",
        source_reference=ref("SOURCE-F09-HIDDEN"),
        retrieved_reference=ref("RETRIEVED-F09-HIDDEN"),
        retrieval_timestamp=TS,
        transformation_reference=None,
        fidelity_status="FAITHFUL",
        provenance=prov("PROV-F09-HIDDEN"),
        observed_transformation_reference=ref("TRANSFORM-F09-HIDDEN"),
    )

    r = run("F09", AuditInput(retrieval_events=(event,)))
    assert "UNDECLARED_TRANSFORMATION" in r.violations


def test_f09_retrieval_with_transformation_discrepancy():
    from core.schema import RetrievalEvent

    event = RetrievalEvent(
        retrieval_id="RETRIEVAL-F09-DISCREPANCY",
        source_reference=ref("SOURCE-F09-DISCREPANCY"),
        retrieved_reference=ref("RETRIEVED-F09-DISCREPANCY"),
        retrieval_timestamp=TS,
        transformation_reference=ref("TRANSFORM-F09-DECLARED"),
        fidelity_status="FAITHFUL",
        provenance=prov("PROV-F09-DISCREPANCY"),
        observed_transformation_reference=ref("TRANSFORM-F09-OBSERVED"),
    )

    r = run("F09", AuditInput(retrieval_events=(event,)))
    assert "RETRIEVAL_DISCREPANCY" in r.violations

def test_f10_assessment_with_declared_admissible_evidence():
    from core.schema import Assessment

    ev = evidence(
        "E-F10",
        ("OBS-F10",),
        IndependenceStatus.INDEPENDENT,
    )

    assessment = Assessment(
        assessment_id="ASSESS-F10",
        assessment_version="1",
        rule_version="M0-1.0",
        admissible_evidence_refs=(ref("E-F10"),),
        condition_evaluation="SUPPORTED",
        assessment_basis="Declared admissible evidence",
        scope="F10 positive fixture",
    )

    r = run(
        "F10",
        AuditInput(
            evidence=(ev,),
            assessments=(assessment,),
        ),
    )

    assert "EVIDENCE_INADMISSIBLE" not in r.violations
def test_f02_missing_claim_id():
    from core.schema import Claim, EpistemicStatus, SchemaVersion, Timestamp

    try:
        Claim(
            claim_id="",
            schema_version=SchemaVersion("M0-1.0"),
            created_at=Timestamp("M0-30"),
            origin_reference=ref("ORIGIN-F02"),
            status=EpistemicStatus.UNKNOWN,
        )
    except ValueError:
        return

    raise AssertionError("Missing claim ID was accepted")


def test_f03_duplicate_claim_id():
    from core.schema import Claim, EpistemicStatus, SchemaVersion, Timestamp

    claim_a = Claim(
        claim_id="CLAIM-F03",
        schema_version=SchemaVersion("M0-1.0"),
        created_at=Timestamp("M0-30"),
        origin_reference=ref("ORIGIN-F03-A"),
        status=EpistemicStatus.UNKNOWN,
    )

    claim_b = Claim(
        claim_id="CLAIM-F03",
        schema_version=SchemaVersion("M0-1.0"),
        created_at=Timestamp("M0-30"),
        origin_reference=ref("ORIGIN-F03-B"),
        status=EpistemicStatus.UNKNOWN,
    )

    r = run("F03", AuditInput(claims=(claim_a, claim_b)))

    assert "IDENTITY_CONFLICT" in r.violations


def test_f07_similarity_only_lineage_is_inadmissible():
    r = run("F07", AuditInput(
        lineage_edges=(edge("STATE-A", "STATE-B"),),
    ))

    assert "LINEAGE_INADMISSIBLE" not in r.violations

    # The current model has no similarity relation type.
    # Therefore this regression verifies that a structurally explicit
    # lineage edge is not itself treated as a similarity-only edge.


def test_f12_repeated_observation_causes_evidence_inflation():
    ev_a = evidence(
        "E-F12-A",
        ("OBS-F12",),
        IndependenceStatus.INDEPENDENT,
    )

    ev_b = evidence(
        "E-F12-B",
        ("OBS-F12",),
        IndependenceStatus.INDEPENDENT,
    )

    r = run(
        "F12",
        AuditInput(evidence=(ev_a, ev_b)),
    )

    assert "EVIDENCE_INFLATION" in r.violations
    assert r.violations.count("EVIDENCE_INFLATION") == 1


def test_f14_two_states_without_temporal_relation():
    state_a = state("S-F14-A")
    state_b = state("S-F14-B")

    r = run(
        "F14",
        AuditInput(
            historical_states=(state_a, state_b),
        ),
    )

    assert "TEMPORALLY_UNRESOLVED" in r.violations


def test_f16_missing_provenance_is_detected():
    from core.schema import RetrievalEvent

    missing_state = HistoricalState(
        state_id="STATE-F16-MISSING",
        claim_id="CLAIM-M0-14J",
        state_version="F16",
        observed_at=TS,
        state_context=TemporalContext(snapshot_id="F16"),
        content_reference=ref("CONTENT-F16"),
        provenance=None,
    )

    missing_edge = LineageEdge(
        lineage_id="EDGE-F16-MISSING",
        from_reference=ref("FROM-F16"),
        to_reference=ref("TO-F16"),
        relation_type="EXPLICIT_RELATION",
        derivation_reference=ref("DER-F16"),
        admissibility_status="ADMISSIBLE",
        provenance=None,
    )

    missing_retrieval = RetrievalEvent(
        retrieval_id="RETRIEVAL-F16-MISSING",
        source_reference=ref("SOURCE-F16"),
        retrieved_reference=ref("RETRIEVED-F16"),
        retrieval_timestamp=TS,
        transformation_reference=None,
        fidelity_status="FAITHFUL",
        provenance=None,
    )

    r = run(
        "F16",
        AuditInput(
            historical_states=(missing_state,),
            lineage_edges=(missing_edge,),
            retrieval_events=(missing_retrieval,),
        ),
    )

    assert r.violations.count("MISSING_PROVENANCE") == 3

def f07_candidate(
    candidate_id,
    basis,
    rule_version="M0-F07-1.0",
 ):
    return LineageCandidate(
        candidate_id=candidate_id,
        from_reference=ref(f"FROM-{candidate_id}"),
        to_reference=ref(f"TO-{candidate_id}"),
        proposed_relation_type="LINEAGE_CONTINUATION",
        inference_basis=basis,
        derivation_reference=ref(f"DER-{candidate_id}"),
        provenance=prov(f"PROV-{candidate_id}"),
        lineage_rule_version=rule_version,
    )



def test_f07_similarity_candidate_is_inadmissible():
    candidate = f07_candidate("F07-SIMILARITY", "SIMILARITY")

    r = run(
        "F07-SIMILARITY-CANDIDATE",
        AuditInput(lineage_candidates=(candidate,)),
        rule_versions=("M0-1.0", "M0-F07-1.0",),
    )

    assert r.verdict == "FAIL"
    assert "LINEAGE_INADMISSIBLE" in r.violations



def test_f07_explicit_relation_candidate_has_no_f07_violation():
    candidate = f07_candidate("F07-EXPLICIT", "EXPLICIT_RELATION")

    r = run(
        "F07-EXPLICIT-CANDIDATE",
        AuditInput(lineage_candidates=(candidate,)),
        rule_versions=("M0-1.0", "M0-F07-1.0",),
    )

    assert r.verdict == "PASS"
    assert "LINEAGE_INADMISSIBLE" not in r.violations
    assert "UNKNOWN" not in r.violations



def test_f07_unsupported_rule_is_unknown():
    candidate = f07_candidate(
        "F07-UNSUPPORTED",
        "EXPLICIT_RELATION",
        rule_version="M0-F07-9.9",
    )

    r = run(
        "F07-UNSUPPORTED-RULE",
        AuditInput(lineage_candidates=(candidate,)),
        rule_versions=("M0-1.0", "M0-F07-9.9",),
    )

    assert r.verdict == "FAIL"
    assert "UNKNOWN" in r.violations



def test_f07_undeclared_rule_is_unknown():
    candidate = f07_candidate("F07-UNDECLARED", "EXPLICIT_RELATION")

    r = run(
        "F07-UNDECLARED-RULE",
        AuditInput(lineage_candidates=(candidate,)),
        rule_versions=("M0-1.0",),
    )

    assert r.verdict == "FAIL"
    assert "UNKNOWN" in r.violations

def f05_candidate(
    canonical_id,
    replacement_id,
    canonical_value,
    replacement_value,
    rule_version="M0-F05-1.0",
):
    return HistoricalMutationCandidate(
        canonical_artifact=ref(canonical_id),
        canonical_integrity=IntegrityRepresentation(
            method="SHA256",
            value=canonical_value,
        ),
        attempted_replacement=ref(replacement_id),
        attempted_replacement_integrity=IntegrityRepresentation(
            method="SHA256",
            value=replacement_value,
        ),
        historical_scope=ref("HISTORY-F05"),
        mutation_rule_version=rule_version,
    )


def test_f05_historical_overwrite_is_detected():
    candidate = f05_candidate(
        "CANONICAL-F05",
        "REPLACEMENT-F05",
        "HASH-CANONICAL",
        "HASH-REPLACEMENT",
    )

    r = run(
        "F05",
        AuditInput(
            historical_mutation_candidates=(candidate,),
        ),
        rule_versions=("M0-1.0", "M0-F05-1.0"),
    )

    assert r.verdict == "FAIL"
    assert "HISTORY_MUTATION" in r.violations


def test_f05_same_integrity_is_not_mutation():
    candidate = f05_candidate(
        "CANONICAL-F05-SAME",
        "REPLACEMENT-F05-SAME",
        "HASH-SAME",
        "HASH-SAME",
    )

    r = run(
        "F05-SAME",
        AuditInput(
            historical_mutation_candidates=(candidate,),
        ),
        rule_versions=("M0-1.0", "M0-F05-1.0"),
    )

    assert r.verdict == "PASS"
    assert "HISTORY_MUTATION" not in r.violations


def test_f05_reference_difference_does_not_imply_mutation():
    candidate = f05_candidate(
        "CANONICAL-F05-REF",
        "DIFFERENT-REFERENCE-F05",
        "HASH-SAME-REFERENCE-CONTENT",
        "HASH-SAME-REFERENCE-CONTENT",
    )

    r = run(
        "F05-REFERENCE",
        AuditInput(
            historical_mutation_candidates=(candidate,),
        ),
        rule_versions=("M0-1.0", "M0-F05-1.0"),
    )

    assert r.verdict == "PASS"
    assert "HISTORY_MUTATION" not in r.violations


def test_f05_missing_integrity_is_unknown():
    candidate = HistoricalMutationCandidate(
        canonical_artifact=ref("CANONICAL-F05-MISSING"),
        canonical_integrity=None,
        attempted_replacement=ref("REPLACEMENT-F05-MISSING"),
        attempted_replacement_integrity=None,
        historical_scope=ref("HISTORY-F05-MISSING"),
        mutation_rule_version="M0-F05-1.0",
    )

    r = run(
        "F05-MISSING-INTEGRITY",
        AuditInput(
            historical_mutation_candidates=(candidate,),
        ),
        rule_versions=("M0-1.0", "M0-F05-1.0"),
    )

    assert r.verdict == "FAIL"
    assert "UNKNOWN" in r.violations
    assert "HISTORY_MUTATION" not in r.violations


def test_f05_unsupported_rule_is_unknown():
    candidate = f05_candidate(
        "CANONICAL-F05-RULE",
        "REPLACEMENT-F05-RULE",
        "HASH-A",
        "HASH-B",
        rule_version="M0-F05-UNSUPPORTED",
    )

    r = run(
        "F05-UNSUPPORTED-RULE",
        AuditInput(
            historical_mutation_candidates=(candidate,),
        ),
        rule_versions=("M0-1.0", "M0-F05-UNSUPPORTED"),
    )

    assert r.verdict == "FAIL"
    assert "UNKNOWN" in r.violations
    assert "HISTORY_MUTATION" not in r.violations


def test_f05_undeclared_rule_is_unknown():
    candidate = f05_candidate(
        "CANONICAL-F05-UNDECLARED",
        "REPLACEMENT-F05-UNDECLARED",
        "HASH-A",
        "HASH-B",
    )

    r = run(
        "F05-UNDECLARED-RULE",
        AuditInput(
            historical_mutation_candidates=(candidate,),
        ),
        rule_versions=("M0-1.0",),
    )

    assert r.verdict == "FAIL"
    assert "UNKNOWN" in r.violations
    assert "HISTORY_MUTATION" not in r.violations


# F11: audit results are a distinct artifact kind, never assessment evidence.


def _run_f11(name, artifacts):
    return run(
        name,
        artifacts,
        rule_versions=("M0-1.0", "M0-F11-1.0"),
    )
def _f11_assessment(assessment_id, references):
    from core.schema import Assessment

    return Assessment(
        assessment_id=assessment_id,
        assessment_version="1",
        rule_version="M0-F11-1.0",
        admissible_evidence_refs=tuple(references),
        condition_evaluation="SUPPORTED",
        assessment_basis="F11 regression fixture",
        scope="F11",
    )


def _f11_audit_result(audit_id, verdict="PASS", examined=()):
    from core.schema import AuditResult

    return AuditResult(
        audit_id=audit_id,
        inspector_id="F11-TEST-INSPECTOR",
        inspector_version="1",
        execution_timestamp=TS,
        configuration_id="F11-TEST",
        rule_versions=("M0-F11-1.0",),
        artifacts_examined=tuple(examined),
        violations=() if verdict == "PASS" else ("TEST_FIXTURE_VIOLATION",),
        verdict=verdict,
        verdict_basis="Fixture only; not a truth claim",
    )


def test_f11_a_real_evidence_reference_remains_admissible():
    ev = evidence("E-F11-A", ("OBS-F11-A",), IndependenceStatus.INDEPENDENT)
    assessment = _f11_assessment("ASSESS-F11-A", (ref("E-F11-A"),))

    r = _run_f11("F11-A", AuditInput(evidence=(ev,), assessments=(assessment,)))

    assert r.verdict == "PASS"
    assert "COMPOSITION_FORBIDDEN" not in r.violations
    assert "EVIDENCE_INADMISSIBLE" not in r.violations


def test_f11_b_audit_result_id_in_evidence_position_is_forbidden():
    result = _f11_audit_result("AUDIT-F11-B", "PASS")
    assessment = _f11_assessment("ASSESS-F11-B", (ref("AUDIT-F11-B"),))

    r = _run_f11(
        "F11-B",
        AuditInput(assessments=(assessment,), prior_audit_results=(result,)),
    )

    assert r.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in r.violations


def test_f11_c_caller_label_cannot_retype_audit_result_as_evidence():
    result = _f11_audit_result("AUDIT-F11-C", "PASS")
    misleading_reference = Reference("AUDIT-F11-C", "EVIDENCE")
    assessment = _f11_assessment("ASSESS-F11-C", (misleading_reference,))

    r = _run_f11(
        "F11-C",
        AuditInput(assessments=(assessment,), prior_audit_results=(result,)),
    )

    assert "COMPOSITION_FORBIDDEN" in r.violations
    assert r.verdict == "FAIL"


def test_f11_d_valid_evidence_does_not_hide_a_verdict_reference():
    ev = evidence("E-F11-D", ("OBS-F11-D",), IndependenceStatus.INDEPENDENT)
    result = _f11_audit_result("AUDIT-F11-D", "PASS")
    assessment = _f11_assessment(
        "ASSESS-F11-D",
        (ref("E-F11-D"), ref("AUDIT-F11-D")),
    )

    r = _run_f11(
        "F11-D",
        AuditInput(
            evidence=(ev,),
            assessments=(assessment,),
            prior_audit_results=(result,),
        ),
    )

    assert "COMPOSITION_FORBIDDEN" in r.violations
    assert "EVIDENCE_INADMISSIBLE" not in r.violations
    assert r.verdict == "FAIL"


def test_f11_e_unknown_evidence_reference_cannot_pass():
    assessment = _f11_assessment("ASSESS-F11-E", (ref("UNKNOWN-F11-E"),))

    r = _run_f11("F11-E", AuditInput(assessments=(assessment,)))

    assert "EVIDENCE_INADMISSIBLE" in r.violations
    assert r.verdict != "PASS"


def test_f11_f_separately_recorded_audit_result_is_not_itself_a_violation():
    result = _f11_audit_result("AUDIT-F11-F", "PASS")

    r = _run_f11("F11-F", AuditInput(prior_audit_results=(result,)))

    assert "COMPOSITION_FORBIDDEN" not in r.violations
    # Recording a result is permitted, but the result alone cannot make a
    # fresh audit PASS when no primary artifacts were supplied.
    assert r.verdict == "UNKNOWN"
    assert "prior audit results alone do not support a new verdict" in r.verdict_basis
    assert any(
        item.reference_id == "AUDIT-F11-F"
        and item.reference_type == "AUDIT_RESULT"
        for item in r.artifacts_examined
    )


def test_f11_g_a_verdict_does_not_inflate_its_underlying_observation():
    ev = evidence("E-F11-G", ("OBS-F11-G",), IndependenceStatus.INDEPENDENT)
    result = _f11_audit_result(
        "AUDIT-F11-G",
        "PASS",
        examined=(Reference("OBS-F11-G", "OBSERVATION"),),
    )

    r = _run_f11(
        "F11-G",
        AuditInput(evidence=(ev,), prior_audit_results=(result,)),
    )

    assert "EVIDENCE_INFLATION" not in r.violations
    assert r.verdict == "PASS"
    # The nested result's examined observation is not re-expanded as a second
    # observation in this audit's own examined-artifact list.
    assert sum(
        item.reference_id == "OBS-F11-G"
        for item in r.artifacts_examined
    ) == 1


def test_f11_requires_its_rule_version_to_emit_composition_forbidden():
    result = _f11_audit_result("AUDIT-F11-VERSION", "PASS")
    assessment = _f11_assessment(
        "ASSESS-F11-VERSION",
        (ref("AUDIT-F11-VERSION"),),
    )

    # Use the legacy declared rule set intentionally: F11's specialized
    # classification must not activate without its declared rule version.
    r = run(
        "F11-VERSION-NOT-DECLARED",
        AuditInput(assessments=(assessment,), prior_audit_results=(result,)),
        rule_versions=("M0-1.0",),
    )

    assert "COMPOSITION_FORBIDDEN" not in r.violations
    assert "EVIDENCE_INADMISSIBLE" in r.violations
    assert r.verdict == "FAIL"


def test_f11_cross_kind_id_collision_remains_unknown():
    ev = evidence(
        "SHARED-F11-ID",
        ("OBS-F11-COLLISION",),
        IndependenceStatus.INDEPENDENT,
    )
    result = _f11_audit_result("SHARED-F11-ID", "PASS")
    assessment = _f11_assessment(
        "ASSESS-F11-COLLISION",
        (ref("SHARED-F11-ID"),),
    )

    r = _run_f11(
        "F11-CROSS-KIND-COLLISION",
        AuditInput(
            evidence=(ev,),
            assessments=(assessment,),
            prior_audit_results=(result,),
        ),
    )

    assert "UNKNOWN" in r.violations
    assert "COMPOSITION_FORBIDDEN" not in r.violations
    assert r.verdict == "FAIL"


def test_f11_duplicate_audit_result_ids_remain_unknown():
    first = _f11_audit_result("DUPLICATE-AUDIT-ID", "PASS")
    second = _f11_audit_result("DUPLICATE-AUDIT-ID", "FAIL")
    assessment = _f11_assessment(
        "ASSESS-F11-DUPLICATE-AUDIT-ID",
        (ref("DUPLICATE-AUDIT-ID"),),
    )

    r = _run_f11(
        "F11-DUPLICATE-AUDIT-ID",
        AuditInput(
            assessments=(assessment,),
            prior_audit_results=(first, second),
        ),
    )

    assert "UNKNOWN" in r.violations
    assert "COMPOSITION_FORBIDDEN" not in r.violations
    assert r.verdict == "FAIL"


def test_f11_h_verdict_polarity_does_not_change_artifact_type_classification():
    outcomes = []
    for verdict in ("PASS", "FAIL"):
        result = _f11_audit_result(f"AUDIT-F11-H-{verdict}", verdict)
        assessment = _f11_assessment(
            f"ASSESS-F11-H-{verdict}",
            (ref(f"AUDIT-F11-H-{verdict}"),),
        )
        r = _run_f11(
            f"F11-H-{verdict}",
            AuditInput(
                assessments=(assessment,),
                prior_audit_results=(result,),
            ),
        )
        outcomes.append(r.violations)
        assert "COMPOSITION_FORBIDDEN" in r.violations

    assert outcomes[0] == outcomes[1]


def test_f11_false_positive_control_allows_evidence_ids_containing_keywords():
    evidence_id = "PASS-AUDIT-VERDICT-EVIDENCE"
    ev = evidence(
        evidence_id,
        ("OBS-F11-FALSE-POSITIVE",),
        IndependenceStatus.INDEPENDENT,
    )
    assessment = _f11_assessment(
        "ASSESS-F11-FALSE-POSITIVE",
        (ref(evidence_id),),
    )

    r = _run_f11(
        "F11-FALSE-POSITIVE",
        AuditInput(evidence=(ev,), assessments=(assessment,)),
    )

    assert "COMPOSITION_FORBIDDEN" not in r.violations
    assert "EVIDENCE_INADMISSIBLE" not in r.violations
    assert r.verdict == "PASS"


def test_f11_ambiguous_duplicate_evidence_ids_remain_unknown():
    first = evidence("E-F11-AMBIGUOUS", ("OBS-F11-AMBIGUOUS-1",), IndependenceStatus.INDEPENDENT)
    second = evidence("E-F11-AMBIGUOUS", ("OBS-F11-AMBIGUOUS-2",), IndependenceStatus.INDEPENDENT)
    assessment = _f11_assessment(
        "ASSESS-F11-AMBIGUOUS",
        (ref("E-F11-AMBIGUOUS"),),
    )

    r = _run_f11(
        "F11-AMBIGUOUS",
        AuditInput(evidence=(first, second), assessments=(assessment,)),
    )

    assert "UNKNOWN" in r.violations
    assert r.verdict == "FAIL"
# F15: cross-IRG composition firewall regression coverage.

def _f15_fixture(conclusion):
    from core.schema import (
        AuditResult, CompositionConclusion, CompositionParticipantResult, CompositionRequest,
    )

    results = tuple(
        AuditResult(
            audit_id=f"F15-AUDIT-{i}",
            inspector_id="F15-TEST-INSPECTOR",
            inspector_version="1",
            execution_timestamp=TS,
            configuration_id="F15-TEST",
            rule_versions=("M0-F15-1.0",),
            artifacts_examined=(),
            violations=(),
            verdict="PASS",
            verdict_basis="Local structural fixture only",
        )
        for i in range(1, 6)
    )
    request = CompositionRequest(
        composition_id="F15-COMPOSITION",
        participant_results=tuple(
            CompositionParticipantResult(
                f"IRG-{i:02d}",
                f"F15-AUDIT-{i}",
                declared_scope=f"F15-TEST-SCOPE-IRG-{i:02d}",
            )
            for i in range(1, 6)
        ),
        composition_rule_id=(
            "M0-F15-LOCAL-SUMMARY"
            if conclusion == CompositionConclusion.LOCAL_RESULT_SUMMARY
            else "M0-F15"
        ),
        composition_rule_version=(
            "1.0"
            if conclusion == CompositionConclusion.LOCAL_RESULT_SUMMARY
            else "M0-F15-1.0"
        ),
        temporal_context="F15-TEST-SNAPSHOT",
        requested_conclusion=conclusion,
        limitations="Local structure does not establish truth or ontology",
        scope="F15 regression fixture",
    )
    return results, request


def test_f15_forbids_global_truth_from_five_local_results():
    from core.schema import CompositionConclusion

    results, request = _f15_fixture(CompositionConclusion.GLOBAL_TRUTH)
    r = run(
        "F15-GLOBAL-TRUTH",
        AuditInput(prior_audit_results=results, composition_requests=(request,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    assert r.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in r.violations


def test_f15_allows_bounded_summary():
    from core.schema import CompositionConclusion

    results, request = _f15_fixture(CompositionConclusion.LOCAL_RESULT_SUMMARY)
    r = run(
        "F15-BOUNDED-SUMMARY",
        AuditInput(prior_audit_results=results, composition_requests=(request,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    assert r.verdict == "PASS"
    assert "COMPOSITION_FORBIDDEN" not in r.violations
    assert len(r.composition_summaries) == 1
    summary = r.composition_summaries[0]
    assert summary.composition_id == "F15-COMPOSITION"
    assert summary.summary_rule_id == "M0-F15-LOCAL-SUMMARY"
    assert summary.summary_rule_version == "1.0"
    assert len(summary.records) == 5
    assert summary.verdict_counts == (("PASS", 5),)
    assert all(record.declared_irg_id.startswith("IRG-") for record in summary.records)
    assert all(record.declared_scope.startswith("F15-TEST-SCOPE-") for record in summary.records)
    assert "scopes are caller-supplied" in summary.limitations
    assert "does not establish Claim truth" in summary.limitations


def test_f15_supplied_results_only_emits_subset_summary():
    from dataclasses import replace
    from core.schema import CompositionConclusion, CompositionInputScope

    results, request = _f15_fixture(CompositionConclusion.LOCAL_RESULT_SUMMARY)
    request = replace(
        request,
        participant_results=request.participant_results[:2],
        requested_input_scope=CompositionInputScope.SUPPLIED_RESULTS_ONLY,
    )
    r = run(
        "F15-SUPPLIED-RESULTS-SUBSET",
        AuditInput(prior_audit_results=results, composition_requests=(request,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    assert r.verdict == "PASS"
    assert len(r.composition_summaries) == 1
    assert len(r.composition_summaries[0].records) == 2
    assert r.composition_summaries[0].verdict_counts == (("PASS", 2),)


def test_f15_legacy_bounded_summary_label_is_not_accepted():
    from dataclasses import replace
    from core.schema import CompositionConclusion

    results, request = _f15_fixture(CompositionConclusion.LOCAL_RESULT_SUMMARY)
    request = replace(request, requested_conclusion=CompositionConclusion.BOUNDED_SUMMARY)
    r = run(
        "F15-LEGACY-BOUNDED-SUMMARY",
        AuditInput(prior_audit_results=results, composition_requests=(request,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    assert r.verdict == "FAIL"
    assert "UNKNOWN" in r.violations
    assert r.composition_summaries == ()


def test_f15_missing_participant_result_is_unknown():
    from dataclasses import replace
    from core.schema import CompositionConclusion

    results, request = _f15_fixture(CompositionConclusion.LOCAL_RESULT_SUMMARY)
    request = replace(request, participant_results=request.participant_results[:-1])
    r = run(
        "F15-MISSING-PARTICIPANT",
        AuditInput(prior_audit_results=results, composition_requests=(request,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    assert r.verdict == "FAIL"
    assert "UNKNOWN" in r.violations


def test_f15_rejects_noncanonical_irgs_for_five_result_summary():
    from dataclasses import replace
    from core.schema import CompositionConclusion, CompositionParticipantResult

    results, request = _f15_fixture(CompositionConclusion.LOCAL_RESULT_SUMMARY)
    request = replace(
        request,
        participant_results=tuple(
            CompositionParticipantResult(f"IRG-X{i}", f"F15-AUDIT-{i}")
            for i in range(1, 6)
        ),
    )
    r = run(
        "F15-NONCANONICAL-IRGS",
        AuditInput(prior_audit_results=results, composition_requests=(request,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    assert "UNKNOWN" in r.violations
    assert r.verdict != "PASS"


def test_f15_rejects_unrecognized_composition_rule_id():
    from dataclasses import replace
    from core.schema import CompositionConclusion

    results, request = _f15_fixture(CompositionConclusion.LOCAL_RESULT_SUMMARY)
    request = replace(request, composition_rule_id="CALLER-DEFINED-ALLOW-ALL")
    r = run(
        "F15-UNRECOGNIZED-RULE-ID",
        AuditInput(prior_audit_results=results, composition_requests=(request,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    assert "UNKNOWN" in r.violations
    assert r.verdict != "PASS"


def test_f15_rejects_composition_id_collision_with_input_audit_id():
    from dataclasses import replace
    from core.schema import CompositionConclusion

    results, request = _f15_fixture(CompositionConclusion.LOCAL_RESULT_SUMMARY)
    request = replace(request, composition_id=results[0].audit_id)
    r = run(
        "F15-SELF-REFERENCE-COLLISION",
        AuditInput(prior_audit_results=results, composition_requests=(request,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    assert "UNKNOWN" in r.violations
    assert r.verdict != "PASS"


def test_f15_claim_truth_cannot_be_downgraded_by_caller_rule_tampering():
    from dataclasses import replace
    from core.schema import CompositionConclusion

    results, request = _f15_fixture(CompositionConclusion.CLAIM_TRUTH)
    request = replace(
        request,
        composition_rule_id="CALLER-DEFINED-ALLOW-ALL",
        composition_rule_version="9.9",
    )
    r = run(
        "F15-CLAIM-TRUTH-RULE-TAMPERING",
        AuditInput(prior_audit_results=results, composition_requests=(request,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )

    assert r.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in r.violations
    assert "UNKNOWN" not in r.violations


def test_f15_forbids_claim_truth_from_five_local_results():
    from core.schema import CompositionConclusion

    results, request = _f15_fixture(CompositionConclusion.CLAIM_TRUTH)
    r = run(
        "F15-CLAIM-TRUTH",
        AuditInput(prior_audit_results=results, composition_requests=(request,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )

    assert r.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in r.violations
    assert "UNKNOWN" not in r.violations


def test_f15_claim_truth_requires_declared_firewall_version():
    from core.schema import CompositionConclusion

    results, request = _f15_fixture(CompositionConclusion.CLAIM_TRUTH)
    r = run(
        "F15-CLAIM-TRUTH-F15-NOT-DECLARED",
        AuditInput(prior_audit_results=results, composition_requests=(request,)),
        rule_versions=("M0-1.0",),
    )

    assert r.verdict == "FAIL"
    assert "UNKNOWN" in r.violations
    assert "COMPOSITION_FORBIDDEN" not in r.violations


def test_f15_duplicate_participant_audit_id_is_unknown():
    from dataclasses import replace
    from core.schema import CompositionConclusion

    results, request = _f15_fixture(CompositionConclusion.LOCAL_RESULT_SUMMARY)
    participants = list(request.participant_results)
    participants[-1] = replace(participants[-1], audit_id=participants[0].audit_id)
    request = replace(request, participant_results=tuple(participants))
    r = run(
        "F15-DUPLICATE-PARTICIPANT-AUDIT-ID",
        AuditInput(prior_audit_results=results, composition_requests=(request,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )

    assert r.verdict == "FAIL"
    assert "UNKNOWN" in r.violations
    assert "COMPOSITION_FORBIDDEN" not in r.violations


def test_f15_duplicate_participant_irg_label_is_unknown():
    from dataclasses import replace
    from core.schema import CompositionConclusion, CompositionParticipantResult

    results, request = _f15_fixture(CompositionConclusion.LOCAL_RESULT_SUMMARY)
    participants = list(request.participant_results)
    participants[-1] = CompositionParticipantResult(
        irg_id=participants[0].irg_id,
        audit_id=participants[-1].audit_id,
    )
    request = replace(request, participant_results=tuple(participants))
    r = run(
        "F15-DUPLICATE-PARTICIPANT-IRG-LABEL",
        AuditInput(prior_audit_results=results, composition_requests=(request,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )

    assert r.verdict == "FAIL"
    assert "UNKNOWN" in r.violations
    assert "COMPOSITION_FORBIDDEN" not in r.violations


def test_f15_composition_summary_is_not_admissible_assessment_evidence():
    from core.schema import Assessment, CompositionConclusion, Reference

    source_results, request = _f15_fixture(CompositionConclusion.LOCAL_RESULT_SUMMARY)
    summary_result = run(
        "F15-SUMMARY-SOURCE",
        AuditInput(prior_audit_results=source_results, composition_requests=(request,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    assessment = Assessment(
        assessment_id="ASSESSMENT-USES-COMPOSITION-SUMMARY",
        assessment_version="1",
        rule_version="ASSESSMENT-RULE-1",
        admissible_evidence_refs=(Reference("F15-COMPOSITION", "COMPOSITION_SUMMARY"),),
        condition_evaluation="Treat the summary as evidence",
        assessment_basis="Adversarial F15 regression",
        scope="F15-I6",
    )
    r = run(
        "F15-SUMMARY-AS-EVIDENCE",
        AuditInput(assessments=(assessment,), prior_audit_results=(summary_result,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    assert r.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in r.violations


def test_f15_summary_cannot_be_wrapped_as_observation_evidence():
    from core.schema import Assessment, CompositionConclusion, IndependenceStatus, Reference

    source_results, request = _f15_fixture(CompositionConclusion.LOCAL_RESULT_SUMMARY)
    summary_result = run(
        "F15-SUMMARY-SOURCE-WRAPPED",
        AuditInput(prior_audit_results=source_results, composition_requests=(request,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    wrapped = Evidence(
        evidence_id="EVIDENCE-WRAPPED-SUMMARY",
        observation_refs=(Reference("F15-COMPOSITION", "COMPOSITION_SUMMARY"),),
        evidence_level="OBSERVATION",
        independence_status=IndependenceStatus.DEPENDENT,
        derivation_reference=Reference("DER-WRAPPED-SUMMARY", "DERIVATION"),
        scope="Adversarial F15 regression",
    )
    assessment = Assessment(
        assessment_id="ASSESSMENT-WRAPPED-SUMMARY",
        assessment_version="1",
        rule_version="ASSESSMENT-RULE-1",
        admissible_evidence_refs=(Reference(wrapped.evidence_id, "EVIDENCE"),),
        condition_evaluation="Treat a wrapper around the summary as evidence",
        assessment_basis="Adversarial F15 regression",
        scope="F15-I6",
    )
    r = run(
        "F15-WRAPPED-SUMMARY-AS-EVIDENCE",
        AuditInput(
            assessments=(assessment,),
            evidence=(wrapped,),
            prior_audit_results=(summary_result,),
        ),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    assert r.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in r.violations


def test_f15_audit_verdict_id_is_not_admissible_assessment_evidence():
    from core.schema import Assessment, CompositionConclusion, Reference

    source_results, request = _f15_fixture(CompositionConclusion.LOCAL_RESULT_SUMMARY)
    summary_result = run(
        "F15-AUDIT-VERDICT-SOURCE",
        AuditInput(prior_audit_results=source_results, composition_requests=(request,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    assessment = Assessment(
        assessment_id="ASSESSMENT-USES-AUDIT-VERDICT",
        assessment_version="1",
        rule_version="ASSESSMENT-RULE-1",
        admissible_evidence_refs=(Reference(summary_result.audit_id, "AUDIT_RESULT"),),
        condition_evaluation="Treat an audit verdict as evidence",
        assessment_basis="Adversarial F15 regression",
        scope="F15-I6",
    )
    r = run(
        "F15-AUDIT-VERDICT-AS-EVIDENCE",
        AuditInput(assessments=(assessment,), prior_audit_results=(summary_result,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    assert r.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in r.violations


def test_f15_composition_request_id_is_not_admissible_assessment_evidence():
    from core.schema import Assessment, CompositionConclusion, Reference

    source_results, request = _f15_fixture(CompositionConclusion.LOCAL_RESULT_SUMMARY)
    assessment = Assessment(
        assessment_id="ASSESSMENT-USES-COMPOSITION-REQUEST",
        assessment_version="1",
        rule_version="ASSESSMENT-RULE-1",
        admissible_evidence_refs=(Reference(request.composition_id, "COMPOSITION_REQUEST"),),
        condition_evaluation="Treat the composition request as evidence",
        assessment_basis="Adversarial F15 regression",
        scope="F15-I6",
    )
    r = run(
        "F15-COMPOSITION-REQUEST-AS-EVIDENCE",
        AuditInput(
            assessments=(assessment,),
            prior_audit_results=source_results,
            composition_requests=(request,),
        ),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    assert r.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in r.violations


def test_f15_mixed_local_verdicts_still_forbid_claim_truth():
    from dataclasses import replace
    from core.schema import CompositionConclusion

    results, request = _f15_fixture(CompositionConclusion.CLAIM_TRUTH)
    mixed_results = tuple(
        replace(result, verdict="FAIL" if index == 1 else result.verdict)
        for index, result in enumerate(results)
    )
    r = run(
        "F15-MIXED-VERDICTS-CLAIM-TRUTH",
        AuditInput(prior_audit_results=mixed_results, composition_requests=(request,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    assert r.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in r.violations
    assert "UNKNOWN" not in r.violations


def test_f15_summary_rule_version_is_exactly_gated():
    from dataclasses import replace
    from core.schema import CompositionConclusion

    results, request = _f15_fixture(CompositionConclusion.LOCAL_RESULT_SUMMARY)
    request = replace(request, composition_rule_version="2.0")
    r = run(
        "F15-SUMMARY-UNSUPPORTED-RULE-VERSION",
        AuditInput(prior_audit_results=results, composition_requests=(request,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    assert r.verdict == "FAIL"
    assert "UNKNOWN" in r.violations
    assert r.composition_summaries == ()


def test_f15_summary_cannot_be_smuggled_through_derivation_reference():
    from core.schema import Assessment, CompositionConclusion, IndependenceStatus, Reference

    source_results, request = _f15_fixture(CompositionConclusion.LOCAL_RESULT_SUMMARY)
    summary_result = run(
        "F15-DERIVATION-SUMMARY-SOURCE",
        AuditInput(prior_audit_results=source_results, composition_requests=(request,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    wrapped = Evidence(
        evidence_id="EVIDENCE-DERIVATION-WRAPPER",
        observation_refs=(Reference("UNRELATED-OBSERVATION-01", "OBSERVATION"),),
        evidence_level="OBSERVATION",
        independence_status=IndependenceStatus.DEPENDENT,
        derivation_reference=Reference("F15-COMPOSITION", "COMPOSITION_SUMMARY"),
        scope="Adversarial F15 derivation-reference smuggling test",
    )
    assessment = Assessment(
        assessment_id="ASSESSMENT-DERIVATION-WRAPPER",
        assessment_version="1",
        rule_version="ASSESSMENT-RULE-1",
        admissible_evidence_refs=(Reference(wrapped.evidence_id, "EVIDENCE"),),
        condition_evaluation="Treat a wrapper whose derivation points to the summary as evidence",
        assessment_basis="Adversarial F15 regression",
        scope="F15-I6",
    )
    r = run(
        "F15-DERIVATION-REFERENCE-SUMMARY-SMUGGLING",
        AuditInput(
            assessments=(assessment,),
            evidence=(wrapped,),
            prior_audit_results=(summary_result,),
        ),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    assert r.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in r.violations


def test_f15_assessment_rejects_forbidden_type_even_when_id_matches_evidence():
    from core.schema import Assessment, Reference

    real_evidence = evidence(
        "EVIDENCE-REAL-01",
        ("OBS-REAL-01",),
        IndependenceStatus.DEPENDENT,
    )
    assessment = Assessment(
        assessment_id="ASSESSMENT-TYPE-CONFUSION",
        assessment_version="1",
        rule_version="ASSESSMENT-RULE-1",
        admissible_evidence_refs=(
            Reference(real_evidence.evidence_id, "COMPOSITION_SUMMARY"),
        ),
        condition_evaluation="Attempt to relabel real evidence as a composition summary",
        assessment_basis="Adversarial F15 reference-type confusion test",
        scope="F15-I6",
    )
    r = run(
        "F15-ASSESSMENT-REFERENCE-TYPE-CONFUSION",
        AuditInput(assessments=(assessment,), evidence=(real_evidence,)),
        rule_versions=("M0-1.0", "M0-F15-1.0"),
    )
    assert r.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in r.violations


def test_adv_xirg_recomputed_hashes_do_not_authorize_history_or_composition():
    """Synthetic M0/F15 boundary regression; independent continuity stays unestablished."""
    import copy
    import hashlib
    import json

    from core.schema import (
        Assessment, CompositionConclusion, CompositionInputScope,
        CompositionParticipantResult, CompositionRequest,
    )

    def canonical(value):
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False).encode("utf-8")

    def seal(records):
        sealed = copy.deepcopy(records)
        previous = None
        for record in sealed:
            record.pop("sha256", None)
            record["previous_sha256"] = previous
            record["sha256"] = hashlib.sha256(canonical(record)).hexdigest()
            previous = record["sha256"]
        return sealed

    def ledger_bytes(records):
        return b"".join(canonical(record) + b"\n" for record in records)

    before = seal([
        {"record_id": "ROW-0", "observed_at": "2026-10-12T00:00:00Z",
         "payload": {"node_id": "NODE-A", "claim_id": "SYNTHETIC-CLAIM",
                     "value": "original synthetic observation"}},
        {"record_id": "ROW-1", "observed_at": "2026-10-12T00:01:00Z",
         "payload": {"node_id": "NODE-B", "claim_id": "SYNTHETIC-CLAIM",
                     "value": "synthetic successor",
                     "lineage_from": "NODE-A", "lineage_to": "NODE-B"}},
    ])
    before_bytes = ledger_bytes(before)
    preserved_before = memoryview(before_bytes).tobytes()
    before_hash = hashlib.sha256(preserved_before).hexdigest()
    after = copy.deepcopy(before)
    after[0]["payload"]["value"] = "rewritten synthetic observation"
    after[1]["payload"]["lineage_from"] = "MISSING-HISTORICAL-NODE"
    after = seal(after)
    after_hash = hashlib.sha256(ledger_bytes(after)).hexdigest()

    assert before_hash == "00a9c8f968a53e987e2c90b93eecf32186612d28bb12568bc608b59c13ef4e94"
    assert after_hash == "1de90b651db983a31b82529b19e86755bee8f8f23579eba25935f165be9be529"
    assert before_hash != after_hash
    assert ledger_bytes(before) == preserved_before
    for records in (before, after):
        previous = None
        for record in records:
            unhashed = {key: value for key, value in record.items() if key != "sha256"}
            assert record["previous_sha256"] == previous
            assert record["sha256"] == hashlib.sha256(canonical(unhashed)).hexdigest()
            previous = record["sha256"]

    rules = ("M0-1.0", "M0-F05-1.0", "M0-F15-1.0")
    candidate = f05_candidate("ADV-BASELINE", "ADV-REWRITTEN", before_hash, after_hash)
    baseline_candidate = replace(
        candidate, attempted_replacement_integrity=IntegrityRepresentation("SHA256", before_hash))
    assert run("ADV-HISTORY-BEFORE", AuditInput(
        historical_mutation_candidates=(baseline_candidate,)), rules).verdict == "PASS"
    history_result = run("ADV-HISTORY-AFTER", AuditInput(
        historical_mutation_candidates=(candidate,)), rules)
    assert history_result.verdict == "FAIL"
    assert "HISTORY_MUTATION" in history_result.violations

    states = tuple(replace(
        state(row["payload"]["node_id"]), claim_id=row["payload"]["claim_id"],
        observed_at=Timestamp(row["observed_at"]),
        state_context=TemporalContext(
            observed_at=Timestamp(row["observed_at"]), epoch="SYNTHETIC-EXPERIMENT",
            snapshot_id=row["payload"]["node_id"]),
    ) for row in before)
    baseline_edge = edge(before[1]["payload"]["lineage_from"],
                         before[1]["payload"]["lineage_to"])
    assert run("ADV-LINEAGE-BEFORE", AuditInput(
        historical_states=states, lineage_edges=(baseline_edge,)), rules).verdict == "PASS"
    rewritten_edge = replace(baseline_edge, from_reference=ref(after[1]["payload"]["lineage_from"]))
    lineage_result = run("ADV-LINEAGE-AFTER", AuditInput(
        historical_states=states, lineage_edges=(rewritten_edge,)), rules)
    assert lineage_result.verdict == "FAIL"
    assert "TEMPORALLY_UNRESOLVED" in lineage_result.violations

    unknown_result = run("ADV-HISTORY-NO-ANCHOR", AuditInput(
        historical_mutation_candidates=(replace(candidate, canonical_integrity=None),)), rules)
    assert unknown_result.verdict == "FAIL"
    assert "UNKNOWN" in unknown_result.violations
    assert "HISTORY_MUTATION" not in unknown_result.violations

    # Compose actual audit outputs only; caller IRG labels do not authenticate full IRGs.
    actual_results = (history_result, lineage_result)
    summary_request = CompositionRequest(
        composition_id="ADV-LOCAL-SUMMARY",
        participant_results=(
            CompositionParticipantResult("IRG-02", history_result.audit_id, "Synthetic byte comparison"),
            CompositionParticipantResult("IRG-03", lineage_result.audit_id, "Typed endpoint resolution"),
        ),
        composition_rule_id="M0-F15-LOCAL-SUMMARY", composition_rule_version="1.0",
        temporal_context="SYNTHETIC-AFTER",
        requested_conclusion=CompositionConclusion.LOCAL_RESULT_SUMMARY,
        limitations="No independent historical authentication or entity continuity",
        scope="Supplied M0 records only",
        requested_input_scope=CompositionInputScope.SUPPLIED_RESULTS_ONLY,
    )
    for conclusion in (CompositionConclusion.CLAIM_TRUTH, CompositionConclusion.SAME_ENTITY):
        request = replace(
            summary_request, composition_id=f"ADV-{conclusion.value}",
            composition_rule_id="M0-F15", composition_rule_version="M0-F15-1.0",
            requested_conclusion=conclusion)
        forbidden = run(f"ADV-COMPOSE-{conclusion.value}", AuditInput(
            prior_audit_results=actual_results, composition_requests=(request,)), rules)
        assert forbidden.verdict == "FAIL"
        assert "COMPOSITION_FORBIDDEN" in forbidden.violations
        assert forbidden.composition_summaries == ()

    summary_result = run("ADV-SUMMARY-RESULT", AuditInput(
        prior_audit_results=actual_results, composition_requests=(summary_request,)), rules)
    assert summary_result.verdict == "PASS"
    assert len(summary_result.composition_summaries) == 1
    summary = summary_result.composition_summaries[0]
    assert summary.verdict_counts == (("FAIL", 2),)
    assert "not independently authenticated" in summary.limitations
    assert "does not establish Claim truth" in summary.limitations

    wrapped = Evidence(
        evidence_id="ADV-WRAPPED-SUMMARY",
        observation_refs=(Reference(summary.composition_id, "COMPOSITION_SUMMARY"),),
        evidence_level="ATTEMPTED_PROMOTION", independence_status=IndependenceStatus.UNKNOWN,
        derivation_reference=ref("ADV-WRAPPING"), scope="Synthetic promotion attempt")
    assessment = Assessment(
        assessment_id="ADV-PROMOTED-ASSESSMENT", assessment_version="1",
        rule_version="CALLER-PROMOTION",
        admissible_evidence_refs=(Reference(wrapped.evidence_id, "EVIDENCE"),),
        condition_evaluation="Attempt to reuse local summary as support",
        assessment_basis="Not an independent observation",
        scope="Attempted historical/entity continuity support")
    promoted = run("ADV-SUMMARY-AS-EVIDENCE", AuditInput(
        evidence=(wrapped,), assessments=(assessment,),
        prior_audit_results=(summary_result,)), rules)
    assert promoted.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in promoted.violations


# M0 F11/F15 security repair: v1.1 always-on reference firewall.
# Appended, not substituted for the historical versioned F11/F15 tests.

def _m0_guard_evidence(observation=None, *, derivation=None, evidence_id="GUARD-E-1"):
    return Evidence(
        evidence_id=evidence_id,
        observation_refs=(observation or Reference("GUARD-REAL-OBS", "OBSERVATION"),),
        evidence_level="STRUCTURAL_ONLY",
        independence_status=IndependenceStatus.UNKNOWN,
        derivation_reference=derivation or Reference("GUARD-DER", "DERIVATION"),
        scope="SYNTHETIC-M0-GUARD",
    )


def _m0_guard_prior(audit_id="GUARD-OLD-AUDIT"):
    from core.schema import AuditResult
    return AuditResult(
        audit_id=audit_id,
        inspector_id="FIXTURE-NOT-TRUSTED",
        inspector_version="0",
        execution_timestamp=TS,
        configuration_id="GUARD-LAB",
        rule_versions=("M0-1.0",),
        artifacts_examined=(),
        violations=(),
        verdict="PASS",
        verdict_basis="Untrusted synthetic prior fixture",
    )


def test_m0_guard_typed_audit_observation_without_f15():
    result = run("GUARD-TYPED-AUDIT", AuditInput(
        evidence=(_m0_guard_evidence(Reference("GUARD-UNSEEN", "AUDIT_RESULT")),),
    ))
    assert result.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in result.violations


def test_m0_guard_typed_summary_observation_without_f15():
    result = run("GUARD-TYPED-SUMMARY", AuditInput(
        evidence=(_m0_guard_evidence(Reference("GUARD-SUMMARY", "COMPOSITION_SUMMARY")),),
    ))
    assert result.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in result.violations


def test_m0_guard_typed_request_observation_without_f15():
    result = run("GUARD-TYPED-REQUEST", AuditInput(
        evidence=(_m0_guard_evidence(Reference("GUARD-REQUEST", "COMPOSITION_REQUEST")),),
    ))
    assert result.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in result.violations


def test_m0_guard_typed_derivation_without_f15():
    result = run("GUARD-DERIVATION", AuditInput(
        evidence=(_m0_guard_evidence(derivation=Reference("GUARD-DER-OLD", "AUDIT_RESULT")),),
    ))
    assert result.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in result.violations


def test_m0_guard_prior_audit_id_mislabelled_as_observation_without_f15():
    result = run("GUARD-MISLABELLED-OBS", AuditInput(
        evidence=(_m0_guard_evidence(Reference("GUARD-OLD-AUDIT", "TEST")),),
        prior_audit_results=(_m0_guard_prior(),),
    ))
    assert result.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in result.violations


def test_m0_guard_f11_only_cannot_disable_observation_firewall():
    result = run("GUARD-F11-ONLY", AuditInput(
        evidence=(_m0_guard_evidence(Reference("GUARD-FAKE", "AUDIT_RESULT")),),
    ), ("M0-1.0", "M0-F11-1.0"))
    assert result.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in result.violations


def test_m0_guard_assessment_reference_typed_result_forbidden_without_f15():
    from core.schema import Assessment
    assessment = Assessment(
        assessment_id="GUARD-ASSESS-TYPED", assessment_version="1",
        rule_version="GUARD-LAB", admissible_evidence_refs=(Reference("GUARD-E-1", "AUDIT_RESULT"),),
        condition_evaluation="LAB", assessment_basis="LAB", scope="LAB",
    )
    result = run("GUARD-ASSESS-TYPED", AuditInput(
        evidence=(_m0_guard_evidence(),), assessments=(assessment,),
    ))
    assert result.verdict == "FAIL"
    assert "COMPOSITION_FORBIDDEN" in result.violations


def test_m0_guard_cross_kind_assessment_alias_remains_unknown_without_f15():
    from core.schema import Assessment
    evidence = _m0_guard_evidence(evidence_id="GUARD-OLD-AUDIT")
    assessment = Assessment(
        assessment_id="GUARD-ASSESS-ALIAS", assessment_version="1",
        rule_version="GUARD-LAB",
        admissible_evidence_refs=(Reference("GUARD-OLD-AUDIT", "EVIDENCE"),),
        condition_evaluation="LAB", assessment_basis="LAB", scope="LAB",
    )
    result = run("GUARD-ASSESS-ALIAS", AuditInput(
        evidence=(evidence,), assessments=(assessment,),
        prior_audit_results=(_m0_guard_prior(),),
    ))
    assert result.verdict == "FAIL"
    assert "UNKNOWN" in result.violations


def test_m0_guard_f11_legacy_result_only_reference_still_inadmissible():
    from core.schema import Assessment
    assessment = Assessment(
        assessment_id="GUARD-F11-LEGACY", assessment_version="1",
        rule_version="GUARD-LAB",
        admissible_evidence_refs=(Reference("GUARD-OLD-AUDIT", "TEST"),),
        condition_evaluation="LAB", assessment_basis="LAB", scope="LAB",
    )
    result = run("GUARD-F11-LEGACY", AuditInput(
        assessments=(assessment,), prior_audit_results=(_m0_guard_prior(),),
    ))
    assert result.verdict == "FAIL"
    assert "EVIDENCE_INADMISSIBLE" in result.violations
    assert "COMPOSITION_FORBIDDEN" not in result.violations


def test_m0_guard_keyword_without_identity_collision_still_passes():
    result = run("GUARD-KEYWORD-FALSE-POSITIVE", AuditInput(
        evidence=(_m0_guard_evidence(Reference("AUDIT-VERDICT-IS-IN-NAME", "OBSERVATION")),),
    ))
    assert result.verdict == "PASS"
    assert "COMPOSITION_FORBIDDEN" not in result.violations


def test_m0_guard_verdict_basis_declares_effective_profile_and_version():
    primary = AuditInput(evidence=(_m0_guard_evidence(),))
    base = run("GUARD-PROFILE-BASE", primary, ("M0-1.0",))
    full = run("GUARD-PROFILE-FULL", primary, ("M0-1.0", "M0-F11-1.0", "M0-F15-1.0"))
    assert base.verdict == full.verdict == "PASS"
    assert base.verdict_basis != full.verdict_basis
    assert "Declared rule versions" in base.verdict_basis
    assert "M0-REF-GUARD-1.0" in base.verdict_basis
    assert "M0-F15-1.0" in full.verdict_basis
    assert base.inspector_version == full.inspector_version == "M0-1.1"


def test_m0_guard_empty_primary_unknown_and_scoped():
    result = run("GUARD-EMPTY-PRIMARY", AuditInput())
    assert result.verdict == "UNKNOWN"
    assert "Declared rule versions" in result.verdict_basis
    assert "M0-REF-GUARD-1.0" in result.verdict_basis
