"""Opt-in bounded Ario agent + #290 offline PR-claim diagnostic.

Research only. Only the agent's explicit append-only ledger is written.
No core memory, M0, signer, trust or live network use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ario_agent import MAX_READ_BYTES, AgentRequestError, _inside, run_task
from pr_claim_audit import Invalid, _decode_json, assess

SCHEMA = "ARIO-SELF-AUDIT-ENGINE-0.1"
TASK_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}\Z")
LIMITATIONS = [
    "Both snapshots are caller-supplied and are not authenticated execution evidence",
    "Agent writes only the nominated append-only task ledger, not Ario memory",
    "File fingerprint and later read are not an atomic filesystem snapshot",
    "MATCH is correspondence, not truth, approval, or evidence admission",
    "No automatic execution by the normal engine, model, or CLI",
]


def _unknown(reason: str, *, agent_status: str = "NOT_RUN") -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "UNKNOWN",
        "claim_correspondence": "UNKNOWN",
        "reason": reason,
        "agent_task_status": agent_status,
        "source_delivery": "CALLER_SUPPLIED_LOCAL_FILES",
        "source_transport_status": "UNVERIFIED",
        "execution_attestation": "NOT_ESTABLISHED",
        "evidence_admission": "NOT_EVALUATED",
        "memory_updated": False,
        "trust_activated": False,
        "limitations": list(LIMITATIONS),
    }


def _checked_bytes(root: Path, relative: str, observation: Any) -> bytes:
    if not isinstance(observation, dict) or observation.get("ok") is not True:
        raise AgentRequestError("MISSING_AGENT_FINGERPRINT")
    path = _inside(root, relative)
    if path.is_symlink() or not path.is_file():
        raise AgentRequestError("LOCAL_INPUT_NOT_REGULAR")
    with path.open("rb") as stream:
        raw = stream.read(MAX_READ_BYTES + 1)
    if len(raw) > MAX_READ_BYTES:
        raise AgentRequestError("LOCAL_INPUT_EXCEEDS_AGENT_LIMIT")
    if (type(observation.get("bytes")) is not int
            or observation["bytes"] != len(raw)
            or observation.get("path") != relative
            or observation.get("sha256") != hashlib.sha256(raw).hexdigest()):
        raise AgentRequestError("INPUT_CHANGED_AFTER_AGENT_FINGERPRINT")
    return raw


def inspect_with_agent(
    *, workspace: str | Path, ledger: str | Path, task_id: str,
    pr_body: str, evidence: str,
) -> dict[str, Any]:
    """Run two real, read-only agent actions and a separate offline comparator.

    Always return top-level UNKNOWN, even if supplied snapshots match.
    """
    response = _unknown("UNASSESSED")
    try:
        if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
            raise AgentRequestError("INVALID_TASK_ID")
        root = Path(workspace).resolve()
        if not root.is_dir():
            raise AgentRequestError("WORKSPACE_NOT_FOUND")
        if not isinstance(pr_body, str) or not isinstance(evidence, str):
            raise AgentRequestError("INVALID_INPUT_PATH")
        claim_file = _inside(root, pr_body)
        evidence_file = _inside(root, evidence)
        ledger_file = Path(ledger).resolve()
        if claim_file == evidence_file or ledger_file in (claim_file, evidence_file):
            raise AgentRequestError("INPUT_PATH_COLLISION")
        task = {
            "task_id": task_id,
            "goal": "Fingerprint caller-supplied CI research snapshots, without source authority",
            "actions": [
                {"step_id": "claim", "tool": "file_fingerprint", "path": pr_body},
                {"step_id": "evidence", "tool": "file_fingerprint", "path": evidence},
            ],
        }
        agent = run_task(task, root, ledger_file)
        response["agent_task_status"] = agent.get("status", "UNKNOWN")
        if agent.get("status") != "COMPLETED":
            response["reason"] = "AGENT_FINGERPRINT_TASK_NOT_COMPLETED"
            return response
        steps = agent.get("steps", [])
        if len(steps) != 2 or any(step.get("status") != "SUCCEEDED" for step in steps):
            raise AgentRequestError("AGENT_STEP_INCOMPLETE")
        claim_bytes = _checked_bytes(root, pr_body, steps[0].get("observation"))
        evidence_bytes = _checked_bytes(root, evidence, steps[1].get("observation"))
        try:
            claim_text = claim_bytes.decode("utf-8-sig")
            evidence_data = _decode_json(evidence_bytes.decode("utf-8-sig"))
        except (Invalid, UnicodeError, ValueError, RecursionError) as exc:
            raise AgentRequestError("INVALID_LOCAL_SNAPSHOT") from exc
        if not isinstance(evidence_data, dict):
            raise AgentRequestError("EVIDENCE_NOT_OBJECT")
        diagnostic = assess(claim_text, evidence_data)
        correspondence = diagnostic.get("status", "UNKNOWN")
        response["claim_correspondence"] = (
            correspondence if correspondence in ("MATCH", "MISMATCH", "UNKNOWN")
            else "UNKNOWN"
        )
        response["reason"] = diagnostic.get("reason", "AUDITOR_RETURNED_NO_REASON")
        response["input_fingerprints"] = {
            "claim_sha256": steps[0]["observation"]["sha256"],
            "evidence_sha256": steps[1]["observation"]["sha256"],
        }
        response["differences"] = (
            diagnostic.get("differences", []) if correspondence == "MISMATCH" else []
        )
    except (AgentRequestError, OSError, TypeError, ValueError, UnicodeError,
            RecursionError, OverflowError) as exc:
        response["reason"] = (
            str(exc) if isinstance(exc, AgentRequestError)
            else "LOCAL_AGENT_OR_AUDIT_UNAVAILABLE"
        )
        response["claim_correspondence"] = "UNKNOWN"
        response.pop("input_fingerprints", None)
        response.pop("differences", None)
    return response


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Opt-in Ario bounded agent and offline PR claim self-audit"
    )
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--ledger", required=True, help="Append-only agent event journal")
    parser.add_argument("--task-id", required=True, help="Unique research task identifier")
    parser.add_argument("--pr-body", required=True, help="Workspace-relative claim text")
    parser.add_argument("--evidence", required=True, help="Workspace-relative evidence JSON")
    args = parser.parse_args(argv)
    output = inspect_with_agent(
        workspace=args.workspace, ledger=args.ledger, task_id=args.task_id,
        pr_body=args.pr_body, evidence=args.evidence,
    )
    print(json.dumps(output, sort_keys=True, ensure_ascii=True))
    return 0  # No approval or trust authority is granted by exit status.


if __name__ == "__main__":
    raise SystemExit(main())
