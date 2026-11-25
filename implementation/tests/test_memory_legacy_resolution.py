"""Regression checks for the v2 read-side projection of historical v1 IDs."""
import hashlib
import json
import pickle
import tempfile
import unittest
from pathlib import Path

from core.memory_consolidation import ConsolidationEngine, ConsolidationError


PAIRS = (("a:b", "c"), ("a", "b:c"))


def row(pair):
    event = dict(zip(("concept", "assertion"), pair))
    raw = json.dumps(event, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest(), event


def engine_with(*pairs):
    engine = ConsolidationEngine(node_id_version="v2")
    engine.ingest_event_stream(map(row, pairs))
    return engine


class LegacyResolutionTests(unittest.TestCase):
    def assert_ambiguous(self, engine):
        legacy = engine.compute_node_id(*PAIRS[0])
        self.assertEqual(legacy, engine.compute_node_id(*PAIRS[1]))
        self.assertIsNone(engine.resolve_node_id(legacy))
        self.assertIsNone(engine.get_node(legacy))
        for pair in PAIRS:
            node_id = engine.compute_node_id(*pair, version="v2")
            node = engine.get_node(node_id)
            self.assertEqual((node.concept, node.assertion), pair)
            self.assertEqual(node.status.value, "RECORDED")

    def test_both_orders_and_pickle(self):
        for order in (PAIRS, PAIRS[::-1]):
            with self.subTest(order=order):
                engine = engine_with(*order)
                self.assert_ambiguous(engine)
                self.assertEqual(engine.ingest_event_stream(map(row, order)), 0)
                self.assert_ambiguous(pickle.loads(pickle.dumps(engine)))

    def test_old_single_winner_snapshot_is_reindexed_without_mutation(self):
        engine = engine_with(*PAIRS)
        legacy = engine.compute_node_id(*PAIRS[0])
        for pair in PAIRS:
            state = engine.__getstate__()
            old_index = {legacy: engine.compute_node_id(*pair, version="v2")}
            state["_legacy_aliases"] = old_index.copy()
            restored = ConsolidationEngine.__new__(ConsolidationEngine)
            restored.__setstate__(state)
            self.assert_ambiguous(restored)
            self.assertEqual(state["_legacy_aliases"], old_index)

    def test_unique_missing_and_historical_v1_lookup(self):
        for version in ("v1", "v2"):
            engine = ConsolidationEngine(node_id_version=version)
            engine.ingest_event_stream([row(PAIRS[0])])
            legacy = engine.compute_node_id(*PAIRS[0])
            expected = engine.compute_node_id(*PAIRS[0], version=version)
            for view in (engine, pickle.loads(pickle.dumps(engine))):
                self.assertEqual(view.resolve_node_id(legacy), expected)
                self.assertEqual(view.get_node(expected).node_id, expected)
                self.assertIsNone(view.get_node("missing"))

    def test_failed_batch_preserves_unique_alias(self):
        engine = engine_with(PAIRS[0])
        legacy = engine.compute_node_id(*PAIRS[0])
        with self.assertRaises(ConsolidationError):
            engine.ingest_event_stream([row(PAIRS[1]), ("invalid", {})])
        self.assertEqual(engine.resolve_node_id(legacy),
                         engine.compute_node_id(*PAIRS[0], version="v2"))
        self.assertEqual(len(engine.nodes), 1)

    def test_alias_cache_cannot_supply_a_different_restored_target(self):
        unrelated = ("other", "claim")
        engine = engine_with(PAIRS[0], unrelated)
        state = engine.__getstate__()
        legacy = engine.compute_node_id(*PAIRS[0])
        state["_legacy_aliases"][legacy] = engine.compute_node_id(*unrelated, version="v2")
        restored = ConsolidationEngine.__new__(ConsolidationEngine)
        restored.__setstate__(state)
        self.assertEqual(restored.get_node(legacy).concept, PAIRS[0][0])

    def test_mismatched_snapshot_node_key_rejected_before_install(self):
        engine = engine_with(PAIRS[0])
        before = engine.nodes
        state = engine.__getstate__()
        state["_nodes"] = {"wrong": next(iter(before.values()))}
        with self.assertRaisesRegex(ConsolidationError, "HOLD_INVALID_SNAPSHOT_NODE_ID"):
            engine.__setstate__(state)
        self.assertEqual(engine.nodes, before)

    def test_import_replay_and_raw_status(self):
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch, "events.jsonl")
            lines = [json.dumps(dict(row(pair)[1], status=status))
                     for pair, status in zip(PAIRS, ("ACCEPTED", "SUPPORTED"))]
            original = ("\n".join(lines) + "\n").encode()
            path.write_bytes(original)
            engine = engine_with()
            self.assertEqual(engine.ingest_ledger_file(path), 2)
            self.assertEqual(engine.ingest_ledger_file(path), 0)
            self.assert_ambiguous(engine)
            self.assertEqual(path.read_bytes(), original)
