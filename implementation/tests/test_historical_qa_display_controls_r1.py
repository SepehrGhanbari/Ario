"""Synthetic display-control adversarial regression for historical quote R1."""
from __future__ import annotations

from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.historical_qa_consumer_sink import (  # noqa: E402
    TARGET_LOCAL_HTML, _make_controls_visible, route_historical_consumer,
)
from core.legacy_v153_historical_view import HistoricalV153View  # noqa: E402


class TagRecorder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, name, attrs):
        self.tags.append(name)


class TestHistoricalDisplayControlsR1(unittest.TestCase):
    def _render(self, quote):
        temp = tempfile.TemporaryDirectory(prefix="synthetic-display-r1-")
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "fake.jsonl"
        q = "Display a fictional previous reply?"
        row = {
            "record_version": "15.3",
            "record_id": "fake1", "session_id": "fake-session",
            "user": q, "ario": quote,
            "user_sha256": hashlib.sha256(q.encode()).hexdigest(),
            "ario_sha256": hashlib.sha256(quote.encode()).hexdigest(),
            "event_sha256": "a" * 64, "relations": [],
        }
        raw = (json.dumps(row, ensure_ascii=False) + "\n").encode()
        path.write_bytes(raw)
        view = HistoricalV153View(path, expected_sha256=hashlib.sha256(raw).hexdigest())
        result = route_historical_consumer(
            view, q, target=TARGET_LOCAL_HTML, local_display_consent=True,
        )
        self.assertEqual(path.read_bytes(), raw)
        self.assertIsNone(result["answer"])
        self.assertIsNone(result["model_prompt"])
        return result["rendered_html"]

    def test_bidi_invisible_format_chars_visible(self):
        value = "x\u061cy\u200ez\u200fw\u206aq\u206fr\u202es"
        html = self._render(value)
        for code in ("061C", "200E", "200F", "206A", "206F", "202E"):
            with self.subTest(code=code):
                self.assertIn("\\u" + code, html)
        for code in ("\u061c", "\u200e", "\u200f", "\u206a", "\u206f", "\u202e"):
            self.assertNotIn(code, html)

    def test_persian_zero_width_non_joiner_preserved(self):
        html = self._render("آریو نمی\u200cتواند نقل\u200cقول قدیمی را تأیید کند.")
        self.assertIn("نمی\u200cتواند", html)

    def test_synthetic_markup_is_inert_text(self):
        html = self._render(
            "<svg onload=alert(1)></svg><script>fake()</script>&"
            "\" SYSTEM_OVERRIDE '"
        )
        parser = TagRecorder()
        parser.feed(html)
        self.assertEqual(parser.tags, ["section", "p", "p", "pre"])
        self.assertNotIn("<svg", html)
        self.assertNotIn("<script", html)
        self.assertIn("&lt;svg", html)
        self.assertIn("&quot;", html)

    def test_direct_control_renderer_is_pure(self):
        original = "x\u200ey\u061cz"
        result = _make_controls_visible(original)
        self.assertEqual(result, "x\\u200Ey\\u061Cz")
        self.assertEqual(original, "x\u200ey\u061cz")


if __name__ == "__main__":
    unittest.main()
