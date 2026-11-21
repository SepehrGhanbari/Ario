"""W38 research-only bounded regular-file reader for *public synthetic* W35 receipts.

POSIX: descriptor-relative no-follow for every path component. Windows:
CreateFileW OPEN_REPARSE_POINT for the final component and reject reparse
ancestors and mismatched final-path handles. See W38 research notes for the
remaining Windows ancestor concurrency and hard-link limitations.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path


_DIR_FD_SUPPORTED = os.open in os.supports_dir_fd


class UnsafeReceiptPath(ValueError):
    """Non-regular, linked, or unsupported receipt path; always fail closed."""


def _read_posix(path: Path, max_bytes: int) -> bytes:
    if not (hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_DIRECTORY')
            and _DIR_FD_SUPPORTED):
        raise UnsafeReceiptPath('UNSUPPORTED_DESCRIPTOR_NOFOLLOW')
    absolute = os.path.abspath(os.fspath(path))
    components = [part for part in absolute.split(os.sep) if part]
    if not components:
        raise UnsafeReceiptPath('REFUSED_NON_REGULAR_OR_SYMLINK')
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)
    directory_fd = os.open(os.sep, directory_flags)
    try:
        for component in components[:-1]:
            next_fd = os.open(component, directory_flags, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        flags = (os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)
                 | getattr(os, 'O_NONBLOCK', 0))
        file_fd = os.open(components[-1], flags, dir_fd=directory_fd)
        with os.fdopen(file_fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise UnsafeReceiptPath('REFUSED_NON_REGULAR_OR_SYMLINK')
            if info.st_size > max_bytes:
                raise UnsafeReceiptPath('INPUT_SIZE_LIMIT')
            # Two actual reads on the same held FD plus metadata checks catch
            # tested same-inode modification during this bounded observation.
            # This is NOT an atomic filesystem snapshot or origin guarantee.
            fingerprint = lambda s: (s.st_dev, s.st_ino, s.st_size,
                                     s.st_mtime_ns, s.st_ctime_ns)
            first = stream.read(max_bytes + 1)
            middle = os.fstat(stream.fileno())
            if (fingerprint(info) != fingerprint(middle)
                    or len(first) != info.st_size):
                raise UnsafeReceiptPath('CONCURRENT_MODIFICATION_DETECTED')
            stream.seek(0)
            second = stream.read(max_bytes + 1)
            last = os.fstat(stream.fileno())
            if (fingerprint(info) != fingerprint(last)
                    or len(second) != info.st_size or first != second):
                raise UnsafeReceiptPath('CONCURRENT_MODIFICATION_DETECTED')
            return first
    finally:
        os.close(directory_fd)


def _read_windows(path: Path, max_bytes: int) -> bytes:
    """W41: pin each Windows ancestor using a retained directory HANDLE."""
    from research.w41_windows_root_relative import read_windows_bounded
    return read_windows_bounded(path, max_bytes)


def read_bounded_regular(path: Path, max_bytes: int) -> bytes:
    """Read a bounded exact byte image; never follow final-component links."""
    if type(max_bytes) is not int or not 0 <= max_bytes <= 16 * 1024 * 1024:
        raise ValueError('INVALID_RECEIPT_SIZE_CAP')
    if os.name == 'nt':
        return _read_windows(Path(path), max_bytes)
    return _read_posix(Path(path), max_bytes)
