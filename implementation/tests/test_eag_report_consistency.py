"""Report consistency regression for #75; parsing never authenticates evidence."""
import json

import pytest

from core.audit_engine import (
    EAG_FINDINGS_BEGIN, EAG_FINDINGS_END, parse_evidence_ancestry_findings,
)


def report():
    return {
        "profile": "M0-EAG-0.1",
        "mandatory_guards": ["M0-REF-GUARD-1.0", "M0-EAG-0.1"],
        "independent_admission_authority": "NONE",
        "candidate_use": "NOT_EVALUATED",
        "candidate_ancestry": "TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT",
        "claim_truth": "UNKNOWN",
        "entity_continuity": "UNKNOWN",
        "report_complete": True,
        "assessments": [{
            "assessment_id": "A",
            "target": {"reference_id": "C", "reference_type": "CLAIM"},
            "property_id": "SUPPLIED_RECORD_PRESENT",
            "requested_use": "RECORD_DESCRIPTION",
            "ancestry": "TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT",
            "record_presence": "MATCH",
            "use_disposition": "RECORD_DESCRIPTION_ONLY",
            "source_authentication": "UNKNOWN",
            "reasons": [],
        }],
    }


def parse(data):
    return parse_evidence_ancestry_findings(
        EAG_FINDINGS_BEGIN
        + json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
        + EAG_FINDINGS_END
    )


@pytest.mark.parametrize("delta", [
    {"record_presence": "NOT_EVALUATED"},
    {"record_presence": "UNKNOWN"},
    {"ancestry": "UNKNOWN"},
    {"assessment_id": None},
    {"reasons": ["PROTECTED_RESULT_ID_COLLISION"]},
])
def test_inconsistent_positive_description_rejected(delta):
    data = report()
    data["assessments"][0].update(delta)
    with pytest.raises(ValueError, match="description disposition inconsistent"):
        parse(data)


@pytest.mark.parametrize("delta", [
    {},
    {"use_disposition": "UNKNOWN", "ancestry": "UNKNOWN",
     "reasons": ["ANCESTRY_UNRESOLVED"]},
    {"use_disposition": "UNKNOWN", "record_presence": "NOT_EVALUATED",
     "assessment_id": None, "reasons": ["MISSING_OR_UNREPORTABLE_TARGET_USE"]},
])
def test_legitimate_reports_preserved(delta):
    data = report()
    data["assessments"][0].update(delta)
    assert parse(data) == data
