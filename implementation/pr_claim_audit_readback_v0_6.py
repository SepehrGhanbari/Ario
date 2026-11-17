"""Ario PR-CI v0.6 — bounded sampled-readback receipts; no truth authority.

RESEARCH ONLY. No filesystem writes, GitHub mutations, or signer/key access.
No network claim is elevated to independently verified TLS provenance.
The v0.5 comparator remains unchanged; this sidecar observes its PR reads.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

from pr_claim_audit_github_v0_3 import PublicGitHubReader
from pr_claim_audit_state_v0_5 import assess_github_pr as assess_v05

SCHEMA = "ARIO-PR-CI-0.6"
_SHA = re.compile(r"[0-9a-f]{40}\Z")
LIMITATIONS = (
    "Reader observations are not an independently authenticated TLS or GitHub attestation",
    "Timestamps are local observation times, not trustworthy server timestamps",
    "Three sampled PR reads are not an atomic snapshot; a PR may change afterwards",
    "Log content, test command and counts are not independently attested pytest execution",
    "Read-only diagnostics never authorize merge, signer operation, or trust activation",
)


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _valid_pr(data: Any) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    head = data.get("head")
    sha = head.get("sha") if isinstance(head, dict) else None
    if (type(data.get("id")) is not int or data["id"] < 1 or
            type(data.get("number")) is not int or data["number"] < 1 or
            not isinstance(sha, str) or not _SHA.fullmatch(sha) or
            not isinstance(data.get("body"), str)):
        return None
    return {
        "id": data["id"], "number": data["number"], "head_sha": sha,
        "body_sha256": hashlib.sha256(data["body"].encode("utf-8")).hexdigest(),
    }


class _TracingReader:
    """Collect bounded PR-GET receipts; transport itself is not a witness."""

    def __init__(self, reader: Any, pr_url: str):
        self.reader = reader
        self.pr_url = pr_url
        self.samples: list[dict[str, Any]] = []

    def get_json(self, url: str) -> dict[str, Any]:
        if url != self.pr_url:
            return self.reader.get_json(url)
        begin = _stamp()
        try:
            data = self.reader.get_json(url)
        except Exception as exc:
            self.samples.append({
                "result": "FAILED", "requested_utc": begin,
                "completed_utc": _stamp(), "exception_type": type(exc).__name__,
            })
            raise
        record = _valid_pr(data)
        self.samples.append({
            "result": "OK" if record is not None else "PARTIAL",
            "requested_utc": begin, "completed_utc": _stamp(),
            "identity": record,
        })
        return data

    def get_job_log(self, url: str) -> str:
        return self.reader.get_job_log(url)


def _discard_diagnostic(result: dict[str, Any], reason: str, state: str) -> None:
    result.update({
        "status": "UNKNOWN", "reason": reason,
        "claim_correspondence": "UNKNOWN", "correspondence_status": "UNKNOWN",
        "state_consistency": state, "binding": None, "observed": None,
        "differences": [], "workflow_overall_conclusion": "UNKNOWN",
        "workflow_state_changed_during_recheck": None,
    })


def assess_github_pr(owner: str, repo: str, pr_number: int, *,
                     reader: Any = None) -> dict[str, Any]:
    """Evaluate v0.5 and make sample completeness explicit, never final MATCH.

    `last_pr_head_sha_observed` is *never* called current; it describes only the
    last complete observed PR response and is null if the last read fails.
    Caller-injected readers, patched transports, and actual HTTPS transports
    have no independent provenance claim in this output.
    """
    mode = "PUBLIC_READER_CONFIGURED" if reader is None else "CALLER_INJECTED_READER"
    base_reader = PublicGitHubReader() if reader is None else reader
    pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    traced = _TracingReader(base_reader, pr_url)
    result = assess_v05(owner, repo, pr_number, reader=traced)
    result = {
        **result, "schema": SCHEMA, "status": "UNKNOWN",
        "source_delivery": "READER_RESPONSE_UNATTESTED",
        "source_transport_status": "UNVERIFIED",
        "origin_status": "UNVERIFIED",
        "origin_basis": "READ_ONLY_READER_RESPONSES",
        "transport_configuration": mode,
        "tls_route_verification": "NOT_INDEPENDENTLY_VERIFIED",
        "execution_attestation": "NOT_ESTABLISHED",
        "log_execution_attestation": "NOT_ESTABLISHED",
        "pr_read_samples": [
            {k: v for k, v in sample.items() if k != "identity"}
            for sample in traced.samples
        ],
        "pr_read_count": len(traced.samples),
        "final_pr_readback_status": "NOT_REACHED",
        "last_pr_head_sha_observed": None,
        "pinned_pr_head_sha": None,
        "limitations": list(dict.fromkeys([*result.get("limitations", ()), *LIMITATIONS])),
    }
    if traced.samples and traced.samples[0].get("result") == "OK":
        first = traced.samples[0]["identity"]
        result["pinned_pr_head_sha"] = first["head_sha"]
    # No final PR recheck ⇒ never claim a last-read head or stable state.
    if len(traced.samples) < 3:
        if result.get("state_consistency") == "STABLE_AT_SAMPLED_READS":
            _discard_diagnostic(result, "FINAL_PR_READBACK_NOT_REACHED", "UNRESOLVED")
        return result
    last = traced.samples[-1]
    if last["result"] != "OK":
        result["final_pr_readback_status"] = last["result"]
        _discard_diagnostic(
            result,
            "FINAL_PR_READBACK_FAILED" if last["result"] == "FAILED" else "FINAL_PR_READBACK_PARTIAL",
            "UNRESOLVED",
        )
        return result
    final = last["identity"]
    result["last_pr_head_sha_observed"] = final["head_sha"]
    if traced.samples[0].get("result") != "OK":
        result["final_pr_readback_status"] = "UNRESOLVED"
        _discard_diagnostic(result, "INITIAL_PR_UNRESOLVED", "UNRESOLVED")
        return result
    first = traced.samples[0]["identity"]
    if final != first:
        result["final_pr_readback_status"] = "CHANGED"
        _discard_diagnostic(result, "PR_CHANGED_AT_LAST_SAMPLED_READ", "PR_CHANGED")
        return result
    # The sampled PR is the same, but v0.5 could have failed on run/job state.
    result["final_pr_readback_status"] = "OK"
    if result.get("claim_correspondence") in ("MATCH", "MISMATCH"):
        initial = result.get("workflow_conclusion_initial")
        final_run = result.get("workflow_conclusion_final")
        if not isinstance(initial, str) or not isinstance(final_run, str):
            _discard_diagnostic(result, "RUN_STATE_UNRESOLVED", "RUN_STATE_UNRESOLVED")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ario PR/CI v0.6 non-authoritative sampled readback")
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", required=True, type=int)
    args = parser.parse_args(argv)
    print(json.dumps(assess_github_pr(args.owner, args.repo, args.pr),
                     sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
