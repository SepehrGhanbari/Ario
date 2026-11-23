"""W41 research-only Windows single-component, directory-HANDLE-relative file open.

Avoid W38's path precheck / final pathname-open race by retaining the opened
parent directory handle and opening every next component relative to it with
NtCreateFile(OBJECT_ATTRIBUTES.RootDirectory). Fail closed on ambiguity.

Only for local synthetic read-only receipt / JSONL observation inputs.
No assertion of historical provenance, atomic in-place content snapshots, or
production trust. Native Windows API required; never silently fall back to
CreateFileW on the original absolute leaf pathname.
"""
from __future__ import annotations

import ntpath
import os
from pathlib import Path

from research.w38_receipt_fd_guard import UnsafeReceiptPath


def read_windows_bounded(path: Path, max_bytes: int) -> bytes:
    """Read existing local-drive regular file; no Win32 pathname leaf open."""
    import ctypes
    from ctypes import wintypes

    absolute = ntpath.abspath(os.fspath(path))
    drive, tail = ntpath.splitdrive(absolute)
    # Unsupported UNC / device namespaces, ADS, trailing-space/dot aliases or
    # components with separators are rejected, never handled via path fallback.
    if (len(drive) != 2 or drive[1:] != ':' or not drive[0].isalpha()
            or not tail.startswith('\\') or tail.startswith('\\\\')):
        raise UnsafeReceiptPath('UNSUPPORTED_WINDOWS_PATH')
    parts = tail[1:].split('\\')
    if (not parts or any(not x or x in ('.', '..') or ':' in x
                         or x.endswith((' ', '.')) for x in parts)):
        raise UnsafeReceiptPath('UNSUPPORTED_WINDOWS_COMPONENT')

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    ntdll = ctypes.WinDLL('ntdll', use_last_error=True)
    share_all = 0x0001 | 0x0002 | 0x0004
    file_read_attributes = 0x0080
    file_traverse = 0x0020
    file_read_data = 0x0001
    synchronize = 0x00100000
    open_reparse = 0x00200000
    backup_semantics = 0x02000000
    invalid_handle = ctypes.c_void_p(-1).value
    reparse_attribute = 0x00000400
    directory_attribute = 0x00000010
    file_open_reparse_point = 0x00200000
    file_sync_nonal = 0x00000020
    file_non_directory = 0x00000040
    file_open = 1
    obj_case_insensitive = 0x00000040
    obj_dont_reparse = 0x00001000

    class AttributeTagInfo(ctypes.Structure):
        _fields_ = [('FileAttributes', wintypes.DWORD),
                    ('ReparseTag', wintypes.DWORD)]

    class UnicodeString(ctypes.Structure):
        _fields_ = [('Length', wintypes.USHORT),
                    ('MaximumLength', wintypes.USHORT),
                    ('Buffer', wintypes.LPWSTR)]

    class ObjectAttributes(ctypes.Structure):
        _fields_ = [('Length', wintypes.ULONG),
                    ('RootDirectory', wintypes.HANDLE),
                    ('ObjectName', ctypes.POINTER(UnicodeString)),
                    ('Attributes', wintypes.ULONG),
                    ('SecurityDescriptor', wintypes.LPVOID),
                    ('SecurityQualityOfService', wintypes.LPVOID)]

    class IoStatusBlock(ctypes.Structure):
        # The native IO_STATUS_BLOCK begins with a pointer-sized union.
        _fields_ = [('StatusOrPointer', ctypes.c_void_p),
                    ('Information', ctypes.c_size_t)]

    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.GetFileInformationByHandleEx.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    ]
    kernel32.GetFileInformationByHandleEx.restype = wintypes.BOOL
    kernel32.GetFinalPathNameByHandleW.argtypes = [
        wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
    ]
    kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    kernel32.GetFileSizeEx.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(ctypes.c_longlong),
    ]
    kernel32.GetFileSizeEx.restype = wintypes.BOOL
    kernel32.ReadFile.argtypes = [
        wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID,
    ]
    kernel32.ReadFile.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    ntdll.NtCreateFile.argtypes = [
        ctypes.POINTER(wintypes.HANDLE), wintypes.ULONG,
        ctypes.POINTER(ObjectAttributes), ctypes.POINTER(IoStatusBlock),
        ctypes.c_void_p, wintypes.ULONG, wintypes.ULONG, wintypes.ULONG,
        wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG,
    ]
    ntdll.NtCreateFile.restype = ctypes.c_long

    def check_handle(handle, want_dir: bool):
        info = AttributeTagInfo()
        if not kernel32.GetFileInformationByHandleEx(
                handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            raise OSError(ctypes.get_last_error(), 'HANDLE_ATTRIBUTES_FAILED')
        if info.FileAttributes & reparse_attribute:
            raise UnsafeReceiptPath('REFUSED_REPARSE_POINT')
        if bool(info.FileAttributes & directory_attribute) is not want_dir:
            raise UnsafeReceiptPath('REFUSED_NON_REGULAR_OR_SYMLINK')

    def open_relative(root_handle, name: str, directory: bool):
        encoded_size = len(name.encode('utf-16-le'))
        if encoded_size == 0 or encoded_size > 65532:
            raise UnsafeReceiptPath('INVALID_NT_COMPONENT_LENGTH')
        name_buffer = ctypes.create_unicode_buffer(name)
        uni = UnicodeString(encoded_size, encoded_size + 2,
                            ctypes.cast(name_buffer, wintypes.LPWSTR))
        attrs = ObjectAttributes(ctypes.sizeof(ObjectAttributes), root_handle,
                                 ctypes.pointer(uni),
                                 obj_case_insensitive | obj_dont_reparse,
                                 None, None)
        handle = wintypes.HANDLE()
        status_block = IoStatusBlock()
        desired = file_read_attributes | synchronize | (
            file_traverse if directory else file_read_data)
        # Do not combine FILE_DIRECTORY_FILE with FILE_OPEN_REPARSE_POINT:
        # the documented compatible-option list for DIR_FILE excludes it.
        # Open type-neutral and enforce directory vs regular via HANDLE attrs.
        options = file_open_reparse_point | file_sync_nonal | (
            0 if directory else file_non_directory)
        # W42: refuse a regular leaf if an existing handle requests write
        # or delete access, and deny new incompatible writers for our read.
        # Directory handles deliberately retain share-all (W39 rename test).
        share_mode = share_all if directory else 0x0001  # FILE_SHARE_READ
        status = ntdll.NtCreateFile(
            ctypes.byref(handle), desired, ctypes.byref(attrs),
            ctypes.byref(status_block), None, 0, share_mode, file_open,
            options, None, 0)
        if status != 0 or not handle.value:
            if handle.value:
                kernel32.CloseHandle(handle)
            raise UnsafeReceiptPath(f'NT_RELATIVE_OPEN_FAILED_{status & 0xffffffff:08X}')
        try:
            check_handle(handle, directory)
            return handle
        except BaseException:
            kernel32.CloseHandle(handle)
            raise

    root_dir = drive + '\\'
    parent_handle = kernel32.CreateFileW(
        root_dir, file_read_attributes | file_traverse | synchronize,
        share_all, None, 3, backup_semantics | open_reparse, None)
    if parent_handle is None or parent_handle == invalid_handle:
        raise OSError(ctypes.get_last_error(), 'DRIVE_ROOT_OPEN_FAILED')
    try:
        check_handle(parent_handle, True)
        # Every path component is opened relative to a held parent HANDLE.
        # Closing a parent only after opening its child prevents the W39 race.
        for component in parts[:-1]:
            child = open_relative(parent_handle, component, True)
            kernel32.CloseHandle(parent_handle)
            parent_handle = child

        leaf_handle = open_relative(parent_handle, parts[-1], False)
        try:
            # Fail closed if a retained parent was renamed while opening:
            # the actual leaf path must still be the nominated lexical path.
            namebuf = ctypes.create_unicode_buffer(32768)
            count = kernel32.GetFinalPathNameByHandleW(
                leaf_handle, namebuf, len(namebuf), 0)
            if not (0 < count < len(namebuf)):
                raise UnsafeReceiptPath('UNVERIFIED_HANDLE_PATH')
            actual = namebuf.value
            if actual.startswith('\\' * 2 + '?' + '\\' + 'UNC' + '\\'):
                actual = '\\' * 2 + actual[8:]
            elif actual.startswith('\\' * 2 + '?' + '\\'):
                actual = actual[4:]
            if ntpath.normcase(ntpath.normpath(actual)) != ntpath.normcase(
                    ntpath.normpath(absolute)):
                raise UnsafeReceiptPath('HANDLE_PATH_MISMATCH')

            size = ctypes.c_longlong()
            if not kernel32.GetFileSizeEx(leaf_handle, ctypes.byref(size)):
                raise OSError(ctypes.get_last_error(), 'FILE_SIZE_UNAVAILABLE')
            if size.value < 0 or size.value > max_bytes:
                raise UnsafeReceiptPath('INPUT_SIZE_LIMIT')

            buf = ctypes.create_string_buffer(max_bytes + 1)
            n = wintypes.DWORD()
            if not kernel32.ReadFile(leaf_handle, buf, max_bytes + 1,
                                     ctypes.byref(n), None):
                raise OSError(ctypes.get_last_error(), 'NATIVE_READ_FAILED')
            if n.value > max_bytes:
                raise UnsafeReceiptPath('INPUT_SIZE_LIMIT')
            # One more path identity check guards obvious rename-after-read.
            check_count = kernel32.GetFinalPathNameByHandleW(
                leaf_handle, namebuf, len(namebuf), 0)
            if not (0 < check_count < len(namebuf)):
                raise UnsafeReceiptPath('UNVERIFIED_HANDLE_PATH')
            final = namebuf.value
            if final.startswith('\\' * 2 + '?' + '\\' + 'UNC' + '\\'):
                final = '\\' * 2 + final[8:]
            elif final.startswith('\\' * 2 + '?' + '\\'):
                final = final[4:]
            if ntpath.normcase(ntpath.normpath(final)) != ntpath.normcase(
                    ntpath.normpath(absolute)):
                raise UnsafeReceiptPath('HANDLE_PATH_MISMATCH')
            return buf.raw[:n.value]
        finally:
            kernel32.CloseHandle(leaf_handle)
    finally:
        kernel32.CloseHandle(parent_handle)
