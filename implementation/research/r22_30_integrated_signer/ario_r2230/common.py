"""Shared canonical encoding, durable-file and process helpers.

The durable-write routine is intentionally boring: write a temporary file in
the destination directory, fsync it, rename it, then fsync the directory.  A
caller never treats a partially written file as a committed record.
"""

from __future__ import annotations

import contextlib
import errno
import fcntl
import hashlib
import json
import os
import pwd
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Iterator

PROFILE_PREFIX = "ARIO-R22.30"


class LabError(RuntimeError):
    """A bounded research-lab failure, never an accepted signing result."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_object(value: Any) -> str:
    return sha256_hex(canonical_bytes(value))


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LabError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_loads(raw: bytes, *, canonical: bool = True) -> Any:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LabError(f"invalid JSON: {exc}") from exc
    if canonical and canonical_bytes(value) != raw:
        raise LabError("non-canonical JSON encoding")
    return value


def read_bytes(path: Path, *, limit: int = 2 * 1024 * 1024) -> bytes:
    try:
        with path.open("rb") as handle:
            raw = handle.read(limit + 1)
    except OSError as exc:
        raise LabError(f"cannot read {path}: {exc}") from exc
    if len(raw) > limit:
        raise LabError(f"oversized file: {path}")
    return raw


def read_json(path: Path, *, canonical: bool = True) -> Any:
    return strict_loads(read_bytes(path), canonical=canonical)


def _optional_chown(path: Path, uid: int | None, gid: int | None) -> None:
    if uid is None and gid is None:
        return
    try:
        os.chown(path, -1 if uid is None else uid, -1 if gid is None else gid)
    except PermissionError:
        pass


def atomic_write(
    path: Path,
    data: bytes | Any,
    *,
    mode: int = 0o640,
    uid: int | None = None,
    gid: int | None = None,
) -> None:
    """Durably replace ``path`` with canonical JSON or raw bytes."""
    payload = canonical_bytes(data) if not isinstance(data, (bytes, bytearray)) else bytes(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".tmp-", dir=str(path.parent))
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, mode)
        _optional_chown(temp, uid, gid)
        os.replace(temp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temp.unlink()


@contextlib.contextmanager
def file_lock(
    path: Path,
    *,
    mode: int = 0o660,
    uid: int | None = None,
    gid: int | None = None,
    blocking: bool = True,
) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, mode)
    try:
        os.fchmod(fd, mode)
        if uid is not None or gid is not None:
            try:
                os.fchown(fd, -1 if uid is None else uid, -1 if gid is None else gid)
            except PermissionError:
                pass
        flags = fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB
        fcntl.flock(fd, flags)
        yield
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def make_private_dir(path: Path, uid: int, gid: int, mode: int = 0o700) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, mode)
    os.chown(path, uid, gid)


def make_shared_dir(path: Path, gid: int, mode: int = 0o2770) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, mode)
    os.chown(path, 0, gid)


def run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 60,
    check: bool = True,
    input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    try:
        result = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            env=merged_env,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise LabError(f"missing executable: {argv[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise LabError(f"timeout running {argv[0]}") from exc
    if check and result.returncode != 0:
        raise LabError(
            f"command failed ({result.returncode}): {' '.join(argv)}\n"
            f"stdout={result.stdout.decode('utf-8', 'replace')}\n"
            f"stderr={result.stderr.decode('utf-8', 'replace')}"
        )
    return result


def run_ok(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 60,
) -> bool:
    try:
        result = run(argv, cwd=cwd, env=env, timeout=timeout, check=False)
    except LabError:
        return False
    return result.returncode == 0


def setpriv(
    uid: int,
    gid: int,
    supplementary: list[int],
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 120,
    check: bool = True,
    input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    command = [
        "setpriv",
        f"--reuid={uid}",
        f"--regid={gid}",
        "--clear-groups",
    ]
    if supplementary:
        command.append("--groups=" + ",".join(str(item) for item in supplementary))
    command.extend(argv)
    return run(
        command,
        cwd=cwd,
        env=env,
        timeout=timeout,
        check=check,
        input_bytes=input_bytes,
    )


def wait_for_socket(path: Path, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            try:
                import socket

                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                    client.settimeout(0.2)
                    client.connect(str(path))
                return
            except OSError:
                pass
        time.sleep(0.05)
    raise LabError(f"socket did not become ready: {path}")


def log(message: str) -> None:
    print(message, flush=True)


def log_json(event: str, **fields: Any) -> None:
    log("RESULT " + json.dumps({"event": event, **fields}, sort_keys=True))


def rpc_call(socket_path: Path, request: dict[str, Any], *, timeout: float = 60.0) -> dict[str, Any]:
    import socket

    raw = canonical_bytes(request) + b"\n"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect(str(socket_path))
        client.sendall(raw)
        client.shutdown(socket.SHUT_WR)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = client.recv(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > 2 * 1024 * 1024:
                raise LabError("RPC response too large")
            chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise LabError("empty RPC response")
    return strict_loads(data)


def peer_uid(sock: Any) -> int:
    import socket
    import struct

    raw = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    _pid, uid, _gid = struct.unpack("3i", raw)
    return uid


def new_request_id() -> str:
    return "req-" + uuid.uuid4().hex


def user_ids() -> dict[str, int]:
    result: dict[str, int] = {}
    for name in ("ario2230signer", "ario2230policy", "ario2230founder", "ario2230ario",
                 "ario2230w1", "ario2230w2", "ario2230w3", "ario2230pub"):
        try:
            result[name] = pwd.getpwnam(name).pw_uid
        except KeyError as exc:
            raise LabError(f"required disposable user is missing: {name}") from exc
    return result


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
