"""R63 V10 defensive synthetic RPC crash-window matrix.

Research-only, stdlib, loopback; SHA-pinned V9 V2 model, no V9 signer/CNG/ACL.
Three forced process exits after distinct journal boundaries. A second *local*
readback process and 2/8/16 TCP retries observe fail-closed handling.

This is NOT independent administrative custody, atomicity, power-loss proof,
or real V9 witness RPC recovery.
"""
from __future__ import annotations
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time

THIS = Path(__file__).resolve()
SIDECAR_DIR = THIS.parent.parent / "r63_v10_source_gate"
sys.path.insert(0, str(SIDECAR_DIR))
import spend_chain_v2 as v2

PIN = "c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd"
N0, ID0 = "a" * 64, "1" * 64
N1, ID1 = "b" * 64, "2" * 64
N2, ID2 = "c" * 64, "3" * 64
REQUEST = b"ARIO_R63_V10_SYNTHETIC_RETRY\n"
PHASES = ("pre_v2", "post_v2", "post_v1")
COUNT_BY_PHASE = {"pre_v2": (2, 2), "post_v2": (2, 3), "post_v1": (3, 3)}
BATCHES = (2, 8, 16)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def pinned():
    if sha((SIDECAR_DIR / "spend_chain_v2.py").read_bytes()) != PIN:
        raise RuntimeError("frozen V9 sidecar SHA256 mismatch")

def durable(path, data, *, append=False):
    with Path(path).open("ab" if append else "xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())

def legacy(rows):
    return b"".join(v2.canonical(p) + b"\n" for p in rows)

def prepare(root):
    durable(root / "SYNTHETIC_ONLY", b"LOCAL_RESEARCH_NO_SIGNER\n")
    rows = [[N0, ID0], [N1, ID1]]
    durable(root / "v1.jsonl", legacy(rows))
    journal = b""
    for n, ident in rows:
        journal, status = v2.append(journal, n, ident)
        if status != "NEW_NEEDS_DURABLE_APPEND":
            raise RuntimeError("init reservation failure")
    durable(root / "v2.jsonl", journal)

def observe(root):
    """Called from a *distinct* Python process, same user and same filesystem."""
    raw1 = (root / "v1.jsonl").read_bytes()
    raw2 = (root / "v2.jsonl").read_bytes()
    state = v2.review(raw2)
    entries = raw1.splitlines(keepends=True)
    if any(not item.endswith(b"\n") for item in entries):
        raise RuntimeError("partial V1 line")
    for item in entries:
        if v2.canonical(json.loads(item)) + b"\n" != item:
            raise RuntimeError("noncanonical V1")
    return {
        "v1_lines": len(entries), "v2_events": state.seq,
        "v1_sha256": sha(raw1), "v2_sha256": sha(raw2),
        "v2_head": state.head,
        "coherent": raw1 == legacy([list(p) for p in state.pairs]),
    }

def publish_port(root, port):
    temp = root / "listen.tmp"
    temp.write_text(str(port), encoding="ascii")
    os.replace(temp, root / "listen.port")

def handler_factory(root, phase):
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            with self.request.makefile("rb") as f:
                msg = f.readline(160)
            if msg != REQUEST:
                self.request.sendall(b"HOLD_INVALID\n")
                return
            if phase == "recovery":
                # No durable/verifiable signed receipt exists in this model.
                # Even coherent V1+V2 is insufficient to assume a prior ACK.
                if not (root / "crashed.marker").is_file():
                    self.request.sendall(b"HOLD_UNCERTAIN\n")
                    return
                try:
                    observe(root)
                except Exception:
                    self.request.sendall(b"HOLD_UNCERTAIN\n")
                    return
                self.request.sendall(b"HOLD_UNCERTAIN\n")
                return
            if phase not in PHASES:
                self.request.sendall(b"HOLD_INVALID_PHASE\n")
                return
            first = v2.review((root / "v2.jsonl").read_bytes())
            if first.seq != 2:
                self.request.sendall(b"HOLD_NOT_FRESH\n")
                return
            if phase != "pre_v2":
                old = (root / "v2.jsonl").read_bytes()
                new, disposition = v2.append(old, N2, ID2)
                if disposition != "NEW_NEEDS_DURABLE_APPEND":
                    self.request.sendall(b"HOLD_BAD_RESERVATION\n")
                    return
                durable(root / "v2.jsonl", new[len(old):], append=True)
            if phase == "post_v1":
                durable(root / "v1.jsonl", legacy([[N2, ID2]]), append=True)
            # A marker is written and fsynced, but it is NOT an external anchor.
            durable(root / "crashed.marker",
                    ("PHASE=" + phase + "\nPID=" + str(os.getpid()) +
                     "\nSYNTHETIC_ONLY\n").encode("ascii"))
            os._exit(73)
    return Handler

class LocalServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = False
    request_queue_size = 64

def run_server(root, phase):
    if not (root / "SYNTHETIC_ONLY").is_file():
        raise RuntimeError("missing synthetic-only marker")
    pinned()
    with LocalServer(("127.0.0.1", 0), handler_factory(root, phase)) as server:
        publish_port(root, server.server_address[1])
        if phase == "recovery":
            for _ in range(sum(BATCHES)):
                server.handle_request()
        else:
            server.handle_request()

def port_wait(root, proc):
    target = root / "listen.port"
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("child exited before ready: " + str(proc.returncode))
        if target.is_file():
            txt = target.read_text(encoding="ascii").strip()
            if txt.isdigit() and 1 <= int(txt) <= 65535:
                return int(txt)
        time.sleep(.03)
    raise RuntimeError("child readiness timeout")

def request(port, *, allowed_reset=False):
    with socket.create_connection(("127.0.0.1", port), timeout=8) as s:
        s.settimeout(8)
        s.sendall(REQUEST)
        # shutdown the write side so a line reader can always finish.
        s.shutdown(socket.SHUT_WR)
        try:
            return s.recv(128)
        except (ConnectionResetError, ConnectionAbortedError) as exc:
            if allowed_reset:
                return b""
            raise RuntimeError("recovery connection reset") from exc

def observer_process(root):
    out = subprocess.check_output([sys.executable, "-I", "-B",
                                   str(THIS), "--observer", str(root)], timeout=12)
    return json.loads(out)

def spawn(root, phase):
    portfile = root / "listen.port"
    if portfile.exists():
        portfile.unlink()
    proc = subprocess.Popen([sys.executable, "-I", "-B", str(THIS),
                             "--server", str(root), phase],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    return proc, port_wait(root, proc)

def matrix_one(phase):
    with tempfile.TemporaryDirectory(prefix="r63_ci_crash_matrix_") as td:
        root = Path(td)
        prepare(root)
        baseline = observer_process(root)
        if (baseline["v1_lines"], baseline["v2_events"]) != (2, 2):
            raise RuntimeError("baseline mismatch")
        first = None
        restart = None
        try:
            first, port = spawn(root, phase)
            reply = request(port, allowed_reset=True)
            if reply != b"":
                raise RuntimeError("crashed RPC unexpectedly acknowledged: " + repr(reply))
            rc = first.wait(timeout=12)
            if rc != 73:
                raise RuntimeError("expected process death 73, got " + str(rc))
            state = observer_process(root)
            expected = COUNT_BY_PHASE[phase]
            if (state["v1_lines"], state["v2_events"]) != expected:
                raise RuntimeError("wrong durable state: " + repr(state))
            marker = (root / "crashed.marker").read_text("ascii")
            if "PHASE=" + phase + "\n" not in marker:
                raise RuntimeError("crash marker missing phase")
            restart, port = spawn(root, "recovery")
            count = 0
            for batch in BATCHES:
                with concurrent.futures.ThreadPoolExecutor(max_workers=batch) as pool:
                    replies = list(pool.map(lambda _: request(port), range(batch)))
                if replies != [b"HOLD_UNCERTAIN\n"] * batch:
                    raise RuntimeError("a retry was acknowledged or dropped: " + repr(replies))
                count += batch
            if restart.wait(timeout=12) != 0:
                raise RuntimeError("recovery server exit not clean")
            reread = observer_process(root)
            if reread != state:
                raise RuntimeError("recovery modified durable journals")
            return {
                "phase": phase, "crash_exit": rc,
                "crash_pid": first.pid, "restart_pid": restart.pid,
                "pid_distinct": first.pid != restart.pid,
                "readback": state, "retry_clients": count,
                "retries_all_hold": True,
                "no_new_journal_write": True,
                "native_signer_not_used": True,
            }
        finally:
            for proc in (first, restart):
                if proc is not None and proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=5)

def main():
    pinned()
    args = sys.argv[1:]
    if len(args) == 3 and args[0] == "--server":
        run_server(Path(args[1]), args[2])
        return
    if len(args) == 2 and args[0] == "--observer":
        print(json.dumps(observe(Path(args[1])), sort_keys=True))
        return
    if len(args) == 2 and args[0] == "--ci" and args[1].endswith(".json"):
        report = {
            "mode": "RESEARCH_ONLY_SYNTHETIC_PROCESS_MATRIX",
            "source_v2_sha256": PIN,
            "production": "NO_GO",
            "trust_activation": "NO_GO",
            "v9_signer": "NOT_EXECUTED",
            "native_ncrypt": "NOT_MEASURED",
            "power_loss": "NOT_TESTED",
            "external_custody": "NOT_ESTABLISHED",
            "windows": [matrix_one(p) for p in PHASES],
        }
        for case in report["windows"]:
            if not case["pid_distinct"]:
                raise RuntimeError("identical process ID across restart")
        Path(args[1]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                                 encoding="utf-8", newline="\n")
        print("PASS: 3 crash windows x 26 same-nonce TCP HOLD retries")
        print("MODEL_ONLY / NATIVE_V9=NOT_EXECUTED / CNG=NOT_MEASURED")
        return
    raise RuntimeError("invalid invocation")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("HOLD: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        sys.exit(1)
