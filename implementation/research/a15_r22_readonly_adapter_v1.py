#!/usr/bin/env python3
"""A15 v0.5 read-only checkpoint adapter for the R22 external-witness research.

This module never opens the Broker database for writing, never repairs the local
floor, never publishes to a network, and never grants operational authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

FORMAT = "ario-a15-r22-readonly-checkpoint-v1"
DOMAIN = "ARIO/A15/R22"
BROKER_SOURCE_FILENAME = "a15_custodian_broker_v0_5.py"
BROKER_SOURCE_COMMIT = "bfe66cbba60a25086773d1790284eb97e3a6202a"
BROKER_SOURCE_GIT_BLOB_SHA1 = "612fa44e6eb2cb1078561bca85bb0f69f984bff9"
BROKER_SOURCE_REPO_PATH = "implementation/research/a15_custodian_broker_v0_5.py"
LEDGER_FILENAME = "custodian.sqlite3"
FLOOR_FILENAME = "custodian.floor.json"
FLOOR_FORMAT = "a15-custodian-floor-v1"
GENESIS = "GENESIS"
HASH_RE = re.compile(r"[0-9a-f]{64}\Z")
SCOPE_RE = re.compile(r"[A-Z0-9_-]{4,64}\Z")
MAX_FLOOR_BYTES = 4096
MAX_PREVIOUS_BYTES = 16384
EXPECTED_COLUMNS = (
    ("seq", "INTEGER", 0, 1),
    ("request_key", "TEXT", 1, 0),
    ("input_hash", "TEXT", 1, 0),
    ("decision", "TEXT", 1, 0),
    ("reason", "TEXT", 1, 0),
    ("disposition", "TEXT", 1, 0),
    ("prev_hash", "TEXT", 1, 0),
    ("hash", "TEXT", 1, 0),
)
DECISIONS = frozenset(("ACCEPT", "DECLINE", "UNKNOWN"))
PAYLOAD_KEYS = frozenset((
    "format", "domain", "enrollment", "journal_scope", "broker_source",
    "broker_head", "previous_external_checkpoint_sha256",
))
ENVELOPE_KEYS = frozenset(("payload", "payload_sha256"))
SOURCE = {
    "commit": BROKER_SOURCE_COMMIT,
    "git_blob_sha1": BROKER_SOURCE_GIT_BLOB_SHA1,
    "path": BROKER_SOURCE_REPO_PATH,
}


class AdapterHold(ValueError):
    """Fail-closed result: no checkpoint should be published."""


def canonical(value):
    """Canonical ASCII JSON for the new envelope (not the Broker's row JSON)."""
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    )


def _broker_json(value):
    """Match the exact insertion-order JSON encoding used by Broker v0.5."""
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
    )


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data):
    """Return the Git blob ID, normalizing Windows CRLF checkout bytes to LF."""
    normalized = data.replace(b"\r\n", b"\n")
    if b"\r" in normalized:
        raise AdapterHold("Broker source contains an unsupported standalone CR byte")
    header = b"blob " + str(len(normalized)).encode("ascii") + b"\0"
    return hashlib.sha1(header + normalized).hexdigest()


def _no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AdapterHold("duplicate JSON key")
        result[key] = value
    return result


def _parse_json(raw):
    try:
        return json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_no_duplicates,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                AdapterHold("non-finite JSON value")
            ),
        )
    except (UnicodeError, json.JSONDecodeError, TypeError) as exc:
        raise AdapterHold("invalid JSON input") from exc


def _require_hash(value, label):
    if type(value) is not str or not HASH_RE.fullmatch(value):
        raise AdapterHold(label + " is not a lowercase SHA-256 digest")


def _path_stat(path):
    st = path.stat()
    return (
        st.st_dev, st.st_ino, st.st_size,
        getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)),
        getattr(st, "st_ctime_ns", int(st.st_ctime * 1_000_000_000)),
    )


def _read_regular_file(path, max_bytes, label):
    if path.is_symlink() or not path.is_file():
        raise AdapterHold(label + " must be an existing regular non-symlink file")
    before = _path_stat(path)
    if before[2] > max_bytes:
        raise AdapterHold(label + " exceeds the bounded input size")
    data = path.read_bytes()
    after = _path_stat(path)
    if before != after or len(data) != before[2]:
        raise AdapterHold(label + " changed while being read")
    return data


def _verify_broker_source(source_path):
    path = Path(source_path)
    if path.is_symlink() or not path.is_file():
        raise AdapterHold("pinned Broker source must be a regular non-symlink file")
    data = path.read_bytes()
    actual = git_blob_sha1(data)
    if actual != BROKER_SOURCE_GIT_BLOB_SHA1:
        raise AdapterHold("Broker source blob does not match the pinned #346 source")
    return dict(SOURCE)


def _parse_floor(raw):
    floor = _parse_json(raw)
    if type(floor) is not dict or set(floor) != {
        "format", "ledger", "expected_seq", "expected_hash"
    }:
        raise AdapterHold("local floor schema mismatch")
    seq = floor["expected_seq"]
    head = floor["expected_hash"]
    valid_head = (
        (seq == 0 and head == GENESIS)
        or (type(seq) is int and seq > 0 and type(head) is str
            and HASH_RE.fullmatch(head))
    )
    if (
        floor["format"] != FLOOR_FORMAT
        or floor["ledger"] != LEDGER_FILENAME
        or type(seq) is not int
        or seq < 0
        or not valid_head
    ):
        raise AdapterHold("local floor fields are invalid")
    return seq, head


def _read_previous_checkpoint(path, journal_scope):
    previous_path = Path(path)
    raw = _read_regular_file(
        previous_path, MAX_PREVIOUS_BYTES, "previous checkpoint",
    )
    envelope = _parse_json(raw)
    if type(envelope) is not dict or set(envelope) != ENVELOPE_KEYS:
        raise AdapterHold("previous checkpoint envelope schema mismatch")
    payload = envelope["payload"]
    payload_sha = envelope["payload_sha256"]
    if type(payload) is not dict or set(payload) != PAYLOAD_KEYS:
        raise AdapterHold("previous checkpoint payload schema mismatch")
    _require_hash(payload_sha, "previous payload digest")
    if _sha256(canonical(payload).encode("ascii")) != payload_sha:
        raise AdapterHold("previous checkpoint payload digest mismatch")
    if (
        payload["format"] != FORMAT
        or payload["domain"] != DOMAIN
        or payload["journal_scope"] != journal_scope
        or payload["broker_source"] != SOURCE
        or payload["enrollment"] not in ("INITIAL_BASELINE", "CONTINUATION")
    ):
        raise AdapterHold("previous checkpoint scope/source/domain mismatch")
    head = payload["broker_head"]
    if type(head) is not dict or set(head) != {"seq", "hash"}:
        raise AdapterHold("previous checkpoint head schema mismatch")
    seq, digest = head["seq"], head["hash"]
    if type(seq) is not int or seq < 0:
        raise AdapterHold("previous checkpoint sequence is invalid")
    if seq == 0:
        if digest != GENESIS:
            raise AdapterHold("previous genesis checkpoint hash is invalid")
    else:
        _require_hash(digest, "previous Broker head")
    prior = payload["previous_external_checkpoint_sha256"]
    if prior != GENESIS:
        _require_hash(prior, "previous external checkpoint link")
    return payload_sha, (seq, digest)


def _verify_event_rows(conn, previous_head):
    previous = GENESIS
    expected_seq = 1
    previous_checkpoint_hash = GENESIS if previous_head and previous_head[0] == 0 else None

    rows = conn.execute(
        """SELECT seq,request_key,input_hash,decision,reason,disposition,prev_hash,hash
           FROM events ORDER BY seq"""
    )
    for row in rows:
        seq, request_key, input_hash, decision, reason, disposition, prior, actual = row
        if (
            type(seq) is not int
            or seq != expected_seq
            or type(request_key) is not str or not request_key
            or type(input_hash) is not str or not HASH_RE.fullmatch(input_hash)
            or decision not in DECISIONS
            or type(reason) is not str or not reason
            or type(disposition) is not str or not disposition
            or prior != previous
            or type(actual) is not str or not HASH_RE.fullmatch(actual)
        ):
            raise AdapterHold("Broker event row schema/sequence/hash-chain conflict")
        core = {
            "seq": seq,
            "request_key": request_key,
            "input_hash": input_hash,
            "decision": decision,
            "reason": reason,
            "disposition": disposition,
            "prev_hash": prior,
        }
        expected_hash = _sha256(_broker_json(core).encode("utf-8"))
        if actual != expected_hash:
            raise AdapterHold("Broker event hash mismatch")
        if previous_head and seq == previous_head[0]:
            previous_checkpoint_hash = actual
        previous = actual
        expected_seq += 1

    head_seq, head_hash = expected_seq - 1, previous
    if previous_head:
        old_seq, old_hash = previous_head
        if old_seq > head_seq:
            raise AdapterHold("Broker is behind the previous external checkpoint: rollback HOLD")
        if previous_checkpoint_hash != old_hash:
            raise AdapterHold("Broker history diverges at the previous checkpoint: fork HOLD")
        if head_seq <= old_seq:
            raise AdapterHold("Broker head has not advanced beyond the previous checkpoint")
    return head_seq, head_hash


def _read_broker_snapshot(state_dir, previous_head):
    root = Path(state_dir)
    if root.is_symlink() or not root.is_dir():
        raise AdapterHold("state directory must already exist and must not be a symlink")
    db_path = root / LEDGER_FILENAME
    floor_path = root / FLOOR_FILENAME
    if db_path.is_symlink() or not db_path.is_file():
        raise AdapterHold("Broker ledger must be an existing regular non-symlink file")
    if floor_path.is_symlink() or not floor_path.is_file():
        raise AdapterHold("local floor must be an existing regular non-symlink file")
    for suffix in ("-journal", "-wal", "-shm"):
        if (root / (LEDGER_FILENAME + suffix)).exists():
            raise AdapterHold("SQLite sidecar present; read-only snapshot refused")
    floor_before = _read_regular_file(
        floor_path, MAX_FLOOR_BYTES, "local floor",
    )
    db_stat_before = _path_stat(db_path)
    if db_stat_before[2] < 100:
        raise AdapterHold("Broker ledger is smaller than a SQLite header")

    conn = None
    try:
        uri = db_path.absolute().as_uri() + "?mode=ro"
        conn = sqlite3.connect(
            uri, uri=True, timeout=2, isolation_level=None,
        )
        conn.execute("PRAGMA query_only=ON")
        if conn.execute("PRAGMA query_only").fetchone() != (1,):
            raise AdapterHold("SQLite query_only could not be confirmed")
        conn.execute("BEGIN")
        # This first read establishes the SQLite snapshot. No write statement
        # is issued anywhere in this adapter.
        objects = conn.execute(
            """SELECT type,name FROM sqlite_master
               WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"""
        ).fetchall()
        if objects != [("table", "events")]:
            raise AdapterHold("Broker database contains an unexpected schema/object set")
        mode = conn.execute("PRAGMA journal_mode").fetchone()
        if not mode or str(mode[0]).lower() != "delete":
            raise AdapterHold("Broker journal mode is not the pinned DELETE mode")
        integrity = conn.execute("PRAGMA integrity_check").fetchall()
        if integrity != [("ok",)]:
            raise AdapterHold("SQLite integrity_check did not return exactly ok")
        columns = conn.execute("PRAGMA table_info(events)").fetchall()
        observed_columns = tuple(
            (row[1], str(row[2]).upper(), row[3], row[5]) for row in columns
        )
        if observed_columns != EXPECTED_COLUMNS:
            raise AdapterHold("Broker events table columns differ from the pinned schema")
        head_seq, head_hash = _verify_event_rows(conn, previous_head)
        floor_after = _read_regular_file(
            floor_path, MAX_FLOOR_BYTES, "local floor",
        )
        if floor_before != floor_after:
            raise AdapterHold("local floor changed during the SQLite snapshot")
        floor_seq, floor_hash = _parse_floor(floor_after)
        if (floor_seq, floor_hash) != (head_seq, head_hash):
            raise AdapterHold("local floor does not exactly match the read-only Broker head")
        if _path_stat(db_path) != db_stat_before:
            raise AdapterHold("Broker ledger path changed during the read-only snapshot")
        for suffix in ("-journal", "-wal", "-shm"):
            if (root / (LEDGER_FILENAME + suffix)).exists():
                raise AdapterHold("SQLite sidecar appeared during snapshot")
        return head_seq, head_hash
    except (sqlite3.Error, OSError) as exc:
        raise AdapterHold("read-only SQLite snapshot failed") from exc
    finally:
        if conn is not None:
            try:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
            finally:
                conn.close()


def build_checkpoint(
    state_dir,
    journal_scope,
    *,
    previous_checkpoint_path=None,
    enroll_genesis=False,
    broker_source_path=None,
):
    """Build a canonical checkpoint from one read-only Broker snapshot.

    First enrollment requires explicit enroll_genesis=True. Later checkpoints
    require a prior envelope file and a strictly advanced, matching Broker
    chain. The prior envelope is integrity-checked, not authenticated.
    """
    if type(journal_scope) is not str or not SCOPE_RE.fullmatch(journal_scope):
        raise AdapterHold("journal_scope must be 4-64 uppercase ASCII letters/digits/_/-")
    if (previous_checkpoint_path is None) == (not enroll_genesis):
        raise AdapterHold("choose exactly one: explicit genesis enrollment or previous checkpoint")
    source_path = (
        Path(broker_source_path) if broker_source_path is not None
        else Path(__file__).with_name(BROKER_SOURCE_FILENAME)
    )
    source = _verify_broker_source(source_path)

    if enroll_genesis:
        previous_digest = GENESIS
        previous_head = None
        enrollment = "INITIAL_BASELINE"
    else:
        previous_digest, previous_head = _read_previous_checkpoint(
            previous_checkpoint_path, journal_scope,
        )
        enrollment = "CONTINUATION"

    head_seq, head_hash = _read_broker_snapshot(state_dir, previous_head)
    payload = {
        "format": FORMAT,
        "domain": DOMAIN,
        "enrollment": enrollment,
        "journal_scope": journal_scope,
        "broker_source": source,
        "broker_head": {"seq": head_seq, "hash": head_hash},
        "previous_external_checkpoint_sha256": previous_digest,
    }
    return {
        "payload": payload,
        "payload_sha256": _sha256(canonical(payload).encode("ascii")),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="A15 R22 read-only checkpoint adapter; no network publication",
    )
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--journal-scope", required=True)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--enroll-genesis", action="store_true")
    choice.add_argument("--previous-checkpoint")
    args = parser.parse_args(argv)
    try:
        envelope = build_checkpoint(
            args.state_dir,
            args.journal_scope,
            previous_checkpoint_path=args.previous_checkpoint,
            enroll_genesis=args.enroll_genesis,
        )
        sys.stdout.write(canonical(envelope) + "\n")
        return 0
    except (AdapterHold, OSError, sqlite3.Error, ValueError) as exc:
        sys.stderr.write("A15_R22_ADAPTER_HOLD:" + type(exc).__name__ + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
