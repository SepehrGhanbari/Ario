"""Bounded synthetic inputs to the real M0 JSON runtime; no admission authority.

Run from the repository root with Python 3.13:
    python -B implementation/m0_reproducibility_demo.py
    python -B implementation/m0_reproducibility_demo.py --inputs

All identifiers, labels and the fixed timestamp are fixture declarations. The
timestamp is not a measurement or evidence that an event actually occurred.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json

from ario_cli import execute_request
from core.audit_engine import AuditInput, parse_evidence_ancestry_findings
from core.schema import (
    Assessment,
    Claim,
    EpistemicStatus,
    Evidence,
    EvidenceUse,
    IndependenceStatus,
    ObservationRecord,
    Reference,
    SchemaVersion,
    SupportTarget,
    Timestamp,
)


FIXTURE_TIMESTAMP = "2026-10-17T00:00:00Z"
CONFIGURATION_ID = "M0-REPRODUCIBILITY-DEMO-1"


def _fixture(*, presence: bool) -> AuditInput:
    """One claim, observation, evidence wrapper and assessment; no external I/O."""
    claim_ref = Reference("DEMO-C1", "CLAIM")
    target = SupportTarget(
        claim_ref, "SUPPLIED_RECORD_PRESENT" if presence else "SYNTHETIC_PROPERTY"
    )
    use = (
        EvidenceUse.RECORD_DESCRIPTION
        if presence else EvidenceUse.INDEPENDENT_TARGET_SUPPORT
    )
    scope = "SUPPLIED_INPUT_RECORDS_ONLY" if presence else "SYNTHETIC-DEMO"
    return AuditInput(
        claims=(Claim(
            claim_id=claim_ref.reference_id,
            schema_version=SchemaVersion("M0-1.0"),
            created_at=Timestamp(FIXTURE_TIMESTAMP),
            origin_reference=Reference("DEMO-ORIGIN", "DECLARATION"),
            status=EpistemicStatus.UNKNOWN,
        ),),
        observations=(ObservationRecord(
            observation_id="DEMO-O1",
            record_version="M0-EAG-OBSERVATION-0.1",
            target=target,
            declared_use=use,
            provenance_refs=(claim_ref,),
        ),),
        evidence=(Evidence(
            evidence_id="DEMO-E1",
            observation_refs=(Reference("DEMO-O1", "OBSERVATION"),),
            evidence_level="SYNTHETIC_DECLARATION",
            independence_status=IndependenceStatus.DEPENDENT,
            derivation_reference=Reference("DEMO-PROCEDURE", "TRANSFORMATION"),
            scope=scope,
        ),),
        assessments=(Assessment(
            assessment_id="DEMO-A1",
            assessment_version="1",
            rule_version=(
                "M0-EAG-RECORD-PRESENCE-0.1" if presence else "M0-EAG-0.1"
            ),
            admissible_evidence_refs=(Reference("DEMO-E1", "EVIDENCE"),),
            condition_evaluation="SYNTHETIC_REQUEST_ONLY",
            assessment_basis="Synthetic declaration; no authenticated source",
            scope=scope,
            target=target,
            requested_use=use,
        ),),
    )


def build_requests() -> dict[str, dict]:
    """Return fresh JSON-serializable requests accepted by ario_cli.py."""
    fixtures = {
        "empty_input": AuditInput(),
        "record_presence": _fixture(presence=True),
        "self_support": _fixture(presence=False),
    }
    return {
        name: {
            "audit_id": f"DEMO-{name}",
            "rule_versions": ["M0-1.0"],
            "configuration_id": CONFIGURATION_ID,
            "execution_timestamp": FIXTURE_TIMESTAMP,
            "artifacts": json.loads(json.dumps(asdict(artifacts))),
        }
        for name, artifacts in fixtures.items()
    }


def run_demo() -> dict:
    """Preserve actual engine results and parse their engine-owned findings."""
    cases = []
    for name, request in build_requests().items():
        result = execute_request(request)
        cases.append({
            "case": name,
            "result": result,
            "ancestry_findings": parse_evidence_ancestry_findings(
                result["verdict_basis"]
            ),
        })
    return {"demo_version": "1", "cases": cases}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inputs", action="store_true",
        help="Print complete synthetic requests instead of executing the demo",
    )
    args = parser.parse_args(argv)
    output = build_requests() if args.inputs else run_demo()
    print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False))
    # Execution success is distinct from each case's structural audit verdict.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
