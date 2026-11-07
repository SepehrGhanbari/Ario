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
            # Freeze source bytes explicitly: Path.write_text translates LF
            # to CRLF on Windows, while import_legacy hashes actual bytes.
            frozen = raw.encode("utf-8")
            source.write_bytes(frozen)
            messages, h = exp.import_legacy(source)
            self.assertEqual(h, exp.sha(frozen))
            self.assertEqual(len(messages), 2)
            self.assertEqual(source.read_bytes(), frozen)

    def test_legacy_crlf_jsonl_preserves_original_byte_hash(self):
        # CRLF from a Windows export must be parsed without claiming LF bytes.
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "old-windows.jsonl"
            raw = ('{"speaker":"Ava-A","turn":1,"content":"Hello"}\r\n'
                   '{"speaker":"Ava-B","turn":2,"content":"Hi"}\r\n').encode("utf-8")
            source.write_bytes(raw)
            messages, digest = exp.import_legacy(source)
            self.assertEqual(len(messages), 2)
            self.assertEqual(digest, exp.sha(raw))
            self.assertEqual(source.read_bytes(), raw)

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
        # A fake flag must not erase the real Windows CRT binary mode.
        # Without it, os.write silently transforms LF into CRLF and
        # ExclusiveRunLock correctly refuses to release its altered bytes.
        native_binary = getattr(os, "O_BINARY", 0)
        marker = 1 << 27
        flags_seen = []
        def fake_open(path, flags, mode=0o777, *, dir_fd=None):
            if str(path).endswith((".run_writer.lock", "events.jsonl")):
                flags_seen.append((str(path), flags))
            real_flags = (flags & ~marker) | (native_binary if flags & marker else 0)
            if dir_fd is not None:
                return original(path, real_flags, mode, dir_fd=dir_fd)
            return original(path, real_flags, mode)
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


if __name__ == "__main__":
    unittest.main()
