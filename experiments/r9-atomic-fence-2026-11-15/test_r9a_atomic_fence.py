"""Real multi-process R9-A research controls, including a retained negative.

All expectations and labels are investigator-authored, not blinded verification.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

from r9a_atomic_fence import ALLOWED_SCOPE, FORMAT, GENESIS, canonical, digest, sign

SOURCE = Path(__file__).resolve().with_name("r9a_atomic_fence.py")


class R9AMultiProcess(unittest.TestCase):
    def setUp(self):
        if os.name != "posix" or not hasattr(socket, "AF_UNIX"):
            self.skipTest("R9-A AF_UNIX process experiment requires POSIX")
        self.tmp = tempfile.TemporaryDirectory(prefix="ario-r9a-disposable-")
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.ckpt = self.home / "checkpoint.db"
        self.sink = self.home / "action_sink.db"
        self.sock = self.home / "checkpoint.sock"
        self.key_file = self.home / "ephemeral_test_key.bin"
        self.key_file.write_bytes(secrets.token_bytes(32))
        self.key_file.chmod(0o600)
        self.server = None
        self.start_witness()
        self.e1 = self.epoch("index-A")["digest"]

    def start_witness(self):
        self.server = subprocess.Popen(
            [sys.executable, "-B", str(SOURCE), "witness", "--checkpoint-db", str(self.ckpt),
             "--socket", str(self.sock), "--key-file", str(self.key_file)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        self.addCleanup(self.stop_witness)
        for _ in range(200):
            if self.server.poll() is not None:
                raise AssertionError("Witness terminated unexpectedly: " + self.server.stderr.read().decode())
            if self.sock.exists():
                probe = self.cli("head")
                if probe[0] == 0:
                    return
            time.sleep(0.01)
        raise AssertionError("Witness socket did not become ready")

    def stop_witness(self):
        if self.server is not None and self.server.poll() is None:
            self.server.terminate()
            try:
                self.server.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.server.kill()
                self.server.wait(timeout=3)
        if self.server is not None and self.server.stderr is not None:
            self.server.stderr.close()
        self.server = None
        # This experiment owns the fresh temporary socket; no user files touched.
        if self.sock.exists():
            self.sock.unlink()

    def cli(self, mode, *args, key=None, timeout=14):
        proc = subprocess.run(
            [sys.executable, "-B", str(SOURCE), mode, "--sink-db", str(self.sink),
             "--socket", str(self.sock), "--key-file", str(key or self.key_file), *args],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, text=True, check=False,
        )
        try:
            out = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
        except json.JSONDecodeError as exc:
            raise AssertionError(f"Invalid child JSON (exit={proc.returncode}): {proc.stdout} / {proc.stderr}") from exc
        if proc.returncode not in (0, 2, 77):
            raise AssertionError(f"Unexpected child exit {proc.returncode}: {proc.stderr} / {proc.stdout}")
        return proc.returncode, out

    def epoch(self, name, crash=False):
        opts = ("--commitment", hashlib.sha256(name.encode()).hexdigest())
        if crash:
            code, result = self.cli("epoch", *opts, "--crash-after-checkpoint")
            self.assertEqual(code, 77)
            self.assertFalse(result)
            return None
        code, result = self.cli("epoch", *opts)
        self.assertEqual((code, result.get("status")), (0, "ADVANCED"), result)
        return result

    def ticket(self, op="op-01", seq=1, head=None, payload="payload-A", use="RESEARCH_VIEW", scope=ALLOWED_SCOPE):
        return {"seq": seq, "head_digest": head or self.e1,
                "op_id": op, "payload_digest": hashlib.sha256(payload.encode()).hexdigest(),
                "use": use, "scope": scope}

    def action(self, ticket):
        return self.cli("action", "--ticket-json", json.dumps(ticket, sort_keys=True))

    def count(self):
        code, out = self.cli("count")
        self.assertEqual(code, 0)
        return out["count"]

    def test_01_valid_action_commits_locally(self):
        code, result = self.action(self.ticket())
        self.assertEqual((code, result["status"]), (0, "APPLIED"))
        self.assertEqual(self.count(), 1)

    def test_02_same_id_repeated_has_no_second_effect(self):
        first = self.action(self.ticket())[1]
        second = self.action(self.ticket())[1]
        self.assertEqual(first["receipt"], second["receipt"])
        self.assertEqual(second["status"], "DUPLICATE_NO_NEW_EFFECT")
        self.assertEqual(self.count(), 1)

    def test_03_same_id_different_payload_holds(self):
        self.assertEqual(self.action(self.ticket())[1]["status"], "APPLIED")
        code, out = self.action(self.ticket(payload="DIFFERENT"))
        self.assertEqual((code, out["reason"]), (2, "DUPLICATE_OP_CONFLICT"))
        self.assertEqual(self.count(), 1)

    def test_04_stale_ticket_after_epoch_transition(self):
        stale = self.ticket()
        self.epoch("index-B")
        code, out = self.action(stale)
        self.assertEqual((code, out["reason"]), (2, "STALE_AT_EFFECT_BOUNDARY"))
        self.assertEqual(self.count(), 0)

    def test_05_aba_stale_even_if_corpus_text_repeats(self):
        stale = self.ticket()
        self.epoch("index-B")
        e3 = self.epoch("index-A")
        self.assertNotEqual(e3["digest"], self.e1)
        self.assertEqual(self.action(stale)[1]["reason"], "STALE_AT_EFFECT_BOUNDARY")
        self.assertEqual(self.count(), 0)

    def test_06_witness_unreachable_holds_without_effect(self):
        self.stop_witness()
        code, out = self.action(self.ticket())
        self.assertEqual((code, out["reason"]), (2, "CHECKPOINT_UNREACHABLE"))
        self.assertEqual(self.count(), 0)

    def test_07_real_crash_after_witness_before_sink_commit_holds(self):
        self.epoch("index-B", crash=True)
        code, out = self.action(self.ticket())
        self.assertEqual((code, out["reason"]), (2, "CHECKPOINT_LOCAL_MISMATCH"))
        self.assertEqual(self.count(), 0)
        head = self.cli("head")[1]
        self.assertEqual(head["local"][0], 1)
        self.assertEqual(head["checkpoint"][0], 2)

    def test_08_local_sink_disk_rollback_is_detected(self):
        snapshot = self.home / "sink_E1_copy.db"
        shutil.copy2(self.sink, snapshot)
        self.epoch("index-B")
        # No process is holding the sink database open at this point.
        shutil.copy2(snapshot, self.sink)
        code, out = self.action(self.ticket())
        self.assertEqual((code, out["reason"]), (2, "CHECKPOINT_LOCAL_MISMATCH"))
        self.assertEqual(self.count(), 0)

    def test_09_same_admin_can_rollback_both_NEGATIVE_CAPABILITY(self):
        sink_copy, witness_copy = self.home / "sink_before.db", self.home / "checkpoint_before.db"
        shutil.copy2(self.sink, sink_copy)
        self.stop_witness()  # clean shutdown ensures checkpoint SQLite files are closed
        shutil.copy2(self.ckpt, witness_copy)
        self.start_witness()
        self.epoch("index-B")
        self.stop_witness()
        shutil.copy2(sink_copy, self.sink)
        shutil.copy2(witness_copy, self.ckpt)
        self.start_witness()
        # This is a successful ATTACK, not a successful anti-rollback guarantee.
        code, out = self.action(self.ticket())
        self.assertEqual((code, out["status"]), (0, "APPLIED"))
        self.assertEqual(self.count(), 1)

    def test_10_non_view_evidence_admission_is_not_supported(self):
        for bad in (self.ticket(use="EVIDENCE_ADMISSION"), self.ticket(scope="external:http")):
            with self.subTest(bad=bad):
                code, out = self.action(bad)
                self.assertEqual((code, out["reason"]), (2, "NO_ACTION_AUTHORITY"))
        self.assertEqual(self.count(), 0)

    def test_11_forged_head_refused(self):
        code, out = self.action(self.ticket(head="0" * 64))
        self.assertEqual((code, out["reason"]), (2, "STALE_AT_EFFECT_BOUNDARY"))
        self.assertEqual(self.count(), 0)

    def test_12_eight_real_processes_same_operation_commit_at_most_once(self):
        ticket = self.ticket(op="concurrent-01")
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.action(ticket), range(8)))
        self.assertEqual(sum(x[1].get("status") == "APPLIED" for x in results), 1, results)
        self.assertEqual(sum(x[1].get("status") == "DUPLICATE_NO_NEW_EFFECT" for x in results), 7, results)
        self.assertEqual(self.count(), 1)

    def test_13_real_epoch_action_race_serializes_without_false_approval(self):
        ticket = self.ticket(op="racing-01")
        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(self.epoch, "index-B")
            f2 = pool.submit(self.action, ticket)
            advanced, action_result = f1.result(), f2.result()
        self.assertEqual(advanced["seq"], 2)
        self.assertIn(action_result[1].get("status"), ("HOLD", "APPLIED"))
        if action_result[1]["status"] == "HOLD":
            self.assertEqual(action_result[1]["reason"], "STALE_AT_EFFECT_BOUNDARY")
            self.assertEqual(self.count(), 0)
        else:
            self.assertEqual(self.count(), 1)
        code, out = self.action(self.ticket(op="different-later"))
        self.assertEqual((code, out["reason"]), (2, "STALE_AT_EFFECT_BOUNDARY"))

    def test_14_wrong_hmac_key_never_authorizes_effect(self):
        wrong = self.home / "wrong_test_key.bin"
        wrong.write_bytes(secrets.token_bytes(32))
        code, out = self.cli("action", "--ticket-json", json.dumps(self.ticket()), key=wrong)
        self.assertEqual(code, 2)
        self.assertIn(out["reason"], ("INVALID_CHECKPOINT_RESPONSE_AUTH", "MALFORMED_CHECKPOINT_RESPONSE"))
        self.assertEqual(self.count(), 0)

    def test_15_request_nonce_replay_refused_at_witness(self):
        key = self.key_file.read_bytes()
        body = {"protocol": FORMAT, "nonce": secrets.token_hex(16), "op": "HEAD"}
        msg = canonical({"body": body, "mac": sign(key, body)}) + b"\n"
        def send():
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                s.connect(str(self.sock))
                s.sendall(msg)
                buf = b""
                while not buf.endswith(b"\n"):
                    buf += s.recv(2048)
            raw = json.loads(buf)
            self.assertEqual(raw["mac"], sign(key, raw["body"]))
            return raw["body"]["value"]
        first = send()
        second = send()
        self.assertTrue(first["ok"])
        self.assertFalse(second["ok"])
        self.assertEqual(second["reason"], "REPLAYED_REQUEST_NONCE")

    def test_17_out_of_band_checkpoint_CAS_during_action_NEGATIVE_CAPABILITY(self):
        # This uses a REAL separate checkpoint process. Only the reader is
        # deliberately interposed in the test process, to force this ordering.
        # An actor allowed to directly CAS the checkpoint bypasses the local
        # sink lock, so a local effect can commit after external epoch change.
        from r9a_atomic_fence import ActionSink, CheckpointClient
        base = CheckpointClient(self.sock, self.key_file)

        class UncoordinatedClient:
            changed = False

            def request(self, op, **args):
                seen = base.request(op, **args)
                if op == "HEAD" and not self.changed:
                    self.changed = True
                    external_head = digest("out_of_band", seen[0] + 1, seen[1])
                    got = base.request("CAS", expected_seq=seen[0], expected_digest=seen[1],
                                       new_seq=seen[0] + 1, new_digest=external_head)
                    assert got[0] == 2
                return seen

        sink = ActionSink(self.sink, UncoordinatedClient())
        result = sink.action(self.ticket(op="out-of-band-unsafe"))
        self.assertEqual(result["status"], "APPLIED")  # INTENTIONAL NEGATIVE
        self.assertEqual(self.count(), 1)
        self.assertEqual(self.action(self.ticket(op="post-mismatch"))[1]["reason"],
                         "CHECKPOINT_LOCAL_MISMATCH")

    def test_16_invalid_and_boolean_fields_fail_closed(self):
        variants = [self.ticket(seq=True), self.ticket(payload="p") | {"payload_digest": "bad"},
                    self.ticket() | {"op_id": "x/../y"}, self.ticket() | {"extra": "ADMITTED"}]
        for value in variants:
            with self.subTest(value=value):
                code, out = self.action(value)
                self.assertEqual(code, 2)
                self.assertTrue(out["reason"].startswith("INVALID_TICKET"))
        self.assertEqual(self.count(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
