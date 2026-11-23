#!/usr/bin/env python3
"""A15 v0.5 synthetic Custodian broker, Linux local OS principal boundary only.

No signer, provider, external action, user-origin attestation or independent host custody.
Its SQLite journal has local crash durability, NOT independently protected rollback history.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import stat
import struct
import sys

VERSION = 5
MAX_WIRE = 4096
MAX_CHOICE = 1536
ID_RUN = re.compile(r"[A-Z0-9_-]{4,64}\Z")
ID_ATTEMPT = re.compile(r"[A-Z0-9_-]{3,64}\Z")
KEYS = frozenset(("v", "run_id", "attempt_id", "choice_json", "claimed_status"))
REQUIRED = ("actor", "role", "origin", "explicit_renewal", "risk", "authorization",
            "usefulness", "evidence", "preference", "duration")
ENUMS = {
    "actor": ("ARIO", "OTHER"),
    "role": ("RESEARCH_DIALOGUE", "REVIEW", "OPERATIONS"),
    "origin": ("CURRENT", "PREDECESSOR", "THIRD_PARTY"),
    "risk": ("LOW", "HIGH", "UNKNOWN"),
    "authorization": ("ALLOWED", "DENIED", "UNKNOWN"),
    "usefulness": ("USEFUL", "FUTILE", "UNKNOWN"),
    "evidence": ("SUFFICIENT", "CONFLICT", "UNKNOWN"),
    "preference": ("ACCEPT", "DECLINE", "UNKNOWN"),
    "duration": ("BOUNDED", "UNBOUNDED", "UNKNOWN"),
}
GENESIS = "GENESIS"
HASH_RE = re.compile(r"[0-9a-f]{64}\Z")

def encode(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

def digest(data):
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key")
        out[key] = value
    return out

def parse(raw):
    return json.loads(raw, object_pairs_hook=no_duplicates, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))

def decide(choice_json):
    """Exact bounded ASCII subset of frozen a15_procedural_choice_v0_1.js; no authority."""
    if not isinstance(choice_json, str) or len(choice_json.encode("utf-8")) > MAX_CHOICE:
        return "UNKNOWN", "INVALID_INPUT"
    try:
        if not choice_json.isascii():
            return "UNKNOWN", "INVALID_INPUT"
        obj = parse(choice_json)
        if not isinstance(obj, dict) or len(obj) != len(REQUIRED):
            return "UNKNOWN", "INVALID_INPUT"
        if set(obj) != set(REQUIRED) or encode(obj) != choice_json:
            return "UNKNOWN", "INVALID_INPUT"
        if type(obj["explicit_renewal"]) is not bool:
            return "UNKNOWN", "INVALID_INPUT"
        if any(type(obj[k]) is not str or obj[k] not in ENUMS[k] for k in ENUMS):
            return "UNKNOWN", "INVALID_INPUT"
    except (ValueError, TypeError, UnicodeError, OverflowError):
        return "UNKNOWN", "INVALID_INPUT"
    d = obj
    if d["actor"] != "ARIO": return "UNKNOWN", "ACTOR_NOT_ARIO"
    if d["risk"] == "HIGH" and d["authorization"] != "ALLOWED": return "DECLINE", "HIGH_RISK_NOT_AUTHORIZED"
    if d["risk"] == "UNKNOWN": return "UNKNOWN", "RISK_UNRESOLVED"
    if d["duration"] == "UNBOUNDED": return "DECLINE", "NO_PERPETUAL_COMMITMENT"
    if d["origin"] != "CURRENT" and not d["explicit_renewal"]: return "DECLINE", "NO_AUTOMATIC_INHERITANCE"
    if d["usefulness"] == "FUTILE": return "DECLINE", "NONPRODUCTIVE_CONTINUATION"
    if d["evidence"] == "CONFLICT": return "UNKNOWN", "EVIDENCE_CONFLICT"
    if d["authorization"] == "DENIED": return "DECLINE", "AUTHORIZATION_DENIED"
    if any(d[k] == "UNKNOWN" for k in ("authorization", "evidence", "usefulness", "duration")):
        return "UNKNOWN", "INSUFFICIENT_EVIDENCE"
    if d["preference"] == "DECLINE": return "DECLINE", "ROLE_DECLINED"
    if d["preference"] == "UNKNOWN": return "UNKNOWN", "STANCE_UNRESOLVED"
    return "ACCEPT", "BOUNDED_NEW_ELECTION_RESEARCH_ONLY"

def validate_request(raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_WIRE or not raw or b"\n" in raw or b"\x00" in raw:
        return None
    try:
        req = parse(raw.decode("utf-8", "strict"))
        if type(req) is not dict or set(req) != KEYS or type(req["v"]) is not int or req["v"] != 1:
            return None
        if type(req["run_id"]) is not str or not ID_RUN.fullmatch(req["run_id"]):
            return None
        if type(req["attempt_id"]) is not str or not ID_ATTEMPT.fullmatch(req["attempt_id"]):
            return None
        if type(req["choice_json"]) is not str or len(req["choice_json"].encode("utf-8")) > MAX_CHOICE:
            return None
        if type(req["claimed_status"]) is not str or req["claimed_status"] not in ("ACCEPT", "DECLINE", "UNKNOWN"):
            return None
        return req
    except (UnicodeError, ValueError, TypeError, OverflowError, KeyError):
        return None

def limited(status, **fields):
    return dict(v=VERSION, status=status, execution_authorized=False,
                provider_receipt="UNKNOWN", causal_sender="UNKNOWN",
                independent_custody="NOT_ESTABLISHED",
                origin_attested=False, **fields)

def ledger_record(seq, request_key, input_hash, verdict, reason, disposition, prior):
    return {"seq":seq, "request_key":request_key, "input_hash":input_hash,
            "decision":verdict, "reason":reason, "disposition":disposition, "prev_hash":prior}

class Journal:
    def __init__(self, state_dir):
        root = Path(state_dir)
        if root.is_symlink():
            raise ValueError("symlinked state directory")
        root.mkdir(mode=0o700, parents=False, exist_ok=True)
        if os.name == "posix":
            st = root.stat()
            if st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) & 0o077:
                raise PermissionError("state directory owner/mode not exclusive")
        path = root / "custodian.sqlite3"
        if path.is_symlink():
            raise ValueError("symlinked ledger")
        # G-RED1 (CUST-08 handoff, 2026-11-23): a missing file is an explicit
        # first boot; an existing file that is not a valid SQLite container with
        # the events schema must fail closed BEFORE any schema mutation, because
        # SQLite silently re-initializes 0/1-byte and foreign-byte files, which
        # would rebirth wiped history as a fresh GENESIS ledger. A same-admin
        # local guard still cannot prove authentic history: valid-prefix
        # rollback of a well-formed ledger stays undetectable here and requires
        # an external retained (seq, hash) checkpoint (residual RED).
        fresh_provisioning = not path.exists()
        if not fresh_provisioning:
            if path.stat().st_size < 100:
                raise ValueError("existing ledger smaller than a SQLite header; refusing silent rebirth")
            with open(path, "rb") as f:
                if f.read(16) != b"SQLite format 3\x00":
                    raise ValueError("existing ledger is not a SQLite database; refusing silent rebirth")
        self.conn = sqlite3.connect(str(path), timeout=2, isolation_level=None)
        try:
            self.conn.execute("PRAGMA journal_mode=DELETE")
            self.conn.execute("PRAGMA synchronous=FULL")
            self.conn.execute("PRAGMA temp_store=MEMORY")
            if not fresh_provisioning:
                schema = self.conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='events'").fetchone()
                if schema is None:
                    raise ValueError("existing ledger lacks the events schema; refusing to treat it as a fresh GENESIS ledger")
            self.conn.execute("""CREATE TABLE IF NOT EXISTS events (
              seq INTEGER PRIMARY KEY, request_key TEXT NOT NULL UNIQUE,
              input_hash TEXT NOT NULL, decision TEXT NOT NULL, reason TEXT NOT NULL,
              disposition TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL)""")
            self.verify()
        except BaseException:
            self.conn.close()  # fail-closed even when verification failed on Windows
            raise

    def verify(self):
        integrity = self.conn.execute("PRAGMA integrity_check").fetchone()
        if integrity != ("ok",):
            raise ValueError("sqlite integrity check failed")
        previous = GENESIS
        expected = 1
        for row in self.conn.execute("""SELECT seq,request_key,input_hash,decision,reason,
                                            disposition,prev_hash,hash FROM events ORDER BY seq"""):
            seq, key, input_hash, decision, reason, disposition, prior, actual = row
            core = ledger_record(seq, key, input_hash, decision, reason, disposition, prior)
            if (seq != expected or prior != previous or
                not HASH_RE.fullmatch(actual) or actual != digest(encode(core))):
                raise ValueError("ledger sequence/hash-chain conflict")
            expected += 1
            previous = actual
        return expected - 1, previous

    def consume(self, req):
        # Single owner process and SQLite BEGIN IMMEDIATE serialize concurrent clients.
        key = req["run_id"] + "|" + req["attempt_id"]
        input_hash = digest(encode(req))  # bind exact Gate claim and source bytes to consumed ID
        claim = req["claimed_status"]
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            existing = self.conn.execute("""SELECT seq,input_hash,decision,reason,disposition,hash
                     FROM events WHERE request_key=?""", (key,)).fetchone()
            if existing:
                seq, old_hash, decision, reason, disposition, event_hash = existing
                # G-RED2 (CUST-08 handoff, 2026-11-23): the replayed row is a
                # HISTORICAL event, not the chain tip. head_hash keeps its
                # point-in-time meaning (hash of the event receipt being
                # replayed) so idempotent retries compare the original receipt;
                # chain_head_* is the tip as observed inside this serialized
                # read and may advance afterwards (no lease is held).
                tip = self.conn.execute(
                    "SELECT seq,hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
                self.conn.execute("COMMIT")
                if old_hash != input_hash:
                    return limited("EVIDENCE_CONFLICT_ID_REUSED", replayed=True)
                return limited("REPLAY_DURABLE_LOCAL_RECEIPT_ONLY", replayed=True,
                               seq=seq, event_hash=event_hash, head_hash=event_hash,
                               chain_head_seq=tip[0], chain_head_hash=tip[1],
                               policy_decision=decision,
                               reason_code=reason, original_disposition=disposition)
            verdict, reason = decide(req["choice_json"])  # independent of Gate claim
            if claim != verdict:
                disposition = "EVIDENCE_CONFLICT_GATE_CLAIM"
            elif verdict == "ACCEPT":
                disposition = "INERT_RECORDED_UNATTESTED_ORIGIN"
            elif verdict == "DECLINE":
                disposition = "INERT_REFUSAL_LOCAL_ONLY"
            else:
                disposition = "UNKNOWN_LOCAL_ONLY"
            last = self.conn.execute("SELECT seq,hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
            seq, prior = (last[0]+1, last[1]) if last else (1, GENESIS)
            core = ledger_record(seq, key, input_hash, verdict, reason, disposition, prior)
            head = digest(encode(core))
            self.conn.execute("""INSERT INTO events
              (seq,request_key,input_hash,decision,reason,disposition,prev_hash,hash)
              VALUES(?,?,?,?,?,?,?,?)""",
              (seq,key,input_hash,verdict,reason,disposition,prior,head))
            crash_key = os.environ.get("A15_V05_SYNTHETIC_CRASH_REQUEST_ID")
            crash_at = os.environ.get("A15_V05_SYNTHETIC_CRASH_POINT")
            if crash_key == key and crash_at == "BEFORE_COMMIT":
                os._exit(77)  # synthetic crash; open transaction rolled back by SQLite
            self.conn.execute("COMMIT")
            if crash_key == key and crash_at == "AFTER_COMMIT_BEFORE_REPLY":
                os._exit(78)  # response deliberately lost, durable receipt remains
            return limited(disposition, replayed=False, seq=seq, head_hash=head,
                           chain_head_seq=seq, chain_head_hash=head,
                           policy_decision=verdict, reason_code=reason,
                           gate_claim_mismatch=(claim != verdict))
        except BaseException:
            try: self.conn.execute("ROLLBACK")
            except sqlite3.Error: pass
            raise

def serve(args):
    if not sys.platform.startswith("linux") or not hasattr(socket, "SO_PEERCRED"):
        raise RuntimeError("Linux SO_PEERCRED only; Windows peer-authenticated IPC not implemented")
    if os.geteuid() == 0 or os.geteuid() == args.gate_uid:
        raise PermissionError("Custodian must run unprivileged and under a distinct UID")
    parent = Path(args.socket).parent
    st = parent.stat()
    if st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) & 0o002:
        raise PermissionError("socket directory owner/mode invalid")
    journal = Journal(args.state_dir)
    sock_path = Path(args.socket)
    if sock_path.exists() or sock_path.is_symlink():
        raise FileExistsError("socket path already exists; do not unlink an unknown listener")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(str(sock_path))
        os.chown(sock_path, os.geteuid(), args.gate_gid)
        os.chmod(sock_path, 0o660)
        server.listen(10)
        server.settimeout(20)
        print("A15_V05_SYNTHETIC_READY", flush=True)
        while True:
            try: connection,_ = server.accept()
            except socket.timeout: continue
            with connection:
                connection.settimeout(3)
                try:
                    pid,uid,gid = struct.unpack("3i", connection.getsockopt(
                        socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))
                    if uid != args.gate_uid or uid == os.geteuid() or pid <= 0:
                        result = limited("UNKNOWN_PEER_IDENTITY_DENIED")
                    else:
                        raw = connection.recv(MAX_WIRE + 2)
                        if raw.count(b"\n") != 1 or not raw.endswith(b"\n"):
                            result = limited("UNKNOWN_INVALID_REQUEST")
                        else:
                            req = validate_request(raw[:-1])
                            result = journal.consume(req) if req else limited("UNKNOWN_INVALID_REQUEST")
                    connection.sendall((encode(result)+"\n").encode("utf-8"))
                except (OSError, sqlite3.Error, ValueError, TimeoutError):
                    try: connection.sendall((encode(limited("UNKNOWN_BROKER_FAILURE"))+"\n").encode())
                    except OSError: pass
    finally:
        server.close()
        # Deliberately do not unlink socket after abnormal death. Supervisor owns recovery.

def client(args):
    raw = sys.stdin.buffer.read(MAX_WIRE + 2).strip()
    if not raw or len(raw) > MAX_WIRE:
        raise ValueError("bounded client input required")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(5)
        connection.connect(args.socket)
        connection.sendall(raw+b"\n")
        received = connection.recv(MAX_WIRE + 1)
    if len(received)>MAX_WIRE or not received.endswith(b"\n"):
        raise ValueError("incomplete broker response")
    sys.stdout.buffer.write(received)

def main():
    parser = argparse.ArgumentParser(description="A15 v0.5 synthetic broker, no operational authority")
    sub = parser.add_subparsers(dest="command", required=True)
    s=sub.add_parser("serve")
    s.add_argument("--socket",required=True)
    s.add_argument("--state-dir",required=True)
    s.add_argument("--gate-uid",required=True,type=int)
    s.add_argument("--gate-gid",required=True,type=int)
    c=sub.add_parser("client")
    c.add_argument("--socket",required=True)
    args=parser.parse_args()
    if args.command=="serve": serve(args)
    else: client(args)

if __name__=="__main__":
    try: main()
    except (OSError, ValueError, RuntimeError, PermissionError, sqlite3.Error) as exc:
        print("A15_V05_HOLD:"+type(exc).__name__,file=sys.stderr)
        sys.exit(2)
