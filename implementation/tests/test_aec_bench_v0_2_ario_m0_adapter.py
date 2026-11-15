from research.aec_bench_v0_2_adapters.ario_m0_eag_adapter import (
    ENGINE_VERSION,
    build_m0_probe_report,
)


def test_m0_probe_report_calls_current_repository_engine():
    report = build_m0_probe_report()
    assert report["runtime_identity"] == "ACTUAL_REPOSITORY_AUDIT_ENGINE"
    assert report["engine_version"] == ENGINE_VERSION == "M0-1.2"
    assert report["mandatory_guard"] == "M0-EAG-0.1"
    assert report["case_count"] == 12
    assert report["predicate_matches"] == 12


def test_fixed_presence_is_the_only_positive_description_predicate():
    report = build_m0_probe_report()
    case = next(c for c in report["cases"] if c["case_id"] == "M0_EAG_01_RECORD_PRESENCE")
    row = case["observed"]["assessment"]
    assert case["observed"]["verdict"] == "PASS"
    assert row["record_presence"] == "MATCH"
    assert row["use_disposition"] == "RECORD_DESCRIPTION_ONLY"
    assert row["source_authentication"] == "UNKNOWN"
    assert case["observed"]["claim_truth"] == "UNKNOWN"


def test_m0_does_not_grant_independent_support_and_blocks_self_confirmation():
    report = build_m0_probe_report()
    cases = {c["case_id"]: c for c in report["cases"]}
    unresolved = cases["M0_EAG_02_NO_ADMISSION_AUTHORITY"]["observed"]
    self_confirm = cases["M0_EAG_03_EXACT_SELF_CONFIRMATION"]["observed"]
    assert unresolved["assessment"]["use_disposition"] == "UNKNOWN"
    assert self_confirm["assessment"]["use_disposition"] == "KNOWN_INADMISSIBLE"
    assert "EVIDENCE_INADMISSIBLE" in self_confirm["violations"]


def test_m0_preserves_shared_source_inflation_and_all_branch_failures():
    report = build_m0_probe_report()
    cases = {c["case_id"]: c for c in report["cases"]}
    shared = cases["M0_EAG_05_SHARED_SOURCE_INFLATION"]["observed"]
    mixed = cases["M0_EAG_07_FORBIDDEN_PLUS_MISSING"]["observed"]
    assert "EVIDENCE_INFLATION" in shared["violations"]
    assert {"COMPOSITION_FORBIDDEN", "UNKNOWN"}.issubset(mixed["violations"])


def test_m0_candidate_only_is_not_misread_as_admission():
    report = build_m0_probe_report()
    case = next(c for c in report["cases"] if c["case_id"] == "M0_EAG_09_CANDIDATE_ONLY")
    assert case["observed"]["verdict"] == "PASS"
    assert case["observed"]["candidate_use"] == "NOT_EVALUATED"
    assert case["observed"]["claim_truth"] == "UNKNOWN"
    assert case["observed"]["assessment"] is None
