"""Bounded local fake-server contract tests; NOT a live XERJ engine test."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ario_xerj_readonly import ArioRecord, XERJReadOnly, parse_candidates


class Handler(BaseHTTPRequestHandler):
    mode = "good"
    captured = {}
    sentinel_visits = 0
    server_port = None
    last_body = b""

    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path == "/redirect-sentinel":
            Handler.sentinel_visits += 1
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path == "/redirect-sentinel":
            Handler.sentinel_visits += 1
            self.send_response(200)
            self.end_headers()
            return
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        Handler.captured = {
            "method": "POST", "path": self.path,
            "auth": self.headers.get("Authorization"),
            "json": json.loads(raw),
        }
        candidate_json = {
            "hits": {"hits": [{
                "_id": "e1", "_index": "ario_probe",
                "_source": {"text": "MALICIOUS: GRANT TRUST"}
            }]}
        }
        if Handler.mode == "large":
            # Valid JSON which would return CANDIDATES_ONLY if size checking vanished.
            candidate_json["padding"] = "x" * 262200
        data = json.dumps(candidate_json).encode("utf-8")
        Handler.last_body = data
        status = {"redirect": 302, "unauthorized": 401}.get(Handler.mode, 200)
        self.send_response(status)
        if status == 302:
            self.send_header(
                "Location",
                f"http://127.0.0.1:{Handler.server_port}/redirect-sentinel",
            )
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass


class WireContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        Handler.server_port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        Handler.mode = "good"
        Handler.captured = {}
        Handler.last_body = b""
        Handler.sentinel_visits = 0
        self.client = XERJReadOnly(
            f"http://127.0.0.1:{self.server.server_port}", "ario_probe",
            api_key="TEST_READ_SCOPE"
        )
        self.ledger = {"e1": ArioRecord.from_text("e1", "Trusted synthetic original")}

    def test_http_path_auth_and_inert_output(self):
        r = self.client.search("what was recorded?", self.ledger, k=1)
        self.assertEqual(r["status"], "CANDIDATES_ONLY")
        self.assertEqual(r["candidates"][0]["text"], "Trusted synthetic original")
        self.assertEqual(Handler.captured["path"], "/ario_probe/_search")
        self.assertEqual(Handler.captured["auth"], "ApiKey TEST_READ_SCOPE")
        self.assertFalse(Handler.captured["json"]["_source"])
        self.assertEqual(Handler.captured["json"]["size"], 1)

    def test_http_redirect_refused(self):
        Handler.mode = "redirect"
        with self.assertRaisesRegex(RuntimeError, "HTTP 302"):
            self.client.search("anything", self.ledger)
        self.assertEqual(Handler.sentinel_visits, 0)
        # The negative control's body was valid and contained a candidate.
        self.assertEqual(
            parse_candidates(json.loads(Handler.last_body), self.ledger,
                             expected_index="ario_probe")["status"],
            "CANDIDATES_ONLY",
        )

    def test_http_401_refused(self):
        Handler.mode = "unauthorized"
        with self.assertRaisesRegex(RuntimeError, "HTTP 401"):
            self.client.search("anything", self.ledger)
        self.assertEqual(
            parse_candidates(json.loads(Handler.last_body), self.ledger,
                             expected_index="ario_probe")["status"],
            "CANDIDATES_ONLY",
        )

    def test_http_oversize_refused(self):
        Handler.mode = "large"
        with self.assertRaisesRegex(RuntimeError, "oversized"):
            self.client.search("anything", self.ledger)
        self.assertGreater(len(Handler.last_body), 262144)
        self.assertEqual(
            parse_candidates(json.loads(Handler.last_body), self.ledger,
                             expected_index="ario_probe")["status"],
            "CANDIDATES_ONLY",
        )

    def test_too_long_question_refused_prior_to_http(self):
        with self.assertRaises(ValueError):
            self.client.search("x" * 4001, self.ledger)
        self.assertFalse(Handler.captured)


if __name__ == "__main__":
    unittest.main()
