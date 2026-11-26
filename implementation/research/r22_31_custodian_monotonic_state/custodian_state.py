#!/usr/bin/env python3
"""Research-only monotonic custodian journal prototype (Linux/Python stdlib + OpenSSL)."""
from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ZERO_HASH = "0" * 64
POLICY = "R22.31_CUSTODIAN_MONOTONIC_JOURNAL_V1"
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
NONCE_RE = HASH_RE


class GateError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class DuplicateJSONKeyError(ValueError):
    pass


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJSONKeyError(key)
        result[key] = value
    return result


def canonical(obj: Any) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw, object_pairs_hook=reject_duplicate_json_keys)
    except DuplicateJSONKeyError as exc:
        raise GateError("JSON_DUPLICATE_KEY") from exc
    except Exception as exc:
        raise GateError("JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise GateError("JSON_OBJECT_REQUIRED")
    return value, raw


def openssl_sign(private_key: Path, payload: bytes) -> bytes:
    try:
        proc = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", str(private_key)],
            input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
    except OSError as exc:
        raise GateError("OPENSSL_UNAVAILABLE") from exc
    if proc.returncode != 0:
        raise GateError("SIGNATURE_CREATE_FAILED")
    return proc.stdout


def openssl_verify(public_key: Path, payload: bytes, signature: bytes) -> bool:
    with tempfile.NamedTemporaryFile(prefix="ario-r22-31-sig-", delete=True) as sig_file:
        sig_file.write(signature)
        sig_file.flush()
        proc = subprocess.run(
            ["openssl", "dgst", "-sha256", "-verify", str(public_key), "-signature", sig_file.name],
            input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
    return proc.returncode == 0


def atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb", closefd=True) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def validate_hash(value: Any, code: str) -> str:
    if not isinstance(value, str) or not HASH_RE.fullmatch(value):
        raise GateError(code)
    return value


def validate_anchor(anchor: dict[str, Any]) -> dict[str, Any]:
    required = {"format", "device_ek_sha256", "storage_root_sha256", "epoch", "head_sha256"}
    if set(anchor) != required or anchor.get("format") != "ARIO-R22.31-ANCHOR-V1":
        raise GateError("ANCHOR_SCHEMA_INVALID")
    validate_hash(anchor.get("device_ek_sha256"), "ANCHOR_EK_INVALID")
    validate_hash(anchor.get("storage_root_sha256"), "ANCHOR_STORAGE_ROOT_INVALID")
    validate_hash(anchor.get("head_sha256"), "ANCHOR_HEAD_INVALID")
    epoch = anchor.get("epoch")
    if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
        raise GateError("ANCHOR_EPOCH_INVALID")
    return dict(anchor)


def validate_request(req: dict[str, Any], state: dict[str, Any]) -> None:
    required = {
        "device_ek_sha256", "storage_root_sha256", "previous_epoch", "next_epoch",
        "previous_head_sha256", "next_head_sha256", "reason", "nonce",
    }
    if set(req) != required:
        raise GateError("REQUEST_SCHEMA_INVALID")
    validate_hash(req.get("device_ek_sha256"), "REQUEST_EK_INVALID")
    validate_hash(req.get("storage_root_sha256"), "REQUEST_STORAGE_ROOT_INVALID")
    validate_hash(req.get("previous_head_sha256"), "REQUEST_PREVIOUS_HEAD_INVALID")
    validate_hash(req.get("next_head_sha256"), "REQUEST_NEXT_HEAD_INVALID")
    nonce = req.get("nonce")
    if not isinstance(nonce, str) or not NONCE_RE.fullmatch(nonce):
        raise GateError("NONCE_FORMAT_INVALID")
    if req.get("reason") != "TPM_CLEAR_RECOVERY":
        raise GateError("RECOVERY_REASON_INVALID")
    if req["device_ek_sha256"] != state["device_ek_sha256"]:
        raise GateError("DEVICE_IDENTITY_MISMATCH")
    previous = req.get("previous_epoch")
    following = req.get("next_epoch")
    if isinstance(previous, bool) or not isinstance(previous, int) or previous != state["epoch"]:
        raise GateError("EPOCH_STALE")
    if isinstance(following, bool) or not isinstance(following, int) or following != state["epoch"] + 1:
        raise GateError("EPOCH_STEP_INVALID")
    if req["previous_head_sha256"] != state["head_sha256"]:
        raise GateError("PREVIOUS_HEAD_MISMATCH")
    if req["storage_root_sha256"] == state["storage_root_sha256"]:
        raise GateError("RESET_NOT_PROVEN")
    if req["next_head_sha256"] == state["head_sha256"]:
        raise GateError("NEXT_HEAD_NOT_ADVANCED")


def initial_state(anchor: dict[str, Any]) -> dict[str, Any]:
    return {
        "device_ek_sha256": anchor["device_ek_sha256"],
        "storage_root_sha256": anchor["storage_root_sha256"],
        "epoch": anchor["epoch"],
        "head_sha256": anchor["head_sha256"],
    }


def expected_receipt(req: dict[str, Any], request_hash: str) -> dict[str, Any]:
    return {
        "decision": "APPROVED_EXPLICIT_RECOVERY",
        "device_ek_sha256": req["device_ek_sha256"],
        "previous_storage_root_sha256": None,
        "new_storage_root_sha256": req["storage_root_sha256"],
        "previous_epoch": req["previous_epoch"],
        "next_epoch": req["next_epoch"],
        "previous_head_sha256": req["previous_head_sha256"],
        "next_head_sha256": req["next_head_sha256"],
        "request_sha256": request_hash,
        "nonce": req["nonce"],
        "storage_root_provenance": "CALLER_SUPPLIED_UNATTESTED",
        "policy": POLICY,
    }


def load_journal(journal_path: Path, public_key: Path, anchor: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    state = initial_state(anchor)
    records: list[dict[str, Any]] = []
    previous_record_hash = ZERO_HASH
    seen_nonces: dict[str, dict[str, Any]] = {}
    if not journal_path.exists():
        return state, records, previous_record_hash

    raw = journal_path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise GateError("JOURNAL_TRUNCATED_FINAL_RECORD")
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line:
            raise GateError("JOURNAL_EMPTY_LINE")
        try:
            record = json.loads(line, object_pairs_hook=reject_duplicate_json_keys)
        except DuplicateJSONKeyError as exc:
            raise GateError(f"JOURNAL_DUPLICATE_KEY_LINE_{line_number}") from exc
        except Exception as exc:
            raise GateError(f"JOURNAL_JSON_INVALID_LINE_{line_number}") from exc
        if not isinstance(record, dict):
            raise GateError("JOURNAL_RECORD_NOT_OBJECT")
        if line + b"\n" != canonical(record):
            raise GateError("JOURNAL_RECORD_NOT_CANONICAL")
        required = {
            "sequence", "previous_record_sha256", "request", "request_sha256",
            "receipt", "receipt_signature_b64", "record_sha256",
        }
        if set(record) != required:
            raise GateError("JOURNAL_RECORD_SCHEMA_INVALID")
        claimed_record_hash = validate_hash(record["record_sha256"], "JOURNAL_RECORD_HASH_INVALID")
        body = {key: value for key, value in record.items() if key != "record_sha256"}
        actual_record_hash = sha256(canonical(body))
        if actual_record_hash != claimed_record_hash:
            raise GateError("JOURNAL_RECORD_HASH_MISMATCH")
        if record["previous_record_sha256"] != previous_record_hash:
            raise GateError("JOURNAL_CHAIN_MISMATCH")

        req = record["request"]
        if not isinstance(req, dict):
            raise GateError("JOURNAL_REQUEST_INVALID")
        request_hash = sha256(canonical(req))
        if record["request_sha256"] != request_hash:
            raise GateError("JOURNAL_REQUEST_HASH_MISMATCH")
        nonce = req.get("nonce")
        if nonce in seen_nonces:
            raise GateError("JOURNAL_DUPLICATE_NONCE")
        validate_request(req, state)
        if record["sequence"] != req["next_epoch"]:
            raise GateError("JOURNAL_SEQUENCE_MISMATCH")

        receipt = record["receipt"]
        if not isinstance(receipt, dict):
            raise GateError("JOURNAL_RECEIPT_INVALID")
        expected = expected_receipt(req, request_hash)
        expected["previous_storage_root_sha256"] = state["storage_root_sha256"]
        if receipt != expected:
            raise GateError("JOURNAL_RECEIPT_MISMATCH")
        try:
            signature = base64.b64decode(record["receipt_signature_b64"], validate=True)
        except Exception as exc:
            raise GateError("JOURNAL_SIGNATURE_ENCODING_INVALID") from exc
        if not openssl_verify(public_key, canonical(receipt), signature):
            raise GateError("JOURNAL_RECEIPT_SIGNATURE_INVALID")

        state = {
            "device_ek_sha256": req["device_ek_sha256"],
            "storage_root_sha256": req["storage_root_sha256"],
            "epoch": req["next_epoch"],
            "head_sha256": req["next_head_sha256"],
        }
        records.append(record)
        seen_nonces[nonce] = record
        previous_record_hash = claimed_record_hash
    return state, records, previous_record_hash


def append_durable(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise GateError("JOURNAL_APPEND_FAILED")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    dir_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)



def validate_distinct_paths(args: argparse.Namespace) -> None:
    """Reject path aliases before opening the lock or mutating any file.

    resolve() catches lexical and symlink aliases; samefile() additionally catches
    existing hard links. This is a caller-path safety guard, not protection from a
    hostile process racing filesystem changes after validation.
    """
    names = (
        "anchor", "anchor_signature", "public_key", "private_key",
        "journal", "lock", "request", "response", "response_signature",
    )
    seen: list[tuple[str, Path, Path]] = []
    for name in names:
        path = getattr(args, name)
        try:
            resolved = path.resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            raise GateError("PATH_RESOLUTION_FAILED") from exc
        for prior_name, prior_path, prior_resolved in seen:
            aliases = resolved == prior_resolved
            if not aliases:
                try:
                    aliases = path.exists() and prior_path.exists() and os.path.samefile(path, prior_path)
                except OSError:
                    aliases = False
            if aliases:
                raise GateError(f"PATH_ALIAS:{prior_name}:{name}")
        seen.append((name, path, resolved))



def process_request(args: argparse.Namespace) -> int:
    validate_distinct_paths(args)
    lock_path: Path = args.lock
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock_stream:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX)
        anchor, anchor_raw = read_json(args.anchor)
        if not openssl_verify(args.public_key, anchor_raw, args.anchor_signature.read_bytes()):
            raise GateError("ANCHOR_SIGNATURE_INVALID")
        if anchor_raw != canonical(anchor):
            raise GateError("ANCHOR_NOT_CANONICAL")
        anchor = validate_anchor(anchor)
        state, records, previous_record_hash = load_journal(args.journal, args.public_key, anchor)

        req, req_raw = read_json(args.request)
        if req_raw != canonical(req):
            raise GateError("REQUEST_NOT_CANONICAL")
        request_hash = sha256(canonical(req))
        nonce = req.get("nonce")
        for record in records:
            if record["request"].get("nonce") == nonce:
                if record["request_sha256"] != request_hash:
                    raise GateError("NONCE_REUSE_DIFFERENT_REQUEST")
                receipt = record["receipt"]
                signature = base64.b64decode(record["receipt_signature_b64"], validate=True)
                atomic_write(args.response, canonical(receipt))
                atomic_write(args.response_signature, signature)
                print("IDEMPOTENT_RECEIPT_REPLAY")
                return 0

        if args.test_delay_after_lock_ms:
            time.sleep(args.test_delay_after_lock_ms / 1000.0)

        validate_request(req, state)
        receipt = expected_receipt(req, request_hash)
        receipt["previous_storage_root_sha256"] = state["storage_root_sha256"]
        signature = openssl_sign(args.private_key, canonical(receipt))
        body = {
            "sequence": req["next_epoch"],
            "previous_record_sha256": previous_record_hash,
            "request": req,
            "request_sha256": request_hash,
            "receipt": receipt,
            "receipt_signature_b64": base64.b64encode(signature).decode("ascii"),
        }
        record = dict(body)
        record["record_sha256"] = sha256(canonical(body))
        append_durable(args.journal, canonical(record))

        # Simulates process death after the durable commit but before the caller
        # receives/writes the receipt. A retry must return the exact stored bytes.
        if args.crash_after_commit:
            return 99

        atomic_write(args.response, canonical(receipt))
        atomic_write(args.response_signature, signature)
        print(f"APPROVED epoch={req['next_epoch']} record={record['record_sha256']}")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in (
        "anchor", "anchor-signature", "public-key", "private-key", "journal",
        "lock", "request", "response", "response-signature",
    ):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--test-delay-after-lock-ms", type=int, default=0)
    parser.add_argument("--crash-after-commit", action="store_true")
    args = parser.parse_args()
    if args.test_delay_after_lock_ms < 0 or args.test_delay_after_lock_ms > 2000:
        print("REJECT TEST_DELAY_OUT_OF_RANGE")
        return 3
    try:
        return process_request(args)
    except GateError as exc:
        print("REJECT " + exc.code)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
