"""W43 research-only negative controls: pre-existing writable mmap and ABA.

Uses disposable synthetic receipt/JSONL bytes only. A reproduced bypass is
explicitly recorded as XFAIL/RED, never described as a security pass.
"""
from __future__ import annotations

import hashlib
import json
import mmap
import os
from unittest.mock import patch

import pytest

from ledger_observation_adapter import observe_ledger
from research.w38_receipt_fd_guard import read_bounded_regular


def _event(status: str) -> bytes:
    return (json.dumps({
        "event": "TASK_STARTED",
        "timestamp": "2026-11-21T00:00:00Z",
        "task_id": "synthetic-w43",
        "status": status,
    }, separators=(",", ":")).encode("utf-8") + b"\n")


def _fingerprint(path):
    s = path.stat()
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def test_w43_uncontended_exact_bytes(tmp_path):
    """Retain an ordinary positive control on both operating systems."""
    path = tmp_path / "w43-public-synthetic-receipt"
    expected = b"W43-PUBLIC-SYNTHETIC\x00\r\n"
    path.write_bytes(expected)
    assert read_bounded_regular(path, len(expected)) == expected


@pytest.mark.skipif(os.name != "posix", reason="POSIX held-FD/mmap interleaving")
def test_w43_posix_mmap_aba_torn_jsonl_not_silently_observed(tmp_path):
    """Two native reads; mutate second line via a primed writable mmap.

    mmap dirty-page bookkeeping may leave fstat timestamps unchanged for
    subsequent stores. If the platform does update them, report SKIP rather
    than pretending to have reproduced this Linux-specific condition.
    """
    path = tmp_path / "w43-synthetic.jsonl"
    first_old, second_old = _event("AAAA"), _event("BBBB")
    second_new = _event("DDDD")
    old = first_old + second_old
    mixed = first_old + second_new
    assert len(second_new) == len(second_old)
    path.write_bytes(old)
    inode = path.stat().st_ino
    offset = len(first_old)
    actual_fdopen = os.fdopen
    triggers = []

    with path.open("r+b") as writer:
        with mmap.mmap(writer.fileno(), len(old), access=mmap.ACCESS_WRITE) as view:
            # Warm the already-mapped page *before* the fstat used by W38.
            # No flush: a flush may rearm Linux's dirty-page timestamp update.
            view[offset:] = second_new
            view[offset:] = second_old
            warmed = _fingerprint(path)
            assert path.read_bytes() == old

            class InjectedRead:
                def __init__(self, stream):
                    self.stream = stream

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return self.stream.__exit__(*args)

                def __getattr__(self, attr):
                    return getattr(self.stream, attr)

                def read(self, amount=-1):
                    if not triggers:
                        first = os.read(self.stream.fileno(), len(first_old))
                        assert first == first_old
                        view[offset:] = second_new
                        triggers.append("MAPPED_WRITE_BETWEEN_TWO_NATIVE_READS")
                        rest = os.read(self.stream.fileno(), amount - len(first))
                        return first + rest
                    second = self.stream.read(amount)
                    view[offset:] = second_old  # ABA before the last fstat
                    triggers.append("MAPPED_RESTORE_BEFORE_FINAL_FSTAT")
                    return second

            def hooked_fdopen(fd, mode="r", *args, **kwargs):
                stream = actual_fdopen(fd, mode, *args, **kwargs)
                if mode == "rb" and os.fstat(stream.fileno()).st_ino == inode:
                    return InjectedRead(stream)
                return stream

            with patch("os.fdopen", side_effect=hooked_fdopen):
                result = observe_ledger(path)

            assert triggers == [
                "MAPPED_WRITE_BETWEEN_TWO_NATIVE_READS",
                "MAPPED_RESTORE_BEFORE_FINAL_FSTAT",
            ]
            assert path.read_bytes() == old
            if _fingerprint(path) != warmed:
                pytest.skip("W43_MMAP_DIRTY_TIMESTAMP_PRECONDITION_NOT_MET")
            if result["status"] == "OBSERVED":
                assert result["sha256"] == hashlib.sha256(mixed).hexdigest()
                assert result["sha256"] != hashlib.sha256(old).hexdigest()
                assert result["event_count"] == 2
                pytest.xfail(
                    "W43_VERIFIED_RED_POSIX: mmap ABA admitted mixed JSONL "
                    "despite matching before/mid/after fstat and repeat reads"
                )
            assert result["status"] == "UNKNOWN"
            assert result["observations"] == []


@pytest.mark.skipif(os.name != "nt", reason="Windows native mmap/ReadFile probe")
def test_w43_windows_preexisting_mapped_view_during_readfile(tmp_path, monkeypatch):
    """A view created before the leaf reader may outlive its writable handle.

    Hook the *real* native ReadFile, not a mocked file-read result.
    A returned transient image is recorded RED. An open rejection is a
    measured refusal, not proof against every mapped or privileged writer.
    """
    import ctypes

    path = tmp_path / "w43-synthetic-receipt"
    old = b"W43-OLD-MAPPED-RECEIPT-AAAAAAAA"
    new = b"W43-NEW-MAPPED-RECEIPT-BBBBBBBB"
    assert len(old) == len(new)
    path.write_bytes(old)
    with path.open("r+b") as writable:
        view = mmap.mmap(writable.fileno(), len(old), access=mmap.ACCESS_WRITE)
    # Writable file HANDLE is closed; the mapped view intentionally persists.
    native_dll = ctypes.WinDLL
    transitions = []

    class Intercept:
        def __init__(self, fn):
            self.fn = fn

        @property
        def argtypes(self):
            return self.fn.argtypes

        @argtypes.setter
        def argtypes(self, value):
            self.fn.argtypes = value

        @property
        def restype(self):
            return self.fn.restype

        @restype.setter
        def restype(self, value):
            self.fn.restype = value

        def __call__(self, *args):
            view[:] = new
            transitions.append("MAPPED_WRITE_DURING_HELD_READ_HANDLE")
            try:
                return self.fn(*args)
            finally:
                view[:] = old
                transitions.append("MAPPED_RESTORE_BEFORE_PATH_RECHECK")

    class DllProxy:
        def __init__(self, dll):
            self.dll = dll
            self.read = Intercept(dll.ReadFile)

        def __getattr__(self, name):
            return self.read if name == "ReadFile" else getattr(self.dll, name)

    def dll_factory(name, *args, **kwargs):
        dll = native_dll(name, *args, **kwargs)
        return DllProxy(dll) if str(name).lower() == "kernel32" else dll

    try:
        monkeypatch.setattr(ctypes, "WinDLL", dll_factory)
        try:
            result = read_bounded_regular(path, len(old))
        except (OSError, ValueError):
            assert not transitions, "reader failed only after mapped mutation"
            return  # Windows rejected the held read before the native ReadFile
        assert transitions == [
            "MAPPED_WRITE_DURING_HELD_READ_HANDLE",
            "MAPPED_RESTORE_BEFORE_PATH_RECHECK",
        ]
        assert path.read_bytes() == old
        if result == new:
            pytest.xfail(
                "W43_VERIFIED_RED_WINDOWS: preexisting mmap changed the "
                "held-handle read and restored bytes before path recheck"
            )
        if result == old:
            pytest.skip("W43_WINDOWS_INTERLEAVING_INCONCLUSIVE")
        pytest.fail("W43_UNEXPECTED_TRANSIENT_OR_TORN_IMAGE")
    finally:
        view.close()
