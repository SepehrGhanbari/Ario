"""R22.8: bind R22.7 floor bytes to R9-C's existing two-process receipt lab.

Linux disposable AF_UNIX processes, synthetic ephemeral HMAC keys and SQLite.
This is not a remote independently administered service or a production adapter.
"""
import hashlib
import hmac
import importlib.util
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time

import pytest

from test_r22_7_retained_witness_floor import (
    SCOPE, advance, assess, floor_record, history, ledger, provision, read_floor, r10,
)
from test_r22_5_replay_aba_boundary import sample
from test_r22_6_ci_witness_prefix_integration import observed_rows

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="R9-C POSIX socket process lab; Linux only"
)

SOURCE = (Path(__file__).resolve().parents[2] / "experiments" /
          "r9c-conditional-destination-2026-11-15" / "r9c_conditional_destination.py")
spec = importlib.util.spec_from_file_location("r22_8_pinned_r9c", SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def commitment(record):
    # Binds complete canonical retained record, including scope and both anchors.
    return m.sha("R22.8-FLOOR-v1", record)


def op_id(count):
    return "R22-8-FLOOR-" + str(count)


class Lab:
    def __init__(self, root):
        self.root = root
        self.floor = root / "publisher-floor.json"
        self.rows = history()
        provision(self.floor, self.rows)
        self.procs = {}
        for name in ("dk", "wk", "seal"):
            path = root / name
            path.write_bytes(secrets.token_bytes(32))
            path.chmod(0o600)
        self.dest = m.WireClient(self.sock("dest"), (root / "dk").read_bytes())
        self.wit = m.WireClient(self.sock("witness"), (root / "wk").read_bytes())
        self.co = m.CoordinatedResearch(self.dest, self.wit)

    def sock(self, role):
        return self.root / ("d.sock" if role == "dest" else "w.sock")

    def db(self, role):
        return self.root / (role + ".sqlite3")

    def stop(self, role):
        p = self.procs.pop(role, None)
        if p is not None:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait(timeout=3)
            p.stderr.close()
        self.sock(role).unlink(missing_ok=True)

    def start(self, role, **faults):
        self.stop(role)
        env = dict(os.environ)
        for k in ("R9C_KILL_AFTER_COMMIT_OP", "R9C_KILL_AFTER_WIT_RECORD_IDX"):
            env.pop(k, None)
        env.update(faults)
        key = self.root / ("dk" if role == "dest" else "wk")
        p = subprocess.Popen(
            [sys.executable, "-B", str(SOURCE), role, "--db", str(self.db(role)),
             "--socket", str(self.sock(role)), "--auth-key", str(key),
             "--receipt-key", str(self.root / "seal")],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=env,
        )
        self.procs[role] = p
        for _ in range(200):
            if p.poll() is not None:
                raise RuntimeError("R9-C startup failed: " + p.stderr.read().decode()[:500])
            if self.sock(role).exists():
                try:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                        s.settimeout(0.2)
                        s.connect(str(self.sock(role)))
                    return
                except OSError:
                    pass
            time.sleep(0.025)
        raise RuntimeError("R9-C socket startup timeout")

    def initialize(self):
        self.start("dest")
        self.start("witness")
        r = self.co.advance(m.sha("R22.8-SCOPE", SCOPE))
        assert r["status"] == "SIMULATED_EPOCH_CHECKPOINTED_NOT_INDEPENDENT"
        h = self.co.heads()
        self.epoch = (h["epoch"], h["epoch_hash"])
        assert self.epoch[0] == 1 and h["idx"] == 1
        assert self.commit()["status"] == "SIMULATED_EFFECT_CHECKPOINTED_NOT_INDEPENDENT"

    def commit(self):
        record, _ = read_floor(self.floor)
        return self.co.apply(op_id(record["seq"]), commitment(record))

    def prepare_next(self):
        assert advance(self.floor, self.rows) == "ADVANCED_LAB_FLOOR_ONLY"

    def verify(self, raw):
        """Conditional matching of current retained floor and receipt tip.

        No promotion, no implicit repair, no trusted statement of external origin.
        The verifier shares lab HMAC material: not an independence boundary.
        """
        try:
            record, _ = read_floor(self.floor)
            if assess(raw, self.floor) != "MATCH_RETAINED_LAB_CHECKPOINT_ONLY":
                return "HOLD_LOCAL_FLOOR"
            h = self.co.heads()
            expected_index = {2: 2, 4: 3}[record["seq"]]
            lookup = self.dest.call("DEST_LOOKUP", op_id=op_id(record["seq"]))
            if lookup.get("status") != "FOUND":
                return "HOLD_NO_RECEIPT"
            proof = lookup["proof"]
            p = proof["body"]
            if (not hmac.compare_digest(proof["mac"], m.sig((self.root / "seal").read_bytes(), p))
                    or p["format"] != m.CERT or p["kind"] != "APPLY"
                    or p["op_id"] != op_id(record["seq"])
                    or p["payload_hash"] != commitment(record)
                    or (p["epoch"], p["epoch_hash"]) != self.epoch
                    or (h["epoch"], h["epoch_hash"]) != self.epoch
                    or p["idx"] != expected_index or h["idx"] != expected_index
                    or p["event_hash"] != h["event_hash"]
                    or p["event_hash"] != m.sha("R9C-EVENT", p["idx"], p["prev"],
                                                p["kind"], p["epoch"], p["epoch_hash"],
                                                p["op_id"], p["payload_hash"])):
                return "HOLD_RECEIPT_OR_FLOOR_MISMATCH"
            return "MATCH_LAB_RECEIPT_TIP_ONLY"
        except (m.Hold, OSError, ValueError, TypeError, KeyError):
            return "HOLD_UNCERTAIN_OR_INVALID"

    def counts(self):
        result = []
        for role, table in (("dest", "effects"), ("witness", "checkpoints")):
            con = sqlite3.connect(self.db(role))
            try:
                result.append(con.execute("SELECT COUNT(*) FROM " + table).fetchone()[0])
            finally:
                con.close()
        return tuple(result)

    def snapshot(self):
        # Quiesce both processes before copying SQLite files.
        self.stop("dest")
        self.stop("witness")
        saved = (self.db("dest").read_bytes(), self.db("witness").read_bytes(),
                 self.floor.read_bytes())
        self.start("dest")
        self.start("witness")
        return saved

    def restore(self, saved, *, joint=False):
        self.stop("dest")
        if joint:
            self.stop("witness")
            self.db("witness").write_bytes(saved[1])
        self.db("dest").write_bytes(saved[0])
        self.floor.write_bytes(saved[2])
        self.start("dest")
        if joint:
            self.start("witness")


@pytest.fixture
def lab():
    with tempfile.TemporaryDirectory(prefix="r22-8-", dir="/tmp") as directory:
        x = Lab(Path(directory))
        try:
            x.initialize()
            yield x
        finally:
            x.stop("dest")
            x.stop("witness")


def test_bound_receipt_tip_matches_and_advances(lab):
    assert lab.verify(ledger(lab.rows[:2])) == "MATCH_LAB_RECEIPT_TIP_ONLY"
    lab.prepare_next()
    assert lab.verify(ledger(lab.rows)) == "HOLD_NO_RECEIPT"
    assert lab.commit()["status"] == "SIMULATED_EFFECT_CHECKPOINTED_NOT_INDEPENDENT"
    assert lab.verify(ledger(lab.rows)) == "MATCH_LAB_RECEIPT_TIP_ONLY"
    assert lab.counts() == (2, 3)


def test_publisher_restore_with_witness_retained(lab):
    old = lab.snapshot()
    lab.prepare_next()
    lab.commit()
    lab.restore(old)
    assert lab.wit.call("WIT_HEAD")["idx"] == 3
    assert lab.dest.call("DEST_HEAD")["idx"] == 2
    assert lab.verify(ledger(lab.rows[:2])) == "HOLD_UNCERTAIN_OR_INVALID"


def test_joint_admin_restore_is_preserved_residual(lab):
    old = lab.snapshot()
    lab.prepare_next()
    lab.commit()
    lab.restore(old, joint=True)
    assert lab.verify(ledger(lab.rows[:2])) == "MATCH_LAB_RECEIPT_TIP_ONLY"
    assert lab.counts() == (1, 2)


def test_witness_outage_does_not_mint_receipt(lab):
    lab.prepare_next()
    lab.stop("witness")
    with pytest.raises(m.Hold, match="UNCERTAIN_REMOTE_RESULT"):
        lab.commit()
    assert lab.verify(ledger(lab.rows)) == "HOLD_UNCERTAIN_OR_INVALID"
    assert lab.dest.call("DEST_HEAD")["idx"] == 2
    lab.start("witness")
    assert lab.commit()["status"] == "SIMULATED_EFFECT_CHECKPOINTED_NOT_INDEPENDENT"
    assert lab.counts() == (2, 3)


def test_witness_process_death_after_commit_before_reply(lab):
    lab.prepare_next()
    lab.start("witness", R9C_KILL_AFTER_WIT_RECORD_IDX="3")
    assert lab.commit()["status"] == "HOLD_UNCERTAIN_CHECKPOINT"
    assert lab.procs["witness"].wait(timeout=5) == 76
    lab.start("witness")
    assert lab.wit.call("WIT_HEAD")["idx"] == 3
    assert lab.co.reconcile(op_id(4))["status"] == "SIMULATED_RECONCILED_NOT_INDEPENDENT"
    assert lab.verify(ledger(lab.rows)) == "MATCH_LAB_RECEIPT_TIP_ONLY"
    assert lab.counts() == (2, 3)


def test_destination_process_death_after_commit_before_reply(lab):
    lab.prepare_next()
    lab.start("dest", R9C_KILL_AFTER_COMMIT_OP=op_id(4))
    assert lab.commit()["status"] == "HOLD_UNCERTAIN_DESTINATION"
    assert lab.procs["dest"].wait(timeout=5) == 75
    lab.start("dest")
    assert lab.wit.call("WIT_HEAD")["idx"] == 2
    assert lab.dest.call("DEST_HEAD")["idx"] == 3
    assert lab.verify(ledger(lab.rows)) == "HOLD_UNCERTAIN_OR_INVALID"
    assert lab.co.reconcile(op_id(4))["status"] == "SIMULATED_RECONCILED_NOT_INDEPENDENT"
    assert lab.verify(ledger(lab.rows)) == "MATCH_LAB_RECEIPT_TIP_ONLY"
    assert lab.counts() == (2, 3)


def test_old_authentic_receipt_cannot_rewind_witness(lab):
    old = lab.dest.call("DEST_LOOKUP", op_id=op_id(2))["proof"]
    lab.prepare_next()
    lab.commit()
    with pytest.raises(m.Hold, match="CHECKPOINT_GAP_OR_CONFLICT"):
        lab.wit.call("WIT_RECORD", proof=old)
    assert lab.wit.call("WIT_HEAD")["idx"] == 3
    assert lab.counts() == (2, 3)


def test_replayed_response_fails_fresh_request_nonce(lab, monkeypatch):
    body = {"format": m.PROTOCOL, "nonce": secrets.token_hex(16), "op": "WIT_HEAD"}
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(3)
        s.connect(str(lab.sock("witness")))
        s.sendall(m.canonical({"body": body, "mac": m.sig(lab.wit.key, body)}) + b"\n")
        old = m.read_packet(s)
    assert old["body"]["nonce"] == body["nonce"]
    assert hmac.compare_digest(old["mac"], m.sig(lab.wit.key, old["body"]))
    lab.prepare_next()
    lab.commit()
    monkeypatch.setattr(m, "read_packet", lambda _: old)
    with pytest.raises(m.Hold, match="INVALID_RESPONSE_AUTH"):
        lab.wit.call("WIT_HEAD")


def test_resealed_same_count_floor_cannot_reuse_receipt(lab):
    lab.prepare_next()
    lab.commit()
    w, o = sample("stable")
    fork = observed_rows(w, o)
    r10._write_floor(lab.floor, floor_record(fork, 4))
    assert assess(ledger(fork), lab.floor) == "MATCH_RETAINED_LAB_CHECKPOINT_ONLY"
    assert lab.verify(ledger(fork)) == "HOLD_RECEIPT_OR_FLOOR_MISMATCH"
    assert lab.counts() == (2, 3)


def test_idempotent_retry_does_not_duplicate_commitment(lab):
    lab.prepare_next()
    lab.commit()
    again = lab.commit()
    assert again["status"] == "SIMULATED_EFFECT_CHECKPOINTED_NOT_INDEPENDENT"
    assert again["destination_status"] == "ALREADY_APPLIED_DESTINATION"
    assert lab.counts() == (2, 3)
    assert lab.verify(ledger(lab.rows)) == "MATCH_LAB_RECEIPT_TIP_ONLY"
