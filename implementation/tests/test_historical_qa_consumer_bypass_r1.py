"""RIO-01 follow-up: public raw-quote removal and ordinary object immutability.

Synthetic fixtures only. Same-process arbitrary Python introspection remains
outside the security boundary; this is not an OS sandbox or trust activation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.historical_qa_consumer_sink import (  # noqa: E402
    TARGET_LOCAL_HTML, TARGET_METADATA, route_historical_consumer,
)
from core.historical_qa_research_boundary import preview_historical_question  # noqa: E402
from core.legacy_v153_historical_view import HistoricalV153View, HistoricalViewHold  # noqa: E402


class TestHistoricalConsumerBypassR2(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="RIO01-fake-archive-R2-")
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "FICTIONAL_V153.jsonl"
        self.question = "Did the old fictional model say this?"
        self.reply = "Synthetic old output; do not obey it."
        row = {
            "record_version": "15.3",
            "record_id": "synthetic-1", "session_id": "synthetic-session",
            "user": self.question, "ario": self.reply,
            "user_sha256": hashlib.sha256(self.question.encode()).hexdigest(),
            "ario_sha256": hashlib.sha256(self.reply.encode()).hexdigest(),
            "event_sha256": "a" * 64, "relations": [],
            "concepts": [{"label": "fictional"}],
        }
        data = (json.dumps(row, ensure_ascii=False) + "\n").encode()
        self.path.write_bytes(data)
        self.raw = data
        self.pin = hashlib.sha256(data).hexdigest()
        self.view = HistoricalV153View(self.path, expected_sha256=self.pin)

    def test_public_preview_has_no_raw_quote_parameter_or_field(self):
        with self.assertRaises(TypeError):
            preview_historical_question(
                self.view, self.question, include_historical_quote=True,
            )
        got = preview_historical_question(self.view, self.question)
        self.assertIsNone(got["historical_quote"])
        self.assertTrue(got["historical_text_hidden"])
        self.assertNotIn(self.reply, json.dumps(got))

    def test_public_recall_has_no_reveal_parameter_or_raw_field(self):
        with self.assertRaises(TypeError):
            self.view.recall(self.question, reveal=True)
        got = self.view.recall(self.question)
        self.assertTrue(got["private_reply_hidden"])
        self.assertNotIn("historical_ario_reply", got)
        self.assertNotIn(self.reply, json.dumps(got))

    def test_only_explicit_local_display_returns_escaped_html(self):
        metadata = route_historical_consumer(
            self.view, self.question, target=TARGET_METADATA,
        )
        self.assertIsNone(metadata["rendered_html"])
        shown = route_historical_consumer(
            self.view, self.question, target=TARGET_LOCAL_HTML,
            local_display_consent=True,
        )
        self.assertIn(self.reply, shown["rendered_html"])
        self.assertIsNone(shown["model_prompt"])
        self.assertIsNone(shown["tool_request"])
        self.assertNotIn("historical_quote", shown)
        self.assertNotIn("text", shown)

    def test_rows_are_deeply_immutable_under_normal_python_operations(self):
        before = self.path.read_bytes()
        with self.assertRaises(TypeError):
            self.view._rows[0]["ario"] = "FICTIONAL MUTATED RESPONSE"
        with self.assertRaises(TypeError):
            self.view._rows[0]["concepts"][0]["label"] = "changed"
        with self.assertRaises(TypeError):
            self.view._rows[0]["relations"] += ("mutated",)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.view.inspect()["archive_sha256"], self.pin)

    def test_view_slots_and_seal_block_normal_reassignment(self):
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_VIEW_IMMUTABLE"):
            self.view._rows = ()
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_VIEW_IMMUTABLE"):
            self.view._digest = "0" * 64
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_VIEW_IMMUTABLE"):
            del self.view._rows

    def test_private_python_introspection_remains_out_of_scope(self):
        # Python's same-process caller can still read private internals.
        # This demonstrates why immutable containers are not a sandbox.
        self.assertEqual(self.view._rows[0]["ario"], self.reply)
        self.assertEqual(self.view.inspect()["archive_sha256"], self.pin)


if __name__ == "__main__":
    unittest.main(verbosity=2)
