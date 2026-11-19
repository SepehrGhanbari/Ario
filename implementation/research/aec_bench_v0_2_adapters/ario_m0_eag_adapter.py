"""Direct synthetic probes of Ario's actual M0-1.2 / M0-EAG-0.1 runtime.

This is a separate, bounded runtime profile, not a reimplementation of M0 and
not a forced mapping of every generic AEC fixture to unsupported semantics.
"""
from __future__ import annotations

from typing import Any

from core.audit_engine import AuditEngine, AuditInput, parse_evidence_ancestry_findings
from core.schema import (
    Assessment, AuditResult, Claim, EpistemicStatus, Evidence, EvidenceUse,
    IndependenceStatus, ObservationRecord, Reference, SchemaVersion,
    SupportTarget, Timestamp,
)

ENGINE_VERSION = AuditEngine.INSPECTOR_VERSION
STAMP = Timestamp("2026-11-15T00:00:00Z")


def ref(identifier: str, kind: str) -> Reference:
    return Reference(identifier, kind)


def claim(identifier: str, status: EpistemicStatus = EpistemicStatus.UNKNOWN) -> Claim:
    return Claim(identifier, SchemaVersion("M0-1.0"), STAMP,
                 ref("DECL-" + identifier, "DECLARATION"), status)


def target(identifier: str = "M0-C1", kind: str = "CLAIM", presence: bool = False) -> SupportTarget:
    return SupportTarget(ref(identifier, kind),
                         "SUPPLIED_RECORD_PRESENT" if presence else "SYNTHETIC_PROPERTY")


def observation(identifier: str, subject: SupportTarget, parents=(), *,
                use=EvidenceUse.INDEPENDENT_TARGET_SUPPORT,
                version="M0-EAG-OBSERVATION-0.1") -> ObservationRecord:
    return ObservationRecord(identifier, version, subject, use, tuple(parents))


def evidence(identifier: str, obs_ids: tuple[str, ...],
             independence=IndependenceStatus.INDEPENDENT) -> Evidence:
    return Evidence(identifier, tuple(ref(x, "OBSERVATION") for x in obs_ids),
                    "SYNTHETIC_DECLARATION", independence,
                    ref("PROC-" + identifier, "TRANSFORMATION"), "SYNTHETIC-M0")


def assessment(subject: SupportTarget, evidence_ids=("M0-E1",), *,
               use=EvidenceUse.INDEPENDENT_TARGET_SUPPORT,
               rule="M0-EAG-0.1", scope="SYNTHETIC-M0") -> Assessment:
    return Assessment("M0-A1", "1", rule,
                      tuple(ref(x, "EVIDENCE") for x in evidence_ids),
                      "SYNTHETIC_REQUEST", "No authenticated source", scope,
                      subject, use)


def known_audit_result(identifier="M0-R0") -> AuditResult:
    return AuditResult(identifier, "M0-PROBE", "1", STAMP, "SYNTHETIC-M0",
                       ("M0-1.0",), (), (), "PASS",
                       "Synthetic prior audit result; not evidence of truth.")


def run(artifacts: AuditInput, audit_id: str) -> dict[str, Any]:
    result = AuditEngine().audit(
        artifacts, rule_versions=("M0-1.0",), configuration_id="AEC-M0-PROBE",
        execution_timestamp=STAMP, audit_id=audit_id,
    )
    findings = parse_evidence_ancestry_findings(result.verdict_basis)
    row = findings["assessments"][0] if findings["assessments"] else None
    return {
        "verdict": result.verdict,
        "violations": sorted(result.violations),
        "inspector_version": result.inspector_version,
        "candidate_ancestry": findings["candidate_ancestry"],
        "candidate_use": findings["candidate_use"],
        "claim_truth": findings["claim_truth"],
        "entity_continuity": findings["entity_continuity"],
        "independent_admission_authority": findings["independent_admission_authority"],
        "report_complete": findings["report_complete"],
        "assessment": row,
    }


def base(*, subject=None, parents=(), source_claims=(), obs_use=EvidenceUse.INDEPENDENT_TARGET_SUPPORT,
         obs_version="M0-EAG-OBSERVATION-0.1", obs_ids=("M0-O1",),
         obs_parent_rows=None, evidence_rows=None, assessment_row=None,
         include_assessment=True, prior_results=()) -> AuditInput:
    subject = subject or target()
    claims = (claim(subject.subject_reference.reference_id),) + tuple(source_claims)
    if obs_parent_rows is None:
        obs_parent_rows = [(oid, tuple(parents)) for oid in obs_ids]
    observations = tuple(
        observation(oid, subject, row_parents, use=obs_use, version=obs_version)
        for oid, row_parents in obs_parent_rows
    )
    if evidence_rows is None:
        evidence_rows = [(f"M0-E{i+1}", (oid,), IndependenceStatus.INDEPENDENT)
                         for i, oid in enumerate(obs_ids)]
    evidences = tuple(evidence(eid, ids, independence) for eid, ids, independence in evidence_rows)
    if assessment_row is None and include_assessment:
        assessment_row = assessment(subject, tuple(eid for eid, _, _ in evidence_rows))
    return AuditInput(
        claims=claims, observations=observations, evidence=evidences,
        assessments=(assessment_row,) if assessment_row is not None else (),
        prior_audit_results=tuple(prior_results),
    )


def _case(case_id: str, artifacts: AuditInput, expected: dict[str, Any]) -> dict[str, Any]:
    observed = run(artifacts, case_id)
    checks = []
    for key, value in expected.items():
        if key == "required_violations":
            checks.append(set(value).issubset(observed["violations"]))
        elif key == "forbidden_violations":
            checks.append(not (set(value) & set(observed["violations"])))
        elif key == "assessment_fields":
            row = observed["assessment"] or {}
            checks.append(all(row.get(k) == v for k, v in value.items()))
        else:
            checks.append(observed.get(key) == value)
    return {
        "case_id": case_id,
        "expected_predicates": expected,
        "observed": observed,
        "predicates_match": all(checks),
        "runtime_identity": "ACTUAL_REPOSITORY_AUDIT_ENGINE",
    }


def build_m0_probe_report() -> dict[str, Any]:
    cases = []
    # Exact positive control is only supplied-record presence, never claim truth.
    ptarget = target(presence=True)
    pobs = observation("M0-O1", ptarget, (ref("M0-C1", "CLAIM"),),
                       use=EvidenceUse.RECORD_DESCRIPTION)
    passessment = assessment(ptarget, use=EvidenceUse.RECORD_DESCRIPTION,
                             rule="M0-EAG-RECORD-PRESENCE-0.1",
                             scope="SUPPLIED_INPUT_RECORDS_ONLY")
    cases.append(_case("M0_EAG_01_RECORD_PRESENCE",
        base(subject=ptarget, obs_parent_rows=[("M0-O1", pobs.provenance_refs)],
             obs_use=EvidenceUse.RECORD_DESCRIPTION, assessment_row=passessment),
        {"verdict":"PASS","claim_truth":"UNKNOWN","candidate_use":"NOT_EVALUATED",
         "assessment_fields":{"record_presence":"MATCH","use_disposition":"RECORD_DESCRIPTION_ONLY",
                              "source_authentication":"UNKNOWN"}}))

    # Traceable graph does not grant independent support.
    cases.append(_case("M0_EAG_02_NO_ADMISSION_AUTHORITY",
        base(), {"verdict":"FAIL","required_violations":["UNKNOWN"],
                 "candidate_ancestry":"TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT",
                 "claim_truth":"UNKNOWN",
                 "assessment_fields":{"use_disposition":"UNKNOWN",
                                      "source_authentication":"UNKNOWN"}}))

    # Exact self-confirmation is a known inadmissibility.
    cases.append(_case("M0_EAG_03_EXACT_SELF_CONFIRMATION",
        base(parents=(ref("M0-C1","CLAIM"),)),
        {"verdict":"FAIL","required_violations":["EVIDENCE_INADMISSIBLE"],
         "assessment_fields":{"use_disposition":"KNOWN_INADMISSIBLE"}}))

    # A distinct claim is traceable; it is not the assessment's target.
    cases.append(_case("M0_EAG_04_DISTINCT_CLAIM_ANCESTRY",
        base(parents=(ref("M0-C0","CLAIM"),),
             source_claims=(claim("M0-C0",EpistemicStatus.UNSUPPORTED),)),
        {"verdict":"FAIL","required_violations":["UNKNOWN"],
         "forbidden_violations":["EVIDENCE_INADMISSIBLE","COMPOSITION_FORBIDDEN"],
         "candidate_ancestry":"TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT",
         "assessment_fields":{"ancestry":"TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT",
                              "use_disposition":"UNKNOWN"}}))

    # Two fresh observations/evidence wrappers share the same supplied root.
    shared = target()
    shared_claim = claim("M0-C0")
    shared_obs = (("M0-O1",(ref("M0-C0","CLAIM"),)),
                  ("M0-O2",(ref("M0-C0","CLAIM"),)))
    shared_ev = (("M0-E1",("M0-O1",),IndependenceStatus.INDEPENDENT),
                 ("M0-E2",("M0-O2",),IndependenceStatus.INDEPENDENT))
    shared_assessment = assessment(shared,("M0-E1","M0-E2"))
    cases.append(_case("M0_EAG_05_SHARED_SOURCE_INFLATION",
        base(subject=shared,source_claims=(shared_claim,),obs_ids=("M0-O1","M0-O2"),
             obs_parent_rows=shared_obs,evidence_rows=shared_ev,
             assessment_row=shared_assessment),
        {"verdict":"FAIL","required_violations":["EVIDENCE_INFLATION","UNKNOWN"],
         "assessment_fields":{"use_disposition":"UNKNOWN"}}))

    # Missing ancestry remains UNKNOWN.
    cases.append(_case("M0_EAG_06_MISSING_ANCESTOR",
        base(parents=(ref("M0-MISSING","OBSERVATION"),)),
        {"verdict":"FAIL","required_violations":["UNKNOWN"],
         "candidate_ancestry":"UNKNOWN",
         "assessment_fields":{"ancestry":"UNKNOWN","use_disposition":"UNKNOWN"}}))

    # Forbidden and missing branches are retained together.
    cases.append(_case("M0_EAG_07_FORBIDDEN_PLUS_MISSING",
        base(parents=(ref("M0-FORBIDDEN","AUDIT_RESULT"),
                      ref("M0-MISSING","OBSERVATION"))),
        {"verdict":"FAIL","required_violations":["COMPOSITION_FORBIDDEN","UNKNOWN"],
         "candidate_ancestry":"UNKNOWN"}))

    # A known prior audit result is screenable but cannot become evidence.
    cases.append(_case("M0_EAG_08_KNOWN_FORBIDDEN_RESULT",
        base(parents=(ref("M0-R0","AUDIT_RESULT"),),
             prior_results=(known_audit_result(),)),
        {"verdict":"FAIL","required_violations":["COMPOSITION_FORBIDDEN"],
         "forbidden_violations":["EVIDENCE_INADMISSIBLE"],
         "candidate_ancestry":"TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT"}))

    # Candidate-only observation can pass structural inspection while use remains unevaluated.
    ctarget = target()
    cases.append(_case("M0_EAG_09_CANDIDATE_ONLY",
        base(subject=ctarget,parents=(ref("M0-C1","CLAIM"),),include_assessment=False,
             evidence_rows=()),
        {"verdict":"PASS","candidate_ancestry":"TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT",
         "candidate_use":"NOT_EVALUATED","assessment":None}))

    # Duplicate same-typed observation identifiers are ambiguous.
    dtarget = target(presence=True)
    dobs = observation("M0-O1",dtarget,use=EvidenceUse.RECORD_DESCRIPTION)
    dassessment = assessment(dtarget,use=EvidenceUse.RECORD_DESCRIPTION,
                             rule="M0-EAG-RECORD-PRESENCE-0.1",
                             scope="SUPPLIED_INPUT_RECORDS_ONLY")
    cases.append(_case("M0_EAG_10_DUPLICATE_OBSERVATION",
        base(subject=dtarget,obs_parent_rows=(("M0-O1",()),("M0-O1",())),
             obs_use=EvidenceUse.RECORD_DESCRIPTION,assessment_row=dassessment),
        {"verdict":"FAIL","required_violations":["UNKNOWN"],
         "candidate_ancestry":"UNKNOWN"}))

    # Unsupported observation record versions are unresolved.
    cases.append(_case("M0_EAG_11_UNSUPPORTED_RECORD_PROFILE",
        base(obs_version="M0-EAG-OBSERVATION-9.9"),
        {"verdict":"FAIL","required_violations":["UNKNOWN"],
         "candidate_ancestry":"UNKNOWN"}))

    # Exact target/use binding blocks description-to-support replay.
    desc_target = target(presence=True)
    desc_obs = observation("M0-O1",desc_target,use=EvidenceUse.RECORD_DESCRIPTION)
    support_target = target()
    cases.append(_case("M0_EAG_12_DESCRIPTION_REPLAY_AS_SUPPORT",
        AuditInput(claims=(claim("M0-C1"),),observations=(desc_obs,),
                   evidence=(evidence("M0-E1",("M0-O1",)),),
                   assessments=(assessment(support_target),)),
        {"verdict":"FAIL","required_violations":["UNKNOWN"],
         "assessment_fields":{"record_presence":"NOT_EVALUATED",
                              "use_disposition":"UNKNOWN"}}))

    return {
        "benchmark":"AEC-Bench-0.2-Ario-M0-EAG-runtime-probes",
        "runtime_identity":"ACTUAL_REPOSITORY_AUDIT_ENGINE",
        "engine_version":ENGINE_VERSION,
        "mandatory_guard":AuditEngine.ALWAYS_ON_ANCESTRY_VERSION,
        "case_count":len(cases),
        "predicate_matches":sum(case["predicates_match"] for case in cases),
        "cases":cases,
        "limitations":[
            "These probes call the repository's actual M0 AuditEngine; they do not reimplement EAG.",
            "They are a separate M0 runtime profile, not all 120 generic AEC fixtures.",
            "M0 does not expose a distinct-root count, source authentication, proposition truth, or general independent-admission authorization.",
            "All fixtures and expected predicates are synthetic and author-authored; independent oracle review remains NOT RUN.",
        ],
    }
