#!/usr/bin/env python3
"""W25 offline research ONLY: durable unsigned receipt + two-store anchor laboratory.

The 'external' anchor is a separately stored SQLite file with a separate API, but
BOTH files are controlled by the SAME LAB ADMIN. It is NOT external independent
custody; it has no keys/real signatures/HTTP/Ario authority.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from w23_checkpoint_gossip import read_signed_note, verify_compact_consistency

ORIGIN='ario-w22-research.invalid/synthetic-log'
RID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')


def result(status, reason, receipt=None):
    r={'status':status,'reason':reason,'operational_authority':'NONE',
       'witness_cosignatures_issued':0,'publisher_actions':0,
       'source_truth':'UNKNOWN','latest_world_state':'UNKNOWN',
       'independent_operator_custody':'NOT_ESTABLISHED',
       'anchor_authentication':'NOT_ESTABLISHED', 'memory_admitted':False}
    if receipt is not None:r['unsigned_lab_receipt']=receipt
    return r


def _connect(path, kind):
    con=sqlite3.connect(str(path), timeout=8, isolation_level=None)
    try:
        con.execute('PRAGMA busy_timeout=8000')
        con.execute('PRAGMA journal_mode=DELETE')
        con.execute('PRAGMA synchronous=FULL')
        if kind=='publisher':
            con.execute('CREATE TABLE IF NOT EXISTS head (singleton INTEGER PRIMARY KEY CHECK(singleton=1), size INTEGER NOT NULL, root TEXT NOT NULL)')
            con.execute('CREATE TABLE IF NOT EXISTS requests (rid TEXT PRIMARY KEY, old_size INTEGER NOT NULL, size INTEGER NOT NULL, root TEXT NOT NULL, note_hash TEXT NOT NULL, proof_hash TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('PENDING','FINAL')), receipt TEXT)')
        elif kind=='anchor':
            con.execute('CREATE TABLE IF NOT EXISTS anchor (singleton INTEGER PRIMARY KEY CHECK(singleton=1), size INTEGER NOT NULL, root TEXT NOT NULL)')
        else:raise ValueError('invalid store kind')
        return con
    except BaseException:
        con.close()
        raise


def _read(con, table):
    row=con.execute(f'SELECT size,root FROM {table} WHERE singleton=1').fetchone()
    return None if row is None else {'size':row[0], 'root':row[1]}


def _proof_digest(proof):
    if type(proof) is not list or len(proof)>16 or any(type(p) is not str or re.fullmatch(r'[a-f0-9]{64}',p) is None for p in proof):
        return None
    return hashlib.sha256(json.dumps(proof,separators=(',',':')).encode()).hexdigest()


def _validated(old_size, note, key, proof):
    if type(old_size) is not int or not 0 <= old_size <= 64: return None
    digest=_proof_digest(proof)
    if digest is None:return None
    head=read_signed_note(note,key)
    if head is None or head['size'] < old_size:return None
    return head,digest


def _consistent(old, head, proof):
    if old is None:
        return not proof
    return verify_compact_consistency(old['size'],head['size'],old['root'],head['root'],proof)


def prepare(publisher_path, *, request_id, old_size, candidate_note, pinned_vkey, proof=None, crash_stage=None):
    """Commit request intent only; never issue a receipt here."""
    if proof is None:proof=[]
    if type(request_id) is not str or not RID.fullmatch(request_id):return result('DENY','INVALID_REQUEST_ID')
    if crash_stage not in (None,'after_prepare_commit'):return result('DENY','UNKNOWN_INJECTION')
    checked=_validated(old_size,candidate_note,pinned_vkey,proof)
    if checked is None:return result('DENY','INVALID_INPUT_OR_SIGNED_NOTE')
    head,pdigest=checked
    try:
        con=_connect(publisher_path,'publisher')
    except (sqlite3.DatabaseError,OSError):
        return result('HOLD','INVALID_PUBLISHER_STORAGE')
    try:
        con.execute('BEGIN IMMEDIATE')
        stored=con.execute('SELECT old_size,size,root,note_hash,proof_hash,state FROM requests WHERE rid=?',(request_id,)).fetchone()
        requested=(old_size,head['size'],head['root'],head['note_sha256'],pdigest)
        if stored is not None:
            con.execute('ROLLBACK')
            if tuple(stored[:5])!=requested:return result('DENY','REQUEST_ID_REUSED_WITH_DIFFERENT_BYTES')
            return result('EXISTING_INTENT','REPLAY_REQUIRES_ANCHOR_CHECK')
        if con.execute('SELECT 1 FROM requests WHERE state='PENDING' LIMIT 1').fetchone():
            con.execute('ROLLBACK');return result('HOLD','ANOTHER_REQUEST_PENDING')
        previous=_read(con,'head')
        expected=0 if previous is None else previous['size']
        if old_size!=expected:
            con.execute('ROLLBACK');return result('CONFLICT','LOCAL_OLD_SIZE_MISMATCH')
        if not _consistent(previous,head,proof):
            con.execute('ROLLBACK');return result('DENY','BAD_CONSISTENCY_OR_FORK')
        con.execute('INSERT INTO requests(rid,old_size,size,root,note_hash,proof_hash,state,receipt) VALUES(?,?,?,?,?,?,'PENDING',NULL)', (request_id,*requested))
        con.execute('COMMIT')
        if crash_stage=='after_prepare_commit':os._exit(81)
        return result('PENDING_ANCHOR','DURABLE_REQUEST_INTENT_NO_RECEIPT')
    except (sqlite3.DatabaseError,OSError):
        if con.in_transaction:con.execute('ROLLBACK')
        return result('HOLD','PUBLISHER_DATABASE_ERROR')
    finally:
        con.close()


def anchor_observe(anchor_path, *, old_size, candidate_note, pinned_vkey, proof=None, crash_stage=None):
    """Simulated *separate actor*; this method is NOT called by prepare/finalize.

    No authenticator or ACL separates it from publisher in this sandbox.
    """
    if proof is None:proof=[]
    if crash_stage not in (None,'before_anchor_commit','after_anchor_commit'):return result('DENY','UNKNOWN_INJECTION')
    checked=_validated(old_size,candidate_note,pinned_vkey,proof)
    if checked is None:return result('DENY','INVALID_INPUT_OR_SIGNED_NOTE')
    head,_=checked
    try:
        con=_connect(anchor_path,'anchor')
    except (sqlite3.DatabaseError,OSError):
        return result('HOLD','INVALID_ANCHOR_STORAGE')
    try:
        con.execute('BEGIN IMMEDIATE')
        prev=_read(con,'anchor')
        if old_size!=(0 if prev is None else prev['size']):
            con.execute('ROLLBACK');return result('CONFLICT','ANCHOR_OLD_SIZE_MISMATCH')
        if not _consistent(prev,head,proof):
            con.execute('ROLLBACK');return result('DENY','ANCHOR_REJECTED_FORK_OR_PROOF')
        con.execute('INSERT INTO anchor(singleton,size,root) VALUES(1,?,?) ON CONFLICT(singleton) DO UPDATE SET size=excluded.size,root=excluded.root', (head['size'],head['root']))
        if crash_stage=='before_anchor_commit':os._exit(82)
        con.execute('COMMIT')
        if crash_stage=='after_anchor_commit':os._exit(83)
        return result('ANCHORED_LAB','SEPARATE_DB_NOT_SEPARATE_ADMIN')
    except (sqlite3.DatabaseError,OSError):
        if con.in_transaction:con.execute('ROLLBACK')
        return result('HOLD','ANCHOR_DATABASE_ERROR')
    finally:
        con.close()


def read_heads(publisher_path, anchor_path):
    """Read-only logical comparison; database files still same-admin mutable."""
    if not Path(publisher_path).exists() and not Path(anchor_path).exists():
        return result('HOLD','NO_STORED_HEADS')
    try:
        pub=_connect(publisher_path,'publisher'); anch=_connect(anchor_path,'anchor')
        try: p,a=_read(pub,'head'),_read(anch,'anchor')
        finally:pub.close();anch.close()
    except (sqlite3.DatabaseError, OSError, ValueError):return result('HOLD','DAMAGED_OR_UNREADABLE_STORAGE')
    if a is None:return result('HOLD','NO_ANCHOR_HEAD')
    if p is None or p['size']<a['size']:return result('DENY','LOCAL_ROLLBACK_RELATIVE_TO_ANCHOR')
    if p['size']==a['size'] and p['root']!=a['root']:return result('DENY','SAME_SIZE_ROOT_CONFLICT')
    if p['size']>a['size']:return result('HOLD','ANCHOR_BEHIND_LOCAL')
    return result('MATCH','SAME_ADMIN_HEADS_AGREE_NOT_INDEPENDENCE')


def _receipt(request_id,note_hash,size,root):
    payload=f'ARIO-W25-UNSIGNED-RECEIPT-V1\n{request_id}\n{note_hash}\n{size}\n{root}\n'
    return 'UNSIGNED_W25_LAB_RECEIPT:'+hashlib.sha256(payload.encode()).hexdigest()


def finalize(publisher_path, anchor_path, *, request_id, crash_stage=None):
    """Only after exact anchored head: persist receipt and head atomically.

    Holds if anchor unavailable; cannot authenticate operator separation.
    """
    if type(request_id) is not str or not RID.fullmatch(request_id):return result('DENY','INVALID_REQUEST_ID')
    if crash_stage not in (None,'before_final_commit','after_final_commit'):
        return result('DENY','UNKNOWN_INJECTION')
    # Read separate store; in a real system this MUST be an authenticated reply
    # from a principal beyond the publisher's administrative authority.
    if not Path(anchor_path).exists():return result('HOLD','ANCHOR_UNAVAILABLE')
    try:
        an=_connect(anchor_path,'anchor')
        try: a=_read(an,'anchor')
        finally:an.close()
    except (sqlite3.DatabaseError, OSError):return result('HOLD','INVALID_ANCHOR_STORAGE')
    if a is None:return result('HOLD','ANCHOR_UNAVAILABLE')
    try:
        pub=_connect(publisher_path,'publisher')
    except (sqlite3.DatabaseError,OSError):
        return result('HOLD','INVALID_PUBLISHER_STORAGE')
    try:
        pub.execute('BEGIN IMMEDIATE')
        row=pub.execute('SELECT old_size,size,root,note_hash,state,receipt FROM requests WHERE rid=?',(request_id,)).fetchone()
        if row is None:
            pub.execute('ROLLBACK');return result('HOLD','UNKNOWN_OR_ROLLED_BACK_REQUEST')
        old_size,size,root,note_hash,state,stored_receipt=row
        p=_read(pub,'head')
        if p is None and old_size!=0:
            pub.execute('ROLLBACK');return result('DENY','LOCAL_STATE_MISSING')
        if p is not None and p['size']<a['size'] and state=='FINAL':
            pub.execute('ROLLBACK');return result('DENY','LOCAL_ROLLBACK_RELATIVE_TO_ANCHOR')
        if state=='FINAL':
            pub.execute('ROLLBACK')
            if p is None or p!={'size':size,'root':root} or a!={'size':size,'root':root} or stored_receipt!=_receipt(request_id,note_hash,size,root):
                return result('HOLD','FINAL_RECEIPT_HEAD_OR_ANCHOR_MISMATCH')
            return result('FINAL_UNSIGNED_RECEIPT','SAME_STORED_RECEIPT',stored_receipt)
        if a!={'size':size,'root':root}:
            pub.execute('ROLLBACK');return result('HOLD','ANCHOR_NOT_EXACTLY_REQUESTED_HEAD')
        if old_size!=(0 if p is None else p['size']):
            pub.execute('ROLLBACK');return result('CONFLICT','PREPARED_OLD_HEAD_CHANGED')
        receipt=_receipt(request_id,note_hash,size,root)
        pub.execute('INSERT INTO head(singleton,size,root) VALUES(1,?,?) ON CONFLICT(singleton) DO UPDATE SET size=excluded.size,root=excluded.root', (size,root))
        pub.execute('UPDATE requests SET state='FINAL',receipt=? WHERE rid=? AND state='PENDING'', (receipt,request_id))
        if crash_stage=='before_final_commit':os._exit(84)
        pub.execute('COMMIT')
        if crash_stage=='after_final_commit':os._exit(85)
        return result('FINAL_UNSIGNED_RECEIPT','PERSISTED_AFTER_ANCHOR_MATCH',receipt)
    except (sqlite3.DatabaseError,OSError):
        if pub.in_transaction:pub.execute('ROLLBACK')
        return result('HOLD','PUBLISHER_DATABASE_ERROR')
    finally:pub.close()


def worker(op, path1, path2, kwargs):
    """Spawnable multiprocessing worker for the synthetic race tests."""
    if op=='finalize':return finalize(path1,path2,**kwargs)
    if op=='prepare':return prepare(path1,**kwargs)
    raise ValueError('invalid worker operation')
