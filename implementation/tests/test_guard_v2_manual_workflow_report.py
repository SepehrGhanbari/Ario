"""Synthetic Bash execution of the real staged workflow run block, with fake CLI."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest

WF = Path(__file__).resolve().parents[2] / ".github/workflows/ario-guard-v2-trusted-read-manual.yml"
NEEDS_BASH = sys.platform != "win32" and shutil.which("bash") is not None


def diagnostic(reason, complete=False):
    report = {
        "schema": "ARIO-GUARD-V2-TRUSTED-MANUAL-READ-LAB-0.1",
        "status": "UNKNOWN",
        "disposition": "HOLD",
        "reason": reason,
        "merge_authorized": False,
        "check_publish_authorized": False,
        "trust_activated": False,
        "execution_attestation": "NOT_ESTABLISHED",
        "independent_custody": "NOT_ESTABLISHED",
        "atomic_merge_attestation": "NOT_ESTABLISHED",
        "source_provenance": "PROVIDED_BY_CALLER_NOT_INDEPENDENTLY_VERIFIED",
    }
    if complete:
        report.update({
            "source_commit_sha": "b" * 40,
            "review_graph_sample": "SAMPLED_STABLE_UNATTESTED",
            "review_graph_reason": "TWO_COMPLETE_GRAPH_SAMPLES_MATCH",
            "review_freshness": "TWO_SAMPLED_GRAPHS_MATCH_NON_ATOMIC",
            "first_digest": "c" * 64,
            "second_digest": "c" * 64,
            "live_identity": {
                "repository_id": 1401709791,
                "pr_id": 5402535550,
                "pr_number": 295,
                "head_sha": "a" * 40,
                "base_sha": "d" * 40,
            },
        })
    return json.dumps(report, sort_keys=True) + "\n"

def script():
    text = WF.read_text(encoding="utf-8")
    assert text.count("        run: |\n") == 1
    raw = text.split("        run: |\n", 1)[1].splitlines()
    assert all(not line.strip() or line.startswith("          ") for line in raw)
    return "\n".join(line[10:] if line.strip() else "" for line in raw) + "\n"

def execute(tmp_path, output, exit_code):
    (tmp_path / "implementation").mkdir()
    # Keep the fake reader isolated, but run the real report validator in a
    # copy of the expected package path. This tests actual JSON decoding.
    research = tmp_path / "implementation" / "research"
    research.mkdir()
    (research / "__init__.py").write_text("", encoding="utf-8")
    shutil.copyfile(Path(__file__).resolve().parents[1] / "research" /
                    "guard_v2_manual_report.py",
                    research / "guard_v2_manual_report.py")
    binary = tmp_path / "bin"
    binary.mkdir()
    git = binary / "git"
    python = binary / "python"
    git.write_text('#!/bin/sh\nprintf "%s\\n" "$ARIO_SOURCE_SHA"\n')
    python.write_text('#!/bin/sh\nprintf "%s" "$ARIO_TEST_OUTPUT"\nexit "$ARIO_TEST_EXIT"\n')
    git.chmod(0o755)
    python.chmod(0o755)
    summary = tmp_path / "summary.md"
    env = dict(os.environ)
    env.update({"PATH": str(binary) + os.pathsep + env.get("PATH", ""),
                "RUNNER_TEMP": str(tmp_path),
                "GITHUB_STEP_SUMMARY": str(summary),
                "ARIO_PR_NUMBER": "295", "ARIO_EXPECTED_HEAD": "a"*40,
                "ARIO_SOURCE_SHA": "b"*40,
                "ARIO_TEST_OUTPUT": output, "ARIO_TEST_EXIT": str(exit_code)})
    env.pop("ARIO_TRUSTED_READ_TOKEN", None)
    process = subprocess.run(["bash", "--noprofile", "--norc", "-e", "-o", "pipefail",
                              "-c", script()], cwd=tmp_path, env=env,
                             capture_output=True, text=True, timeout=12)
    return process, summary.read_text() if summary.exists() else ""

@pytest.mark.skipif(not NEEDS_BASH, reason="Bash test on Linux only")
def test_failed_cli_is_logged_and_step_still_fails(tmp_path):
    payload = diagnostic("MISSING_READ_ONLY_TOKEN")
    proc, summary = execute(tmp_path, payload, 2)
    assert proc.returncode == 2
    assert "MISSING_READ_ONLY_TOKEN" in proc.stdout
    assert "MISSING_READ_ONLY_TOKEN" in summary

@pytest.mark.skipif(not NEEDS_BASH, reason="Bash test on Linux only")
def test_successfully_sampled_hold_is_visible(tmp_path):
    payload = diagnostic("PR_DRAFT_READ_ONLY_HOLD", complete=True)
    proc, summary = execute(tmp_path, payload, 0)
    assert proc.returncode == 0
    assert "PR_DRAFT_READ_ONLY_HOLD" in proc.stdout
    assert "PR_DRAFT_READ_ONLY_HOLD" in summary

@pytest.mark.skipif(not NEEDS_BASH, reason="Bash test on Linux only")
def test_empty_output_is_not_success(tmp_path):
    proc, summary = execute(tmp_path, "", 0)
    assert proc.returncode != 0
    assert "NO_DIAGNOSTIC_JSON" in summary
    assert "NO_DIAGNOSTIC_JSON" in proc.stdout

def test_staged_workflow_keeps_main_source_pin():
    text = WF.read_text()
    assert "workflow_dispatch:" in text
    assert "if: github.ref == 'refs/heads/main'" in text
    assert "ref: ${{ github.sha }}" in text
    assert "persist-credentials: false" in text
    assert "pull_request_target" not in text


@pytest.mark.skipif(not NEEDS_BASH, reason="Bash test on Linux only")
@pytest.mark.parametrize("bad_output", [
    "plain text\n", "     \n", "[]\n",
    '{"schema":"wrong","disposition":"HOLD","merge_authorized":false}\n',
    '{"schema":"ARIO-GUARD-V2-TRUSTED-MANUAL-READ-LAB-0.1","status":"UNKNOWN","disposition":"HOLD","reason":"fake","merge_authorized":true,"check_publish_authorized":false,"trust_activated":false}\n',
    '{"schema":"ARIO-GUARD-V2-TRUSTED-MANUAL-READ-LAB-0.1","status":"UNKNOWN","disposition":"HOLD","reason":"fake","merge_authorized":false,"merge_authorized":true,"check_publish_authorized":false,"trust_activated":false}\n',
])
def test_cli_exit_zero_with_invalid_or_unsafe_json_is_never_green(tmp_path, bad_output):
    proc, summary = execute(tmp_path, bad_output, 0)
    assert proc.returncode != 0
    assert "INVALID_DIAGNOSTIC_JSON" in proc.stdout
    assert "INVALID_DIAGNOSTIC_JSON" in summary


@pytest.mark.skipif(not NEEDS_BASH, reason="Bash test on Linux only")
@pytest.mark.parametrize("code,report,reason", [
    (17, "", "NO_DIAGNOSTIC_JSON"),
    (17, "plain-text\n", "INVALID_DIAGNOSTIC_JSON"),
    (2, "[]\n", "INVALID_DIAGNOSTIC_JSON"),
])
def test_nonzero_error_exit_is_preserved_with_visible_reason(tmp_path, code, report, reason):
    proc, summary = execute(tmp_path, report, code)
    assert proc.returncode == code
    assert reason in proc.stdout
    assert reason in summary


@pytest.mark.skipif(not NEEDS_BASH, reason="Bash test on Linux only")
def test_valid_base_error_hold_retains_original_reason_and_nonzero_exit(tmp_path):
    proc, summary = execute(tmp_path, diagnostic("GRAPHQL_HTTP_403"), 2)
    assert proc.returncode == 2
    assert "GRAPHQL_HTTP_403" in summary
    assert "GRAPHQL_HTTP_403" in proc.stdout
    assert "INVALID_DIAGNOSTIC_JSON" not in summary


@pytest.mark.skipif(not NEEDS_BASH, reason="Bash test on Linux only")
@pytest.mark.parametrize("change", ["false_bool_alias", "missing_complete_graph",
                                     "wrong_head", "non_matching_digests",
                                     "wrong_source", "wrong_reason"])
def test_exit_zero_requires_complete_pinned_non_authoritative_report(tmp_path, change):
    report = json.loads(diagnostic("PR_DRAFT_READ_ONLY_HOLD", complete=True))
    if change == "false_bool_alias":
        report["merge_authorized"] = 0
    elif change == "missing_complete_graph":
        del report["review_graph_sample"]
    elif change == "wrong_head":
        report["live_identity"]["head_sha"] = "f" * 40
    elif change == "non_matching_digests":
        report["second_digest"] = "0" * 64
    elif change == "wrong_source":
        report["source_commit_sha"] = "f" * 40
    elif change == "wrong_reason":
        report["reason"] = "CI_PASSED_SO_MERGE"
    proc, summary = execute(tmp_path, json.dumps(report) + "\n", 0)
    assert proc.returncode == 2
    assert "INVALID_DIAGNOSTIC_JSON" in proc.stdout
    assert "INVALID_DIAGNOSTIC_JSON" in summary
