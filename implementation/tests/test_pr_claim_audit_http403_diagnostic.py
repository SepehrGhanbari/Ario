"""Ario: bounded anonymous HTTP diagnostics for CI job-log 403 (research only).

No Authorization header, no tokens, no signed redirect URL, no body text/log
content exposed. This test never claims independently verified origin or execution.
It intentionally SKIPS in CI after recording an observation, including HTTP 200.
"""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import hashlib
import json
import os
import re
import ssl
from email.message import Message
import urllib.error
import urllib.parse
import urllib.request
import warnings

import pytest

_REPO = "SepehrGhanbari/Ario"
_RUN_ID = 43949946093
_JOB_ID = 133589448819
_API = f"https://api.github.com/repos/{_REPO}"
_MAX_ERROR_BODY = 1024
_MAX_READ = 1024


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _allowed_ci(env=None):
    e = os.environ if env is None else env
    return (e.get("GITHUB_ACTIONS") == "true" and
            e.get("GITHUB_EVENT_NAME") == "pull_request" and
            e.get("GITHUB_REPOSITORY") == _REPO)


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _number_header(headers, name):
    x = headers.get(name)
    return x if isinstance(x, str) and re.fullmatch(r"\d{1,12}", x) else None


def _safe_headers(headers):
    req_id = headers.get("X-GitHub-Request-Id")
    if not isinstance(req_id, str) or not re.fullmatch(r"[a-zA-Z0-9:-]{1,100}", req_id):
        req_id = None
    return {
        "github_request_id": req_id,
        "www_authenticate_present": headers.get("WWW-Authenticate") is not None,
        "retry_after_seconds": _number_header(headers, "Retry-After"),
        "ratelimit_remaining": _number_header(headers, "X-RateLimit-Remaining"),
        "ratelimit_limit": _number_header(headers, "X-RateLimit-Limit"),
        "ratelimit_reset_unix": _number_header(headers, "X-RateLimit-Reset"),
        "accepted_permissions_header_present": headers.get("X-Accepted-GitHub-Permissions") is not None,
        "location_header_present": headers.get("Location") is not None,
    }


def _error_family(body):
    """Categorize, but NEVER log free text from an untrusted error body."""
    try:
        obj = json.loads(body.decode("utf-8"))
        msg = obj.get("message", "")
        if not isinstance(msg, str):
            return "NONSTANDARD_MESSAGE"
        s = msg.lower()
        if "admin rights" in s:
            return "ADMIN_RIGHTS_WORDING"
        if "rate limit" in s:
            return "RATE_LIMIT_WORDING"
        if "resource not accessible" in s:
            return "RESOURCE_ACCESS_WORDING"
        if "requires authentication" in s or "authentication required" in s:
            return "AUTHENTICATION_WORDING"
        return "UNCLASSIFIED_GITHUB_ERROR_MESSAGE"
    except (ValueError, UnicodeError, AttributeError):
        return "NON_JSON_ERROR_BODY"


def _anonymous_get(endpoint, url, opener=None):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "api.github.com" or parsed.port not in (None, 443):
        raise ValueError("Only GitHub API HTTPS endpoints are permitted")
    opener = opener or urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _NoRedirect(),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
    )
    req = urllib.request.Request(url, method="GET", headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "Ario-Anonymous-HTTP-Diagnostic-0.1",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    observed = {
        "endpoint": endpoint, "method": "GET", "api_host": "api.github.com",
        "request_has_authorization": "Authorization" in req.headers,
        "observed_utc": _utc_now(),
        "network_status": "UNKNOWN", "http_status": None,
        "error_body_family": "UNKNOWN", "sample_sha256": None,
    }
    try:
        with opener.open(req, timeout=10) as response:
            sample = response.read(_MAX_READ)
            observed.update({
                "network_status": "HTTP_RESPONSE_OBSERVED", "http_status": response.status,
                "response_headers": _safe_headers(response.headers),
                "sample_sha256": hashlib.sha256(sample).hexdigest(),
                "error_body_family": "NOT_ERROR_RESPONSE",
            })
    except urllib.error.HTTPError as exc:
        # A 3xx response carries a signed Location. Presence only, never its value.
        body = exc.read(_MAX_ERROR_BODY)
        observed.update({
            "network_status": "HTTP_RESPONSE_OBSERVED", "http_status": exc.code,
            "response_headers": _safe_headers(exc.headers),
            "sample_sha256": hashlib.sha256(body).hexdigest(),
            "error_body_family": _error_family(body) if exc.code >= 400 else "NOT_ERROR_RESPONSE",
        })
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        observed["network_error_class"] = type(exc).__name__
    return observed


def test_real_http403_diagnostics_ci_only():
    if not _allowed_ci():
        pytest.skip("ANONYMOUS_HTTP_DIAGNOSTIC_NOT_RUN: authorized PR CI only")
    # Only public metadata & historical job logs. No secrets or authentication.
    endpoints = (
        ("RUN_METADATA", f"{_API}/actions/runs/{_RUN_ID}"),
        ("JOB_LOG_REDIRECT_ENDPOINT", f"{_API}/actions/jobs/{_JOB_ID}/logs"),
    )
    events = [_anonymous_get(name, url) for name, url in endpoints]
    result = {
        "schema": "ARIO-ANONYMOUS-HTTP-FORENSICS-0.1", "research_verdict": "UNKNOWN",
        "execution_attestation": "NOT_ESTABLISHED", "job_log_downloaded": False,
        "source_custody_verified": False, "events": events, "observed_utc": _utc_now(),
        "runner_os": os.environ.get("RUNNER_OS", "UNKNOWN"),
    }
    warnings.warn("ARIO_HTTP403_DIAGNOSTIC " + json.dumps(result, sort_keys=True), UserWarning, stacklevel=2)
    pytest.skip("ANONYMOUS_HTTP_DIAGNOSTIC_RECORDED_NOT_A_PASS")


def test_whitelisted_headers_hide_secrets():
    h = Message()
    h["Location"] = "https://results-receiver.actions.githubusercontent.com/job?sig=DO_NOT_LOG"
    h["WWW-Authenticate"] = "Bearer token=DO_NOT_LOG"
    h["X-GitHub-Request-Id"] = "DEAD:123:456"
    h["X-RateLimit-Remaining"] = "59"
    data = json.dumps(_safe_headers(h))
    assert "DO_NOT_LOG" not in data and "sig=" not in data
    assert _safe_headers(h)["location_header_present"] is True
    assert _safe_headers(h)["www_authenticate_present"] is True
    assert _safe_headers(h)["github_request_id"] == "DEAD:123:456"


def test_anonymous_403_captures_family_without_message_or_url():
    headers = Message()
    headers["Content-Type"] = "application/json"
    headers["X-RateLimit-Remaining"] = "60"
    headers["Location"] = "https://example.invalid/?sig=DO_NOT_LOG"
    message = b'{"message":"Must have admin rights to Repository","secret":"DO_NOT_LOG"}'
    err = urllib.error.HTTPError("https://api.github.com/mock", 403, "Forbidden", headers, BytesIO(message))
    class FakeOpener:
        def open(self, req, timeout=None):
            assert req.get_header("Authorization") is None
            raise err
    result = _anonymous_get("JOB_LOG", f"{_API}/actions/jobs/{_JOB_ID}/logs", FakeOpener())
    data = json.dumps(result)
    assert result["network_status"] == "HTTP_RESPONSE_OBSERVED"
    assert result["http_status"] == 403
    assert result["error_body_family"] == "ADMIN_RIGHTS_WORDING"
    assert result["response_headers"]["ratelimit_remaining"] == "60"
    assert "DO_NOT_LOG" not in data and "Must have admin" not in data


def test_allowed_ci_gate_no_ambient_environment_confusion():
    assert not _allowed_ci({})
    assert not _allowed_ci({"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "push", "GITHUB_REPOSITORY": _REPO})
    assert _allowed_ci({"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "pull_request", "GITHUB_REPOSITORY": _REPO})


def test_error_messages_are_categorized_not_emitted():
    assert _error_family(b'{"message":"Must have admin rights to Repository"}') == "ADMIN_RIGHTS_WORDING"
    assert _error_family(b'{"message":"API rate limit exceeded for somebody"}') == "RATE_LIMIT_WORDING"
    assert _error_family(b'{"message":"Unknown private code xyz"}') == "UNCLASSIFIED_GITHUB_ERROR_MESSAGE"
    assert _error_family(b'not json') == "NON_JSON_ERROR_BODY"