"""CI bridge: run every offline #134 experiment unittest without provider access.

Deliberately uses the existing fake transport; no cloud credentials or
provider dispatch. This is an isolated test of the research branch only.
"""
from __future__ import annotations

import importlib.util
import os
from unittest.mock import patch
from pathlib import Path
import unittest


def test_pr134_exact_offline_suite():
    repo_root = Path(__file__).resolve().parents[2]
    runner_tests = (repo_root / "experiments" / "ava-cloud-identity-2026-11-03"
                    / "test_ario_ava_cloud_50.py")
    assert runner_tests.is_file(), "PR134_OFFLINE_TEST_SOURCE_MISSING"
    native_windows_probe = runner_tests.with_name("test_native_windows_recovery_smoke.py")
    assert native_windows_probe.is_file(), "PR134_WINDOWS_SMOKE_SOURCE_MISSING"
    # Ubuntu CI can parse the Windows-only probe, but cannot execute it as native Windows.
    compile(native_windows_probe.read_text(encoding="utf-8"),
            str(native_windows_probe), "exec")
    spec = importlib.util.spec_from_file_location("_ario_pr134_offline_suite", runner_tests)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    result = unittest.TestResult()
    # Prevent accidental urllib-based cloud dispatch during the offline suite.
    # This is a scoped guard, not a general OS-level network sandbox.
    with patch("urllib.request.urlopen", side_effect=AssertionError("OFFLINE_PROVIDER_DISPATCH_FORBIDDEN")):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            suite.run(result)
    assert not result.skipped, f"Offline suite silently skipped: {result.skipped}"
    details = [f"{case}: {tb}" for case, tb in result.errors + result.failures]
    assert result.testsRun >= 32, f"Expected >=32 offline tests, got {result.testsRun}"
    assert result.wasSuccessful(), (
        f"PR134_OFFLINE_SUITE_FAILED: {result.testsRun} tests, "
        f"{len(result.failures)} failures, {len(result.errors)} errors\n"
        + "\n".join(details)
    )
