#!/usr/bin/env python3
"""R6 research-only OS principal / nonce journal exercise. Not production authority.

Only synthetic data, ephemeral Ed25519 key, no real tool executions, no Ario keys.
Executor E signs a fabricated receipt; Custodian C pins E's public key in an
OS-owned 0700 directory, verifies signatures, and performs locked nonce spends.
The SAME GitHub runner administrator provisions both users; administrative
independence is therefore explicitly NOT ESTABLISHED.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption

DOMAIN = b"ARIO-R6-SYNTHETIC-EXECUTION-V0.1\x00"
CHAIN_DOMAIN = b"ARIO-R6-SYNTHETIC-CUSTODY-V0.1\x00"
VERSION = "ARIO-R6-SYNTHETIC-RECEIPT-v0.1"
GENESIS = "0" * 64
MAX_RECEIPT = 4096
MAX_LOG = 65536
MAX_EVENTS = 128
MAX_SKEW_SECONDS = 300
_NONCE = re.compile(r"[a-zA-Z0-9._:-]{1,96}\Z")
_HEX = re.compile(r"[0-9a-f]{64}\Z")


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def pairs(values):
    d = {}
    for k, v in values:
        if k in d:
            raise ValueError("DUPLICATE_JSON_KEY")
        d[k] = v
    return d


def load(raw, limit=MAX_RECEIPT):
    if type(raw) is not bytes or not 0 < len(raw) <= limit:
        raise ValueError("INVALID_BYTES")
    obj = json.loads(raw.decode("ascii"), object_pairs_hook=pairs,
                     parse_float=lambda _: (_ for _ in ()).throw(ValueError("FLOAT_NOT_ALLOWED")),
                     parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_NOT_ALLOWED")))
    if canon(obj) != raw:
        raise ValueError("NONCANONICAL_JSON")
    return obj


def outcome(code, *, head=GENESIS, count=0, observed=False, **extra):
    # A valid OS permission boundary or a valid signature never grants Ario authority.
    return dict(profile="R6_OS_BOUNDARY_RESEARCH_ONLY", reason_code=code,
                inspection="OBSERVED_ONLY" if observed else "UNKNOWN",
                head_sha256=head, record_count=count, **extra,
                os_principal_separation="OBSERVED_IN_DISPOSABLE_RUNNER_ONLY",
                administrative_independence="NOT_ESTABLISHED",
                external_anchor_proof="NOT_ESTABLISHED",
                execution_reality="NOT_ESTABLISHED",
                evidence_admission_allowed=False, memory_write_allowed=False,
                tool_execution_allowed=False, signing_authority_allowed=False,
                trust_activation_allowed=False)


def create_private(path, data):
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def keygen(private_path, public_path):
    key = Ed25519PrivateKey.generate()
    priv = key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    pub = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    create_private(private_path, priv)
    create_private(public_path, pub)
    return outcome("SYNTHETIC_KEY_CREATED", key_id=hashlib.sha256(pub).hexdigest())


def sign(private_path, public_path, out_path, nonce, age_seconds):
    if not isinstance(nonce, str) or not _NONCE.fullmatch(nonce):
        raise ValueError("INVALID_NONCE")
    if type(age_seconds) is not int or not -86400 <= age_seconds <= 3600:
        raise ValueError("INVALID_AGE_PARAMETER")
    priv = Path(private_path).read_bytes()
    pub = Path(public_path).read_bytes()
    if len(priv) != 32 or len(pub) != 32:
        raise ValueError("INVALID_SYNTHETIC_KEY_BYTES")
    key = Ed25519PrivateKey.from_private_bytes(priv)
    if key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw) != pub:
        raise ValueError("PUBLIC_PRIVATE_MISMATCH")
    payload = {"version": VERSION, "key_id": hashlib.sha256(pub).hexdigest(),
               "nonce": nonce, "issued_epoch": int(time.time()) + age_seconds,
               "request_sha256": "a" * 64, "result_sha256": "b" * 64}
    envelope = {"payload": payload, "signature_hex": key.sign(DOMAIN + canon(payload)).hex()}
    create_private(out_path, canon(envelope))
    os.chmod(out_path, 0o644)  # Shared synthetic receipt, never a private key.
    return outcome("SYNTHETIC_RECEIPT_SIGNED", nonce=nonce)


def assert_custody_directory(directory):
    st = os.lstat(directory)
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) != 0o700:
        raise ValueError("CUSTODY_DIRECTORY_WRONG_OWNER_OR_MODE")


def secure_open(path):
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0), 0o600)
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) != 0o600:
        os.close(fd)
        raise ValueError("UNSAFE_JOURNAL_FILE_OWNER_OR_MODE")
    return fd


def journal_state(fd):
    os.lseek(fd, 0, os.SEEK_SET)
    raw = os.read(fd, MAX_LOG + 1)
    if len(raw) > MAX_LOG or (raw and not raw.endswith(b"\n")):
        raise ValueError("TRUNCATED_OR_OVERSIZED_JOURNAL")
    lines = raw.split(b"\n")[:-1] if raw else []
    if len(lines) > MAX_EVENTS:
        raise ValueError("JOURNAL_RECORD_LIMIT")
    prev, seen, revoked = GENESIS, set(), False
    for idx, line in enumerate(lines, 1):
        obj = load(line, 1024)
        if type(obj) is not dict or set(obj) != {"event", "head_sha256"}:
            raise ValueError("INVALID_EVENT_SHAPE")
        ev = obj["event"]
        if (type(ev) is not dict or set(ev) != {"sequence", "previous_sha256", "kind", "nonce", "receipt_sha256"}
            or type(ev["sequence"]) is not int or ev["sequence"] != idx
            or type(ev["previous_sha256"]) is not str or ev["previous_sha256"] != prev
            or type(ev["kind"]) is not str or ev["kind"] not in ("NONCE_SPENT", "KEY_REVOKED")
            or type(ev["receipt_sha256"]) is not str or not _HEX.fullmatch(ev["receipt_sha256"])
            or not isinstance(obj["head_sha256"], str) or not _HEX.fullmatch(obj["head_sha256"])):
            raise ValueError("INVALID_JOURNAL_EVENT")
        if ev["kind"] == "NONCE_SPENT":
            if revoked or type(ev["nonce"]) is not str or not _NONCE.fullmatch(ev["nonce"]) or ev["nonce"] in seen:
                raise ValueError("INVALID_OR_DUPLICATE_NONCE_HISTORY")
            seen.add(ev["nonce"])
        else:
            if revoked or ev["nonce"] is not None:
                raise ValueError("INVALID_REVOCATION_HISTORY")
            revoked = True
        prev = hashlib.sha256(CHAIN_DOMAIN + canon(ev)).hexdigest()
        if obj["head_sha256"] != prev:
            raise ValueError("JOURNAL_HASH_MISMATCH")
    return prev, len(lines), seen, revoked


def append(fd, head, count, kind, nonce, receipt_digest):
    ev = {"sequence": count + 1, "previous_sha256": head, "kind": kind,
          "nonce": nonce, "receipt_sha256": receipt_digest}
    new_head = hashlib.sha256(CHAIN_DOMAIN + canon(ev)).hexdigest()
    line = canon({"event": ev, "head_sha256": new_head}) + b"\n"
    if count >= MAX_EVENTS:
        raise ValueError("JOURNAL_RECORD_LIMIT")
    size = os.fstat(fd).st_size
    if size + len(line) > MAX_LOG:
        raise ValueError("JOURNAL_BYTE_LIMIT")
    count_written = os.write(fd, line)
    if count_written != len(line):
        raise OSError("PARTIAL_JOURNAL_APPEND_FAIL_CLOSED")
    os.fsync(fd)
    return new_head


def custodian(directory, command, receipt_file=None):
    import fcntl  # POSIX-only laboratory; never imported on Windows.
    assert_custody_directory(directory)
    pubpath = Path(directory) / "trusted_executor.pub"
    pubstat = os.lstat(pubpath)
    if (not stat.S_ISREG(pubstat.st_mode) or pubstat.st_uid != os.geteuid()
        or stat.S_IMODE(pubstat.st_mode) != 0o600):
        raise ValueError("TRUSTED_PUBLIC_KEY_OWNER_OR_MODE")
    pub = pubpath.read_bytes()
    if len(pub) != 32:
        raise ValueError("INVALID_PUBLIC_KEY_SIZE")
    if command == "spend":
        if receipt_file is None:
            raise ValueError("MISSING_RECEIPT")
        raw = Path(receipt_file).read_bytes()
        envelope = load(raw)
        if type(envelope) is not dict or set(envelope) != {"payload", "signature_hex"}:
            raise ValueError("INVALID_RECEIPT_ENVELOPE")
        payload, signature = envelope["payload"], envelope["signature_hex"]
        if (type(payload) is not dict
            or set(payload) != {"version", "key_id", "nonce", "issued_epoch", "request_sha256", "result_sha256"}
            or payload["version"] != VERSION
            or type(payload["key_id"]) is not str or payload["key_id"] != hashlib.sha256(pub).hexdigest()
            or type(payload["nonce"]) is not str or not _NONCE.fullmatch(payload["nonce"])
            or type(payload["issued_epoch"]) is not int
            or abs(int(time.time()) - payload["issued_epoch"]) > MAX_SKEW_SECONDS
            or type(payload["request_sha256"]) is not str or not _HEX.fullmatch(payload["request_sha256"])
            or type(payload["result_sha256"]) is not str or not _HEX.fullmatch(payload["result_sha256"])
            or type(signature) is not str or not re.fullmatch(r"[0-9a-f]{128}", signature)):
            raise ValueError("INVALID_RECEIPT_OR_CUSTODIAN_CLOCK")
        try:
            Ed25519PublicKey.from_public_bytes(pub).verify(bytes.fromhex(signature), DOMAIN + canon(payload))
        except InvalidSignature as ex:
            raise ValueError("INVALID_SIGNATURE") from ex
        nonce, receipt_digest = payload["nonce"], hashlib.sha256(raw).hexdigest()
    else:
        nonce, receipt_digest = None, "0" * 64
    lockfd = secure_open(Path(directory) / "journal.lock")
    try:
        fcntl.flock(lockfd, fcntl.LOCK_EX)
        statefd = secure_open(Path(directory) / "journal.jsonl")
        try:
            head, count, seen, revoked = journal_state(statefd)
            if revoked:
                return outcome("KEY_ALREADY_REVOKED", head=head, count=count)
            if command == "spend":
                if nonce in seen:
                    return outcome("REPLAYED_NONCE", head=head, count=count)
                head = append(statefd, head, count, "NONCE_SPENT", nonce, receipt_digest)
                return outcome("SYNTHETIC_NONCE_SPEND_RECORDED", head=head, count=count + 1, observed=True)
            if command == "revoke":
                head = append(statefd, head, count, "KEY_REVOKED", None, "0" * 64)
                return outcome("SYNTHETIC_REVOCATION_RECORDED", head=head, count=count + 1, observed=True)
            raise ValueError("UNKNOWN_CUSTODIAN_COMMAND")
        finally:
            os.close(statefd)
    finally:
        fcntl.flock(lockfd, fcntl.LOCK_UN)
        os.close(lockfd)


def probe(path, mode):
    try:
        if mode == "read":
            with open(path, "rb") as f:
                f.read(1)
        elif mode == "write":
            with open(path, "ab") as f:
                f.write(b"")  # never mutates byte history; open itself is the ACL test
        else:
            raise ValueError("INVALID_PROBE_MODE")
    except PermissionError as exc:
        if exc.errno in (errno.EACCES, errno.EPERM):
            return {"probe": "ACCESS_DENIED", "errno": errno.errorcode.get(exc.errno), "uid": os.geteuid()}
        raise
    return {"probe": "ACCESS_GRANTED", "uid": os.geteuid()}


def main():
    p = argparse.ArgumentParser(description="Synthetic R6 custody experiment — never grants authority")
    subs = p.add_subparsers(dest="operation", required=True)
    k = subs.add_parser("keygen")
    k.add_argument("--private", required=True); k.add_argument("--public", required=True)
    s = subs.add_parser("sign")
    s.add_argument("--private", required=True); s.add_argument("--public", required=True)
    s.add_argument("--out", required=True); s.add_argument("--nonce", required=True)
    s.add_argument("--age-seconds", type=int, default=0)
    c = subs.add_parser("custodian")
    c.add_argument("--dir", required=True); c.add_argument("--action", choices=("spend", "revoke"), required=True)
    c.add_argument("--receipt")
    q = subs.add_parser("probe")
    q.add_argument("--path", required=True); q.add_argument("--mode", choices=("read", "write"), required=True)
    args = p.parse_args()
    try:
        if args.operation == "keygen":
            result = keygen(args.private, args.public)
        elif args.operation == "sign":
            result = sign(args.private, args.public, args.out, args.nonce, args.age_seconds)
        elif args.operation == "custodian":
            result = custodian(args.dir, args.action, args.receipt)
        else:
            result = probe(args.path, args.mode)
    except (ValueError, OSError, TypeError, UnicodeError) as exc:
        result = outcome("LAB_ERROR_FAIL_CLOSED", error_type=type(exc).__name__)
    print(json.dumps(result, sort_keys=True))
    # Protocol result is structured; nonzero for refusals and access-granted probes.
    if args.operation == "probe":
        return 0 if result.get("probe") == "ACCESS_DENIED" else 2
    return 0 if result.get("inspection") == "OBSERVED_ONLY" or result.get("reason_code") in (
        "SYNTHETIC_KEY_CREATED", "SYNTHETIC_RECEIPT_SIGNED"
    ) else 3


if __name__ == "__main__":
    sys.exit(main())
