"""Optional live GitHub network probe on the existing PR regression runners.

Research-only, READ-ONLY, unauthenticated, and never a merge/trust/pytest-execution
attestation. A network failure is reported as UNKNOWN (pytest skip), not PASS.
This file adds no workflow job and makes no writes or remote mutations.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import urllib.parse
import warnings

import pytest

from pr_claim_audit_github_v0_3 import OriginUnknown, PublicGitHubReader

REPO = "SepehrGhanbari/Ario"
BASE = f"https://api.github.com/repos/{REPO}"
PR_NUMBER = 249
PINNED_HEAD = "c800b45c2c06d1bbeacaa063cca4573f0ec1d879"
RUN_ID = 43949946093
ATTEMPT = 1
JOB_ID = 133589448819
LOG_MARKER = "1 failed, 1140 passed, 121 subtests passed"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _on_authorized_ci_runner(environment: dict[str, str] | None = None) -> bool:
    e = os.environ if environment is None else environment
    return (e.get("GITHUB_ACTIONS") == "true" and
            e.get("GITHUB_EVENT_NAME") == "pull_request" and
            e.get("GITHUB_REPOSITORY") == REPO)


class _ReadOnlyObservedReader(PublicGitHubReader):
    """Observe *returned* statuses, never expose signed log-redirect URLs."""

    def __init__(self):
        super().__init__(timeout=10)
        self.http_events: list[dict[str, object]] = []

    def _fetch(self, url: str, cap: int) -> tuple[int, bytes, str | None]:
        status, data, redirect = super()._fetch(url, cap)
        # The redirect URL can include bearer-like signed query credentials.
        # Keep only the hostname and response status; never the path/query.
        self.http_events.append({
            "host": urllib.parse.urlsplit(url).hostname,
            "http_status": status,
            "byte_count": len(data),
            "observed_utc": _utc_now(),
            "redirect_received": bool(redirect),
        })
        return status, data, redirect


def _publish(outcome: str, reader: _ReadOnlyObservedReader, stage: str,
             **details: object) -> None:
    payload = {
        "schema": "ARIO-LIVE-TRANSPORT-RESEARCH-0.1",
        "outcome": outcome,
        "stage": stage,
        "local_observation_utc": _utc_now(),
        "runner_os": os.environ.get("RUNNER_OS", "UNKNOWN"),
        "repository": REPO,
        "pinned_pr": PR_NUMBER,
        "run_id": RUN_ID,
        "run_attempt": ATTEMPT,
        "job_id": JOB_ID,
        "authenticated_github_origin": "NOT_ESTABLISHED",
        "pytest_execution_attested": "NOT_ESTABLISHED",
        "http_events": reader.http_events,
        **details,
    }
    # Pytest displays warnings even with -q and normal output capture.
    # We emit only numeric IDs, public SHA/hash/host and bounded reason codes.
    warnings.warn("ARIO_LIVE_FETCH_RESULT " + json.dumps(payload, sort_keys=True),
                  UserWarning, stacklevel=2)


def test_opt_in_real_python_public_github_reader() -> None:
    """A real *network observation*, not an independently proven CI execution."""
    if not _on_authorized_ci_runner():
        pytest.skip("LIVE_FETCH_NOT_RUN: only on this repository's PR GitHub Actions")

    reader = _ReadOnlyObservedReader()
    stage = "PR_METADATA"
    try:
        pr = reader.get_json(f"{BASE}/pulls/{PR_NUMBER}")
        if pr.get("number") != PR_NUMBER or pr.get("head", {}).get("sha") != PINNED_HEAD:
            _publish("UNKNOWN", reader, stage, reason="PR_HEAD_PIN_MISMATCH")
            pytest.skip("LIVE_FETCH_UNKNOWN: pinned public PR head changed")

        stage = "RUN_METADATA"
        run = reader.get_json(f"{BASE}/actions/runs/{RUN_ID}")
        if (run.get("id") != RUN_ID or run.get("run_attempt") != ATTEMPT or
                run.get("head_sha") != PINNED_HEAD or run.get("event") != "pull_request"):
            _publish("UNKNOWN", reader, stage, reason="RUN_IDENTITY_MISMATCH")
            pytest.skip("LIVE_FETCH_UNKNOWN: public run identity mismatch")

        stage = "ATTEMPT_JOBS"
        jobs = reader.get_json(f"{BASE}/actions/runs/{RUN_ID}/attempts/{ATTEMPT}/jobs?per_page=100&page=1")
        if (jobs.get("total_count", 0) > 100 or
                len([j for j in jobs.get("jobs", []) if j.get("id") == JOB_ID and
                     j.get("run_id") == RUN_ID and j.get("run_attempt") == ATTEMPT]) != 1):
            _publish("UNKNOWN", reader, stage, reason="JOB_MEMBERSHIP_UNRESOLVED")
            pytest.skip("LIVE_FETCH_UNKNOWN: job not bound to exact run attempt")

        stage = "JOB_LOG"
        job_log = reader.get_job_log(f"{BASE}/actions/jobs/{JOB_ID}/logs")
        if not job_log or LOG_MARKER not in job_log:
            _publish("UNKNOWN", reader, stage, reason="LOG_MISSING_EXPECTED_MARKER")
            pytest.skip("LIVE_FETCH_UNKNOWN: unexpected or missing public job log")

        _publish("LIVE_PYTHON_FETCH_OBSERVED", reader, "DONE",
                 log_bytes=len(job_log.encode("utf-8")),
                 log_sha256=hashlib.sha256(job_log.encode("utf-8")).hexdigest(),
                 content_check="KNOWN_PYTEST_SHAPED_LINE_PRESENT")
    except OriginUnknown as exc:
        # These reasons are bounded by the pre-existing reader. No signed links,
        # tokens, log bytes, or untrusted GitHub content are printed.
        _publish("UNKNOWN", reader, stage, reason=str(exc)[:100])
        pytest.skip("LIVE_FETCH_UNKNOWN: public unauthenticated GitHub read unavailable")
    except (OSError, TimeoutError, UnicodeError, ValueError) as exc:
        _publish("UNKNOWN", reader, stage, reason_type=type(exc).__name__)
        pytest.skip("LIVE_FETCH_UNKNOWN: network/response handling failure")


def test_probe_uses_explicit_ci_gate_only() -> None:
    assert not _on_authorized_ci_runner({})
    assert not _on_authorized_ci_runner({"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "push", "GITHUB_REPOSITORY": REPO})
    assert not _on_authorized_ci_runner({"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "pull_request", "GITHUB_REPOSITORY": "other/repo"})
    assert _on_authorized_ci_runner({"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "pull_request", "GITHUB_REPOSITORY": REPO})


def test_events_cannot_contain_signed_redirect_query(monkeypatch: pytest.MonkeyPatch) -> None:
    reader = _ReadOnlyObservedReader()
    url = "https://results-receiver.actions.githubusercontent.com/private?sig=DO_NOT_LOG"
    monkeypatch.setattr(PublicGitHubReader, "_fetch", lambda self, u, cap: (200, b"safe", None))
    assert reader._fetch(url, 100) == (200, b"safe", None)
    captured = json.dumps(reader.http_events)
    assert "DO_NOT_LOG" not in captured and "private" not in captured
    assert "results-receiver.actions.githubusercontent.com" in captured
    assert reader.http_events[0]["http_status"] == 200
