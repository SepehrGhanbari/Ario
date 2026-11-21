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
            data = stream.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise UnsafeReceiptPath('INPUT_SIZE_LIMIT')
        return data
    finally:
        os.close(directory_fd)


def _read_windows(path: Path, max_bytes: int) -> bytes:
    """Windows handle-based leaf no-follow; ancestor race is still NOT_ESTABLISHED."""
    import ctypes
    from ctypes import wintypes
    import ntpath

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                      ctypes.c_void_p, wintypes.DWORD]
    kernel32.GetFileInformationByHandleEx.restype = wintypes.BOOL
    kernel32.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR,
                                                   wintypes.DWORD, wintypes.DWORD]
    kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    kernel32.ReadFile.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                                  ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    kernel32.ReadFile.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    # FILE_FLAG_OPEN_REPARSE_POINT disables following the *final* name component.
    nofollow = 0x00200000
    backup_semantics = 0x02000000
    reparse_attribute = 0x00000400
    directory_attribute = 0x00000010
    share_all = 0x00000001 | 0x00000002 | 0x00000004
    read_access = 0x80000000
    open_existing = 3
    invalid_handle = ctypes.c_void_p(-1).value

    class AttributeTagInfo(ctypes.Structure):
        _fields_ = [('FileAttributes', wintypes.DWORD), ('ReparseTag', wintypes.DWORD)]

    def open_handle(name: str, directory: bool):
        flags = nofollow | (backup_semantics if directory else 0)
        handle = kernel32.CreateFileW(name, read_access if not directory else 0,
                                      share_all, None, open_existing, flags, None)
        if handle is None or handle == invalid_handle:
            raise OSError(ctypes.get_last_error(), 'CreateFileW failed')
        try:
            attrs = AttributeTagInfo()
            if not kernel32.GetFileInformationByHandleEx(handle, 9, ctypes.byref(attrs),
                                                          ctypes.sizeof(attrs)):
                raise OSError(ctypes.get_last_error(), 'GetFileInformationByHandleEx failed')
            if attrs.FileAttributes & reparse_attribute:
                raise UnsafeReceiptPath('REFUSED_REPARSE_POINT')
            if bool(attrs.FileAttributes & directory_attribute) is not directory:
                raise UnsafeReceiptPath('REFUSED_NON_REGULAR_OR_SYMLINK')
            return handle
        except BaseException:
            kernel32.CloseHandle(handle)
            raise

    absolute = ntpath.abspath(os.fspath(path))
    # Check all lexical directory ancestors for reparse points. This is not
    # equivalent to an atomic directory-relative NT open (documented limit).
    parents = list(Path(absolute).parents)
    for ancestor in reversed(parents):
        handle = open_handle(str(ancestor), directory=True)
        kernel32.CloseHandle(handle)
    handle = open_handle(absolute, directory=False)
    try:
        # Compare final opened object location to the requested lexical path.
        # This detects ancestor redirections that survive until the file open.
        name_buf = ctypes.create_unicode_buffer(32768)
        length = kernel32.GetFinalPathNameByHandleW(handle, name_buf, len(name_buf), 0)
        if not (0 < length < len(name_buf)):
            raise UnsafeReceiptPath('UNVERIFIED_HANDLE_PATH')
        final_path = name_buf.value
        if final_path.startswith('\\\\?\\UNC\\'):
            final_path = '\\\\' + final_path[8:]
        elif final_path.startswith('\\\\?\\'):
            final_path = final_path[4:]
        if ntpath.normcase(ntpath.normpath(final_path)) != ntpath.normcase(ntpath.normpath(absolute)):
            raise UnsafeReceiptPath('HANDLE_PATH_MISMATCH')
        buffer = ctypes.create_string_buffer(max_bytes + 1)
        count = wintypes.DWORD(0)
        if not kernel32.ReadFile(handle, buffer, max_bytes + 1, ctypes.byref(count), None):
            raise OSError(ctypes.get_last_error(), 'ReadFile failed')
        if count.value > max_bytes:
            raise UnsafeReceiptPath('INPUT_SIZE_LIMIT')
        return buffer.raw[:count.value]
    finally:
        kernel32.CloseHandle(handle)


def read_bounded_regular(path: Path, max_bytes: int) -> bytes:
    """Read a bounded exact byte image; never follow final-component links."""
    if type(max_bytes) is not int or not 0 <= max_bytes <= 16 * 1024 * 1024:
        raise ValueError('INVALID_RECEIPT_SIZE_CAP')
    if os.name == 'nt':
        return _read_windows(Path(path), max_bytes)
    return _read_posix(Path(path), max_bytes)
