"""Ario PR-CI v0.5: separate correspondence, source delivery, state, execution.

RESEARCH ONLY. Read-only. The result is NEVER an attestation/merge verdict.
Preserve all pre-v0.5 modules byte-for-byte; this is an additive sidecar.
"""
from __future__ import annotations

import argparse
import json
import hashlib
import urllib.error
from typing import Any

from pr_claim_audit_github_v0_3 import OriginUnknown, PublicGitHubReader
from pr_claim_audit_log_boundary_v0_4 import assess_github_pr as assess_v04

SCHEMA = "ARIO-PR-CI-0.5"
LIMITATIONS = (
    "Delivery through GitHub is not independent execution attestation",
    "A changing workflow conclusion is flagged separately from job/log correspondence",
    "State readbacks are sampled, not atomic; a PR can change after the final GET",
    "No run/test-quality approval, signer, merge authority, or trust activation",
)


class _RecordingReader:
    """Wrap one read-only reader; capture the first PR and run GET for comparison.

    Its stored observations are NOT a separate source, signature, or authority.
    """

    def __init__(self, reader: Any, pr_url: str):
        self._reader = reader
        self.pr_url = pr_url
        self.first_pr: dict[str, Any] | None = None
        self.first_run_conclusion: str | None = None

    def get_json(self, url: str) -> dict[str, Any]:
        data = self._reader.get_json(url)
        if isinstance(data, dict):
            if url == self.pr_url and self.first_pr is None:
                # Only immutable values needed for the last recheck.
                head = data.get("head")
                self.first_pr = {
                    "number": data.get("number"), "id": data.get("id"),
                    "head": head.get("sha") if isinstance(head, dict) else None,
                    "body": data.get("body"),
                }
            elif "/actions/runs/" in url and "/attempts/" not in url and "?" not in url:
                if self.first_run_conclusion is None:
                    conclusion = data.get("conclusion")
                    if isinstance(conclusion, str):
                        self.first_run_conclusion = conclusion
        return data

    def get_job_log(self, url: str) -> str:
        return self._reader.get_job_log(url)


def _hold(result: dict[str, Any], reason: str, state: str) -> dict[str, Any]:
    """Discard stale/unsupported diagnostics; never turn absence into mismatch."""
    result.update({
        "status": "UNKNOWN", "reason": reason,
        "claim_correspondence": "UNKNOWN", "correspondence_status": "UNKNOWN",
        "state_consistency": state,
        "binding": None, "observed": None, "differences": [],
        "workflow_overall_conclusion": "UNKNOWN",
        "workflow_state_changed_during_recheck": False,
    })
    return result


def assess_github_pr(owner: str, repo: str, pr_number: int, *,
                     reader: Any = None) -> dict[str, Any]:
    """Report four independent dimensions; final status is always UNKNOWN.

    Injected readers (even real-class instances) never gain TLS origin credit.
    No user-supplied field is accepted as an execution attestation.
    """
    injected = reader is not None
    try:
        transport = PublicGitHubReader() if reader is None else reader
        pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        recording = _RecordingReader(transport, pr_url)
        old = assess_v04(owner, repo, pr_number, reader=recording)
        correspondence = old.get("correspondence_status", "UNKNOWN")
        # Source-delivery is about this execution path, not independently witnessed custody.
        source = ("GITHUB_API_TLS_ROUTE" if not injected and correspondence in ("MATCH", "MISMATCH")
                  else "UNVERIFIED")
        result = {
            **old, "schema": SCHEMA, "status": "UNKNOWN",
            "claim_correspondence": correspondence,
            "source_delivery": source,
            "source_transport_status": source,
            "state_consistency": "UNKNOWN",
            "execution_attestation": "NOT_ESTABLISHED",
            "log_execution_attestation": "NOT_ESTABLISHED",
            "workflow_state_changed_during_recheck": False,
            "limitations": list(dict.fromkeys([*old.get("limitations", ()), *LIMITATIONS])),
        }
        if correspondence not in ("MATCH", "MISMATCH"):
            return result
        binding, observed, first_pr = old.get("binding"), old.get("observed"), recording.first_pr
        if not isinstance(binding, dict) or not isinstance(observed, dict) or not isinstance(first_pr, dict):
            return _hold(result, "MISSING_PINNED_PR_BINDING", "UNKNOWN")
        # One last PR GET after v0.4's run + job readback closes its particular
        # v0.3->v0.4 window. There is no atomic snapshot or perpetual guarantee.
        final_pr = recording.get_json(pr_url)
        if not isinstance(final_pr, dict):
            return _hold(result, "FINAL_PR_RECHECK_UNAVAILABLE", "UNKNOWN")
        head = final_pr.get("head")
        final_head = head.get("sha") if isinstance(head, dict) else None
        if (final_pr.get("id") != first_pr["id"] or
                final_pr.get("number") != first_pr["number"] or
                final_head != binding.get("head_sha") or final_head != first_pr["head"] or
                final_pr.get("body") != first_pr["body"]):
            return _hold(result, "PR_CHANGED_AFTER_V04_READBACK", "PR_CHANGED")
        initial_run = recording.first_run_conclusion
        final_run = old.get("workflow_overall_conclusion")
        if not isinstance(initial_run, str) or not isinstance(final_run, str) or final_run == "UNKNOWN":
            return _hold(result, "RUN_CONCLUSION_NOT_COMPARABLE", "UNKNOWN")
        changed = initial_run != final_run
        result["state_consistency"] = ("WORKFLOW_CONCLUSION_CHANGED" if changed
                                       else "STABLE_AT_SAMPLED_READS")
        result["workflow_state_changed_during_recheck"] = changed
        result["workflow_conclusion_initial"] = initial_run
        result["workflow_conclusion_final"] = final_run
        result["pr_body_sha256"] = hashlib.sha256(first_pr["body"].encode("utf-8")).hexdigest()
        # Other than scoped state diagnostics, this cannot establish execution.
        result["reason"] = "LOG_EXECUTION_NOT_ATTESTED"
        return result
    except (OriginUnknown, KeyError, TypeError, ValueError, UnicodeError, OSError,
            urllib.error.URLError, OverflowError, RecursionError) as exc:
        return {
            "schema": SCHEMA, "status": "UNKNOWN", "reason": "FINAL_PR_RECHECK_UNAVAILABLE",
            "claim_correspondence": "UNKNOWN", "correspondence_status": "UNKNOWN",
            "source_delivery": "UNVERIFIED", "state_consistency": "UNKNOWN",
            "execution_attestation": "NOT_ESTABLISHED", "limitations": list(LIMITATIONS),
            "error_type": type(exc).__name__,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ario PR-CI v0.5 four-axis read-only audit")
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", type=int, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(assess_github_pr(args.owner, args.repo, args.pr), sort_keys=True, ensure_ascii=True))
    return 0  # Execution of the reporting command is not approval.


if __name__ == "__main__":
    raise SystemExit(main())
