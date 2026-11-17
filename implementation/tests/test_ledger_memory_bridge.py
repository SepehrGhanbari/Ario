"""Comprehensive verification of EpistemicLedgerBridge and Issue #216 Invariants."""

import json
import tempfile
import unittest
from pathlib import Path

from core.ledger_memory_bridge import EpistemicLedgerBridge, BridgeError
from core.memory_consolidation import ConsolidationEngine, NodeEpistemicStatus
from core.source_monitoring import SourceMonitoringGuard, SourceMonitoringError
from core.prospective_memory import ProspectiveMemoryRegistry


class LedgerMemoryBridgeTests(unittest.TestCase):

    def test_bridge_ingests_agent_events_end_to_end(self):
        """Verify synthetic ledger reports are consolidated but not source-authenticated."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "agent_events.jsonl"
            events = [
                {"event": "TASK_STARTED", "task_id": "task-42", "goal": "Audit project integrity", "timestamp": "2026-11-17T12:00:00Z"},
                {
                    "event": "STEP_OBSERVED",
                    "task_id": "task-42",
                    "step_id": "step-1",
                    "tool": "file_fingerprint",
                    "status": "COMPLETED",
                    "result": {"path": "README.md", "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "bytes": 0},
                    "timestamp": "2026-11-17T12:00:01Z",
                },
                {"event": "TASK_FINISHED", "task_id": "task-42", "status": "COMPLETED", "exit_code": 0, "timestamp": "2026-11-17T12:00:02Z"},
            ]
            ledger_path.write_text("\n".join(json.dumps(ev) for ev in events) + "\n", encoding="utf-8")

            bridge = EpistemicLedgerBridge()
            summary = bridge.ingest_agent_ledger(ledger_path)

            self.assertEqual(summary.total_events_read, 3)
            self.assertEqual(summary.steps_observed, 1)
            self.assertGreaterEqual(summary.nodes_consolidated, 2)
            self.assertEqual(summary.contested_nodes_count, 0)

            # A self-reported successful step remains RECORDED, never verified evidence.
            tool_node = [n for n in bridge.engine.nodes.values() if "agent_tool:file_fingerprint" in n.concept][0]
            self.assertEqual(tool_node.status, NodeEpistemicStatus.RECORDED)

    def test_bridge_detects_contradictory_step_results_as_contested(self):
        """Conflicting observations on the same target must yield CONTESTED without erasure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "conflicting_events.jsonl"
            events = [
                {
                    "event": "STEP_OBSERVED",
                    "task_id": "task-1",
                    "step_id": "s1",
                    "tool": "file_fingerprint",
                    "status": "COMPLETED",
                    "result": {"path": "data.txt", "sha256": "1111111111111111111111111111111111111111111111111111111111111111"},
                },
                {
                    "event": "STEP_OBSERVED",
                    "task_id": "task-2",
                    "step_id": "s2",
                    "tool": "file_fingerprint",
                    "status": "COMPLETED",
                    "result": {"path": "data.txt", "sha256": "2222222222222222222222222222222222222222222222222222222222222222"},
                },
            ]
            ledger_path.write_text("\n".join(json.dumps(ev) for ev in events) + "\n", encoding="utf-8")

            bridge = EpistemicLedgerBridge()
            summary = bridge.ingest_agent_ledger(ledger_path)

            self.assertGreater(summary.contested_nodes_count, 0)
            contested_nodes = [n for n in bridge.engine.nodes.values() if n.status == NodeEpistemicStatus.CONTESTED]
            self.assertGreaterEqual(len(contested_nodes), 1)

    def test_bridge_does_not_trigger_intentions_on_untrusted_task_finish(self):
        """Reported TASK_FINISHED is an audit fact, not an authorized action trigger."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "task_finish.jsonl"
            events = [
                {"event": "TASK_STARTED", "task_id": "build-prod", "goal": "Compile release"},
                {"event": "TASK_FINISHED", "task_id": "build-prod", "status": "COMPLETED", "exit_code": 0},
            ]
            ledger_path.write_text("\n".join(json.dumps(ev) for ev in events) + "\n", encoding="utf-8")

            registry = ProspectiveMemoryRegistry()
            registry.register_intention(
                description="Trigger deployment pipeline when build finishes",
                predicate_expr="task_id == 'build-prod' and status == 'COMPLETED'",
                action_payload={"deploy": True},
                created_at_epoch=1000.0,
                ttl_epoch=2000.0,
            )

            bridge = EpistemicLedgerBridge(prospective_registry=registry)
            summary = bridge.ingest_agent_ledger(ledger_path, current_epoch=1000.0)

            self.assertEqual(summary.reported_task_finishes_count, 1)
            self.assertEqual(summary.triggered_intentions_count, 0)
            self.assertEqual(summary.triggered_intentions, ())
            self.assertEqual(len(registry.get_pending_intentions()), 1)

    def test_v2_canonical_node_id_eliminates_delimiter_collision(self):
        """Invariant (Issue #216): ('a:b', 'c') and ('a', 'b:c') must have distinct v2 IDs."""
        v1_id1 = ConsolidationEngine.compute_node_id("a:b", "c", version="v1")
        v1_id2 = ConsolidationEngine.compute_node_id("a", "b:c", version="v1")
        # In v1 they collided:
        self.assertEqual(v1_id1, v1_id2)

        # In v2 they are strictly distinct:
        v2_id1 = ConsolidationEngine.compute_node_id("a:b", "c", version="v2")
        v2_id2 = ConsolidationEngine.compute_node_id("a", "b:c", version="v2")
        self.assertNotEqual(v2_id1, v2_id2)
        self.assertTrue(v2_id1.startswith("SEM-v2-"))
        self.assertTrue(v2_id2.startswith("SEM-v2-"))

    def test_dual_resolver_backward_compatibility(self):
        """Dual resolver allows looking up v2 nodes via their legacy v1 IDs."""
        engine = ConsolidationEngine(node_id_version="v2", default_status=NodeEpistemicStatus.RECORDED)
        event_hash = "a" * 64
        engine.ingest_event_stream([(event_hash, {"concept": "network", "assertion": "gateway online"})])

        v2_id = ConsolidationEngine.compute_node_id("network", "gateway online", version="v2")
        v1_id = ConsolidationEngine.compute_node_id("network", "gateway online", version="v1")

        self.assertIn(v2_id, engine.nodes)
        self.assertNotIn(v1_id, engine.nodes)

        # Dual resolver resolves legacy v1 ID to the canonical v2 node:
        resolved_id = engine.resolve_node_id(v1_id)
        self.assertEqual(resolved_id, v2_id)
        node = engine.get_node(v1_id)
        self.assertIsNotNone(node)
        self.assertEqual(node.node_id, v2_id)

    def test_no_history_promotion_invariant(self):
        """Invariant (Issue #216 / SARA / W11): Repeating unverified events does NOT promote RECORDED to SUPPORTED."""
        engine = ConsolidationEngine(default_status=NodeEpistemicStatus.RECORDED)
        
        # Ingest 10 times
        for i in range(10):
            fake_hash = f"{i:064x}"
            engine.ingest_event_stream([(fake_hash, {"concept": "rumor", "assertion": "unverified claim"})])

        node = list(engine.nodes.values())[0]
        self.assertEqual(node.reinforcement_count, 10)
        self.assertGreater(node.saliency_score, 0.9)
        # Saliency increased, but epistemic status strictly stayed RECORDED:
        self.assertEqual(node.status, NodeEpistemicStatus.RECORDED)
        self.assertNotEqual(node.status, NodeEpistemicStatus.SUPPORTED)

    def test_bridge_read_only_invariance(self):
        """Bridge ingestion must not mutate even a single byte of the input ledger."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "immutable.jsonl"
            content = b'{"event": "TASK_STARTED", "task_id": "test"}\n'
            ledger_path.write_bytes(content)

            bridge = EpistemicLedgerBridge()
            bridge.ingest_agent_ledger(ledger_path)

            self.assertEqual(ledger_path.read_bytes(), content)

    def test_bridge_rejects_symlink_ledger(self):
        """Symlink ledgers fail closed to prevent traversal attacks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            real_file = Path(temp_dir) / "real.jsonl"
            real_file.write_text('{"event": "TASK_STARTED"}\n')
            symlink_file = Path(temp_dir) / "symlink.jsonl"
            symlink_file.symlink_to(real_file)

            bridge = EpistemicLedgerBridge()
            with self.assertRaises(BridgeError):
                bridge.ingest_agent_ledger(symlink_file)


if __name__ == "__main__":
    unittest.main()
