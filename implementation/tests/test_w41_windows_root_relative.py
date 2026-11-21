"""W41: native Windows RootDirectory race guard, reproducing the W39 attack.

The W39 old reader accepted substitute directory bytes. W41 must reject a
verified injected ordinary-parent rename at the final NtCreateFile call.
A no-hook / skipped probe is NOT evidence of security.
"""
from __future__ import annotations

import ntpath
import os

import pytest

from research.w38_receipt_fd_guard import read_bounded_regular


@pytest.mark.skipif(os.name != 'nt', reason='Native Windows HANDLE test only')
def test_w41_regular_windows_handle_read(tmp_path):
    file = tmp_path / 'receipt'
    data = b'W41-EXACT-PUBLIC\r\n\x00synthetic\n'
    file.write_bytes(data)
    assert read_bounded_regular(file, len(data)) == data
    with pytest.raises((OSError, ValueError)):
        read_bounded_regular(file, len(data) - 1)
    assert file.read_bytes() == data


@pytest.mark.skipif(os.name != 'nt', reason='Native Windows HANDLE test only')
def test_w41_unsupported_windows_names_fail_closed():
    from research.w41_windows_root_relative import read_windows_bounded
    from pathlib import Path

    for name in ('\\\\example.invalid\\share\\receipt',
                 'C:\\safe\\receipt:alternate',
                 'C:\\safe\\trailing.\\receipt'):
        with pytest.raises((OSError, ValueError)):
            read_windows_bounded(Path(name), 64)


@pytest.mark.skipif(os.name != 'nt', reason='Needs real Win32 NtCreateFile HANDLE')
def test_w39_same_ordinary_parent_swap_is_refused_by_w41(tmp_path, monkeypatch):
    """Intercept *native* final relative open, after W41 holds parent HANDLE."""
    import ctypes

    parent = tmp_path / 'requested'
    replacement = tmp_path / 'replacement'
    saved = tmp_path / 'original-saved'
    parent.mkdir()
    replacement.mkdir()
    expected = b'ORIGINAL-PUBLIC-SYNTHETIC'
    substitution = b'SUBSTITUTED-PUBLIC-SYNTHETIC'
    (parent / 'receipt').write_bytes(expected)
    (replacement / 'receipt').write_bytes(substitution)
    target = parent / 'receipt'

    real_dll = ctypes.WinDLL
    swapped = []

    class NativeOpenProxy:
        def __init__(self, underlying):
            self.underlying = underlying

        @property
        def argtypes(self):
            return self.underlying.argtypes

        @argtypes.setter
        def argtypes(self, value):
            self.underlying.argtypes = value

        @property
        def restype(self):
            return self.underlying.restype

        @restype.setter
        def restype(self, value):
            self.underlying.restype = value

        def __call__(self, *args):
            # W41's call uses ctypes.byref(OBJECT_ATTRIBUTES) as third arg.
            attrs = args[2]._obj
            component = attrs.ObjectName.contents.Buffer
            if component == 'receipt' and not swapped:
                try:
                    parent.rename(saved)
                    replacement.rename(parent)
                except OSError as exc:
                    pytest.skip(f'W41_NATIVE_RENAME_NOT_TESTED: {exc!r}')
                swapped.append('SWAP_AFTER_PARENT_HANDLE_BEFORE_NT_RELATIVE_LEAF')
            return self.underlying(*args)

    class DllProxy:
        def __init__(self, underlying):
            self.underlying = underlying
            self.nt_create = NativeOpenProxy(underlying.NtCreateFile)

        def __getattr__(self, attribute):
            if attribute == 'NtCreateFile':
                return self.nt_create
            return getattr(self.underlying, attribute)

    def dll(name, *args, **kwargs):
        lib = real_dll(name, *args, **kwargs)
        return DllProxy(lib) if str(name).lower() == 'ntdll' else lib

    observed = None
    refused = None
    with monkeypatch.context() as mp:
        mp.setattr(ctypes, 'WinDLL', dll)
        try:
            observed = read_bounded_regular(target, 256)
        except (OSError, ValueError) as exc:
            refused = exc

    assert swapped == ['SWAP_AFTER_PARENT_HANDLE_BEFORE_NT_RELATIVE_LEAF'], (
        'W41_UNTESTED: NtCreateFile leaf injection never ran'
    )
    assert (parent / 'receipt').read_bytes() == substitution
    assert (saved / 'receipt').read_bytes() == expected
    # A successful read of even the old file is not "refusal"; the requested
    # path has changed. Path identity check must reject this named-path race.
    assert refused is not None, (
        f'W41_UNSAFE: returned {observed!r} after ordinary-parent substitution'
    )
    assert observed is None
