"""R22.5: indistinguishable histories through the real REST decoder.

A fake opener models response delivery, not a demonstrated GitHub/TLS attack.
Only synthetic state is changed. No network, tokens, real clocks or writes.
"""
import copy
import json
from email.message import Message

import pytest

import ario_repo_self_audit as mod
from test_ario_repo_self_audit import Fake, HEAD, PR
from test_guard_v2_live_link import evaluate


class Response:
    def __init__(self, body, *, age=None, status=200):
        self.status = status
        self.body = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        self.headers = Message()
        self.headers["Content-Length"] = str(len(self.body))
        self.headers["Date"] = "Tue, 24 Nov 2026 12:00:00 GMT"
        self.headers["ETag"] = '"synthetic-representation"'
        if age is not None:
            self.headers["Age"] = str(age)

    def read(self, cap):
        return self.body[:cap]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class World:
    def __init__(self, mode):
        self.mode = mode
        self.live = Fake()
        self.initial = copy.deepcopy(self.live)
        self.transcript = []
        self.events = []
        if mode == "full_replay":
            self.rerun()

    def rerun(self):
        self.live.runs["workflow_runs"][0].update(
            run_attempt=2, status="in_progress", conclusion=None)
        self.live.checks["check_runs"][0].update(
            status="in_progress", conclusion=None)
        self.events.append("RERUN_STARTED")

    def open(self, request, timeout):
        url = request.full_url
        n = len(self.transcript) + 1
        assert request.get_method() == "GET"
        assert request.get_header("Authorization") is None
        assert timeout == 12
        if self.mode == "aba" and n == 2:
            self.live.pr["body"] = "temporary different evidence"
            self.events.append("PR_A_TO_B")
        if self.mode == "aba" and n == 4:
            assert self.live.pr["body"] != self.initial.pr["body"]
            self.live.pr["body"] = self.initial.pr["body"]
            self.events.append("PR_B_TO_A")
        if self.mode in ("final_replay", "aged_cache", "visible_rerun") and n == 6:
            self.rerun()
        if self.mode == "visible_pr" and n == 5:
            self.live.pr["body"] = "visible mutation"
            self.events.append("PR_A_TO_B")

        replay = (self.mode == "full_replay" or
                  (self.mode in ("final_replay", "aged_cache") and n >= 6))
        source = self.initial if replay else self.live
        payload = source.get_json(url)
        age = 120 if self.mode == "aged_cache" and replay else None
        status = 304 if self.mode == "not_modified" and n == 6 else 200
        response = Response(payload, age=age, status=status)
        self.transcript.append((url, response.status, tuple(response.headers.items()),
                                response.body))
        return response


def sample(mode):
    world = World(mode)
    reader = mod.GitHubReadOnly()
    reader.opener = world
    return world, mod.observe(PR, HEAD, reader=reader)


def assert_no_authority(result):
    assert result["status"] == "UNKNOWN"
    assert result["merge_authorized"] is False
    assert result["memory_updated"] is False
    assert result["trust_activated"] is False
    assert result["execution_attestation"] == "NOT_ESTABLISHED"


@pytest.mark.parametrize("mode", ["aba", "final_replay", "full_replay"])
def test_different_hidden_history_same_wire_transcript_same_result(mode):
    stable, expected = sample("stable")
    other, actual = sample(mode)
    assert not stable.events
    assert other.events
    assert len(stable.transcript) == len(other.transcript) == 7
    assert stable.transcript == other.transcript
    assert actual == expected
    assert actual["required_check_observation"] == "REPORTED_SUCCESS_BY_LINKED_PR_RUN"
    assert actual["workflow_freshness"] == "SAMPLED_NOT_ATOMIC"
    if mode != "aba":
        assert other.live.runs["workflow_runs"][0]["run_attempt"] == 2
        assert other.live.runs["workflow_runs"][0]["status"] == "in_progress"
    else:
        assert other.events == ["PR_A_TO_B", "PR_B_TO_A"]
    assert_no_authority(actual)


def test_explicit_age_is_not_independent_freshness_proof():
    stable, expected = sample("stable")
    aged, actual = sample("aged_cache")
    assert aged.events == ["RERUN_STARTED"]
    assert stable.transcript != aged.transcript
    assert dict(aged.transcript[-1][2])["Age"] == "120"
    assert actual == expected  # Current decoder discards cache metadata.
    assert_no_authority(actual)


@pytest.mark.parametrize(("mode", "reason"), [
    ("visible_rerun", "CHECKS_CHANGED_DURING_OBSERVATION"),
    ("visible_pr", "PR_CHANGED_BETWEEN_SAMPLES"),
    ("not_modified", "NON_200_RESPONSE"),
])
def test_visible_changes_or_304_do_not_preserve_positive(mode, reason):
    _, actual = sample(mode)
    assert actual["required_check_observation"] == "NOT_CONFIRMED"
    assert actual["reason"] == reason
    assert_no_authority(actual)


@pytest.mark.parametrize("mode", ["stable", "aba", "final_replay", "full_replay",
                                 "aged_cache", "visible_rerun", "not_modified"])
def test_output_never_conflates_sample_agreement_with_freshness(mode):
    _, actual = sample(mode)
    assert actual["source_freshness"] == "NOT_ESTABLISHED"
    assert actual["history_continuity"] == "NOT_ESTABLISHED"


def test_bridge_preserves_ci_freshness_boundary_on_reviewable_only():
    actual = evaluate()
    assert actual["disposition"] == "REVIEWABLE_ONLY"
    assert actual["ci_sample_freshness"] == "SAMPLED_NOT_ATOMIC"
    assert actual["ci_source_freshness"] == "NOT_ESTABLISHED"
    assert actual["ci_history_continuity"] == "NOT_ESTABLISHED"
    assert actual["merge_authorized"] is False
    assert actual["trust_activated"] is False
