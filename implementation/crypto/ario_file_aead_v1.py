"""Ario per-file authenticated encryption / integrity RESEARCH sample (v1).

No keys are loaded or persisted. Do not replace original append-only ledgers.
Separate content and anchor keys are supplied explicitly by test-only callers.
This module does NOT authenticate real custodians or authorize Ario signing.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import secrets
import stat

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

FORMAT = "ARIO-AEAD-INDIVIDUAL-FILE-RESEARCH-V1"
RECEIPT = "ARIO-EXTERNAL-ANCHOR-RESEARCH-V1"
ROOT = "ARIO-COLLECTION-COMMITMENT-RESEARCH-V1"
ALLOWED_CLASSES = (
    "conversation-history", "research-evidence", "public-document", "other"
)

class Refuse(ValueError):
    """An explicit, fail-closed research check failed."""


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def unb64(value: str) -> bytes:
    if not isinstance(value, str):
        raise Refuse("MALFORMED_BASE64")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise Refuse("MALFORMED_BASE64") from exc
    if b64(raw) != value:
        raise Refuse("NONCANONICAL_BASE64")
    return raw


def validate_path(path: str) -> str:
    if not isinstance(path, str) or not path or "\\" in path or "\x00" in path:
        raise Refuse("INVALID_LOGICAL_PATH")
    p = PurePosixPath(path)
    if (p.is_absolute() or p.as_posix() != path or
            any(part in ("", ".", "..") for part in path.split("/"))):
        raise Refuse("INVALID_LOGICAL_PATH")
    return path


def validate_class(content_class: str) -> str:
    if content_class not in ALLOWED_CLASSES:
        raise Refuse("UNKNOWN_CONTENT_CLASS")
    return content_class


def require_key(key: bytes, role: str) -> None:
    if not isinstance(key, bytes) or len(key) != 32:
        raise Refuse("INVALID_" + role)


def file_key(master: bytes, salt: bytes, path: str, content_class: str) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt,
                info=canonical(["Ario v1 file", path, content_class])).derive(master)


def seal_file(data: bytes, path: str, content_class: str, generation: int,
              content_master_key: bytes, independent_anchor_key: bytes
              ) -> tuple[bytes, bytes]:
    """Return ciphertext envelope and separately keyed HMAC receipt, in memory."""
    require_key(content_master_key, "CONTENT_MASTER_KEY")
    require_key(independent_anchor_key, "INDEPENDENT_ANCHOR_KEY")
    if content_master_key == independent_anchor_key:
        raise Refuse("KEY_ROLE_REUSE")
    if not isinstance(data, bytes):
        raise Refuse("FILE_CONTENT_MUST_BE_BYTES")
    validate_path(path)
    validate_class(content_class)
    if type(generation) is not int or generation < 1:
        raise Refuse("INVALID_GENERATION")
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    header = {"format": FORMAT, "path": path, "class": content_class,
              "generation": generation, "salt": b64(salt), "nonce": b64(nonce)}
    encrypted = AESGCM(file_key(content_master_key, salt, path, content_class)).encrypt(
        nonce, data, canonical(header))
    envelope = canonical({"header": header, "ciphertext": b64(encrypted)})
    receipt_core = {"format": RECEIPT, "path": path, "class": content_class,
                    "generation": generation, "envelope_sha256": sha256(envelope)}
    proof = hmac.new(independent_anchor_key, canonical(receipt_core), hashlib.sha256).hexdigest()
    receipt = canonical({**receipt_core, "hmac_sha256": proof})
    return envelope, receipt


def open_file(envelope: bytes, receipt: bytes, expected_path: str,
              expected_class: str, expected_generation: int,
              content_master_key: bytes, independent_anchor_key: bytes) -> bytes:
    """Refuse to decrypt unless receipt, metadata, generation and AEAD verify."""
    require_key(content_master_key, "CONTENT_MASTER_KEY")
    require_key(independent_anchor_key, "INDEPENDENT_ANCHOR_KEY")
    validate_path(expected_path)
    validate_class(expected_class)
    if type(expected_generation) is not int or expected_generation < 1:
        raise Refuse("INVALID_GENERATION")
    try:
        proof = json.loads(receipt)
        box = json.loads(envelope)
        if canonical(proof) != receipt or canonical(box) != envelope:
            raise Refuse("NONCANONICAL_JSON")
        if not isinstance(proof, dict) or not isinstance(box, dict):
            raise Refuse("MALFORMED_ENVELOPE_OR_RECEIPT")
        given = proof["hmac_sha256"]
        core = {key: val for key, val in proof.items() if key != "hmac_sha256"}
        expected_mac = hmac.new(independent_anchor_key, canonical(core),
                                hashlib.sha256).hexdigest()
        if not isinstance(given, str) or not hmac.compare_digest(given, expected_mac):
            raise Refuse("EXTERNAL_RECEIPT_INVALID")
        if core != {"format": RECEIPT, "path": expected_path,
                    "class": expected_class, "generation": expected_generation,
                    "envelope_sha256": sha256(envelope)}:
            raise Refuse("EXTERNAL_RECEIPT_MISMATCH")
        if set(box) != {"header", "ciphertext"}:
            raise Refuse("BAD_ENVELOPE_FORMAT")
        header = box["header"]
        if not isinstance(header, dict) or header.get("format") != FORMAT:
            raise Refuse("BAD_ENVELOPE_FORMAT")
        if set(header) != {"format", "path", "class", "generation", "salt", "nonce"}:
            raise Refuse("MALFORMED_HEADER")
        if (header["path"] != expected_path or header["class"] != expected_class
                or header["generation"] != expected_generation):
            raise Refuse("WRONG_FILE_BINDING")
        salt = unb64(header["salt"])
        nonce = unb64(header["nonce"])
        ciphertext = unb64(box["ciphertext"])
        if len(salt) != 16 or len(nonce) != 12 or len(ciphertext) < 16:
            raise Refuse("BAD_CRYPTO_PARAMETERS")
        return AESGCM(file_key(content_master_key, salt, expected_path, expected_class)).decrypt(
            nonce, ciphertext, canonical(header))
    except Refuse:
        raise
    except InvalidTag as exc:
        raise Refuse("AEAD_AUTHENTICATION_FAILED") from exc
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeError,
            OverflowError, RecursionError) as exc:
        # Deeply nested untrusted JSON is a refused input, not an
        # uncaught parser exception or a reason to continue.
        raise Refuse("MALFORMED_ENVELOPE_OR_RECEIPT") from exc


def collection_receipt(receipts: dict[str, bytes], anchor_key: bytes,
                       generation: int) -> bytes:
    """Collection commitment; its authentic latest version MUST be pinned elsewhere."""
    require_key(anchor_key, "INDEPENDENT_ANCHOR_KEY")
    if type(generation) is not int or generation < 1 or not receipts:
        raise Refuse("INVALID_COLLECTION")
    items = []
    for path, receipt in sorted(receipts.items()):
        validate_path(path)
        items.append({"path": path, "receipt_sha256": sha256(receipt)})
    body = {"format": ROOT, "generation": generation, "files": items}
    proof = hmac.new(anchor_key, canonical(body), hashlib.sha256).hexdigest()
    return canonical({**body, "hmac_sha256": proof})


def verify_collection(receipts: dict[str, bytes], root: bytes,
                      anchor_key: bytes, expected_generation: int) -> None:
    expected = collection_receipt(receipts, anchor_key, expected_generation)
    if not hmac.compare_digest(expected, root):
        raise Refuse("COLLECTION_ROOT_MISMATCH")


@dataclass(frozen=True)
class LocalIntegrityBaseline:
    """Unkeyed full-byte digest: detects drift, not independently authorized history.

    Rechecks are NOT atomic with a future append; the containing directory
    must be trusted and controlled by one writer. No independent attestation.
    """
    device: int
    inode: int
    byte_count: int
    content_sha256: str

    @classmethod
    def capture(cls, path: Path) -> "LocalIntegrityBaseline":
        """Hash a local regular file in bounded chunks; NOT an external anchor."""
        p = Path(path)
        if p.is_symlink():
            raise Refuse("LEDGER_SYMLINK")
        fd = os.open(str(p), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                     | getattr(os, "O_BINARY", 0))
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise Refuse("LEDGER_NOT_PRIVATE_REGULAR_FILE")
            digest = hashlib.sha256()
            total = 0
            with os.fdopen(os.dup(fd), "rb") as stream:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
                    total += len(chunk)
            after = os.fstat(fd)
            if ((before.st_dev, before.st_ino, before.st_size) !=
                    (after.st_dev, after.st_ino, after.st_size)
                    or total != after.st_size):
                raise Refuse("LEDGER_CHANGED_DURING_READ")
            return cls(after.st_dev, after.st_ino, total, digest.hexdigest())
        finally:
            os.close(fd)

    def verify_before_append(self, path: Path) -> None:
        """Recheck bounded local drift; excludes neither races nor rollback."""
        other = type(self).capture(path)
        if (self.device, self.inode) != (other.device, other.inode):
            raise Refuse("LEDGER_REPLACED")
        if self.byte_count != other.byte_count:
            raise Refuse("LEDGER_SIZE_CHANGED")
        if not hmac.compare_digest(self.content_sha256, other.content_sha256):
            raise Refuse("LEDGER_SAME_SIZE_BYTES_MUTATED")
