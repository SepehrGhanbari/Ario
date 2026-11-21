"""W42 baseline-only diagnostics: same-file in-place writes during bounded reads.

Synthetic temporary JSONL and receipt data only; never live Ario ledger.
An xfail is a verified vulnerability observation, NOT proof of safety.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from research.w38_receipt_fd_guard import read_bounded_regular
from ledger_observation_adapter import observe_ledger


def _event(status: str) -> bytes:
    return (json.dumps({
        "event": "TASK_STARTED", "timestamp": "2026-11-21T00:00:00Z",
        "task_id": "synthetic-w42", "status": status,
    }, separators=(',', ':')).encode() + b'\n')


def test_uncontended_read_preserves_exact_bytes(tmp_path):
    file = tmp_path / 'receipt'
    expected = b'W42-PUBLIC-SYNTHETIC\r\n\x00file\n'
    file.write_bytes(expected)
    assert read_bounded_regular(file, len(expected)) == expected
    assert file.read_bytes() == expected


@pytest.mark.skipif(os.name != 'posix', reason='POSIX deterministic native two-read injection')
def test_posix_inplace_torn_jsonl_is_not_accepted(tmp_path):
    """Perform two *real os.read calls* with a same-inode write in between."""
    file = tmp_path / 'synthetic.jsonl'
    first_old, second_old = _event('AAAA'), _event('BBBB')
    first_new, second_new = _event('CCCC'), _event('DDDD')
    before, after = first_old + second_old, first_new + second_new
    assert len(before) == len(after)
    file.write_bytes(before)
    inode = file.stat().st_ino
    real_fdopen = os.fdopen
    read_triggers = []

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
            if not read_triggers:
                # This simulates an interrupted large read using two actual
                # native reads on the existing open file descriptor.
                initial = os.read(self.stream.fileno(), len(first_old))
                assert initial == first_old
                with file.open('r+b') as writer:
                    writer.write(after)
                    writer.flush()
                    os.fsync(writer.fileno())
                read_triggers.append('SAME_INODE_WRITE_BETWEEN_REAL_READS')
                rest = os.read(self.stream.fileno(), amount - len(initial))
                return initial + rest
            return self.stream.read(amount)

    def hooked_fdopen(fd, mode='r', *args, **kwargs):
        stream = real_fdopen(fd, mode, *args, **kwargs)
        if mode == 'rb' and os.fstat(stream.fileno()).st_ino == inode:
            return InjectedRead(stream)
        return stream

    with patch('os.fdopen', side_effect=hooked_fdopen):
        result = observe_ledger(file)
    mixed = first_old + second_new
    assert read_triggers == ['SAME_INODE_WRITE_BETWEEN_REAL_READS']
    assert file.stat().st_ino == inode
    assert file.read_bytes() == after
    if result['status'] == 'OBSERVED':
        assert result['sha256'] == hashlib.sha256(mixed).hexdigest()
        assert result['event_count'] == 2
        pytest.xfail('W42_VERIFIED_RED_POSIX: accepted a mixed two-read JSONL image')
    assert result['status'] == 'UNKNOWN'
    assert not result['observations']


@pytest.mark.skipif(os.name != 'nt', reason='Windows native share-mode experiment')
def test_windows_existing_writer_must_preclude_snapshot(tmp_path):
    """Old W41 leaf share-all admits writer; W42 should fail closed."""
    file = tmp_path / 'synthetic-receipt'
    old = b'W42-PUBLIC-SYNTHETIC' * 3
    file.write_bytes(old)
    observed = None
    rejected = None
    with file.open('r+b') as writer:
        writer.seek(0)
        try:
            observed = read_bounded_regular(file, len(old))
        except (OSError, ValueError) as exc:
            rejected = exc
        assert writer.writable()
    if observed is not None:
        assert observed == old
        pytest.xfail('W42_VERIFIED_RED_WINDOWS: reader opened with live writable handle')
    assert rejected is not None


@pytest.mark.skipif(os.name != 'nt', reason='Windows native share-mode experiment')
def test_windows_new_writer_blocked_while_leaf_handle_held(tmp_path, monkeypatch):
    """Intercept a real ReadFile so a competing writer tries opening at read."""
    import ctypes

    path = tmp_path / 'synthetic-receipt'
    expected = b'W42-IMMUTABLE-DURING-WIN32-READ'
    path.write_bytes(expected)
    actual_dll = ctypes.WinDLL
    attempts = []

    class ReadIntercept:
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
            if not attempts:
                try:
                    with path.open('r+b') as writer:
                        writer.seek(0)
                        writer.write(b'CHANGED')
                    attempts.append('WRITER_OPENED_WHILE_READER_HELD')
                except OSError:
                    attempts.append('WRITER_REFUSED_WHILE_READER_HELD')
            return self.fn(*args)

    class DllProxy:
        def __init__(self, dll):
            self.dll = dll
            self.read = ReadIntercept(dll.ReadFile)
        def __getattr__(self, name):
            return self.read if name == 'ReadFile' else getattr(self.dll, name)

    def factory(name, *args, **kwargs):
        lib = actual_dll(name, *args, **kwargs)
        return DllProxy(lib) if str(name).lower() == 'kernel32' else lib

    monkeypatch.setattr(ctypes, 'WinDLL', factory)
    returned = read_bounded_regular(path, len(expected))
    assert attempts == ['WRITER_REFUSED_WHILE_READER_HELD'], attempts
    assert returned == expected
    assert path.read_bytes() == expected
