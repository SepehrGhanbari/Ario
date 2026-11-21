"""W38: controlled read-only receipt path substitutions and exact-byte preservation.

All synthetic payloads and temporary paths. No network, keys or ledger changes.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
from unittest import mock

import pytest

from research.w38_receipt_fd_guard import read_bounded_regular


@pytest.fixture
def box():
    with tempfile.TemporaryDirectory(prefix='ario-w38-') as tmp:
        yield Path(tmp)


def _symlink_or_skip(link: Path, target: Path, *, directory: bool = False):
    try:
        link.symlink_to(target, target_is_directory=directory)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f'symlink unsupported on host: {type(exc).__name__}')


def test_plain_regular_bytes_preserved(box):
    src = box/'receipt'
    data = b'HEADER\r\nsynthetic\x00data\n'
    src.write_bytes(data)
    assert read_bounded_regular(src, len(data)) == data
    assert src.read_bytes() == data


def test_absolute_and_relative_regular_paths(box, monkeypatch):
    root = box/'root'
    root.mkdir()
    src = root/'receipt'
    src.write_bytes(b'known-public')
    monkeypatch.chdir(root)
    assert read_bounded_regular(Path('receipt'), 64) == b'known-public'
    assert read_bounded_regular(src, 64) == b'known-public'


def test_cap_boundary_exact_and_one_byte_over(box):
    src = box/'receipt'
    src.write_bytes(b'A' * 32)
    assert read_bounded_regular(src, 32) == b'A' * 32
    with pytest.raises((OSError, ValueError), match='INPUT_SIZE_LIMIT'):
        read_bounded_regular(src, 31)


@pytest.mark.parametrize('cap', [None, -1, 1.0, True, 17 * 1024 * 1024])
def test_invalid_caps_refused(box, cap):
    src = box/'receipt'
    src.write_bytes(b'safe')
    with pytest.raises(ValueError, match='INVALID_RECEIPT_SIZE_CAP'):
        read_bounded_regular(src, cap)


def test_direct_symlink_refused(box):
    outside = box/'outside'
    outside.write_bytes(b'outside-secret')
    link = box/'link'
    _symlink_or_skip(link, outside)
    with pytest.raises((OSError, ValueError)):
        read_bounded_regular(link, 256)


def test_directory_symlink_refused(box):
    good = box/'good'
    good.mkdir()
    (good/'receipt').write_bytes(b'exact-fixture')
    alias = box/'alias'
    _symlink_or_skip(alias, good, directory=True)
    with pytest.raises((OSError, ValueError)):
        read_bounded_regular(alias/'receipt', 256)


def test_missing_and_directory_leaf_refused(box):
    with pytest.raises((OSError, ValueError)):
        read_bounded_regular(box/'missing', 256)
    with pytest.raises((OSError, ValueError)):
        read_bounded_regular(box, 256)


@pytest.mark.skipif(os.name != 'posix', reason='POSIX descriptor-relative race experiment')
def test_file_swap_at_final_open_is_refused(box, monkeypatch):
    src = box/'receipt'
    src.write_bytes(b'original')
    outside = box/'outside'
    outside.write_bytes(b'outside-secret')
    real_open = os.open
    swapped = False

    def race_open(name, flags, *args, **kwargs):
        nonlocal swapped
        if not swapped and name == 'receipt' and 'dir_fd' in kwargs:
            swapped = True
            src.unlink()
            src.symlink_to(outside)
        return real_open(name, flags, *args, **kwargs)

    with mock.patch('os.open', side_effect=race_open):
        with pytest.raises((OSError, ValueError)):
            read_bounded_regular(src, 256)
    assert swapped
    assert outside.read_bytes() == b'outside-secret'


@pytest.mark.skipif(os.name != 'posix', reason='POSIX descriptor-relative race experiment')
def test_parent_swap_at_directory_open_is_refused(box):
    local = box/'local'
    local.mkdir()
    (local/'receipt').write_bytes(b'original')
    outside = box/'outside'
    outside.mkdir()
    (outside/'receipt').write_bytes(b'outside-secret')
    real_open = os.open
    swapped = False
    # Inject an attacker swap at the precise openat of the parent's basename.
    def race_open(name, flags, *args, **kwargs):
        nonlocal swapped
        if not swapped and name == 'local' and 'dir_fd' in kwargs:
            swapped = True
            local.rename(box/'old-local')
            local.symlink_to(outside, target_is_directory=True)
        return real_open(name, flags, *args, **kwargs)

    with mock.patch('os.open', side_effect=race_open):
        with pytest.raises((OSError, ValueError)):
            read_bounded_regular(local/'receipt', 256)
    assert swapped
    assert (outside/'receipt').read_bytes() == b'outside-secret'


@pytest.mark.skipif(os.name != 'posix' or not hasattr(os, 'mkfifo'), reason='POSIX FIFO experiment')
def test_fifo_is_refused_without_blocking(box):
    fifo = box/'fifo'
    os.mkfifo(fifo)
    with pytest.raises((OSError, ValueError)):
        read_bounded_regular(fifo, 64)


def test_hardlink_is_not_a_provenance_verification(box):
    outside = box/'outside'
    outside.write_bytes(b'public-bytes')
    linked = box/'linked'
    try:
        os.link(outside, linked)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f'hardlinks unavailable: {type(exc).__name__}')
    # Current guard tests no-follow symlinks/reparse points, NOT hardlinks or provenance.
    assert read_bounded_regular(linked, 64) == b'public-bytes'
