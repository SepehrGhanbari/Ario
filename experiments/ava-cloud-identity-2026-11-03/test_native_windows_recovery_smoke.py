"""Native Windows CRT/NTFS bounded scratch probes for PR #144.

Run manually on the owner's Windows host in a disposable environment:
    py -3 -m unittest -v test_native_windows_recovery_smoke.py

Never uses OpenRouter, network, keys, real transcript, signing or trust.
Results are local-only and do not prove power-loss durability or identity.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import ario_ava_cloud_50 as exp

@unittest.skipUnless(os.name == "nt", "Only a native Windows run has evidentiary value here")
class WindowsNativeScratchTests(unittest.TestCase):
    def test_lock_exact_binary_bytes_and_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            with exp.ExclusiveRunLock(path) as lock:
                self.assertEqual(lock.path.read_bytes(), lock.raw)
                self.assertTrue(lock.raw.endswith(b"\n"))
                self.assertNotIn(b"\r\n", lock.raw)
                lock.assert_owned()
            self.assertFalse((path / ".run_writer.lock").exists())

    def test_append_only_events_exact_binary_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            a = exp.Ledger(folder)
            a.add("SCRATCH_FIRST", text="windows-native")
            a.add("SCRATCH_SECOND", text="another")
            first_bytes = a.path.read_bytes()
            self.assertNotIn(b"\r\n", first_bytes)
            self.assertTrue(first_bytes.endswith(b"\n"))
            b = exp.Ledger(folder)
            self.assertEqual(len(b.events), 2)
            self.assertEqual(b.hash, a.hash)
            self.assertEqual(first_bytes, b.path.read_bytes())

    def test_second_native_process_cannot_acquire_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            cmd = [
                sys.executable,
                "-c",
                (
                    "import sys; from pathlib import Path; "
                    "import ario_ava_cloud_50 as e; "
                    "p=Path(sys.argv[1]); "
                    "l=e.ExclusiveRunLock(p); "
                    "\ntry:\n with l: sys.exit(40)\n"
                    "except e.Hold: sys.exit(33)\n"
                ),
                str(folder),
            ]
            env = {**os.environ, "OPENROUTER_API_KEY": ""}
            with exp.ExclusiveRunLock(folder):
                proc = subprocess.run(
                    cmd, cwd=str(Path(__file__).parent), env=env,
                    capture_output=True, text=True, timeout=15, check=False,
                )
                self.assertEqual(proc.returncode, 33, proc.stderr)
            proc = subprocess.run(
                cmd, cwd=str(Path(__file__).parent), env=env,
                capture_output=True, text=True, timeout=15, check=False,
            )
            self.assertEqual(proc.returncode, 40, proc.stderr)

    def test_stale_lock_is_preserved_and_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            path = folder / ".run_writer.lock"
            path.write_bytes(b"UNCERTAIN_STALE")
            with self.assertRaisesRegex(exp.Hold, "RUN_WRITER_LOCK_EXISTS"):
                with exp.ExclusiveRunLock(folder):
                    pass
            self.assertEqual(path.read_bytes(), b"UNCERTAIN_STALE")

    def test_lost_lock_refuses_before_second_provider_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            ledger = exp.Ledger(folder)
            letter = "NATIVE WINDOWS TEST ONLY"
            exp.init_run(ledger, letter, exp.sha(letter.encode("utf-8")), [], None, 2)
            lock = exp.ExclusiveRunLock(folder)
            seen = []
            def fake_provider(_payload, _key):
                seen.append(1)
                lock.path.write_bytes(b"MODIFIED")
                return {"model": exp.MODEL, "id": "fake", "choices": [
                    {"message": {"content": "one"}, "finish_reason": "stop"}]}
            with self.assertRaisesRegex(exp.Hold, "WRITER_LOCK_"):
                with lock:
                    exp.run(ledger, letter, "fake-key-not-used", fake_provider, writer_lock=lock)
            self.assertEqual(len(seen), 1)
            self.assertFalse(ledger.items("REPLY"))


if __name__ == "__main__":
    unittest.main()
