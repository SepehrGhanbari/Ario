#!/usr/bin/env python3
"""W29 two simulated observer channels: RESEARCH_ONLY, NO TRUST.

Two distinct SQLite files are still under ONE administrator and do not prove
external keeper identity, key custody, channel authentication or world freshness.
No network, real witness signatures, signer, Ario memory or production effects.
"""
from __future__ import annotations
import base64
import os
from pathlib import Path
import sqlite3
from w23_checkpoint_gossip import read_signed_note, verify_compact_consistency

ORIGIN = "ario-w22-research.invalid/synthetic-log"
READY = "READ_ONLY_UNAUTHENTICATED"


def answer(status, reason, **extra):
    return {
        "status":status,"reason":reason,"policy":"HOLD",
        "independent_operator_custody":"NOT_ESTABLISHED",
        "observer_channel_authentication":"NOT_ESTABLISHED",
        "externally_protected_floor":"NOT_ESTABLISHED",
        "world_freshness":"UNKNOWN","source_truth":"UNKNOWN",
        "authority":"NONE","production":"NO_GO","genesis":"NO_GO",
        "trust_activation":"NO_GO","memory_admitted":False,
        "cosignatures_issued":0,"external_submissions":0,**extra
    }


def _connect(path):
    c=sqlite3.connect(str(path),timeout=12,isolation_level=None)
    try:
        c.execute("PRAGMA busy_timeout=12000")
        c.execute("PRAGMA journal_mode=DELETE")
        c.execute("PRAGMA synchronous=FULL")
        c.execute("CREATE TABLE IF NOT EXISTS head(singleton INTEGER PRIMARY KEY CHECK(singleton=1),size INTEGER NOT NULL,root TEXT NOT NULL,note BLOB NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS history(size INTEGER PRIMARY KEY,root TEXT NOT NULL,note BLOB NOT NULL)")
        return c
    except BaseException:
        c.close();raise


def observe(db_path, *, old_size, signed_note, pinned_log_vkey, proof=None, crash=None):
    """Verify signed W22 note + monotonic Merkle continuity, atomically persist."""
    if proof is None:proof=[]
    if type(old_size) is not int or not 0<=old_size<=64:
        return answer("DENY","INVALID_EXPECTED_SIZE")
    if crash not in (None,"before_commit","after_commit"):
        return answer("DENY","INVALID_CRASH_STAGE")
    head=read_signed_note(signed_note,pinned_log_vkey,origin=ORIGIN)
    if head is None:return answer("DENY","INVALID_SIGNED_CHECKPOINT")
    if head["size"]<old_size:return answer("DENY","CANDIDATE_SIZE_DECREASE")
    if type(proof) is not list or len(proof)>16 or any(type(x) is not str or len(x)!=64 for x in proof):
        return answer("DENY","MALFORMED_PROOF")
    try: c=_connect(db_path)
    except (sqlite3.DatabaseError,OSError):
        return answer("HOLD","OBSERVER_STORAGE_UNREADABLE")
    try:
        c.execute("BEGIN IMMEDIATE")
        previous=c.execute("SELECT size,root FROM head WHERE singleton=1").fetchone()
        expected=0 if previous is None else previous[0]
        if expected!=old_size:
            c.execute("ROLLBACK");return answer("CONFLICT","EXPECTED_SIZE_MISMATCH")
        consistent=(not proof) if previous is None else verify_compact_consistency(
            old_size,head["size"],previous[1],head["root"],proof)
        if not consistent:
            c.execute("ROLLBACK");return answer("DENY","BAD_CONSISTENCY_OR_FORK")
        stored=c.execute("SELECT root FROM history WHERE size=?",(head["size"],)).fetchone()
        if stored and stored[0]!=head["root"]:
            c.execute("ROLLBACK");return answer("DENY","HISTORY_FORK")
        c.execute("INSERT INTO head(singleton,size,root,note) VALUES(1,?,?,?) ON CONFLICT(singleton) DO UPDATE SET size=excluded.size,root=excluded.root,note=excluded.note",(head["size"],head["root"],signed_note))
        c.execute("INSERT OR IGNORE INTO history(size,root,note) VALUES(?,?,?)",(head["size"],head["root"],signed_note))
        if crash=="before_commit":os._exit(91)
        c.execute("COMMIT")
        if crash=="after_commit":os._exit(92)
        return answer("COMMITTED_UNSIGNED_OBSERVATION","PERSISTED_IN_SAME_ADMIN_LAB",size=head["size"],root=head["root"])
    except (sqlite3.DatabaseError,OSError):
        if c.in_transaction:c.execute("ROLLBACK")
        return answer("HOLD","OBSERVER_TRANSACTION_ERROR")
    finally:c.close()


def readback(db_path):
    """These unsigned local-file readbacks are NOT authenticated witness replies."""
    if not Path(db_path).is_file():
        return answer("OFFLINE","OBSERVER_FILE_ABSENT")
    try:
        c=_connect(db_path)
        try:row=c.execute("SELECT size,root,note FROM head WHERE singleton=1").fetchone()
        finally:c.close()
    except (sqlite3.DatabaseError,OSError):
        return answer("UNREADABLE","OBSERVER_FILE_CORRUPT")
    if row is None:return answer("OFFLINE","OBSERVER_NOT_INITIALIZED")
    return answer("READ_ONLY_UNAUTHENTICATED","SAME_ADMIN_FILE_READBACK",size=row[0],
                  root=row[1],note_b64=base64.b64encode(row[2]).decode())


def _parse(view,vkey):
    if type(view) is not dict or view.get("status")!=READY:return None
    encoded=view.get("note_b64")
    if type(encoded) is not str or len(encoded)>8192:return None
    try:
        raw=base64.b64decode(encoded,validate=True)
        if base64.b64encode(raw).decode()!=encoded:return None
    except (ValueError,base64.binascii.Error):
        return None
    h=read_signed_note(raw,vkey,origin=ORIGIN)
    if (h is None or type(view.get("size")) is not int
        or view["size"]!=h["size"] or view.get("root")!=h["root"]):
        return None
    return h


def _check(old,new,proof):
    return verify_compact_consistency(old["size"],new["size"],old["root"],new["root"],proof)


def compare(view_a,view_b, *, pinned_log_vkey, floor_note=None,
            proof_small_to_large=None, floor_proofs=None):
    """All caller supplied, including a floor; no protection inferred from an input."""
    if proof_small_to_large is None:proof_small_to_large=[]
    if floor_proofs is None:floor_proofs={"a":[],"b":[]}
    if (type(proof_small_to_large) is not list or type(floor_proofs) is not dict
        or set(floor_proofs)!={"a","b"}
        or any(type(q) is not list for q in floor_proofs.values())):
        return answer("HOLD","INVALID_PROOF_ENVELOPE")
    if (type(view_a) is not dict or type(view_b) is not dict
        or view_a.get("status")!=READY or view_b.get("status")!=READY):
        return answer("HOLD","ONE_OR_BOTH_OBSERVERS_UNAVAILABLE")
    a,b=_parse(view_a,pinned_log_vkey),_parse(view_b,pinned_log_vkey)
    if a is None or b is None:
        return answer("HOLD","INVALID_OR_TAMPERED_READBACK_NOTE")
    floor=None
    if floor_note is not None:
        floor=read_signed_note(floor_note,pinned_log_vkey,origin=ORIGIN)
        if floor is None:return answer("HOLD","INVALID_SUPPLIED_FLOOR")
        if a["size"]<floor["size"] or b["size"]<floor["size"]:
            return answer("HOLD","OBSERVER_BELOW_SUPPLIED_FLOOR",sizes=[a["size"],b["size"]])
        for label,head in (("a",a),("b",b)):
            if head["size"]==floor["size"]:
                if head["root"]!=floor["root"]:
                    return answer("HOLD","OBSERVER_FORK_VS_SUPPLIED_FLOOR")
            elif not _check(floor,head,floor_proofs[label]):
                return answer("HOLD","FLOOR_TO_OBSERVER_PROOF_UNVERIFIED")
    if a["size"]==b["size"]:
        if a["root"]!=b["root"]:
            return answer("HOLD","TWO_SIGNED_SAME_SIZE_FORK",size=a["size"])
        return answer("HOLD","TWO_VIEWS_AGREE_WITHOUT_INDEPENDENT_CUSTODY",
                      size=a["size"],
                      floor_evidence="CALLER_SUPPLIED_ONLY" if floor else "NONE")
    older,newer=(a,b) if a["size"]<b["size"] else (b,a)
    if not _check(older,newer,proof_small_to_large):
        return answer("HOLD","DIFFERING_VIEWS_NO_CONSISTENCY_PROOF",sizes=[a["size"],b["size"]])
    return answer("HOLD","ONE_OBSERVER_LAGS_BUT_CONSISTENCY_PROVEN_FOR_SUPPLIED_NOTES",
                  sizes=[a["size"],b["size"]])


def worker(args):
    """Local spawn-compatible worker only; not a distinct operator."""
    operation,db_path,kw=args
    if operation=="observe":return observe(db_path,**kw)
    if operation=="readback":return readback(db_path)
    raise ValueError("UNSUPPORTED_WORKER_OPERATION")
