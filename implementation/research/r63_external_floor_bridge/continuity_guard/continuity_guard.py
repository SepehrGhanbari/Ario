"""R63 witness continuity guard — RESEARCH_ONLY protocol model.

A surviving signing key is not evidence that a witness's durable history survived.
The witness must match a fresh 3-of-4 externally anchored checkpoint before serving.
"""
import hashlib
import json
import re
import secrets
import sqlite3
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ANCHORS = ("a1", "a2", "a3", "a4")
Q = 3
ZERO = "0" * 64
ACTIVE = "ACTIVE_CONTINUITY_VERIFIED"
QUARANTINED = "QUARANTINED_HISTORY_MISSING_OR_MISMATCHED"
HOLD = "HOLD_EXTERNAL_CONTINUITY_UNAVAILABLE"
HEX = re.compile(r"[0-9a-f]{64}\Z")

class ContinuityError(Exception):
    pass

def need(ok, message):
    if not ok:
        raise ContinuityError(message)

def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def pub(key):
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

def sign(key, tag, body):
    return key.sign(tag + b"\0" + body).hex()

def verify(public_hex, tag, body, signature):
    need(type(signature) is str and re.fullmatch(r"[0-9a-f]{128}", signature) is not None, "signature syntax")
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex)).verify(bytes.fromhex(signature), tag + b"\0" + body)

def decode(raw):
    need(type(raw) is bytes and 0 < len(raw) <= 32768, "wire size")
    def pairs(items):
        out = {}
        for k, v in items:
            need(k not in out, "duplicate JSON key")
            out[k] = v
        return out
    obj = json.loads(raw.decode("ascii"), object_pairs_hook=pairs)
    need(canon(obj) == raw, "noncanonical JSON")
    return obj

def valid_hex(value):
    return type(value) is str and HEX.fullmatch(value) is not None

def make_checkpoint(identity, policy_hash, witness_pub, seq, parent, state, op_id):
    cp = dict(identity=identity, policy_hash=policy_hash, witness_pub=witness_pub,
              sequence=seq, parent_hash=parent, state_hash=state, operation_id=op_id)
    validate_checkpoint(cp)
    return cp

def validate_checkpoint(cp):
    need(type(cp) is dict and set(cp) == {"identity", "policy_hash", "witness_pub", "sequence", "parent_hash", "state_hash", "operation_id"}, "checkpoint schema")
    need(type(cp["identity"]) is str and 1 <= len(cp["identity"]) <= 128, "identity")
    for k in ("policy_hash", "witness_pub", "parent_hash", "state_hash", "operation_id"):
        need(valid_hex(cp[k]), "checkpoint " + k)
    need(type(cp["sequence"]) is int and not isinstance(cp["sequence"], bool) and 0 <= cp["sequence"] < 2**63, "sequence")
    return cp

def cp_hash(cp):
    return sha(canon(cp))

class Anchor:
    """One independently administered anchor, represented by a separate SQLite DB."""
    def __init__(self, name, path, key, operator_key):
        need(name in ANCHORS, "anchor name")
        self.name, self.path, self.key, self.operator_key = name, Path(path), key, operator_key
        self.public, self.operator_public = pub(key), pub(operator_key)

    def _db(self):
        c = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        c.execute("PRAGMA journal_mode=DELETE")
        c.execute("PRAGMA synchronous=FULL")
        c.execute("CREATE TABLE IF NOT EXISTS identity (id TEXT PRIMARY KEY, policy TEXT NOT NULL, witness_pub TEXT NOT NULL, cp BLOB NOT NULL, witness_sig TEXT NOT NULL, commit_sig TEXT NOT NULL, initialized INTEGER NOT NULL DEFAULT 0)")
        return c

    def provision(self, cp, operator_sig):
        validate_checkpoint(cp)
        need(cp["sequence"] == 0 and cp["parent_hash"] == ZERO, "genesis only")
        body = canon(cp)
        verify(self.operator_public, b"R63-ANCHOR-ENROLL", body, operator_sig)
        c = self._db()
        try:
            c.execute("BEGIN IMMEDIATE")
            need(c.execute("SELECT 1 FROM identity WHERE id=?", (cp["identity"],)).fetchone() is None, "identity already enrolled")
            sig = sign(self.key, b"R63-ANCHOR-COMMIT", body)
            c.execute("INSERT INTO identity VALUES(?,?,?,?,?,?,0)", (cp["identity"], cp["policy_hash"], cp["witness_pub"], body, "GENESIS", sig))
            c.commit()
            return self.commit_receipt(cp, sig)
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    def mark_initialized(self, identity, genesis):
        c = self._db()
        try:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT cp,initialized FROM identity WHERE id=?", (identity,)).fetchone()
            need(row is not None and decode(row[0]) == genesis and genesis["sequence"] == 0, "not exact genesis")
            if not row[1]:
                c.execute("UPDATE identity SET initialized=1 WHERE id=?", (identity,))
            c.commit()
            b = dict(anchor=self.name, identity=identity, genesis_hash=cp_hash(genesis), initialized=True)
            return canon(dict(body=b, signature=sign(self.key, b"R63-LOCAL-INITIALIZED", canon(b))))
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    def commit_receipt(self, cp, sig):
        b = dict(anchor=self.name, anchor_pub=self.public, checkpoint=cp, checkpoint_hash=cp_hash(cp))
        return canon(dict(body=b, signature=sig))

    def commit(self, cp, witness_sig):
        validate_checkpoint(cp)
        body = canon(cp)
        c = self._db()
        try:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT policy,witness_pub,cp,commit_sig FROM identity WHERE id=?", (cp["identity"],)).fetchone()
            need(row is not None, "not enrolled")
            policy, witness_pub, old_raw, old_sig = row
            need(cp["policy_hash"] == policy and cp["witness_pub"] == witness_pub, "identity scope")
            verify(witness_pub, b"R63-WITNESS-CHECKPOINT", body, witness_sig)
            old = decode(old_raw)
            if cp == old:
                c.commit()
                return self.commit_receipt(old, old_sig)
            need(cp["sequence"] == old["sequence"] + 1 and cp["parent_hash"] == old["state_hash"], "non-monotonic or wrong parent")
            sig = sign(self.key, b"R63-ANCHOR-COMMIT", body)
            c.execute("UPDATE identity SET cp=?,witness_sig=?,commit_sig=? WHERE id=?", (body, witness_sig, sig, cp["identity"]))
            c.commit()  # durable state before returning a receipt
            return self.commit_receipt(cp, sig)
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    def read(self, identity, nonce):
        c = self._db()
        try:
            row = c.execute("SELECT policy,witness_pub,cp,commit_sig,initialized FROM identity WHERE id=?", (identity,)).fetchone()
        finally:
            c.close()
        if row is None:
            b = dict(anchor=self.name, anchor_pub=self.public, nonce=nonce, status="NOT_ENROLLED", checkpoint=None)
        else:
            policy, witness_pub, raw, sig, initialized = row
            cp = decode(raw)
            b = dict(anchor=self.name, anchor_pub=self.public, nonce=nonce, status="ENROLLED",
                     policy=policy, witness_pub=witness_pub, checkpoint=cp, checkpoint_hash=cp_hash(cp),
                     commit_signature=sig, initialized=bool(initialized))
        return canon(dict(body=b, signature=sign(self.key, b"R63-ANCHOR-READ", canon(b))))

class AnchorQuorum:
    def __init__(self, anchors):
        anchors = tuple(anchors)
        need(len(anchors) == len(ANCHORS), "exact four-anchor roster required")
        names = [a.name for a in anchors]
        need(len(set(names)) == len(ANCHORS) and set(names) == set(ANCHORS), "unique exact anchor identities required")
        anchor_keys = [a.public for a in anchors]
        need(len(set(anchor_keys)) == len(ANCHORS), "anchor signing keys must be distinct")
        operator_keys = [a.operator_public for a in anchors]
        need(len(set(operator_keys)) == len(ANCHORS), "anchor enrollment keys must be distinct")
        store_paths = [str(a.path.resolve()) for a in anchors]
        need(len(set(store_paths)) == len(ANCHORS), "anchor stores must be distinct paths")
        self.anchors = {a.name: a for a in anchors}
        self.pinned = {n: a.public for n, a in self.anchors.items()}

    def provision(self, cp, operators):
        out = []
        for n, a in self.anchors.items():
            out.append(a.provision(cp, sign(operators[n], b"R63-ANCHOR-ENROLL", canon(cp))))
        need(len(out) >= Q, "enrollment quorum")
        return out

    def mark_initialized(self, identity, genesis):
        names, out = set(), []
        for n, a in self.anchors.items():
            try:
                raw = a.mark_initialized(identity, genesis)
                obj = decode(raw); b = obj["body"]
                need(b == dict(anchor=n, identity=identity, genesis_hash=cp_hash(genesis), initialized=True), "init receipt scope")
                verify(self.pinned[n], b"R63-LOCAL-INITIALIZED", canon(b), obj["signature"])
                names.add(n); out.append(raw)
            except Exception:
                continue
        need(len(names) >= Q, "initialization marker quorum unavailable")
        return out

    def _verify_commit(self, raw, cp):
        o = decode(raw); b = o["body"]; n = b["anchor"]
        need(n in self.pinned and b["anchor_pub"] == self.pinned[n] and b["checkpoint"] == cp and b["checkpoint_hash"] == cp_hash(cp), "commit receipt scope")
        verify(self.pinned[n], b"R63-ANCHOR-COMMIT", canon(cp), o["signature"])
        return n

    def commit(self, cp, witness_sig, available=None):
        available = set(self.anchors) if available is None else set(available)
        names, out = set(), []
        for n, a in self.anchors.items():
            if n not in available: continue
            try:
                raw = a.commit(cp, witness_sig); who = self._verify_commit(raw, cp)
                need(who not in names, "duplicate anchor receipt")
                names.add(who); out.append(raw)
            except Exception:
                continue
        need(len(names) >= Q, "durable write quorum unavailable")
        return out

    def latest(self, identity, nonce, available=None):
        need(valid_hex(nonce), "nonce")
        available = set(self.anchors) if available is None else set(available)
        replies, groups = [], {}
        for n, a in self.anchors.items():
            if n not in available: continue
            try:
                raw = a.read(identity, nonce); o = decode(raw); b = o["body"]
                need(b["anchor"] == n and b["anchor_pub"] == self.pinned[n] and b["nonce"] == nonce, "read scope")
                verify(self.pinned[n], b"R63-ANCHOR-READ", canon(b), o["signature"])
                replies.append((n, b, raw))
                if b["status"] == "ENROLLED":
                    cp = validate_checkpoint(b["checkpoint"])
                    need(cp["identity"] == identity and cp["policy_hash"] == b["policy"] and cp["witness_pub"] == b["witness_pub"], "checkpoint scope")
                    need(cp_hash(cp) == b["checkpoint_hash"], "checkpoint hash")
                    verify(self.pinned[n], b"R63-ANCHOR-COMMIT", canon(cp), b["commit_signature"])
                    groups.setdefault(canon(cp), []).append((n, raw, b["initialized"]))
                else:
                    need(b["status"] == "NOT_ENROLLED", "anchor status")
            except Exception:
                continue
        need(len(replies) >= Q, "fewer than three authenticated reads")
        winners = [(k, v) for k, v in groups.items() if len(v) >= Q]
        need(len(winners) == 1, "no unique 3-of-4 matching head")
        cp = decode(winners[0][0])
        for _, b, _ in replies:
            if b["status"] == "ENROLLED":
                other = b["checkpoint"]
                need(other["sequence"] <= cp["sequence"], "higher unquorummed head: HOLD")
                if other["sequence"] == cp["sequence"]:
                    need(other == cp, "same-sequence fork: HOLD")
        init_count = sum(1 for _, _, flag in winners[0][1] if flag is True)
        return cp, tuple(raw for _, raw, _ in winners[0][1]), init_count

class Witness:
    def __init__(self, identity, policy_hash, path, key, quorum):
        self.identity, self.policy, self.path = identity, policy_hash, Path(path)
        self.key, self.quorum, self.witness_pub = key, quorum, pub(key)

    def _db(self):
        c = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        c.execute("PRAGMA journal_mode=DELETE"); c.execute("PRAGMA synchronous=FULL")
        c.execute("CREATE TABLE IF NOT EXISTS local (id INTEGER PRIMARY KEY CHECK(id=1), identity TEXT, policy TEXT, witness_pub TEXT, cp BLOB NOT NULL, pending BLOB)")
        return c

    def _local(self):
        if not self.path.exists(): return None
        c = self._db()
        try: return c.execute("SELECT identity,policy,witness_pub,cp,pending FROM local WHERE id=1").fetchone()
        finally: c.close()

    def provision_local(self, genesis):
        validate_checkpoint(genesis)
        need(genesis["identity"] == self.identity and genesis["policy_hash"] == self.policy and genesis["witness_pub"] == self.witness_pub and genesis["sequence"] == 0 and genesis["parent_hash"] == ZERO, "genesis scope")
        anchored, _, init_count = self.quorum.latest(self.identity, secrets.token_hex(32))
        need(anchored == genesis and init_count < Q, "identity already initialized or not at genesis")
        existing = self._local()
        if existing is not None:
            need((existing[0], existing[1], existing[2]) == (self.identity, self.policy, self.witness_pub) and decode(existing[3]) == genesis and existing[4] is None, "existing local state mismatch")
        # Consume external one-time init marker before creating local DB: a crash here retires the identity.
        self.quorum.mark_initialized(self.identity, genesis)
        if existing is None:
            c = self._db()
            try:
                c.execute("BEGIN IMMEDIATE")
                need(c.execute("SELECT 1 FROM local WHERE id=1").fetchone() is None, "local already exists")
                c.execute("INSERT INTO local VALUES(1,?,?,?,?,NULL)", (self.identity, self.policy, self.witness_pub, canon(genesis)))
                c.commit()
            finally: c.close()

    def status(self, available=None):
        try:
            anchored, _, init_count = self.quorum.latest(self.identity, secrets.token_hex(32), available)
        except Exception:
            return HOLD
        if init_count < Q: return HOLD
        try: row = self._local()
        except Exception: return QUARANTINED
        if row is None: return QUARANTINED
        identity, policy, witness_pub, raw, pending = row
        if (identity, policy, witness_pub) != (self.identity, self.policy, self.witness_pub): return QUARANTINED
        try:
            local = decode(raw)
            if pending is not None:
                pcp = decode(pending)
                if pcp == anchored:
                    self._commit_local(pcp, pending); local = pcp
                elif pcp["parent_hash"] == local["state_hash"] and pcp["sequence"] == local["sequence"] + 1 and anchored == local:
                    return "PENDING_ANCHOR_RECOVERY_REQUIRED"
                else: return QUARANTINED
            return ACTIVE if local == anchored else QUARANTINED
        except Exception:
            return QUARANTINED

    def _write_pending(self, cp):
        c = self._db()
        try:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT cp,pending FROM local WHERE id=1").fetchone()
            need(row is not None and row[1] is None, "missing local state or pending")
            old = decode(row[0]); need(cp["sequence"] == old["sequence"] + 1 and cp["parent_hash"] == old["state_hash"], "local parent mismatch")
            c.execute("UPDATE local SET pending=? WHERE id=1", (canon(cp),)); c.commit()
        finally: c.close()

    def _commit_local(self, cp, pending):
        c = self._db()
        try:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT pending FROM local WHERE id=1").fetchone()
            need(row is not None and row[0] == pending, "pending changed")
            c.execute("UPDATE local SET cp=?,pending=NULL WHERE id=1", (canon(cp),)); c.commit()
        except BaseException:
            c.rollback(); raise
        finally: c.close()

    def transition(self, new_state_hash, write_available=None, failpoint=None):
        need(valid_hex(new_state_hash) and self.status() == ACTIVE, "witness not continuity-active")
        row = self._local(); old = decode(row[3])
        cp = make_checkpoint(self.identity, self.policy, self.witness_pub, old["sequence"] + 1,
                             old["state_hash"], new_state_hash, secrets.token_hex(32))
        raw = canon(cp); self._write_pending(cp)
        if failpoint: failpoint("after_local_pending")
        sig = sign(self.key, b"R63-WITNESS-CHECKPOINT", raw)
        receipts = self.quorum.commit(cp, sig, write_available)
        if failpoint: failpoint("after_anchor_quorum")
        self._commit_local(cp, raw)
        if failpoint: failpoint("after_local_commit")
        return dict(status="CONTINUITY_COMMITTED_RESEARCH_ONLY", checkpoint=cp, anchor_receipts=len(receipts))

    def resume_pending(self, write_available=None):
        if self.status() == QUARANTINED: raise ContinuityError("quarantined; identity cannot be re-enrolled")
        row = self._local(); need(row is not None and row[4] is not None, "no pending transition")
        cp = decode(row[4]); sig = sign(self.key, b"R63-WITNESS-CHECKPOINT", canon(cp))
        receipts = self.quorum.commit(cp, sig, write_available)
        self._commit_local(cp, row[4])
        return dict(status="RECOVERED_RESEARCH_ONLY", checkpoint=cp, anchor_receipts=len(receipts))

    def read_identity_proof(self, nonce, available=None):
        need(valid_hex(nonce) and self.status(available) == ACTIVE, "witness cannot prove continuity")
        cp, reads, init_count = self.quorum.latest(self.identity, nonce, available)
        need(init_count >= Q, "initialization marker quorum missing")
        row = self._local(); need(decode(row[3]) == cp, "local/anchor mismatch")
        body = dict(identity=self.identity, policy=self.policy, witness_pub=self.witness_pub,
                    nonce=nonce, checkpoint=cp, anchor_read_responses=[r.decode("ascii") for r in reads])
        return canon(dict(body=body, signature=sign(self.key, b"R63-WITNESS-CONTINUITY", canon(body))))
