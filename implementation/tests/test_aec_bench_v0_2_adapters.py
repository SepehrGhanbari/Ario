from __future__ import annotations

from dataclasses import replace

import pytest

from research.aec_benchmark_v0_2 import corpus


def test_prov_round_trip_preserves_synthetic_lineage_structure():
    pytest.importorskip("prov")
    from research.aec_bench_v0_2_adapters.prov_adapter import (
        build_prov_document,
        round_trip_prov_n,
        serialize_prov_n,
    )

    case = next(c for c in corpus() if c.case_id == "AEC02_LINEAGE_DEPENDENCE_06")
    provn = serialize_prov_n(case)
    assert "wasDerivedFrom" in provn
    assert round_trip_prov_n(case) is True
    assert build_prov_document(case) is not None


def test_prov_adapter_does_not_claim_truth_or_authenticity():
    pytest.importorskip("prov")
    from research.aec_bench_v0_2_adapters.prov_adapter import serialize_prov_n

    case = next(c for c in corpus() if c.case_id == "AEC02_LINEAGE_DEPENDENCE_01")
    provn = serialize_prov_n(case)
    assert "root_5231" in provn and "root_5232" in provn
    # The adapter returns a representation only; it has no truth/auth verdict.


def test_ltms_tracks_assumption_and_retraction():
    pytest.importorskip("ltms")
    from research.aec_bench_v0_2_adapters.ltms_adapter import assumption_retraction_probe

    result = assumption_retraction_probe()
    assert result == {
        "supported_before_retraction": True,
        "unknown_after_retraction": True,
    }


def test_ltms_comparable_conjunction_cases_and_explicit_non_comparability():
    pytest.importorskip("ltms")
    from research.aec_bench_v0_2_adapters.ltms_adapter import evaluate_dependency_case

    cases = {c.case_id: c for c in corpus()}
    supported = evaluate_dependency_case(cases["AEC02_COMPOSITION_DEPENDENCIES_01"])
    missing = evaluate_dependency_case(cases["AEC02_COMPOSITION_DEPENDENCIES_02"])
    incompatible = evaluate_dependency_case(cases["AEC02_COMPOSITION_DEPENDENCIES_03"])

    assert supported["comparable"] is True
    assert supported["status"] == "SUPPORTED"
    assert missing["comparable"] is True
    assert missing["status"] == "UNKNOWN"
    assert incompatible["comparable"] is False
    assert incompatible["status"] == "NOT_COMPARABLE"


def test_prov_rejects_missing_or_undeclared_source_root_entries():
    pytest.importorskip("prov")
    from research.aec_bench_v0_2_adapters.prov_adapter import build_prov_document

    case = next(c for c in corpus() if c.case_id == "AEC02_LINEAGE_DEPENDENCE_01")

    missing = dict(case.input["roots"])
    missing.pop("B")
    with pytest.raises(ValueError, match="exact source-to-root mapping"):
        build_prov_document(replace(case, input={**case.input, "roots": missing}))

    extra = {**case.input["roots"], "UNDECLARED": ["R99"]}
    with pytest.raises(ValueError, match="exact source-to-root mapping"):
        build_prov_document(replace(case, input={**case.input, "roots": extra}))


def test_prov_rejects_blank_root_identifiers_instead_of_dropping_them():
    pytest.importorskip("prov")
    from research.aec_bench_v0_2_adapters.prov_adapter import build_prov_document

    case = next(c for c in corpus() if c.case_id == "AEC02_LINEAGE_DEPENDENCE_01")
    malformed = {**case.input["roots"], "B": [" "]}
    with pytest.raises(ValueError, match="non-empty string root identifiers"):
        build_prov_document(replace(case, input={**case.input, "roots": malformed}))


def test_prov_round_trip_handles_arbitrary_utf8_source_and_root_ids():
    pytest.importorskip("prov")
    from research.aec_bench_v0_2_adapters.prov_adapter import (
        round_trip_prov_n,
        serialize_prov_n,
    )

    case = next(c for c in corpus() if c.case_id == "AEC02_LINEAGE_DEPENDENCE_01")
    fixture = replace(
        case,
        input={
            "sources": ["A / B"],
            "roots": {"A / B": ["R / 1"]},
        },
    )
    provn = serialize_prov_n(fixture)
    # UTF-8 hex encoding is reversible and keeps generated PROV local IDs safe.
    assert "agent_41202f2042" in provn
    assert "root_52202f2031" in provn
    assert round_trip_prov_n(fixture) is True
