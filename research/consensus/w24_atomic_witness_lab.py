#!/usr/bin/env python3
"""W24 synthetic SQLite witness state machine: NOT a C2SP witness/cosigner.

Only emits NON-CRYPTOGRAPHIC deterministic receipts after COMMIT. No signer, HTTP,
real Ario memory, or production trust. A same-admin SQLite DB is NOT independent custody.
"""
import hashlib
import os
import sqlite3
from pathlib import Path
from w23_checkpoint_gossip import read_signed_note, verify_compact_consistency

ORIGIN = 'ario-w22-research.invalid/synthetic-log'

def _receipt(head):
    return 'UNSIGNED_W24_LAB_RECEIPT:' + hashlib.sha256(
        ('W24-LAB-NOT-A-SIGNATURE\n' + ORIGIN + '\n' + str(head['size']) + '\n' + head['root'] + '\n').encode()
    ).hexdigest()

def _answer(code, message, *, head=None):
    result = {'status': code, 'reason': message, 'authority': 'NONE',
              'cosignature_issued': False, 'custody': 'SAME_ADMIN_NOT_INDEPENDENT',
              'world_freshness': 'UNKNOWN', 'external_actions': 0}
    if code == 'COMMITTED_UNSIGNED_LAB_RECEIPT' and head is not None:
        result['receipt'] = _receipt(head)
    return result

def open_store(db_path):
    """One SQLite writer per transaction, durable settings required for this test."""
    con = sqlite3.connect(str(db_path), timeout=15, isolation_level=None)
    con.execute('PRAGMA busy_timeout=15000')
    con.execute('PRAGMA journal_mode=DELETE')
    con.execute('PRAGMA synchronous=FULL')
    con.execute('CREATE TABLE IF NOT EXISTS heads (origin TEXT PRIMARY KEY, size INTEGER NOT NULL, root TEXT NOT NULL, note_hash TEXT NOT NULL)')
    return con

def observe(db_path, *, old_size, candidate_note, pinned_vkey, proof=None, crash_stage=None):
    """Serializable compare/write; hard subprocess crash injection; no signing."""
    if type(old_size) is not int or old_size < 0 or old_size > 64:
        return _answer('DENY', 'INVALID_OLD_SIZE')
    if crash_stage not in (None, 'before_commit', 'after_commit_before_receipt'):
        return _answer('DENY', 'INVALID_INJECTION')
    head = read_signed_note(candidate_note, pinned_vkey)
    if head is None:
        return _answer('DENY', 'INVALID_SIGNED_CHECKPOINT')
    con = open_store(db_path)
    try:
        con.execute('BEGIN IMMEDIATE')
        current = con.execute('SELECT size,root FROM heads WHERE origin=?', (ORIGIN,)).fetchone()
        expected = 0 if current is None else current[0]
        if old_size != expected:
            con.execute('ROLLBACK')
            return _answer('CONFLICT', 'RETAINED_SIZE_MISMATCH')
        if head['size'] < old_size:
            con.execute('ROLLBACK')
            return _answer('DENY', 'SIZE_DECREASE')
        if current is None:
            if proof not in (None, []):
                con.execute('ROLLBACK')
                return _answer('DENY', 'FIRST_CHECKPOINT_MUST_NOT_HAVE_PROOF')
        elif not verify_compact_consistency(old_size, head['size'], current[1], head['root'], proof if proof is not None else []):
            con.execute('ROLLBACK')
            return _answer('DENY', 'BAD_CONSISTENCY_OR_FORK')
        con.execute('INSERT INTO heads(origin,size,root,note_hash) VALUES (?,?,?,?) ON CONFLICT(origin) DO UPDATE SET size=excluded.size,root=excluded.root,note_hash=excluded.note_hash',
                    (ORIGIN,head['size'],head['root'],head['note_sha256']))
        if crash_stage == 'before_commit':
            os._exit(73)
        con.execute('COMMIT')
        if crash_stage == 'after_commit_before_receipt':
            os._exit(74)
        return _answer('COMMITTED_UNSIGNED_LAB_RECEIPT', 'COMMIT_COMPLETED', head=head)
    except Exception:
        if con.in_transaction:
            con.execute('ROLLBACK')
        raise
    finally:
        con.close()

def retained_head(db_path):
    if not Path(db_path).exists():
        return None
    con = open_store(db_path)
    try:
        row = con.execute('SELECT size,root FROM heads WHERE origin=?', (ORIGIN,)).fetchone()
        return None if row is None else {'size': row[0], 'root': row[1]}
    finally:
        con.close()

def worker(args):
    """Top-level spawn-compatible process worker, labels do NOT imply separate admins."""
    return observe(args[0], **args[1])
