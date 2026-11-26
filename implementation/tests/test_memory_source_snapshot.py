from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from core.memory_consolidation import ConsolidationEngine, ConsolidationError
from core.memory_snapshot import (
    decode_cognitive_memory_snapshot,
    encode_cognitive_memory_snapshot,
    restore_cognitive_memory_snapshot,
    restore_cognitive_memory_snapshot_file,
    write_cognitive_memory_snapshot,
)
from core.source_monitoring import (
    AttributionMismatchError,
    SelfCitationError,
    SourceMonitoringError,
    SourceMonitoringGuard,
    VeracityState,
)


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(document: dict) -> bytes:
    return json.dumps(
        document, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def _event(concept: str, assertion: str) -> tuple[str, dict[str, str]]:
    event = {"concept": concept, "assertion": assertion}
    return _digest(json.dumps(event, sort_keys=True).encode()), event


def _populated_pair() -> tuple[ConsolidationEngine, SourceMonitoringGuard, str, str]:
    engine = ConsolidationEngine()
    event_hash, event = _event("source", "recovered event")
    assert engine.ingest_event_stream([(event_hash, event)]) == 1

    guard = SourceMonitoringGuard(allowlisted_tools={"run_tests"})
    assertion = "tool_exit:run_tests:sample:test:0"
    guard.create_hypothesis(
        assertion,
        attribution_id="claim-stable-id",
        falsification_condition="A fresh run returns a non-zero exit code",
    )
    guard.create_external_testimony("unrelated assertion", attribution_id="testimony-id")
    with pytest.raises(AttributionMismatchError):
        guard.record_empirical_observation(
            assertion="tool_exit:run_tests:sample:bad-lock:0",
            tool="run_tests",
            target="sample:bad-lock",
            exit_code=0,
            stdout="mismatch output",
            execution_lock="actual lock",
            expected_execution_lock_sha256="0" * 64,
            attribution_id="mismatch-history-id",
            parent_attribution_ids=("testimony-id",),
        )
    with pytest.raises(SelfCitationError):
        guard.evaluate_claim_promotion("claim-stable-id", ["testimony-id"])
    observation = guard.record_empirical_observation(
        assertion=assertion,
        tool="run_tests",
        target="sample:test",
        exit_code=0,
        stdout="tests passed",
        execution_lock="runner-lock-v1",
        attribution_id="empirical-stable-id",
    )
    assert observation.veracity_state == VeracityState.VERIFIED_EMPIRICAL
    guard.evaluate_claim_promotion("claim-stable-id", [observation.attribution_id])
    assert len(guard.attribution_history("claim-stable-id")) == 3
    return engine, guard, "claim-stable-id", "empirical-stable-id"


def test_fresh_process_recovers_engine_and_complete_source_history(tmp_path: Path):
    engine, guard, claim_id, observation_id = _populated_pair()
    snapshot_path = tmp_path / "combined.snapshot.json"
    retained_sha256 = write_cognitive_memory_snapshot(engine, guard, snapshot_path)
    snapshot = snapshot_path.read_bytes()
    assert _digest(snapshot) == retained_sha256
    assert b"allowlisted_tools" not in snapshot

    child = r"""
import hashlib, sys
from pathlib import Path
from core.memory_snapshot import decode_cognitive_memory_snapshot
from core.source_monitoring import SourceMonitoringError, VeracityState
raw = Path(sys.argv[1]).read_bytes()
expected = sys.argv[2]
assert hashlib.sha256(raw).hexdigest() == expected
engine, guard = decode_cognitive_memory_snapshot(
    __import__('core.memory_consolidation', fromlist=['ConsolidationEngine']).ConsolidationEngine,
    raw, expected_sha256=expected, allowlisted_tools={'run_tests'},
)
assert len(engine.nodes) == 1
assert guard.attribution_history('claim-stable-id')[-1].veracity_state is VeracityState.VERIFIED_EMPIRICAL
assert [r.veracity_state.value for r in guard.attribution_history('claim-stable-id')] == [
    'UNVERIFIED_HYPOTHESIS', 'UNSUPPORTED', 'VERIFIED_EMPIRICAL'
]
assert guard.filter_working_memory_candidates(['empirical-stable-id'], require_verified=False)
assert not guard.filter_working_memory_candidates(['empirical-stable-id'], require_verified=True)
try:
    guard.create_hypothesis('conflicting source', attribution_id='claim-stable-id')
except SourceMonitoringError as error:
    assert 'ATTRIBUTION_ID_COLLISION' in str(error)
else:
    raise AssertionError('conflicting attribution ID reuse was accepted')
try:
    guard.record_empirical_observation(
        'tool_exit:compile_python:sample:0', 'compile_python', 'sample', 0,
        'output', 'lock', attribution_id='new-observation',
    )
except SourceMonitoringError:
    pass
else:
    raise AssertionError('snapshot expanded the caller tool allowlist')
print('fresh-process joint recovery passed')
"""
    implementation_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-c", child, str(snapshot_path), retained_sha256],
        cwd=implementation_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "fresh-process joint recovery" in result.stdout

    restored_engine = ConsolidationEngine()
    restored_guard = SourceMonitoringGuard(allowlisted_tools={"run_tests"})
    restore_cognitive_memory_snapshot_file(
        restored_engine, restored_guard, snapshot_path, expected_sha256=retained_sha256
    )
    assert encode_cognitive_memory_snapshot(restored_engine, restored_guard) == snapshot
    assert list(restored_engine.nodes) == list(engine.nodes)
    assert restored_guard.attributions == guard.attributions
    assert restored_guard.attribution_history(claim_id) == guard.attribution_history(claim_id)
    assert restored_guard.attributions[observation_id].veracity_state is VeracityState.VERIFIED_EMPIRICAL
    assert not restored_guard.filter_working_memory_candidates(
        [claim_id, observation_id], require_verified=True
    )

    fresh = restored_guard.record_empirical_observation(
        assertion=restored_guard.attributions[claim_id].assertion,
        tool="run_tests",
        target="sample:test",
        exit_code=0,
        stdout="new process evidence",
        execution_lock="new runner lock",
        attribution_id="fresh-observation-id",
    )
    restored_guard.create_hypothesis(
        assertion=fresh.assertion, attribution_id="new-claim-id"
    )
    promoted = restored_guard.evaluate_claim_promotion(
        "new-claim-id", ["fresh-observation-id"]
    )
    assert promoted.veracity_state == VeracityState.VERIFIED_EMPIRICAL
    assert restored_guard.filter_working_memory_candidates(
        ["fresh-observation-id"], require_verified=True
    )


def test_conflicting_attribution_reuse_is_rejected_after_recovery():
    engine, guard, claim_id, _ = _populated_pair()
    raw = encode_cognitive_memory_snapshot(engine, guard)
    restored = SourceMonitoringGuard(allowlisted_tools={"run_tests"})
    restore_cognitive_memory_snapshot(
        ConsolidationEngine(), restored, raw, expected_sha256=_digest(raw)
    )
    with pytest.raises(SourceMonitoringError, match="ATTRIBUTION_ID_COLLISION"):
        restored.create_hypothesis("different claim", attribution_id=claim_id)


def test_forged_histories_fail_atomically_for_both_state_objects():
    source_engine, source_guard, claim_id, observation_id = _populated_pair()
    valid = encode_cognitive_memory_snapshot(source_engine, source_guard)
    bad_documents = []

    dangling = json.loads(valid)
    dangling_records = {item["attribution_id"]: item for item in dangling["source_monitoring"]["records"]}
    dangling_records[claim_id]["revisions"][0]["parent_attribution_ids"] = ["missing-parent"]
    dangling_records[claim_id]["revisions"][1]["parent_attribution_ids"] = ["missing-parent", "testimony-id"]
    dangling_records[claim_id]["revisions"][2]["parent_attribution_ids"] = [
        "missing-parent", "testimony-id", observation_id
    ]
    bad_documents.append(dangling)

    forged_transition = json.loads(valid)
    forged_records = {item["attribution_id"]: item for item in forged_transition["source_monitoring"]["records"]}
    testimony = forged_records["testimony-id"]["revisions"][0]
    forged = dict(testimony)
    forged["veracity_state"] = "VERIFIED_EMPIRICAL"
    forged["parent_attribution_ids"] = [claim_id]
    forged_records["testimony-id"]["revisions"].append(forged)
    bad_documents.append(forged_transition)

    malformed_revision = json.loads(valid)
    malformed_records = {item["attribution_id"]: item for item in malformed_revision["source_monitoring"]["records"]}
    malformed_records[claim_id]["revisions"][1]["assertion"] = "rewritten assertion"
    bad_documents.append(malformed_revision)

    circular = json.loads(valid)
    circular_records = {item["attribution_id"]: item for item in circular["source_monitoring"]["records"]}
    circular_records["testimony-id"]["revisions"][0]["parent_attribution_ids"] = [claim_id]
    circular_records[claim_id]["revisions"][1]["parent_attribution_ids"] = ["testimony-id"]
    circular_records[claim_id]["revisions"][2]["parent_attribution_ids"] = ["testimony-id", observation_id]
    bad_documents.append(circular)

    target_engine, target_guard, _, _ = _populated_pair()
    target_guard_before_active = set(target_guard._active_verified_ids)
    before = encode_cognitive_memory_snapshot(target_engine, target_guard)
    allowlist_before = set(target_guard._allowlisted_tools)

    for candidate_document in bad_documents:
        candidate = _canonical(candidate_document)
        with pytest.raises(ConsolidationError):
            restore_cognitive_memory_snapshot(
                target_engine, target_guard, candidate,
                expected_sha256=_digest(candidate),
            )
        assert encode_cognitive_memory_snapshot(target_engine, target_guard) == before
        assert target_guard._active_verified_ids == target_guard_before_active
        assert target_guard._allowlisted_tools == allowlist_before


def test_joint_snapshot_waits_for_mutations_and_captures_consistent_pair():
    engine = ConsolidationEngine()
    guard = SourceMonitoringGuard(allowlisted_tools={"run_tests"})
    writer_has_both_locks = threading.Event()
    release_writer = threading.Event()
    snapshot_started = threading.Event()
    snapshot_done = threading.Event()
    result: list[bytes] = []
    event_hash, event = _event("concurrent", "committed together")

    def writer() -> None:
        locks = sorted((engine._batch_lock, guard._lock), key=id)
        with locks[0], locks[1]:
            engine.ingest_event_stream([(event_hash, event)])
            guard.create_hypothesis("paired source", attribution_id="paired-source")
            writer_has_both_locks.set()
            assert release_writer.wait(2)

    def capture() -> None:
        snapshot_started.set()
        result.append(encode_cognitive_memory_snapshot(engine, guard))
        snapshot_done.set()

    writing = threading.Thread(target=writer)
    writing.start()
    assert writer_has_both_locks.wait(2)
    capturing = threading.Thread(target=capture)
    capturing.start()
    assert snapshot_started.wait(2)
    assert not snapshot_done.wait(0.05)
    release_writer.set()
    writing.join(2)
    capturing.join(2)
    assert not writing.is_alive() and not capturing.is_alive()
    assert snapshot_done.is_set()

    recovered_engine, recovered_guard = decode_cognitive_memory_snapshot(
        ConsolidationEngine, result[0], expected_sha256=_digest(result[0]),
        allowlisted_tools={"run_tests"},
    )
    assert len(recovered_engine.nodes) == 1
    assert recovered_guard.attributions["paired-source"].assertion == "paired source"


def test_existing_ltm_recall_reference_survives_joint_recovery():
    engine, guard, _, _ = _populated_pair()
    node = next(iter(engine.nodes.values()))
    recall_id = "recall_" + node.node_id
    guard.create_hypothesis(node.assertion, attribution_id=recall_id,
                            parent_attribution_ids=(node.node_id,))
    raw = encode_cognitive_memory_snapshot(engine, guard)
    restored_engine, restored_guard = decode_cognitive_memory_snapshot(
        ConsolidationEngine, raw, expected_sha256=_digest(raw), allowlisted_tools=set()
    )
    assert restored_engine.get_node(node.node_id) == node
    assert restored_guard.attribution_history(recall_id) == guard.attribution_history(recall_id)
    assert not restored_guard.filter_working_memory_candidates([recall_id], require_verified=True)
    bad = json.loads(raw)
    rec = next(r for r in bad["source_monitoring"]["records"] if r["attribution_id"] == recall_id)
    rec["revisions"][0]["assertion"] = "unrelated forged recall"
    changed = _canonical(bad)
    with pytest.raises(ConsolidationError, match="HOLD_DANGLING_SOURCE_REFERENCE"):
        decode_cognitive_memory_snapshot(ConsolidationEngine, changed,
            expected_sha256=_digest(changed), allowlisted_tools=set())


def test_previously_verified_claim_can_be_revised_to_unsupported_and_recovered():
    engine, guard, claim_id, observation_id = _populated_pair()
    with pytest.raises(SelfCitationError):
        guard.evaluate_claim_promotion(claim_id, ["testimony-id"])
    assert guard.attributions[claim_id].veracity_state is VeracityState.UNSUPPORTED
    raw = encode_cognitive_memory_snapshot(engine, guard)
    _, recovered = decode_cognitive_memory_snapshot(
        ConsolidationEngine, raw, expected_sha256=_digest(raw), allowlisted_tools=set()
    )
    assert recovered.attribution_history(claim_id) == guard.attribution_history(claim_id)
    assert recovered.attributions[claim_id].veracity_state is VeracityState.UNSUPPORTED
    assert not recovered.filter_working_memory_candidates([claim_id, observation_id], require_verified=True)
