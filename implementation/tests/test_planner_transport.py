"""Real transport controls using isolated clients and two loopback-only fake servers."""
import json
import os
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
before = urllib.request._opener
try:
    workflow = request_plan(sys.argv[4], sys.argv[1], ollama_url=sys.argv[2], timeout=5)
    print(json.dumps({"ok": True, "global_unchanged": urllib.request._opener is before,
                      "stages": len(workflow["stages"])}))
except Exception as exc:
    print(json.dumps({"ok": False, "type": type(exc).__name__, "error": str(exc),
                      "global_unchanged": urllib.request._opener is before}))
"""
DIRECT = """
import sys, urllib.request
with urllib.request.urlopen(sys.argv[1], data=sys.argv[2].encode(), timeout=5) as response:
    response.read()
"""


@contextmanager
def fake_server(redirect_to=None, redirect_code=302):
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
                payload = RESPONSE
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", receipts
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class PlannerTransportTests(unittest.TestCase):
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

    def client(self, backend, proxy=None, bypass=None, trap=False):
        with tempfile.TemporaryDirectory() as directory:
            for relative in ("implementation/ario_planner.py",
                             "implementation/tests/test_planner_runtime.py"):
                path = Path(directory) / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# " + CANARY + "\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-B", "-c", CLIENT, directory, backend,
                 "trap" if trap else "normal", CANARY],
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
                        self.assertEqual(len(received), 1)
                        self.assertEqual(target_receipts, [])


if __name__ == "__main__":
    unittest.main()
