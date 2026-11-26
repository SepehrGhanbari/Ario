#!/usr/bin/env python3
"""Ario's synthetic C2SP transparency-log client for the Markovian research witness.

RESEARCH_ONLY. It reuses the already-created, encrypted Kladje research identity.
It never generates, prints, uploads, or commits private-key material. The bundle
contains only a synthetic memory capsule and public C2SP artifacts.

The C2SP note/vkey and tlog-witness framing follow:
  https://c2sp.org/signed-note
  https://c2sp.org/tlog-checkpoint
  https://c2sp.org/tlog-cosignature
  https://c2sp.org/tlog-witness
"""
from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import hmac
import json
import os
import re
import stat
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

ORIGIN = "github.com/SepehrGhanbari/Ario/kladje-test-v1"
DEFAULT_KEY_PATH = Path.home() / "Ario-Kladje-Research-v1" / "research-log.private.pem"
DEFAULT_BUNDLE_PATH = Path.home() / "Ario-Markovian-Test-v1"
WITNESS_NAME = "markovianprotocol.com/witness"
WITNESS_VKEY = (
    "markovianprotocol.com/witness+41b8827f+"
    "BJKLl8rBYM0oUxSaWh9rjTldTprEpYj/SWVIGgacA9XC"
)
WITNESS_SUBMIT_URL = "https://witness.markovianprotocol.com/add-checkpoint"
WITNESS_MONITOR_BASE = "https://witness.markovianprotocol.com"
USER_AGENT = "markovian-log/1.0 (+https://markovianprotocol.com/log; c2sp tlog-witness submit)"
CAPSULE_FORMAT = "ario.synthetic-memory-capsule.v1"
LEAF_FORMAT = "ario.external-witness.synthetic-record.v1"
SCOPE = "RESEARCH_ONLY"
MAX_KEY_FILE = 16 * 1024
MAX_BUNDLE_FILE = 4 * 1024 * 1024
_HEX8 = re.compile(r"[0-9a-f]{8}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_SIGTYPE_LOG = 0x01
_SIGTYPE_COSIGN = 0x04
_EM_DASH = "—"


class Hold(RuntimeError):
    """Fail-closed result for invalid or incomplete research evidence."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as exc:
        raise Hold("HOLD_NONCANONICAL_JSON") from exc


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Hold("HOLD_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def parse_canonical_json(data: bytes, *, max_bytes: int = MAX_BUNDLE_FILE) -> Any:
    if type(data) is not bytes or not data or len(data) > max_bytes:
        raise Hold("HOLD_JSON_SIZE")
    try:
        value = json.loads(
            data.decode("ascii", errors="strict"),
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=lambda _: (_ for _ in ()).throw(Hold("HOLD_JSON_CONSTANT")),
        )
    except Hold:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise Hold("HOLD_INVALID_JSON") from exc
    if canonical_json(value) != data:
        raise Hold("HOLD_JSON_NOT_CANONICAL")
    return value


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(text: str, label: str) -> bytes:
    if type(text) is not str:
        raise Hold(f"HOLD_{label}_BASE64_TYPE")
    try:
        raw = base64.b64decode(text, validate=True)
    except (ValueError, TypeError) as exc:
        raise Hold(f"HOLD_{label}_BASE64") from exc
    if _b64(raw) != text:
        raise Hold(f"HOLD_{label}_BASE64_NONCANONICAL")
    return raw


def key_id(name: str, public_key: bytes, sig_type: int) -> bytes:
    if type(name) is not str or not name or "+" in name or any(ch.isspace() for ch in name):
        raise Hold("HOLD_VKEY_NAME")
    if type(public_key) is not bytes or len(public_key) != 32:
        raise Hold("HOLD_VKEY_PUBLIC_KEY")
    return hashlib.sha256(name.encode("utf-8") + b"\n" + bytes([sig_type]) + public_key).digest()[:4]


def make_vkey(name: str, public_key: bytes) -> str:
    kid = key_id(name, public_key, _SIGTYPE_LOG)
    material = bytes([_SIGTYPE_LOG]) + public_key
    return f"{name}+{kid.hex()}+{_b64(material)}"


def parse_vkey(value: str, *, expected_sig_type: int) -> tuple[str, bytes, bytes]:
    if type(value) is not str or value.count("+") < 2:
        raise Hold("HOLD_VKEY_FORMAT")
    name, kid_hex, material_text = value.strip().split("+", 2)
    if not _HEX8.fullmatch(kid_hex):
        raise Hold("HOLD_VKEY_KEY_ID")
    material = _unb64(material_text, "VKEY")
    if len(material) != 33 or material[0] != expected_sig_type:
        raise Hold("HOLD_VKEY_KEY_MATERIAL")
    public_key = material[1:]
    expected = key_id(name, public_key, expected_sig_type)
    if expected.hex() != kid_hex:
        raise Hold("HOLD_VKEY_KEY_ID_MISMATCH")
    return name, expected, public_key


def leaf_hash(data: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + data).digest()


def _node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def _largest_power_of_two_less_than(n: int) -> int:
    if n < 2:
        raise ValueError("n must be >= 2")
    k = 1
    while k * 2 < n:
        k *= 2
    return k


def merkle_tree_hash(leaves: Sequence[bytes]) -> bytes:
    n = len(leaves)
    if n == 0:
        return hashlib.sha256(b"").digest()
    if n == 1:
        return leaf_hash(leaves[0])
    k = _largest_power_of_two_less_than(n)
    return _node_hash(merkle_tree_hash(leaves[:k]), merkle_tree_hash(leaves[k:]))


def consistency_proof(leaves: Sequence[bytes], first_size: int) -> list[bytes]:
    second_size = len(leaves)
    if not 0 < first_size <= second_size:
        raise ValueError("require 0 < first_size <= len(leaves)")

    def subproof(m: int, subset: Sequence[bytes], complete: bool) -> list[bytes]:
        n = len(subset)
        if m == n:
            return [] if complete else [merkle_tree_hash(subset)]
        k = _largest_power_of_two_less_than(n)
        if m <= k:
            return subproof(m, subset[:k], complete) + [merkle_tree_hash(subset[k:])]
        return subproof(m - k, subset[k:], False) + [merkle_tree_hash(subset[:k])]

    return subproof(first_size, leaves, True)


def verify_consistency(first_size: int, second_size: int, proof: Sequence[bytes],
                       first_root: bytes, second_root: bytes) -> bool:
    if first_size <= 0 or first_size > second_size:
        return False
    if first_size == second_size:
        return not proof and hmac.compare_digest(first_root, second_root)
    path = list(proof)
    if first_size & (first_size - 1) == 0:
        path = [first_root] + path
    if not path:
        return False
    fn, sn = first_size - 1, second_size - 1
    while fn & 1:
        fn >>= 1
        sn >>= 1
    fr = sr = path[0]
    for node in path[1:]:
        if sn == 0:
            return False
        if (fn & 1) == 1 or fn == sn:
            fr = _node_hash(node, fr)
            sr = _node_hash(node, sr)
            if (fn & 1) == 0:
                while (fn & 1) == 0 and fn != 0:
                    fn >>= 1
                    sn >>= 1
        else:
            sr = _node_hash(sr, node)
        fn >>= 1
        sn >>= 1
    return fn == 0 and hmac.compare_digest(fr, first_root) and hmac.compare_digest(sr, second_root)


def checkpoint_note(origin: str, tree_size: int, root: bytes) -> bytes:
    if type(origin) is not str or not origin or "+" in origin or any(ch.isspace() for ch in origin):
        raise Hold("HOLD_CHECKPOINT_ORIGIN")
    if type(tree_size) is not int or isinstance(tree_size, bool) or tree_size < 0:
        raise Hold("HOLD_CHECKPOINT_SIZE")
    if type(root) is not bytes or len(root) != 32:
        raise Hold("HOLD_CHECKPOINT_ROOT")
    return f"{origin}\n{tree_size}\n{_b64(root)}\n".encode("utf-8")


def sign_checkpoint(origin: str, leaves: Sequence[bytes], signer: Ed25519PrivateKey) -> bytes:
    public = signer.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    note_text = checkpoint_note(origin, len(leaves), merkle_tree_hash(leaves))
    signature = signer.sign(note_text)
    payload = key_id(origin, public, _SIGTYPE_LOG) + signature
    return note_text + b"\n" + f"{_EM_DASH} {origin} {_b64(payload)}\n".encode("utf-8")


def parse_checkpoint(note: bytes) -> dict[str, Any]:
    if type(note) is not bytes or not note or len(note) > 64 * 1024:
        raise Hold("HOLD_CHECKPOINT_SIZE_BYTES")
    try:
        text = note.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise Hold("HOLD_CHECKPOINT_UTF8") from exc
    if "\r" in text or not text.endswith("\n") or "\n\n" not in text:
        raise Hold("HOLD_CHECKPOINT_FRAMING")
    note_text, signature_block = text.split("\n\n", 1)
    note_text += "\n"
    body_lines = note_text.split("\n")
    if len(body_lines) != 4 or not all(body_lines[:3]):
        raise Hold("HOLD_CHECKPOINT_BODY")
    origin, size_text, root_text = body_lines[:3]
    if not size_text.isascii() or not size_text.isdigit() or (size_text != "0" and size_text.startswith("0")):
        raise Hold("HOLD_CHECKPOINT_SIZE_ENCODING")
    root = _unb64(root_text, "CHECKPOINT_ROOT")
    if len(root) != 32:
        raise Hold("HOLD_CHECKPOINT_ROOT_LENGTH")
    signatures = []
    for line in signature_block.splitlines():
        if not line.startswith(_EM_DASH + " "):
            raise Hold("HOLD_CHECKPOINT_SIGNATURE_LINE")
        parts = line[2:].split(" ", 1)
        if len(parts) != 2 or not parts[0]:
            raise Hold("HOLD_CHECKPOINT_SIGNATURE_LINE")
        signatures.append((parts[0], _unb64(parts[1], "CHECKPOINT_SIGNATURE")))
    if not signatures:
        raise Hold("HOLD_CHECKPOINT_NO_SIGNATURES")
    return {
        "origin": origin,
        "tree_size": int(size_text),
        "root": root,
        "note_text": note_text.encode("utf-8"),
        "signatures": signatures,
    }


def verify_log_checkpoint(note: bytes, log_vkey: str) -> dict[str, Any]:
    name, kid, public = parse_vkey(log_vkey, expected_sig_type=_SIGTYPE_LOG)
    parsed = parse_checkpoint(note)
    if parsed["origin"] != name:
        raise Hold("HOLD_CHECKPOINT_VKEY_ORIGIN")
    matches = [blob for sig_name, blob in parsed["signatures"] if sig_name == name and len(blob) >= 4 and blob[:4] == kid]
    if len(matches) != 1 or len(matches[0]) != 68:
        raise Hold("HOLD_LOG_SIGNATURE_MISSING_OR_DUPLICATE")
    try:
        Ed25519PublicKey.from_public_bytes(public).verify(matches[0][4:], parsed["note_text"])
    except (ValueError, InvalidSignature) as exc:
        raise Hold("HOLD_LOG_SIGNATURE_INVALID") from exc
    return parsed


def verify_witness_cosignature_line(note_text: bytes, line: bytes, witness_vkey: str = WITNESS_VKEY) -> dict[str, Any]:
    name, kid, public = parse_vkey(witness_vkey, expected_sig_type=_SIGTYPE_COSIGN)
    try:
        decoded = line.decode("utf-8", errors="strict").strip("\n")
    except UnicodeDecodeError as exc:
        raise Hold("HOLD_WITNESS_COSIGNATURE_UTF8") from exc
    if not decoded.startswith(_EM_DASH + " "):
        raise Hold("HOLD_WITNESS_COSIGNATURE_FORMAT")
    parts = decoded[2:].split(" ", 1)
    if len(parts) != 2 or parts[0] != name:
        raise Hold("HOLD_WITNESS_COSIGNATURE_NAME")
    payload = _unb64(parts[1], "WITNESS_COSIGNATURE")
    if len(payload) != 76 or payload[:4] != kid:
        raise Hold("HOLD_WITNESS_COSIGNATURE_KEY_ID_OR_LENGTH")
    timestamp = int.from_bytes(payload[4:12], "big")
    if timestamp > 2**63 - 1:
        raise Hold("HOLD_WITNESS_COSIGNATURE_TIMESTAMP")
    message = b"cosignature/v1\ntime " + str(timestamp).encode("ascii") + b"\n" + note_text
    try:
        Ed25519PublicKey.from_public_bytes(public).verify(payload[12:], message)
    except (ValueError, InvalidSignature) as exc:
        raise Hold("HOLD_WITNESS_COSIGNATURE_INVALID") from exc
    return {"witness": name, "timestamp": timestamp, "key_id": kid.hex()}


def verify_cosigned_checkpoint(note: bytes, log_vkey: str,
                               witness_vkey: str = WITNESS_VKEY) -> dict[str, Any]:
    parsed = verify_log_checkpoint(note, log_vkey)
    witness_name, witness_kid, _ = parse_vkey(witness_vkey, expected_sig_type=_SIGTYPE_COSIGN)
    matches = []
    for sig_name, blob in parsed["signatures"]:
        if sig_name == witness_name and len(blob) == 76 and blob[:4] == witness_kid:
            matches.append(blob)
    if len(matches) != 1:
        raise Hold("HOLD_WITNESS_COSIGNATURE_MISSING_OR_DUPLICATE")
    line = f"{_EM_DASH} {witness_name} {_b64(matches[0])}\n".encode("utf-8")
    witness = verify_witness_cosignature_line(parsed["note_text"], line, witness_vkey)
    parsed["witness"] = witness
    return parsed


def _read_regular(path: Path, *, max_bytes: int = MAX_BUNDLE_FILE) -> bytes:
    try:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise Hold("HOLD_BUNDLE_FILE_NOT_REGULAR")
        if info.st_size > max_bytes:
            raise Hold("HOLD_BUNDLE_FILE_TOO_LARGE")
        return path.read_bytes()
    except Hold:
        raise
    except OSError as exc:
        raise Hold("HOLD_BUNDLE_FILE_READ") from exc


def _write_new(path: Path, data: bytes) -> None:
    try:
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise Hold("HOLD_OUTPUT_ALREADY_EXISTS") from exc
    except OSError as exc:
        raise Hold("HOLD_OUTPUT_WRITE") from exc


def _write_replace(path: Path, data: bytes) -> None:
    temp = path.with_name(path.name + ".tmp")
    if temp.exists() or temp.is_symlink():
        raise Hold("HOLD_TEMP_FILE_EXISTS")
    try:
        with temp.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    except OSError as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise Hold("HOLD_ATOMIC_REPLACE") from exc


def load_research_key(path: Path, password: bytes) -> Ed25519PrivateKey:
    raw = _read_regular(path, max_bytes=MAX_KEY_FILE)
    try:
        key = serialization.load_pem_private_key(raw, password=password)
    except (TypeError, ValueError) as exc:
        raise Hold("HOLD_RESEARCH_KEY_DECRYPTION") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise Hold("HOLD_RESEARCH_KEY_TYPE")
    return key


def public_vkey_for_signer(signer: Ed25519PrivateKey) -> str:
    public = signer.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return make_vkey(ORIGIN, public)


def synthetic_capsule() -> bytes:
    return canonical_json({
        "format": CAPSULE_FORMAT,
        "scope": SCOPE,
        "synthetic": True,
        "events": [
            {"id": "MCR-SYN-001", "claim": "synthetic memory item alpha", "source": "fixture"},
            {"id": "MCR-SYN-002", "claim": "synthetic memory item beta", "source": "fixture"},
            {"id": "MCR-SYN-003", "claim": "synthetic memory item gamma", "source": "fixture"},
        ],
    })


def synthetic_leaf(sequence: int, capsule: bytes, previous_leaf: bytes | None) -> bytes:
    return canonical_json({
        "format": LEAF_FORMAT,
        "origin": ORIGIN,
        "scope": SCOPE,
        "synthetic": True,
        "experiment": "MCR-01",
        "sequence": sequence,
        "capsule_sha256": sha256(capsule),
        "capsule_bytes": len(capsule),
        "previous_leaf_sha256": sha256(previous_leaf) if previous_leaf is not None else None,
    })


def _manifest(capsule: bytes, entries: bytes, checkpoint: bytes, vkey: str, leaves: Sequence[bytes]) -> bytes:
    parsed = verify_log_checkpoint(checkpoint, vkey)
    value = {
        "format": "ario.markovian-synthetic-log-bundle.v1",
        "origin": ORIGIN,
        "scope": SCOPE,
        "synthetic": True,
        "tree_size": parsed["tree_size"],
        "root_hash_b64": _b64(parsed["root"]),
        "capsule_sha256": sha256(capsule),
        "entries_sha256": sha256(entries),
        "checkpoint_sha256": sha256(checkpoint),
        "vkey": vkey,
        "leaf_count": len(leaves),
    }
    return canonical_json(value) + b"\n"


def _write_bundle_files(out: Path, capsule: bytes, leaves: Sequence[bytes],
                        checkpoint: bytes, vkey: str, *, initial: bool) -> None:
    entries = b"".join(leaf + b"\n" for leaf in leaves)
    manifest = _manifest(capsule, entries, checkpoint, vkey, leaves)
    if initial:
        out.mkdir(parents=True, exist_ok=False)
        (out / "history").mkdir()
        _write_new(out / "capsule.json", capsule + b"\n")
        _write_new(out / "entries", entries)
        _write_new(out / "checkpoint", checkpoint)
        _write_new(out / "vkey.txt", (vkey + "\n").encode("ascii"))
        _write_new(out / "manifest.json", manifest)
        _write_new(out / "history" / "checkpoint-000001", checkpoint)
    else:
        _write_replace(out / "entries", entries)
        _write_replace(out / "checkpoint", checkpoint)
        _write_replace(out / "manifest.json", manifest)


def prepare_bundle(out: Path, signer: Ed25519PrivateKey) -> dict[str, Any]:
    if out.exists() or out.is_symlink():
        raise Hold("HOLD_OUTPUT_ALREADY_EXISTS")
    capsule = synthetic_capsule()
    leaf = synthetic_leaf(1, capsule, None)
    leaves = [leaf]
    checkpoint = sign_checkpoint(ORIGIN, leaves, signer)
    vkey = public_vkey_for_signer(signer)
    _write_bundle_files(out, capsule, leaves, checkpoint, vkey, initial=True)
    return verify_bundle(out)


def _read_bundle(out: Path) -> tuple[bytes, list[bytes], bytes, str, dict[str, Any]]:
    if out.is_symlink() or not out.is_dir():
        raise Hold("HOLD_BUNDLE_DIRECTORY")
    capsule_raw = _read_regular(out / "capsule.json")
    if not capsule_raw.endswith(b"\n"):
        raise Hold("HOLD_CAPSULE_NEWLINE")
    capsule = capsule_raw[:-1]
    entries_raw = _read_regular(out / "entries")
    if not entries_raw.endswith(b"\n"):
        raise Hold("HOLD_ENTRIES_NEWLINE")
    leaves = entries_raw[:-1].split(b"\n")
    if not leaves or any(not item for item in leaves):
        raise Hold("HOLD_ENTRIES_EMPTY_LINE")
    checkpoint = _read_regular(out / "checkpoint", max_bytes=64 * 1024)
    vkey_raw = _read_regular(out / "vkey.txt", max_bytes=4096)
    if not vkey_raw.endswith(b"\n") or b"\n" in vkey_raw[:-1]:
        raise Hold("HOLD_VKEY_FILE_FRAMING")
    try:
        vkey = vkey_raw[:-1].decode("ascii")
    except UnicodeDecodeError as exc:
        raise Hold("HOLD_VKEY_FILE_ENCODING") from exc
    manifest_raw = _read_regular(out / "manifest.json", max_bytes=64 * 1024)
    manifest = parse_canonical_json(manifest_raw[:-1] if manifest_raw.endswith(b"\n") else manifest_raw, max_bytes=64 * 1024)
    if type(manifest) is not dict:
        raise Hold("HOLD_MANIFEST_SCHEMA")
    return capsule, leaves, checkpoint, vkey, manifest


def verify_bundle(out: Path) -> dict[str, Any]:
    capsule, leaves, checkpoint, vkey, manifest = _read_bundle(out)
    expected_manifest_keys = {
        "format", "origin", "scope", "synthetic", "tree_size", "root_hash_b64",
        "capsule_sha256", "entries_sha256", "checkpoint_sha256", "vkey", "leaf_count",
    }
    if set(manifest) != expected_manifest_keys:
        raise Hold("HOLD_MANIFEST_SCHEMA")
    capsule_obj = parse_canonical_json(capsule)
    if (type(capsule_obj) is not dict or capsule_obj.get("format") != CAPSULE_FORMAT
            or capsule_obj.get("scope") != SCOPE or capsule_obj.get("synthetic") is not True):
        raise Hold("HOLD_CAPSULE_SCOPE")
    if type(capsule_obj.get("events")) is not list or len(capsule_obj["events"]) != 3:
        raise Hold("HOLD_CAPSULE_RECORDS")
    parsed = verify_log_checkpoint(checkpoint, vkey)
    if parsed["origin"] != ORIGIN:
        raise Hold("HOLD_ORIGIN_MISMATCH")
    if parsed["tree_size"] != len(leaves) or parsed["root"] != merkle_tree_hash(leaves):
        raise Hold("HOLD_ENTRIES_ROOT_MISMATCH")
    previous = None
    for index, leaf in enumerate(leaves, start=1):
        obj = parse_canonical_json(leaf)
        if (type(obj) is not dict or obj.get("format") != LEAF_FORMAT
                or obj.get("origin") != ORIGIN or obj.get("scope") != SCOPE
                or obj.get("synthetic") is not True or obj.get("sequence") != index
                or obj.get("capsule_sha256") != sha256(capsule)
                or obj.get("capsule_bytes") != len(capsule)
                or obj.get("previous_leaf_sha256") != (sha256(previous) if previous is not None else None)):
            raise Hold("HOLD_SYNTHETIC_LEAF_CHAIN")
        previous = leaf
    entries_raw = b"".join(leaf + b"\n" for leaf in leaves)
    expected = {
        "format": "ario.markovian-synthetic-log-bundle.v1",
        "origin": ORIGIN,
        "scope": SCOPE,
        "synthetic": True,
        "tree_size": len(leaves),
        "root_hash_b64": _b64(parsed["root"]),
        "capsule_sha256": sha256(capsule),
        "entries_sha256": sha256(entries_raw),
        "checkpoint_sha256": sha256(checkpoint),
        "vkey": vkey,
        "leaf_count": len(leaves),
    }
    if manifest != expected:
        raise Hold("HOLD_MANIFEST_BINDING")
    return {
        "origin": ORIGIN,
        "vkey": vkey,
        "tree_size": len(leaves),
        "root_hash_b64": _b64(parsed["root"]),
        "checkpoint_sha256": sha256(checkpoint),
        "capsule_sha256": sha256(capsule),
        "entries_sha256": sha256(entries_raw),
        "bundle": str(out),
    }


def append_synthetic_record(out: Path, signer: Ed25519PrivateKey) -> dict[str, Any]:
    current = verify_bundle(out)
    capsule, leaves, old_checkpoint, vkey, _ = _read_bundle(out)
    if public_vkey_for_signer(signer) != vkey:
        raise Hold("HOLD_SIGNER_DOES_NOT_MATCH_BUNDLE")
    old_size = len(leaves)
    previous = leaves[-1]
    new_leaf = synthetic_leaf(old_size + 1, capsule, previous)
    new_leaves = leaves + [new_leaf]
    parsed_old = verify_log_checkpoint(old_checkpoint, vkey)
    if parsed_old["tree_size"] != old_size or parsed_old["root"] != merkle_tree_hash(leaves):
        raise Hold("HOLD_PREVIOUS_LOCAL_CHECKPOINT")
    proof = consistency_proof(new_leaves, old_size)
    if not verify_consistency(old_size, old_size + 1, proof, parsed_old["root"], merkle_tree_hash(new_leaves)):
        raise Hold("HOLD_LOCAL_CONSISTENCY_SELF_CHECK")
    history = out / "history"
    history.mkdir(exist_ok=True)
    history_path = history / f"checkpoint-{old_size:06d}"
    if not history_path.exists():
        _write_new(history_path, old_checkpoint)
    checkpoint = sign_checkpoint(ORIGIN, new_leaves, signer)
    _write_bundle_files(out, capsule, new_leaves, checkpoint, vkey, initial=False)
    cosigned = out / "checkpoint.cosigned"
    if cosigned.exists():
        archive_path = history / f"checkpoint-cosigned-{old_size:06d}"
        if archive_path.exists():
            raise Hold("HOLD_HISTORY_COSIGNATURE_ALREADY_EXISTS")
        os.replace(cosigned, archive_path)
    return verify_bundle(out)


def build_witness_request(old_size: int, proof: Sequence[bytes], checkpoint: bytes) -> bytes:
    if type(old_size) is not int or isinstance(old_size, bool) or old_size < 0:
        raise Hold("HOLD_WITNESS_OLD_SIZE")
    if len(proof) > 63 or any(type(node) is not bytes or len(node) != 32 for node in proof):
        raise Hold("HOLD_WITNESS_PROOF")
    header = f"old {old_size}\n".encode("ascii")
    proof_lines = b"".join(_b64(node).encode("ascii") + b"\n" for node in proof)
    return header + proof_lines + b"\n" + checkpoint


def _http_get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = response.read(128 * 1024 + 1)
            if len(data) > 128 * 1024:
                raise Hold("HOLD_WITNESS_RESPONSE_TOO_LARGE")
            return data
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return b""
        raise Hold(f"HOLD_WITNESS_READ_HTTP_{exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise Hold("HOLD_WITNESS_READ_NETWORK") from exc


def submit_checkpoint(out: Path, *, witness_url: str = WITNESS_SUBMIT_URL) -> dict[str, Any]:
    result = verify_bundle(out)
    capsule, leaves, checkpoint, log_vkey, _ = _read_bundle(out)
    current = verify_log_checkpoint(checkpoint, log_vkey)
    origin_hash = hashlib.sha256(ORIGIN.encode("utf-8")).hexdigest()
    remote_url = f"{WITNESS_MONITOR_BASE}/{origin_hash}/checkpoint"
    remote_note = _http_get(remote_url)
    if not remote_note:
        old_size, old_root, proof = 0, hashlib.sha256(b"").digest(), []
    else:
        remote = verify_cosigned_checkpoint(remote_note, log_vkey, WITNESS_VKEY)
        old_size, old_root = remote["tree_size"], remote["root"]
        if old_size > len(leaves):
            raise Hold("HOLD_WITNESS_AHEAD_OF_LOCAL_LOG")
        if merkle_tree_hash(leaves[:old_size]) != old_root:
            raise Hold("HOLD_WITNESS_ROOT_NOT_LOCAL_PREFIX")
        if old_size == current["tree_size"]:
            if old_root == current["root"]:
                return {"status": "ALREADY_COSIGNED", **result}
            raise Hold("HOLD_WITNESS_EQUIVOCATION_AT_CURRENT_SIZE")
        if old_size > current["tree_size"]:
            raise Hold("HOLD_LOCAL_CHECKPOINT_BEHIND_WITNESS")
        proof = consistency_proof(leaves, old_size) if old_size > 0 else []
        if old_size > 0 and not verify_consistency(
            old_size, current["tree_size"], proof, old_root, current["root"]
        ):
            raise Hold("HOLD_LOCAL_CONSISTENCY_PROOF")
    body = build_witness_request(old_size, proof, checkpoint)
    request = urllib.request.Request(
        witness_url,
        data=body,
        method="POST",
        headers={"Content-Type": "text/plain; charset=utf-8", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            status = response.getcode()
            cosig = response.read(16 * 1024 + 1)
    except urllib.error.HTTPError as exc:
        response_body = exc.read(4096).decode("utf-8", errors="replace").strip()
        if exc.code == 404:
            raise Hold("HOLD_ORIGIN_NOT_PINNED_BY_MARKOVIAN") from exc
        if exc.code == 409:
            raise Hold("HOLD_WITNESS_STATE_CHANGED_RECHECK_BEFORE_RETRY") from exc
        raise Hold(f"HOLD_WITNESS_SUBMIT_HTTP_{exc.code}: {response_body}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise Hold("HOLD_WITNESS_SUBMIT_NETWORK") from exc
    if status != 200 or len(cosig) > 16 * 1024:
        raise Hold("HOLD_WITNESS_SUBMIT_BAD_RESPONSE")
    verified = verify_witness_cosignature_line(current["note_text"], cosig, WITNESS_VKEY)
    cosigned_note = checkpoint + cosig
    verify_cosigned_checkpoint(cosigned_note, log_vkey, WITNESS_VKEY)
    _write_replace_or_new(out / "witness-cosignature.txt", cosig)
    _write_replace_or_new(out / "checkpoint.cosigned", cosigned_note)
    return {"status": "COSIGNED_AND_VERIFIED", "witness": verified, **result}


def _write_replace_or_new(path: Path, data: bytes) -> None:
    if path.exists():
        _write_replace(path, data)
    else:
        _write_new(path, data)


def package_public_bundle(out: Path) -> Path:
    verify_bundle(out)
    archive_path = out.with_suffix(".zip")
    temp = archive_path.with_name(archive_path.name + ".tmp")
    if temp.exists():
        raise Hold("HOLD_PUBLIC_ZIP_TEMP_EXISTS")
    allowed = ["capsule.json", "entries", "checkpoint", "vkey.txt", "manifest.json"]
    try:
        with zipfile.ZipFile(temp, "x", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in allowed:
                zf.write(out / name, arcname=name)
        os.replace(temp, archive_path)
    except OSError as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise Hold("HOLD_PUBLIC_ZIP_WRITE") from exc
    return archive_path


def _cmd_prepare(args: argparse.Namespace) -> int:
    password = getpass.getpass("Existing Ario research-key passphrase (not displayed): ").encode("utf-8")
    signer = load_research_key(args.key, password)
    result = prepare_bundle(args.out, signer)
    zip_path = package_public_bundle(args.out)
    print("PREPARED — synthetic C2SP log; no network request sent")
    print("origin:", result["origin"])
    print("vkey:", result["vkey"])
    print("tree size:", result["tree_size"])
    print("root hash (base64):", result["root_hash_b64"])
    print("checkpoint SHA-256:", result["checkpoint_sha256"])
    print("public bundle:", zip_path)
    print("private key: remains at its existing local path; not copied to the bundle")
    return 0


def _cmd_append(args: argparse.Namespace) -> int:
    password = getpass.getpass("Existing Ario research-key passphrase (not displayed): ").encode("utf-8")
    signer = load_research_key(args.key, password)
    result = append_synthetic_record(args.bundle, signer)
    zip_path = package_public_bundle(args.bundle)
    print("APPENDED — synthetic record only; no network request sent")
    print("tree size:", result["tree_size"])
    print("root hash (base64):", result["root_hash_b64"])
    print("checkpoint SHA-256:", result["checkpoint_sha256"])
    print("public bundle:", zip_path)
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    result = verify_bundle(args.bundle)
    print("PASS — local synthetic log bundle")
    for key in ("origin", "tree_size", "root_hash_b64", "checkpoint_sha256", "capsule_sha256", "vkey"):
        print(f"{key}: {result[key]}")
    return 0


def _cmd_submit(args: argparse.Namespace) -> int:
    result = submit_checkpoint(args.bundle, witness_url=args.witness_url)
    print(result["status"])
    if result["status"] == "COSIGNED_AND_VERIFIED":
        print("witness:", result["witness"]["witness"])
        print("witness timestamp:", result["witness"]["timestamp"])
        print("saved: checkpoint.cosigned and witness-cosignature.txt")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="sign the first synthetic checkpoint using the existing encrypted research key")
    prepare.add_argument("--key", type=Path, default=DEFAULT_KEY_PATH)
    prepare.add_argument("--out", type=Path, default=DEFAULT_BUNDLE_PATH)
    prepare.set_defaults(func=_cmd_prepare)
    append = sub.add_parser("append", help="append one synthetic record and sign a consistent larger checkpoint")
    append.add_argument("--key", type=Path, default=DEFAULT_KEY_PATH)
    append.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE_PATH)
    append.set_defaults(func=_cmd_append)
    verify = sub.add_parser("verify", help="verify the local public bundle offline")
    verify.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE_PATH)
    verify.set_defaults(func=_cmd_verify)
    submit = sub.add_parser("submit", help="submit the current checkpoint once to Markovian after its operator pins the origin")
    submit.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE_PATH)
    submit.add_argument("--witness-url", default=WITNESS_SUBMIT_URL)
    submit.set_defaults(func=_cmd_submit)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Hold as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except OSError as exc:
        print("HOLD_IO:", type(exc).__name__, str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
