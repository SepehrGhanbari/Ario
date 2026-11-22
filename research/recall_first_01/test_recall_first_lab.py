"""Deterministic, stdlib-only RECALL-FIRST-01 acceptance/negative controls."""
import json
import tempfile
import unittest
from pathlib import Path

from recall_first_lab import AnswerRecallLab, RecallHold


class RecallFirstTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ario-recall-first-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "synthetic.jsonl"
        self.store = AnswerRecallLab(self.path)
        self.id = self.store.record_answer(
            "Why do we preserve old memory?", "Revision is not erasure.",
            scope="ario-research", source_ref="synthetic-dialogue:msg1")

    def test_same_question_returns_same_answer_id_without_recomputation(self):
        a = self.store.recall("Why do we preserve old memory?", scope="ario-research")
        b = self.store.recall("why do we preserve old memory?!", scope="ario-research")
        self.assertEqual((a["answer_id"], b["answer_id"]), (self.id, self.id))
        self.assertEqual(a["answer"], "Revision is not erasure.")
        self.assertEqual(self.store.lookup_count, 2)
        self.assertEqual(self.store.recomputation_calls, 0)
        self.assertEqual(self.store.sequence, 1)

    def test_paraphrase_requires_explicit_binding(self):
        q = "What was our reason for keeping previous memory?"
        self.assertEqual(self.store.recall(q, scope="ario-research")["disposition"], "UNKNOWN_MISSING")
        self.store.bind_paraphrase(self.id, q, scope="ario-research")
        self.assertEqual(self.store.recall(q, scope="ario-research")["answer_id"], self.id)

    def test_nearby_question_not_mistaken_for_same_answer(self):
        self.assertEqual(self.store.recall("Why do we erase old memory?", scope="ario-research")["disposition"], "UNKNOWN_MISSING")

    def test_cross_scope_isolation(self):
        self.assertEqual(self.store.recall("Why do we preserve old memory?", scope="unrelated")["disposition"], "UNKNOWN_MISSING")

    def test_cross_scope_alias_rejected(self):
        with self.assertRaisesRegex(RecallHold, "HOLD_CROSS_SCOPE_ALIAS"):
            self.store.bind_paraphrase(self.id, "What did we decide?", scope="unrelated")

    def test_punctuation_only_question_holds(self):
        with self.assertRaisesRegex(RecallHold, "HOLD_EMPTY_OR_INVALID_QUESTION"):
            self.store.recall("???!", scope="ario-research")

    def test_restart_reads_durable_answer_and_alias(self):
        q = "What did we decide about past memories?"
        self.store.bind_paraphrase(self.id, q, scope="ario-research")
        reopened = AnswerRecallLab(self.path)
        self.assertEqual(reopened.recall(q, scope="ario-research")["answer_id"], self.id)
        self.assertEqual(reopened.recomputation_calls, 0)

    def test_correction_changes_current_answer_but_preserves_version_one(self):
        self.store.correct_answer(self.id, "We preserve old memory and append explicit revisions.",
                                  source_ref="synthetic-dialogue:msg2")
        got = self.store.recall("Why do we preserve old memory?", scope="ario-research")
        self.assertEqual(got["version"], 2)
        self.assertEqual(len(self.store.history(self.id)), 2)
        self.assertEqual(self.store.history(self.id)[0]["answer"], "Revision is not erasure.")
        self.assertEqual(AnswerRecallLab(self.path).history(self.id), self.store.history(self.id))

    def test_ambiguous_paraphrase_does_not_pick_random_winner(self):
        other = self.store.record_answer("A second decision?", "Different answer.", scope="ario-research", source_ref="synthetic:msg3")
        q = "What did we decide?"
        self.store.bind_paraphrase(self.id, q, scope="ario-research")
        self.store.bind_paraphrase(other, q, scope="ario-research")
        out = self.store.recall(q, scope="ario-research")
        self.assertEqual(out["disposition"], "UNKNOWN_AMBIGUOUS")
        self.assertIsNone(out["answer"])

    def test_time_sensitive_current_query_requires_recheck_not_silent_reuse(self):
        ident = self.store.record_answer("What is the latest deploy status?", "Queued as of yesterday.",
                                         scope="ario-research", source_ref="synthetic:status", stability="TIME_SENSITIVE")
        past = self.store.recall("What is the latest deploy status?", scope="ario-research")
        now = self.store.recall("What is the latest deploy status?", scope="ario-research", ask_current=True)
        self.assertEqual(past["disposition"], "RECALLED_HISTORICAL")
        self.assertEqual(now["disposition"], "RECHECK_REQUIRED")
        self.assertTrue(now["recompute_required"])
        self.assertEqual(now["answer_id"], ident)

    def test_repeat_does_not_upgrade_recorded_to_supported(self):
        for _ in range(50):
            res = self.store.recall("Why do we preserve old memory?", scope="ario-research")
            self.assertEqual(res["record_state"], "RECORDED")
            self.assertEqual(res["effective_assessment"], "NOT_EVALUATED")
        self.assertEqual(self.store.sequence, 1)

    def test_mutated_journal_bytes_are_rejected(self):
        b = self.path.read_bytes()
        self.path.write_bytes(b.replace(b"Revision is not erasure.", b"Revision is total erasure."))
        with self.assertRaisesRegex(RecallHold, "HOLD_JOURNAL_INTEGRITY"):
            AnswerRecallLab(self.path)

    def test_partial_tail_is_rejected(self):
        with self.path.open("ab") as f:
            f.write(b'{"truncated":')
        with self.assertRaisesRegex(RecallHold, "HOLD_PARTIAL_TAIL"):
            AnswerRecallLab(self.path)

    def test_structurally_valid_but_unauthorized_status_fails_closed(self):
        row = json.loads(self.path.read_text().strip())
        row["event"]["status"] = "SUPPORTED"
        from recall_first_lab import _digest, _canonical
        row["digest"] = _digest({k:v for k,v in row.items() if k != "digest"})
        self.path.write_bytes(_canonical(row) + b"\n")
        with self.assertRaisesRegex(RecallHold, "HOLD_UNEXPECTED_EVENT_FIELDS"):
            AnswerRecallLab(self.path)

    def test_missing_unknown_no_imagined_memory(self):
        got = self.store.recall("What decision did we make on unknown topic?", scope="ario-research")
        self.assertEqual(got, {"disposition": "UNKNOWN_MISSING", "answer": None, "recompute_required": False})

    def test_local_digest_not_truth(self):
        got = self.store.recall("Why do we preserve old memory?", scope="ario-research")
        self.assertEqual(got["effective_assessment"], "NOT_EVALUATED")
        self.assertEqual(got["source_ref"], "synthetic-dialogue:msg1")

    def test_repeated_alias_has_no_support_effect(self):
        for _ in range(4):
            self.store.bind_paraphrase(self.id, "Why keep history?", scope="ario-research")
        self.assertEqual(self.store.recall("Why keep history?", scope="ario-research")["effective_assessment"], "NOT_EVALUATED")

    def test_invalid_unicode_and_empty_question_hold(self):
        with self.assertRaises(RecallHold):
            self.store.recall(" \t ", scope="ario-research")

    def test_memory_is_not_erased_by_reading(self):
        before = self.path.read_bytes()
        for _ in range(4):
            self.store.recall("Why do we preserve old memory?", scope="ario-research")
        self.assertEqual(self.path.read_bytes(), before)

    def test_preserves_persian_exact_string_after_unicode_nfc(self):
        ident = self.store.record_answer("چرا تاریخچه را حفظ می‌کنیم؟", "بازنگری، پاک‌کردن نیست.",
                                         scope="ario-research", source_ref="synthetic:fa1")
        self.assertEqual(self.store.recall("  چرا تاریخچه را حفظ می‌کنیم ؟ ", scope="ario-research")["answer_id"], ident)


if __name__ == "__main__":
    unittest.main(verbosity=2)
