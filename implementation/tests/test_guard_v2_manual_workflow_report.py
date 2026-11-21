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

def script():
    text = WF.read_text(encoding="utf-8")
    assert text.count("        run: |\n") == 1
    raw = text.split("        run: |\n", 1)[1].splitlines()
    assert all(not line.strip() or line.startswith("          ") for line in raw)
    return "\n".join(line[10:] if line.strip() else "" for line in raw) + "\n"

def execute(tmp_path, output, exit_code):
    (tmp_path / "implementation").mkdir()
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
    payload = json.dumps({"reason":"MISSING_READ_ONLY_TOKEN","disposition":"HOLD",
                          "merge_authorized":False}) + "\n"
    proc, summary = execute(tmp_path, payload, 2)
    assert proc.returncode == 2
    assert "MISSING_READ_ONLY_TOKEN" in proc.stdout
    assert "MISSING_READ_ONLY_TOKEN" in summary

@pytest.mark.skipif(not NEEDS_BASH, reason="Bash test on Linux only")
def test_successfully_sampled_hold_is_visible(tmp_path):
    payload = json.dumps({"reason":"PR_DRAFT_READ_ONLY_HOLD","disposition":"HOLD",
                          "merge_authorized":False}) + "\n"
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
