"""Trusted-main-only reader: synthetic REST/GraphQL contract, no live token."""
from __future__ import annotations

import copy

from research import guard_v2_trusted_manual as manual
from test_guard_v2_review_graph import FakeGraphQL, original, REPO_ID, PR_ID, HEAD, BASE


SOURCE_SHA = "c" * 40


class FakeRest:
    def __init__(self):
        self.repo = {"id": REPO_ID}
        self.pr = {"id": PR_ID, "number": 295, "head": {"sha": HEAD},
                   "base": {"sha": BASE, "ref": "main", "repo": {"id": REPO_ID}},
                   "state": "open", "draft": True,
                   "body": "Original reviewed PR text",
                   "updated_at": "2026-11-21T00:00:00Z"}
        self.after = None
        self.calls = []

    def get_json(self, url):
        self.calls.append(url)
        if url == manual.REPO_URL:
            return copy.deepcopy(self.repo)
        if url == manual.rest.API + "/pulls/295":
            if self.after is not None and self.calls.count(url) == 2:
                return copy.deepcopy(self.after)
            return copy.deepcopy(self.pr)
        raise AssertionError("unexpected provider read: " + url)


def run(rest=None, graph=None, pr=295, head=HEAD, source=SOURCE_SHA):
    result = manual.observe(pr, head, rest_reader=rest or FakeRest(),
                            graph_reader=graph or FakeGraphQL(),
                            source_sha=source)
    assert result["status"] == "UNKNOWN"
    assert result["disposition"] == "HOLD"
    assert result["merge_authorized"] is False
    assert result["check_publish_authorized"] is False
    assert result["trust_activated"] is False
    assert result["execution_attestation"] == "NOT_ESTABLISHED"
    assert result["atomic_merge_attestation"] == "NOT_ESTABLISHED"
    assert result["independent_custody"] == "NOT_ESTABLISHED"
    return result


def test_stable_realistic_complete_graph_is_still_only_hold():
    r = FakeRest()
    result = run(r)
    assert result["reason"] == "PR_DRAFT_READ_ONLY_HOLD"
    assert result["review_graph_sample"] == "SAMPLED_STABLE_UNATTESTED"
    assert result["first_digest"] == result["second_digest"]
    assert len(r.calls) == 3


def test_ready_pr_is_not_merge_authority_either():
    r = FakeRest()
    r.pr["draft"] = False
    assert run(r)["reason"] == "LIVE_READ_ONLY_NON_ATOMIC_HOLD"


def test_review_edited_with_fixed_pr_timestamp_denied():
    a = original()
    b = copy.deepcopy(a)
    b["reviews"][0]["body"] = "review edited while PR metadata stays unchanged"
    assert run(graph=FakeGraphQL(a, b))["reason"] == "GRAPH_REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES"


def test_comment_deleted_with_fixed_pr_timestamp_denied():
    a = original()
    b = copy.deepcopy(a)
    b["comments"].clear()
    assert run(graph=FakeGraphQL(a, b))["reason"] == "GRAPH_REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES"


def test_thread_resolved_to_unresolved_denied():
    a = original()
    b = copy.deepcopy(a)
    b["threads"][0]["isResolved"] = False
    assert run(graph=FakeGraphQL(a, b))["reason"] == "GRAPH_REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES"


def test_pr_changed_between_graph_and_last_rest_get_denied():
    r = FakeRest()
    r.after = copy.deepcopy(r.pr)
    r.after["body"] += "\nnew text"
    assert run(r)["reason"] == "REST_PR_CHANGED_DURING_GRAPH_READ"


def test_head_mismatch_denied_before_graph_call():
    assert run(head="d" * 40)["reason"] == "REST_PR_IDENTITY_OR_HEAD_MISMATCH"


def test_rest_wrong_repo_id_denied():
    r = FakeRest()
    r.pr["base"]["repo"]["id"] = REPO_ID + 1
    assert run(r)["reason"] == "REST_PR_IDENTITY_OR_HEAD_MISMATCH"


def test_rest_bool_database_id_denied():
    r = FakeRest()
    r.pr["id"] = True
    assert run(r)["reason"] == "REST_PR_IDENTITY_OR_HEAD_MISMATCH"


def test_pr_no_longer_targets_protected_main_denied():
    r = FakeRest()
    r.pr["base"]["ref"] = "development"
    assert run(r)["reason"] == "REST_PR_BASE_OR_STATE_UNEXPECTED"


def test_bad_source_sha_denied():
    assert run(source="untrusted/source/branch")["reason"] == "INVALID_FIXED_TARGET_OR_SOURCE_SHA"


def test_graph_query_failure_denied():
    g = FakeGraphQL()
    g.graph_errors = True
    assert run(graph=g)["reason"] == "GRAPH_GRAPHQL_ERROR_OR_MISSING_PAGE"


def test_graph_403_denied():
    g = FakeGraphQL()
    g.fail_on_call = 2
    assert run(graph=g)["reason"] == "GRAPH_GRAPHQL_HTTP_403"


def test_pre_first_read_deletion_remains_unproved_even_if_samples_match():
    a = original()
    a["comments"].clear()
    result = run(graph=FakeGraphQL(a, a))
    assert result["reason"] == "PR_DRAFT_READ_ONLY_HOLD"
    assert result["independent_custody"] == "NOT_ESTABLISHED"


def test_untrusted_workflow_must_not_reference_manual_read_source():
    from pathlib import Path
    path = Path(__file__).resolve().parents[2] / ".github/workflows/ario-self-audit-lab.yml"
    assert "guard_v2_trusted_manual" not in path.read_text(encoding="utf-8")


def test_manual_workflow_never_checks_out_target_pr_code():
    from pathlib import Path
    f = Path(__file__).resolve().parents[2] / ".github/workflows/ario-guard-v2-trusted-read-manual.yml"
    source = f.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in source
    assert "pull_request_target" not in source
    assert "workflow_run" not in source
    assert "if: github.ref == 'refs/heads/main'" in source
    assert "ref: ${{ github.sha }}" in source
    assert "persist-credentials: false" in source
    assert "ARIO_TRUSTED_READ_TOKEN: ${{ github.token }}" in source
    assert "pull_request.head" not in source
    assert "pull_request.merge" not in source


# RED→GREEN real REST-class coverage: mock only urllib transport,
# not GitHubReadOnly's exact path authorization or JSON decoding.
class _NetworkResponse:
    def __init__(self, obj):
        import io
        import json
        from email.message import Message
        encoded = json.dumps(obj, separators=(",", ":")).encode("utf-8")
        self.stream = io.BytesIO(encoded)
        self.status = 200
        self.headers = Message()
        self.headers["Content-Length"] = str(len(encoded))

    def read(self, size=-1):
        return self.stream.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stream.close()
        return False


class _NetworkOpener:
    def __init__(self, model):
        self.model = model
        self.calls = []

    def open(self, request, timeout):
        self.calls.append({"url": request.full_url,
                           "method": request.get_method(),
                           "timeout": timeout})
        if request.full_url == manual.REPO_URL:
            obj = self.model.repo
        elif request.full_url == manual.rest.API + "/pulls/295":
            obj = self.model.pr
        else:
            raise AssertionError("unexpected real-reader HTTP route")
        return _NetworkResponse(obj)


def test_real_reader_exact_repository_root_get_allowed_with_mock_transport():
    real = manual.rest.GitHubReadOnly(token=None)
    transport = _NetworkOpener(FakeRest())
    real.opener = transport
    assert real.get_json(manual.REPO_URL) == {"id": REPO_ID}
    assert transport.calls == [{"url": manual.REPO_URL, "method": "GET", "timeout": 12}]


def test_real_reader_rejects_all_but_exact_repo_root_and_original_allowlist():
    import pytest
    reader = manual.rest.GitHubReadOnly(token=None)
    transport = _NetworkOpener(FakeRest())
    reader.opener = transport
    for path in (manual.REPO_URL + "/", manual.REPO_URL + "?x=1",
                 manual.REPO_URL + "/../../users/me",
                 manual.REPO_URL + "/issues/1",
                 "https://api.github.com/repos/SepehrGhanbari/ArioEVIL"):
        with pytest.raises(manual.rest.ReadUnknown):
            reader.get_json(path)
    assert transport.calls == []


def test_real_rest_class_complete_guard_probe_reaches_graph_and_records_hold():
    real = manual.rest.GitHubReadOnly(token=None)
    transport = _NetworkOpener(FakeRest())
    real.opener = transport
    graph_reader = FakeGraphQL()
    result = run(rest=real, graph=graph_reader)
    assert result["review_graph_sample"] == "SAMPLED_STABLE_UNATTESTED"
    assert result["reason"] == "PR_DRAFT_READ_ONLY_HOLD"
    assert result["first_digest"] == result["second_digest"]
    assert len(graph_reader.calls) == 6
    assert [c["url"] for c in transport.calls] == [
        manual.REPO_URL,
        manual.rest.API + "/pulls/295",
        manual.rest.API + "/pulls/295",
    ]
    assert all(c["method"] == "GET" for c in transport.calls)
    assert result["merge_authorized"] is False


def test_manual_cli_not_green_if_network_reader_never_reaches_graph(monkeypatch, capsys):
    class _EarlyFailure:
        def __init__(self, token):
            pass
        def get_json(self, url):
            raise manual.rest.ReadUnknown("FORBIDDEN_HOST")

    monkeypatch.setenv("ARIO_TRUSTED_READ_TOKEN", "synthetic-only")
    monkeypatch.setattr(manual.rest, "GitHubReadOnly", _EarlyFailure)
    monkeypatch.setattr(manual.graph, "ReadOnlyGraphQL", lambda token: FakeGraphQL())
    status = manual.main(["--pr", "295", "--expected-head", HEAD,
                          "--source-sha", SOURCE_SHA])
    assert status != 0, "No-data HOLD cannot be a green manual job"
    import json
    result = json.loads(capsys.readouterr().out)
    assert result["reason"] == "FORBIDDEN_HOST"
    assert result["merge_authorized"] is False


def test_manual_cli_complete_but_non_authoritative_graph_capture_can_exit_zero(
        monkeypatch, capsys):
    """Exit 0 means read completed, never permission to merge or activate trust."""
    import json
    actual_reader_class = manual.rest.GitHubReadOnly
    opened = _NetworkOpener(FakeRest())
    graph_reader = FakeGraphQL()

    def construct_reader(token):
        reader = actual_reader_class(token=token)
        reader.opener = opened
        return reader

    monkeypatch.setenv("ARIO_TRUSTED_READ_TOKEN", "synthetic-only")
    monkeypatch.setattr(manual.rest, "GitHubReadOnly", construct_reader)
    monkeypatch.setattr(manual.graph, "ReadOnlyGraphQL", lambda token: graph_reader)
    status = manual.main(["--pr", "295", "--expected-head", HEAD,
                          "--source-sha", SOURCE_SHA])
    result = json.loads(capsys.readouterr().out)
    assert status == 0
    assert result["reason"] == "PR_DRAFT_READ_ONLY_HOLD"
    assert result["review_graph_sample"] == "SAMPLED_STABLE_UNATTESTED"
    assert result["merge_authorized"] is False
    assert result["check_publish_authorized"] is False
    assert result["trust_activated"] is False
    assert len(opened.calls) == 3
    assert len(graph_reader.calls) == 6


def test_manual_cli_missing_token_fails_as_no_data(monkeypatch, capsys):
    import json
    monkeypatch.delenv("ARIO_TRUSTED_READ_TOKEN", raising=False)
    status = manual.main(["--pr", "295", "--expected-head", HEAD,
                          "--source-sha", SOURCE_SHA])
    result = json.loads(capsys.readouterr().out)
    assert status != 0
    assert result["reason"] == "MISSING_READ_ONLY_TOKEN"
    assert result["merge_authorized"] is False
