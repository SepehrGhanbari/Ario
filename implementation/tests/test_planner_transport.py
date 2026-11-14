"""Real transport controls using isolated clients and two loopback-only fake servers."""
import json
import os
import socket
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

IMPLEMENTATION = Path(__file__).resolve().parents[1]
CANARY = "ARIO-SYNTHETIC-TRANSPORT-CANARY-163"
RECOMMENDATION = {
    "implementation_path": "implementation/ario_planner.py",
    "test_path": "implementation/tests/test_planner_runtime.py",
    "engineering_question": "Which transport edge case needs an independent regression test?",
    "rationale": "The supplied source and tests describe bounded local planning.",
}
RESPONSE = json.dumps({"message": {"content": json.dumps(RECOMMENDATION)}}).encode()
CLIENT = """
import json, sys, urllib.request
from ario_planner import request_plan
if sys.argv[3] == "trap":
    class Trap:
        def open(self, *args, **kwargs):
            raise AssertionError("process-global opener used")
    urllib.request.install_opener(Trap())
# Test containment: no probe may connect to a non-loopback address, even if
# the runtime regression under test is broken. Record attempted connections.
import ipaddress, socket
attempts = []
dns_calls = []
real_resolve = socket.getaddrinfo
def resolve(host, *args, **kwargs):
    if host == "localhost":
        dns_calls.append(host)
        if sys.argv[5] == "unsafe" or (sys.argv[5] == "rebind" and len(dns_calls) > 1):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.1", 11434))]
    return real_resolve(host, *args, **kwargs)
socket.getaddrinfo = resolve
def audit(event, args):
    if event == "socket.connect":
        address = args[1]
        attempts.append(list(address))
        if not ipaddress.ip_address(address[0]).is_loopback:
            raise AssertionError("test containment blocked non-loopback connection")
sys.addaudithook(audit)
before = urllib.request._opener
try:
    workflow = request_plan(sys.argv[4], sys.argv[1], ollama_url=sys.argv[2], timeout=5)
    print(json.dumps({"ok": True, "global_unchanged": urllib.request._opener is before,
                      "stages": len(workflow["stages"]), "attempts": attempts, "dns_calls": dns_calls}))
except Exception as exc:
    print(json.dumps({"ok": False, "type": type(exc).__name__, "error": str(exc),
                      "global_unchanged": urllib.request._opener is before, "attempts": attempts, "dns_calls": dns_calls}))
"""
DIRECT = """
import sys, urllib.request
with urllib.request.urlopen(sys.argv[1], data=sys.argv[2].encode(), timeout=5) as response:
    response.read()
"""


GET_REDIRECT_PROBE = """
import json, sys, urllib.request
from ario_planner import _open_local_ollama
req = urllib.request.Request(sys.argv[1], method="GET")
try:
    if sys.argv[2] == "default":
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=5) as response:
            response.read()
    else:
        with _open_local_ollama(req, timeout=5) as response:
            response.read()
    print(json.dumps({"ok": True}))
except Exception as exc:
    print(json.dumps({"ok": False, "type": type(exc).__name__,
                      "code": getattr(exc, "code", None)}))
"""


@contextmanager
def fake_server(redirect_to=None, redirect_code=302, *, host="127.0.0.1", responses=None):
    receipts = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.handle_request()

        def do_GET(self):
            self.handle_request()

        def handle_request(self):
            data = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            receipts.append({"method": self.command, "path": self.path, "body": data})
            if redirect_to is not None:
                self.send_response(redirect_code)
                self.send_header("Location", redirect_to)
                payload = b""
            else:
                self.send_response(200)
                payload = RESPONSE if responses is None else responses[min(len(receipts) - 1, len(responses) - 1)]
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    class IPv6Server(ThreadingHTTPServer):
        address_family = socket.AF_INET6
    server_type = IPv6Server if ":" in host else ThreadingHTTPServer
    try:
        server = server_type((host, 0), Handler)
    except OSError as exc:
        if host == "::1":
            raise unittest.SkipTest(f"IPv6 loopback unavailable: {exc}") from exc
        raise
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        endpoint_host = f"[{host}]" if ":" in host else host
        yield f"http://{endpoint_host}:{server.server_port}", receipts
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class PlannerTransportTests(unittest.TestCase):
    @staticmethod
    def localhost_binding():
        # Mirror the actual runtime's loopback preference without assuming IPv4.
        addresses = {item[4][0] for item in socket.getaddrinfo(
            "localhost", 11434, type=socket.SOCK_STREAM)}
        assert addresses and addresses <= {"127.0.0.1", "::1"}, addresses
        return "127.0.0.1" if "127.0.0.1" in addresses else "::1"

    @staticmethod
    def hostname_localhost(backend):
        return backend.replace("127.0.0.1", "localhost").replace("[::1]", "localhost")

    def environment(self, proxy_url=None, bypass=None):
        env = {key: value for key, value in os.environ.items()
               if not key.lower().endswith("_proxy") and key.upper() != "REQUEST_METHOD"}
        env.update(PYTHONPATH=str(IMPLEMENTATION), PYTHONDONTWRITEBYTECODE="1")
        if proxy_url is not None:
            env.update(HTTP_PROXY=proxy_url, http_proxy=proxy_url, HTTPS_PROXY=proxy_url,
                       https_proxy=proxy_url, ALL_PROXY=proxy_url, all_proxy=proxy_url)
        if bypass is not None:
            env.update(NO_PROXY=bypass, no_proxy=bypass)
        return env

    def client(self, backend, proxy=None, bypass=None, trap=False, dns="normal"):
        with tempfile.TemporaryDirectory() as directory:
            for relative in ("implementation/ario_planner.py",
                             "implementation/tests/test_planner_runtime.py"):
                path = Path(directory) / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# " + CANARY + "\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-B", "-c", CLIENT, directory, backend,
                 "trap" if trap else "normal", CANARY, dns],
                env=self.environment(proxy, bypass), cwd=directory,
                capture_output=True, text=True, timeout=20,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_positive_control_default_urlopen_reaches_configured_proxy(self):
        with fake_server() as (backend, backend_receipts), fake_server() as (proxy, proxy_receipts):
            result = subprocess.run(
                [sys.executable, "-B", "-c", DIRECT, backend + "/api/chat", CANARY],
                env=self.environment(proxy), capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(backend_receipts), 0)
            self.assertEqual(len(proxy_receipts), 1)
            self.assertIn(CANARY.encode(), proxy_receipts[0]["body"])
            self.assertEqual(proxy_receipts[0]["path"], backend + "/api/chat")

    def test_planner_bypasses_configured_proxy_with_no_proxy_exemption(self):
        with fake_server() as (backend, received), fake_server() as (proxy, proxied):
            result = self.client(backend, proxy)
            self.assertTrue(result["ok"], result)
            self.assertEqual(len(proxied), 0, "planning context reached the configured proxy")
            self.assertEqual(len(received), 1)
            self.assertIn(CANARY.encode(), received[0]["body"])
            self.assertEqual(received[0]["path"], "/api/chat")
            self.assertTrue(result["global_unchanged"], result)

    def test_planner_works_without_proxy_and_with_explicit_bypass(self):
        for mode in ("no_proxy_configured", "explicit_bypass"):
            with self.subTest(mode=mode):
                with fake_server() as (backend, received), fake_server() as (proxy, proxied):
                    result = self.client(backend, proxy if mode == "explicit_bypass" else None,
                                         "127.0.0.1" if mode == "explicit_bypass" else None)
                    self.assertTrue(result["ok"], result)
                    self.assertEqual(len(received), 1)
                    self.assertEqual(proxied, [])

    def test_preinstalled_global_opener_is_not_used_or_replaced(self):
        with fake_server() as (backend, received):
            result = self.client(backend, trap=True)
            self.assertTrue(result["ok"], result)
            self.assertTrue(result["global_unchanged"], result)
            self.assertEqual(len(received), 1)

    def test_redirects_never_reach_a_second_server(self):
        # The target is also loopback: refusal is verified without contacting an
        # external address. Reject all redirects rather than interpreting targets.
        for code in (301, 302, 303, 307, 308):
            with self.subTest(code=code):
                with fake_server() as (target, target_receipts):
                    with fake_server(target + "/redirected", code) as (backend, received):
                        result = self.client(backend)
                        self.assertFalse(result["ok"], result)
                        self.assertEqual(result["type"], "AgentRequestError")
                        self.assertIn(f"HTTP Error {code}", result["error"])
                        self.assertEqual(len(received), 1)
                        self.assertEqual(target_receipts, [])


    def test_get_redirect_handler_distinguishes_custom_307_308_from_default(self):
        # Default urllib follows GET 307/308; our request-local handler must not.
        # POST-only 307/308 controls cannot distinguish these implementations.
        for code in (307, 308):
            with self.subTest(code=code):
                with fake_server() as (target, target_receipts):
                    with fake_server(target + "/redirected", code) as (backend, received):
                        def run(mode):
                            process = subprocess.run(
                                [sys.executable, "-B", "-c", GET_REDIRECT_PROBE,
                                 backend + "/api/chat", mode],
                                env=self.environment(), capture_output=True,
                                text=True, timeout=20,
                            )
                            self.assertEqual(process.returncode, 0, process.stderr)
                            return json.loads(process.stdout)
                        baseline = run("default")
                        self.assertTrue(baseline["ok"], baseline)
                        self.assertEqual(len(received), 1)
                        self.assertEqual(len(target_receipts), 1)
                        self.assertEqual(target_receipts[0]["method"], "GET")
                        protected = run("protected")
                        self.assertFalse(protected["ok"], protected)
                        self.assertEqual(protected["type"], "HTTPError")
                        self.assertEqual(protected["code"], code)
                        self.assertEqual(len(received), 2)
                        self.assertEqual(len(target_receipts), 1)


    def test_ipv6_loopback_bypasses_ipv4_proxy(self):
        with fake_server(host="::1") as (backend, received), fake_server() as (proxy, proxied):
            result = self.client(backend, proxy)
            self.assertTrue(result["ok"], result)
            self.assertEqual(len(received), 1)
            self.assertEqual(proxied, [])
            self.assertEqual({a[0] for a in result["attempts"]}, {"::1"})

    def test_real_localhost_resolution_is_pinned_to_loopback(self):
        selected = self.localhost_binding()
        with fake_server(host=selected) as (backend, received), fake_server() as (proxy, proxied):
            result = self.client(self.hostname_localhost(backend), proxy)
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["dns_calls"], ["localhost"])
            self.assertEqual({a[0] for a in result["attempts"]}, {selected})
            self.assertEqual(len(received), 1)
            self.assertEqual(proxied, [])


    def test_unsafe_localhost_resolution_is_rejected_before_connect(self):
        with fake_server() as (backend, received), fake_server() as (proxy, proxied):
            result = self.client(backend.replace("127.0.0.1", "localhost"), proxy, dns="unsafe")
            self.assertFalse(result["ok"], result)
            self.assertEqual(result["type"], "AgentRequestError")
            self.assertIn("localhost must resolve only to loopback", result["error"])
            self.assertEqual(result["attempts"], [])
            self.assertEqual(received, [])
            self.assertEqual(proxied, [])

    def test_localhost_is_not_resolved_again_after_validation(self):
        selected = self.localhost_binding()
        with fake_server(host=selected) as (backend, received):
            result = self.client(self.hostname_localhost(backend), dns="rebind")
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["dns_calls"], ["localhost"])
            self.assertEqual({a[0] for a in result["attempts"]}, {selected})
            self.assertEqual(len(received), 1)


    def test_correction_attempt_stays_direct_and_is_bounded(self):
        invalid = json.dumps({"message": {"content": "{}"}}).encode()
        for responses, expected_ok in (([invalid, RESPONSE], True), ([invalid], False)):
            with self.subTest(expected_ok=expected_ok):
                with fake_server(responses=responses) as (backend, received), fake_server() as (proxy, proxied):
                    result = self.client(backend, proxy)
                    self.assertEqual(result["ok"], expected_ok, result)
                    self.assertEqual(len(received), 2)
                    self.assertEqual(proxied, [])
                    self.assertTrue(all(row["path"] == "/api/chat" for row in received))
                    correction = json.loads(received[1]["body"])
                    self.assertIn("Do not return stages", correction["messages"][-1]["content"])
                    if not expected_ok:
                        self.assertIn("one correction attempt", result["error"])

    def test_external_redirects_are_rejected_before_outbound_connect(self):
        for code in (301, 302, 303, 307, 308):
            with self.subTest(code=code):
                with fake_server("http://192.0.2.1:9/never-contact", code) as (backend, received):
                    result = self.client(backend)
                    self.assertFalse(result["ok"], result)
                    self.assertEqual(result["type"], "AgentRequestError")
                    self.assertIn(f"HTTP Error {code}", result["error"])
                    self.assertEqual(len(received), 1)
                    self.assertEqual({a[0] for a in result["attempts"]}, {"127.0.0.1"})

    def test_ipv6_redirects_never_reach_a_second_server(self):
        for code in (301, 302, 303, 307, 308):
            with self.subTest(code=code):
                with fake_server(host="::1") as (target, target_receipts):
                    with fake_server(target + "/redirected", code, host="::1") as (backend, received):
                        result = self.client(backend)
                        self.assertFalse(result["ok"], result)
                        self.assertIn(f"HTTP Error {code}", result["error"])
                        self.assertEqual(len(received), 1)
                        self.assertEqual(target_receipts, [])


if __name__ == "__main__":
    unittest.main()
