# Ario Self-Audit Engine Adapter v0.1

Status: RESEARCH_ONLY / OFF_BY_DEFAULT / DRAFT / NO_AUTO_MERGE /
PRODUCTION=NO_GO / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO.

## What is connected

This standalone executable calls the REAL bounded Ario agent
(ario_agent.run_task) for two read-only file_fingerprint actions, re-reads
and re-hashes both files, and calls the merged #290 offline PR-CI comparison
(pr_claim_audit.assess).

It produces a diagnostic claim_correspondence of MATCH, MISMATCH or UNKNOWN.
The TOP-LEVEL status is ALWAYS UNKNOWN. Even MATCH is only agreement with a
caller-supplied log; it is not evidence admission, execution attestation,
correctness, truth or an owner merge decision.

The bounded agent appends task observations to its explicitly nominated
append-only JSONL ledger. The two input files remain unchanged. No other
Ario memory, M0, model, signer, workflow, trust or Genesis state changes.
The normal engine and Ollama planner are untouched. This is the FIRST
experimental engine attachment, NOT yet an interactive model integration.

The existing agent caps each input file at 20,000 bytes. Actual larger
CI logs are deliberately unsupported at this prototype stage. The inputs
are not independently authenticated and readback is not atomic. Use only
synthetic non-sensitive samples for now.

## Run CI-focused regression

From implementation/ under Windows PowerShell:

    $env:PYTHONDONTWRITEBYTECODE = "1"
    python -B -m pytest -p no:cacheprovider -q tests/test_ario_self_audit_adapter.py

## Try the adapter on synthetic local data

From implementation/ under PowerShell:

    $lab = Join-Path $env:TEMP "ario-self-audit-lab"
    New-Item -ItemType Directory -Force $lab | Out-Null
    @'
    import json, sys
    from pathlib import Path
    sys.path.insert(0, "tests")
    from test_pr_claim_audit import body, evidence
    out = Path(sys.argv[1])
    (out / "claim.md").write_text(body(), encoding="utf-8")
    (out / "evidence.json").write_text(json.dumps(evidence()), encoding="utf-8")
    '@ | python -B - $lab

    python -B .\ario_self_audit_adapter.py --workspace $lab --ledger (Join-Path $lab "events.jsonl") --task-id LAB-001 --pr-body claim.md --evidence evidence.json

Expected: claim_correspondence MATCH, agent_task_status COMPLETED,
top-level status UNKNOWN, and execution_attestation NOT_ESTABLISHED.

To see MISMATCH, change passed 1140 to 1141 ONLY in the synthetic claim
file, and rerun with a NEW task ID (LAB-002). Missing evidence produces
UNKNOWN and a stopped fingerprint task; never a fabricated MATCH.

Disabling is trivial: do not call the adapter. All ordinary engine entry
points behave as before. Later iterations may add a separately reviewed
Ollama-facing observation hook, but no model access, persistent memory
changes or trust authority are authorized by this PR.

Exact proposed files (additive only):
- implementation/ario_self_audit_adapter.py
- implementation/tests/test_ario_self_audit_adapter.py
- implementation/ARIO_SELF_AUDIT_ENGINE_ADAPTER_V0_1.md
