#!/usr/bin/env python3
"""R9-B proposed safety boundary: disposable SQLite effect sink + observer reservation.

Not a real independent witness, signer, production authority, or proof of external
exactly-once semantics. A single test administrator controls all processes/keys.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import socket
import sqlite3
import sys
from typing import Any

FORMAT = "ario-r9b-lab-v01"
GENESIS = "R9B-DISPOSABLE-GENESIS"
SCOPE = "disposable:research-view"
MAX_MESSAGE = 16000
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
ID = re.compile(r"[a-zA-Z0-9_.-]{1,80}\Z")


class Hold(Exception):
    """Conservatively deny an operation; no inference of factual truth."""


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True,
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(*parts: Any) -> str:
    return hashlib.sha256(canonical(parts)).hexdigest()


def sign(key: bytes, obj: dict) -> str:
    return hmac.new(key, canonical(obj), hashlib.sha256).hexdigest()


def valid_hash(value: Any) -> bool:
    return isinstance(value, str) and bool(HEX64.fullmatch(value))


@contextmanager
def database(path: Path):
    conn = sqlite3.connect(str(path), isolation_level=None, timeout=12.0)
    try:
        conn.execute("PRAGMA busy_timeout=12000")
        conn.execute("PRAGMA synchronous=FULL")
        yield conn
        if conn.in_transaction:
            raise RuntimeError("UNCOMMITTED_TRANSACTION")
    except BaseException:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def _receive(sock: socket.socket) -> dict:
    data = b""
    while b"\n" not in data:
        chunk = sock.recv(2048)
        if not chunk:
            raise Hold("MISSING_LINE_TERMINATOR")
        data += chunk
        if len(data) > MAX_MESSAGE:
            raise Hold("MESSAGE_TOO_LARGE")
    one, trailing = data.split(b"\n", 1)
    if trailing.strip():
        raise Hold("EXTRA_MESSAGE_BYTES")
    obj = json.loads(one.decode("utf-8"))
    if not isinstance(obj, dict):
        raise Hold("NOT_AN_OBJECT")
    return obj


class ObserverServer:
    """Separate process; SQLite head + reservations under *same observer lock*.

    Observer only authenticates HMAC possession; key and disk remain under the
    same test administrator. Direct CAS is allowed for race tests but cannot
    pass while an effect reservation is pending.
    """

    def __init__(self, db_file: Path, sock_file: Path, key_file: Path):
        self.db_file, self.sock_file = db_file, sock_file
        self.key = key_file.read_bytes()
        if len(self.key) != 32:
            raise Hold("INVALID_EPHEMERAL_KEY")
        with database(db_file) as db:
            db.execute("CREATE TABLE IF NOT EXISTS head(seq INTEGER PRIMARY KEY, hash TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS reservations(op_id TEXT PRIMARY KEY, seq INTEGER NOT NULL, head_hash TEXT NOT NULL, fingerprint TEXT NOT NULL, status TEXT NOT NULL, receipt TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS nonces(nonce TEXT PRIMARY KEY)")
            if not db.execute("SELECT seq FROM head").fetchone():
                db.execute("INSERT INTO head(seq,hash) VALUES (0,?)", (GENESIS,))

    def process(self, request: dict) -> dict:
        if set(request) != {"body", "mac"} or not isinstance(request["body"], dict):
            raise Hold("INVALID_ENVELOPE")
        body = request["body"]
        if not isinstance(request["mac"], str) or not hmac.compare_digest(sign(self.key, body), request["mac"]):
            raise Hold("BAD_AUTHENTICATION")
        if body.get("format") != FORMAT or not isinstance(body.get("nonce"), str) or not re.fullmatch(r"[0-9a-f]{32}", body["nonce"]):
            raise Hold("INVALID_PROTOCOL_OR_NONCE")
        op = body.get("op")
        fields = {
            "HEAD": {"format", "nonce", "op"},
            "CAS": {"format", "nonce", "op", "seq", "head_hash", "next_hash"},
            "RESERVE": {"format", "nonce", "op", "seq", "head_hash", "op_id", "fingerprint"},
            "FINALIZE": {"format", "nonce", "op", "op_id", "fingerprint", "receipt"},
        }
        if op not in fields or set(body) != fields[op]:
            raise Hold("INVALID_FIELDS")
        with database(self.db_file) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute("INSERT INTO nonces VALUES (?)", (body["nonce"],))
            except sqlite3.IntegrityError as exc:
                raise Hold("REPLAYED_NONCE") from exc
            head = db.execute("SELECT seq,hash FROM head ORDER BY seq DESC LIMIT 1").fetchone()
            pending = db.execute("SELECT COUNT(*) FROM reservations WHERE status='PREPARED'").fetchone()[0]
            if op == "HEAD":
                result = {"seq": head[0], "head_hash": head[1], "pending": pending}
            elif op == "CAS":
                if (type(body["seq"]) is not int or body["seq"] < 0 or not isinstance(body["head_hash"], str)
                        or not valid_hash(body["next_hash"])):
                    raise Hold("BAD_CAS_FIELDS")
                if pending:
                    raise Hold("PENDING_EFFECT_FENCE")
                if (body["seq"], body["head_hash"]) != head:
                    raise Hold("CAS_HEAD_MISMATCH")
                db.execute("INSERT INTO head(seq,hash) VALUES (?,?)", (head[0]+1, body["next_hash"]))
                result = {"seq": head[0]+1, "head_hash": body["next_hash"]}
            elif op == "RESERVE":
                if (type(body["seq"]) is not int or body["seq"] < 1 or not isinstance(body["head_hash"], str)
                        or not isinstance(body["op_id"], str) or not ID.fullmatch(body["op_id"])
                        or not valid_hash(body["fingerprint"])):
                    raise Hold("BAD_RESERVE_FIELDS")
                if pending:
                    raise Hold("PENDING_EFFECT_FENCE")
                if (body["seq"], body["head_hash"]) != head:
                    raise Hold("STALE_OBSERVER_HEAD")
                if db.execute("SELECT 1 FROM reservations WHERE op_id=?", (body["op_id"],)).fetchone():
                    raise Hold("OP_ALREADY_RESERVED")
                db.execute("INSERT INTO reservations VALUES (?,?,?,?,?,NULL)",
                           (body["op_id"], body["seq"], body["head_hash"], body["fingerprint"], "PREPARED"))
                result = {"reserved": body["op_id"]}
            else:  # FINALIZE; cannot cancel without independently justified recovery
                if (not isinstance(body["op_id"], str) or not ID.fullmatch(body["op_id"])
                        or not valid_hash(body["fingerprint"]) or not valid_hash(body["receipt"])):
                    raise Hold("BAD_FINALIZE_FIELDS")
                record = db.execute("SELECT fingerprint,status,receipt FROM reservations WHERE op_id=?", (body["op_id"],)).fetchone()
                if not record or record[0] != body["fingerprint"] or record[1] != "PREPARED":
                    raise Hold("NO_MATCHING_PENDING_RESERVATION")
                # The observer does not validate actual external side effects.
                db.execute("UPDATE reservations SET status='COMPLETE',receipt=? WHERE op_id=?", (body["receipt"], body["op_id"]))
                result = {"completed": body["op_id"]}
            db.execute("COMMIT")
            return result

    def serve(self):
        if self.sock_file.exists():
            raise Hold("SOCKET_PATH_ALREADY_EXISTS")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(self.sock_file))
            os.chmod(self.sock_file, 0o600)
            server.listen(32)
            server.settimeout(0.5)
            while True:
                try:
                    conn, _ = server.accept()
                except socket.timeout:
                    continue
                with conn:
                    conn.settimeout(4.0)
                    request = None
                    try:
                        request = _receive(conn)
                        value = {"ok": True, "result": self.process(request)}
                    except (Hold, ValueError, TypeError, UnicodeError, sqlite3.DatabaseError) as exc:
                        value = {"ok": False, "reason": str(exc) if isinstance(exc, Hold) else "INVALID_OR_CORRUPT_REQUEST"}
                    nonce = (request.get("body", {}).get("nonce") if isinstance(request, dict)
                             and isinstance(request.get("body"), dict) else None)
                    signed = {"nonce": nonce, "value": value}
                    try:
                        conn.sendall(canonical({"body": signed, "mac": sign(self.key, signed)}) + b"\n")
                    except OSError:
                        pass


class ObserverClient:
    def __init__(self, sock: Path, key_file: Path):
        self.sock = sock
        self.key = key_file.read_bytes()
        if len(self.key) != 32:
            raise Hold("INVALID_TEST_KEY")

    def call(self, op: str, **fields):
        nonce = secrets.token_hex(16)
        body = {"format": FORMAT, "nonce": nonce, "op": op, **fields}
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
                conn.settimeout(3.0)
                conn.connect(str(self.sock))
                conn.sendall(canonical({"body": body, "mac": sign(self.key, body)}) + b"\n")
                response = _receive(conn)
        except (OSError, TimeoutError) as exc:
            raise Hold("OBSERVER_UNREACHABLE") from exc
        try:
            signed = response["body"]
            if (not isinstance(signed, dict) or signed.get("nonce") != nonce
                    or not hmac.compare_digest(response["mac"], sign(self.key, signed))):
                raise Hold("OBSERVER_RESPONSE_AUTH_FAILED")
            value = signed["value"]
            if value.get("ok") is not True:
                reason = value.get("reason", "REJECTED")
                if not isinstance(reason, str):
                    raise Hold("MALFORMED_OBSERVER_RESPONSE")
                raise Hold("OBSERVER_" + reason)
            result = value["result"]
            if not isinstance(result, dict):
                raise Hold("INVALID_OBSERVER_RESULT")
            return result
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise Hold("MALFORMED_OBSERVER_RESPONSE") from exc


class ConditionalSink:
    """Only local disposable RESEARCH_VIEW effect; no external action adapter."""

    def __init__(self, path: Path, observer: ObserverClient):
        self.path, self.observer = path, observer
        with database(path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS current(seq INTEGER NOT NULL, head_hash TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS effects(op_id TEXT PRIMARY KEY,seq INTEGER,head_hash TEXT,fingerprint TEXT,receipt TEXT)")
            if not db.execute("SELECT 1 FROM current").fetchone():
                db.execute("INSERT INTO current VALUES (?,?)", (0, GENESIS))

    def checked(self, db, require_no_pending=True):
        local = db.execute("SELECT seq,head_hash FROM current").fetchall()
        if len(local) != 1:
            raise Hold("CORRUPT_LOCAL_HEAD")
        remote = self.observer.call("HEAD")
        if (type(remote.get("seq")) is not int or not isinstance(remote.get("head_hash"), str)
                or type(remote.get("pending")) is not int or remote["pending"] < 0):
            raise Hold("MALFORMED_OBSERVER_HEAD")
        if tuple(local[0]) != (remote["seq"], remote["head_hash"]):
            raise Hold("LOCAL_OBSERVER_MISMATCH")
        if require_no_pending and remote["pending"]:
            raise Hold("PENDING_RECONCILIATION_REQUIRED")
        return tuple(local[0])

    def advance(self, commitment: str, crash_after_observer=False):
        if not valid_hash(commitment):
            raise Hold("BAD_COMMITMENT")
        with database(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            seq, old = self.checked(db)
            new = digest("R9B-EPOCH", seq + 1, old, commitment)
            remote = self.observer.call("CAS", seq=seq, head_hash=old, next_hash=new)
            if remote != {"seq": seq+1, "head_hash": new}:
                raise Hold("CAS_UNEXPECTED_RESULT")
            if crash_after_observer:
                os._exit(77)
            db.execute("UPDATE current SET seq=?,head_hash=?", (seq+1, new))
            db.execute("COMMIT")
            return {"status": "ADVANCED", "seq": seq+1, "head_hash": new}

    def apply(self, ticket: dict, crash_after_reserve=False, crash_after_local=False):
        if not isinstance(ticket, dict) or set(ticket) != {"seq", "head_hash", "op_id", "payload_hash", "use", "scope"}:
            raise Hold("BAD_TICKET_SHAPE")
        if ticket["use"] != "RESEARCH_VIEW" or ticket["scope"] != SCOPE:
            raise Hold("NO_EVIDENCE_OR_EXTERNAL_AUTHORITY")
        if (type(ticket["seq"]) is not int or ticket["seq"] < 1
                or not valid_hash(ticket["head_hash"]) or not valid_hash(ticket["payload_hash"])
                or not isinstance(ticket["op_id"], str) or not ID.fullmatch(ticket["op_id"])):
            raise Hold("BAD_TICKET_FIELDS")
        fingerprint = digest("R9B-INTENT", ticket)
        with database(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            seq, head_hash = self.checked(db)
            if (ticket["seq"], ticket["head_hash"]) != (seq, head_hash):
                raise Hold("STALE_AT_SINK")
            prev = db.execute("SELECT fingerprint,receipt FROM effects WHERE op_id=?", (ticket["op_id"],)).fetchone()
            if prev:
                if prev[0] != fingerprint:
                    raise Hold("OP_ID_PAYLOAD_CONFLICT")
                db.execute("COMMIT")
                return {"status": "DUPLICATE_NO_EFFECT", "receipt": prev[1]}
            # Observer reserve is a durable fence on *all API-level epoch CAS*.
            # An externally submitted CAS between HEAD and RESERVE fails RESERVE.
            self.observer.call("RESERVE", seq=seq, head_hash=head_hash,
                               op_id=ticket["op_id"], fingerprint=fingerprint)
            if crash_after_reserve:
                os._exit(77)
            receipt = digest("R9B-LOCAL-EFFECT", ticket["op_id"], fingerprint)
            db.execute("INSERT INTO effects VALUES (?,?,?,?,?)",
                       (ticket["op_id"], seq, head_hash, fingerprint, receipt))
            db.execute("COMMIT")
        if crash_after_local:
            os._exit(78)
        try:
            self.observer.call("FINALIZE", op_id=ticket["op_id"],
                               fingerprint=fingerprint, receipt=receipt)
        except Hold as exc:
            # Local row may exist. Never claim a finalized/e2e effect.
            return {"status": "HOLD_UNCERTAIN_LOCAL_EFFECT", "reason": str(exc)}
        return {"status": "APPLIED_LOCAL_ONLY", "receipt": receipt}

    def count(self):
        with database(self.path) as db:
            return db.execute("SELECT COUNT(*) FROM effects").fetchone()[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description="R9-B bounded two-process observer/sink research")
    parser.add_argument("command", choices=("observer", "head", "advance", "apply", "count", "observer-cas"))
    parser.add_argument("--sink-db", type=Path)
    parser.add_argument("--observer-db", type=Path)
    parser.add_argument("--socket", required=True, type=Path)
    parser.add_argument("--key", required=True, type=Path)
    parser.add_argument("--commitment", default="")
    parser.add_argument("--ticket-json", default="")
    parser.add_argument("--expect-seq", type=int)
    parser.add_argument("--expect-hash", default="")
    parser.add_argument("--crash-after-observer", action="store_true")
    parser.add_argument("--crash-after-reserve", action="store_true")
    parser.add_argument("--crash-after-local", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "observer":
            if args.observer_db is None:
                raise Hold("OBSERVER_DB_REQUIRED")
            ObserverServer(args.observer_db, args.socket, args.key).serve()
            return 0
        client = ObserverClient(args.socket, args.key)
        if args.command == "observer-cas":  # intentionally privileged/direct for adversarial controls
            result = client.call("CAS", seq=args.expect_seq, head_hash=args.expect_hash,
                                 next_hash=args.commitment)
        elif args.command == "head":
            result = client.call("HEAD")
        else:
            if args.sink_db is None:
                raise Hold("SINK_DB_REQUIRED")
            sink = ConditionalSink(args.sink_db, client)
            if args.command == "advance":
                result = sink.advance(args.commitment, args.crash_after_observer)
            elif args.command == "apply":
                result = sink.apply(json.loads(args.ticket_json), args.crash_after_reserve,
                                    args.crash_after_local)
            else:
                result = {"status": "READ_ONLY", "count": sink.count()}
        print(json.dumps(result, sort_keys=True), flush=True)
        return 0
    except (Hold, ValueError, TypeError, sqlite3.DatabaseError) as exc:
        print(json.dumps({"status": "HOLD", "reason": str(exc) if isinstance(exc, Hold)
                          else "BAD_INPUT_OR_STORAGE"}, sort_keys=True), flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
