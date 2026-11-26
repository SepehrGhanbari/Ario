from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

CLI_PATH = Path(__file__).resolve().parents[1] / "ario_memory_cli.py"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-B", str(CLI_PATH), *args]
    return subprocess.run(
        cmd,
        cwd=CLI_PATH.parent,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_memory_conflicts_missing_ledger():
    proc = run_cli("--memory-conflicts")
    assert proc.returncode == 2
    data = json.loads(proc.stderr)
    assert data["error"] == "MISSING_REQUIRED_ARGUMENT"
    assert "--ledger" in data["detail"]


def test_cli_memory_conflicts_ledger_not_found(tmp_path: Path):
    missing = tmp_path / "does_not_exist.jsonl"
    proc = run_cli("--memory-conflicts", "--ledger", str(missing))
    assert proc.returncode == 2
    data = json.loads(proc.stderr)
    assert data["error"] == "LEDGER_NOT_FOUND"


def test_cli_memory_conflicts_empty_uncontested_markdown(tmp_path: Path):
    ledger = tmp_path / "empty.jsonl"
    ledger.write_text("", encoding="utf-8")

    proc = run_cli("--memory-conflicts", "--ledger", str(ledger))
    assert proc.returncode == 0
    assert "No contested memories" in proc.stdout
    assert "Contestation & Conflict Audit Report" in proc.stdout


def test_cli_memory_conflicts_json_format_with_contradiction(tmp_path: Path):
    ledger = tmp_path / "contradictions.jsonl"
    ev1 = {"concept": "network_isolation", "assertion": "Proxy loopback enabled", "value": "ISOLATED"}
    ev2 = {"concept": "network_isolation", "assertion": "Direct egress allowed", "value": "CONNECTED", "relation": "opposite"}

    lines = [
        json.dumps(ev1, ensure_ascii=False),
        json.dumps(ev2, ensure_ascii=False),
    ]
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")

    proc = run_cli("--memory-conflicts", "--ledger", str(ledger), "--format", "json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["total_nodes"] == 2
    assert data["contested_nodes_count"] == 2
    assert data["contested_concepts"] == ["network_isolation"]
    assert len(data["conflicts"]) == 1
    assert data["conflicts"][0]["concept"] == "network_isolation"


def test_cli_memory_conflicts_export_to_file(tmp_path: Path):
    ledger = tmp_path / "events.jsonl"
    ledger.write_text(json.dumps({"concept": "auth", "assertion": "Token verified"}) + "\n", encoding="utf-8")
    report_file = tmp_path / "report.md"

    proc = run_cli("--memory-conflicts", "--ledger", str(ledger), "--output", str(report_file))
    assert proc.returncode == 0
    assert report_file.exists()
    assert "Contestation & Conflict Audit Report" in report_file.read_text(encoding="utf-8")


def test_cli_inspect_ledger_clean(tmp_path: Path):
    ledger = tmp_path / "clean.jsonl"
    ledger.write_text(
        json.dumps({"task_id": "T1", "assertion": "Initialized"}) + "\n" +
        json.dumps({"task_id": "T2", "assertion": "Executed"}) + "\n",
        encoding="utf-8",
    )

    proc = run_cli("--inspect-ledger", "--ledger", str(ledger))
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["is_clean"] is True
    assert data["valid_lines"] == 2
    assert data["diagnostic"] == "CLEAN"


def test_cli_inspect_ledger_corrupt_trailing_line(tmp_path: Path):
    ledger = tmp_path / "corrupt.jsonl"
    ledger.write_text(
        json.dumps({"task_id": "T1", "assertion": "Valid Line"}) + "\n" +
        '{"task_id": "T2", "assertion": "truncated_without_closing_brace',
        encoding="utf-8",
    )

    proc = run_cli("--inspect-ledger", "--ledger", str(ledger))
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["is_clean"] is False
    assert data["valid_lines"] == 1
    assert data["corrupt_line_no"] == 2
    assert "CORRUPT_JSON_OR_TRUNCATED_TAIL" in data["diagnostic"]


def test_cli_inspect_ledger_missing_file():
    proc = run_cli("--inspect-ledger")
    assert proc.returncode == 2
    data = json.loads(proc.stderr)
    assert data["error"] == "MISSING_REQUIRED_ARGUMENT"


def test_cli_bridge_agent_ledger_missing_ledger():
    proc = run_cli("--bridge-agent-ledger")
    assert proc.returncode == 2
    data = json.loads(proc.stderr)
    assert data["error"] == "MISSING_REQUIRED_ARGUMENT"


def test_cli_bridge_agent_ledger_success_json(tmp_path: Path):
    ledger = tmp_path / "agent_run.jsonl"
    events = [
        {"event": "TASK_STARTED", "task_id": "T1", "goal": "Verify system"},
        {"event": "STEP_OBSERVED", "task_id": "T1", "step_id": "S1", "tool": "git_status", "status": "COMPLETED", "result": {"clean": True}},
        {"event": "TASK_FINISHED", "task_id": "T1", "status": "COMPLETED"},
    ]
    ledger.write_text("\n".join(json.dumps(ev) for ev in events) + "\n", encoding="utf-8")

    proc = run_cli("--bridge-agent-ledger", "--ledger", str(ledger), "--format", "json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["total_events_read"] == 3
    assert data["steps_observed"] == 1
    assert data["nodes_consolidated"] >= 2
    assert data["contested_nodes_count"] == 0
