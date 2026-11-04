"""CI bridge: run every offline #134 experiment unittest without provider access.

Deliberately uses the existing fake transport; no cloud credentials or
provider dispatch. This is an isolated test of the research branch only.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


def test_pr134_exact_offline_suite():
    repo_root = Path(__file__).resolve().parents[2]
    runner_tests = (repo_root / "experiments" / "ava-cloud-identity-2026-11-03"
                    / "test_ario_ava_cloud_50.py")
    assert runner_tests.is_file(), "PR134_OFFLINE_TEST_SOURCE_MISSING"
    spec = importlib.util.spec_from_file_location("_ario_pr134_offline_suite", runner_tests)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    result = unittest.TestResult()
    suite.run(result)
    details = [f"{case}: {tb}" for case, tb in result.errors + result.failures]
    assert result.testsRun >= 25, f"Expected >=25 offline tests, got {result.testsRun}"
    assert result.wasSuccessful(), (
        f"PR134_OFFLINE_SUITE_FAILED: {result.testsRun} tests, "
        f"{len(result.failures)} failures, {len(result.errors)} errors\n"
        + "\n".join(details)
    )
