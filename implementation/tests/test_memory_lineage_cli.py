"""Public memory CLI exercises the existing lineage reader on pinned inputs."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from ario_agent import run_task
from core.memory_consolidation import ConsolidationEngine
from core.memory_snapshot import encode_cognitive_memory_snapshot
from core.source_monitoring import SourceMonitoringGuard
from core.working_memory import WorkingMemoryBuffer

CLI = Path(__file__).resolve().parents[1] / "ario_memory_cli.py"


def call(*args):
    return subprocess.run([sys.executable, "-B", str(CLI), "--memory-lineage", *args],
                          cwd=CLI.parent, capture_output=True, text=True, check=False)


def pin(raw):
    return hashlib.sha256(raw).hexdigest()


def test_cli_native_ledger_index_then_lineage(tmp_path):
    (tmp_path / "input.txt").write_text("data", encoding="utf-8")
    ledger = tmp_path / "events.jsonl"
    run_task({"task_id": "T", "goal": "read", "actions": [
        {"step_id": "s", "tool": "file_fingerprint", "path": "input.txt"}]}, tmp_path, ledger)
    raw = ledger.read_bytes()
    args = ["--ledger", str(ledger), "--expected-sha256", pin(raw)]
    listing = call(*args)
    assert listing.returncode == 0, listing.stderr
    node = next(n for n in json.loads(listing.stdout)["nodes"]
                if n["concept"].startswith("agent_tool:file_fingerprint"))
    result = call(*args, "--node-id", node["node_id"])
    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert report["sources"][0]["status"] == "LEDGER_REFERENCE_ONLY"
    assert report["claim_truth"] == report["freshness"] == "UNKNOWN"
    assert report["input_sha256"] == pin(raw)
    assert ledger.read_bytes() == raw
    rejected = call("--ledger", str(ledger), "--expected-sha256", "0"*64)
    assert rejected.returncode == 2 and not rejected.stdout


def test_cli_pinned_joint_snapshot_resolves_exact_historical_source(tmp_path):
    engine, guard = ConsolidationEngine(), SourceMonitoringGuard()
    h = guard.create_hypothesis("claim", attribution_id="origin")
    wm = WorkingMemoryBuffer(consolidation_engine=engine, source_guard=guard)
    wm.ingest("topic", h.assertion, h, salience=.9)
    wm.flush_to_long_term()
    node = next(iter(engine.nodes.values()))
    raw = encode_cognitive_memory_snapshot(engine, guard)
    path = tmp_path / "memory.json"
    path.write_bytes(raw)
    args = ["--snapshot", str(path), "--expected-sha256", pin(raw)]
    result = call(*args, "--node-id", node.node_id)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["sources"][0]["status"] == "MATCHED_WM_EVENT"
    assert report["sources"][0]["revision_candidates"][0]["attribution_id"] == "origin"
    assert report["independent_admission_authority"] == "NONE"
    missing = call(*args, "--node-id", "missing")
    assert missing.returncode == 1
    assert json.loads(missing.stdout)["reason"] == "EXACT_NODE_NOT_FOUND"
    bad = call("--snapshot", str(path), "--expected-sha256", "0"*64)
    assert bad.returncode == 2 and not bad.stdout
    assert path.read_bytes() == raw


def test_cli_requires_explicit_pin_and_single_input(tmp_path):
    p = tmp_path / "unused.json"
    p.write_bytes(b"{}")
    assert call("--snapshot", str(p)).returncode == 2
    assert call("--snapshot", str(p), "--ledger", str(p),
                "--expected-sha256", pin(p.read_bytes())).returncode == 2


def test_exact_inspection_has_no_recall_side_effect():
    engine, guard = ConsolidationEngine(), SourceMonitoringGuard()
    engine.ingest_event_stream([("1"*64, {"concept": "topic", "assertion": "claim"})])
    node = next(iter(engine.nodes.values()))
    before = encode_cognitive_memory_snapshot(engine, guard)
    wm = WorkingMemoryBuffer(consolidation_engine=engine, source_guard=guard)
    result = wm.inspect_semantic_lineage(node.node_id)
    assert result["sources"][0]["status"] == "UNKNOWN"
    assert wm.active_count == 0
    assert encode_cognitive_memory_snapshot(engine, guard) == before
