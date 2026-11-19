"""Regression tests from the 2026-11-15 blind multi-model review.

R1 and R2 pin two comparison rules that earlier tests left loose: a weakened
version of either rule still passed the whole suite (verified by mutation).
R3 pins, and makes visible in the report, a design decision (unresolved
TRANSFORMATION derivations) that is not a defect.
"""
import json
import os
import sys
from dataclasses import replace

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import test_m0_regression as t
from core.audit_engine import (
    AuditEngine, AuditInput, EAG_FINDINGS_BEGIN, EAG_FINDINGS_END,
    _EvidenceAncestryGuard, _serialize_ancestry_report,
    parse_evidence_ancestry_findings,
)
from core.schema import Reference, RetrievalEvent


def test_r1_history_mutation_detected_when_only_digest_suffix_differs():
    canonical = "00a9c8f9aabbccdd" + "1" * 48
    replacement = "00a9c8f9aabbccdd" + "2" * 48
    assert canonical[:16] == replacement[:16] and canonical != replacement
    candidate = t.f05_candidate("CANON-R1", "REPL-R1", canonical, replacement)
    result = t.run("R1", AuditInput(historical_mutation_candidates=(candidate,)),
                   ("M0-1.0", "M0-F05-1.0"))
    assert result.verdict == "FAIL"
    assert "HISTORY_MUTATION" in result.violations


def test_r1_truncated_digest_is_not_equal_to_full_digest():
    full = "00a9c8f9aabbccdd" + "1" * 48
    candidate = t.f05_candidate("CANON-R1B", "REPL-R1B", full, full[:16])
    result = t.run("R1B", AuditInput(historical_mutation_candidates=(candidate,)),
                   ("M0-1.0", "M0-F05-1.0"))
    assert "HISTORY_MUTATION" in result.violations


def test_r2_retrieval_discrepancy_when_only_reference_type_differs():
    event = RetrievalEvent(
        retrieval_id="RETRIEVAL-R2",
        source_reference=t.ref("SOURCE-R2"),
        retrieved_reference=t.ref("RETRIEVED-R2"),
        retrieval_timestamp=t.TS,
        transformation_reference=Reference("SAME", "TRANSFORMATION"),
        fidelity_status="CORRUPT",
        provenance=t.prov("PROV-R2"),
        observed_transformation_reference=Reference("SAME", "OTHER_TYPE"),
    )
    result = t.run("R2", AuditInput(retrieval_events=(event,)))
    assert "RETRIEVAL_DISCREPANCY" in result.violations
    assert result.verdict == "FAIL"


def test_r3_unresolved_transformation_is_reported_but_verdict_unchanged():
    base = t._eag_fixture(presence=True)
    for rid in ("MISSING-DERIV", "EAG-PROCEDURE"):
        ev = replace(base.evidence[0], derivation_reference=Reference(rid, "TRANSFORMATION"))
        result = t.run(f"R3-{rid}", replace(base, evidence=(ev,)))
        doc = t._eag_doc(result)
        assert result.verdict == "PASS"          # design decision, pinned
        assert result.violations == ()
        assert doc["transformation_derivations_declared_not_resolved"] == [rid]
        assert doc["transformation_derivations_truncated"] is False


def test_r3_same_derivation_typed_as_claim_still_fails_closed():
    base = t._eag_fixture(presence=True)
    ev = replace(base.evidence[0], derivation_reference=Reference("MISSING-DERIV", "CLAIM"))
    result = t.run("R3-CLAIM", replace(base, evidence=(ev,)))
    assert result.verdict == "FAIL"
    assert "UNKNOWN" in result.violations
    assert t._eag_doc(result)["transformation_derivations_declared_not_resolved"] == []


def test_r3_unreportable_transformation_id_is_counted_not_silently_dropped():
    base = t._eag_fixture(presence=True)
    ev = replace(base.evidence[0], derivation_reference=Reference("X" * 200, "TRANSFORMATION"))
    result = t.run("R3-LONG", replace(base, evidence=(ev,)))
    doc = t._eag_doc(result)
    assert doc["transformation_derivations_declared_not_resolved"] == []
    assert doc["transformation_derivations_unreportable_count"] == 1


_EXTRA_KEYS = (
    "transformation_derivations_declared_not_resolved",
    "transformation_derivations_truncated",
    "transformation_derivations_unreportable_count",
)


@pytest.mark.parametrize("pos", [0, 15, 16, 17, 31, 62, 63])
def test_r1_full_digest_equality_any_single_position(pos):
    canonical = "ab" * 32
    chars = list(canonical)
    chars[pos] = "0" if chars[pos] != "0" else "1"
    replacement = "".join(chars)
    assert len(canonical) == len(replacement) == 64 and canonical != replacement
    candidate = t.f05_candidate("CANON-POS", "REPL-POS", canonical, replacement)
    result = t.run("R1POS", AuditInput(historical_mutation_candidates=(candidate,)),
                   ("M0-1.0", "M0-F05-1.0"))
    assert "HISTORY_MUTATION" in result.violations


def _r2_event(fidelity, declared_type, observed_type, ident):
    return RetrievalEvent(
        retrieval_id=f"RETRIEVAL-{ident}",
        source_reference=t.ref(f"SOURCE-{ident}"),
        retrieved_reference=t.ref(f"RETRIEVED-{ident}"),
        retrieval_timestamp=t.TS,
        transformation_reference=Reference("SAME", declared_type),
        fidelity_status=fidelity,
        provenance=t.prov(f"PROV-{ident}"),
        observed_transformation_reference=Reference("SAME", observed_type),
    )


def test_r2_type_difference_is_a_discrepancy_even_when_fidelity_is_faithful():
    result = t.run("R2B", AuditInput(retrieval_events=(
        _r2_event("FAITHFUL", "TRANSFORMATION", "OTHER_TYPE", "R2B"),)))
    assert "RETRIEVAL_DISCREPANCY" in result.violations


def test_r2_identical_references_are_not_a_discrepancy_whatever_the_fidelity_label():
    result = t.run("R2C", AuditInput(retrieval_events=(
        _r2_event("CORRUPT", "TRANSFORMATION", "TRANSFORMATION", "R2C"),)))
    assert "RETRIEVAL_DISCREPANCY" not in result.violations


def test_r3_cap_of_64_ids_sets_truncated_and_keeps_sorted_prefix():
    base = t._eag_fixture(presence=True)
    items = tuple(
        replace(base.evidence[0], evidence_id=f"EAG-X{i:03d}",
                independence_status=t.IndependenceStatus.DEPENDENT,
                derivation_reference=Reference(f"D{i:03d}", "TRANSFORMATION"))
        for i in range(65))
    for count, truncated in ((64, False), (65, True)):
        result = t.run(f"R3CAP{count}", replace(base, evidence=items[:count]))
        doc = t._eag_doc(result)
        listed = doc["transformation_derivations_declared_not_resolved"]
        assert listed == [f"D{i:03d}" for i in range(min(count, 64))]
        assert doc["transformation_derivations_truncated"] is truncated


def _near_cap_artifacts(n, k):
    base = t._eag_fixture(presence=True)
    first = base.assessments[0]
    items = tuple(replace(first, assessment_id=f"{i:04d}" + "b" * k) for i in range(n))
    return replace(base, assessments=items)


def test_r4_new_keys_never_change_whether_the_report_overflows():
    engine = AuditEngine()
    limit = engine.MAX_ANCESTRY_REPORT_BYTES
    omitted_while_fitting = 0
    for k in range(60, 101, 4):
        artifacts = _near_cap_artifacts(160, k)
        _, report = _EvidenceAncestryGuard(artifacts, engine).evaluate()
        base = {key: val for key, val in report.items() if key not in _EXTRA_KEYS}
        base_overflows = _serialize_ancestry_report(base, [], limit)[1]
        result = t.run(f"R4-{k}", artifacts)
        doc = t._eag_doc(result)
        assert doc["report_complete"] is (not base_overflows)
        assert ("UNKNOWN" in result.violations) == base_overflows
        if not base_overflows and _EXTRA_KEYS[0] not in doc:
            omitted_while_fitting += 1
            assert result.verdict == "PASS"
    assert omitted_while_fitting >= 1, "boundary not exercised; retune ids"


def _rewrite_basis(result, mutate):
    doc = t._eag_doc(result)
    mutate(doc)
    encoded = json.dumps(doc, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False)
    return result.verdict_basis[:result.verdict_basis.index(EAG_FINDINGS_BEGIN)] \
        + EAG_FINDINGS_BEGIN + encoded + EAG_FINDINGS_END


@pytest.mark.parametrize("key,bad", [
    ("transformation_derivations_declared_not_resolved", "not-a-list"),
    ("transformation_derivations_declared_not_resolved", [1, 2]),
    ("transformation_derivations_declared_not_resolved", ["x"] * 65),
    ("transformation_derivations_truncated", "yes"),
    ("transformation_derivations_unreportable_count", {"a": 1}),
    ("transformation_derivations_unreportable_count", -1),
    ("transformation_derivations_unreportable_count", True),
    ("transformation_derivations_unreportable_count", 1.0),
    ("transformation_derivations_unreportable_count", 4097),
    ("transformation_derivations_truncated", 1),
    ("transformation_derivations_truncated", True),   # True needs exactly 64 ids
    ("transformation_derivations_declared_not_resolved", [""]),
    ("transformation_derivations_declared_not_resolved", [" "]),
    ("transformation_derivations_declared_not_resolved", ["x" * 129]),
    ("transformation_derivations_declared_not_resolved", ["B", "A"]),
    ("transformation_derivations_declared_not_resolved", ["A", "A"]),
])
def test_r5_parser_rejects_malformed_new_keys(key, bad):
    result = t.run("R5", t._eag_fixture(presence=True))
    good = _rewrite_basis(result, lambda d: None)
    assert parse_evidence_ancestry_findings(good)[_EXTRA_KEYS[0]] == ["EAG-PROCEDURE"]
    with pytest.raises(ValueError):
        parse_evidence_ancestry_findings(_rewrite_basis(result, lambda d: d.__setitem__(key, bad)))


@pytest.mark.parametrize("suffix_a,suffix_b", [("", "z"), ("q", "p")])
def test_r1_difference_beyond_index_64_is_a_mutation(suffix_a, suffix_b):
    head = "ab" * 32  # 64 identical characters
    candidate = t.f05_candidate("CANON-LONG", "REPL-LONG", head + suffix_a + "-end", head + suffix_b + "-end")
    result = t.run("R1LONG", AuditInput(historical_mutation_candidates=(candidate,)),
                   ("M0-1.0", "M0-F05-1.0"))
    assert "HISTORY_MUTATION" in result.violations


def test_r1_whitespace_only_difference_is_a_mutation():
    candidate = t.f05_candidate("CANON-WS", "REPL-WS", "ab" * 32, "ab" * 32 + " ")
    result = t.run("R1WS", AuditInput(historical_mutation_candidates=(candidate,)),
                   ("M0-1.0", "M0-F05-1.0"))
    assert "HISTORY_MUTATION" in result.violations


def test_r3_shared_transformation_id_is_listed_once_and_does_not_truncate():
    base = t._eag_fixture(presence=True)
    items = tuple(
        replace(base.evidence[0], evidence_id=f"EAG-S{i:03d}",
                independence_status=t.IndependenceStatus.DEPENDENT,
                derivation_reference=Reference("SAME", "TRANSFORMATION"))
        for i in range(65))
    doc = t._eag_doc(t.run("R3SAME", replace(base, evidence=items)))
    assert doc["transformation_derivations_declared_not_resolved"] == ["SAME"]
    assert doc["transformation_derivations_truncated"] is False


def test_r4_gate_is_tight_at_every_offset_near_the_cap():
    """The keys are added iff base + keys fits; checked at every 1-byte offset
    across a window wider than the keys themselves (about 164 bytes)."""
    engine = AuditEngine()
    limit = engine.MAX_ANCESTRY_REPORT_BYTES
    extras = {_EXTRA_KEYS[0]: ["EAG-PROCEDURE"], _EXTRA_KEYS[1]: False, _EXTRA_KEYS[2]: 0}
    saw_omitted = saw_included = False
    for shorten in range(0, 158):
        base_art = _near_cap_artifacts(160, 80)
        cut_first = min(shorten, 79)
        cut_second = shorten - cut_first
        first = replace(base_art.assessments[0], assessment_id="0000" + "b" * (80 - cut_first))
        second = replace(base_art.assessments[1], assessment_id="0001" + "b" * (80 - cut_second))
        artifacts = replace(base_art, assessments=(first, second) + base_art.assessments[2:])
        _, report = _EvidenceAncestryGuard(artifacts, engine).evaluate()
        base = {k: v for k, v in report.items() if k not in _EXTRA_KEYS}
        base_over = _serialize_ancestry_report(base, [], limit)[1]
        with_over = _serialize_ancestry_report(dict(base, **extras), [], limit)[1]
        has_keys = _EXTRA_KEYS[0] in report
        assert has_keys == (not with_over), f"shorten={shorten}"
        if not base_over:
            result = t.run(f"R4T-{shorten}", artifacts)
            assert t._eag_doc(result)["report_complete"] is True, f"shorten={shorten}"
            saw_omitted |= not has_keys
            saw_included |= has_keys
    assert saw_omitted and saw_included


def test_r5_truncation_flag_must_be_a_real_bool_even_with_64_ids():
    result = t.run("R5T", t._eag_fixture(presence=True))
    ids = [f"D{i:03d}" for i in range(64)]

    def with_flag(flag):
        def mutate(d):
            d[_EXTRA_KEYS[0]] = ids
            d[_EXTRA_KEYS[1]] = flag
        return _rewrite_basis(result, mutate)

    assert parse_evidence_ancestry_findings(with_flag(True))[_EXTRA_KEYS[1]] is True
    assert parse_evidence_ancestry_findings(with_flag(False))[_EXTRA_KEYS[1]] is False
    for bad in (1, 0, "true", None):
        with pytest.raises(ValueError):
            parse_evidence_ancestry_findings(with_flag(bad))
