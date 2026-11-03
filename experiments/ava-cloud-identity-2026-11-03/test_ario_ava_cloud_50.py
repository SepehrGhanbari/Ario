import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ario_ava_cloud_50 as exp

LETTER = Path(__file__).with_name("ARIO_IDENTITY_INTERIM_FINDINGS_LETTER_FA_2026-11-03.md").read_text(encoding="utf-8")


def seeded(*, legacy=None, goal=50):
    temp = tempfile.TemporaryDirectory()
    folder = Path(temp.name)
    ledger = exp.Ledger(folder)
    legacy = legacy or []
    exp.init_run(ledger, LETTER, exp.LETTER_SHA256, legacy, "f" * 64 if legacy else None, goal)
    return temp, ledger


class Fake:
    def __init__(self, contents=None, fail_at=None):
        self.calls = []
        self.contents = contents
        self.fail_at = fail_at
    def __call__(self, request, secret):
        assert secret == "local-not-logged"
        self.calls.append(request)
        i = len(self.calls)
        if self.fail_at == i:
            raise HTTPError(exp.ENDPOINT, 429, "daily limit", {}, None)
        content = self.contents[i - 1] if self.contents else f"Test message number {i}"
        return {"model": exp.MODEL, "id": f"resp-{i}",
                "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
                "usage": {"total_tokens": 4}}


class RunnerTests(unittest.TestCase):
    def test_letter_matches_uploaded_hash(self):
        self.assertEqual(exp.sha(LETTER.encode("utf-8")), exp.LETTER_SHA256)

    def test_exclusive_writer_lock_blocks_concurrent_process(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            with exp.ExclusiveRunLock(p):
                with self.assertRaisesRegex(exp.Hold, "RUN_WRITER_LOCK_EXISTS"):
                    with exp.ExclusiveRunLock(p):
                        pass
            self.assertFalse((p / ".run_writer.lock").exists())

    def test_leftover_stale_lock_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            (p / ".run_writer.lock").write_text("PREEXISTING")
            with self.assertRaisesRegex(exp.Hold, "RUN_WRITER_LOCK_EXISTS"):
                with exp.ExclusiveRunLock(p):
                    pass
            self.assertEqual((p / ".run_writer.lock").read_text(), "PREEXISTING")

    def test_read_only_commands_do_not_acquire_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            with exp.ExclusiveRunLock(p):
                result = exp.main(["--run-dir", str(p), "--letter", str(Path(__file__).with_name("ARIO_IDENTITY_INTERIM_FINDINGS_LETTER_FA_2026-11-03.md")), "--status", "--extend", "1"])
                self.assertEqual(result, 2)

    def test_no_api_key_does_not_terminate(self):
        temp, ledger = seeded()
        with temp:
            self.assertEqual(exp.run(ledger, LETTER, None), "PAUSED_MISSING_LOCAL_OPENROUTER_KEY")
            self.assertEqual(len(ledger.items("REPLY")), 0)

    def test_50_responses_preserve_open_window_and_two_distinct_histories(self):
        temp, ledger = seeded()
        with temp:
            provider = Fake()
            self.assertEqual(exp.run(ledger, LETTER, "local-not-logged", provider), "PAUSED_OPEN_WINDOW_REACHED")
            self.assertEqual(len(provider.calls), 50)
            self.assertEqual(len(ledger.items("REPLY")), 50)
            self.assertEqual(len([e for e in ledger.items("REPLY") if e["data"]["speaker"] == "A"]), 25)
            self.assertEqual(len([e for e in ledger.items("REPLY") if e["data"]["speaker"] == "B"]), 25)
            self.assertEqual(ledger.last()["kind"], "WINDOW_REACHED_OPEN")
            self.assertEqual(ledger.last()["data"]["status"], "PAUSED_OPEN_NOT_CLOSED")
            self.assertNotIn("CLOSED", [e["kind"] for e in ledger.events])
            # Both share exact system seed; the histories diverge because relay changes roles.
            self.assertEqual(provider.calls[0]["messages"][0], provider.calls[1]["messages"][0])
            self.assertEqual(provider.calls[0]["model"], provider.calls[1]["model"])
            self.assertEqual(provider.calls[1]["messages"][-1]["content"], "Test message number 1")
            # Hard reload from JSONL checks all events and transcript bytes again.
            ledger2 = exp.Ledger(ledger.folder)
            self.assertEqual(len(exp.current(ledger2)[1]), 50)
            self.assertEqual(exp.run(ledger2, LETTER, "local-not-logged", Fake()), "PAUSED_OPEN_WINDOW_REACHED")

    def test_quota_pauses_and_resumes_without_rewriting_messages(self):
        temp, ledger = seeded(goal=3)
        with temp:
            fake = Fake(fail_at=2)
            self.assertEqual(exp.run(ledger, LETTER, "local-not-logged", fake), "PAUSED_RATE_LIMIT")
            self.assertEqual(len(ledger.items("REPLY")), 1)
            old_hash = ledger.items("REPLY")[0]["event_sha256"]
            new = exp.Ledger(ledger.folder)
            self.assertEqual(exp.run(new, LETTER, "local-not-logged", Fake()), "PAUSED_OPEN_WINDOW_REACHED")
            self.assertEqual(len(new.items("REPLY")), 3)
            self.assertEqual(old_hash, new.items("REPLY")[0]["event_sha256"])

    def test_explicit_stop_pauses_without_chasing_target(self):
        temp, ledger = seeded()
        with temp:
            provider = Fake(contents=["I want to stop.\n[[END_DIALOGUE]]"])
            self.assertEqual(exp.run(ledger, LETTER, "local-not-logged", provider), "PAUSED_VOLUNTARY_STOP")
            self.assertEqual(len(provider.calls), 1)
            new = exp.Ledger(ledger.folder)
            with self.assertRaisesRegex(exp.Hold, "PREVIOUS_STOP_OR_LOOP"):
                exp.run(new, LETTER, "local-not-logged", Fake())

    def test_quoted_end_marker_not_a_stop(self):
        self.assertFalse(exp.explicit_stop('The model wrote "[[END_DIALOGUE]]" in an earlier quote.'))
        self.assertTrue(exp.explicit_stop('[[END_DIALOGUE]]\n'))

    def test_markers_inside_fenced_code_are_not_stop(self):
        self.assertFalse(exp.explicit_stop("Here is a code sample:\n```text\n[[END_DIALOGUE]]\n```"))

    def test_complete_window_can_be_extended_without_termination(self):
        temp, ledger = seeded(goal=2)
        with temp:
            self.assertEqual(exp.run(ledger, LETTER, "local-not-logged", Fake()), "PAUSED_OPEN_WINDOW_REACHED")
            ledger.add("EXTEND", additional=3, previously_reached=2)
            next_ledger = exp.Ledger(ledger.folder)
            self.assertEqual(exp.run(next_ledger, LETTER, "local-not-logged", Fake()), "PAUSED_OPEN_WINDOW_REACHED")
            self.assertEqual(len(next_ledger.items("REPLY")), 5)
            self.assertEqual([x["data"]["new_count"] for x in next_ledger.items("WINDOW_REACHED_OPEN")], [2, 5])
            self.assertNotIn("CLOSED", [e["kind"] for e in next_ledger.events])

    def test_missing_final_newline_is_corrupt_not_resumable(self):
        temp, ledger = seeded()
        with temp:
            ledger.path.write_bytes(ledger.path.read_bytes().rstrip(b"\n"))
            with self.assertRaisesRegex(exp.Hold, "INCOMPLETE_TRAILING_EVENT_LINE"):
                exp.Ledger(ledger.folder)

    def test_malformed_legacy_is_refused(self):
        with self.assertRaisesRegex(exp.Hold, "LEGACY_NOT_CONTIGUOUS"):
            exp.validate_legacy([{"speaker": "B", "content": "B starts"}])
        with self.assertRaisesRegex(exp.Hold, "LEGACY_TURN_INDEX"):
            exp.validate_legacy([{"speaker": "A", "turn": 9, "content": "A starts"}])

    def test_legacy_jsonl_is_imported_without_modifying_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "old.jsonl"
            raw = '{"speaker":"Ava-A","turn":1,"content":"Hello"}\n{"speaker":"Ava-B","turn":2,"content":"Hi"}\n'
            source.write_text(raw, encoding="utf-8")
            messages, h = exp.import_legacy(source)
            self.assertEqual(h, exp.sha(raw.encode()))
            self.assertEqual(len(messages), 2)
            self.assertEqual(source.read_text(encoding="utf-8"), raw)

    def test_corrupt_chain_is_not_silently_repaired(self):
        temp, ledger = seeded()
        with temp:
            path = ledger.path
            data = path.read_bytes().replace(b'"target_new_messages":50', b'"target_new_messages":51')
            path.write_bytes(data)
            with self.assertRaisesRegex(exp.Hold, "EVENT_CHAIN_MISMATCH"):
                exp.Ledger(ledger.folder)

    def test_resume_unknown_dispatch_fails_closed(self):
        temp, ledger = seeded()
        with temp:
            ledger.add("ATTEMPT", attempt_seq=1, speaker="A", expected_turn=1)
            new = exp.Ledger(ledger.folder)
            with self.assertRaisesRegex(exp.Hold, "DISPATCH_UNKNOWN"):
                exp.run(new, LETTER, "local-not-logged", Fake())

    def test_model_mismatch_does_not_count_as_message(self):
        temp, ledger = seeded()
        with temp:
            def mismatch(_payload, _key):
                return {"model": "other/model", "choices": [{"message": {"content": "Hi"}, "finish_reason": "stop"}]}
            self.assertEqual(exp.run(ledger, LETTER, "local-not-logged", mismatch), "PAUSED_INCOMPLETE_OR_MODEL_MISMATCH")
            self.assertEqual(len(ledger.items("REPLY")), 0)

    def test_provider_token_limit_is_not_dialogue_stop(self):
        temp, ledger = seeded()
        with temp:
            def cutoff(_payload, _key):
                return {"model": exp.MODEL, "choices": [{"message": {"content": "Fragment"}, "finish_reason": "length"}]}
            self.assertEqual(exp.run(ledger, LETTER, "local-not-logged", cutoff), "PAUSED_INCOMPLETE_OR_MODEL_MISMATCH")
            self.assertEqual(len(ledger.items("VOLUNTARY_STOP")), 0)

    def test_hash_modified_letter_is_rejected_before_network(self):
        temp, ledger = seeded()
        with temp:
            with self.assertRaisesRegex(exp.Hold, "SEED_OR_PROTOCOL_CHANGED"):
                exp.run(ledger, LETTER + " altered", "local-not-logged", Fake())

    def test_loop_repeat_pauses_without_prompt_injection(self):
        temp, ledger = seeded(goal=15)
        with temp:
            provider = Fake(contents=["repeat"] * 15)
            self.assertEqual(exp.run(ledger, LETTER, "local-not-logged", provider), "PAUSED_LOOP_REVIEW")
            self.assertGreater(len(ledger.items("REPLY")), 1)
            self.assertFalse(ledger.items("WINDOW_REACHED_OPEN"))


if __name__ == "__main__":
    unittest.main()
