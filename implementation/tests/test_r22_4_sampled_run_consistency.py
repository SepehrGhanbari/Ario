"""R22.4: distinguish the selected run from other sampled canonical evidence.

All cases are deterministic, offline, and non-authoritative.
"""
import copy

import pytest

from test_ario_repo_self_audit import Fake, call


class OlderCanonicalRun(Fake):
    def __init__(self, mutation):
        super().__init__()
        self.mutation = mutation
        self.reads = 0
        older = copy.deepcopy(self.runs["workflow_runs"][0])
        older.update(id=99, run_number=9)
        if mutation == "stable_failed":
            older["conclusion"] = "failure"
        self.runs["workflow_runs"].append(older)
        self.runs["total_count"] = 2

    def get_json(self, url):
        result = super().get_json(url)
        if "/actions/runs?" not in url:
            return result
        self.reads += 1
        if self.reads != 2:
            return result
        older = result["workflow_runs"][1]
        if self.mutation == "rerun":
            older.update(run_attempt=2, status="in_progress", conclusion=None)
        elif self.mutation == "failed_rerun":
            older.update(run_attempt=2, status="completed", conclusion="failure")
        elif self.mutation == "delete":
            result["workflow_runs"].pop()
            result["total_count"] -= 1
        elif self.mutation == "add":
            added = copy.deepcopy(older)
            added.update(id=98, run_number=8)
            result["workflow_runs"].append(added)
            result["total_count"] += 1
        elif self.mutation == "path":
            older["path"] += "@refs/heads/other"
        elif self.mutation == "presentation":
            older["display_title"] = "metadata only"
            result["workflow_runs"].reverse()
        return result


@pytest.mark.parametrize("mutation", [
    "rerun", "failed_rerun", "delete", "add", "path",
])
def test_nonselected_canonical_run_drift_is_not_silently_ignored(mutation):
    result = call(OlderCanonicalRun(mutation))
    assert result["status"] == "UNKNOWN"
    assert result["required_check_observation"] == "NOT_CONFIRMED"
    assert result["reason"] == "RUNS_CHANGED_DURING_OBSERVATION"
    assert "linked_runs" not in result
    assert result["merge_authorized"] is False


@pytest.mark.parametrize("mutation", ["stable_failed", "presentation"])
def test_stable_older_run_does_not_change_current_run_policy(mutation):
    result = call(OlderCanonicalRun(mutation))
    assert result["status"] == "UNKNOWN"
    assert result["required_check_observation"] == "REPORTED_SUCCESS_BY_LINKED_PR_RUN"
    assert result["workflow_freshness"] == "SAMPLED_NOT_ATOMIC"
    assert result["merge_authorized"] is False
