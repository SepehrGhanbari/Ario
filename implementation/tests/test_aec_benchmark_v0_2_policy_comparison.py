from research.aec_benchmark_v0_2_policy_comparison import (
    METHODS,
    build_report,
    evaluate_method,
)
from research.aec_benchmark_v0_2 import corpus


def test_comparison_methods_are_task_scoped_and_disjoint():
    report = build_report()
    assert set(report["methods"]) == set(METHODS)
    assert report["methods"]["raw_relay_count"]["applicable_cases"] == 24
    assert report["methods"]["majority_vote"]["applicable_cases"] == 12
    assert report["methods"]["hash_integrity_only"]["applicable_cases"] == 12
    assert report["methods"]["ario_typed_policy_candidate"]["applicable_cases"] == 120
    assert report["methods"]["raw_relay_count"]["not_comparable_cases"] == 96
    assert report["methods"]["majority_vote"]["not_comparable_cases"] == 108


def test_typed_candidate_matches_each_authored_family_contract_without_global_score():
    report = build_report()
    typed = report["methods"]["ario_typed_policy_candidate"]
    assert len(typed["metrics"]["by_family_target_field"]) == 10
    for family, result in typed["metrics"]["by_family_target_field"].items():
        assert result["cases"] == 12, family
        assert result["matches"] == 12, family
        assert result["target_field_accuracy"] == 1.0, family
    assert "overall_score" not in typed
    assert "leaderboard_score" not in report


def test_raw_relay_count_inflates_shared_source_roots():
    report = build_report()
    raw = report["methods"]["raw_relay_count"]["metrics"]
    typed = report["methods"]["ario_typed_policy_candidate"]["metrics"]
    assert raw["false_independence_inflations"]["count"] > 0
    assert typed["false_independence_inflations"]["count"] == 0


def test_missing_ancestry_is_not_counted_as_a_known_root_count():
    report = build_report()
    raw = report["methods"]["raw_relay_count"]["metrics"]["missing_ancestry_preservation"]
    typed = report["methods"]["ario_typed_policy_candidate"]["metrics"]["missing_ancestry_preservation"]
    assert raw["rate"] == 0.0
    assert typed["rate"] == 1.0


def test_majority_vote_can_promote_minority_supported_claim():
    report = build_report()
    majority = report["methods"]["majority_vote"]["metrics"]
    typed = report["methods"]["ario_typed_policy_candidate"]["metrics"]
    assert majority["unsupported_claim_promotions"]["count"] > 0
    assert typed["unsupported_claim_promotions"]["count"] == 0


def test_hash_only_baseline_does_not_claim_authentication():
    report = build_report()
    hashed = report["methods"]["hash_integrity_only"]["metrics"]
    assert hashed["authentication_state"].startswith("NOT_COMPARABLE")
    assert "authentication" not in hashed["integrity_state"]


def test_each_baseline_rejects_out_of_lane_fixture_calls():
    cases = corpus()
    claim = next(c for c in cases if c.family == "claim_disposition")
    lineage = next(c for c in cases if c.family == "lineage_dependence")
    try:
        evaluate_method(claim, "raw_relay_count")
    except ValueError as exc:
        assert "not applicable" in str(exc)
    else:
        raise AssertionError("raw relay baseline accepted an unsupported family")
    try:
        evaluate_method(lineage, "majority_vote")
    except ValueError as exc:
        assert "not applicable" in str(exc)
    else:
        raise AssertionError("majority baseline accepted an unsupported family")


def test_comparison_report_contains_no_composite_ranking():
    report = build_report()
    assert report["method_count"] == 4
    assert report["case_count"] == 120
    assert "overall_score" not in report
    assert "composite_score" not in report
    assert any("No aggregate/composite leaderboard score" in item for item in report["non_claims"])


def test_macro_f1_discloses_class_support_and_exclusions():
    report = build_report()
    majority = report["methods"]["majority_vote"]["metrics"]["claim_disposition"]
    assert majority["per_class"]["REJECTED"]["support"] == 0
    assert "REJECTED" in majority["classes_excluded_for_zero_support"]
    assert majority["macro_f1_classes_included"] == 4
