import http.client
import io
import json
import socket
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from ario_agent import AgentRequestError, MAX_READ_BYTES
import ario_planner
from ario_planner import _local_ollama_endpoint, _validate_plan_quality, build_observation, request_plan


def ollama_response(payload):
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps({
        "message": {"content": json.dumps(payload)}
    }).encode("utf-8")
    return response


class LocalOllamaPlannerTests(unittest.TestCase):
    def response_from_memory(self, body, declared_length):
        header = b"" if declared_length is None else f"Content-Length: {declared_length}\r\n".encode("ascii")
        stream = io.BytesIO(b"HTTP/1.1 200 OK\r\n" + header + b"\r\n" + body)
        source = MagicMock(spec=socket.socket)
        source.makefile.return_value = stream
        response = ario_planner._StrictOllamaHTTPResponse(source)
        response.begin()
        self.addCleanup(response.close)
        return response

    def response_with_wire_headers(self, body, headers, wrap=False):
        header_lines = b"".join(name.encode("ascii") + b": " + value.encode("ascii") + b"\r\n"
                                for name, value in headers)
        source = MagicMock(spec=socket.socket)
        source.makefile.return_value = io.BytesIO(b"HTTP/1.1 200 OK\r\n" + header_lines + b"\r\n" + body)
        response = ario_planner._StrictOllamaHTTPResponse(source)
        response.begin()
        self.addCleanup(response.close)
        if wrap:
            # urllib.request returns an addinfourl wrapper around HTTPResponse.
            from urllib.response import addinfourl
            return addinfourl(response, response.headers, "http://127.0.0.1:11434/api/chat", 200)
        return response

    @patch("ario_planner.run_workflow")
    @patch("ario_planner._open_local_ollama")
    def test_malformed_http_framing_fails_before_decode_or_execution(self, open_response, run_workflow):
        body = json.dumps({"message": {"content": json.dumps(self.valid_recommendation())}}).encode()
        n = str(len(body))
        cases = {
            "conflicting_duplicate": [("Content-Length", n), ("Content-Length", str(len(body) + 1))],
            "identical_duplicate": [("Content-Length", n), ("Content-Length", n)],
            "comma_conflict": [("Content-Length", f"{n}, {len(body) + 1}")],
            "comma_identical": [("Content-Length", f"{n},{n}")],
            "negative": [("Content-Length", "-1")],
            "plus": [("Content-Length", "+1")],
            "nonnumeric": [("Content-Length", "invalid")],
            "huge_digits": [("Content-Length", "9" * 100)],
            "empty": [("Content-Length", "")],
            "transfer_and_length": [("Transfer-Encoding", "chunked"), ("Content-Length", n)],
            "unsupported_transfer": [("Transfer-Encoding", "identity")],
            "comma_transfer": [("Transfer-Encoding", "gzip, chunked")],
            "duplicate_transfer": [("Transfer-Encoding", "chunked"), ("Transfer-Encoding", "chunked")],
            "short_body": [("Content-Length", str(len(body) + 1))],
        }
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            ledger = Path(directory) / "events.jsonl"
            for wrap in (False, True):
                for label, headers in cases.items():
                    with self.subTest(wrap=wrap, case=label):
                        open_response.return_value = self.response_with_wire_headers(body, headers, wrap)
                        with patch.object(ario_planner, "loads_bounded", wraps=ario_planner.loads_bounded) as decode:
                            with redirect_stderr(io.StringIO()) as stderr:
                                rc = ario_planner.main(["--workspace", directory, "--goal", "Review the planner",
                                                        "--ledger", str(ledger), "--execute"])
                        self.assertEqual(rc, 2)
                        self.assertEqual(json.loads(stderr.getvalue())["status"], "UNKNOWN")
                        self.assertFalse(ledger.exists())
                        decode.assert_not_called()
            run_workflow.assert_not_called()
            self.assertEqual(open_response.call_count, 2 * len(cases))

    @patch("ario_planner._open_local_ollama")
    def test_supported_http_framing_preserves_valid_plans(self, open_response):
        body = json.dumps({"message": {"content": json.dumps(self.valid_recommendation())}}).encode()
        chunked = f"{len(body):X}\r\n".encode() + body + b"\r\n0\r\n\r\n"
        cases = [
            (body, []),
            (body, [("Content-Length", str(len(body)))]),
            (body, [("Content-Length", "000" + str(len(body)))]),
            (chunked, [("Transfer-Encoding", "chunked")]),
            (chunked, [("Transfer-Encoding", "chunked ")]),
            (chunked, [("Transfer-Encoding", "ChUnKeD\t")]),
        ]
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            for wrap in (False, True):
                for wire_body, headers in cases:
                    with self.subTest(wrap=wrap, headers=headers):
                        open_response.return_value = self.response_with_wire_headers(wire_body, headers, wrap)
                        self.assertTrue(request_plan("Review the planner", directory)["stages"])

    @patch("ario_planner.run_workflow")
    @patch("ario_planner._open_local_ollama")
    def test_chunk_size_and_trailer_grammar_rejected_before_decode(self, open_response, run_workflow):
        body = json.dumps({"message": {"content": json.dumps(self.valid_recommendation())}}).encode()
        size = f"{len(body):X}".encode()
        cases = {
            "chunk_size_lf": size + b"\n" + body + b"\r\n0\r\n\r\n",
            "leading_space": b" " + size + b"\r\n" + body + b"\r\n0\r\n\r\n",
            "signed_chunk_size": b"+" + size + b"\r\n" + body + b"\r\n0\r\n\r\n",
            "malformed_extension": size + b';x="unterminated\r\n' + body + b"\r\n0\r\n\r\n",
            "last_chunk_lf": size + b"\r\n" + body + b"\r\n0\n\r\n",
            "missing_trailer_end": size + b"\r\n" + body + b"\r\n0\r\n",
            "trailer_lf": size + b"\r\n" + body + b"\r\n0\r\nX-Review: yes\n\n",
            "trailer_without_name": size + b"\r\n" + body + b"\r\n0\r\n bad\r\n\r\n",
            "forbidden_trailer": size + b"\r\n" + body + b"\r\n0\r\nContent-Length: 1\r\n\r\n",
            "oversized_chunk_size": b"F" * 200 + b"\r\n" + body + b"\r\n0\r\n\r\n",
        }
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            ledger = Path(directory) / "events.jsonl"
            for wrap in (False, True):
                for label, wire in cases.items():
                    with self.subTest(wrap=wrap, malformed=label):
                        open_response.return_value = self.response_with_wire_headers(
                            wire, [("Transfer-Encoding", "chunked")], wrap
                        )
                        with patch.object(ario_planner, "loads_bounded", wraps=ario_planner.loads_bounded) as decode:
                            with redirect_stderr(io.StringIO()) as stderr:
                                rc = ario_planner.main([
                                    "--workspace", directory, "--goal", "Review the planner",
                                    "--ledger", str(ledger), "--execute",
                                ])
                        self.assertEqual(rc, 2)
                        self.assertEqual(json.loads(stderr.getvalue())["status"], "UNKNOWN")
                        decode.assert_not_called()
                        self.assertFalse(ledger.exists())
            run_workflow.assert_not_called()

    @patch("ario_planner._open_local_ollama")
    def test_valid_chunk_extension_trailer_and_two_chunks(self, open_response):
        body = json.dumps({"message": {"content": json.dumps(self.valid_recommendation())}}).encode()
        left, right = body[:len(body) // 2], body[len(body) // 2:]
        fixtures = (
            f'{len(body):X};audit=ok\r\n'.encode() + body + b"\r\n0\r\n\r\n",
            f'{len(body):X};audit="reviewed"\r\n'.encode() + body + b"\r\n0\r\n\r\n",
            f'{len(body):X}\r\n'.encode() + body + b"\r\n0\r\nX-Review: yes\r\n\r\n",
            f'{len(left):X}\r\n'.encode() + left + b"\r\n" +
            f'{len(right):X}\r\n'.encode() + right + b"\r\n0\r\n\r\n",
        )
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            for wrap in (False, True):
                for wire in fixtures:
                    with self.subTest(wrap=wrap, fixture_size=len(wire)):
                        open_response.return_value = self.response_with_wire_headers(
                            wire, [("Transfer-Encoding", "chunked")], wrap
                        )
                        self.assertTrue(request_plan("Review the planner", directory)["stages"])

    @patch("ario_planner.run_workflow")
    @patch("ario_planner._open_local_ollama")
    def test_too_many_chunk_headers_fail_closed(self, open_response, run_workflow):
        body = json.dumps({"message": {"content": json.dumps(self.valid_recommendation())}}).encode()
        # Prefix with valid JSON whitespace: without an explicit chunk-count
        # bound, the decoded JSON would still be accepted as a valid plan.
        wire = (b"1\r\n \r\n" * ario_planner._MAX_OLLAMA_CHUNKS
                + f"{len(body):X}\r\n".encode() + body + b"\r\n0\r\n\r\n")
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            ledger = Path(directory) / "events.jsonl"
            for wrap in (False, True):
                with self.subTest(wrap=wrap):
                    open_response.return_value = self.response_with_wire_headers(
                        wire, [("Transfer-Encoding", "chunked")], wrap
                    )
                    with patch.object(ario_planner, "loads_bounded", wraps=ario_planner.loads_bounded) as decode:
                        with redirect_stderr(io.StringIO()) as stderr:
                            rc = ario_planner.main([
                                "--workspace", directory, "--goal", "Review the planner",
                                "--ledger", str(ledger), "--execute",
                            ])
                    self.assertEqual(rc, 2)
                    self.assertEqual(json.loads(stderr.getvalue())["status"], "UNKNOWN")
                    self.assertFalse(ledger.exists())
                    decode.assert_not_called()
            run_workflow.assert_not_called()

    @patch("ario_planner.run_workflow")
    @patch("ario_planner._open_local_ollama")
    def test_invalid_chunk_data_terminator_never_decodes_or_executes(self, open_response, run_workflow):
        body = json.dumps({"message": {"content": json.dumps(self.valid_recommendation())}}).encode()
        midpoint = len(body) // 2
        part1, part2 = body[:midpoint], body[midpoint:]
        malformed = {
            "XX": f"{len(body):X}\r\n".encode() + body + b"XX0\r\n\r\n",
            "LF_only": f"{len(body):X}\r\n".encode() + body + b"\n\n0\r\n\r\n",
            "CR_wrong": f"{len(body):X}\r\n".encode() + body + b"\rX0\r\n\r\n",
            "no_delimiter": f"{len(body):X}\r\n".encode() + body + b"0\r\n\r\n",
            "second_chunk": (f"{len(part1):X}\r\n".encode() + part1 + b"\r\n"
                             + f"{len(part2):X}\r\n".encode() + part2 + b"XX0\r\n\r\n"),
        }
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            ledger = Path(directory) / "ledger.jsonl"
            for wrap in (False, True):
                for label, wire in malformed.items():
                    with self.subTest(wrap=wrap, malformed=label):
                        open_response.return_value = self.response_with_wire_headers(
                            wire, [("Transfer-Encoding", "chunked")], wrap
                        )
                        with patch.object(ario_planner, "loads_bounded", wraps=ario_planner.loads_bounded) as decode:
                            with redirect_stderr(io.StringIO()) as stderr:
                                rc = ario_planner.main([
                                    "--workspace", directory, "--goal", "Review the planner",
                                    "--ledger", str(ledger), "--execute",
                                ])
                        self.assertEqual(rc, 2)
                        self.assertEqual(json.loads(stderr.getvalue())["status"], "UNKNOWN")
                        decode.assert_not_called()
                        self.assertFalse(ledger.exists())
            self.assertEqual(open_response.call_count, 2 * len(malformed))
            run_workflow.assert_not_called()

    @patch("ario_planner._open_local_ollama")
    def test_valid_two_chunk_message_retains_normal_planning(self, open_response):
        body = json.dumps({"message": {"content": json.dumps(self.valid_recommendation())}}).encode()
        a, b = body[:len(body) // 2], body[len(body) // 2:]
        wire = f"{len(a):X}\r\n".encode() + a + b"\r\n" + f"{len(b):X}\r\n".encode() + b + b"\r\n0\r\n\r\n"
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            for wrap in (False, True):
                with self.subTest(wrap=wrap):
                    open_response.return_value = self.response_with_wire_headers(
                        wire, [("Transfer-Encoding", "chunked")], wrap
                    )
                    self.assertTrue(request_plan("Review the planner", directory)["stages"])

    def test_local_http_opener_uses_strict_response_class(self):
        request = ario_planner.urllib.request.Request("http://127.0.0.1:11434/api/chat", data=b"{}")
        with patch.object(ario_planner.urllib.request, "build_opener") as build:
            ario_planner._open_local_ollama(request, timeout=3)
            handlers = build.call_args.args
            strict = [handler for handler in handlers if isinstance(handler, ario_planner._StrictOllamaHTTPHandler)]
            self.assertEqual(len(strict), 1)
            self.assertIs(ario_planner._StrictOllamaHTTPConnection.response_class,
                          ario_planner._StrictOllamaHTTPResponse)
            with patch.object(strict[0], "do_open") as do_open:
                strict[0].http_open(request)
            self.assertIs(do_open.call_args.args[0], ario_planner._StrictOllamaHTTPConnection)

    @patch("ario_planner._open_local_ollama")
    def test_long_zero_padded_content_length_stays_valid(self, open_response):
        body = json.dumps({"message": {"content": json.dumps(self.valid_recommendation())}}).encode()
        wire_length = "0" * 32 + str(len(body))
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            for wrap in (False, True):
                with self.subTest(wrap=wrap):
                    open_response.return_value = self.response_with_wire_headers(
                        body, [("Content-Length", wire_length)], wrap
                    )
                    self.assertTrue(request_plan("Review the planner", directory)["stages"])

    @patch("ario_planner.run_workflow")
    @patch("ario_planner._open_local_ollama")
    def test_short_fixed_length_response_stops_before_json(self, open_response, run_workflow):
        open_response.return_value = self.response_from_memory(b"{}", 3)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger.jsonl"
            stderr = io.StringIO()
            with patch.object(ario_planner, "loads_bounded", wraps=ario_planner.loads_bounded) as decode:
                with redirect_stderr(stderr):
                    rc = ario_planner.main(["--workspace", directory, "--goal", "Review the planner",
                                            "--ledger", str(ledger), "--execute"])
            self.assertEqual(rc, 2)
            self.assertEqual(json.loads(stderr.getvalue())["status"], "UNKNOWN")
            self.assertFalse(ledger.exists())
            run_workflow.assert_not_called()
            open_response.assert_called_once()
            decode.assert_not_called()

    @patch("ario_planner._open_local_ollama")
    def test_complete_known_and_unknown_lengths_accept_normal_plan(self, open_response):
        body = json.dumps({"message": {"content": json.dumps(self.valid_recommendation())}}).encode()
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            for length in (len(body), None):
                with self.subTest(declared_length=length):
                    open_response.return_value = self.response_from_memory(body, length)
                    result = request_plan("Review the planner", directory)
                    self.assertTrue(result["stages"])

    def valid_workflow(self):
        return {
            "workflow_id": "WF-TEST",
            "goal": "Inspect workspace",
            "stages": [{
                "stage_id": "stage-source-review",
                "task": {
                    "task_id": "TASK-TEST",
                    "goal": "Read source and tests",
                    "actions": [
                        {"step_id": "step-source", "tool": "read_text", "path": "implementation/ario_planner.py"},
                        {"step_id": "step-tests", "tool": "read_text", "path": "implementation/tests/test_planner_runtime.py"},
                    ],
                },
            }],
        }

    def valid_recommendation(self):
        return {
            "implementation_path": "implementation/ario_planner.py",
            "test_path": "implementation/tests/test_planner_runtime.py",
            "engineering_question": "Which missing edge-case test would improve fail-closed planner validation?",
            "rationale": "The planner normalizes identifiers and validates model recommendations before constructing a workflow.",
        }

    def _populate_planner_context(self, directory):
        for relative in (
            "implementation/ario_planner.py",
            "implementation/tests/test_planner_runtime.py",
            "implementation/ario_workflow.py",
            "implementation/tests/test_workflow_runtime.py",
        ):
            path = Path(directory) / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# bounded test evidence", encoding="utf-8")

    def test_planner_prompt_requests_recommendation_not_workflow_structure(self):
        self.assertIn("not a workflow generator", ario_planner.SYSTEM_PROMPT)
        self.assertIn('"engineering_question"', ario_planner.SYSTEM_PROMPT)
        self.assertIn("Do not propose workflow stages", ario_planner.SYSTEM_PROMPT)

    def test_planning_context_prioritizes_planner_and_its_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = (
                "implementation/ario_planner.py",
                "implementation/tests/test_planner_runtime.py",
                "implementation/ario_workflow.py",
                "implementation/tests/test_workflow_runtime.py",
                "implementation/ario_agent.py",
                "implementation/tests/test_agent_runtime.py",
            )
            for relative in paths:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"# evidence from {relative}\n", encoding="utf-8")
            context = build_observation(root)["planning_context"]
            self.assertEqual([item["path"] for item in context], list(paths[:4]))

    def test_context_budget_keeps_both_approved_implementation_test_pairs_available(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = (
                "implementation/ario_planner.py",
                "implementation/tests/test_planner_runtime.py",
                "implementation/ario_workflow.py",
                "implementation/tests/test_workflow_runtime.py",
            )
            for relative in paths:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x" * 5_000, encoding="utf-8")

            context = build_observation(root)["planning_context"]
            observed_paths = {item["path"] for item in context}
            self.assertEqual(observed_paths, set(paths))
            self.assertLessEqual(
                sum(len(item["content"]) for item in context),
                ario_planner.MAX_CONTEXT_TOTAL_CHARS,
            )

    def test_endpoint_accepts_loopback_and_rejects_remote_hosts(self):
        self.assertEqual(_local_ollama_endpoint("http://127.0.0.1:11434"), "http://127.0.0.1:11434/api/chat")
        with self.assertRaisesRegex(AgentRequestError, "loopback"):
            _local_ollama_endpoint("http://example.com:11434")
        with self.assertRaisesRegex(AgentRequestError, "loopback"):
            _local_ollama_endpoint("https://127.0.0.1:11434")

    @patch("ario_planner.socket.getaddrinfo")
    def test_localhost_endpoint_pins_validated_loopback_ip(self, getaddrinfo):
        getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 11434)),
        ]

        endpoint = _local_ollama_endpoint("http://localhost:11434")

        self.assertEqual(endpoint, "http://127.0.0.1:11434/api/chat")
        getaddrinfo.assert_called_once_with("localhost", 11434, type=socket.SOCK_STREAM)

    @patch("ario_planner.socket.getaddrinfo")
    def test_localhost_endpoint_rejects_mixed_loopback_and_remote_resolution(self, getaddrinfo):
        getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 11434)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.25", 11434)),
        ]

        with self.assertRaisesRegex(AgentRequestError, "only to loopback"):
            _local_ollama_endpoint("http://localhost:11434")

    def test_observation_is_bounded_metadata_and_does_not_read_file_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "private.txt").write_text("secret body must not be sent", encoding="utf-8")
            observation = build_observation(root)
            self.assertIn({"path": "private.txt", "kind": "file"}, observation["entries"])
            self.assertNotIn("secret body must not be sent", json.dumps(observation))
            self.assertIn("does not read arbitrary file contents", observation["note"])

    def test_planning_context_reads_only_bounded_allowlisted_source_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            implementation = root / "implementation"
            implementation.mkdir()
            (implementation / "ario_agent.py").write_text("def safe_runtime():\n    return 'bounded-source-evidence'\n", encoding="utf-8")
            (root / "private.txt").write_text("DO NOT SEND THIS SECRET", encoding="utf-8")
            observation = build_observation(root)
            context = observation["planning_context"]
            self.assertEqual([item["path"] for item in context], ["implementation/ario_agent.py"])
            self.assertIn("bounded-source-evidence", context[0]["content"])
            self.assertNotIn("DO NOT SEND THIS SECRET", json.dumps(observation))
            self.assertLessEqual(sum(len(item["content"]) for item in context), ario_planner.MAX_CONTEXT_TOTAL_CHARS)

    @patch("ario_planner._open_local_ollama")
    def test_valid_recommendation_builds_deterministic_workflow(self, urlopen):
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            urlopen.return_value = ollama_response(self.valid_recommendation())
            plan = request_plan("Inspect this repository", directory)
            self.assertEqual(plan["goal"], "Inspect this repository")
            self.assertTrue(plan["workflow_id"].startswith("WF-PLANNER-"))
            self.assertEqual(len(plan["stages"]), 1)
            stage = plan["stages"][0]
            self.assertEqual(stage["stage_id"], "stage-source-review")
            self.assertTrue(stage["task"]["task_id"].startswith("TASK-PLANNER-"))
            self.assertEqual(
                [(a["tool"], a["path"]) for a in stage["task"]["actions"]],
                [
                    ("read_text", "implementation/ario_planner.py"),
                    ("read_text", "implementation/tests/test_planner_runtime.py"),
                ],
            )
            self.assertEqual(len({a["step_id"] for a in stage["task"]["actions"]}), 2)
            request = urlopen.call_args.args[0]
            self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
            sent = json.loads(request.data.decode("utf-8"))
            self.assertEqual(sent["model"], "qwen2.5:7b")
            self.assertEqual(sent["format"], "json")
            self.assertFalse(sent["stream"])
            self.assertEqual(urlopen.call_args.kwargs["timeout"], 300)

    @patch("ario_planner._open_local_ollama")
    def test_model_cannot_inject_duplicate_stage_ids_or_workflow_actions(self, urlopen):
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            old_style = {
                "workflow_id": "model-workflow",
                "goal": "model goal",
                "stages": [{"stage_id": "same", "task": {}}, {"stage_id": "same", "task": {}}],
            }
            urlopen.side_effect = [ollama_response(old_style), ollama_response(self.valid_recommendation())]
            plan = request_plan("Inspect repository", directory)
            self.assertEqual(urlopen.call_count, 2)
            self.assertEqual(len(plan["stages"]), 1)
            self.assertEqual(plan["stages"][0]["stage_id"], "stage-source-review")
            self.assertEqual(len(plan["stages"][0]["task"]["actions"]), 2)
            correction = json.loads(urlopen.call_args_list[1].args[0].data.decode("utf-8"))
            self.assertIn("Do not return stages, actions, IDs", correction["messages"][-1]["content"])

    @patch("ario_planner._open_local_ollama")
    def test_duplicate_stage_ids_are_not_part_of_recommendation_schema(self, urlopen):
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            invalid = self.valid_recommendation()
            invalid["stages"] = [{"stage_id": "same"}, {"stage_id": "same"}]
            urlopen.return_value = ollama_response(invalid)
            with self.assertRaisesRegex(AgentRequestError, "recommendation remained invalid"):
                request_plan("Inspect repository", directory)
            self.assertEqual(urlopen.call_count, 2)

    @patch("ario_planner._open_local_ollama")
    def test_planner_builds_complete_bounded_chunks_for_large_source_files(self, urlopen):
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            source = Path(directory) / "implementation/ario_planner.py"
            source.write_text("".join(f"line-{index:04d} " + ("x" * 90) + "\n" for index in range(300)), encoding="utf-8", newline="")
            urlopen.return_value = ollama_response(self.valid_recommendation())

            plan = request_plan("Inspect repository", directory)

            actions = plan["stages"][0]["task"]["actions"]
            source_actions = [a for a in actions if a["path"] == "implementation/ario_planner.py"]
            test_actions = [a for a in actions if a["path"] == "implementation/tests/test_planner_runtime.py"]
            self.assertGreaterEqual(len(source_actions), 2)
            self.assertEqual(len(test_actions), 1)
            self.assertEqual(source_actions[0]["start_line"], 1)
            self.assertTrue(source_actions[0]["expected_truncated"])
            self.assertEqual(source_actions[0]["expected_next_start_line"], source_actions[1]["start_line"])
            self.assertFalse(source_actions[-1]["expected_truncated"])
            self.assertFalse(test_actions[0]["expected_truncated"])
            self.assertLessEqual(len(actions), 8)

            result = ario_planner.run_workflow(plan, directory, Path(directory) / "events.jsonl")
            self.assertEqual(result["status"], "COMPLETED")
            steps = result["stages"][0]["task_result"]["steps"]
            for relative in (
                "implementation/ario_planner.py",
                "implementation/tests/test_planner_runtime.py",
            ):
                observed = "".join(
                    step["observation"]["content"]
                    for step in steps
                    if step["observation"].get("path") == relative
                )
                expected = (Path(directory) / relative).read_text(encoding="utf-8")
                self.assertEqual(observed, expected, relative)
            self.assertTrue(all(step["status"] == "SUCCEEDED" for step in steps))

    def test_oversized_source_line_is_rejected_with_bounded_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "implementation/source.py"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"x" * (MAX_READ_BYTES + 100))

            original_open = Path.open
            read_sizes = []

            class ReadlineRecorder:
                def __init__(self, stream):
                    self.stream = stream

                def __enter__(self):
                    self.stream.__enter__()
                    return self

                def __exit__(self, *args):
                    return self.stream.__exit__(*args)

                def __iter__(self):
                    return iter(self.stream)

                def readline(self, size=-1):
                    read_sizes.append(size)
                    return self.stream.readline(size)

            def tracked_open(path, *args, **kwargs):
                stream = original_open(path, *args, **kwargs)
                if path == target:
                    return ReadlineRecorder(stream)
                return stream

            with patch.object(Path, "open", tracked_open):
                with self.assertRaisesRegex(AgentRequestError, "line longer than"):
                    ario_planner._read_action_chunks(root, "implementation/source.py", "step-read")

            self.assertEqual(read_sizes, [MAX_READ_BYTES + 1])

    @patch("ario_planner._open_local_ollama")
    def test_recommendation_schema_error_gets_one_correction_attempt(self, urlopen):
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            urlopen.side_effect = [ollama_response({"unexpected": "extra"}), ollama_response(self.valid_recommendation())]
            plan = request_plan("Inspect repository", directory)
            self.assertEqual(len(plan["stages"]), 1)
            self.assertEqual(urlopen.call_count, 2)
            correction = json.loads(urlopen.call_args_list[1].args[0].data.decode("utf-8"))["messages"][-1]["content"]
            self.assertIn("implementation_path, test_path, engineering_question, rationale", correction)
            self.assertIn("Do not return stages, actions, IDs", correction)

    @patch("ario_planner._open_local_ollama")
    def test_model_conditions_are_rejected_and_never_enter_workflow(self, urlopen):
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            invalid = self.valid_recommendation()
            invalid["when"] = {"stage_id": "self", "status": "COMPLETED"}
            urlopen.side_effect = [ollama_response(invalid), ollama_response(self.valid_recommendation())]
            plan = request_plan("Inspect repository", directory)
            self.assertNotIn("when", plan["stages"][0])
            self.assertEqual(urlopen.call_count, 2)

    @patch("ario_planner._open_local_ollama")
    def test_recommendation_stops_after_one_correction_attempt(self, urlopen):
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            invalid = {"unexpected": "extra"}
            urlopen.side_effect = [ollama_response(invalid), ollama_response(invalid)]
            with self.assertRaisesRegex(AgentRequestError, "recommendation remained invalid"):
                request_plan("Inspect repository", directory)
            self.assertEqual(urlopen.call_count, 2)

    @patch("ario_planner._open_local_ollama")
    def test_unresolved_template_recommendation_is_rejected(self, urlopen):
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            template = self.valid_recommendation()
            template["engineering_question"] = "placeholder"
            urlopen.side_effect = [ollama_response(template), ollama_response(template)]
            with self.assertRaisesRegex(AgentRequestError, "recommendation remained invalid"):
                request_plan("Inspect repository", directory)

    def test_plan_quality_rejects_directory_only_plan_when_source_context_exists(self):
        workflow = {
            "stages": [{"task": {"actions": [{"tool": "inspect_directory", "path": "."}]}}]
        }
        observation = {"planning_context": [{"path": "implementation/ario_agent.py", "content": "def example(): pass"}]}
        with self.assertRaisesRegex(AgentRequestError, "only lists directories"):
            _validate_plan_quality(workflow, observation)

    def test_plan_quality_rejects_repeated_action_across_stages(self):
        action = {"step_id": "step", "tool": "read_text", "path": "implementation/ario_agent.py"}
        workflow = {"stages": [
            {"task": {"actions": [action]}},
            {"task": {"actions": [{**action, "step_id": "different"}]}},
        ]}
        with self.assertRaisesRegex(AgentRequestError, "duplicates an action"):
            _validate_plan_quality(workflow, {"planning_context": []})

    @patch("ario_planner._open_local_ollama")
    def test_timeout_must_be_within_supported_bounds(self, urlopen):
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            for timeout in (0, -1, 1801, True, "300"):
                with self.subTest(timeout=timeout):
                    with self.assertRaisesRegex(AgentRequestError, "timeout must be an integer"):
                        request_plan("Inspect repository", directory, timeout=timeout)

    @patch("ario_planner._open_local_ollama")
    def test_unapproved_paths_are_rejected_before_workflow_construction(self, urlopen):
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            invalid = self.valid_recommendation()
            invalid["implementation_path"] = "../outside.py"
            urlopen.side_effect = [ollama_response(invalid), ollama_response(invalid)]
            with self.assertRaisesRegex(AgentRequestError, "recommendation remained invalid"):
                request_plan("Inspect repository", directory)

    @patch("ario_planner._open_local_ollama")
    def test_malformed_ollama_envelope_is_rejected(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"message": {}}'
        urlopen.return_value = response
        with tempfile.TemporaryDirectory() as directory:
            self._populate_planner_context(directory)
            with self.assertRaisesRegex(AgentRequestError, "valid JSON recommendation"):
                request_plan("Inspect repository", directory)

    @patch("ario_planner.run_workflow")
    @patch("ario_planner.request_plan")
    def test_cli_is_plan_only_by_default(self, request_plan_mock, run_workflow_mock):
        request_plan_mock.return_value = self.valid_workflow()
        with patch("sys.argv", ["ario_planner.py", "--goal", "inspect", "--workspace", ".", "--ledger", "events.jsonl"]):
            with redirect_stdout(io.StringIO()) as output:
                code = ario_planner.main()
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "PLAN_READY")
        run_workflow_mock.assert_not_called()

    @patch("ario_planner.run_workflow")
    @patch("ario_planner.request_plan")
    def test_cli_executes_only_with_explicit_execute_flag(self, request_plan_mock, run_workflow_mock):
        request_plan_mock.return_value = self.valid_workflow()
        run_workflow_mock.return_value = {"status": "COMPLETED"}
        with patch("sys.argv", ["ario_planner.py", "--goal", "inspect", "--workspace", ".", "--ledger", "events.jsonl", "--execute"]):
            with redirect_stdout(io.StringIO()) as output:
                code = ario_planner.main()
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "COMPLETED")
        run_workflow_mock.assert_called_once()


    @patch("ario_planner.run_workflow")
    @patch("ario_planner.request_plan")
    def test_cli_never_executes_when_plan_validation_fails(self, request_plan_mock, run_workflow_mock):
        request_plan_mock.side_effect = AgentRequestError(
            "Ollama recommendation remained invalid after one correction attempt"
        )
        argv = [
            "ario_planner.py", "--goal", "inspect", "--workspace", ".",
            "--ledger", "events.jsonl", "--execute",
        ]
        with patch("sys.argv", argv):
            with redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
                code = ario_planner.main()

        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), "")
        error = json.loads(stderr.getvalue())
        self.assertEqual(error["status"], "UNKNOWN")
        self.assertIn("remained invalid", error["error"])
        run_workflow_mock.assert_not_called()
        request_plan_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
