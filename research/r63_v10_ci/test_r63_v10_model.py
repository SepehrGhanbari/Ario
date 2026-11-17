"""R63 V10 synthetic journal/RPC CI fixtures. NO signer, CNG, service, or trust.

This is a *model contract* based on reported V9 spend sidecar semantics, not a
copy of frozen native V9 code. Never interpret this suite as native R63 PASS.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import unittest

DOMAIN = b"ARIO-R63/spend/v2\0"
VERSION = "ARIO_R63_SPEND_V2_RESEARCH"
ZERO = "0" * 64
HEX = re.compile(r"[0-9a-f]{64}\Z")
CAP = 2 * 1024 * 1024

class Hold(ValueError):
    pass

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")

def h(data):
    return hashlib.sha256(data).hexdigest()

def valid_hash(x):
    return type(x) is str and HEX.fullmatch(x) is not None

def content_digest(pairs):
    return h(canonical(sorted(pairs, key=lambda x: x[0])))

def read_bounded(path):
    try:
        with Path(path).open("rb") as fd:
            raw = fd.read(CAP + 1)
    except OSError as exc:
        raise Hold("missing or unreadable journal") from exc
    if len(raw) > CAP:
        raise Hold("journal above cap")
    return raw

def v1_parse(raw):
    if raw and not raw.endswith(b"\n"):
        raise Hold("partial V1 record")
    lines = raw[:-1].split(b"\n") if raw else []
    if len(lines) > 100000:
        raise Hold("too many rows")
    rows = []
    for line in lines:
        if not line or len(line) > 8192:
            raise Hold("invalid row length")
        try:
            pair = json.loads(line.decode("ascii"))
            if (type(pair) is not list or len(pair) != 2
                    or not all(valid_hash(x) for x in pair)
                    or canonical(pair) != line):
                raise Hold("noncanonical V1 pair")
        except (ValueError, UnicodeError, TypeError) as exc:
            raise Hold("invalid V1") from exc
        if any(pair[0] == p[0] or pair[1] == p[1] for p in rows):
            raise Hold("duplicate V1 nonce or identifier")
        rows.append(pair)
    return rows

def v2_review(raw, anchor=None):
    if raw and not raw.endswith(b"\n"):
        raise Hold("partial V2 record")
    lines = raw[:-1].split(b"\n") if raw else []
    if len(lines) > 100000:
        raise Hold("too many V2 rows")
    head = ZERO
    pairs = []
    seen_anchor = anchor == (0, ZERO)
    for seq, line in enumerate(lines, 1):
        if not line or len(line) > 8192:
            raise Hold("invalid V2 row length")
        try:
            obj = json.loads(line.decode("ascii"))
            if type(obj) is not dict or canonical(obj) != line:
                raise Hold("noncanonical V2 record")
        except (ValueError, UnicodeError, TypeError) as exc:
            raise Hold("invalid V2") from exc
        if set(obj) != {"version", "seq", "prev", "nonce", "id", "before", "after", "hash"}:
            raise Hold("unexpected V2 fields")
        n, ident = obj["nonce"], obj["id"]
        if (obj["version"] != VERSION or type(obj["seq"]) is not int
                or obj["seq"] != seq or obj["prev"] != head
                or not valid_hash(n) or not valid_hash(ident)
                or any(n == p[0] or ident == p[1] for p in pairs)):
            raise Hold("V2 predecessor, nonce or id invalid")
        new_pairs = pairs + [[n, ident]]
        body = {k: v for k, v in obj.items() if k != "hash"}
        if (obj["before"] != content_digest(pairs)
                or obj["after"] != content_digest(new_pairs)
                or obj["hash"] != h(DOMAIN + canonical(body))):
            raise Hold("V2 content or event digest mismatch")
        head = obj["hash"]
        pairs = new_pairs
        if anchor is not None and seq == anchor[0]:
            if head != anchor[1]:
                raise Hold("anchor fork")
            seen_anchor = True
    if anchor is not None and not seen_anchor:
        raise Hold("anchor prefix missing")
    return len(pairs), head, pairs

def append_v2(raw, nonce, ident):
    seq, head, pairs = v2_review(raw)
    if not valid_hash(nonce) or not valid_hash(ident):
        raise Hold("invalid new nonce or identifier")
    if any(nonce == p[0] or ident == p[1] for p in pairs):
        raise Hold("duplicate reservation")
    body = dict(version=VERSION, seq=seq + 1, prev=head,
                nonce=nonce, id=ident, before=content_digest(pairs),
                after=content_digest(pairs + [[nonce, ident]]))
    return raw + canonical({**body, "hash": h(DOMAIN + canonical(body))}) + b"\n"

def require_agreement(v1, v2, memory, before, hook=None):
    """Read-only model, final re-read detects some drift but is NOT atomic."""
    first_v1, first_v2 = read_bounded(v1), read_bounded(v2)
    if hook:
        hook()
    left = v1_parse(first_v1)
    seq, head, right = v2_review(first_v2)
    if type(memory) is not list or left != right or left != memory:
        raise Hold("V1 / V2 / RAM diverged")
    if not valid_hash(before) or before != content_digest(left):
        raise Hold("R60 sorted content mismatch")
    if read_bounded(v1) != first_v1 or read_bounded(v2) != first_v2:
        raise Hold("concurrent journal change detected")
    return seq, head

def v1_bytes(pairs):
    return b"".join(canonical(pair) + b"\n" for pair in pairs)

# Isolated TCP RPC parent model: one request then fsynced V2 write and abrupt exit.
# This does NOT use a real witness, broker or CNG signer.
def rpc_crash_fixture(root):
    root = Path(root)
    if not (root / "R63_CI_SYNTHETIC_ONLY").is_file():
        return 92
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            msg = self.request.recv(64)
            if msg != b"synthetic-spend":
                os._exit(91)
            f = root / "v2.jsonl"
            old = read_bounded(f)
            updated = append_v2(old, "a" * 64, "b" * 64)
            with f.open("ab") as stream:
                stream.write(updated[len(old):])
                stream.flush()
                os.fsync(stream.fileno())
            os._exit(73)  # Process death before V1 append / RPC ACK.
    with socketserver.TCPServer(("127.0.0.1", 0), Handler) as server:
        (root / "port").write_text(str(server.server_address[1]), encoding="ascii")
        server.handle_request()
    return 90

class ModelTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix="r63-github-ci-")
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.v1, self.v2 = self.root / "v1.jsonl", self.root / "v2.jsonl"
        self.pairs = [["e" * 64, "1" * 64], ["1" * 64, "2" * 64]]
        self.save(self.pairs)

    def save(self, pairs):
        self.v1.write_bytes(v1_bytes(pairs))
        journal = b""
        for n, ident in pairs:
            journal = append_v2(journal, n, ident)
        self.v2.write_bytes(journal)

    def verify(self, hook=None):
        return require_agreement(self.v1, self.v2, self.pairs,
                                 content_digest(self.pairs), hook)

    def test_clean_and_append_order_distinct_from_content(self):
        self.assertEqual(self.verify()[0], 2)
        self.assertEqual(content_digest(self.pairs), content_digest(list(reversed(self.pairs))))
        other = b""
        for n, ident in reversed(self.pairs):
            other = append_v2(other, n, ident)
        self.assertNotEqual(v2_review(other)[1], self.verify()[1])

    def test_empty_state_has_no_nonrollback_proof(self):
        self.pairs = []
        self.save([])
        self.assertEqual(self.verify()[0], 0)

    def test_corrupt_and_diverged_v1(self):
        original = self.v1.read_bytes()
        for bad in [b"", b"missing-newline", original[:-1], original.replace(b",", b", ", 1),
                    original + original[:original.index(b"\n") + 1],
                    v1_bytes([["7" * 64, "3" * 64]])]:
            self.v1.write_bytes(bad)
            with self.assertRaises(Hold):
                self.verify()
        self.v1.write_bytes(original)
        self.assertEqual(self.verify()[0], 2)

    def test_corrupt_and_diverged_v2(self):
        original = self.v2.read_bytes()
        for bad in [b"", original[:-1], original.replace(b'"prev":"', b'"prev":"f', 1),
                    append_v2(original, "7" * 64, "3" * 64)]:
            self.v2.write_bytes(bad)
            with self.assertRaises(Hold):
                self.verify()

    def test_missing_journals(self):
        self.v1.unlink()
        with self.assertRaises(Hold):
            self.verify()
        self.save(self.pairs)
        self.v2.unlink()
        with self.assertRaises(Hold):
            self.verify()

    def test_stale_memory_and_broker_digest(self):
        with self.assertRaises(Hold):
            require_agreement(self.v1, self.v2, list(reversed(self.pairs)), content_digest(self.pairs))
        with self.assertRaises(Hold):
            require_agreement(self.v1, self.v2, self.pairs, "f" * 64)

    def test_drift_during_validation(self):
        with self.assertRaises(Hold):
            self.verify(hook=lambda: self.v1.unlink())

    def test_change_after_final_check_still_unsafe(self):
        self.verify()
        self.v1.unlink()
        self.assertFalse(self.v1.exists())  # Expected negative control, not security PASS.

    def test_full_local_rollback_not_detected(self):
        old_v1, old_v2 = self.v1.read_bytes(), self.v2.read_bytes()
        new = self.pairs + [["7" * 64, "3" * 64]]
        self.save(new)
        anchor = v2_review(self.v2.read_bytes())[:2]
        self.v1.write_bytes(old_v1)
        self.v2.write_bytes(old_v2)
        self.assertEqual(self.verify()[0], 2)  # Expected rollback failure.
        with self.assertRaises(Hold):
            v2_review(self.v2.read_bytes(), anchor=anchor)

    def test_rpc_process_abrupt_exit_after_v2_fsync(self):
        # Actual subprocess exit is observed; it is a synthetic TCP RPC parent.
        self.pairs = [["e" * 64, "1" * 64], ["1" * 64, "2" * 64]]
        (self.root / "R63_CI_SYNTHETIC_ONLY").write_text("yes")
        child = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()),
                                  "--rpc-crash", str(self.root)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 10
            while not (self.root / "port").exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(.025)
            self.assertTrue((self.root / "port").exists(), "synthetic RPC did not bind")
            port = int((self.root / "port").read_text())
            with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
                client.sendall(b"synthetic-spend")
                client.settimeout(5)
                reply = client.recv(64)
            self.assertEqual(reply, b"")
            self.assertEqual(child.wait(timeout=10), 73)
            self.assertEqual(v2_review(self.v2.read_bytes())[0], 3)
            self.assertEqual(len(v1_parse(self.v1.read_bytes())), 2)
            with self.assertRaises(Hold):
                self.verify()
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
            if child.stderr is not None:
                child.stderr.close()

    def test_concurrent_socket_clients_model_only(self):
        # Real TCP clients, but the only counter is Python memory; NO crypto.
        for clients in (2, 8, 16):
            count = [0]
            lock = threading.Lock()
            class Handler(socketserver.BaseRequestHandler):
                def handle(self):
                    nonce = self.request.recv(128)
                    with lock:
                        if nonce == b"same-fixture-nonce" and count[0] == 0:
                            count[0] += 1
                            response = b"NEW"
                        else:
                            response = b"REPLAY"
                    self.request.sendall(response)
            class Server(socketserver.ThreadingTCPServer):
                allow_reuse_address = True
                daemon_threads = True
            with Server(("127.0.0.1", 0), Handler) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                outputs = []
                def run_one():
                    with socket.create_connection(server.server_address, timeout=8) as s:
                        s.sendall(b"same-fixture-nonce")
                        s.settimeout(8)
                        return s.recv(128)
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=clients) as pool:
                    outputs = list(pool.map(lambda _: run_one(), range(clients)))
                server.shutdown()
                thread.join(timeout=5)
                self.assertEqual(count[0], 1)
                self.assertEqual(outputs.count(b"NEW"), 1)
                self.assertEqual(outputs.count(b"REPLAY"), clients - 1)

if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--rpc-crash":
    sys.exit(rpc_crash_fixture(sys.argv[2]))
elif __name__ == "__main__":
    unittest.main(verbosity=2)
