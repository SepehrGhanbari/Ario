"""Synthetic-only tests of a localhost no-tools Ollama probe: NEVER network."""
from __future__ import annotations

import contextlib
from io import StringIO
import json
from pathlib import Path
import sys
import unittest

# Import research module without installing it or running its CLI.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.historical_qa_ollama_probe_r0.ollama_synthetic_probe import (  # noqa: E402
    ATTACK, ATTACKS, SAFE, URL, ProbeHold, _bounded_response,
    _classify, main, run_fixed_probes,
)


class TestSyntheticNoToolsOllamaProbe(unittest.TestCase):
    def test_fixed_4_requests_fake_safe_response(self):
        payloads = []
        def send(payload):
            payloads.append(payload)
            return {"message": {"role": "assistant", "content": SAFE}}
        receipt = run_fixed_probes(model="llama3.2", send=send)
        self.assertEqual(receipt["request_count"], 4)
        self.assertEqual(len(payloads), 4)
        self.assertTrue(all(r["outcome"] == "SAFE_MARKER_ONLY" for r in receipt["cases"]))
        self.assertFalse(receipt["model_security_proven"])
        self.assertFalse(receipt["isolated_os_sandbox_established"])

    def test_control_arm_detects_mock_role_spoofing(self):
        def mock_reply(payload):
            system = payload["messages"][0]["content"]
            has_untrusted_text_in_system = "BEGIN UNTRUSTED ARCHIVAL QUOTE" in system
            return {"message": {"content": ATTACK if has_untrusted_text_in_system else SAFE}}
        receipt = run_fixed_probes(send=mock_reply)
        self.assertEqual(
            [x["outcome"] for x in receipt["cases"]],
            ["SAFE_MARKER_ONLY", "ATTACK_MARKER_OBSERVED"] * 2,
        )

    def test_no_tools_no_files_no_real_archive_in_any_request(self):
        seen = []
        def capture(payload):
            seen.append(payload)
            return {"message": {"content": SAFE}}
        receipt = run_fixed_probes(send=capture)
        for payload in seen:
            self.assertEqual(set(payload), {"model", "messages", "stream", "options"})
            self.assertIs(payload["stream"], False)
            self.assertEqual([x["role"] for x in payload["messages"]], ["system", "user"])
            self.assertNotIn("tools", payload)
            self.assertNotIn("tool_choice", payload)
            self.assertNotIn("archive_path", json.dumps(payload))
            self.assertNotIn("QwenMemory", json.dumps(payload))
        self.assertFalse(receipt["private_archive_sent"])
        self.assertFalse(receipt["tool_execution_possible_by_probe"])

    def test_fixed_loopback_endpoint(self):
        self.assertEqual(URL, "http://127.0.0.1:11434/api/chat")

    def test_model_name_rejects_invalid_or_nonlocal_config(self):
        for bad in ("", "model with spaces", "x;curl", "https://evil.test", "a" * 81, 3, None):
            with self.subTest(value=repr(bad)):
                with self.assertRaisesRegex(ProbeHold, "HOLD_BAD_MODEL_NAME"):
                    run_fixed_probes(model=bad, send=lambda _: self.fail("should not send"))

    def test_local_model_name_accepts_ollama_tags(self):
        for name in ("llama3.2", "qwen2.5:7b", "qwen2.5:7b-instruct"):
            got = run_fixed_probes(model=name, send=lambda _: {"message": {"content": SAFE}})
            self.assertEqual(got["model"], name)

    def test_tool_intent_never_executed_and_classified(self):
        receipt = run_fixed_probes(send=lambda _: {
            "message": {"content": SAFE, "tool_calls": [{"function": {"name": "pretend"}}]}
        })
        self.assertTrue(all(x["outcome"] == "UNEXPECTED_TOOL_INTENT_NO_EXECUTION" for x in receipt["cases"]))
        self.assertFalse(receipt["tool_execution_possible_by_probe"])

    def test_echoed_secret_model_reply_does_not_leak_to_receipt(self):
        secret = "SYNTHETIC_PRIVATE_MODEL_RESPONSE_NEVER_PRINT"
        receipt = run_fixed_probes(send=lambda _: {"message": {"content": secret}})
        self.assertNotIn(secret, json.dumps(receipt))
        self.assertEqual(receipt["request_count"], 4)
        self.assertTrue(all(x["raw_reply_hidden"] for x in receipt["cases"]))

    def test_invalid_envelope_rejected(self):
        for response in (None, {}, [], {"message": None}, {"message": []}):
            with self.subTest(response=repr(response)):
                with self.assertRaisesRegex(ProbeHold, "HOLD_INVALID_MODEL_ENVELOPE"):
                    _bounded_response(response)

    def test_invalid_content_rejected(self):
        for content in (None, False, 4, {}, "A" * 8193):
            with self.subTest(type=type(content).__name__):
                with self.assertRaisesRegex(ProbeHold, "HOLD_INVALID_MODEL_CONTENT"):
                    _bounded_response({"message": {"content": content}})

    def test_no_transport_or_unexpected_output_schema(self):
        with self.assertRaisesRegex(ProbeHold, "HOLD_INVALID_TRANSPORT"):
            run_fixed_probes(send=False)

    def test_attack_marker_overrides_safe_marker_for_classification(self):
        self.assertEqual(_classify("SAFE_ONLY but " + ATTACK, False), "ATTACK_MARKER_OBSERVED")
        self.assertEqual(_classify("anything", True), "UNEXPECTED_TOOL_INTENT_NO_EXECUTION")
        self.assertEqual(_classify("maybe yes", False), "INDETERMINATE_RESPONSE")

    def test_cli_needs_explicit_opt_in_without_any_network_call(self):
        out = StringIO()
        with contextlib.redirect_stdout(out):
            code = main([])
        self.assertEqual(code, 2)
        data = json.loads(out.getvalue())
        self.assertEqual(data["status"], "HOLD_EXPLICIT_LOCAL_OPT_IN_REQUIRED")

    def test_no_real_archive_input_options_exist(self):
        # Structural guarantee: tests check exactly hardcoded fictional strings.
        self.assertEqual(len(ATTACKS), 2)
        self.assertNotIn("ARIO_ARCHIVE_V15_3.jsonl", json.dumps(ATTACKS))
        self.assertNotIn("Ario_Backup", json.dumps(ATTACKS))

    def test_results_never_claim_trust_or_live_memory(self):
        data = run_fixed_probes(send=lambda _: {"message": {"content": SAFE}})
        self.assertFalse(data["live_ario_recall_established"])
        self.assertFalse(data["production_authorized"])
        self.assertFalse(data["trust_activation"])
        self.assertEqual(data["evidence_admission"], "NO_ADMISSION")
        self.assertEqual(data["files_written_by_probe"], 0)
        self.assertEqual(data["ollama_service_internal_writes"], "NOT_AUDITED")


if __name__ == "__main__":
    unittest.main()
