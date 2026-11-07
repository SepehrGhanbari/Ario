"""Opt-in Python-only transport denial for GitHub Windows research scratch.

Loaded by Python/sitecustomize *only* when the workflow sets PYTHONPATH and
ARIO_CI_PYTHON_NETWORK_DENY=1. This is not an OS firewall, cannot block native
programs or GitHub checkout traffic, and is not a production security feature.
"""
import os

if os.environ.get("ARIO_CI_PYTHON_NETWORK_DENY") == "1":
    import socket
    import urllib.request

    def _refuse_test_python_network(*args, **kwargs):
        raise RuntimeError("ARIO_CI_PYTHON_NETWORK_DENIED")

    socket.socket.connect = _refuse_test_python_network
    socket.socket.connect_ex = _refuse_test_python_network
    socket.socket.sendto = _refuse_test_python_network
    socket.create_connection = _refuse_test_python_network
    socket.getaddrinfo = _refuse_test_python_network
    urllib.request.urlopen = _refuse_test_python_network
