"""Guard V2 + Ario live self-audit: synthetic replay, not an operational merge test."""
from __future__ import annotations

import copy
import pytest

import ario_repo_self_audit as selfaudit
from research import guard_v2_live_link as link
from test_guard_v2_pr_scope import BASE, HEAD, PR14_ID, PR15_ID, PR16_ID, REPO, checks, pin, snapshot
from test_guard_v2_review_graph import FakeGraphQL, original as graph_original


class FakeReader:
    """Only the three genuine #295 GitHub GET URL shapes, zero writes."""

    def __init__(self, pr_number=14, pr_id=PR14_ID):
        self.pr_number = pr_number
        self.raw = {
            "id": pr_id, "number": pr_number,
            "head": {"sha": HEAD},
            "base": {"sha": BASE, "repo": {"id": REPO}},
            "body": "Pinned synthetic review body", "updated_at": "2026-11-21T18:00:00Z",
            "draft": False, "state": "open",
        }
        self.checks = {"total_count": 1, "check_runs": [
            {"id": 41, "name": "m0-regression", "head_sha": HEAD,
             "status": "completed", "conclusion": "success",
             "app": {"id": 15368},
             "details_url": "https://github.com/SepehrGhanbari/Ario/actions/runs/83/job/41"},
        ]}
        self.runs = {"total_count": 1, "workflow_runs": [
            {"id": 83, "workflow_id": 4242, "run_number": 10,
             "run_attempt": 1, "head_sha": HEAD, "event": "pull_request",
             "status": "completed", "conclusion": "success",
             "pull_requests": [{"id": pr_id, "number": pr_number,
                                "head": {"sha": HEAD}}]},
        ]}
        self.pr_reads = 0
        self.log = []
        self.versions = {}
        self.fail_at = None

    def get_json(self, url):
        self.log.append(url)
        if self.fail_at == len(self.log):
            raise selfaudit.ReadUnknown("GITHUB_HTTP_403")
        if url == selfaudit.API + f"/pulls/{self.pr_number}":
            self.pr_reads += 1
            return copy.deepcopy(self.versions.get(self.pr_reads, self.raw))
        if url == selfaudit.API + f"/commits/{HEAD}/check-runs?per_page=100":
            return copy.deepcopy(self.checks)
        if url == (selfaudit.API + f"/actions/runs?head_sha={HEAD}"
                   + "&event=pull_request&per_page=100"):
            return copy.deepcopy(self.runs)
        raise AssertionError("unexpected URL " + url)


def evaluate(fake=None, **kwargs):
    result = link.examine(pin(), reader=fake or FakeReader(),
                          first=kwargs.pop("first", snapshot()),
                          last=kwargs.pop("last", snapshot()),
                          checks=kwargs.pop("checks", checks()), **kwargs)
    assert result["status"] == "UNKNOWN"
    assert result["merge_authorized"] is False
    assert result["check_publish_authorized"] is False
    assert result["trust_activated"] is False
    assert result["execution_attestation"] == "NOT_ESTABLISHED"
    return result


def test_live_pr_ci_and_synthetic_matching_guard_stays_reviewable_only():
    fake = FakeReader()
    r = evaluate(fake)
    assert r["disposition"] == "REVIEWABLE_ONLY"
    assert r["ci_observation"] == "REPORTED_SUCCESS_BY_LINKED_PR_RUN"
    assert fake.pr_reads == 4
    assert len(fake.log) == 6


def test_without_live_review_evidence_stays_hold():
    r = link.examine(pin(), reader=FakeReader())
    assert r["disposition"] == "HOLD"
    assert r["reason"] == "REVIEW_AND_APP_EVIDENCE_NOT_CAPTURED"
    assert r["ci_observation"] == "REPORTED_SUCCESS_BY_LINKED_PR_RUN"


def test_post_observation_pr_body_change_immediately_before_decision_is_hold():
    fake = FakeReader()
    edited = copy.deepcopy(fake.raw)
    edited["body"] += "\nPost-check evidence changed"
    fake.versions[4] = edited
    r = evaluate(fake)
    assert r["disposition"] == "HOLD"
    assert r["reason"] == "LIVE_PR_CHANGED_BEFORE_DECISION"


def test_post_observation_comment_only_change_with_updated_at_is_hold():
    fake = FakeReader()
    edited = copy.deepcopy(fake.raw)
    edited["updated_at"] = "2026-11-21T18:04:00Z"
    fake.versions[4] = edited
    r = evaluate(fake)
    assert r["reason"] == "LIVE_PR_CHANGED_BEFORE_DECISION"


def test_changed_review_comment_between_supplied_snapshots_is_hold():
    last = snapshot()
    last["evidence"]["comments"]["nodes"][0]["body"] = "Synthetic Critical found just before decision"
    r = evaluate(last=last)
    assert r["reason"] == "GUARD_SNAPSHOT_CHANGED_BETWEEN_READS"


def test_unchanged_forged_snapshots_are_not_independent_attestation():
    r = evaluate()
    assert r["disposition"] == "REVIEWABLE_ONLY"
    assert r["review_freshness"] == "NOT_ATTESTED_BY_LIVE_GITHUB_READ"


@pytest.mark.parametrize("pr_number,pr_id", [(15, PR15_ID), (16, PR16_ID)])
def test_real_shared_sha_app_check_bound_to_old_pr_is_hold(pr_number, pr_id, monkeypatch):
    """Must reach Guard Check matching, not fail the earlier PR-identity read."""
    fake = FakeReader(pr_number=pr_number, pr_id=pr_id)
    seen = []
    original_assess = link.guard.assess

    def trace_assess(pin_arg, first_arg, last_arg, checks_arg, self_audit=None):
        seen.append((pin_arg["pr_number"], pin_arg["pr_id"]))
        return original_assess(pin_arg, first_arg, last_arg, checks_arg,
                               self_audit=self_audit)

    monkeypatch.setattr(link.guard, "assess", trace_assess)
    r = link.examine(pin(pr_number, pr_id), reader=fake,
                     first=snapshot(pr_number, pr_id),
                     last=snapshot(pr_number, pr_id), checks=checks())
    assert r["reason"] == "GUARD_CHECK_PR_ID_MISMATCH"
    assert r["disposition"] == "HOLD"
    assert r["merge_authorized"] is False
    assert seen == [(pr_number, pr_id)]
    assert fake.pr_reads == 4
    assert fake.log.count(selfaudit.API + f"/pulls/{pr_number}") == 4


@pytest.mark.parametrize("pr_number,pr_id", [(15, PR15_ID), (16, PR16_ID)])
def test_shared_sha_check_reissued_for_exact_destination_is_only_reviewable(pr_number, pr_id):
    """Positive control: correct destination IDs must reach Guard, never authorize merge."""
    fake = FakeReader(pr_number=pr_number, pr_id=pr_id)
    result = link.examine(pin(pr_number, pr_id), reader=fake,
                          first=snapshot(pr_number, pr_id),
                          last=snapshot(pr_number, pr_id),
                          checks=checks(original_pr=pr_number, original_id=pr_id))
    assert result["reason"] == "LIVE_PR_AND_SUPPLIED_LAB_METADATA_CORRESPOND"
    assert result["disposition"] == "REVIEWABLE_ONLY"
    assert result["merge_authorized"] is False
    assert result["review_freshness"] == "NOT_ATTESTED_BY_LIVE_GITHUB_READ"
    assert fake.pr_reads == 4


def test_stale_head_just_before_decision_is_hold():
    fake = FakeReader()
    edited = copy.deepcopy(fake.raw)
    edited["head"]["sha"] = "f" * 40
    fake.versions[4] = edited
    r = evaluate(fake)
    assert r["reason"] == "LIVE_PR_REVISION_MISMATCH"


def test_stale_base_just_before_decision_is_hold():
    fake = FakeReader()
    edited = copy.deepcopy(fake.raw)
    edited["base"]["sha"] = "f" * 40
    fake.versions[4] = edited
    r = evaluate(fake)
    assert r["reason"] == "LIVE_PR_REVISION_MISMATCH"


@pytest.mark.parametrize("bad_id", [float(REPO), str(REPO), True])
def test_live_repository_numeric_aliases_fail_closed(bad_id):
    fake = FakeReader()
    fake.raw["base"]["repo"]["id"] = bad_id
    r = evaluate(fake)
    assert r["reason"] == "INVALID_LIVE_REPOSITORY_ID"


def test_missing_live_repo_id_fails_closed():
    fake = FakeReader()
    fake.raw["base"]["repo"] = None
    r = evaluate(fake)
    assert r["reason"] == "INVALID_LIVE_REPOSITORY_ID"


def test_draft_live_pr_does_not_get_reviewable_only():
    fake = FakeReader()
    fake.raw["draft"] = True
    r = evaluate(fake)
    assert r["reason"] == "LIVE_PR_NOT_READY"


def test_incomplete_or_pending_pr_ci_does_not_pass_bridge():
    fake = FakeReader()
    fake.runs["workflow_runs"][0].update(status="in_progress", conclusion=None)
    r = evaluate(fake)
    assert r["reason"] == "LINKED_PR_CI_NOT_CONFIRMED"


def test_live_reader_403_is_hold():
    fake = FakeReader()
    fake.fail_at = 2
    r = evaluate(fake)
    assert r["disposition"] == "HOLD"
    assert r["reason"] in {"GITHUB_HTTP_403", "SELF_AUDIT_SAMPLES_UNCONFIRMED"}


def test_changed_live_db_id_at_final_read_is_hold():
    fake = FakeReader()
    edited = copy.deepcopy(fake.raw)
    edited["id"] = PR15_ID
    fake.versions[4] = edited
    r = evaluate(fake)
    assert r["reason"] == "LIVE_PR_IDENTITY_MISMATCH"


def test_incorrect_lab_check_app_binding_is_hold():
    fake_checks = checks()
    fake_checks["check_runs"][0]["app"]["id"] = 15368
    r = evaluate(checks=fake_checks)
    assert r["reason"] == "GUARD_MISSING_OR_AMBIGUOUS_APP_CHECK"


def test_wrong_app_id_numeric_alias_is_hold():
    fake_checks = checks()
    fake_checks["check_runs"][0]["app"]["id"] = 5747504.0
    r = evaluate(checks=fake_checks)
    assert r["reason"] == "GUARD_MISSING_OR_AMBIGUOUS_APP_CHECK"


def test_self_audit_cannot_grant_authority(monkeypatch):
    def spoof(*args, **kwargs):
        return {"status": "MATCH", "merge_authorized": True,
                "required_check_observation": "REPORTED_SUCCESS_BY_LINKED_PR_RUN"}
    monkeypatch.setattr(selfaudit, "observe", spoof)
    r = evaluate()
    assert r["reason"] == "INVALID_SELF_AUDIT_AUTHORITY"


def test_bad_pin_rejected_before_any_get():
    fake = FakeReader()
    malformed = pin()
    malformed["pr_id"] = True
    r = link.examine(malformed, reader=fake)
    assert r["reason"] == "INVALID_PIN_PR_ID"
    assert fake.log == []


def graph_for_guard_pr(before=None, after=None):
    """Bind GraphQL fixture to the identical PR14 identity used by the live fake."""
    result = FakeGraphQL(before, after)
    result.repo_id = str(REPO)
    result.pr_id = str(PR14_ID)
    result.pr_number = 14
    result.head = HEAD
    result.base = BASE
    return result


@pytest.mark.parametrize("family", ["comments", "reviews", "threads"])
def test_hidden_review_change_detected_despite_constant_pr_updated_at(family):
    first_graph = graph_original()
    last_graph = copy.deepcopy(first_graph)
    if family == "comments":
        last_graph["comments"][0]["body"] = "Edited without PR timestamp change"
    elif family == "reviews":
        last_graph["reviews"][0]["body"] = "Review edited silently"
    else:
        last_graph["threads"][0]["isResolved"] = False
    fake = FakeReader()
    result = evaluate(fake, review_graph_reader=graph_for_guard_pr(first_graph, last_graph))
    assert result["disposition"] == "HOLD"
    assert result["reason"] == "GRAPH_FRESHNESS_REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES"
    assert fake.pr_reads == 3  # no false final agreement or Guard check
    assert fake.raw["updated_at"] == "2026-11-21T18:00:00Z"


def test_comment_deleted_without_pr_timestamp_bump_is_hold():
    first_graph = graph_original()
    last_graph = copy.deepcopy(first_graph)
    last_graph["comments"].clear()
    fake = FakeReader()
    result = evaluate(fake, review_graph_reader=graph_for_guard_pr(first_graph, last_graph))
    assert result["reason"] == "GRAPH_FRESHNESS_REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES"
    assert result["review_graph_status"] == "UNKNOWN"
    assert result["merge_authorized"] is False


def test_graph_403_is_hold_even_if_pr_ci_is_reported_success():
    fake_graph = graph_for_guard_pr()
    fake_graph.fail_on_call = 4
    result = evaluate(review_graph_reader=fake_graph)
    assert result["reason"] == "GRAPH_FRESHNESS_GRAPHQL_HTTP_403"
    assert result["ci_observation"] == "REPORTED_SUCCESS_BY_LINKED_PR_RUN"


def test_complete_same_graph_two_reads_are_only_sampled_and_non_authoritative():
    result = evaluate(review_graph_reader=graph_for_guard_pr())
    assert result["review_graph_status"] == "SAMPLED_STABLE_UNATTESTED"
    assert result["review_freshness"] == "SAMPLED_STABLE_UNATTESTED"
    assert result["disposition"] == "REVIEWABLE_ONLY"  # only supplied synthetic Guard records
    assert result["merge_authorized"] is False
    assert result["check_publish_authorized"] is False
    assert result["execution_attestation"] == "NOT_ESTABLISHED"


def test_absent_real_graph_reader_remains_unknown_freshness_and_no_merge():
    result = evaluate()
    assert result["review_freshness"] == "NOT_ATTESTED_BY_LIVE_GITHUB_READ"
    assert result["merge_authorized"] is False
