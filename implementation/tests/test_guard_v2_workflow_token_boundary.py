"""Static negative controls for Guard V2 PR-checkout workflow.

These tests run on PR-controlled code and are advisory only; a trusted external
policy must enforce source and token provenance for any operational gate.
"""
from __future__ import annotations

from pathlib import Path
import re


WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ario-self-audit-lab.yml"


def workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_untrusted_pr_checkout_never_receives_github_read_token():
    text = workflow()
    assert "ARIO_GITHUB_READ_TOKEN" not in text
    assert "github.token" not in text.lower()
    assert "${{ secrets." not in text.lower()
    assert "GH_TOKEN:" not in text
    assert "GITHUB_TOKEN:" not in text


def test_untrusted_pr_workflow_has_only_read_contents_permission():
    text = workflow()
    assert re.search(r"(?m)^permissions:\s*\n  contents: read\s*$", text)
    for capability in ("actions", "checks", "pull-requests", "issues", "deployments", "statuses"):
        assert not re.search(r"(?m)^  " + re.escape(capability) + r":", text)
    assert "persist-credentials: false" in text


def test_no_privileged_triggers_in_pr_checkout_workflow():
    text = workflow()
    assert re.search(r"(?m)^on:\s*\n  pull_request:", text)
    assert "pull_request_target" not in text
    assert "workflow_run" not in text
    assert "issue_comment" not in text


def test_untrusted_workflow_keeps_synthetic_negative_controls():
    text = workflow()
    assert "tests/test_ario_repo_self_audit.py" in text
    assert "tests/test_guard_v2_pr_scope.py" in text
    assert "tests/test_guard_v2_live_link.py" in text
    assert "tests/test_guard_v2_review_graph.py" in text
    assert "persist-credentials: false" in text
