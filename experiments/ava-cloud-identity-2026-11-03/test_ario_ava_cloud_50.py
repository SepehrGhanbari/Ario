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

    def test_quota_429_requires_review_and_preserves_existing_messages(self):
        temp, ledger = seeded(goal=3)
        with temp:
            fake = Fake(fail_at=2)
            self.assertEqual(exp.run(ledger, LETTER, "local-not-logged", fake), "PAUSED_RATE_LIMIT")
            self.assertEqual(len(ledger.items("REPLY")), 1)
            old_hash = ledger.items("REPLY")[0]["event_sha256"]
            self.assertEqual(ledger.items("PAUSE")[-1]["data"]["status"],
                             "PAUSED_FOR_REVIEW")
            new = exp.Ledger(ledger.folder)
            retry = Fake()
            with self.assertRaisesRegex(exp.Hold, "REVIEW"):
                exp.run(new, LETTER, "local-not-logged", retry)
            self.assertEqual(len(new.items("REPLY")), 1)
            self.assertEqual(old_hash, new.items("REPLY")[0]["event_sha256"])
            self.assertFalse(retry.calls)

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
            # Byte-exact fixture: Path.write_text translates newlines on
            # Windows and invalidates the expectation before import starts.
            source.write_bytes(raw.encode("utf-8"))
            messages, h = exp.import_legacy(source)
            self.assertEqual(h, exp.sha(raw.encode("utf-8")))
            self.assertEqual(len(messages), 2)
            self.assertEqual(source.read_bytes(), raw.encode("utf-8"))

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

    def test_duplicate_attempt_id_cannot_borrow_older_reply(self):
        """Each ATTEMPT needs its own later, identity-matched resolution."""
        cases = (
            ("duplicate_attempt_id", (
                ("ATTEMPT", {"attempt_seq": 1, "speaker": "A", "expected_turn": 1}),
                ("REPLY", {"attempt_seq": 1, "speaker": "A", "turn": 1,
                           "content": "hello"}),
                ("ATTEMPT", {"attempt_seq": 1, "speaker": "B", "expected_turn": 2}),
            )),
            ("reply_before_attempt", (
                ("REPLY", {"attempt_seq": 1, "speaker": "A", "turn": 1,
                           "content": "hello"}),
                ("ATTEMPT", {"attempt_seq": 1, "speaker": "B", "expected_turn": 2}),
            )),
            ("two_replies_reuse_one_attempt", (
                ("ATTEMPT", {"attempt_seq": 1, "speaker": "A", "expected_turn": 1}),
                ("REPLY", {"attempt_seq": 1, "speaker": "A", "turn": 1,
                           "content": "hello"}),
                ("REPLY", {"attempt_seq": 1, "speaker": "B", "turn": 2,
                           "content": "borrowed identity"}),
            )),
        )
        for label, records in cases:
            with self.subTest(label=label):
                temp, ledger = seeded(goal=3)
                with temp:
                    for kind, data in records:
                        ledger.add(kind, **data)
                    original = ledger.path.read_bytes()
                    fake = Fake()
                    with self.assertRaisesRegex(exp.Hold,
                                                "ATTEMPT|DISPATCH_UNKNOWN"):
                        exp.run(exp.Ledger(ledger.folder), LETTER,
                                "local-not-logged", fake)
                    self.assertEqual(fake.calls, [])
                    self.assertEqual(ledger.path.read_bytes(), original)

    def test_valid_sequential_attempt_reply_pairs_can_resume(self):
        temp, ledger = seeded(goal=3)
        with temp:
            ledger.add("ATTEMPT", attempt_seq=1, speaker="A", expected_turn=1)
            ledger.add("REPLY", attempt_seq=1, speaker="A", turn=1, content="hello")
            ledger.add("ATTEMPT", attempt_seq=2, speaker="B", expected_turn=2)
            ledger.add("REPLY", attempt_seq=2, speaker="B", turn=2, content="world")
            previous = ledger.path.read_bytes()
            fake = Fake()
            self.assertEqual(exp.run(exp.Ledger(ledger.folder), LETTER,
                                     "local-not-logged", fake),
                             "PAUSED_OPEN_WINDOW_REACHED")
            self.assertEqual(len(fake.calls), 1)
            self.assertTrue(ledger.path.read_bytes().startswith(previous))

    def test_unrecognized_pause_cannot_claim_an_attempt_is_resolved(self):
        temp, ledger = seeded(goal=2)
        with temp:
            ledger.add("ATTEMPT", attempt_seq=1, speaker="A", expected_turn=1)
            # A PAUSE is not proof of a provider reply, regardless of an
            # attacker-controlled status or reason string.
            ledger.add("PAUSE", attempt_seq=1, reason="UNRECOGNIZED",
                       status="CLAIMED_SAFE")
            original = ledger.path.read_bytes()
            fake = Fake()
            with self.assertRaisesRegex(exp.Hold, "REVIEW|ATTEMPT"):
                exp.run(exp.Ledger(ledger.folder), LETTER,
                        "local-not-logged", fake)
            self.assertFalse(fake.calls)
            self.assertEqual(ledger.path.read_bytes(), original)

    def test_boolean_target_is_not_valid_init_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = exp.Ledger(Path(tmp))
            with self.assertRaisesRegex(exp.Hold, "INVALID_TARGET_COUNT"):
                exp.init_run(ledger, LETTER, exp.LETTER_SHA256, [], None, True)
            self.assertFalse(ledger.events)
            self.assertFalse(ledger.path.exists())

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


    def test_invalid_provider_shape_requires_review_before_retry(self):
        temp, ledger = seeded(goal=2)
        with temp:
            calls = []
            def invalid(_payload, _key):
                calls.append("request")
                return []
            self.assertEqual(exp.run(ledger, LETTER, "local-not-logged", invalid),
                             "PAUSED_INVALID_RESPONSE")
            self.assertEqual(len(calls), 1)
            pause = ledger.items("PAUSE")[-1]
            self.assertEqual(pause["data"]["status"], "PAUSED_FOR_REVIEW")
            fresh = exp.Ledger(ledger.folder)
            retry = Fake()
            with self.assertRaisesRegex(exp.Hold, "REVIEW"):
                exp.run(fresh, LETTER, "local-not-logged", retry)
            self.assertFalse(retry.calls)

    def test_legacy_invalid_shape_pause_also_blocks_resume(self):
        temp, ledger = seeded(goal=2)
        with temp:
            ledger.add("ATTEMPT", attempt_seq=1, speaker="A", expected_turn=1)
            ledger.add("PAUSE", attempt_seq=1, reason="INVALID_PROVIDER_JSON")
            retry = Fake()
            with self.assertRaisesRegex(exp.Hold, "REVIEW"):
                exp.run(exp.Ledger(ledger.folder), LETTER, "local-not-logged", retry)
            self.assertFalse(retry.calls)

    def test_failed_provider_body_decode_records_review_pause(self):
        temp, ledger = seeded(goal=2)
        with temp:
            def broken(_payload, _key):
                raise json.JSONDecodeError("not JSON", "<html>", 0)
            self.assertEqual(exp.run(ledger, LETTER, "local-not-logged", broken),
                             "PAUSED_INVALID_RESPONSE")
            self.assertEqual(ledger.items("PAUSE")[-1]["data"]["status"],
                             "PAUSED_FOR_REVIEW")
            self.assertFalse(ledger.items("REPLY"))

    def test_crash_after_stop_reply_must_not_dispatch_again(self):
        temp, ledger = seeded(goal=2)
        with temp:
            ledger.add("ATTEMPT", attempt_seq=1, speaker="A", expected_turn=1)
            ledger.add("REPLY", attempt_seq=1, speaker="A", turn=1,
                       content="[[END_DIALOGUE]]")
            retry = Fake()
            with self.assertRaisesRegex(exp.Hold, "STOP.*REVIEW"):
                exp.run(exp.Ledger(ledger.folder), LETTER, "local-not-logged", retry)
            self.assertFalse(retry.calls)

    def test_windows_binary_file_flags_are_explicit(self):
        from unittest.mock import patch
        import os
        original = os.open
        original_binary = getattr(os, "O_BINARY", 0)
        marker = 1 << 27
        flags_seen = []
        def fake_open(path, flags, mode=0o777, *, dir_fd=None):
            if str(path).endswith((".run_writer.lock", "events.jsonl")):
                flags_seen.append((str(path), flags))
            # On real Windows, removing the synthetic marker must restore
            # the actual CRT binary bit; text-mode translation would falsify
            # the lock/ledger bytes and make the fixture itself invalid.
            effective = (flags & ~marker) | (original_binary if flags & marker else 0)
            if dir_fd is not None:
                return original(path, effective, mode, dir_fd=dir_fd)
            return original(path, effective, mode)
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            with patch.object(exp.os, "O_BINARY", marker, create=True):
                with patch.object(exp.os, "open", side_effect=fake_open):
                    with exp.ExclusiveRunLock(p):
                        exp.Ledger(p).add("PROBE", evidence="synthetic")
        names = {Path(path).name for path, flags in flags_seen if flags & marker}
        self.assertEqual(names, {".run_writer.lock", "events.jsonl"})


    def test_http_500_requires_review_before_retry(self):
        temp, ledger = seeded(goal=2)
        with temp:
            def failed(_payload, _key):
                raise HTTPError(exp.ENDPOINT, 500, "ambiguous gateway failure", {}, None)
            self.assertEqual(exp.run(ledger, LETTER, "local-not-logged", failed),
                             "PAUSED_PROVIDER_ERROR")
            self.assertEqual(ledger.items("PAUSE")[-1]["data"]["status"],
                             "PAUSED_FOR_REVIEW")
            retry = Fake()
            with self.assertRaisesRegex(exp.Hold, "REVIEW"):
                exp.run(exp.Ledger(ledger.folder), LETTER, "local-not-logged", retry)
            self.assertFalse(retry.calls)

    def test_old_http_error_pauses_do_not_auto_resume(self):
        for previous_status in ("PAUSED_RATE_LIMIT", "PAUSED_PROVIDER_ERROR"):
            with self.subTest(previous_status=previous_status):
                temp, ledger = seeded(goal=2)
                with temp:
                    ledger.add("ATTEMPT", attempt_seq=1, speaker="A", expected_turn=1)
                    ledger.add("PAUSE", attempt_seq=1, reason="HTTP_ERROR",
                               http_code=429 if previous_status == "PAUSED_RATE_LIMIT" else 500,
                               status=previous_status)
                    retry = Fake()
                    with self.assertRaisesRegex(exp.Hold, "REVIEW"):
                        exp.run(exp.Ledger(ledger.folder), LETTER, "local-not-logged", retry)
                    self.assertFalse(retry.calls)



    def test_provider_transport_refuses_without_owned_writer_lock(self):
        temp, ledger = seeded(goal=1)
        with temp:
            with self.assertRaisesRegex(exp.Hold, "LIVE_DISPATCH_REQUIRES_WRITER_LOCK"):
                exp.run(ledger, LETTER, "synthetic-no-call", transport=exp.send)
            self.assertFalse(ledger.items("ATTEMPT"))

    def test_lock_disappears_during_first_reply_no_second_dispatch(self):
        temp, ledger = seeded(goal=2)
        with temp:
            lock = exp.ExclusiveRunLock(ledger.folder)
            calls = []
            def tamper_transport(_request, _secret):
                calls.append(1)
                lock.path.write_bytes(b"interfering actor")
                return {"model": exp.MODEL, "id": "tamper",
                        "choices": [{"message": {"content": "one"}, "finish_reason": "stop"}]}
            with self.assertRaisesRegex(exp.Hold, "WRITER_LOCK_"):
                with lock:
                    exp.run(ledger, LETTER, "local-not-logged",
                            tamper_transport, writer_lock=lock)
            self.assertEqual(len(calls), 1)
            self.assertFalse(ledger.items("REPLY"))

    def test_clean_owned_lock_allows_fake_transport(self):
        temp, ledger = seeded(goal=1)
        with temp:
            with exp.ExclusiveRunLock(ledger.folder) as lock:
                self.assertEqual(exp.run(ledger, LETTER, "local-not-logged",
                                         Fake(), writer_lock=lock),
                                 "PAUSED_OPEN_WINDOW_REACHED")
            self.assertEqual(len(ledger.items("REPLY")), 1)
            self.assertFalse(lock.path.exists())

    def test_ledger_symlink_is_refused_without_touching_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            folder = p / "run"
            folder.mkdir()
            outside = p / "other.jsonl"
            outside.write_bytes(b"ORIGINAL\n")
            link = folder / "events.jsonl"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError) as e:
                self.skipTest(f"symlinks unavailable: {type(e).__name__}")
            with self.assertRaisesRegex(exp.Hold, "LEDGER_SYMLINK"):
                exp.Ledger(folder)
            self.assertEqual(outside.read_bytes(), b"ORIGINAL\n")

    def test_symlink_replacement_before_append_is_refused(self):
        temp, ledger = seeded(goal=1)
        with temp:
            outside = ledger.folder.parent / (ledger.folder.name + "_external.txt")
            outside.write_bytes(b"SAFE\n")
            try:
                ledger.path.unlink()
                ledger.path.symlink_to(outside)
            except (OSError, NotImplementedError) as e:
                self.skipTest(f"symlinks unavailable: {type(e).__name__}")
            try:
                with self.assertRaisesRegex(exp.Hold, "LEDGER_SYMLINK"):
                    ledger.add("NEVER", example="external")
                self.assertEqual(outside.read_bytes(), b"SAFE\n")
            finally:
                outside.unlink(missing_ok=True)



    def test_symlink_run_folder_must_not_create_external_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            top = Path(temp)
            outside = top / "outside"
            outside.mkdir()
            link = top / "run-link"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"directory symlinks unsupported: {type(exc).__name__}")
            with self.assertRaisesRegex(exp.Hold, "RUN_FOLDER_SYMLINK_REFUSED"):
                with exp.ExclusiveRunLock(link):
                    pass
            self.assertFalse((outside / ".run_writer.lock").exists())


    def test_last_reply_stop_crash_does_not_claim_open_window(self):
        temp, ledger = seeded(goal=1)
        with temp:
            ledger.add("ATTEMPT", attempt_seq=1, speaker="A", expected_turn=1)
            ledger.add("REPLY", attempt_seq=1, speaker="A", turn=1,
                       content="[[END_DIALOGUE]]")
            old_count = len(ledger.events)
            with self.assertRaisesRegex(exp.Hold, "PREVIOUS_STOP_MARKER_REQUIRES_REVIEW"):
                exp.run(ledger, LETTER, "local-not-logged", Fake())
            self.assertEqual(len(ledger.events), old_count)
            self.assertFalse(ledger.items("WINDOW_REACHED_OPEN"))

    def test_completed_window_still_honors_ambiguous_pause(self):
        temp, ledger = seeded(goal=1)
        with temp:
            ledger.add("ATTEMPT", attempt_seq=1, speaker="A", expected_turn=1)
            ledger.add("REPLY", attempt_seq=1, speaker="A", turn=1, content="Normal")
            ledger.add("PAUSE", attempt_seq=2, reason="HTTP_ERROR", status="PAUSED_FOR_REVIEW")
            old_count = len(ledger.events)
            with self.assertRaisesRegex(exp.Hold, "PREVIOUS_UNRESOLVED_REVIEW_PAUSE"):
                exp.run(ledger, LETTER, "local-not-logged", Fake())
            self.assertEqual(len(ledger.events), old_count)
            self.assertFalse(ledger.items("WINDOW_REACHED_OPEN"))

    def test_lock_cannot_protect_another_ledger_folder(self):
        temp, ledger = seeded(goal=1)
        with temp:
            with tempfile.TemporaryDirectory() as other:
                with exp.ExclusiveRunLock(Path(other)) as unrelated_lock:
                    calls = Fake()
                    with self.assertRaisesRegex(exp.Hold, "LOCK_LEDGER_DIR_MISMATCH"):
                        exp.run(ledger, LETTER, "local-not-logged",
                                calls, writer_lock=unrelated_lock)
                    self.assertFalse(calls.calls)
                    self.assertFalse(ledger.items("ATTEMPT"))

    def test_replaced_regular_ledger_rejected_before_append(self):
        # Atomically replace the loaded inode with a distinct file, retaining
        # identical bytes. unlink+recreate alone may recycle the inode on Linux.
        import os
        temp, ledger = seeded(goal=1)
        with temp:
            original = ledger.path.read_bytes()
            old_ino = ledger.path.stat().st_ino
            swap = ledger.folder / "other-regular-ledger.jsonl"
            swap.write_bytes(original)
            self.assertNotEqual(old_ino, swap.stat().st_ino)
            os.replace(swap, ledger.path)
            before = ledger.path.read_bytes()
            with self.assertRaisesRegex(exp.Hold, "LEDGER_REPLACED"):
                ledger.add("SHOULD_NOT_WRITE", why="different inode")
            self.assertEqual(ledger.path.read_bytes(), before)
            self.assertFalse(ledger.items("SHOULD_NOT_WRITE"))

    def test_hardlinked_ledger_rejected_before_append(self):
        import os
        temp, ledger = seeded(goal=1)
        with temp:
            external = ledger.folder / "other-link.jsonl"
            try:
                os.link(ledger.path, external)
            except (OSError, NotImplementedError) as exc:
                self.skipTest("hardlink unavailable: " + type(exc).__name__)
            before = ledger.path.read_bytes()
            with self.assertRaisesRegex(exp.Hold, "LEDGER_MULTIPLE_LINKS"):
                ledger.add("SHOULD_NOT_WRITE", why="hardlink alias")
            self.assertEqual(ledger.path.read_bytes(), before)



    def test_ledger_same_size_mutation_rejected_before_append(self):
        temp, ledger = seeded(goal=2)
        with temp:
            original = ledger.path.read_bytes()
            altered = bytearray(original)
            marker = b'"timestamp_utc":"'
            pos = altered.index(marker) + len(marker)
            altered[pos] = ord("8") if altered[pos] != ord("8") else ord("9")
            ledger.path.write_bytes(altered)
            self.assertEqual(len(altered), len(original))
            self.assertEqual(ledger.path.stat().st_ino, ledger.file_identity[1])
            with self.assertRaisesRegex(exp.Hold, "LEDGER_CONTENT_MUTATED"):
                ledger.add("SHOULD_NOT_APPEND", why="same-size external edit")
            self.assertEqual(ledger.path.read_bytes(), bytes(altered))

    def test_ledger_same_size_mutation_prevents_fake_dispatch(self):
        temp, ledger = seeded(goal=2)
        with temp:
            raw = bytearray(ledger.path.read_bytes())
            marker = b'"timestamp_utc":"'
            pos = raw.index(marker) + len(marker)
            raw[pos] = ord("8") if raw[pos] != ord("8") else ord("9")
            ledger.path.write_bytes(raw)
            fake = Fake()
            with self.assertRaisesRegex(exp.Hold, "LEDGER_CONTENT_MUTATED"):
                exp.run(ledger, LETTER, "local-not-logged", fake)
            self.assertFalse(fake.calls)
            self.assertEqual(ledger.path.read_bytes(), bytes(raw))


    def test_reentrant_add_during_write_is_refused_without_second_event(self):
        """An injected same-thread callback cannot append with stale state."""
        from unittest.mock import patch
        import os
        temp, ledger = seeded(goal=2)
        with temp:
            before = ledger.path.read_bytes()
            real_write = os.write
            invoked = []
            denied = []
            def reenter(fd, content):
                if not invoked:
                    invoked.append(True)
                    try:
                        ledger.add("NESTED", test="never allowed")
                    except exp.Hold as exc:
                        denied.append(str(exc))
                return real_write(fd, content)
            with patch.object(exp.os, "write", side_effect=reenter):
                ledger.add("OUTER", test="single append")
            self.assertEqual(invoked, [True])
            self.assertTrue(any("REENTRANT" in text or "CONCURRENT" in text
                                for text in denied), denied)
            self.assertFalse(ledger.items("NESTED"))
            self.assertEqual(len(ledger.items("OUTER")), 1)
            self.assertTrue(ledger.path.read_bytes().startswith(before))
            readback = exp.Ledger(ledger.folder)
            self.assertEqual(len(readback.items("OUTER")), 1)
            self.assertEqual(readback.hash, ledger.hash)

    def test_same_instance_two_threads_cannot_both_append(self):
        """Deterministic overlap at first write, without real provider IO."""
        from unittest.mock import patch
        import os
        import threading
        temp, ledger = seeded(goal=2)
        with temp:
            before = ledger.path.read_bytes()
            gate = threading.Event()
            release = threading.Event()
            results = {}
            real_write = os.write
            def paused_write(fd, chunk):
                if (threading.current_thread().name == "ario-writer-one"
                        and not gate.is_set()):
                    gate.set()
                    if not release.wait(5):
                        raise TimeoutError("synthetic writer rendezvous timed out")
                return real_write(fd, chunk)
            def worker(name, kind):
                try:
                    ledger.add(kind, test="thread")
                    results[name] = "APPENDED"
                except BaseException as exc:
                    results[name] = exc
            first = threading.Thread(target=worker, args=("first", "FIRST"),
                                     name="ario-writer-one")
            second = threading.Thread(target=worker, args=("second", "SECOND"),
                                      name="ario-writer-two")
            with patch.object(exp.os, "write", side_effect=paused_write):
                first.start()
                try:
                    self.assertTrue(gate.wait(5), "first writer did not reach write")
                    second.start()
                    second.join(timeout=4)
                    self.assertFalse(second.is_alive(), "second writer hung")
                finally:
                    release.set()
                    first.join(timeout=5)
                    if second.ident is not None:
                        second.join(timeout=5)
            self.assertFalse(first.is_alive())
            self.assertIsInstance(results.get("second"), exp.Hold, results)
            self.assertRegex(str(results["second"]), "REENTRANT|CONCURRENT")
            self.assertEqual(results.get("first"), "APPENDED", results)
            self.assertTrue(ledger.path.read_bytes().startswith(before))
            readback = exp.Ledger(ledger.folder)
            self.assertEqual(len(readback.items("FIRST")), 1)
            self.assertFalse(readback.items("SECOND"))
            self.assertEqual(readback.hash, ledger.hash)

    def test_two_concurrent_runs_same_ledger_only_one_fake_dispatch(self):
        """Two run() preflights cannot both dispatch the same logical turn."""
        from unittest.mock import patch
        import threading
        temp, ledger = seeded(goal=1)
        with temp:
            entered = threading.Event()
            release = threading.Event()
            original_messages = exp.make_messages
            fake = Fake()
            results = {}
            def rendezvous_messages(who, prior, letter):
                if (threading.current_thread().name == "ario-runner-one"
                        and not entered.is_set()):
                    entered.set()
                    if not release.wait(5):
                        raise TimeoutError("synthetic run rendezvous timed out")
                return original_messages(who, prior, letter)
            def run_worker(name):
                try:
                    results[name] = exp.run(ledger, LETTER, "local-not-logged",
                                            fake)
                except BaseException as exc:
                    results[name] = exc
            first = threading.Thread(target=run_worker, args=("first",),
                                     name="ario-runner-one")
            second = threading.Thread(target=run_worker, args=("second",),
                                      name="ario-runner-two")
            with patch.object(exp, "make_messages",
                              side_effect=rendezvous_messages):
                first.start()
                try:
                    self.assertTrue(entered.wait(5), "first run did not reach rendezvous")
                    second.start()
                    second.join(timeout=4)
                    self.assertFalse(second.is_alive(), "second run hung")
                finally:
                    release.set()
                    first.join(timeout=5)
                    if second.ident is not None:
                        second.join(timeout=5)
            self.assertFalse(first.is_alive())
            self.assertEqual(results.get("first"), "PAUSED_OPEN_WINDOW_REACHED", results)
            self.assertIsInstance(results.get("second"), exp.Hold, results)
            self.assertRegex(str(results["second"]), "REENTRANT|CONCURRENT")
            self.assertEqual(len(fake.calls), 1)
            reloaded = exp.Ledger(ledger.folder)
            self.assertEqual(len(reloaded.items("ATTEMPT")), 1)
            self.assertEqual(len(reloaded.items("REPLY")), 1)

    def test_ledger_untampered_appends_refresh_cached_digest(self):
        temp, ledger = seeded(goal=2)
        with temp:
            ledger.add("SCRATCH_ONE", evidence="test")
            ledger.add("SCRATCH_TWO", evidence="test")
            readback = exp.Ledger(ledger.folder)
            self.assertEqual(readback.hash, ledger.hash)
            self.assertEqual(len(readback.events), len(ledger.events))


    def test_documented_hostile_writer_race_after_hash_before_append(self):
        """Observe the unfixed gap: a malicious co-writer can race the append."""
        import os
        from unittest.mock import patch
        temp, ledger = seeded(goal=2)
        with temp:
            original = ledger.path.read_bytes()
            needle = b'"timestamp_utc":"'
            at = original.index(needle) + len(needle)
            replacement = b"9" if original[at:at + 1] != b"9" else b"8"
            old_write = os.write
            injected = []
            def race_write(fd, chunk):
                if not injected:
                    injected.append(True)
                    # Another actor modifies the same inode and size after
                    # the runner has completed the digest comparison.
                    with ledger.path.open("r+b") as competing:
                        competing.seek(at)
                        competing.write(replacement)
                        competing.flush()
                return old_write(fd, chunk)
            with patch.object(exp.os, "write", side_effect=race_write):
                ledger.add("SCRATCH_RACE", synthetic=True)
            self.assertEqual(injected, [True])
            self.assertGreater(ledger.path.stat().st_size, len(original))
            self.assertEqual(ledger.path.read_bytes()[at:at + 1], replacement)
            # There is NO claim of prevention: damage is only detected on reload.
            with self.assertRaisesRegex(exp.Hold, "EVENT_CHAIN_MISMATCH"):
                exp.Ledger(ledger.folder)

    def test_partial_record_write_strands_ledger_without_silent_repair(self):
        """Observe intended fail-closed availability failure, without repairing bytes."""
        import os
        from unittest.mock import patch
        temp, ledger = seeded(goal=2)
        with temp:
            before = ledger.path.read_bytes()
            original_write = os.write
            invoked = []
            def fail_after_first_short_write(fd, chunk):
                if not invoked:
                    invoked.append(True)
                    return original_write(fd, chunk[:7])
                raise OSError("synthetic disk write failure")
            with patch.object(exp.os, "write", side_effect=fail_after_first_short_write):
                with self.assertRaisesRegex(OSError, "synthetic disk write failure"):
                    ledger.add("SCRATCH_PARTIAL", synthetic=True)
            damaged = ledger.path.read_bytes()
            self.assertTrue(damaged.startswith(before))
            self.assertNotEqual(damaged, before)
            with self.assertRaisesRegex(exp.Hold, "INCOMPLETE_TRAILING_EVENT_LINE"):
                exp.Ledger(ledger.folder)
            self.assertEqual(ledger.path.read_bytes(), damaged)


    def test_malformed_event_json_is_typed_hold_before_fake_transport(self):
        from unittest.mock import patch
        cases = (
            ("json_null", b"null\n"),
            ("deep_json", b"[" * 20_000 + b"0" + b"]" * 20_000 + b"\n"),
        )
        for name, raw in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                folder = Path(temp)
                path = folder / "events.jsonl"
                path.write_bytes(raw)
                fake = Fake()
                with patch.object(exp.Ledger, "add", side_effect=AssertionError("unexpected append")) as added:
                    with self.assertRaisesRegex(exp.Hold, "INVALID_OR_INCOMPLETE_EVENT_LOG"):
                        resumed = exp.Ledger(folder)
                        exp.run(resumed, LETTER, "local-not-logged", fake)
                    added.assert_not_called()
                self.assertFalse(fake.calls)
                self.assertEqual(path.read_bytes(), raw)

    def test_complete_attempt_write_then_failed_fsync_never_auto_retries(self):
        from unittest.mock import patch
        temp, ledger = seeded(goal=2)
        with temp:
            baseline = (len(ledger.events), ledger.hash, ledger.byte_length,
                        ledger._content_digest.digest())
            original = ledger.path.read_bytes()
            with patch.object(exp.os, "fsync", side_effect=OSError("injected postwrite fsync")):
                with self.assertRaisesRegex(OSError, "injected postwrite fsync"):
                    ledger.add("ATTEMPT", attempt_seq=1, speaker="A", expected_turn=1)
            self.assertEqual(
                (len(ledger.events), ledger.hash, ledger.byte_length,
                 ledger._content_digest.digest()), baseline)
            completed = ledger.path.read_bytes()
            self.assertTrue(completed.startswith(original))
            self.assertGreater(len(completed), len(original))
            loaded = exp.Ledger(ledger.folder)
            self.assertEqual(loaded.last()["kind"], "ATTEMPT")
            fake = Fake()
            with self.assertRaisesRegex(exp.Hold, "DISPATCH_UNKNOWN_UNRESOLVED_ATTEMPT"):
                exp.run(loaded, LETTER, "local-not-logged", fake)
            self.assertFalse(fake.calls)
            self.assertEqual(ledger.path.read_bytes(), completed)


    def test_hash_valid_malformed_event_fields_hold_before_transport(self):
        # An attacker can make internally hash-consistent JSON while omitting
        # fields required by current(), Ledger.items() and later dispatch.
        objects = (
            ("missing_kind", {"data": {}}),
            ("empty_kind", {"kind": "", "data": {}}),
            ("boolean_kind", {"kind": True, "data": {}}),
            ("scalar_data", {"kind": "INIT", "data": 1}),
            ("missing_data", {"kind": "INIT"}),
        )
        for name, additions in objects:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                folder = Path(temp)
                event = {"seq": 1, "previous_sha256": "0" * 64,
                         "timestamp_utc": "2026-11-07T00:00:00Z", **additions}
                canonical = json.dumps(event, ensure_ascii=False, sort_keys=True,
                                       separators=(",", ":")).encode("utf-8")
                event["event_sha256"] = hashlib.sha256(canonical).hexdigest()
                raw = json.dumps(event, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":")).encode("utf-8") + b"\n"
                path = folder / "events.jsonl"
                path.write_bytes(raw)
                fake = Fake()
                with self.assertRaisesRegex(exp.Hold, "INVALID_OR_INCOMPLETE_EVENT_LOG"):
                    ledger = exp.Ledger(folder)
                    exp.run(ledger, LETTER, "local-not-logged", fake)
                self.assertEqual(path.read_bytes(), raw)
                self.assertFalse(fake.calls)


    def test_hash_valid_nested_init_data_hold_before_transport(self):
        """A valid chain hash is not evidence of valid nested replay state."""
        from unittest.mock import patch
        cases = (
            ("null_history", {"imported_messages": None}),
            ("mapping_history", {"imported_messages": {}}),
            ("null_imported_item", {"imported_messages": [None],
                                    "baseline_count": 1}),
            ("wrong_imported_turn", {"imported_messages": [
                {"turn": "1", "speaker": "A", "content": "hello"}],
                "baseline_count": 1}),
            ("wrong_imported_speaker", {"imported_messages": [
                {"turn": 1, "speaker": "B", "content": "hello"}],
                "baseline_count": 1}),
            ("wrong_imported_content", {"imported_messages": [
                {"turn": 1, "speaker": "A", "content": None}],
                "baseline_count": 1}),
            ("null_baseline", {"baseline_count": None}),
            ("string_target", {"target_new_messages": "2"}),
            ("boolean_target", {"target_new_messages": True}),
        )
        for label, updates in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                original = exp.Ledger(folder)
                exp.init_run(original, LETTER, exp.LETTER_SHA256, [], None, 2)
                event = json.loads(original.path.read_bytes())
                event["data"].update(updates)
                event.pop("event_sha256")
                event["event_sha256"] = exp.sha(exp.canonical(event))
                raw = exp.canonical(event) + b"\n"
                original.path.write_bytes(raw)
                fake = Fake()
                with patch.object(exp.Ledger, "add",
                                  side_effect=AssertionError("unexpected append")) as appended:
                    with self.assertRaisesRegex(exp.Hold,
                                                "INVALID_OR_INCOMPLETE_EVENT_LOG"):
                        resumed = exp.Ledger(folder)
                        exp.run(resumed, LETTER, "local-not-logged", fake)
                    appended.assert_not_called()
                self.assertFalse(fake.calls)
                self.assertEqual(original.path.read_bytes(), raw)

    def test_hash_valid_nested_non_init_fields_hold_before_transport(self):
        """Malformed consumed fields in later event kinds must fail on replay."""
        from unittest.mock import patch
        cases = (
            ("reply_null_content", "REPLY",
             {"attempt_seq": 1, "speaker": "A", "turn": 1, "content": None}),
            ("reply_string_turn", "REPLY",
             {"attempt_seq": 1, "speaker": "A", "turn": "1", "content": "hi"}),
            ("extend_null_additional", "EXTEND", {"additional": None}),
            ("attempt_null_seq", "ATTEMPT",
             {"attempt_seq": None, "speaker": "A", "expected_turn": 1}),
            ("pause_null_reason", "PAUSE",
             {"attempt_seq": 1, "reason": None}),
            ("window_string_count", "WINDOW_REACHED_OPEN",
             {"total_count": 0, "new_count": "0",
              "status": "PAUSED_OPEN_NOT_CLOSED"}),
            ("stop_null_turn", "VOLUNTARY_STOP",
             {"speaker": "A", "turn": None}),
            ("loop_null_speaker", "PAUSED_LOOP",
             {"speaker": None, "turn": 1}),
        )
        for label, kind, data in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                original = exp.Ledger(folder)
                exp.init_run(original, LETTER, exp.LETTER_SHA256, [], None, 2)
                original.add(kind, **data)
                raw = original.path.read_bytes()
                fake = Fake()
                with patch.object(exp.Ledger, "add",
                                  side_effect=AssertionError("unexpected append")) as appended:
                    with self.assertRaisesRegex(exp.Hold,
                                                "INVALID_OR_INCOMPLETE_EVENT_LOG"):
                        resumed = exp.Ledger(folder)
                        exp.run(resumed, LETTER, "local-not-logged", fake)
                    appended.assert_not_called()
                self.assertFalse(fake.calls)
                self.assertEqual(original.path.read_bytes(), raw)

    def test_postclose_error_blocks_same_instance_reuse_before_fake_dispatch(self):
        """A complete ATTEMPT can survive a failed close; never retry it blindly."""
        from unittest.mock import patch
        temp, ledger = seeded(goal=1)
        with temp:
            before = ledger.path.read_bytes()
            calls = []
            class FakeReached(Exception):
                pass
            def transport(_request, _key):
                calls.append("dispatched")
                raise FakeReached("must not reach fake transport")

            real_fsync, real_close = exp.os.fsync, exp.os.close
            synced = set()
            injected = []
            def tracked_fsync(fd):
                real_fsync(fd)
                synced.add(fd)
            def close_after_real_close(fd):
                real_close(fd)
                if fd in synced and not injected:
                    injected.append(True)
                    raise OSError("synthetic after real close")

            with patch.object(exp, "now", return_value="2026-11-07T00:00:00Z"):
                with patch.object(exp.os, "fsync", side_effect=tracked_fsync), \
                     patch.object(exp.os, "close", side_effect=close_after_real_close):
                    with self.assertRaisesRegex(OSError, "synthetic after real close"):
                        exp.run(ledger, LETTER, "synthetic", transport)
                first_disk = ledger.path.read_bytes()
                self.assertEqual(injected, [True])
                self.assertEqual(calls, [])
                self.assertTrue(first_disk.startswith(before))
                # No claim of *absence*: an ATTEMPT may be complete on disk.
                reloaded = exp.Ledger(ledger.folder)
                self.assertEqual(reloaded.last()["kind"], "ATTEMPT")
                with self.assertRaisesRegex(exp.Hold, "DISPATCH_UNKNOWN_UNRESOLVED_ATTEMPT"):
                    exp.run(reloaded, LETTER, "synthetic", transport)
                # Original instance must reject reuse before any write or dispatch.
                with self.assertRaisesRegex(exp.Hold, "UNCERTAIN_APPEND"):
                    exp.run(ledger, LETTER, "synthetic", transport)
                self.assertEqual(calls, [])
                self.assertEqual(ledger.path.read_bytes(), first_disk)


if __name__ == "__main__":
    unittest.main()
