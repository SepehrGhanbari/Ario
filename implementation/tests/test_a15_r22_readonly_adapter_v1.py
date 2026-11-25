#!/usr/bin/env python3
"""Offline synthetic tests for the A15 R22 read-only checkpoint adapter."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

RESEARCH = Path(__file__).resolve().parents[1] / "research"
sys.path.insert(0, str(RESEARCH))
import a15_custodian_broker_v0_5 as broker
import a15_r22_readonly_adapter_v1 as adapter

BROKER_SOURCE = RESEARCH / "a15_custodian_broker_v0_5.py"
LEDGER_FILENAME = "custodian.sqlite3"
CHOICE = {
    "actor": "ARIO",
    "role": "RESEARCH_DIALOGUE",
    "origin": "CURRENT",
    "explicit_renewal": False,
    "risk": "LOW",
    "authorization": "ALLOWED",
    "usefulness": "USEFUL",
    "evidence": "SUFFICIENT",
    "preference": "ACCEPT",
    "duration": "BOUNDED",
}


def request(attempt):
    return {
        "v": 1,
        "run_id": "RUN_A15_R22_SYNTHETIC",
        "attempt_id": attempt,
        "choice_json": broker.encode(dict(CHOICE)),
        "claimed_status": "ACCEPT",
    }


class ReadOnlyAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="a15-r22-readonly-")
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / "state"
        self.state.mkdir(mode=0o700)

    def seed(self, count=1):
        journal = broker.Journal(self.state, provision=True)
        receipts = []
        for index in range(count):
            receipts.append(journal.consume(request("ATT_SYNTH_%02d" % (index + 1))))
        journal.conn.close()
        return receipts

    def build_initial(self):
        return adapter.build_checkpoint(
            self.state, "A15_SYNTHETIC_SCOPE", enroll_genesis=True,
        )

    def test_exact_pinned_broker_git_blob(self):
        data = BROKER_SOURCE.read_bytes()
        self.assertEqual(
            adapter.git_blob_sha1(data),
            adapter.BROKER_SOURCE_GIT_BLOB_SHA1,
        )

    def test_explicit_genesis_enrollment_is_required(self):
        self.seed()
        with self.assertRaises(adapter.AdapterHold):
            adapter.build_checkpoint(self.state, "A15_SYNTHETIC_SCOPE")

    def test_initial_enrollment_emits_canonical_commitment_only(self):
        receipts = self.seed(2)
        envelope = self.build_initial()
        payload = envelope["payload"]
        self.assertEqual(payload["enrollment"], "INITIAL_BASELINE")
        self.assertEqual(payload["previous_external_checkpoint_sha256"], "GENESIS")
        self.assertEqual(payload["broker_head"], {
            "seq": 2, "hash": receipts[-1]["chain_head_hash"],
        })
        self.assertEqual(
            envelope["payload_sha256"],
            hashlib.sha256(adapter.canonical(payload).encode("ascii")).hexdigest(),
        )
        encoded = adapter.canonical(envelope)
        self.assertEqual(json.loads(encoded), envelope)
        for forbidden in ("request_key", "choice_json", "input_hash", "run_id", "attempt_id"):
            self.assertNotIn(forbidden, encoded)

    def test_snapshot_is_read_only_and_creates_no_sidecars(self):
        self.seed(2)
        db = self.state / LEDGER_FILENAME
        floor = self.state / broker.FLOOR_NAME
        before_db = db.read_bytes()
        before_floor = floor.read_bytes()
        before_names = sorted(p.name for p in self.state.iterdir())
        before_db_stat = db.stat()
        before_floor_stat = floor.stat()

        self.build_initial()

        self.assertEqual(db.read_bytes(), before_db)
        self.assertEqual(floor.read_bytes(), before_floor)
        self.assertEqual(sorted(p.name for p in self.state.iterdir()), before_names)
        self.assertEqual(db.stat().st_size, before_db_stat.st_size)
        self.assertEqual(db.stat().st_mtime_ns, before_db_stat.st_mtime_ns)
        self.assertEqual(floor.stat().st_mtime_ns, before_floor_stat.st_mtime_ns)

    def test_continuation_links_previous_checkpoint_and_requires_advance(self):
        first_receipt = self.seed(1)[0]
        first = self.build_initial()
        previous = self.state.parent / "first-checkpoint.json"
        previous.write_text(adapter.canonical(first) + "\n", encoding="utf-8")

        journal = broker.Journal(self.state)
        second_receipt = journal.consume(request("ATT_SYNTH_02"))
        journal.conn.close()

        second = adapter.build_checkpoint(
            self.state,
            "A15_SYNTHETIC_SCOPE",
            previous_checkpoint_path=previous,
        )
        self.assertEqual(second["payload"]["enrollment"], "CONTINUATION")
        self.assertEqual(
            second["payload"]["previous_external_checkpoint_sha256"],
            first["payload_sha256"],
        )
        self.assertEqual(second["payload"]["broker_head"]["seq"], 2)
        self.assertEqual(
            second["payload"]["broker_head"]["hash"],
            second_receipt["chain_head_hash"],
        )
        repeated = adapter.build_checkpoint(
            self.state,
            "A15_SYNTHETIC_SCOPE",
            previous_checkpoint_path=previous,
        )
        self.assertEqual(repeated, second)  # deterministic retry; publisher must dedupe by digest

    def test_previous_checkpoint_detects_joint_local_rollback_when_retained_externally(self):
        self.seed(1)
        first_db = (self.state / LEDGER_FILENAME).read_bytes()
        first_floor = (self.state / broker.FLOOR_NAME).read_bytes()
        first = self.build_initial()
        previous = self.state.parent / "external-retained-checkpoint.json"
        previous.write_text(adapter.canonical(first) + "\n", encoding="utf-8")

        journal = broker.Journal(self.state)
        journal.consume(request("ATT_SYNTH_02"))
        journal.conn.close()
        second = adapter.build_checkpoint(
            self.state,
            "A15_SYNTHETIC_SCOPE",
            previous_checkpoint_path=previous,
        )
        self.assertEqual(second["payload"]["broker_head"]["seq"], 2)
        second_checkpoint = self.state.parent / "second-checkpoint.json"
        second_checkpoint.write_text(adapter.canonical(second) + "\n", encoding="utf-8")

        # Simulate same-admin rollback of BOTH local files. The retained seq=2
        # checkpoint is kept outside the rolled-back local state directory.
        (self.state / LEDGER_FILENAME).write_bytes(first_db)
        (self.state / broker.FLOOR_NAME).write_bytes(first_floor)
        with self.assertRaises(adapter.AdapterHold):
            adapter.build_checkpoint(
                self.state,
                "A15_SYNTHETIC_SCOPE",
                previous_checkpoint_path=second_checkpoint,
            )

    def test_same_sequence_fork_is_detected(self):
        first_state = self.state
        self.seed(1)
        first = self.build_initial()
        previous = self.state.parent / "first.json"
        previous.write_text(adapter.canonical(first) + "\n", encoding="utf-8")

        fork_state = Path(self.temp.name) / "fork"
        fork_state.mkdir(mode=0o700)
        fork_journal = broker.Journal(fork_state, provision=True)
        fork_req = request("ATT_DIFFERENT")
        fork_req["choice_json"] = broker.encode({
            **CHOICE, "preference": "DECLINE",
        })
        fork_req["claimed_status"] = "DECLINE"
        fork_journal.consume(fork_req)
        fork_journal.conn.close()

        with self.assertRaises(adapter.AdapterHold):
            adapter.build_checkpoint(
                fork_state,
                "A15_SYNTHETIC_SCOPE",
                previous_checkpoint_path=previous,
            )

    def test_stale_or_modified_floor_holds_without_repair(self):
        self.seed(2)
        floor = self.state / broker.FLOOR_NAME
        original = floor.read_bytes()
        payload = json.loads(original)
        payload["expected_seq"] = 1
        floor.write_text(json.dumps(payload), encoding="utf-8")
        changed = floor.read_bytes()
        with self.assertRaises(adapter.AdapterHold):
            self.build_initial()
        self.assertEqual(floor.read_bytes(), changed)

        payload["expected_seq"] = 2
        payload["expected_hash"] = "0" * 64
        floor.write_text(json.dumps(payload), encoding="utf-8")
        changed = floor.read_bytes()
        with self.assertRaises(adapter.AdapterHold):
            self.build_initial()
        self.assertEqual(floor.read_bytes(), changed)
        self.assertNotEqual(floor.read_bytes(), original)

    def test_duplicate_or_extra_floor_fields_hold(self):
        self.seed(1)
        floor = self.state / broker.FLOOR_NAME
        floor.write_text(
            '{"format":"a15-custodian-floor-v1","format":"forged",'
            '"ledger":"custodian.sqlite3","expected_seq":1,'
            '"expected_hash":"' + "0" * 64 + '"}',
            encoding="utf-8",
        )
        with self.assertRaises(adapter.AdapterHold):
            self.build_initial()

    def test_tampered_broker_hash_chain_holds(self):
        self.seed(1)
        db = self.state / LEDGER_FILENAME
        conn = sqlite3.connect(str(db))
        conn.execute("UPDATE events SET hash=? WHERE seq=1", ("0" * 64,))
        conn.commit()
        conn.close()
        with self.assertRaises(adapter.AdapterHold):
            self.build_initial()

    def test_unexpected_schema_holds(self):
        db = self.state / LEDGER_FILENAME
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE unexpected(value TEXT)")
        conn.commit()
        conn.close()
        floor = self.state / broker.FLOOR_NAME
        floor.write_text(json.dumps({
            "format": broker.FLOOR_FORMAT,
            "ledger": LEDGER_FILENAME,
            "expected_seq": 0,
            "expected_hash": "GENESIS",
        }), encoding="utf-8")
        with self.assertRaises(adapter.AdapterHold):
            self.build_initial()

    def test_sqlite_sidecar_holds(self):
        self.seed(1)
        (self.state / (LEDGER_FILENAME + "-wal")).write_bytes(b"synthetic")
        with self.assertRaises(adapter.AdapterHold):
            self.build_initial()

    def test_source_blob_mismatch_holds(self):
        self.seed(1)
        altered = Path(self.temp.name) / "altered_broker.py"
        altered.write_bytes(BROKER_SOURCE.read_bytes() + b"\n# altered")
        with self.assertRaises(adapter.AdapterHold):
            adapter.build_checkpoint(
                self.state,
                "A15_SYNTHETIC_SCOPE",
                enroll_genesis=True,
                broker_source_path=altered,
            )

    def test_invalid_scope_and_previous_checkpoint_scope_hold(self):
        self.seed(1)
        with self.assertRaises(adapter.AdapterHold):
            adapter.build_checkpoint(self.state, "scope-with-lowercase", enroll_genesis=True)
        first = self.build_initial()
        other_scope = self.state.parent / "other-scope.json"
        payload = dict(first["payload"])
        payload["journal_scope"] = "OTHER_SYNTHETIC_SCOPE"
        other = {
            "payload": payload,
            "payload_sha256": hashlib.sha256(
                adapter.canonical(payload).encode("ascii")
            ).hexdigest(),
        }
        other_scope.write_text(adapter.canonical(other) + "\n", encoding="utf-8")
        journal = broker.Journal(self.state)
        journal.consume(request("ATT_SYNTH_02"))
        journal.conn.close()
        with self.assertRaises(adapter.AdapterHold):
            adapter.build_checkpoint(
                self.state,
                "A15_SYNTHETIC_SCOPE",
                previous_checkpoint_path=other_scope,
            )

    def test_cli_outputs_envelope_and_never_writes_checkpoint_file(self):
        self.seed(1)
        command = [
            sys.executable,
            str(RESEARCH / "a15_r22_readonly_adapter_v1.py"),
            "--state-dir", str(self.state),
            "--journal-scope", "A15_SYNTHETIC_SCOPE",
            "--enroll-genesis",
        ]
        before = sorted(p.name for p in self.state.iterdir())
        result = subprocess.run(
            command, text=True, encoding="utf-8",
            capture_output=True, timeout=15, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["payload"]["broker_head"]["seq"], 1)
        self.assertEqual(sorted(p.name for p in self.state.iterdir()), before)


    def test_sqlite_connection_is_uri_read_only_and_query_only(self):
        self.seed(1)
        original = adapter.sqlite3.connect
        calls = []
        statements = []

        def traced_connect(database, *args, **kwargs):
            calls.append((database, kwargs.get("uri")))
            connection = original(database, *args, **kwargs)
            connection.set_trace_callback(statements.append)
            return connection

        with patch.object(adapter.sqlite3, "connect", side_effect=traced_connect):
            self.build_initial()

        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][1])
        self.assertIn("mode=ro", calls[0][0])
        self.assertIn("PRAGMA query_only=ON", statements)
        forbidden = ("INSERT ", "UPDATE ", "DELETE ", "CREATE ", "DROP ", "ALTER ", "REPLACE ")
        self.assertFalse(any(s.lstrip().upper().startswith(forbidden) for s in statements))

    def test_floor_change_during_snapshot_holds_without_repair(self):
        self.seed(1)
        original = adapter._read_regular_file
        floor_reads = 0

        def changing_floor(path, max_bytes, label):
            nonlocal floor_reads
            data = original(path, max_bytes, label)
            if Path(path).name == broker.FLOOR_NAME:
                floor_reads += 1
                if floor_reads == 2:
                    return data + b" "
            return data

        with patch.object(adapter, "_read_regular_file", side_effect=changing_floor):
            with self.assertRaises(adapter.AdapterHold):
                self.build_initial()

    def test_database_symlink_is_refused(self):
        self.seed(1)
        db = self.state / LEDGER_FILENAME
        target = self.state / "ledger-target.sqlite3"
        db.rename(target)
        try:
            db.symlink_to(target.name)
        except (OSError, NotImplementedError):
            target.rename(db)
            self.skipTest("symlink creation is unavailable on this runner")
        with self.assertRaises(adapter.AdapterHold):
            self.build_initial()

    def test_previous_checkpoint_digest_tampering_holds(self):
        self.seed(1)
        first = self.build_initial()
        previous = self.state.parent / "tampered-previous.json"
        tampered = dict(first)
        tampered["payload_sha256"] = "0" * 64
        previous.write_text(adapter.canonical(tampered) + "\n", encoding="utf-8")
        journal = broker.Journal(self.state)
        journal.consume(request("ATT_SYNTH_02"))
        journal.conn.close()
        with self.assertRaises(adapter.AdapterHold):
            adapter.build_checkpoint(
                self.state,
                "A15_SYNTHETIC_SCOPE",
                previous_checkpoint_path=previous,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
