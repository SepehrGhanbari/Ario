"""ARIO-PR-CI-0.2: source-origin HOLD wrapper for the v0.1 offline comparator.

Research-only, intentionally no API/network, signer, or authority. It preserves
v0.1's snapshot correspondence as a *diagnostic*, but never promotes an
unverified caller-supplied evidence bundle into an externally grounded MATCH.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pr_claim_audit import (
    MAX_EVIDENCE_BYTES,
    MAX_PR_BYTES,
    Invalid,
    _decode_json,
    _read_limited,
    assess as compare_supplied_snapshot,
)

SCHEMA = "ARIO-PR-CI-0.2"
ORIGIN_UNVERIFIED = "UNVERIFIED"
NO_AUTHORITY = (
    "Source origin is not authenticated by this offline comparator",
    "The supplied metadata, log, digest and completeness indicator share caller custody",
    "Correspondence is not test correctness, scientific proof, signer authorization or merge eligibility",
)


def assess(pr_text: str, evidence: Any) -> dict[str, Any]:
    """Offline strict result: no caller-controlled field can establish origin.

    `correspondence_status` can be MATCH/MISMATCH/UNKNOWN, but the final status
    remains UNKNOWN until a separate independently reviewed origin verifier
    is implemented. No future magic `origin_verified` input is accepted here.
    """
    comparison = compare_supplied_snapshot(pr_text, evidence)
    found = comparison["status"]
    answer = {
        "schema": SCHEMA,
        "status": "UNKNOWN",
        "reason": "EVIDENCE_ORIGIN_UNVERIFIED" if found != "UNKNOWN" else "SNAPSHOT_NOT_ASSESSABLE",
        "correspondence_status": found,
        "correspondence_reason": comparison["reason"],
        "origin_status": ORIGIN_UNVERIFIED,
        "origin_basis": "CALLER_SUPPLIED_SNAPSHOT_ONLY",
        "binding": comparison["binding"],
        "observed": comparison["observed"],
        "differences": comparison["differences"],
        "limitations": [*comparison["limitations"], *NO_AUTHORITY],
    }
    return answer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ario PR/CI v0.2 origin-HOLD research probe")
    parser.add_argument("--pr-body", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    opts = parser.parse_args(argv)
    try:
        body = _read_limited(opts.pr_body, MAX_PR_BYTES)
        evidence = _decode_json(_read_limited(opts.evidence, MAX_EVIDENCE_BYTES))
        result = assess(body, evidence)
    except (OSError, Invalid, UnicodeError, OverflowError, RecursionError):
        result = assess("", {})
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    # Exit status is not evidentiary approval.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
