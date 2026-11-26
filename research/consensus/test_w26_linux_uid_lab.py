#!/usr/bin/env python3
"""Nonprivileged W26 policy checks; native UID cases run via --ci-run separately."""
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import w26_linux_uid_lab as lab

class W26Policy(unittest.TestCase):
    def test_01_disallows_unopted_host(self):
        with patch.dict(os.environ, {"ARIO_W26_DISPOSABLE_CI":"0", "ARIO_W26_DISPOSABLE_CONTAINER":"0"},clear=False):
            with self.assertRaises(RuntimeError):lab.guarded()
    def test_02_refuses_no_runner_temp(self):
        with patch.dict(os.environ,{"ARIO_W26_DISPOSABLE_CONTAINER":"1","RUNNER_TEMP":""}):
            with self.assertRaises(RuntimeError):lab.guarded()
    def test_03_disallows_unsafe_root_temp(self):
        with patch.dict(os.environ,{"ARIO_W26_DISPOSABLE_CONTAINER":"1","RUNNER_TEMP":"/"}):
            with self.assertRaises(RuntimeError):lab.guarded()
    def test_04_allows_explicit_disposable_container(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.dict(os.environ,{"ARIO_W26_DISPOSABLE_CONTAINER":"1","RUNNER_TEMP":d}):
                self.assertEqual(lab.guarded(),Path(d).resolve())
    def test_05_rejects_outside_scratch(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve()
            with self.assertRaises(RuntimeError):lab.within(root,'/etc/passwd')
    def test_06_responds_without_real_authority(self):
        x=lab.reply('READ_ONLY_HEAD',size=8)
        self.assertFalse(x['witness_cosignature'])
        self.assertEqual(x['authority'],'NONE')
        self.assertEqual(x['independent_admin'],'NOT_ESTABLISHED')
        self.assertEqual(x['world_freshness'],'UNKNOWN')
        self.assertEqual(x['external_actions'],0)
    def test_07_probe_rejects_unknown_action(self):
        with self.assertRaises(ValueError):lab.probe('unknown','/never')
    def test_08_numeric_uids_are_distinct(self):
        self.assertEqual(len({lab.PUBLISHER_UID,lab.WITNESS_UID,lab.INTRUDER_UID}),3)
    def test_09_no_capability_to_sign_exists_in_module(self):
        self.assertFalse(hasattr(lab,'sign_checkpoint'))
        self.assertFalse(hasattr(lab,'emit_cosignature'))
    def test_10_bounded_wire_request(self):
        self.assertEqual(lab.MAX_REQ,4096)

if __name__=='__main__':unittest.main(verbosity=2)
