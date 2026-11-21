"""W39: actual-Windows controlled ordinary-directory swap at W38 final CreateFileW.

A discovered vulnerability is marked xfail (not a security PASS).
All payloads are synthetic; no privileged junction/symlink creation required.
"""
from __future__ import annotations

import ntpath
import os
from pathlib import Path

import pytest

from research.w38_receipt_fd_guard import read_bounded_regular


def test_regular_receipt_bytes_unchanged(tmp_path):
    receipt = tmp_path / "receipt"
    content = b"W39-PUBLIC-SYNTHETIC\r\n"
    receipt.write_bytes(content)
    assert read_bounded_regular(receipt, len(content)) == content


@pytest.mark.skipif(os.name != "nt", reason="Native Win32 CreateFileW race probe requires Windows")
def test_win32_regular_parent_swap_at_leaf_open_is_not_misreported_as_safe(tmp_path, monkeypatch):
    """Rename two *regular* directories after parent checks, before leaf open.

    This documents the currently known W38 Windows ancestor check/open gap.
    It does not imply the fixed SHA-256 W35 receipt verifier accepts these bytes.
    """
    import ctypes

    parent = tmp_path / "requested"
    replacement = tmp_path / "replacement"
    saved = tmp_path / "original-saved"
    parent.mkdir()
    replacement.mkdir()
    expected = b"ORIGINAL-PUBLIC-SYNTHETIC"
    adversarial = b"SUBSTITUTED-PUBLIC-SYNTHETIC"
    (parent / "receipt").write_bytes(expected)
    (replacement / "receipt").write_bytes(adversarial)
    requested = parent / "receipt"
    requested_name = ntpath.normcase(ntpath.normpath(str(requested)))

    real_windll = ctypes.WinDLL
    intercepted = []

    class InterceptedCreateFile:
        def __init__(self, original):
            self.original = original

        @property
        def argtypes(self):
            return self.original.argtypes

        @argtypes.setter
        def argtypes(self, value):
            self.original.argtypes = value

        @property
        def restype(self):
            return self.original.restype

        @restype.setter
        def restype(self, value):
            self.original.restype = value

        def __call__(self, name, *args, **kwargs):
            if (not intercepted and
                    ntpath.normcase(ntpath.normpath(str(name))) == requested_name):
                # All ancestor handles have been closed by the current W38
                # implementation. Trigger exactly before final native open.
                try:
                    parent.rename(saved)
                    replacement.rename(parent)
                except OSError as exc:
                    pytest.skip(f"Windows directory rename unavailable: {exc!r}")
                intercepted.append("SWAPPED_REGULAR_PARENT_AT_CREATEFILEW")
            return self.original(name, *args, **kwargs)

    class DllProxy:
        def __init__(self, original):
            self.original = original
            self.open_file = InterceptedCreateFile(original.CreateFileW)

        def __getattr__(self, attr):
            return self.open_file if attr == "CreateFileW" else getattr(self.original, attr)

    def dll_factory(name, *args, **kwargs):
        lib = real_windll(name, *args, **kwargs)
        if str(name).lower() == "kernel32":
            return DllProxy(lib)
        return lib

    monkeypatch.setattr(ctypes, "WinDLL", dll_factory)
    caught = None
    observed = None
    try:
        observed = read_bounded_regular(requested, 256)
    except (OSError, ValueError) as exc:
        caught = type(exc).__name__

    assert intercepted == ["SWAPPED_REGULAR_PARENT_AT_CREATEFILEW"], (
        "Synthetic race hook did not run; this probe cannot establish a Windows result"
    )
    assert (parent / "receipt").read_bytes() == adversarial
    assert (saved / "receipt").read_bytes() == expected

    if observed == adversarial:
        pytest.xfail(
            "W39_VERIFIED_RED: W38 returned swapped regular parent's bytes "
            "after final CreateFileW, despite ancestor prechecks"
        )
    assert observed is None, (
        "Unexpected accepted bytes after controlled parent swap: "
        f"{observed!r}; caught={caught}"
    )
