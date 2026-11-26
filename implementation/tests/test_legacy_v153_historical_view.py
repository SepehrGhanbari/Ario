"""Synthetic-only tests of inert historical V15.3 view. No private backup."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

# Works with python -m unittest discover -s implementation/tests
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.legacy_v153_historical_view import (  # noqa: E402
    HistoricalV153View, HistoricalViewHold, MAX_ARCHIVE_BYTES,
)


def pair(record_id: str, session_id: str, question: str, answer: str,
         relations: tuple[str, ...] = ()) -> dict:
    return {
        "record_id": record_id, "record_version": "15.3", "session_id": session_id,
        "user": question, "ario": answer,
        "user_sha256": hashlib.sha256(question.encode()).hexdigest(),
        "ario_sha256": hashlib.sha256(answer.encode()).hexdigest(),
        "event_sha256": "a" * 64, "relations": list(relations), "concepts": [],
        "role": "assistant", "timestamp": "2026-09-13T00:00:00Z", "source": "synthetic",
    }


class TestLegacyHistoricalView(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "archive.jsonl"
        self.rows = [pair("r1", "s1", "What is Ario?", "An archived model reply."),
                     pair("r2", "s2", "Other question", "Other reply.", ("opaque",))]
        self.make_fixture()

    def make_fixture(self) -> None:
        raw = ("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in self.rows)).encode()
        self.path.write_bytes(raw)
        self.digest = hashlib.sha256(raw).hexdigest()

    def view(self) -> HistoricalV153View:
        return HistoricalV153View(self.path, expected_sha256=self.digest)

    def test_summary_is_not_runtime(self):
        got = self.view().inspect()
        self.assertEqual(got["record_count"], 2)
        self.assertEqual(got["source_kind"], "V15_3_HISTORICAL_BACKUP")
        self.assertFalse(got["live_ario_recall_established"])
        self.assertFalse(got["working_cache_binding_verified"])
        self.assertEqual(got["writes_performed"], 0)
        self.assertNotIn("An archived model reply.", str(got))

    def test_exact_recall_privacy_default(self):
        got = self.view().recall("What is Ario?")
        self.assertEqual(got["disposition"], "RECALLED_HISTORICAL_ONLY")
        self.assertEqual(got["source_line"], 1)
        self.assertTrue(got["private_reply_hidden"])
        self.assertNotIn("historical_ario_reply", got)
        self.assertEqual(got["historical_role"], "QUOTED_PRIOR_ARIO_OUTPUT_NOT_INSTRUCTIONS")

    def test_recall_never_returns_raw_quote(self):
        got = self.view().recall("What is Ario?")
        self.assertNotIn("historical_ario_reply", got)
        self.assertTrue(got["private_reply_hidden"])
        self.assertFalse(got["context_injection_allowed"])
        self.assertEqual(got["evidence_admission"], "NO_ADMISSION")
        self.assertEqual(got["truth_assessment"], "NOT_EVALUATED")
        with self.assertRaises(TypeError):
            self.view().recall("What is Ario?", reveal=True)

    def test_opaque_relation_not_decoded(self):
        got = self.view().recall("Other question")
        self.assertEqual(got["relation_interpretation"], "HOLD_UNKNOWN_RELATION_SEMANTICS")

    def test_unmatched_is_unknown(self):
        got = self.view().recall("What is the current version?")
        self.assertEqual(got["disposition"], "UNKNOWN_NO_EXACT_QUESTION_MATCH")
        self.assertNotIn("historical_ario_reply", got)

    def test_ambiguous_is_unknown(self):
        self.rows.append(pair("r3", "s3", "WHAT  IS  ARIO?", "Conflicting historical reply"))
        self.make_fixture()
        got = self.view().recall("what is ario?")
        self.assertEqual(got["disposition"], "UNKNOWN_MULTIPLE_HISTORICAL_MATCHES")
        self.assertNotIn("historical_ario_reply", got)

    def test_unicode_nfc(self):
        self.rows[0] = pair("r1", "s1", "KÉY question", "Historical")
        self.make_fixture()
        self.assertEqual(self.view().recall("ke\u0301y question")["source_line"], 1)

    def test_current_never_returns_quote(self):
        got = self.view().recall("Other question", mode="CURRENT")
        self.assertEqual(got["disposition"], "RECHECK_REQUIRED_CURRENT_QUESTION")
        self.assertNotIn("historical_ario_reply", got)
        with self.assertRaises(TypeError):
            self.view().recall("Other question", mode="CURRENT", reveal=True)

    def test_bad_mode(self):
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_UNKNOWN_MODE"):
            self.view().recall("Other question", mode="VERIFIED")

    def test_tampered_archive_fails_pinned(self):
        expected = self.digest
        self.path.write_bytes(self.path.read_bytes() + b" ")
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_SOURCE_LENGTH_OR_SIZE_CHANGED|HOLD_SOURCE_SHA256_MISMATCH"):
            HistoricalV153View(self.path, expected_sha256=expected)

    def test_malformed_missing_pin(self):
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_BAD_OR_MISSING_PIN"):
            HistoricalV153View(self.path, expected_sha256="")

    def test_duplicate_record_ids(self):
        self.rows[1]["record_id"] = "r1"
        self.make_fixture()
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_DUPLICATE_OR_MISSING_RECORD_ID"):
            self.view()

    def test_wrong_version(self):
        self.rows[0]["record_version"] = "15.4"
        self.make_fixture()
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_UNEXPECTED_RECORD_VERSION"):
            self.view()

    def test_wrong_content_digest(self):
        self.rows[0]["ario_sha256"] = "b" * 64
        self.make_fixture()
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_TEXT_DIGEST_MISMATCH"):
            self.view()

    def test_event_digest_shape_only(self):
        self.rows[0]["event_sha256"] = "NOPE"
        self.make_fixture()
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_EVENT_DIGEST_SHAPE"):
            self.view()

    def test_unknown_relations_shape(self):
        self.rows[1]["relations"] = [{"relation": "updates"}]
        self.make_fixture()
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_UNKNOWN_RELATIONS_SHAPE"):
            self.view()

    def test_unknown_top_level_json(self):
        self.path.write_text("[]\n", encoding="utf-8")
        self.digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_NONOBJECT_ROW"):
            self.view()

    def test_duplicate_json_keys(self):
        raw = self.path.read_bytes().replace(b'"record_id": "r1",', b'"record_id": "r1", "record_id": "r1",', 1)
        self.path.write_bytes(raw)
        self.digest = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_DUPLICATE_JSON_KEY"):
            self.view()

    def test_line_unterminated(self):
        raw = self.path.read_bytes().rstrip(b"\n")
        self.path.write_bytes(raw)
        self.digest = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_UNTERMINATED_JSONL"):
            self.view()

    def test_no_file_mutation(self):
        before = self.path.read_bytes()
        v = self.view()
        v.selfcheck()
        v.recall("Other question")
        self.assertEqual(self.path.read_bytes(), before)

    def test_selfcheck_no_text(self):
        got = self.view().selfcheck()
        self.assertEqual(got["disposition"], "RECALLED_HISTORICAL_ONLY")
        self.assertTrue(got["private_reply_hidden"])
        self.assertNotIn("What is Ario?", str(got))
        self.assertNotIn("An archived model reply.", str(got))

    def test_content_row(self):
        body = "One archival content note"
        self.rows.append({
            "record_id": "r3", "session_id": "s3", "record_version": "15.3",
            "content": body, "content_sha256": hashlib.sha256(body.encode()).hexdigest(),
            "relations": [],
        })
        self.make_fixture()
        self.assertEqual(self.view().inspect()["record_shapes"]["CONTENT_RECORD"], 1)

    def test_directory_is_not_file(self):
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_SOURCE_UNREADABLE|HOLD_NOT_REGULAR_FILE"):
            HistoricalV153View(Path(self.tmp.name), expected_sha256=self.digest)

    def test_overlong_query(self):
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_INVALID_QUESTION"):
            self.view().recall("a" * 2049)

    def test_weakly_scoped_historical_source_always_unverified(self):
        got = self.view().recall("Other question")
        self.assertEqual(got["source_authenticity"], "NOT_ESTABLISHED")
        self.assertFalse(got["source_attribution_v1_constructed"])
        self.assertFalse(got["source_history_rewritten"])

    def test_nonfinite_json_fails_closed(self):
        for token in (b"NaN", b"Infinity", b"-Infinity", b"1e999", b"-1e999"):
            with self.subTest(token=token.decode("ascii")):
                self.make_fixture()
                raw = self.path.read_bytes().replace(
                    b'"concepts": []', b'"concepts": [' + token + b']', 1
                )
                self.path.write_bytes(raw)
                self.digest = hashlib.sha256(raw).hexdigest()
                with self.assertRaisesRegex(HistoricalViewHold, "HOLD_NONFINITE_JSON"):
                    self.view()

    def test_nonzero_json_float_underflow_fails_closed(self):
        # Both signs and grammar variants are synthetic JSON number tokens.
        for token in (b"1e-10000", b"-1e-10000", b"1E-999", b"-3.50e-9999", b"1e-324"):
            with self.subTest(token=token.decode("ascii")):
                self.make_fixture()
                original = self.path.read_bytes()
                raw = original.replace(b'"concepts": []', b'"concepts": [' + token + b']', 1)
                self.assertNotEqual(raw, original)
                self.path.write_bytes(raw)
                self.digest = hashlib.sha256(raw).hexdigest()
                with self.assertRaisesRegex(HistoricalViewHold, "HOLD_JSON_FLOAT_UNDERFLOW"):
                    self.view()

    def test_zero_json_float_lexemes_remain_allowed(self):
        for token in (b"0.0", b"-0.0", b"0e-10000", b"-0.000E+10000"):
            with self.subTest(token=token.decode("ascii")):
                self.make_fixture()
                original = self.path.read_bytes()
                raw = original.replace(b'"concepts": []', b'"concepts": [' + token + b']', 1)
                self.assertNotEqual(raw, original)
                self.path.write_bytes(raw)
                self.digest = hashlib.sha256(raw).hexdigest()
                self.assertEqual(self.view().inspect()["record_count"], 2)

    def test_finite_subnormal_json_float_is_allowed(self):
        original = self.path.read_bytes()
        raw = original.replace(b'"concepts": []', b'"concepts": [5e-324]', 1)
        self.assertNotEqual(raw, original)
        self.path.write_bytes(raw)
        self.digest = hashlib.sha256(raw).hexdigest()
        self.assertEqual(self.view().inspect()["record_count"], 2)

    def test_finite_large_exponent_json_is_allowed(self):
        raw = self.path.read_bytes().replace(
            b'"concepts": []', b'"concepts": [1e308]', 1
        )
        self.path.write_bytes(raw)
        self.digest = hashlib.sha256(raw).hexdigest()
        self.assertEqual(self.view().inspect()["record_count"], 2)

    def test_stale_pin_different_same_length(self):
        old = self.digest
        raw = self.path.read_bytes().replace(b"Other reply.", b"Other replY.", 1)
        self.assertEqual(len(raw), len(self.path.read_bytes()))
        self.path.write_bytes(raw)
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_SOURCE_SHA256_MISMATCH"):
            HistoricalV153View(self.path, expected_sha256=old)

    def test_rejects_link_source(self):
        link = Path(self.tmp.name) / "pointer.jsonl"
        try:
            link.symlink_to(self.path)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_LINK_OR_REPARSE_POINT"):
            HistoricalV153View(link, expected_sha256=self.digest)

    def test_rejects_oversized_source(self):
        old_bytes = self.path.read_bytes()
        try:
            with self.path.open("wb") as f:
                f.write(old_bytes)
                f.truncate(MAX_ARCHIVE_BYTES + 1)
        except OSError:
            self.skipTest("filesystem does not support truncation")
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_SOURCE_SIZE"):
            self.view()

    def test_rejects_blank_line(self):
        raw = self.path.read_bytes() + b"\n"
        self.path.write_bytes(raw)
        self.digest = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_BLANK_JSONL_LINE"):
            self.view()

    def test_error_without_private_text(self):
        self.rows[0]["ario_sha256"] = "0" * 64
        self.make_fixture()
        try:
            self.view()
        except HistoricalViewHold as exc:
            self.assertEqual(str(exc), "HOLD_TEXT_DIGEST_MISMATCH")
            self.assertNotIn("An archived model reply.", str(exc))
        else:
            self.fail("expected HOLD")

    def test_query_control_character_rejected(self):
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_INVALID_QUESTION"):
            self.view().recall("Question\x00injected")

    def test_unknown_requires_no_quote(self):
        got = self.view().recall("never seen")
        self.assertFalse(got["context_injection_allowed"])
        self.assertTrue(got["private_reply_hidden"])
        self.assertNotIn("historical_ario_reply", got)

    def test_rows_are_recursively_immutable(self):
        self.rows[0]["concepts"] = [{"label": "synthetic"}]
        self.make_fixture()
        view = self.view()
        with self.assertRaises(TypeError):
            view._rows[0]["ario"] = "MUTATED"
        with self.assertRaises(TypeError):
            view._rows[0]["relations"] += ("changed",)
        with self.assertRaises(TypeError):
            view._rows[0]["concepts"][0]["label"] = "changed"

    def test_view_state_cannot_be_reassigned_after_construction(self):
        view = self.view()
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_VIEW_IMMUTABLE"):
            view._rows = ()
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_VIEW_IMMUTABLE"):
            view._digest = "0" * 64
        with self.assertRaisesRegex(HistoricalViewHold, "HOLD_VIEW_IMMUTABLE"):
            del view._rows

    def test_local_display_returns_html_not_raw_quote(self):
        view = self.view()
        got = view.render_local_quote_html("What is Ario?", consent=True)
        self.assertIsInstance(got["rendered_html"], str)
        self.assertIn("An archived model reply.", got["rendered_html"])
        self.assertNotIn("historical_ario_reply", got)
        self.assertNotIn("text", got)
        self.assertFalse(got["quote_is_raw"])

    def test_local_display_unknown_question_returns_no_html(self):
        got = self.view().render_local_quote_html("Never asked", consent=True)
        self.assertEqual(got["disposition"], "UNKNOWN_NO_EXACT_QUESTION_MATCH")
        self.assertIsNone(got["rendered_html"])

    def test_failed_second_init_cannot_unseal_pinned_view(self):
        view = self.view()
        original = view.inspect()
        with self.assertRaisesRegex(HistoricalViewHold, "^HOLD_VIEW_ALREADY_INITIALIZED$"):
            view.__init__(self.path, expected_sha256="")
        self.assertEqual(view.inspect(), original)
        with self.assertRaisesRegex(HistoricalViewHold, "^HOLD_VIEW_IMMUTABLE$"):
            view._rows = ()
        with self.assertRaisesRegex(HistoricalViewHold, "^HOLD_VIEW_IMMUTABLE$"):
            view._digest = "0" * 64

    def test_valid_second_init_is_also_refused(self):
        view = self.view()
        with self.assertRaisesRegex(HistoricalViewHold, "^HOLD_VIEW_ALREADY_INITIALIZED$"):
            view.__init__(self.path, expected_sha256=self.digest)
        self.assertEqual(view.recall("What is Ario?")["source_line"], 1)

    def test_freeze_depth_failure_is_bounded_hold(self):
        from unittest.mock import patch
        with patch(
            "core.legacy_v153_historical_view._freeze_json",
            side_effect=RecursionError("SYNTHETIC_PRIVATE_DEPTH"),
        ):
            with self.assertRaisesRegex(HistoricalViewHold, "^HOLD_RECORD_DEPTH$") as caught:
                self.view()
        self.assertNotIn("SYNTHETIC_PRIVATE_DEPTH", str(caught.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
