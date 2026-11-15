"""R9-B bounded real-process controls. All expectations are author-written.

NEGATIVE_CAPABILITY: root replay of both DBs; same-admin HMAC is not an independent witness.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

from r9b_fenced_sink import (SCOPE, FORMAT, ObserverClient, ConditionalSink,
                             Hold, canonical, digest, sign)

SCRIPT = Path(__file__).with_name("r9b_fenced_sink.py")


class R9BRealProcessTests(unittest.TestCase):
    def setUp(self):
        if os.name != "posix" or not hasattr(socket, "AF_UNIX"):
            self.skipTest("POSIX AF_UNIX process test required")
        self.tmp = tempfile.TemporaryDirectory(prefix="ario-r9b-disposable-")
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.sink = self.home / "effect_sink.db"
        self.observer = self.home / "observer.db"
        self.sock = self.home / "observer.sock"
        self.key = self.home / "ephemeral-only.bin"
        self.key.write_bytes(secrets.token_bytes(32))
        self.key.chmod(0o600)
        self.proc = None
        self.start()
        self.e1 = self.advance("corpus-e1")["head_hash"]

    def start(self):
        self.proc = subprocess.Popen([sys.executable, "-B", str(SCRIPT), "observer",
                                      "--observer-db", str(self.observer), "--socket", str(self.sock),
                                      "--key", str(self.key)], stdout=subprocess.DEVNULL,
                                     stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
        self.addCleanup(self.stop)
        for _ in range(300):
            if self.proc.poll() is not None:
                raise AssertionError("Observer crashed: " + self.proc.stderr.read().decode())
            if self.sock.exists() and self.call("head")[0] == 0:
                return
            time.sleep(.01)
        raise AssertionError("Observer failed to start")

    def stop(self):
        if self.proc is not None:
            if self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait(timeout=3)
            if self.proc.stderr:
                self.proc.stderr.close()
            self.proc = None
        if self.sock.exists():
            self.sock.unlink()

    def call(self, command, *args, key=None, timeout=20):
        child = subprocess.run([sys.executable, "-B", str(SCRIPT), command,
                                "--socket", str(self.sock), "--key", str(key or self.key),
                                "--sink-db", str(self.sink), *args],
                               capture_output=True, text=True, timeout=timeout)
        if child.returncode not in (0, 2, 77, 78):
            raise AssertionError(f"child error {child.returncode}: {child.stderr} {child.stdout}")
        return child.returncode, json.loads(child.stdout.strip()) if child.stdout.strip() else {}

    def advance(self, name, *args):
        code, result = self.call("advance", "--commitment", hashlib.sha256(name.encode()).hexdigest(), *args)
        if args:
            return code, result
        self.assertEqual((code, result.get("status")), (0, "ADVANCED"), result)
        return result

    def ticket(self, op="op-1", payload="view-A", head=None, seq=1, use="RESEARCH_VIEW", scope=SCOPE):
        return {"seq": seq, "head_hash": head or self.e1, "op_id": op,
                "payload_hash": hashlib.sha256(payload.encode()).hexdigest(), "use": use, "scope": scope}

    def action(self, ticket, *flags):
        return self.call("apply", "--ticket-json", json.dumps(ticket, sort_keys=True), *flags)

    def count(self):
        code, output = self.call("count")
        self.assertEqual(code, 0)
        return output["count"]

    def pending(self):
        code, res = self.call("head")
        self.assertEqual(code, 0)
        return res["pending"]

    def external_cas(self, seq, head, new):
        return self.call("observer-cas", "--expect-seq", str(seq),
                         "--expect-hash", head, "--commitment", new)

    def test_01_valid_local_effect(self):
        code, out = self.action(self.ticket())
        self.assertEqual((code, out["status"]), (0, "APPLIED_LOCAL_ONLY"))
        self.assertEqual((self.count(), self.pending()), (1, 0))

    def test_02_duplicate_exactly_one_effect(self):
        first = self.action(self.ticket())[1]
        second = self.action(self.ticket())[1]
        self.assertEqual(second["status"], "DUPLICATE_NO_EFFECT")
        self.assertEqual(first["receipt"], second["receipt"])
        self.assertEqual(self.count(), 1)

    def test_03_conflicting_reuse_rejected(self):
        self.action(self.ticket())
        self.assertEqual(self.action(self.ticket(payload="other"))[1]["reason"], "OP_ID_PAYLOAD_CONFLICT")
        self.assertEqual(self.count(), 1)

    def test_04_direct_observer_CAS_prior_to_reservation_revokes_old_ticket(self):
        changed = digest("out-of-band-privileged-change")
        code, res = self.external_cas(1, self.e1, changed)
        self.assertEqual((code, res["seq"]), (0, 2))
        code, out = self.action(self.ticket())
        self.assertEqual((code, out["reason"]), (2, "LOCAL_OBSERVER_MISMATCH"))
        self.assertEqual(self.count(), 0)

    def test_05_direct_CAS_after_RESERVE_is_refused_before_local_effect(self):
        code, out = self.action(self.ticket(op="crash-prepare"), "--crash-after-reserve")
        self.assertEqual((code, out), (77, {}))
        self.assertEqual(self.pending(), 1)
        code, out = self.external_cas(1, self.e1, digest("force-epoch-two"))
        self.assertEqual((code, out["reason"]), (2, "OBSERVER_PENDING_EFFECT_FENCE"))
        self.assertEqual(self.count(), 0)

    def test_06_pending_after_crash_blocks_new_actions_and_epochs(self):
        self.action(self.ticket(op="stop-mid"), "--crash-after-reserve")
        self.assertEqual(self.pending(), 1)
        code, output = self.action(self.ticket(op="different"))
        self.assertEqual((code, output["reason"]), (2, "PENDING_RECONCILIATION_REQUIRED"))
        code, output = self.call("advance", "--commitment", hashlib.sha256(b"e2").hexdigest())
        self.assertEqual((code, output["reason"]), (2, "PENDING_RECONCILIATION_REQUIRED"))
        self.assertEqual(self.count(), 0)

    def test_07_crash_after_local_write_requires_reconciliation(self):
        code, out = self.action(self.ticket(op="crash-after-commit"), "--crash-after-local")
        self.assertEqual((code, out), (78, {}))
        self.assertEqual((self.pending(), self.count()), (1, 1))
        code, output = self.action(self.ticket(op="crash-after-commit"))
        self.assertEqual((code, output["reason"]), (2, "PENDING_RECONCILIATION_REQUIRED"))
        # Local row exists, so a previous ACK would be misleading; this one never ACKed.

    def test_08_crash_between_observer_CAS_and_local_commit_fails_closed(self):
        code, out = self.advance("corpus-e2", "--crash-after-observer")
        self.assertEqual((code, out), (77, {}))
        code, result = self.action(self.ticket())
        self.assertEqual((code, result["reason"]), (2, "LOCAL_OBSERVER_MISMATCH"))
        self.assertEqual(self.count(), 0)

    def test_09_old_ticket_after_coordinated_advance_denied(self):
        self.advance("corpus-e2")
        code, out = self.action(self.ticket())
        self.assertEqual((code, out["reason"]), (2, "STALE_AT_SINK"))
        self.assertEqual(self.count(), 0)

    def test_10_aba_replay_denied(self):
        self.advance("corpus-e2")
        e3 = self.advance("corpus-e1")
        self.assertNotEqual(e3["head_hash"], self.e1)
        self.assertEqual(self.action(self.ticket())[1]["reason"], "STALE_AT_SINK")

    def test_11_observer_unavailable_holds(self):
        self.stop()
        code, result = self.action(self.ticket())
        self.assertEqual((code, result["reason"]), (2, "OBSERVER_UNREACHABLE"))
        self.assertEqual(self.count(), 0)

    def test_12_local_only_rollback_detected(self):
        before = self.home / "local-e1.db"
        shutil.copy2(self.sink, before)
        self.advance("corpus-e2")
        shutil.copy2(before, self.sink)
        self.assertEqual(self.action(self.ticket())[1]["reason"], "LOCAL_OBSERVER_MISMATCH")
        self.assertEqual(self.count(), 0)

    def test_13_eight_real_action_processes_one_effect(self):
        request = self.ticket(op="parallel-operation")
        with ThreadPoolExecutor(max_workers=8) as pool:
            outputs = list(pool.map(lambda i: self.action(request), range(8)))
        self.assertEqual(self.count(), 1, outputs)
        applied = sum(x[1].get("status") == "APPLIED_LOCAL_ONLY" for x in outputs)
        self.assertEqual(applied, 1, outputs)
        self.assertTrue(all(x[1].get("status") in ("APPLIED_LOCAL_ONLY", "DUPLICATE_NO_EFFECT", "HOLD") for x in outputs))
        self.assertEqual(self.pending(), 0)

    def test_14_action_epoch_race_serialized_at_observer(self):
        # Same source HEAD; action may precede epoch CAS, but never APPLIED after CAS.
        with ThreadPoolExecutor(max_workers=2) as pool:
            action_f = pool.submit(self.action, self.ticket(op="race"))
            epoch_f = pool.submit(self.advance, "corpus-e2")
            action = action_f.result()
            epoch = epoch_f.result()
        self.assertEqual(epoch["seq"], 2)
        if action[1].get("status") == "APPLIED_LOCAL_ONLY":
            self.assertEqual(self.count(), 1)
        else:
            self.assertEqual(action[0], 2)
            self.assertIn(action[1]["reason"], ("LOCAL_OBSERVER_MISMATCH", "STALE_AT_SINK"))
            self.assertEqual(self.count(), 0)
        self.assertEqual(self.pending(), 0)

    def test_15_wrong_HMAC_key_cannot_change_observer(self):
        wrong = self.home / "wrong-key.bin"
        wrong.write_bytes(secrets.token_bytes(32))
        code, out = self.call("head", key=wrong)
        self.assertEqual(code, 2)
        self.assertIn(out["reason"], ("OBSERVER_RESPONSE_AUTH_FAILED", "MALFORMED_OBSERVER_RESPONSE"))
        self.assertEqual(self.action(self.ticket())[1]["status"], "APPLIED_LOCAL_ONLY")

    def test_16_non_view_or_boolean_seq_rejected(self):
        for wrong in (self.ticket(use="EVIDENCE_ADMISSION"), self.ticket(scope="external-api"),
                      self.ticket(seq=True), self.ticket(op="")):
            code, res = self.action(wrong)
            self.assertEqual(code, 2)
        self.assertEqual(self.count(), 0)

    def test_18_privileged_epoch_change_between_head_read_and_reserve_is_rejected(self):
        # Exact disputed R9-A T17 timing: an out-of-band authorized CAS occurs
        # after HEAD was read but before the observer transaction RESERVE.
        base = ObserverClient(self.sock, self.key)
        seen = []

        class InterposedObserver:
            def call(self, op, **kw):
                current = base.call(op, **kw)
                if op == "HEAD" and not seen and current["seq"] == 1:
                    seen.append(current)
                    base.call("CAS", seq=1, head_hash=current["head_hash"],
                              next_hash=digest("interleaved-privileged-epoch"))
                return current

        sink = ConditionalSink(self.sink, InterposedObserver())
        with self.assertRaisesRegex(Hold, "OBSERVER_STALE_OBSERVER_HEAD"):
            sink.apply(self.ticket(op="interleaving-attack"))
        self.assertEqual((self.count(), self.pending()), (0, 0))
        self.assertEqual(len(seen), 1)

    def test_19_same_nonce_cannot_be_replayed_to_observer(self):
        body = {"format": FORMAT, "nonce": secrets.token_hex(16), "op": "HEAD"}
        key = self.key.read_bytes()
        message = canonical({"body": body, "mac": sign(key, body)}) + b"\n"

        def one():
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(4)
                sock.connect(str(self.sock))
                sock.sendall(message)
                buf = b""
                while not buf.endswith(b"\n"):
                    fragment = sock.recv(1024)
                    self.assertTrue(fragment)
                    buf += fragment
            received = json.loads(buf)
            self.assertTrue(hmac.compare_digest(received["mac"], sign(key, received["body"])))
            return received["body"]["value"]

        self.assertTrue(one()["ok"])
        failure = one()
        self.assertFalse(failure["ok"])
        self.assertEqual(failure["reason"], "REPLAYED_NONCE")

    def test_17_same_admin_rolls_back_both_databases_NEGATIVE_CAPABILITY(self):
        before_local, before_observer = self.home / "before-local.db", self.home / "before-observer.db"
        shutil.copy2(self.sink, before_local)
        self.stop()
        shutil.copy2(self.observer, before_observer)
        self.start()
        self.advance("corpus-e2")
        self.stop()
        shutil.copy2(before_local, self.sink)
        shutil.copy2(before_observer, self.observer)
        self.start()
        code, out = self.action(self.ticket(op="same-admin-rollback"))
        self.assertEqual((code, out["status"]), (0, "APPLIED_LOCAL_ONLY"))
        self.assertEqual(self.count(), 1)  # attack succeeds, NOT rollback resistance


if __name__ == "__main__":
    unittest.main()
