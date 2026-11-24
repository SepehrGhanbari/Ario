#!/usr/bin/env python3
"""R9-C: disposable in-destination conditional effect + separately stored receipt.

RESEARCH ONLY. SQLite rows simulate effects. This does not perform external actions,
create independent administration, authorize witnesses, or provide exact-once WAN IO.
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
import socketserver
import sqlite3
import sys
from typing import Any

PROTOCOL = "ARIO-R9C-RESEARCH-1"
CERT = "ARIO-R9C-RECEIPT-1"
GENESIS = hashlib.sha256(b"R9C-RESEARCH-ONLY-GENESIS-20261115").hexdigest()
E0 = hashlib.sha256(b"R9C-RESEARCH-ONLY-EVENT-GENESIS").hexdigest()
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
IDENT = re.compile(r"[a-zA-Z0-9_.-]{1,64}\Z")
MAX_PACKET = 12000
SCOPE = "RESEARCH_VIEW_ONLY"

class Hold(Exception):
    pass

def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False,
                      ensure_ascii=True).encode("ascii")

def sha(*values: Any) -> str:
    return hashlib.sha256(canonical(values)).hexdigest()

def sig(key: bytes, body: dict) -> str:
    return hmac.new(key, canonical(body), hashlib.sha256).hexdigest()

def h64(value):
    return isinstance(value, str) and HEX64.fullmatch(value) is not None

def identity(value):
    return isinstance(value, str) and IDENT.fullmatch(value) is not None

@contextmanager
def db_open(path: Path):
    c = sqlite3.connect(str(path), isolation_level=None, timeout=10.0)
    try:
        c.execute("PRAGMA busy_timeout=10000")
        c.execute("PRAGMA synchronous=FULL")
        c.execute("PRAGMA journal_mode=DELETE")
        yield c
        if c.in_transaction:
            raise RuntimeError("UNCOMMITTED_DB_OPERATION")
    except BaseException:
        if c.in_transaction:
            c.rollback()
        raise
    finally:
        c.close()

def read_packet(sock):
    data = bytearray()
    while True:
        byte = sock.recv(4096)
        if not byte:
            raise Hold("TRUNCATED_MESSAGE")
        data += byte
        if len(data) > MAX_PACKET:
            raise Hold("MESSAGE_OVERSIZE")
        if b"\n" in data:
            left, right = data.split(b"\n", 1)
            if right.strip():
                raise Hold("EXTRA_MESSAGE")
            obj = json.loads(left.decode("utf-8"))
            if type(obj) is not dict:
                raise Hold("INVALID_JSON_SHAPE")
            return obj

class Gate:
    def __init__(self, role: str, path: Path, auth_key: bytes, receipt_key: bytes):
        if role not in ("dest", "witness") or len(auth_key) != 32 or len(receipt_key) != 32:
            raise Hold("INVALID_RESEARCH_CONFIGURATION")
        self.role, self.path = role, path
        self.auth_key, self.receipt_key = auth_key, receipt_key
        with db_open(path) as c:
            if role == "dest":
                c.execute("CREATE TABLE IF NOT EXISTS head(singleton INTEGER PRIMARY KEY CHECK(singleton=1), seq INTEGER NOT NULL, hash TEXT NOT NULL, idx INTEGER NOT NULL, event_hash TEXT NOT NULL)")
                c.execute("CREATE TABLE IF NOT EXISTS effects(op_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, proof TEXT NOT NULL)")
                c.execute("CREATE TABLE IF NOT EXISTS events(idx INTEGER PRIMARY KEY, proof TEXT NOT NULL)")
                if not c.execute("SELECT 1 FROM head").fetchone():
                    c.execute("INSERT INTO head VALUES (1,0,?,0,?)", (GENESIS, E0))
            else:
                c.execute("CREATE TABLE IF NOT EXISTS witness_head(singleton INTEGER PRIMARY KEY CHECK(singleton=1), idx INTEGER NOT NULL, hash TEXT NOT NULL)")
                c.execute("CREATE TABLE IF NOT EXISTS checkpoints(idx INTEGER PRIMARY KEY, proof TEXT NOT NULL)")
                if not c.execute("SELECT 1 FROM witness_head").fetchone():
                    c.execute("INSERT INTO witness_head VALUES (1,0,?)", (E0,))
            c.execute("CREATE TABLE IF NOT EXISTS nonces(nonce TEXT PRIMARY KEY)")

    def create_proof(self, idx, prev, kind, seq, head_hash, op_id, payload):
        event_hash = sha("R9C-EVENT", idx, prev, kind, seq, head_hash, op_id, payload)
        fields = dict(format=CERT, idx=idx, prev=prev, event_hash=event_hash,
                      kind=kind, epoch=seq, epoch_hash=head_hash, op_id=op_id,
                      payload_hash=payload)
        return dict(body=fields, mac=sig(self.receipt_key, fields))

    def checked_proof(self, proof):
        if type(proof) is not dict or set(proof) != {"body", "mac"} or type(proof["body"]) is not dict:
            raise Hold("INVALID_PROOF_SHAPE")
        p = proof["body"]
        if set(p) != {"format", "idx", "prev", "event_hash", "kind", "epoch", "epoch_hash", "op_id", "payload_hash"}:
            raise Hold("INVALID_PROOF_FIELDS")
        if (p["format"] != CERT or type(p["idx"]) is not int or p["idx"] < 1
            or type(p["epoch"]) is not int or p["epoch"] < 0
            or p["kind"] not in ("EPOCH", "APPLY") or not h64(p["prev"])
            or not h64(p["event_hash"]) or not h64(p["epoch_hash"])
            or not isinstance(p["op_id"], str) or not h64(p["payload_hash"])
            or not isinstance(proof["mac"], str)
            or not hmac.compare_digest(sig(self.receipt_key, p), proof["mac"])):
            raise Hold("UNTRUSTED_OR_MALFORMED_RECEIPT")
        if p["event_hash"] != sha("R9C-EVENT", p["idx"], p["prev"], p["kind"],
                                  p["epoch"], p["epoch_hash"], p["op_id"], p["payload_hash"]):
            raise Hold("PROOF_CONTENT_MISMATCH")
        return p

    def process(self, envelope):
        if type(envelope) is not dict or set(envelope) != {"body", "mac"} or type(envelope["body"]) is not dict:
            raise Hold("BAD_REQUEST_ENVELOPE")
        body = envelope["body"]
        if not isinstance(envelope["mac"], str) or not hmac.compare_digest(sig(self.auth_key, body), envelope["mac"]):
            raise Hold("BAD_CLIENT_AUTHENTICATION")
        if body.get("format") != PROTOCOL or not isinstance(body.get("nonce"), str) or not re.fullmatch("[0-9a-f]{32}", body["nonce"]):
            raise Hold("BAD_NONCE_OR_PROTOCOL")
        op = body.get("op")
        allowed = {
            "DEST_HEAD": {"format", "nonce", "op"},
            "DEST_APPLY": {"format", "nonce", "op", "op_id", "payload_hash", "scope", "epoch", "epoch_hash"},
            "DEST_ADVANCE": {"format", "nonce", "op", "epoch", "epoch_hash", "commitment"},
            "DEST_LOOKUP": {"format", "nonce", "op", "op_id"},
            "DEST_EVENT": {"format", "nonce", "op", "idx"},
            "WIT_HEAD": {"format", "nonce", "op"},
            "WIT_RECORD": {"format", "nonce", "op", "proof"},
        }
        if op not in allowed or set(body) != allowed[op] or (self.role == "dest") != op.startswith("DEST_"):
            raise Hold("BAD_OPERATION_OR_FIELDS")
        with db_open(self.path) as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                c.execute("INSERT INTO nonces VALUES (?)", (body["nonce"],))
            except sqlite3.IntegrityError as exc:
                raise Hold("REPLAYED_NONCE") from exc
            if self.role == "witness":
                idx, h = c.execute("SELECT idx,hash FROM witness_head").fetchone()
                if op == "WIT_HEAD":
                    answer = {"idx": idx, "event_hash": h}
                else:
                    proof = body["proof"]
                    p = self.checked_proof(proof)
                    if p["idx"] == idx and p["event_hash"] == h:
                        stored = c.execute("SELECT proof FROM checkpoints WHERE idx=?", (idx,)).fetchone()
                        if not stored or stored[0] != canonical(proof).decode("ascii"):
                            raise Hold("CONFLICTING_DUPLICATE_RECEIPT")
                        answer = {"status": "ALREADY_RECORDED", "idx": idx, "event_hash": h}
                    elif p["idx"] == idx+1 and p["prev"] == h:
                        c.execute("INSERT INTO checkpoints VALUES (?,?)", (p["idx"], canonical(proof).decode("ascii")))
                        c.execute("UPDATE witness_head SET idx=?,hash=?", (p["idx"], p["event_hash"]))
                        answer = {"status": "CHECKPOINTED", "idx": p["idx"], "event_hash": p["event_hash"]}
                    else:
                        raise Hold("CHECKPOINT_GAP_OR_CONFLICT")
            else:
                seq, hh, idx, eh = c.execute("SELECT seq,hash,idx,event_hash FROM head").fetchone()
                if op == "DEST_HEAD":
                    answer = {"epoch": seq, "epoch_hash": hh, "idx": idx, "event_hash": eh}
                elif op == "DEST_EVENT":
                    if type(body["idx"]) is not int or body["idx"] < 1:
                        raise Hold("BAD_EVENT_INDEX")
                    row = c.execute("SELECT proof FROM events WHERE idx=?", (body["idx"],)).fetchone()
                    answer = {"status": "FOUND", "proof": json.loads(row[0])} if row else {"status": "UNKNOWN_EVENT"}
                elif op == "DEST_LOOKUP":
                    if not identity(body["op_id"]):
                        raise Hold("BAD_LOOKUP_ID")
                    row = c.execute("SELECT proof FROM effects WHERE op_id=?", (body["op_id"],)).fetchone()
                    answer = {"status": "FOUND", "proof": json.loads(row[0])} if row else {"status": "NOT_FOUND_UNPROVEN"}
                elif op == "DEST_ADVANCE":
                    if (type(body["epoch"]) is not int or body["epoch"] < 0 or
                        not h64(body["epoch_hash"]) or not h64(body["commitment"])):
                        raise Hold("BAD_ADVANCE_FIELDS")
                    if (body["epoch"], body["epoch_hash"]) != (seq, hh):
                        raise Hold("STALE_EPOCH_AT_DESTINATION")
                    seq += 1
                    hh = sha("R9C-EPOCH", seq, hh, body["commitment"])
                    proof = self.create_proof(idx+1, eh, "EPOCH", seq, hh, "", body["commitment"])
                    c.execute("UPDATE head SET seq=?,hash=?,idx=?,event_hash=?", (seq, hh, idx+1, proof["body"]["event_hash"]))
                    c.execute("INSERT INTO events VALUES (?,?)", (idx+1, canonical(proof).decode("ascii")))
                    answer = {"status": "ADVANCED_AT_DESTINATION_ONLY", "proof": proof}
                else:
                    ident, ph, sc, expected_seq, expected_hh = (body[k] for k in ("op_id", "payload_hash", "scope", "epoch", "epoch_hash"))
                    if (not identity(ident) or not h64(ph) or sc != SCOPE or
                        type(expected_seq) is not int or expected_seq < 1 or not h64(expected_hh)):
                        raise Hold("BAD_APPLY_FIELDS_OR_SCOPE")
                    finger = sha("R9C-INTENT", ident, ph, sc, expected_seq, expected_hh)
                    old = c.execute("SELECT fingerprint,proof FROM effects WHERE op_id=?", (ident,)).fetchone()
                    if old:
                        if old[0] != finger:
                            raise Hold("OP_ID_CONFLICT")
                        answer = {"status": "ALREADY_APPLIED_DESTINATION", "proof": json.loads(old[1])}
                    else:
                        if (expected_seq, expected_hh) != (seq, hh):
                            raise Hold("STALE_EPOCH_AT_DESTINATION")
                        proof = self.create_proof(idx+1, eh, "APPLY", seq, hh, ident, ph)
                        c.execute("INSERT INTO effects VALUES (?,?,?)", (ident, finger, canonical(proof).decode("ascii")))
                        c.execute("INSERT INTO events VALUES (?,?)", (idx+1, canonical(proof).decode("ascii")))
                        c.execute("UPDATE head SET idx=?,event_hash=?", (idx+1, proof["body"]["event_hash"]))
                        answer = {"status": "APPLIED_AT_SIMULATED_DESTINATION", "proof": proof}
            c.execute("COMMIT")
            if self.role == "dest" and op == "DEST_APPLY" and os.environ.get("R9C_KILL_AFTER_COMMIT_OP") == body.get("op_id"):
                os._exit(75)
            if self.role == "witness" and op == "WIT_RECORD" and os.environ.get("R9C_KILL_AFTER_WIT_RECORD_IDX") == str(answer["idx"]):
                os._exit(76)
            return answer

class ThreadedUnix(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False

class WireHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(4.0)
        try:
            req = read_packet(self.request)
            value = {"ok": True, "result": self.server.gate.process(req)}
        except (Hold, KeyError, ValueError, TypeError, UnicodeError, OSError, sqlite3.DatabaseError) as exc:
            value = {"ok": False, "reason": str(exc) if isinstance(exc, Hold) else "INVALID_REQUEST_OR_STORAGE"}
        reply = {"value": value, "nonce": (req.get("body", {}).get("nonce") if isinstance(locals().get("req"), dict) and isinstance(req.get("body"), dict) else None)}
        try:
            self.request.sendall(canonical({"body": reply, "mac": sig(self.server.gate.auth_key, reply)})+b"\n")
        except OSError:
            pass

class WireClient:
    def __init__(self, socket_path: Path, key: bytes):
        self.socket_path, self.key = socket_path, key
        if len(key) != 32:
            raise Hold("INVALID_CLIENT_KEY")
    def call(self, op: str, **params):
        nonce = secrets.token_hex(16)
        body = {"format": PROTOCOL, "nonce": nonce, "op": op, **params}
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(3.0)
                s.connect(str(self.socket_path))
                s.sendall(canonical({"body": body, "mac": sig(self.key, body)})+b"\n")
                rep = read_packet(s)
        except (OSError, TimeoutError, Hold) as exc:
            raise Hold("UNCERTAIN_REMOTE_RESULT") from exc
        try:
            response = rep["body"]
            if (type(response) is not dict or response["nonce"] != nonce or
                not isinstance(rep["mac"], str) or not hmac.compare_digest(sig(self.key,response), rep["mac"])):
                raise Hold("INVALID_RESPONSE_AUTH")
            val = response["value"]
            if type(val) is not dict:
                raise Hold("INVALID_RESPONSE_VALUE")
            if val.get("ok") is not True:
                if not isinstance(val.get("reason"), str):
                    raise Hold("INVALID_DENIAL")
                raise Hold("DENIED_"+val["reason"])
            if type(val.get("result")) is not dict:
                raise Hold("INVALID_RESULT_SHAPE")
            return val["result"]
        except (ValueError, KeyError, TypeError) as exc:
            raise Hold("INVALID_RESPONSE_SCHEMA") from exc

class CoordinatedResearch:
    """Orchestration has no global transaction; a lost ACK is HOLD_UNCERTAIN."""
    def __init__(self, dest: WireClient, witness: WireClient):
        self.dest, self.witness = dest, witness
    def heads(self):
        a = self.dest.call("DEST_HEAD")
        b = self.witness.call("WIT_HEAD")
        if (a.get("idx"),a.get("event_hash")) != (b.get("idx"), b.get("event_hash")):
            raise Hold("DESTINATION_WITNESS_HISTORY_DIVERGED")
        return a
    def checkpoint(self, proof):
        return self.witness.call("WIT_RECORD", proof=proof)
    def apply(self, op_id, payload_hash, *, crash_in_ack=False):
        current = self.heads()
        try:
            result = self.dest.call("DEST_APPLY", op_id=op_id, payload_hash=payload_hash,
                                    scope=SCOPE, epoch=current["epoch"], epoch_hash=current["epoch_hash"])
        except Hold:
            return {"status":"HOLD_UNCERTAIN_DESTINATION", "op_id":op_id}
        if crash_in_ack:
            return {"status": "HOLD_UNCERTAIN_DESTINATION", "op_id":op_id}
        try:
            proof = result["proof"]
            w = self.checkpoint(proof)
        except (KeyError, Hold):
            return {"status": "HOLD_UNCERTAIN_CHECKPOINT", "op_id":op_id}
        return {"status":"SIMULATED_EFFECT_CHECKPOINTED_NOT_INDEPENDENT",
                "destination_status": result["status"], "idx":w["idx"]}
    def advance(self, commitment):
        current = self.heads()
        try:
            result=self.dest.call("DEST_ADVANCE",epoch=current["epoch"],epoch_hash=current["epoch_hash"],commitment=commitment)
        except Hold:
            return {"status":"HOLD_UNCERTAIN_EPOCH"}
        try:
            checkpoint=self.checkpoint(result["proof"])
        except Hold:
            return {"status":"HOLD_UNCERTAIN_CHECKPOINT"}
        return {"status":"SIMULATED_EPOCH_CHECKPOINTED_NOT_INDEPENDENT","idx":checkpoint["idx"]}
    def reconcile(self, op_id):
        # Client REQUESTS a read-only destination result, never assumes a timeout means no effect.
        lookup=self.dest.call("DEST_LOOKUP", op_id=op_id)
        if lookup.get("status") != "FOUND":
            return {"status":"HOLD_NO_AUTHENTICATED_DESTINATION_PROOF"}
        proof = lookup.get("proof")
        p = proof.get("body") if isinstance(proof, dict) else None
        if (not isinstance(p, dict) or p.get("kind") != "APPLY" or
                p.get("op_id") != op_id):
            return {"status": "HOLD_LOOKUP_IDENTITY_MISMATCH"}
        # The witness verifies the receipt MAC and event chain; do not fabricate proof locally.
        observed=self.witness.call("WIT_HEAD")
        if p["idx"] > observed["idx"]+1:
            return {"status":"HOLD_MISSING_INTERMEDIATE_CHECKPOINTS"}
        try:
            result=self.checkpoint(lookup["proof"])
        except Hold:
            return {"status":"HOLD_CONFLICTING_OR_UNAVAILABLE_CHECKPOINT"}
        return {"status":"SIMULATED_RECONCILED_NOT_INDEPENDENT", "idx":result["idx"]}

def serve(role, path, socket_path, auth_key_file, receipt_key_file):
    if socket_path.exists():
        raise Hold("SOCKET_ALREADY_PRESENT")
    gate = Gate(role, path, auth_key_file.read_bytes(), receipt_key_file.read_bytes())
    with ThreadedUnix(str(socket_path), WireHandler) as server:
        server.gate=gate
        os.chmod(socket_path,0o600)
        server.serve_forever(poll_interval=0.15)

def main(argv=None):
    p=argparse.ArgumentParser(description="R9-C bounded conditional-destination toy")
    p.add_argument("role",choices=["dest","witness"])
    p.add_argument("--db",type=Path,required=True)
    p.add_argument("--socket",type=Path,required=True)
    p.add_argument("--auth-key",type=Path,required=True)
    p.add_argument("--receipt-key",type=Path,required=True)
    a=p.parse_args(argv)
    serve(a.role,a.db,a.socket,a.auth_key,a.receipt_key)

if __name__=="__main__":
    main()
