"""Executable R10 synthetic-only crash/rollback tests; no external authority."""
from __future__ import annotations

import json
import os
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from research.r10_durable_monitor.monitor import (
    DurableFixtureMonitor, MonitorHold, PinnedObservation, fixture,
)


class R10DurableMonitorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="r10-research-")
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.db = root / "publisher" / "lab.sqlite"
        self.floor = root / "observer" / "floor.json"
        self.lab = DurableFixtureMonitor(self.db, self.floor)
        self.lab.initialize_empty_lab()

    def make_seq1(self):
        self.assertEqual(self.lab.observe(fixture(1)), "RECORDED_SYNTHETIC_ONLY_NOT_TRUTH")
        self.assertEqual(self.lab.status()["seq"], 1)

    def make_seq2(self):
        self.make_seq1()
        self.assertEqual(self.lab.observe(fixture(2)), "RECORDED_SYNTHETIC_ONLY_NOT_TRUTH")
        self.assertEqual(self.lab.status()["seq"], 2)

    def assertHold(self, message, fn):
        with self.assertRaisesRegex(MonitorHold, message):
            fn()

    def child(self, sequence, crash=None):
        # Same synthetic data, entirely separate interpreter and DB connection.
        code = (
            "from pathlib import Path\n"
            "from research.r10_durable_monitor.monitor import DurableFixtureMonitor, fixture\n"
            f"m=DurableFixtureMonitor(Path({str(self.db)!r}),Path({str(self.floor)!r}))\n"
            f"print(m.observe(fixture({sequence}),fault={crash!r}),flush=True)\n"
        )
        env = dict(os.environ, ARIO_R10_ALLOW_LAB_CRASH="YES_TEST_ONLY")
        return subprocess.run([sys.executable, "-c", code], capture_output=True,
                              text=True, timeout=12, env=env)

    def test_initial_bootstrap_is_explicit_not_silent_reset(self):
        self.assertEqual(self.lab.status()["seq"], 0)
        self.assertHold("HOLD_BOOTSTRAP_ALREADY_EXISTS", self.lab.initialize_empty_lab)

    def test_restart_recovers_durable_sequence_and_rejects_old_issuance(self):
        self.make_seq2()
        after_restart = DurableFixtureMonitor(self.db, self.floor)
        self.assertEqual(after_restart.status()["seq"], 2)
        self.assertEqual(after_restart.gate(1), "REJECT_STALE_PREFIX")
        self.assertEqual(after_restart.gate(2), "SAME_CHECKPOINT_NOT_FRESHNESS_PROOF")
        self.assertEqual(after_restart.observe(fixture(2)), "IDEMPOTENT_ALREADY_RECORDED_NOT_FRESHNESS")

    def test_no_online_access_is_hold_and_does_not_change_durable_state(self):
        self.make_seq1()
        self.assertHold("HOLD_EXTERNAL_LOG_UNAVAILABLE", lambda: self.lab.observe(fixture(2), outage=True))
        self.assertEqual(self.lab.gate(1, source_available=False), "HOLD_EXTERNAL_LOG_UNAVAILABLE")
        self.assertEqual(self.lab.status()["seq"], 1)

    def test_incomplete_monitor_scan_is_hold(self):
        self.make_seq1()
        self.assertHold("HOLD_MONITOR_SCAN_INCOMPLETE", lambda: self.lab.observe(fixture(2), scan_complete=False))
        self.assertEqual(self.lab.gate(1, scan_complete=False), "HOLD_MONITOR_SCAN_INCOMPLETE")

    def test_unknown_signer_and_forged_or_unlisted_receipts_are_held(self):
        original = fixture(1)
        bad = PinnedObservation(1, original.payload_sha256, original.proof_sha256,
                                original.leaf_index, signer_keyhash="0" * 64)
        self.assertHold("HOLD_WRONG_SIGNER", lambda: self.lab.observe(bad))
        bad2 = PinnedObservation(1, original.payload_sha256, "0" * 64, original.leaf_index)
        self.assertHold("HOLD_UNPINNED", lambda: self.lab.observe(bad2))
        self.assertHold("HOLD_UNKNOWN_SEQUENCE", lambda: self.lab.observe(fixture(3)))

    def test_unobserved_gap_and_stale_replay_fail_closed(self):
        self.assertHold("HOLD_UNVERIFIED_SEQUENCE_GAP", lambda: self.lab.observe(fixture(2)))
        self.make_seq2()
        self.assertHold("REJECT_STALE", lambda: self.lab.observe(fixture(1)))
        self.assertEqual(self.lab.gate(3), "HOLD_UNOBSERVED_EXTENSION")
        self.assertEqual(self.lab.gate(2, claim_payload_known=False), "HOLD_OPAQUE_CHECKSUM_NO_PLAINTEXT_CHECKPOINT")

    def test_different_process_crash_after_insert_before_floor_is_rolled_back(self):
        self.make_seq1()
        child = self.child(2, "after_insert")
        self.assertEqual(child.returncode, 83)
        self.assertEqual(self.lab.status()["seq"], 1)
        self.assertEqual(self.lab.observe(fixture(2)), "RECORDED_SYNTHETIC_ONLY_NOT_TRUTH")

    def test_crash_after_floor_before_commit_causes_hold_not_auto_repair(self):
        self.make_seq1()
        child = self.child(2, "after_floor")
        self.assertEqual(child.returncode, 83)
        self.assertHold("HOLD_LEDGER_ROLLBACK_BEHIND_RETAINED_FLOOR", self.lab.status)
        self.assertHold("HOLD_LEDGER_ROLLBACK_BEHIND_RETAINED_FLOOR", lambda: self.lab.observe(fixture(2)))

    def test_crash_after_commit_before_response_recovers_without_second_event(self):
        self.make_seq1()
        child = self.child(2, "after_commit")
        self.assertEqual(child.returncode, 83)
        self.assertEqual(self.lab.status()["seq"], 2)
        self.assertEqual(self.lab.observe(fixture(2)), "IDEMPOTENT_ALREADY_RECORDED_NOT_FRESHNESS")
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 2)

    def test_tamper_or_missing_external_floor_never_bootstraps_silently(self):
        self.make_seq2()
        self.floor.unlink()
        self.assertHold("HOLD_RETAINED_FLOOR_MISSING", self.lab.status)
        self.floor.write_text("{}")
        self.assertHold("HOLD_RETAINED_FLOOR_CORRUPT", self.lab.status)

    def test_db_row_mutation_is_detected_against_fixture_chain(self):
        self.make_seq2()
        with closing(sqlite3.connect(self.db)) as c:
            c.execute("UPDATE observations SET row_sha256 = ? WHERE seq = 2", ("0" * 64,))
        self.assertHold("HOLD_LEDGER_CHAIN_OR_ROW_TAMPER", self.lab.status)

    def test_publisher_db_rollback_only_rejected_against_retained_floor(self):
        self.make_seq1()
        snapshot_db = self.db.read_bytes()
        self.assertEqual(self.lab.observe(fixture(2)), "RECORDED_SYNTHETIC_ONLY_NOT_TRUTH")
        self.db.write_bytes(snapshot_db)
        self.assertHold("HOLD_LEDGER_ROLLBACK_BEHIND_RETAINED_FLOOR", self.lab.status)

    def test_joint_publisher_and_floor_rollback_remains_undetected(self):
        # NEGATIVE CONTROL, NOT A SUCCESSFUL REAL ANTI-ROLLBACK GUARANTEE.
        self.make_seq1()
        saved_db, saved_floor = self.db.read_bytes(), self.floor.read_bytes()
        self.assertEqual(self.lab.observe(fixture(2)), "RECORDED_SYNTHETIC_ONLY_NOT_TRUTH")
        self.db.write_bytes(saved_db)
        self.floor.write_bytes(saved_floor)
        self.assertEqual(self.lab.status()["seq"], 1)
        self.assertEqual(self.lab.gate(1), "SAME_CHECKPOINT_NOT_FRESHNESS_PROOF")

    def test_concurrent_duplicate_checkpoint_does_not_double_record(self):
        self.make_seq1()
        code = (
            "from pathlib import Path\n"
            "from research.r10_durable_monitor.monitor import DurableFixtureMonitor, fixture\n"
            f"m=DurableFixtureMonitor(Path({str(self.db)!r}),Path({str(self.floor)!r}))\n"
            "print(m.observe(fixture(2)),flush=True)\n"
        )
        env = dict(os.environ)
        procs = [subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, env=env) for _ in range(2)]
        results = [p.communicate(timeout=15) for p in procs]
        self.assertEqual(sorted(p.returncode for p in procs), [0, 0], results)
        self.assertCountEqual([r[0].strip() for r in results], [
            "RECORDED_SYNTHETIC_ONLY_NOT_TRUTH", "IDEMPOTENT_ALREADY_RECORDED_NOT_FRESHNESS"
        ])
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 2)

    def test_full_database_missing_during_recovery_is_hold(self):
        self.make_seq1()
        self.db.unlink()
        self.assertHold("HOLD_LOCAL_LEDGER_MISSING", self.lab.status)

    def test_diagnostic_gate_does_not_mint_freshness_or_authority(self):
        self.make_seq2()
        self.assertFalse(self.lab.status()["independent_custody"])
        self.assertFalse(self.lab.status()["trust_activation"])
        self.assertEqual(self.lab.gate(True), "HOLD_INVALID_PROPOSAL")
        self.assertEqual(self.lab.gate(2), "SAME_CHECKPOINT_NOT_FRESHNESS_PROOF")


if __name__ == "__main__":
    unittest.main()
