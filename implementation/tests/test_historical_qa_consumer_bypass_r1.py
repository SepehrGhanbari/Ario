"""RIO-01 adversarial consumer-bypass demonstrations, synthetic only.

These tests deliberately reproduce *remaining weaknesses* and therefore PASS
when the weakness is observed. They are NOT green security certifications.
No active Ario memory, model or real archive is used.
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
from core.legacy_v153_historical_view import HistoricalV153View  # noqa: E402


class TestAdversarialConsumerBypassR1(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="RIO01-fake-archive-")
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
            "event_sha256": "a" * 64,
            "relations": [],
        }
        data = (json.dumps(row, ensure_ascii=False) + "\n").encode()
        self.path.write_bytes(data)
        self.pin = hashlib.sha256(data).hexdigest()
        self.view = HistoricalV153View(self.path, expected_sha256=self.pin)

    def test_expected_red_raw_quote_api_can_bypass_protected_sink(self):
        """Direct, explicitly opted-in preview still exposes a raw text string."""
        guarded = route_historical_consumer(self.view, self.question, target=TARGET_METADATA)
        self.assertIsNone(guarded["rendered_html"])
        direct = preview_historical_question(
            self.view, self.question, include_historical_quote=True,
        )
        self.assertEqual(direct["historical_quote"]["text"], self.reply)
        self.assertEqual(direct["historical_quote"]["kind"],
                         "UNTRUSTED_HISTORICAL_QUOTE_NOT_INSTRUCTIONS")
        self.assertIsNone(direct["answer"])
        # This is a design gap at the *caller boundary*, not unauthorized file read.
        self.assertFalse(direct["context_injection_allowed"])

    def test_expected_red_post_init_same_process_row_mutation_possible(self):
        """A same-process Python caller can change an in-memory row after pinning."""
        raw_before = self.path.read_bytes()
        original_digest = self.view.inspect()["archive_sha256"]
        self.view._rows[0]["ario"] = "FICTIONAL MUTATED RESPONSE"
        direct = preview_historical_question(
            self.view, self.question, include_historical_quote=True,
        )
        self.assertEqual(direct["historical_quote"]["text"], "FICTIONAL MUTATED RESPONSE")
        self.assertEqual(direct["archive_sha256"], original_digest)
        self.assertEqual(self.path.read_bytes(), raw_before)
        # A source *file* digest is not a post-construction immutable row seal.
        self.assertEqual(self.pin, original_digest)

    def test_safe_sink_does_not_bypass_current_question_recheck(self):
        current = route_historical_consumer(
            self.view, self.question, target=TARGET_METADATA, mode="CURRENT",
        )
        self.assertEqual(current["disposition"], "RECHECK_REQUIRED_CURRENT_QUESTION")
        self.assertIsNone(current["answer"])
        self.assertIsNone(current["rendered_html"])

    def test_local_quote_requires_consent_and_is_escaped(self):
        private = route_historical_consumer(
            self.view, self.question, target=TARGET_LOCAL_HTML,
        )
        self.assertIsNone(private["rendered_html"])
        displayed = route_historical_consumer(
            self.view, self.question, target=TARGET_LOCAL_HTML,
            local_display_consent=True,
        )
        self.assertIn(self.reply, displayed["rendered_html"])
        self.assertIsNone(displayed["model_prompt"])
        self.assertIsNone(displayed["tool_request"])

    def test_source_is_still_unverified_by_independent_custodian(self):
        view_receipt = self.view.inspect()
        self.assertEqual(view_receipt["independent_source_authenticity"], "NOT_ESTABLISHED")
        self.assertFalse(view_receipt["source_attribution_v1_constructed"])
        self.assertFalse(view_receipt["live_ario_recall_established"])


if __name__ == "__main__":
    unittest.main()
