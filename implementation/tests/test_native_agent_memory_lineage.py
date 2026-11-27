"""Real Agent observations reach cognitive memory without becoming evidence."""
import hashlib
import json

import pytest

from ario_agent import run_task
from core.ledger_memory_bridge import EpistemicLedgerBridge, BridgeError
from core.memory_consolidation import ConsolidationEngine, NodeEpistemicStatus, ledger_line_digests
from core.memory_snapshot import encode_cognitive_memory_snapshot, decode_cognitive_memory_snapshot
from core.source_monitoring import SourceMonitoringGuard, SourceMonitoringError, SourceType, VeracityState
from test_planner_inspections import inputs
from ario_planner import plan_inspections
from ario_workflow import run_workflow


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def step_rows(raw):
    return [(ledger_line_digests(line)[0], json.loads(line))
            for line in raw.splitlines(keepends=True)
            if json.loads(line)["event"] == "STEP_OBSERVED"]


def test_native_three_inspection_results_have_exact_lineage_and_survive_recovery(tmp_path):
    payload = inputs(tmp_path)
    ledger = tmp_path / "combined.jsonl"
    result = run_workflow(plan_inspections(payload, tmp_path, ledger), tmp_path, ledger)
    assert result["status"] == "COMPLETED"
    raw = ledger.read_bytes()
    bridge = EpistemicLedgerBridge()
    summary = bridge.ingest_agent_ledger(ledger)
    assert summary.steps_observed == 3
    assert summary.legacy_native_projections_retained == 0
    for digest, step in step_rows(raw):
        nodes = [n for n in bridge.engine.nodes.values() if digest in n.source_event_hashes]
        assert len(nodes) == 1
        assert json.loads(nodes[0].assertion) == step["observation"]
        assert nodes[0].status == NodeEpistemicStatus.RECORDED
        aid = "ATTR-LEDGER-" + digest
        attribution = bridge.guard.attributions[aid]
        assert attribution.source_type == SourceType.LEDGER_REPORT
        assert attribution.veracity_state == VeracityState.REPORTED_UNVERIFIED
        assert attribution.provenance is None
        assert bridge.guard.filter_working_memory_candidates([aid], require_verified=True) == []
    assert bridge.engine.validate_lineage_integrity()
    snap = encode_cognitive_memory_snapshot(bridge.engine, bridge.guard)
    engine, guard = decode_cognitive_memory_snapshot(
        ConsolidationEngine, snap, expected_sha256=sha(snap),
        allowlisted_tools=set(bridge.guard._allowlisted_tools))
    recovered = EpistemicLedgerBridge(consolidation_engine=engine, source_guard=guard,
                                     report_only_tools=set(bridge._report_only_tools))
    recovered.ingest_agent_ledger(ledger)
    assert encode_cognitive_memory_snapshot(engine, guard) == snap
    assert ledger.read_bytes() == raw


def test_native_distinct_steps_do_not_invent_contradictions(tmp_path):
    ledger = tmp_path / "events.jsonl"
    for i in range(2):
        (tmp_path / "a.txt").write_text(str(i), encoding="utf-8")
        run_task({"task_id": f"T{i}", "goal": "fingerprint", "actions": [
            {"step_id": "s", "tool": "file_fingerprint", "path": "a.txt"}]}, tmp_path, ledger)
    bridge = EpistemicLedgerBridge()
    summary = bridge.ingest_agent_ledger(ledger)
    assert summary.steps_observed == 2
    assert summary.contested_nodes_count == 0
    nodes = [n for n in bridge.engine.nodes.values() if n.concept.startswith("agent_tool:")]
    assert len(nodes) == 2
    assert len({json.loads(n.assertion)["sha256"] for n in nodes}) == 2


def test_previously_imported_empty_projection_is_not_rewritten(tmp_path):
    event = {"event": "STEP_OBSERVED", "tool": "file_fingerprint", "task_id": "T",
             "step_id": "s", "status": "SUCCEEDED", "observation": {"sha256": "a" * 64}}
    ledger = tmp_path / "native.jsonl"
    raw = (json.dumps(event) + "\n").encode()
    ledger.write_bytes(raw)
    digest = ledger_line_digests(raw)[0]
    bridge = EpistemicLedgerBridge()
    # Exact old projection, as produced by the pre-fix bridge.
    bridge.guard.record_unverified_ledger_report(
        "reported_step_execution:file_fingerprint:file_fingerprint:SUCCEEDED", record_sha256=digest)
    bridge.engine.ingest_event_stream([(digest, {"concept": "agent_tool:file_fingerprint:file_fingerprint",
        "assertion": "{}", "status": "RECORDED"})])
    before = encode_cognitive_memory_snapshot(bridge.engine, bridge.guard)
    summary = bridge.ingest_agent_ledger(ledger)
    assert summary.legacy_native_projections_retained == 1
    assert encode_cognitive_memory_snapshot(bridge.engine, bridge.guard) == before


@pytest.mark.parametrize("change", ["dual", "nondict", "missing_step"])
def test_malformed_native_record_rolls_back_entire_import(tmp_path, change):
    event = {"event": "STEP_OBSERVED", "tool": "file_fingerprint", "task_id": "T",
             "step_id": "s", "status": "SUCCEEDED", "observation": {}}
    if change == "dual":
        event["result"] = {}
    elif change == "nondict":
        event["observation"] = []
    else:
        del event["step_id"]
    ledger = tmp_path / "bad.jsonl"
    ledger.write_text(json.dumps({"event": "TASK_STARTED", "task_id": "T", "goal": "g"}) +
                      "\n" + json.dumps(event) + "\n", encoding="utf-8")
    bridge = EpistemicLedgerBridge()
    with pytest.raises(BridgeError):
        bridge.ingest_agent_ledger(ledger)
    assert not bridge.engine.nodes and not bridge.guard.attributions


def test_report_only_tool_does_not_expand_empirical_or_injected_allowlist(tmp_path):
    ledger = tmp_path / "native.jsonl"
    ledger.write_text(json.dumps({"event": "STEP_OBSERVED", "tool": "audit_m0", "task_id": "T",
        "step_id": "s", "status": "SUCCEEDED", "observation": {"verdict": "PASS"}}) + "\n", encoding="utf-8")
    guard = SourceMonitoringGuard(allowlisted_tools=set())
    with pytest.raises(SourceMonitoringError):
        EpistemicLedgerBridge(source_guard=guard).ingest_agent_ledger(ledger)
    bridge = EpistemicLedgerBridge(source_guard=guard, report_only_tools={"audit_m0"})
    assert bridge.ingest_agent_ledger(ledger).steps_observed == 1
    assert guard._allowlisted_tools == set()
    with pytest.raises(SourceMonitoringError):
        guard.record_empirical_observation("tool_exit:audit_m0:x:0", "audit_m0", "x", 0, "out", "lock")
    with pytest.raises(BridgeError):
        EpistemicLedgerBridge(report_only_tools={"unrestricted_shell"})
