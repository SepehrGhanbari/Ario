from research.aec_benchmark_v0_2 import FAMILIES, VERSION, _evaluate, corpus, score


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
    assert "No real-world source independence" in result["limitations"][3]


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
