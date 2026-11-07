"""Negative controls for the opt-in, Python-level network guard only."""
import os
import socket
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

    def test_urllib_provider_request_is_blocked_before_dispatch(self):
        self.assertEqual(os.environ.get("ARIO_CI_PYTHON_NETWORK_DENY"), "1")
        with self.assertRaisesRegex(RuntimeError, "ARIO_CI_PYTHON_NETWORK_DENIED"):
            urllib.request.urlopen("https://example.invalid/should-not-connect", timeout=0.1)


if __name__ == "__main__":
    unittest.main()
