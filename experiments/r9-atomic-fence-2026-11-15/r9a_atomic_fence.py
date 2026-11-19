#!/usr/bin/env python3
"""R9-A: disposable local-action fence + IPC checkpoint prototype.

Research only: a single operator holds both SQLite files and the HMAC key.
No production actions, evidence admissions, external HTTP, or real signers.
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

GENESIS = "R9A-GENESIS-v1"
FORMAT = "r9a-v1"
MAX_MESSAGE = 16384
ALLOWED_SCOPE = "disposable:research-view"


class Hold(Exception):
    """A bounded fail-closed result; not an attestation of truth."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(*parts: Any) -> str:
    return hashlib.sha256(canonical(parts)).hexdigest()


def sign(key: bytes, obj: dict) -> str:
    return hmac.new(key, canonical(obj), hashlib.sha256).hexdigest()


@contextmanager
def _db(path: Path):
    """Explicitly close connections, including when HOLD raises mid-transaction."""
    c = sqlite3.connect(str(path), timeout=7.0, isolation_level=None)
    try:
        c.execute("PRAGMA synchronous=FULL")
        c.execute("PRAGMA busy_timeout=7000")
        yield c
        if c.in_transaction:
            raise RuntimeError("UNCOMMITTED_TRANSACTION")
    except BaseException:
        if c.in_transaction:
            c.rollback()
        raise
    finally:
        c.close()


def _check_hex(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


class CheckpointServer:
    """One separate AF_UNIX process. Authenticated messages; NOT independent administration."""

    def __init__(self, db_path: Path, socket_path: Path, key_file: Path):
        self.db_path = db_path
        self.socket_path = socket_path
        self.key = key_file.read_bytes()
        if len(self.key) < 32:
            raise Hold("TEST_KEY_TOO_SHORT")
        with _db(db_path) as c:
            c.execute("CREATE TABLE IF NOT EXISTS heads(seq INTEGER PRIMARY KEY, digest TEXT NOT NULL, parent TEXT NOT NULL)")
            c.execute("CREATE TABLE IF NOT EXISTS seen_nonces(nonce TEXT PRIMARY KEY)")
            if not c.execute("SELECT 1 FROM heads LIMIT 1").fetchone():
                c.execute("INSERT INTO heads VALUES (?,?,?)", (0, GENESIS, ""))

    def _process(self, request: dict) -> dict:
        if not isinstance(request, dict) or set(request) != {"body", "mac"}:
            raise Hold("MALFORMED_REQUEST")
        body = request["body"]
        if not isinstance(body, dict) or not isinstance(request["mac"], str):
            raise Hold("MALFORMED_REQUEST")
        if not hmac.compare_digest(sign(self.key, body), request["mac"]):
            raise Hold("BAD_REQUEST_MAC")
        nonce = body.get("nonce")
        if not isinstance(nonce, str) or not re.fullmatch(r"[0-9a-f]{32}", nonce):
            raise Hold("INVALID_NONCE")
        if body.get("protocol") != FORMAT:
            raise Hold("WRONG_PROTOCOL")
        op = body.get("op")
        with _db(self.db_path) as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                c.execute("INSERT INTO seen_nonces VALUES (?)", (nonce,))
            except sqlite3.IntegrityError as exc:
                raise Hold("REPLAYED_REQUEST_NONCE") from exc
            now = c.execute("SELECT seq,digest FROM heads ORDER BY seq DESC LIMIT 1").fetchone()
            if op == "HEAD" and set(body) == {"nonce", "protocol", "op"}:
                value = {"seq": now[0], "digest": now[1]}
            elif op == "CAS" and set(body) == {"nonce", "protocol", "op", "expected_seq", "expected_digest", "new_seq", "new_digest"}:
                if (type(body["expected_seq"]) is not int or type(body["new_seq"]) is not int
                    or not isinstance(body["expected_digest"], str) or not _check_hex(body["new_digest"])):
                    raise Hold("INVALID_CAS_FIELDS")
                if (body["expected_seq"], body["expected_digest"]) != now or body["new_seq"] != now[0] + 1:
                    raise Hold("CAS_HEAD_MISMATCH")
                c.execute("INSERT INTO heads VALUES (?,?,?)", (body["new_seq"], body["new_digest"], body["expected_digest"]))
                value = {"seq": body["new_seq"], "digest": body["new_digest"]}
            else:
                raise Hold("INVALID_OPERATION")
            c.execute("COMMIT")
            return value

    def serve(self):
        if self.socket_path.exists():
            raise Hold("SOCKET_PATH_EXISTS")
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.bind(str(self.socket_path))
            os.chmod(self.socket_path, 0o600)
            sock.listen(32)
            sock.settimeout(0.5)
            while True:
                try:
                    conn, _ = sock.accept()
                except socket.timeout:
                    continue
                with conn:
                    conn.settimeout(3.0)
                    request = None
                    try:
                        buf = b""
                        while b"\n" not in buf and len(buf) <= MAX_MESSAGE:
                            chunk = conn.recv(2048)
                            if not chunk:
                                break
                            buf += chunk
                        if b"\n" not in buf or len(buf) > MAX_MESSAGE:
                            raise Hold("TOO_LARGE_OR_UNTERMINATED")
                        request = json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))
                        data = {"ok": True, "data": self._process(request)}
                    except (Hold, ValueError, TypeError, UnicodeError, sqlite3.DatabaseError) as exc:
                        reason = str(exc) if isinstance(exc, Hold) else "INVALID_OR_CORRUPT_REQUEST"
                        data = {"ok": False, "reason": reason}
                    response = {"nonce": request.get("body", {}).get("nonce") if isinstance(request, dict) and isinstance(request.get("body"), dict) else None, "value": data}
                    conn.sendall(canonical({"body": response, "mac": sign(self.key, response)}) + b"\n")
        finally:
            sock.close()
            # No destructive unlink: test fixture directory owner handles scratch cleanup.


class CheckpointClient:
    def __init__(self, socket_path: Path, key_path: Path):
        self.socket_path = socket_path
        self.key = key_path.read_bytes()
        if len(self.key) < 32:
            raise Hold("INVALID_LOCAL_KEY")

    def request(self, op: str, **fields) -> tuple[int, str]:
        nonce = secrets.token_hex(16)
        body = {"protocol": FORMAT, "nonce": nonce, "op": op, **fields}
        message = canonical({"body": body, "mac": sign(self.key, body)}) + b"\n"
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(2.0)
                sock.connect(str(self.socket_path))
                sock.sendall(message)
                response_bytes = b""
                while b"\n" not in response_bytes and len(response_bytes) < MAX_MESSAGE:
                    part = sock.recv(2048)
                    if not part:
                        break
                    response_bytes += part
        except (OSError, TimeoutError) as exc:
            raise Hold("CHECKPOINT_UNREACHABLE") from exc
        try:
            response = json.loads(response_bytes.split(b"\n", 1)[0])
            signed = response["body"]
            if (not isinstance(signed, dict) or signed.get("nonce") != nonce
                or not hmac.compare_digest(response["mac"], sign(self.key, signed))):
                raise Hold("INVALID_CHECKPOINT_RESPONSE_AUTH")
            result = signed["value"]
            if result.get("ok") is not True:
                raise Hold("CHECKPOINT_" + result.get("reason", "REJECTED"))
            head = result["data"]
            if type(head.get("seq")) is not int or head["seq"] < 0 or not isinstance(head.get("digest"), str):
                raise Hold("BAD_CHECKPOINT_HEAD")
            if head["seq"] > 0 and not _check_hex(head["digest"]):
                raise Hold("BAD_CHECKPOINT_HEAD")
            return head["seq"], head["digest"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise Hold("MALFORMED_CHECKPOINT_RESPONSE") from exc


class ActionSink:
    """One SQLite commit boundary shared by epoch updates and local effects."""

    def __init__(self, db_path: Path, checkpoint: CheckpointClient):
        self.db_path = db_path
        self.checkpoint = checkpoint
        with _db(db_path) as c:
            c.execute("CREATE TABLE IF NOT EXISTS current_head(seq INTEGER NOT NULL, digest TEXT NOT NULL)")
            c.execute("CREATE TABLE IF NOT EXISTS effects(op_id TEXT PRIMARY KEY, seq INTEGER NOT NULL, head_digest TEXT NOT NULL, payload_digest TEXT NOT NULL, use TEXT NOT NULL, scope TEXT NOT NULL, receipt TEXT NOT NULL)")
            if not c.execute("SELECT 1 FROM current_head").fetchone():
                c.execute("INSERT INTO current_head VALUES (?,?)", (0, GENESIS))

    def _checked_head(self, c: sqlite3.Connection) -> tuple[int, str]:
        local = c.execute("SELECT seq,digest FROM current_head").fetchall()
        if len(local) != 1:
            raise Hold("LOCAL_HEAD_CORRUPT")
        remote = self.checkpoint.request("HEAD")
        if tuple(local[0]) != remote:
            raise Hold("CHECKPOINT_LOCAL_MISMATCH")
        return tuple(local[0])

    def advance(self, commitment: str, crash_after_remote: bool = False) -> tuple[int, str]:
        if not _check_hex(commitment):
            raise Hold("INVALID_CORPUS_COMMITMENT")
        with _db(self.db_path) as c:
            c.execute("BEGIN IMMEDIATE")
            old = self._checked_head(c)
            head = old[0] + 1, digest("epoch", old[0] + 1, old[1], commitment)
            got = self.checkpoint.request("CAS", expected_seq=old[0], expected_digest=old[1], new_seq=head[0], new_digest=head[1])
            if got != head:
                raise Hold("REMOTE_CAS_WRONG_HEAD")
            if crash_after_remote:
                os._exit(77)  # deliberate subprocess kill; SQLite transaction uncommitted
            c.execute("UPDATE current_head SET seq=?,digest=?", head)
            c.execute("COMMIT")
            return head

    def action(self, ticket: dict) -> dict:
        # This prototype has no evidence-admission or external-action API.
        if not isinstance(ticket, dict) or set(ticket) != {"seq", "head_digest", "op_id", "payload_digest", "use", "scope"}:
            raise Hold("INVALID_TICKET_SHAPE")
        if ticket["use"] != "RESEARCH_VIEW" or ticket["scope"] != ALLOWED_SCOPE:
            raise Hold("NO_ACTION_AUTHORITY")
        if (type(ticket["seq"]) is not int or ticket["seq"] < 1
            or not _check_hex(ticket["payload_digest"]) or not _check_hex(ticket["head_digest"])
            or not isinstance(ticket["op_id"], str) or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,100}", ticket["op_id"])):
            raise Hold("INVALID_TICKET_FIELDS")
        with _db(self.db_path) as c:
            c.execute("BEGIN IMMEDIATE")
            head = self._checked_head(c)
            if head != (ticket["seq"], ticket["head_digest"]):
                raise Hold("STALE_AT_EFFECT_BOUNDARY")
            prior = c.execute("SELECT seq,head_digest,payload_digest,use,scope,receipt FROM effects WHERE op_id=?", (ticket["op_id"],)).fetchone()
            fields = (ticket["seq"], ticket["head_digest"], ticket["payload_digest"], ticket["use"], ticket["scope"])
            if prior:
                if tuple(prior[:5]) != fields:
                    raise Hold("DUPLICATE_OP_CONFLICT")
                c.execute("COMMIT")
                return {"status": "DUPLICATE_NO_NEW_EFFECT", "receipt": prior[5]}
            receipt = digest("local_effect", ticket["op_id"], fields)
            c.execute("INSERT INTO effects VALUES (?,?,?,?,?,?,?)", (ticket["op_id"], *fields, receipt))
            c.execute("COMMIT")
            return {"status": "APPLIED", "receipt": receipt}

    def count(self) -> int:
        with _db(self.db_path) as c:
            return c.execute("SELECT COUNT(*) FROM effects").fetchone()[0]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="R9-A RESEARCH-ONLY local sink/checkpoint")
    parser.add_argument("mode", choices=("witness", "epoch", "action", "count", "head"))
    parser.add_argument("--sink-db", type=Path)
    parser.add_argument("--checkpoint-db", type=Path)
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--commitment", default="")
    parser.add_argument("--ticket-json", default="")
    parser.add_argument("--crash-after-checkpoint", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.mode == "witness":
            if args.checkpoint_db is None:
                raise Hold("MISSING_CHECKPOINT_DB")
            CheckpointServer(args.checkpoint_db, args.socket, args.key_file).serve()
            return 0
        if args.sink_db is None:
            raise Hold("MISSING_SINK_DB")
        sink = ActionSink(args.sink_db, CheckpointClient(args.socket, args.key_file))
        if args.mode == "epoch":
            head = sink.advance(args.commitment, args.crash_after_checkpoint)
            result = {"status": "ADVANCED", "seq": head[0], "digest": head[1]}
        elif args.mode == "action":
            result = sink.action(json.loads(args.ticket_json))
        elif args.mode == "count":
            result = {"status": "READ_ONLY", "count": sink.count()}
        else:
            with _db(args.sink_db) as c:
                result = {"status": "READ_ONLY", "local": list(c.execute("SELECT seq,digest FROM current_head").fetchone() or []), "checkpoint": list(sink.checkpoint.request("HEAD"))}
        print(json.dumps(result, sort_keys=True), flush=True)
        return 0
    except (Hold, ValueError, TypeError, sqlite3.DatabaseError) as exc:
        reason = str(exc) if isinstance(exc, Hold) else "INVALID_INPUT_OR_STORAGE"
        print(json.dumps({"status": "HOLD", "reason": reason}, sort_keys=True), flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
