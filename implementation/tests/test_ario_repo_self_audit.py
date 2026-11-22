"""Source-level PR/check/run self-observation with injected GitHub API responses."""
from __future__ import annotations
import copy
import json
from email.message import Message
from unittest.mock import Mock
import pytest
import ario_repo_self_audit as mod

HEAD = "c" * 40
BASE = "b" * 40
PR = 295


class Fake:
    def __init__(self):
        self.pr = {
            "id": 987, "number": PR, "head": {"sha": HEAD},
            "base": {"sha": BASE}, "draft": True, "state": "open", "body": "claim",
        }
        self.checks = {"total_count": 2, "check_runs": [
            {"id": 1, "name": "m0-regression", "head_sha": HEAD,
             "status": "completed", "conclusion": "success", "app": {"id": 15368},
             "details_url": "https://github.com/SepehrGhanbari/Ario/actions/runs/100/job/1"},
            {"id": 2, "name": "advisory", "head_sha": HEAD,
             "status": "in_progress", "conclusion": None, "app": {"id": 15368}},
        ]}
        self.runs = {"total_count": 1, "workflow_runs": [{
            "id": 100, "workflow_id": 379498305, "path": ".github/workflows/implementation-regression.yml", "run_number": 10,
            "run_attempt": 1, "head_sha": HEAD,
            "event": "pull_request", "status": "completed", "conclusion": "success",
            "pull_requests": [{"id": 987, "number": PR, "head": {"sha": HEAD}}],
        }]}
        self.jobs = {"total_count": 1, "jobs": [{
            "id": 1, "run_id": 100, "run_attempt": 1, "head_sha": HEAD,
            "name": "m0-regression", "status": "completed", "conclusion": "success",
        }]}
        self.calls = []
        self.next_pr = None
        self.fail_at = None

    def get_json(self, url):
        self.calls.append(url)
        if self.fail_at == len(self.calls):
            raise mod.ReadUnknown("GITHUB_HTTP_403")
        if url.endswith("/pulls/295"):
            if sum(x.endswith("/pulls/295") for x in self.calls) == 2:
                return copy.deepcopy(self.next_pr or self.pr)
            return copy.deepcopy(self.pr)
        if "/check-runs?" in url:
            return copy.deepcopy(self.checks)
        if "/actions/runs?" in url:
            return copy.deepcopy(self.runs)
        if "/attempts/" in url and "/jobs?" in url:
            return copy.deepcopy(self.jobs)
        raise AssertionError("unexpected URL " + url)


def call(fake=None):
    return mod.observe(PR, HEAD, reader=fake or Fake())


def test_bound_pr_and_checks_remain_non_authoritative():
    f = Fake()
    result = call(f)
    assert len(f.calls) == 4
    assert result["pr_sample_consistency"] == "SAME_AT_TWO_SAMPLED_READS"
    assert result["required_check_observation"] == "REPORTED_SUCCESS_BY_LINKED_PR_RUN"
    assert result["linked_run_count"] == 1
    assert result["status"] == "UNKNOWN"
    assert result["execution_attestation"] == "NOT_ESTABLISHED"
    assert result["evidence_admission"] == "NOT_EVALUATED"
    assert result["merge_authorized"] is False and result["memory_updated"] is False


@pytest.mark.parametrize(("field", "value"), [
    ("id", 988), ("number", 296), ("body", "edited"),
    ("state", "closed"), ("draft", False),
])
def test_final_change_discards_positive_diagnostics(field, value):
    f = Fake()
    f.next_pr = copy.deepcopy(f.pr)
    f.next_pr[field] = value
    r = call(f)
    assert r["reason"] == ("INVALID_PR_IDENTITY" if field == "number" else "PR_CHANGED_BETWEEN_SAMPLES")
    assert r["required_check_observation"] == "NOT_CONFIRMED"
    assert "checks" not in r


def test_final_head_changed():
    f = Fake()
    f.next_pr = copy.deepcopy(f.pr)
    f.next_pr["head"]["sha"] = "f" * 40
    assert call(f)["reason"] == "PR_CHANGED_BETWEEN_SAMPLES"


def test_initial_head_drift_stops_before_check_get():
    f = Fake()
    r = mod.observe(PR, "d" * 40, reader=f)
    assert r["reason"] == "PR_HEAD_CHANGED"
    assert len(f.calls) == 1


@pytest.mark.parametrize("conclusion", ["failure", "neutral", "skipped", None])
def test_non_success_is_not_pass(conclusion):
    f = Fake()
    f.checks["check_runs"][0]["conclusion"] = conclusion
    if conclusion is None:
        f.checks["check_runs"][0]["status"] = "in_progress"
    assert call(f)["required_check_observation"] == "NOT_CONFIRMED"


def test_wrong_app_not_pass():
    f = Fake()
    f.checks["check_runs"][0]["app"]["id"] = 3
    assert call(f)["required_check_observation"] == "NOT_CONFIRMED"


def test_wrong_head_check_or_duplicate_id_refused():
    f = Fake()
    f.checks["check_runs"][0]["head_sha"] = "f" * 40
    assert call(f)["reason"] == "INVALID_OR_DUPLICATE_CHECK"
    f = Fake()
    f.checks["check_runs"][1]["id"] = 1
    assert call(f)["reason"] == "INVALID_OR_DUPLICATE_CHECK"


@pytest.mark.parametrize("which", ["checks", "runs"])
def test_incomplete_pages_are_unknown(which):
    f = Fake()
    getattr(f, which)["total_count"] += 1
    assert call(f)["status"] == "UNKNOWN"
    assert call(f)["required_check_observation"] == "NOT_CONFIRMED"


def test_wrong_pr_binding_is_not_a_linked_run():
    f = Fake()
    f.runs["workflow_runs"][0]["pull_requests"][0]["id"] = 2000
    result = call(f)
    assert result["reason"] == "RUN_PR_ASSOCIATION_MISMATCH"
    assert result["required_check_observation"] == "NOT_CONFIRMED"


def test_http_403_is_unknown():
    f = Fake()
    f.fail_at = 2
    r = call(f)
    assert r["reason"] == "GITHUB_HTTP_403"
    assert r["required_check_observation"] == "NOT_CONFIRMED"


def test_non_ario_target_cannot_touch_reader():
    f = Fake()
    r = mod.observe(PR, HEAD, repository="another/repo", reader=f)
    assert r["reason"] == "INVALID_FIXED_TARGET"
    assert f.calls == []


@pytest.mark.parametrize("url", [
    "https://evil.example/repos/SepehrGhanbari/Ario/pulls/1",
    mod.API + "/pulls/1/merge",
    mod.API + "/user",
    "http://api.github.com/repos/SepehrGhanbari/Ario/pulls/1",
])
def test_unsafe_url_is_refused_before_network(url):
    reader = mod.GitHubReadOnly()
    reader.opener = Mock()
    with pytest.raises(mod.ReadUnknown):
        reader.get_json(url)
    reader.opener.open.assert_not_called()


def test_strict_json_rejects_duplicate_members():
    raw = b'{"id":1,"id":2}'
    headers = Message()
    headers.add_header("Content-Length", str(len(raw)))
    class Response:
        status = 200
        def __init__(self):
            self.headers = headers
        def __enter__(self):
            return self
        def __exit__(self, *exc):
            return None
        def read(self, maximum):
            return raw
    reader = mod.GitHubReadOnly()
    reader.opener = Mock()
    reader.opener.open.return_value = Response()
    with pytest.raises(mod.ReadUnknown, match="INVALID_API_JSON"):
        reader.get_json(mod.API + "/pulls/1")


def test_bad_sha_cli_never_reads_network(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("called network")
    monkeypatch.setattr(mod, "GitHubReadOnly", forbidden)
    assert mod.main(["--pr", "295", "--expected-head", "invalid"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["status"] == "UNKNOWN" and value["merge_authorized"] is False


# Security regression: a passing push job cannot masquerade as the PR job.
def test_push_success_does_not_mask_failed_pr_job():
    f = Fake()
    f.checks["check_runs"][0]["details_url"] = (
        "https://github.com/SepehrGhanbari/Ario/actions/runs/200/job/1"
    )
    f.checks["check_runs"].append({
        "id": 3, "name": "m0-regression", "head_sha": HEAD,
        "status": "completed", "conclusion": "failure", "app": {"id": 15368},
        "details_url": "https://github.com/SepehrGhanbari/Ario/actions/runs/100/job/3",
    })
    f.checks["total_count"] = 3
    f.runs["workflow_runs"][0]["conclusion"] = "failure"
    assert call(f)["required_check_observation"] == "NOT_CONFIRMED"


def test_push_success_cannot_mask_in_progress_pr_job():
    f = Fake()
    f.checks["check_runs"][0]["details_url"] = (
        "https://github.com/SepehrGhanbari/Ario/actions/runs/200/job/1"
    )
    f.checks["check_runs"].append({
        "id": 3, "name": "m0-regression", "head_sha": HEAD,
        "status": "in_progress", "conclusion": None, "app": {"id": 15368},
        "details_url": "https://github.com/SepehrGhanbari/Ario/actions/runs/100/job/3",
    })
    f.checks["total_count"] = 3
    f.runs["workflow_runs"][0].update(status="in_progress", conclusion=None)
    assert call(f)["required_check_observation"] == "NOT_CONFIRMED"


@pytest.mark.parametrize("url", [
    "https://example.org/actions/runs/100/job/1",
    "https://github.com/SepehrGhanbari/Ario/actions/runs/999/job/1",
    "https://github.com/SepehrGhanbari/Ario/actions/runs/100/job/123",
    "https://github.com/Other/Ario/actions/runs/100/job/1",
    None,
])
def test_mismatched_job_details_not_a_success(url):
    f = Fake()
    f.checks["check_runs"][0]["details_url"] = url
    assert call(f)["required_check_observation"] == "NOT_CONFIRMED"


def test_completed_pr_run_failure_not_confirmed_even_with_success_job():
    f = Fake()
    f.runs["workflow_runs"][0]["conclusion"] = "failure"
    assert call(f)["required_check_observation"] == "NOT_CONFIRMED"


def test_more_than_one_pr_regression_job_is_not_a_unique_success():
    f = Fake()
    f.checks["check_runs"].append({
        "id": 3, "name": "m0-regression", "head_sha": HEAD,
        "status": "completed", "conclusion": "success", "app": {"id": 15368},
        "details_url": "https://github.com/SepehrGhanbari/Ario/actions/runs/100/job/3",
    })
    f.checks["total_count"] = 3
    assert call(f)["required_check_observation"] == "NOT_CONFIRMED"


def test_duplicate_run_id_is_rejected():
    f = Fake()
    f.runs["workflow_runs"].append(copy.deepcopy(f.runs["workflow_runs"][0]))
    f.runs["total_count"] = 2
    result = call(f)
    assert result["reason"] == "INVALID_RUN"
    assert result["required_check_observation"] == "NOT_CONFIRMED"


@pytest.mark.parametrize(("status", "conclusion"), [
    ("in_progress", "success"),
    ("completed", None),
])
def test_incoherent_check_state_is_unknown(status, conclusion):
    f = Fake()
    f.checks["check_runs"][0].update(status=status, conclusion=conclusion)
    assert call(f)["reason"] == "INVALID_OR_DUPLICATE_CHECK"


@pytest.mark.parametrize(("status", "conclusion"), [
    ("in_progress", "success"),
    ("completed", None),
])
def test_incoherent_pr_run_state_is_unknown(status, conclusion):
    f = Fake()
    f.runs["workflow_runs"][0].update(status=status, conclusion=conclusion)
    assert call(f)["reason"] == "INVALID_RUN"


# R22: a prior green run must not qualify when the same workflow has a newer run.
@pytest.mark.parametrize(("status", "conclusion"), [
    ("queued", None),
    ("in_progress", None),
    ("completed", "failure"),
])
def test_older_green_run_does_not_mask_newer_same_workflow_run(status, conclusion):
    f = Fake()
    newer = copy.deepcopy(f.runs["workflow_runs"][0])
    newer.update(id=101, run_number=11, status=status, conclusion=conclusion)
    f.runs["workflow_runs"].append(newer)
    f.runs["total_count"] = 2

    result = call(f)
    assert result["required_check_observation"] == "NOT_CONFIRMED"
    assert result["linked_run_count"] == 2


def test_latest_successful_same_workflow_run_can_be_confirmed():
    f = Fake()
    newer = copy.deepcopy(f.runs["workflow_runs"][0])
    newer.update(id=101, run_number=11)
    f.runs["workflow_runs"].append(newer)
    f.runs["total_count"] = 2

    latest_check = copy.deepcopy(f.checks["check_runs"][0])
    latest_check.update(
        id=3,
        details_url="https://github.com/SepehrGhanbari/Ario/actions/runs/101/job/3",
    )
    f.checks["check_runs"] = [latest_check]
    f.checks["total_count"] = 1

    assert call(f)["required_check_observation"] == "REPORTED_SUCCESS_BY_LINKED_PR_RUN"


def test_newer_run_from_another_workflow_does_not_shadow_target_workflow():
    f = Fake()
    other = copy.deepcopy(f.runs["workflow_runs"][0])
    other.update(id=101, workflow_id=9999, run_number=1,
                 status="queued", conclusion=None)
    f.runs["workflow_runs"].append(other)
    f.runs["total_count"] = 2

    assert call(f)["required_check_observation"] == "REPORTED_SUCCESS_BY_LINKED_PR_RUN"


@pytest.mark.parametrize("field", ["workflow_id", "run_number"])
def test_workflow_run_requires_positive_workflow_and_run_numbers(field):
    f = Fake()
    f.runs["workflow_runs"][0].pop(field)
    result = call(f)
    assert result["reason"] == "INVALID_RUN"
    assert result["required_check_observation"] == "NOT_CONFIRMED"



@pytest.mark.parametrize("links", [None, []])
def test_missing_or_empty_run_pr_association_cannot_leave_old_green_eligible(links):
    f = Fake()
    newer = copy.deepcopy(f.runs["workflow_runs"][0])
    newer.update(id=101, run_number=11, status="queued", conclusion=None,
                 pull_requests=links)
    f.runs["workflow_runs"].append(newer)
    f.runs["total_count"] = 2

    result = call(f)
    assert result["reason"] == "RUN_PR_ASSOCIATION_INCOMPLETE"
    assert result["required_check_observation"] == "NOT_CONFIRMED"



def test_newer_run_with_mismatched_target_pr_link_fails_closed():
    f = Fake()
    newer = copy.deepcopy(f.runs["workflow_runs"][0])
    newer.update(id=101, run_number=11, status="queued", conclusion=None)
    newer["pull_requests"][0]["head"]["sha"] = "d" * 40
    f.runs["workflow_runs"].append(newer)
    f.runs["total_count"] = 2

    result = call(f)
    assert result["reason"] == "RUN_PR_ASSOCIATION_MISMATCH"
    assert result["required_check_observation"] == "NOT_CONFIRMED"


# R22.1 RED controls: same-named checks from noncanonical workflows must not qualify.
def test_same_named_green_job_from_different_workflow_is_not_confirmed():
    f = Fake()
    f.runs["workflow_runs"][0].update(
        workflow_id=4242, path=".github/workflows/other.yml"
    )
    result = call(f)
    assert result["required_check_observation"] == "NOT_CONFIRMED"


def test_canonical_workflow_id_with_wrong_path_is_not_confirmed():
    f = Fake()
    f.runs["workflow_runs"][0]["path"] = ".github/workflows/renamed-or-other.yml"
    result = call(f)
    assert result["required_check_observation"] == "NOT_CONFIRMED"


# The latest run record says attempt 2. The check still points to the old
# attempt-1 job ID; attempt 2 owns a different job ID and is green.
def test_prior_attempt_check_cannot_stand_in_for_latest_attempt_job():
    f = Fake()
    f.runs["workflow_runs"][0]["run_attempt"] = 2
    f.jobs = {"total_count": 1, "jobs": [{
        "id": 3, "run_id": 100, "run_attempt": 2, "head_sha": HEAD,
        "name": "m0-regression", "status": "completed", "conclusion": "success",
    }]}
    result = call(f)
    assert result["required_check_observation"] == "NOT_CONFIRMED"
