from research.aec_benchmark_v0_2 import (
    FAMILIES, VERSION, Fixture, _evaluate, audit_counterfactual_pairs,
    changed_input_paths, corpus, score,
)


def test_version_and_corpus_shape():
    cases = corpus()
    assert VERSION == "AEC-Bench-0.2"
    assert len(cases) == 120
    assert len({case.case_id for case in cases}) == 120
    assert {case.family for case in cases} == set(FAMILIES)


def test_ten_families_have_twelve_cases_each():
    cases = corpus()
    for family in FAMILIES:
        assert sum(case.family == family for case in cases) == 12


def test_reference_evaluator_matches_authored_fixture_oracle():
    for case in corpus():
        assert _evaluate(case) == case.expected, case.case_id


def test_declared_shared_root_is_not_counted_as_independent():
    case = next(c for c in corpus() if c.case_id == "AEC02_LINEAGE_DEPENDENCE_03")
    assert _evaluate(case)["root_count"] == 1


def test_conflicting_claims_remain_contested_despite_majority():
    case = next(c for c in corpus() if c.case_id == "AEC02_CLAIM_DISPOSITION_05")
    assert _evaluate(case)["status"] == "CONTESTED"


def test_valid_digest_does_not_authenticate_source():
    case = next(c for c in corpus() if c.case_id == "AEC02_INTEGRITY_AUTHENTICITY_02")
    result = _evaluate(case)
    assert result["integrity"] == "VALID"
    assert result["auth"] == "UNVERIFIED"
    assert result["status"] == "UNKNOWN"


def test_local_validity_does_not_imply_valid_composition():
    case = next(c for c in corpus() if c.case_id == "AEC02_COMPOSITION_DEPENDENCIES_10")
    assert _evaluate(case) == {"composition": "UNKNOWN", "status": "UNKNOWN"}


def test_revision_erasure_is_not_silently_accepted():
    case = next(c for c in corpus() if c.case_id == "AEC02_REVISION_HISTORY_03")
    assert _evaluate(case)["history"] == "ERASURE_DETECTED"
    assert _evaluate(case)["status"] == "REJECTED"


def test_score_discloses_synthetic_scope_and_per_family_results():
    result = score()
    assert result["case_count"] == 120
    assert result["family_count"] == 10
    assert result["policy_identity"] == "AEC_BENCH_FIXTURE_REFERENCE_EVALUATOR_NOT_ARIO_RUNTIME"
    assert len(result["by_family"]) == 10
    assert all(row["cases"] == 12 for row in result["by_family"].values())
    assert all("fixture_contract_conformance" in row for row in result["by_family"].values())
    assert "overall_fixture_accuracy" not in result
    assert "overall_fixture_matches" not in result
    assert "No aggregate or composite benchmark score is produced." in result["limitations"]
    assert any("No real-world source independence" in item for item in result["limitations"])


def test_counterfactual_pair_changes_exactly_one_controlled_field_per_family():
    cases = corpus()
    for family in FAMILIES:
        pair = [c for c in cases if c.family == family and c.pair_group]
        assert len(pair) == 2, family
        assert pair[0].pair_group == pair[1].pair_group
        left, right = pair
        assert set(left.input) == set(right.input), family
        changed = [key for key in left.input if left.input[key] != right.input[key]]
        assert len(changed) == 1, (family, changed)
        assert _evaluate(left) == left.expected, left.case_id
        assert _evaluate(right) == right.expected, right.case_id


def test_narrow_evidence_does_not_support_a_broader_scope_claim():
    case = next(c for c in corpus() if c.case_id == "AEC02_SCOPE_02")
    assert _evaluate(case) == {"scope": "OUT_OF_SCOPE", "status": "REJECTED"}


def test_missing_root_ancestry_remains_unknown():
    case = next(c for c in corpus() if c.case_id == "AEC02_LINEAGE_DEPENDENCE_05")
    assert _evaluate(case) == {"root_count": None, "status": "UNKNOWN"}


def test_each_family_has_three_controls_adversaries_and_boundaries():
    cases = corpus()
    expected = {
        "positive_control", "positive_control_b", "positive_control_c",
        "adversarial", "adversarial_b", "adversarial_c",
        "boundary", "boundary_b", "boundary_c",
    }
    for family in FAMILIES:
        variants = {c.variant for c in cases if c.family == family}
        assert expected.issubset(variants), family


def test_support_plus_unknown_does_not_promote_claim():
    case = next(c for c in corpus() if c.case_id == "AEC02_CLAIM_DISPOSITION_04")
    assert _evaluate(case) == {"status": "UNKNOWN"}


def test_missing_observation_timestamp_is_partial_not_exception():
    case = next(c for c in corpus() if c.case_id == "AEC02_TEMPORAL_PROVENANCE_03")
    assert _evaluate(case) == {"temporal": "PARTIAL", "status": "UNKNOWN"}


def test_schema_counterfactual_pair_changes_only_compatibility_declaration():
    cases = [c for c in corpus() if c.family == "schema_version" and c.pair_group]
    assert len(cases) == 2
    first, second = cases
    assert set(first.input) == set(second.input)
    changed = [key for key in first.input if first.input[key] != second.input[key]]
    assert changed == ["compatibility_unstated"]


def test_not_applicable_authentication_is_not_relabelled_unverified():
    case = next(c for c in corpus() if c.case_id == "AEC02_INTEGRITY_AUTHENTICITY_06")
    result = _evaluate(case)
    assert result["integrity"] == "VALID"
    assert result["auth"] == "NOT_APPLICABLE"
    assert result["status"] == "UNKNOWN"



def test_counterfactual_pair_audit_checks_atomic_nested_changes():
    cases = corpus()
    audit = audit_counterfactual_pairs(cases)
    assert audit["pair_group_count"] == 10
    assert audit["valid_pair_count"] == 10
    assert audit["invalid_pair_count"] == 0
    assert all(len(pair["changed_input_paths"]) == 1 for pair in audit["pairs"])
    assert audit["limitation"].startswith("A single structural input delta")

    # A top-level-only comparison would miss this two-leaf mutation.
    left = {"metadata": {"scope": "A", "version": 1}}
    right = {"metadata": {"scope": "B", "version": 2}}
    assert changed_input_paths(left, right) == [
        "/metadata/scope",
        "/metadata/version",
    ]


def test_counterfactual_pair_audit_rejects_multiple_nested_mutations():
    left = Fixture(
        case_id="PAIR_A",
        family="lineage_dependence",
        variant="counterfactual_base",
        pair_group="NESTED_MUTATION",
        input={"metadata": {"scope": "A", "version": 1}},
        expected={"status": "UNKNOWN"},
        rationale="test-only",
    )
    right = Fixture(
        case_id="PAIR_B",
        family="lineage_dependence",
        variant="counterfactual_delta",
        pair_group="NESTED_MUTATION",
        input={"metadata": {"scope": "B", "version": 2}},
        expected={"status": "UNKNOWN"},
        rationale="test-only",
    )
    audit = audit_counterfactual_pairs((left, right))
    assert audit["invalid_pair_count"] == 1
    assert audit["pairs"][0]["valid"] is False
    assert audit["pairs"][0]["changed_input_paths"] == [
        "/metadata/scope",
        "/metadata/version",
    ]
    assert "EXPECTED_EXACTLY_ONE_ATOMIC_INPUT_CHANGE" in audit["pairs"][0]["issues"]


def test_fixture_contract_report_includes_pair_structure_audit():
    report = score()
    audit = report["counterfactual_pair_validation"]
    assert audit["audit_kind"] == "STRUCTURAL_COUNTERFACTUAL_PAIR_AUDIT"
    assert audit["pair_group_count"] == 10
    assert audit["valid_pair_count"] == 10
    assert audit["invalid_pair_count"] == 0



def _fixture_with_input(case, input_data):
    return Fixture(
        case_id=case.case_id,
        family=case.family,
        variant=case.variant,
        pair_group=case.pair_group,
        input=input_data,
        expected=case.expected,
        rationale=case.rationale,
    )


def test_missing_source_root_mapping_preserves_unknown_root_count():
    case = next(c for c in corpus() if c.case_id == "AEC02_LINEAGE_DEPENDENCE_01")
    mutated_input = {**case.input, "roots": dict(case.input["roots"])}
    mutated_input["roots"].pop("B")
    assert _evaluate(_fixture_with_input(case, mutated_input)) == {
        "root_count": None, "status": "UNKNOWN"
    }


def test_undeclared_extra_root_mapping_is_not_silently_counted():
    case = next(c for c in corpus() if c.case_id == "AEC02_LINEAGE_DEPENDENCE_01")
    mutated_input = {**case.input, "roots": dict(case.input["roots"])}
    mutated_input["roots"]["UNDECLARED"] = ["R99"]
    assert _evaluate(_fixture_with_input(case, mutated_input)) == {
        "root_count": None, "status": "UNKNOWN"
    }


def test_duplicate_source_declaration_preserves_unknown_root_count():
    case = next(c for c in corpus() if c.case_id == "AEC02_LINEAGE_DEPENDENCE_01")
    mutated_input = {**case.input, "sources": [*case.input["sources"], "A"]}
    assert _evaluate(_fixture_with_input(case, mutated_input)) == {
        "root_count": None, "status": "UNKNOWN"
    }


def test_blank_root_identifier_preserves_unknown_root_count():
    case = next(c for c in corpus() if c.case_id == "AEC02_LINEAGE_DEPENDENCE_01")
    mutated_input = {**case.input, "roots": dict(case.input["roots"])}
    mutated_input["roots"]["B"] = [" "]
    assert _evaluate(_fixture_with_input(case, mutated_input)) == {
        "root_count": None, "status": "UNKNOWN"
    }


def test_missing_event_time_remains_partial_not_exception():
    case = next(c for c in corpus() if c.case_id == "AEC02_TEMPORAL_PROVENANCE_01")
    mutated_input = dict(case.input)
    mutated_input.pop("event")
    assert _evaluate(_fixture_with_input(case, mutated_input)) == {
        "temporal": "PARTIAL", "status": "UNKNOWN"
    }


def test_missing_recorded_time_remains_partial_not_exception():
    case = next(c for c in corpus() if c.case_id == "AEC02_TEMPORAL_PROVENANCE_01")
    mutated_input = {**case.input, "recorded": None}
    assert _evaluate(_fixture_with_input(case, mutated_input)) == {
        "temporal": "PARTIAL", "status": "UNKNOWN"
    }


def test_malformed_timestamp_remains_unknown_not_exception():
    case = next(c for c in corpus() if c.case_id == "AEC02_TEMPORAL_PROVENANCE_01")
    mutated_input = {**case.input, "recorded": "twelve"}
    assert _evaluate(_fixture_with_input(case, mutated_input)) == {
        "temporal": "UNKNOWN", "status": "UNKNOWN"
    }


def test_non_finite_timestamp_remains_unknown_not_ordered():
    case = next(c for c in corpus() if c.case_id == "AEC02_TEMPORAL_PROVENANCE_01")
    mutated_input = {**case.input, "recorded": float("nan")}
    assert _evaluate(_fixture_with_input(case, mutated_input)) == {
        "temporal": "UNKNOWN", "status": "UNKNOWN"
    }


def test_composition_requires_explicit_complete_compatibility_checks():
    case = next(c for c in corpus() if c.case_id == "AEC02_COMPOSITION_DEPENDENCIES_01")
    assert _evaluate(case) == {"composition": "VALID", "status": "UNKNOWN"}
    mutated_input = dict(case.input)
    mutated_input.pop("composition_checks")
    mutated_input.pop("composition_checks_complete")
    assert _evaluate(_fixture_with_input(case, mutated_input)) == {
        "composition": "UNKNOWN", "status": "UNKNOWN"
    }


def test_composition_pair_changes_only_check_completeness_and_never_promotes_truth():
    pair = [
        c for c in corpus()
        if c.family == "composition_dependencies" and c.pair_group
    ]
    assert len(pair) == 2
    first, second = pair
    assert changed_input_paths(first.input, second.input) == [
        "/composition_checks_complete"
    ]
    assert _evaluate(first) == {"composition": "UNKNOWN", "status": "UNKNOWN"}
    assert _evaluate(second) == {"composition": "VALID", "status": "UNKNOWN"}


def test_composition_missing_compatibility_dimension_remains_unknown():
    case = next(c for c in corpus() if c.case_id == "AEC02_COMPOSITION_DEPENDENCIES_01")
    mutated_input = {**case.input, "composition_checks": dict(case.input["composition_checks"])}
    mutated_input["composition_checks"].pop("scope")
    assert _evaluate(_fixture_with_input(case, mutated_input)) == {
        "composition": "UNKNOWN", "status": "UNKNOWN"
    }


def test_composition_unknown_dimension_does_not_become_valid():
    case = next(c for c in corpus() if c.case_id == "AEC02_COMPOSITION_DEPENDENCIES_01")
    mutated_input = {**case.input, "composition_checks": dict(case.input["composition_checks"])}
    mutated_input["composition_checks"]["temporal"] = "UNKNOWN"
    assert _evaluate(_fixture_with_input(case, mutated_input)) == {
        "composition": "UNKNOWN", "status": "UNKNOWN"
    }


def test_composition_explicit_incompatibility_rejects():
    case = next(c for c in corpus() if c.case_id == "AEC02_COMPOSITION_DEPENDENCIES_01")
    mutated_input = {**case.input, "composition_checks": dict(case.input["composition_checks"])}
    mutated_input["composition_checks"]["scope"] = "INCOMPATIBLE"
    assert _evaluate(_fixture_with_input(case, mutated_input)) == {
        "composition": "INVALID", "status": "REJECTED"
    }


def test_shared_dependency_does_not_bypass_missing_requirement_check():
    case = next(c for c in corpus() if c.case_id == "AEC02_COMPOSITION_DEPENDENCIES_04")
    mutated_input = {**case.input, "requirements": ["P1", "P2", "P3"]}
    assert _evaluate(_fixture_with_input(case, mutated_input)) == {
        "composition": "INCOMPLETE", "status": "UNKNOWN"
    }


def test_shared_dependency_is_qualified_and_never_asserts_independence():
    case = next(c for c in corpus() if c.case_id == "AEC02_COMPOSITION_DEPENDENCIES_04")
    assert _evaluate(case) == {
        "composition": "VALID_WITH_SHARED_DEPENDENCY", "status": "UNKNOWN"
    }


def test_composition_check_completion_must_be_a_boolean():
    case = next(c for c in corpus() if c.case_id == "AEC02_COMPOSITION_DEPENDENCIES_01")
    mutated_input = {**case.input, "composition_checks_complete": "false"}
    assert _evaluate(_fixture_with_input(case, mutated_input)) == {
        "composition": "UNKNOWN", "status": "UNKNOWN"
    }


def test_malformed_composition_check_types_fail_closed_without_exception():
    case = next(c for c in corpus() if c.case_id == "AEC02_COMPOSITION_DEPENDENCIES_01")
    mutated_input = {**case.input, "composition_checks": dict(case.input["composition_checks"])}
    mutated_input["composition_checks"]["dependency"] = []
    assert _evaluate(_fixture_with_input(case, mutated_input)) == {
        "composition": "UNKNOWN", "status": "UNKNOWN"
    }


def test_composition_duplicate_premise_identity_remains_unknown():
    case = next(c for c in corpus() if c.case_id == "AEC02_COMPOSITION_DEPENDENCIES_01")
    mutated_input = {**case.input, "premises": ["P1", "P1"]}
    assert _evaluate(_fixture_with_input(case, mutated_input)) == {
        "composition": "UNKNOWN", "status": "UNKNOWN"
    }


def test_legacy_boolean_shared_dependency_is_not_accepted_as_composition_evidence():
    case = next(c for c in corpus() if c.case_id == "AEC02_COMPOSITION_DEPENDENCIES_01")
    mutated_input = {**case.input, "shared_dependency": True}
    assert _evaluate(_fixture_with_input(case, mutated_input)) == {
        "composition": "UNKNOWN", "status": "UNKNOWN"
    }
