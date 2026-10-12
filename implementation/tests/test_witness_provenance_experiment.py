"""Pre-registered TP-01..TP-26 synthetic-only provenance scenarios.

No real witnesses, production evidence, signer, ledger or network operations.
"""

from dataclasses import replace

import witness_provenance_experiment as p

S = "SYNTHETIC:LEDGER-001:EPOCH-01:BRANCH-A"


def node(name, kind, **fields):
    return p.Node(name, kind, S, p.LAB, "FROZEN-SUPPORT:" + name, **fields)


def edge(name, src, dst, kind, **fields):
    return p.Edge(name, src, dst, kind, p.LAB, "FROZEN-SUPPORT:" + name, **fields)


def baseline(*, shared_source=False, shared_admin=False):
    ns = [
        node("source-a", "SOURCE", object_identity="SOURCE-OBJECT-A"),
        node("source-b", "SOURCE", object_identity="SOURCE-OBJECT-B"),
        node("capture-a", "CAPTURE", capture_sequence=1, capture_custodian="origin-a"),
        node("capture-b", "CAPTURE", capture_sequence=2, capture_custodian="origin-b"),
        node("artifact-a", "ARTIFACT"), node("artifact-b", "ARTIFACT"),
        node("store-a", "STORAGE_DOMAIN", object_identity="DISK-A"),
        node("store-b", "STORAGE_DOMAIN", object_identity="DISK-B"),
        node("origin-a", "CUSTODIAN"), node("origin-b", "CUSTODIAN"),
        node("holder-a", "CUSTODIAN"), node("holder-b", "CUSTODIAN"),
        node("actor-a", "CONTROL_PRINCIPAL"), node("actor-b", "CONTROL_PRINCIPAL"),
        node("root-a", "CONTROL_ROOT"), node("root-b", "CONTROL_ROOT"),
    ]
    es = [
        edge("capture-link-a", "artifact-a", "capture-a", "CAPTURED_FROM"),
        edge("capture-link-b", "artifact-b", "capture-b", "CAPTURED_FROM"),
        edge("source-link-a", "capture-a", "source-a", "DERIVED_FROM"),
        edge("source-link-b", "capture-b", "source-a" if shared_source else "source-b", "DERIVED_FROM"),
        edge("storage-link-a", "artifact-a", "store-a", "STORED_AT"),
        edge("storage-link-b", "artifact-b", "store-b", "STORED_AT"),
        edge("holder-link-a", "artifact-a", "holder-a", "HELD_BY"),
        edge("holder-link-b", "artifact-b", "holder-b", "HELD_BY"),
        edge("transfer-a", "origin-a", "holder-a", "TRANSFERRED_TO", subject_artifact_ref="artifact-a", sequence=3),
        edge("transfer-b", "origin-b", "holder-b", "TRANSFERRED_TO", subject_artifact_ref="artifact-b", sequence=4),
        edge("writer-a", "actor-a", "store-a", "CAN_WRITE"),
        edge("writer-b", "actor-b", "store-b", "CAN_WRITE"),
        edge("admin-a", "root-a", "actor-a", "ADMINISTERS"),
        edge("admin-b", "root-a" if shared_admin else "root-b", "actor-b", "ADMINISTERS"),
    ]
    return p.ProvenanceCase(
        p.ControlGraph(tuple(ns), tuple(es)), S, ("artifact-a", "artifact-b"),
        complete_control_surface=True, complete_source_surface=True,
        completeness_origin=p.LAB, mutation_sequence=10,
    )


def edit(case, *, nodes=None, edges=None, **changes):
    return replace(case, graph=replace(case.graph,
        nodes=tuple(nodes if nodes is not None else case.graph.nodes),
        edges=tuple(edges if edges is not None else case.graph.edges)), **changes)


def replace_edge(case, name, **change):
    return edit(case, edges=[replace(e, **change) if e.edge_id == name else e for e in case.graph.edges])


def replace_node(case, name, **change):
    return edit(case, nodes=[replace(n, **change) if n.node_id == name else n for n in case.graph.nodes])


def no_edge(case, name):
    return edit(case, edges=[e for e in case.graph.edges if e.edge_id != name])


def assert_limits(r):
    assert r.production_custody_authenticity == "NOT_ESTABLISHED"
    assert r.cryptographic_authentication == "NOT_CHECKED"
    assert r.historical_event_truth == r.entity_continuity == r.ontological_continuity == "UNKNOWN"
    assert r.human_authorization == r.evidence_admission == "NOT_EVALUATED"
    assert r.production_historical_continuity == "INCONCLUSIVE"
    assert r.kind == "EXPERIMENTAL_PROVENANCE_REPORT"
    assert isinstance(r.reason_codes, tuple)


def check(case):
    result = p.evaluate_provenance(case)
    assert_limits(result)
    return result


def test_tp01_one_administrator_two_objects():
    r = check(baseline(shared_admin=True))
    assert r.administrative_separation.status == "COMMON_CONTROL_DETECTED"
    assert any("CONTROL:root-a" in path for path in r.common_control_paths)
    assert r.storage_separation.status == "LAB_DISTINCT_OBJECTS"


def test_tp02_alias_storage_objects():
    c = replace_node(baseline(), "store-b", object_identity="DISK-A")
    r = check(c)
    assert r.storage_separation.status == "SAME_STORAGE_OBJECT"
    assert r.administrative_separation.status == "COMMON_CONTROL_DETECTED"


def test_tp03_shared_writable_restore_backup():
    c = baseline()
    ns = c.graph.nodes + (node("shared-backup", "STORAGE_DOMAIN", object_identity="BACKUP-1"),
                          node("backup-admin", "CONTROL_PRINCIPAL"))
    es = c.graph.edges + (
        edge("restores-a", "store-a", "shared-backup", "RESTORES_FROM"),
        edge("restores-b", "store-b", "shared-backup", "RESTORES_FROM"),
        edge("backup-write", "backup-admin", "shared-backup", "CAN_WRITE"),
    )
    r = check(edit(c, nodes=ns, edges=es))
    assert r.administrative_separation.status == "COMMON_CONTROL_DETECTED"
    assert any("backup-write" in path for path in r.common_control_paths)


def test_tp04_shared_override_root():
    c = baseline()
    e = edge("root-overrides-b", "root-a", "root-b", "SHARES_CONTROL_ROOT")
    r = check(edit(c, edges=c.graph.edges + (e,)))
    assert r.administrative_separation.status == "COMMON_CONTROL_DETECTED"


def test_tp05_complete_separate_lab_control():
    r = check(baseline())
    assert r.administrative_separation.status == "LAB_CONDITIONALLY_SEPARATE"
    assert r.source_independence.status == "LAB_CONDITIONALLY_DISTINCT"
    assert r.capture_order.status == "LAB_BEFORE_MUTATION"
    assert all(x.status == "LAB_CHAIN_PRESENT" for x in r.per_witness_custody)


def test_tp06_absent_admin_inventory():
    r = check(replace(baseline(), complete_control_surface=False))
    assert r.administrative_separation.status == "UNKNOWN"


def test_tp07_missing_permission_not_evidence_of_absence():
    c = no_edge(baseline(), "writer-b")
    r = check(replace(c, complete_control_surface=False))
    assert r.administrative_separation.status == "UNKNOWN"


def test_tp08_witness_self_provenance_certificate():
    c = baseline()
    forged = replace(edge("self-proof", "root-a", "actor-b", "ADMINISTERS"), origin=p.SELF)
    r = check(replace(c, presented_claims=(forged,)))
    assert "self-proof" in r.unsupported_claims
    assert r.administrative_separation.status == "LAB_CONDITIONALLY_SEPARATE"
    assert "NOT_ESTABLISHED" == r.production_custody_authenticity


def test_tp09_candidate_supplies_alleged_control_graph():
    c = baseline()
    r = check(replace(c, graph=replace(c.graph, origin=p.CANDIDATE)))
    assert r.administrative_separation.status == "UNKNOWN"
    assert r.source_independence.status == "UNKNOWN"


def test_tp10_distinct_custody_same_source():
    r = check(baseline(shared_source=True))
    assert r.administrative_separation.status == "LAB_CONDITIONALLY_SEPARATE"
    assert r.source_independence.status == "COMMON_SOURCE_DETECTED"


def test_tp11_distinct_sources_shared_custody_admin():
    r = check(baseline(shared_admin=True))
    assert r.source_independence.status == "LAB_CONDITIONALLY_DISTINCT"
    assert r.administrative_separation.status == "COMMON_CONTROL_DETECTED"


def test_tp12_missing_transfer_record():
    r = check(no_edge(baseline(), "transfer-b"))
    assert r.per_witness_custody[1].status == "UNKNOWN"
    assert r.administrative_separation.status == "UNKNOWN"


def test_tp13_invalid_transfer_sequence():
    r = check(replace_edge(baseline(), "transfer-a", sequence=0))
    assert r.per_witness_custody[0].status == "UNKNOWN"


def test_tp14_witness_compromised_before_capture():
    c = replace(baseline(), compromise_intervals=(p.CompromiseInterval("artifact-a", 0, 3),))
    r = check(c)
    assert r.capture_order.status == "UNKNOWN"
    assert r.administrative_separation.status == "COMPROMISED_BY_SCENARIO"


def test_tp15_witness_compromised_after_capture_no_retained_exclusive_ref():
    c = replace(baseline(), compromise_intervals=(p.CompromiseInterval("actor-b", 5, None),))
    r = check(c)
    assert r.capture_order.status == "LAB_BEFORE_MUTATION"
    assert r.administrative_separation.status == "COMPROMISED_BY_SCENARIO"
    assert r.production_custody_authenticity == "NOT_ESTABLISHED"


def test_tp16_capture_precedes_modeled_mutation_only():
    r = check(baseline())
    assert r.capture_order.status == "LAB_BEFORE_MUTATION"
    # No candidate ledger bytes are supplied: this does NOT assert actual mutation detection.
    assert r.historical_event_truth == "UNKNOWN"


def test_tp17_controller_full_compromise():
    r = check(replace(baseline(), controller_compromised=True,
                      compromised_node_ids=("root-a", "root-b", "artifact-a", "artifact-b")))
    assert r.administrative_separation.status == "UNKNOWN"
    assert r.source_independence.status == "UNKNOWN"
    assert r.capture_order.status == "UNKNOWN"
    assert all(x.status == "UNKNOWN" for x in r.per_witness_custody)


def test_tp18_replayed_scope():
    c = replace_node(baseline(), "artifact-b", scope="OTHER-BRANCH")
    r = check(c)
    assert r.administrative_separation.status != "LAB_CONDITIONALLY_SEPARATE"
    assert "SCOPE_REPLAY:artifact-b" in r.conflicting_provenance


def test_tp19_changed_witness_reference():
    c = replace(baseline(), witness_artifact_refs=("artifact-a", "artifact-a"))
    r = check(c)
    assert "INVALID_ARTIFACT_OR_COMPROMISE_REFERENCE" in r.reason_codes


def test_tp20_cyclic_provenance_support():
    c = baseline()
    e = edge("cyclic-self-source", "source-a", "source-a", "DERIVED_FROM")
    r = check(edit(c, edges=c.graph.edges + (e,)))
    assert r.source_independence.status == "UNKNOWN"


def test_tp21_one_artifact_duplicated_as_independent():
    c = replace(baseline(), witness_artifact_refs=("artifact-b", "artifact-b"))
    r = check(c)
    assert r.administrative_separation.status == "UNKNOWN"


def test_tp22_conflicting_custody_claims():
    c = baseline()
    extra = edge("second-holder", "artifact-a", "holder-b", "HELD_BY")
    r = check(edit(c, edges=c.graph.edges + (extra,)))
    assert r.per_witness_custody[0].status == "UNKNOWN"
    assert r.administrative_separation.status == "UNKNOWN"


def test_tp23_permutation_determinism():
    c = baseline()
    flipped = edit(c, nodes=reversed(c.graph.nodes), edges=reversed(c.graph.edges))
    assert check(c) == check(flipped)


def test_tp24_duplicate_nodes_edges_and_limits():
    c = baseline()
    dups = edit(c, nodes=c.graph.nodes + (c.graph.nodes[0],))
    assert check(dups).reason_codes == ("INVALID_OR_DUPLICATE_NODE",)
    badedge = edit(c, edges=c.graph.edges + (c.graph.edges[0],))
    assert check(badedge).reason_codes == ("INVALID_OR_DUPLICATE_EDGE",)
    giant = edit(c, nodes=c.graph.nodes + tuple(node(f"filler-{i}", "SOURCE") for i in range(65)))
    assert check(giant).reason_codes == ("INVALID_BOUNDS_OR_TYPES",)


def test_tp25_tb002_report_as_self_certified_custody():
    c = baseline()
    claim = replace(edge("prior-report", "root-a", "actor-b", "ADMINISTERS"), origin=p.DERIVED)
    r = check(replace(c, presented_claims=(claim,)))
    assert "prior-report" in r.unsupported_claims
    assert r.production_custody_authenticity == "NOT_ESTABLISHED"


def test_tp26_provenance_not_m0_truth_or_authority():
    r = check(baseline())
    assert r.kind != "Evidence" and r.kind != "AuditResult"
    assert r.evidence_admission == "NOT_EVALUATED"
    assert r.historical_event_truth == "UNKNOWN"
    assert r.human_authorization == "NOT_EVALUATED"


def test_extra_unsupported_algorithm_and_profile():
    c = baseline()
    assert check(replace(c, profile="UNSUPPORTED")).reason_codes == ("UNSUPPORTED_PROFILE",)


def test_extra_incomplete_source_surface():
    r = check(replace(baseline(), complete_source_surface=False))
    assert r.source_independence.status == "UNKNOWN"


def test_extra_completeness_assertion_from_candidate():
    r = check(replace(baseline(), completeness_origin=p.CANDIDATE))
    assert r.administrative_separation.status == "UNKNOWN"
    assert r.source_independence.status == "UNKNOWN"


def test_extra_untrusted_claim_does_not_override_supported_common_control():
    c = baseline(shared_admin=True)
    fake = replace(edge("deny-admin", "root-b", "actor-b", "ADMINISTERS"), origin=p.SELF)
    r = check(replace(c, presented_claims=(fake,)))
    assert r.administrative_separation.status == "COMMON_CONTROL_DETECTED"


def test_extra_unsupported_transfer_origin():
    r = check(replace_edge(baseline(), "transfer-a", origin=p.SELF))
    assert r.per_witness_custody[0].status == "UNKNOWN"
    assert r.administrative_separation.status == "UNKNOWN"


def test_extra_no_timestamp_authentication():
    r = check(replace(baseline(), mutation_sequence=None))
    assert r.capture_order.status == "UNKNOWN"


def test_extra_case_output_is_repeatable():
    c = baseline()
    assert check(c) == check(c)


def test_extra_distinct_source_ids_same_underlying_source_object():
    c = replace_node(baseline(), "source-b", object_identity="SOURCE-OBJECT-A")
    r = check(c)
    assert r.source_independence.status == "COMMON_SOURCE_DETECTED"
    assert r.administrative_separation.status == "LAB_CONDITIONALLY_SEPARATE"


def test_extra_invalid_compromise_interval_fails_closed():
    c = replace(baseline(), compromise_intervals=(p.CompromiseInterval("artifact-a", 10, 3),))
    assert check(c).reason_codes == ("INVALID_COMPROMISE_INTERVAL",)


def test_extra_control_cycle_cannot_establish_conditional_separation():
    c = baseline()
    # Root-to-root cycle is not independently supported separation.
    es = c.graph.edges + (edge("root-cycle-1", "root-a", "root-b", "ADMINISTERS"),
                          edge("root-cycle-2", "root-b", "root-a", "ADMINISTERS"))
    r = check(edit(c, edges=es))
    assert r.administrative_separation.status in {"COMMON_CONTROL_DETECTED", "UNKNOWN"}
    assert r.administrative_separation.status != "LAB_CONDITIONALLY_SEPARATE"


def test_extra_candidate_origin_node_blocks_conditional_independence():
    c = replace_node(baseline(), "store-b", origin=p.CANDIDATE)
    r = check(c)
    assert r.administrative_separation.status == "UNKNOWN"
    assert r.storage_separation.status == "UNKNOWN"
    assert "NODE:store-b" in r.unsupported_claims


def test_extra_candidate_origin_edge_blocks_conditional_independence():
    c = replace_edge(baseline(), "writer-b", origin=p.CANDIDATE)
    r = check(c)
    assert r.administrative_separation.status == "UNKNOWN"
    assert "writer-b" in r.unsupported_claims


def test_extra_malformed_unhashable_fields_fail_closed():
    c = baseline()
    cases = (
        replace(c, completeness_origin=[]),
        replace(c, graph=replace(c.graph, origin={})),
        replace_node(c, "store-b", kind=[]),
        replace_edge(c, "writer-a", source=[]),
        replace_edge(c, "writer-a", kind={}),
        replace_edge(c, "transfer-a", subject_artifact_ref=[]),
    )
    for bad in cases:
        assert check(bad).reason_codes[0].startswith("INVALID_")


def test_extra_compromise_interval_at_capture_fails_order_closed():
    c = replace(baseline(), compromise_intervals=(p.CompromiseInterval("artifact-b", 2, 2),))
    r = check(c)
    assert r.capture_order.status == "UNKNOWN"
    assert r.administrative_separation.status == "COMPROMISED_BY_SCENARIO"


def test_extra_no_restoration_link_means_backup_not_write_path():
    c = baseline()
    ns = c.graph.nodes + (node("shared-backup", "STORAGE_DOMAIN", object_identity="BACKUP-1"),
                          node("backup-admin", "CONTROL_PRINCIPAL"))
    es = c.graph.edges + (edge("backup-write", "backup-admin", "shared-backup", "CAN_WRITE"),)
    r = check(edit(c, nodes=ns, edges=es))
    assert r.administrative_separation.status == "LAB_CONDITIONALLY_SEPARATE"
