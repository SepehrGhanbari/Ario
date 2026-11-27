"""Read-only EA-0.1 -> ARP-0.1 consumer. No evidence admission or M0 verdict."""
from __future__ import annotations

import hashlib
from pathlib import Path

from admission_review_evaluator import REQUEST_FIELDS, evaluate_review_request
from bounded_json import MAX_JSON_FILE_BYTES, loads_bounded
from candidate_dossier_builder import build_candidate_dossier
from research.w38_receipt_fd_guard import read_bounded_regular

PROPOSAL_FIELDS = {"line", "claim_id", "claim_scope", "proposed_support_relation"}
REVIEW_FIELDS = REQUEST_FIELDS - {"candidate"}


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def _nonfinite(_):
    raise ValueError("nonfinite JSON constant")


def inspect_dossier_files(manifest_path, ledger_path, request_path):
    """Build the candidate from a bounded local observation and screen it again.

    Both stages use the same supplied manifest; the existing evaluator rebuilds
    from a fresh ledger observation. The report is descriptive, not admission.
    """
    report = {
        "operation": "EA_0_1_ARP_0_1_DOSSIER_SCREENING",
        "status": "UNKNOWN",
        "input_sha256": {},
        "candidate": None,
        "review": None,
        "admission_decision": "NOT_EVALUATED",
        "claim_truth": "UNKNOWN",
        "source_authentication": "UNKNOWN",
        "source_independence": "UNKNOWN",
        "freshness": "UNKNOWN",
        "independent_admission_authority": "NONE",
    }
    values = {}
    try:
        for role, path in (("manifest", manifest_path), ("request", request_path)):
            raw = read_bounded_regular(Path(path), MAX_JSON_FILE_BYTES)
            report["input_sha256"][role] = hashlib.sha256(raw).hexdigest()
            values[role] = loads_bounded(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                                         parse_constant=_nonfinite)
        request = values["request"]
        if (not isinstance(request, dict) or set(request) != {"proposal", "review"}
                or not isinstance(request["proposal"], dict)
                or set(request["proposal"]) != PROPOSAL_FIELDS
                or not isinstance(request["review"], dict)
                or set(request["review"]) != REVIEW_FIELDS):
            report.update(status="REJECTED", reason="INVALID_DOSSIER_REQUEST_ENVELOPE")
            return report
        manifest = values["manifest"]
        candidate = build_candidate_dossier(manifest, ledger_path, **request["proposal"])
        report["candidate"] = candidate
        if candidate["status"] != "CANDIDATE":
            report.update(status=candidate["status"], reason="CANDIDATE_NOT_PREPARED")
            return report
        # The candidate is constructed here, never accepted from the request.
        # The separate reviewer fields are not replaced with the proposal.
        review = evaluate_review_request(
            {**request["review"], "candidate": candidate}, manifest, ledger_path)
        report["review"] = review
        report["status"] = "SCREENED" if review["status"] == "UNKNOWN" else review["status"]
        return report
    except (OSError, ValueError, UnicodeError, RecursionError, OverflowError, TypeError):
        report.update(status="UNKNOWN", reason="INPUT_OR_SCREENING_UNAVAILABLE")
        return report
