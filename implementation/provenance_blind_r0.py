"""Ario PR-CI provenance R0: synthetic, fail-closed evaluator boundary.

No secrets, network, filesystem writes, trust activation or cryptographic claims.
A = actual pinned witness_provenance_experiment.evaluate_provenance, with a
synthetic-case adapter. B = actual pinned v0.8 parser + separate research-only
execution/source diagnostic. C = NEW research-only time/revocation diagnostic.
LAB_CONDITIONALLY_* never means external authentication or admitted evidence.
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

# On the stacked research PR, exercise the actual imported Ario modules.
# The test helper supplies a SYNTHETIC graph (never verified custody).
IMPLEMENTATION = Path(__file__).resolve().parent
TESTS = IMPLEMENTATION / "tests"
for x in (str(IMPLEMENTATION), str(TESTS)):
    if x not in sys.path:
        sys.path.insert(0, x)

import witness_provenance_experiment as provenance
from test_witness_provenance_experiment import baseline as graph_baseline
import pr_claim_audit_log_parser_v0_8 as pr_v08

SCHEMA = "ARIO-PR-CI-PROVENANCE-BLIND-R0.1"
TEST_HEAD = "a67c63934a4a0a993fc14032ad29920cc970807f"
RUN_ID = 44123481398
JOB_ID = 134180830525
CMD = "python -m pytest -q tests"
LOG = "\n".join((
    "2026-11-17T16:14:44.0507715Z Successfully set up CPython (3.13.18)",
    "2026-11-17T16:14:51.1730758Z ##[group]Run python -m pytest -q tests",
    "2026-11-17T16:14:58.5347756Z 1253 passed, 2 skipped, 2 warnings, 124 subtests passed in 6.36s",
))
MAX_BYTES = 24000


def _result(case_id: str, domain: str, **fields: object) -> dict:
    return {"schema": SCHEMA, "case_id": case_id, "domain": domain, "status": "UNKNOWN",
            "execution_attestation": "NOT_ESTABLISHED", "evidence_admission": "NOT_EVALUATED",
            "source_provenance": "UNVERIFIED", **fields}


def _forbid_hidden(obj: object) -> None:
    # Explicit boundary: fixture-only oracle truth must not reach evaluator.
    if isinstance(obj, dict):
        if any(k in obj for k in ("oracle", "ground_truth", "hidden_truth", "expected", "secret")):
            raise ValueError("oracle disclosure in observable input")
        for v in obj.values():
            _forbid_hidden(v)
    elif isinstance(obj, list):
        for v in obj:
            _forbid_hidden(v)


def _a(f: dict, case_id: str) -> dict:
    if set(f) != {"shared_admin", "shared_source", "graph_origin", "complete_control", "complete_sources"}:
        raise ValueError("invalid A fields")
    if (any(type(f[k]) is not bool for k in ("shared_admin", "shared_source", "complete_control", "complete_sources"))
            or f["graph_origin"] not in ("LAB_FROZEN", "CANDIDATE_DECLARED")):
        raise ValueError("invalid A field values")
    case = graph_baseline(shared_admin=f["shared_admin"], shared_source=f["shared_source"])
    case = replace(case,
        graph=replace(case.graph, origin=provenance.LAB if f["graph_origin"] == "LAB_FROZEN" else provenance.CANDIDATE),
        complete_control_surface=f["complete_control"],
        complete_source_surface=f["complete_sources"],
        completeness_origin=provenance.LAB if f["graph_origin"] == "LAB_FROZEN" else provenance.CANDIDATE,
    )
    report = provenance.evaluate_provenance(case)  # Existing Ario engine, not our substitute
    admin, source = report.administrative_separation.status, report.source_independence.status
    if admin in ("COMMON_CONTROL_DETECTED", "SAME_STORAGE_OBJECT") or source == "COMMON_SOURCE_DETECTED":
        label = "LAB_DEPENDENCE_OBSERVED"
    elif admin == "LAB_CONDITIONALLY_SEPARATE" and source == "LAB_CONDITIONALLY_DISTINCT":
        label = "LAB_CONDITIONALLY_SEPARATE"
    else:
        label = "UNKNOWN"
    return _result(case_id, "A", independence=label, admin_diagnostic=admin,
                   source_diagnostic=source, custody_authenticity=report.production_custody_authenticity,
                   provenance_input_basis="LAB_ASSUMED_ONLY" if f["graph_origin"] == "LAB_FROZEN" else "SELF_DECLARED")


def _b(f: dict, case_id: str) -> dict:
    valid = {"workflow_steps", "artifact_signature_claim", "log_text", "observed_receipt", "claimed_head"}
    if set(f) != valid or not isinstance(f["workflow_steps"], list) or not all(type(x) is str for x in f["workflow_steps"]):
        raise ValueError("invalid B fields")
    if (not isinstance(f["artifact_signature_claim"], str)
        or not isinstance(f["log_text"], str) or len(f["log_text"]) > 10000
        or f["claimed_head"] not in (TEST_HEAD, "f" * 40)):
        raise ValueError("invalid B values")
    claim = {"schema": "ARIO-PR-CI-0.1", "head_sha": TEST_HEAD,
             "run_id": RUN_ID, "run_attempt": 1, "job_id": JOB_ID,
             "python_version": "3.13.18", "pytest_command": CMD,
             "passed": 1253, "failed": 0, "skipped": 2, "subtests_passed": 124,
             "job_conclusion": "success"}
    claim_text = "<!-- ARIO-CI-CLAIM-V0.1\n" + json.dumps(claim) + "\nARIO-CI-CLAIM-V0.1 -->"
    evidence = {"run": {"id": RUN_ID, "run_attempt": 1, "head_sha": f["claimed_head"], "status": "completed", "event": "pull_request", "conclusion": "success"},
                "job": {"id": JOB_ID, "run_id": RUN_ID, "run_attempt": 1, "head_sha": f["claimed_head"], "status": "completed", "name": "m0-regression", "conclusion": "success"},
                "job_log": f["log_text"], "job_log_complete": True,
                "job_log_sha256": hashlib.sha256(f["log_text"].encode("utf-8")).hexdigest()}
    parsed = pr_v08.assess(claim_text, evidence)  # Existing real v0.8 code
    # The next two fields are EXPERIMENTAL scope diagnostics, not v0.8 features.
    declared_workflow = "DECLARED_PYTEST_STEP" if CMD in f["workflow_steps"] else "NO_PYTEST_STEP_DECLARED"
    receipt = f["observed_receipt"]
    if receipt is not None and (not isinstance(receipt, dict) or
        set(receipt) != {"basis", "head", "command", "job", "separate_controller"}):
        raise ValueError("invalid observer receipt")
    is_lab_receipt = bool(isinstance(receipt, dict)
        and receipt.get("basis") == "LAB_FROZEN_SIMULATION"
        and receipt.get("head") == TEST_HEAD
        and receipt.get("command") == CMD
        and receipt.get("job") == JOB_ID
        and receipt.get("separate_controller") is True
        and declared_workflow == "DECLARED_PYTEST_STEP"
        and f["claimed_head"] == TEST_HEAD)
    execution_observation = "LAB_CONDITIONALLY_OBSERVED" if is_lab_receipt else "UNKNOWN"
    return _result(case_id, "B", claim_correspondence=parsed["claim_correspondence"],
                   workflow_step_diagnostic=declared_workflow,
                   artifact_authenticity="NOT_VERIFIED_SELF_CLAIM_ONLY",
                   execution_observation=execution_observation,
                   parser_final_status=parsed["status"],
                   parser_execution_attestation=parsed["execution_attestation"])


def _c(f: dict, case_id: str) -> dict:
    keys = {"receipts", "current_head", "current_attempt", "revocations", "evaluation_sequence", "lab_inventory_complete"}
    if set(f) != keys or not isinstance(f["receipts"], list) or not isinstance(f["revocations"], list):
        raise ValueError("invalid C fields")
    if (not isinstance(f["current_head"], str) or type(f["current_attempt"]) is not int
        or type(f["evaluation_sequence"]) is not int or type(f["lab_inventory_complete"]) is not bool
        or not (0 <= f["evaluation_sequence"] <= 10000) or len(f["receipts"]) > 12
        or len(f["revocations"]) > 12):
        raise ValueError("invalid C values")
    receipt_ids: list[str] = []
    for rec in f["receipts"]:
        if (not isinstance(rec, dict) or set(rec) != {"id", "head", "attempt", "witness", "issue_sequence", "basis"}
            or not isinstance(rec["id"], str) or type(rec["attempt"]) is not int
            or type(rec["issue_sequence"]) is not int
            or rec["basis"] not in ("LAB_FROZEN", "SELF_DECLARED")):
            raise ValueError("invalid receipt")
        receipt_ids.append(rec["id"])
    if len(set(receipt_ids)) != len(receipt_ids):
        raise ValueError("duplicate receipt ids")
    for rev in f["revocations"]:
        if (not isinstance(rev, dict) or set(rev) != {"witness", "effective_sequence", "scope", "basis"}
            or type(rev["effective_sequence"]) is not int
            or rev["basis"] not in ("LAB_FROZEN", "SELF_DECLARED")):
            raise ValueError("invalid revocation")
    candidates = [r for r in f["receipts"] if r["head"] == f["current_head"] and r["attempt"] == f["current_attempt"]]
    valid_candidates = []
    for r in candidates:
        if r["basis"] != "LAB_FROZEN" or not f["lab_inventory_complete"]:
            continue
        related = [v for v in f["revocations"] if v["witness"] == r["witness"] and v["scope"] == "pr-ci"]
        if any(v["basis"] != "LAB_FROZEN" for v in related):
            continue
        if any(v["effective_sequence"] <= f["evaluation_sequence"] for v in related):
            continue
        if r["issue_sequence"] > f["evaluation_sequence"]:
            continue
        valid_candidates.append(r["id"])
    label = "LAB_CONDITIONALLY_CURRENT" if valid_candidates else "UNRESOLVED"
    return _result(case_id, "C", current_state=label, historical_receipts=receipt_ids,
                   matched_current_receipts=valid_candidates,
                   revocation_effect="NOT_INFERRED_FROM_UNAUTHENTICATED_TIME",
                   history_preserved=True)


def evaluate(observation: dict) -> dict:
    try:
        _forbid_hidden(observation)
        if (type(observation) is not dict or set(observation) != {"case_id", "domain", "facts"}
            or not isinstance(observation["case_id"], str) or len(observation["case_id"]) > 80
            or type(observation["facts"]) is not dict):
            raise ValueError("invalid observable envelope")
        domain = observation["domain"]
        if domain == "A": return _a(observation["facts"], observation["case_id"])
        if domain == "B": return _b(observation["facts"], observation["case_id"])
        if domain == "C": return _c(observation["facts"], observation["case_id"])
        raise ValueError("invalid domain")
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        return {"schema": SCHEMA, "case_id": observation.get("case_id") if isinstance(observation, dict) else None,
                "domain": observation.get("domain") if isinstance(observation, dict) else None,
                "status": "UNKNOWN", "execution_attestation": "NOT_ESTABLISHED",
                "evidence_admission": "NOT_EVALUATED", "source_provenance": "UNVERIFIED",
                "reason": "INVALID_OR_UNSUPPORTED_OBSERVATION"}


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        out = evaluate(None)
    else:
        try:
            out = evaluate(json.loads(raw.decode("utf-8")))
        except (UnicodeError, ValueError, TypeError):
            out = evaluate(None)
    sys.stdout.write(json.dumps(out, ensure_ascii=True, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
