"""Negative controls for the opt-in, Python-level network guard only."""
import os
import socket
import subprocess
import tempfile
import sys
import unittest
import urllib.request


class PythonNetworkGuardTests(unittest.TestCase):
    def test_python_socket_connect_and_dns_are_blocked(self):
        self.assertEqual(os.environ.get("ARIO_CI_PYTHON_NETWORK_DENY"), "1")
        with socket.socket() as client:
            with self.assertRaisesRegex(RuntimeError, "ARIO_CI_PYTHON_NETWORK_DENIED"):
                client.connect(("127.0.0.1", 1))
        with self.assertRaisesRegex(RuntimeError, "ARIO_CI_PYTHON_NETWORK_DENIED"):
            socket.getaddrinfo("example.invalid", 443)

    def test_guard_propagates_to_child_python_process(self):
        # Run without any external endpoint. A missing child-side guard would
        # raise ConnectionRefusedError on local loopback, not our marker.
        script = (
            "import socket\n"
            "with socket.socket() as client:\n"
            "    try:\n"
            "        client.connect(('127.0.0.1', 1))\n"
            "    except RuntimeError as exc:\n"
            "        print(str(exc))\n"
            "    else:\n"
            "        raise SystemExit('NETWORK_GUARD_MISSING')\n"
        )
        with tempfile.TemporaryDirectory() as scratch_cwd:
            # This is deliberately NOT the experiment folder: relative
            # PYTHONPATH would lose the guard. Only absolute CI path survives.
            proc = subprocess.run([sys.executable, "-c", script],
                                  cwd=scratch_cwd, env=os.environ.copy(),
                                  text=True, capture_output=True, timeout=10,
                                  check=False)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("ARIO_CI_PYTHON_NETWORK_DENIED", proc.stdout)

    def test_urllib_provider_request_is_blocked_before_dispatch(self):
        self.assertEqual(os.environ.get("ARIO_CI_PYTHON_NETWORK_DENY"), "1")
        with self.assertRaisesRegex(RuntimeError, "ARIO_CI_PYTHON_NETWORK_DENIED"):
            urllib.request.urlopen("https://example.invalid/should-not-connect", timeout=0.1)


if __name__ == "__main__":
    unittest.main()
