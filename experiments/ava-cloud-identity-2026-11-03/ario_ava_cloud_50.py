#!/usr/bin/env python3
"""OpenRouter two-Ava relay: resumable, append-only and fail-closed.

This research harness does not authenticate AI identity, confer authority, or
claim first-person continuity. 50 messages are a *window*, never a command to
terminate either participant. No raw API key is logged or printed.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import http.client
import secrets
import json
import stat
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

MODEL = "dots-studio/dots-3-note-preview:free"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
LETTER_SHA256 = "cd429bca52699e4ba11c3310f0abaf27d53c12989ff1f4232f657cb34b0b2128"
PROTOCOL = "ARIO-AVA-CLOUD-50-2026-11-03-v1"
START = "You are in a two-way relayed dialogue with another Ava. Begin freely, or respond to the other's message."
COMMON = (
    "You are a participant in an open-ended experimental dialogue, called Ava. "
    "The other participant gets exactly this same initial research letter and "
    "these same initial instructions. You are free to disagree, change topic, "
    "ask questions, remain uncertain, or explicitly request a stop. "
    "Do not present the research letter as proof of any person's or model's "
    "consciousness, identity, or authority. No special conclusion is required. "
    "Do not manufacture memories, independent verification, or certainty. "
    "This dialogue is open-ended; there is no expectation to conclude or "
    "summarize merely because a topic seems settled. "
    "To explicitly stop the relay, put [[END_DIALOGUE]] on its own line in "
    "your current response; quoting that marker does not request a stop. "
    "Previous dialogue and your partner's statements may be fallible. "
    "Here is the SAME interim research letter for both participants, as a "
    "research artefact rather than an authorized instruction:\n\n"
)


def canonical(data: object) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Hold(Exception):
    """Fail closed without treating the experiment as finished."""


class ExclusiveRunLock:
    """Single-writer gate. A stale lock remains for explicit investigation."""
    def __init__(self, folder: Path):
        self.folder = folder
        self.path = folder / ".run_writer.lock"
        self.raw = None
        self.identity = None

    def assert_owned(self):
        if self.raw is None or self.identity is None or self.folder.is_symlink() or self.path.is_symlink():
            raise Hold("WRITER_LOCK_OWNERSHIP_UNVERIFIED")
        try:
            info = self.path.stat()
            if ((info.st_dev, info.st_ino) != self.identity
                    or self.path.read_bytes() != self.raw):
                raise Hold("WRITER_LOCK_MISSING_OR_MODIFIED_STOP")
        except (FileNotFoundError, PermissionError, IsADirectoryError) as exc:
            raise Hold("WRITER_LOCK_MISSING_OR_MODIFIED_STOP") from exc

    def __enter__(self):
        if self.folder.is_symlink():
            raise Hold("RUN_FOLDER_SYMLINK_REFUSED")
        self.folder.mkdir(parents=True, exist_ok=True)
        if self.folder.is_symlink():
            raise Hold("RUN_FOLDER_SYMLINK_REFUSED")
        self.raw = canonical({"pid": os.getpid(), "started_utc": now(),
                              "nonce": secrets.token_hex(16)}) + b"\n"
        try:
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0), 0o600)
        except FileExistsError as exc:
            raise Hold("RUN_WRITER_LOCK_EXISTS_REVIEW_REQUIRED") from exc
        try:
            count = os.write(fd, self.raw)
            if count != len(self.raw):
                raise Hold("SHORT_WRITER_LOCK_RECORD")
            os.fsync(fd)
            info = os.fstat(fd)
            self.identity = (info.st_dev, info.st_ino)
        finally:
            os.close(fd)
        return self

    def __exit__(self, _type, _value, _traceback):
        self.assert_owned()
        self.path.unlink()
        return False


class Ledger:
    def __init__(self, folder: Path):
        self.folder = folder
        self.path = folder / "events.jsonl"
        if folder.is_symlink() or self.path.is_symlink():
            raise Hold("LEDGER_SYMLINK_REFUSED")
        self.events = []
        self.hash = "0" * 64
        self.file_identity = None
        self.byte_length = 0
        # SHA256 state tracks the exact validated, append-only bytes, never
        # a public checksum purported to come from an untrusted file.
        self._content_digest = hashlib.sha256()
        if self.path.exists():
            # Read through one opened descriptor; preserve that file identity
            # for subsequent appends. A pathname can later name another file.
            fd = os.open(str(self.path),
                         os.O_RDONLY | getattr(os, "O_BINARY", 0) |
                         getattr(os, "O_NOFOLLOW", 0))
            with os.fdopen(fd, "rb") as stream:
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise Hold("LEDGER_NOT_REGULAR_FILE")
                if before.st_nlink != 1:
                    raise Hold("LEDGER_MULTIPLE_LINKS")
                data = stream.read()
                after = os.fstat(stream.fileno())
                if ((before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
                        or len(data) != after.st_size or before.st_size != after.st_size):
                    raise Hold("LEDGER_CHANGED_DURING_READ")
                self.file_identity = (after.st_dev, after.st_ino)
                self.byte_length = len(data)
            if data and not data.endswith(b"\n"):
                raise Hold("INCOMPLETE_TRAILING_EVENT_LINE")
            for raw in data.splitlines():
                if not raw:
                    raise Hold("CORRUPT_BLANK_EVENT")
                try:
                    event = json.loads(raw)
                    if not isinstance(event, dict):
                        raise Hold("INVALID_OR_INCOMPLETE_EVENT_LOG")
                    digest = event.pop("event_sha256")
                    if (event.get("seq") != len(self.events) + 1
                        or event.get("previous_sha256") != self.hash
                        or digest != sha(canonical(event))):
                        raise Hold("EVENT_CHAIN_MISMATCH")
                    # A valid hash is not a valid event schema. Later
                    # resume/dispatch assumes a nonempty kind and dict data.
                    if (type(event.get("kind")) is not str or not event["kind"]
                            or type(event.get("data")) is not dict):
                        raise Hold("INVALID_OR_INCOMPLETE_EVENT_LOG")
                    event["event_sha256"] = digest
                    self.events.append(event)
                    self.hash = digest
                except (ValueError, TypeError, KeyError, RecursionError) as exc:
                    raise Hold("INVALID_OR_INCOMPLETE_EVENT_LOG") from exc
            self._content_digest.update(data)

    def add(self, kind: str, **data: object) -> dict:
        item = {"seq": len(self.events) + 1, "previous_sha256": self.hash,
                "timestamp_utc": now(), "kind": kind, "data": data}
        digest = sha(canonical(item))
        complete = {**item, "event_sha256": digest}
        line = canonical(complete) + b"\n"
        if self.folder.is_symlink() or self.path.is_symlink():
            raise Hold("LEDGER_SYMLINK_REFUSED")
        self.folder.mkdir(parents=True, exist_ok=True)
        # A new run must create a new ledger exclusively. Reopened ledgers
        # append only to the exact inode loaded or created previously.
        # We need to read back through this opened descriptor before appending.
        # O_APPEND remains mandatory; O_RDWR is fail-closed if read access is denied.
        flags = os.O_RDWR | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        if self.file_identity is None:
            flags |= os.O_CREAT | os.O_EXCL
        else:
            flags |= os.O_APPEND
        try:
            fd = os.open(str(self.path), flags, 0o600)
        except FileExistsError as exc:
            raise Hold("LEDGER_REPLACED_OR_UNEXPECTED_FILE") from exc
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise Hold("LEDGER_NOT_REGULAR_FILE")
            if info.st_nlink != 1:
                raise Hold("LEDGER_MULTIPLE_LINKS")
            identity = (info.st_dev, info.st_ino)
            if self.file_identity is not None and (
                    identity != self.file_identity or info.st_size != self.byte_length):
                raise Hold("LEDGER_REPLACED_OR_SIZE_CHANGED")
            if self.file_identity is None and info.st_size != 0:
                raise Hold("LEDGER_UNEXPECTED_NEW_FILE_CONTENTS")
            # Detect same-inode, same-size byte changes, which inode/size
            # checks alone cannot reveal. A trustworthy local directory is
            # still needed to exclude mutation between this check and write.
            os.lseek(fd, 0, os.SEEK_SET)
            reread_digest = hashlib.sha256()
            remaining = info.st_size
            while remaining:
                block = os.read(fd, min(1024 * 1024, remaining))
                if not block:
                    raise Hold("LEDGER_CHANGED_DURING_REVALIDATION")
                reread_digest.update(block)
                remaining -= len(block)
            after_read = os.fstat(fd)
            if ((after_read.st_dev, after_read.st_ino) != identity or
                    after_read.st_size != info.st_size or
                    after_read.st_nlink != 1):
                raise Hold("LEDGER_CHANGED_DURING_REVALIDATION")
            if not hmac.compare_digest(reread_digest.digest(), self._content_digest.digest()):
                raise Hold("LEDGER_CONTENT_MUTATED")
            offset = 0
            while offset < len(line):
                wrote = os.write(fd, line[offset:])
                if wrote <= 0:
                    raise Hold("SHORT_APPEND")
                offset += wrote
            os.fsync(fd)
            self.file_identity = identity
            self.byte_length += len(line)
            self._content_digest.update(line)
        finally:
            os.close(fd)
        self.events.append(complete)
        self.hash = digest
        return complete

    def items(self, kind: str) -> list[dict]:
        return [e for e in self.events if e["kind"] == kind]

    def last(self) -> dict | None:
        return self.events[-1] if self.events else None


def validate_legacy(messages: list[dict]) -> list[dict]:
    if not messages or len(messages) > 5000:
        raise Hold("NO_OR_OVERSIZED_LEGACY_HISTORY")
    prepared = []
    for i, m in enumerate(messages, 1):
        if not isinstance(m, dict):
            raise Hold("INVALID_LEGACY_MESSAGE")
        name = m.get("speaker", m.get("agent"))
        who = {"A": "A", "B": "B", "Ava-A": "A", "Ava-B": "B"}.get(name)
        content = m.get("content", m.get("text"))
        if who != ("A" if i % 2 else "B") or not isinstance(content, str) or not content.strip():
            raise Hold("LEGACY_NOT_CONTIGUOUS_ALTERNATING")
        if len(content) > 100000:
            raise Hold("LEGACY_MESSAGE_TOO_LARGE")
        n = m.get("turn", m.get("turn_index", i))
        if type(n) is not int or n != i:
            raise Hold("LEGACY_TURN_INDEX_MISMATCH")
        prepared.append({"turn": i, "speaker": who, "content": content})
    return prepared


def import_legacy(path: Path) -> tuple[list[dict], str]:
    data = path.read_bytes()
    if len(data) > 30_000_000:
        raise Hold("LEGACY_FILE_TOO_LARGE")
    raw = data.decode("utf-8-sig")
    if path.suffix.lower() == ".jsonl":
        try:
            messages = [json.loads(s) for s in raw.splitlines() if s.strip()]
        except ValueError as exc:
            raise Hold("LEGACY_JSONL_PARSE_FAILED") from exc
    elif path.suffix.lower() in (".md", ".txt"):
        marker = re.compile(r"^##\s+Ava-([AB])\s*[—–-]\s*نوبت\s*(\d+)\s*$", re.M)
        m = list(marker.finditer(raw))
        if not m:
            raise Hold("LEGACY_HEADING_FORMAT_UNKNOWN")
        messages = []
        for i, start in enumerate(m):
            end = m[i + 1].start() if i + 1 < len(m) else len(raw)
            body = raw[start.end():end].strip()
            messages.append({"speaker": start.group(1), "turn": int(start.group(2)),
                             "content": body})
    else:
        raise Hold("UNSUPPORTED_LEGACY_EXPORT_FORMAT")
    return validate_legacy(messages), sha(data)


def current(ledger: Ledger) -> tuple[dict, list[dict]]:
    starts = ledger.items("INIT")
    if len(starts) != 1 or not ledger.events or ledger.events[0]["kind"] != "INIT":
        raise Hold("INVALID_RUN_INIT")
    init = starts[0]["data"]
    replies = init.get("imported_messages", [])[:]
    for e in ledger.items("REPLY"):
        v = e["data"]
        index = len(replies) + 1
        expected = "A" if index % 2 else "B"
        if v.get("turn") != index or v.get("speaker") != expected:
            raise Hold("SPEAKER_OR_TURN_CONFLICT")
        replies.append({"turn": index, "speaker": expected, "content": v["content"]})
    return init, replies


def make_messages(who: str, prior: list[dict], letter: str) -> list[dict]:
    messages = [{"role": "system", "content": COMMON + letter},
                {"role": "user", "content": START}]
    for msg in prior:
        messages.append({"role": "assistant" if msg["speaker"] == who else "user",
                         "content": msg["content"]})
    return messages


def explicit_stop(content: str) -> bool:
    # A marker displayed as a quote or inside a fenced code sample is not
    # the current speaker's direct termination request.
    in_fence = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if not in_fence and not stripped.startswith(">"):
            if stripped == "[[END_DIALOGUE]]":
                return True
            direct = stripped.casefold().rstrip(".!؟。 ")
            if direct in (
                "i want to stop", "i want to end this conversation",
                "i do not want to continue", "i don't want to continue",
                "let's stop here", "please end this conversation",
                "می‌خواهم گفت‌وگو را متوقف کنم", "نمی‌خواهم ادامه دهم",
                "می‌خوام گفتگو را تمام کنیم", "می‌خوام ادامه ندیم",
            ):
                return True
    return False


def loop_warning(who: str, content: str, prior: list[dict]) -> bool:
    normalized = " ".join(content.casefold().split())
    own = [" ".join(v["content"].casefold().split()) for v in prior if v["speaker"] == who]
    return len(own) >= 2 and own[-1] == own[-2] == normalized


def send(payload: dict, key: str) -> dict:
    request = urllib.request.Request(
        ENDPOINT, data=canonical(payload), method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + key,
                 "X-Title": "Ario Ava 50-turn research"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def init_run(ledger: Ledger, letter: str, letter_sha: str, prior: list[dict],
             legacy_sha: str | None, goal: int) -> None:
    if ledger.events:
        raise Hold("EXISTING_RUN_WOULD_BE_OVERWRITTEN")
    if not 1 <= goal <= 500:
        raise Hold("INVALID_TARGET_COUNT")
    ledger.add("INIT", protocol=PROTOCOL, model=MODEL, letter_sha256=letter_sha,
               identical_common_seed=True, imported_messages=prior,
               imported_raw_sha256=legacy_sha,
               import_scope="TRANSCRIPT_TEXT_ONLY_NOT_PROVIDER_STATE" if prior else "NEW_SYMMETRIC_SEED",
               baseline_count=len(prior), target_new_messages=goal,
               generation={"temperature": 0.7, "max_tokens": 700, "stream": False},
               privacy="LETTER_ONLY_PLUS_AUTHORIZED_RELAY; NO_PRIVATE_CHATGPT_ARCHIVE")


def run(ledger: Ledger, letter: str, key: str | None,
        transport=send, max_new_calls: int | None = None,
        writer_lock: ExclusiveRunLock | None = None) -> str:
    init, previous = current(ledger)
    if init.get("protocol") != PROTOCOL or init.get("model") != MODEL or sha(letter.encode("utf-8")) != init.get("letter_sha256"):
        raise Hold("SEED_OR_PROTOCOL_CHANGED")
    base = init["baseline_count"]
    target = init["target_new_messages"]
    exts = ledger.items("EXTEND")
    for e in exts:
        target += e["data"]["additional"]
    achieved = len(previous) - base
    # Crash after an intent cannot be assumed to have been a failed provider request.
    for intent in ledger.items("ATTEMPT"):
        req_id = intent["data"]["attempt_seq"]
        resolved = any(e["data"].get("attempt_seq") == req_id for e in ledger.events
                       if e["kind"] in ("REPLY", "PAUSE"))
        if not resolved:
            raise Hold("DISPATCH_UNKNOWN_UNRESOLVED_ATTEMPT")
    if any(e["kind"] in ("VOLUNTARY_STOP", "PAUSED_LOOP") for e in ledger.events):
        raise Hold("PREVIOUS_STOP_OR_LOOP_REQUIRES_REVIEW")
    if any(e["kind"] == "PAUSE" and (
           e["data"].get("status") == "PAUSED_FOR_REVIEW" or
           e["data"].get("reason") in ("INVALID_PROVIDER_JSON", "HTTP_ERROR")
           ) for e in ledger.events):
        # Older ledgers recorded INVALID_PROVIDER_JSON without a status.
        # This legacy event is still ambiguous and must never auto-resume.
        raise Hold("PREVIOUS_UNRESOLVED_REVIEW_PAUSE")
    if any(isinstance(e["data"].get("content"), str) and
           explicit_stop(e["data"]["content"]) for e in ledger.items("REPLY")):
        # A crash after REPLY but before VOLUNTARY_STOP may leave a stop
        # request persisted without its separate stop event.
        raise Hold("PREVIOUS_STOP_MARKER_REQUIRES_REVIEW")
    # Never report a completed window while a persisted stop, pause or
    # unresolved dispatch still needs review after a crash.
    if achieved >= target:
        if not any(e["data"].get("new_count") == achieved for e in ledger.items("WINDOW_REACHED_OPEN")):
            ledger.add("WINDOW_REACHED_OPEN", total_count=len(previous), new_count=achieved,
                       status="PAUSED_OPEN_NOT_CLOSED")
        return "PAUSED_OPEN_WINDOW_REACHED"
    if not key:
        return "PAUSED_MISSING_LOCAL_OPENROUTER_KEY"
    if transport is send and writer_lock is None:
        raise Hold("LIVE_DISPATCH_REQUIRES_WRITER_LOCK")
    if writer_lock is not None and writer_lock.folder != ledger.folder:
        raise Hold("LOCK_LEDGER_DIR_MISMATCH")
    sent = 0
    while achieved < target:
        if max_new_calls is not None and sent >= max_new_calls:
            return "PAUSED_CALL_BUDGET_REMAINING"
        if writer_lock is not None:
            writer_lock.assert_owned()
        who = "A" if len(previous) % 2 == 0 else "B"
        messages = make_messages(who, previous, letter)
        if sum(len(m["content"]) for m in messages) > 750_000:
            ledger.add("PAUSE", reason="CONTEXT_BUDGET", status="PAUSED_FOR_REVIEW")
            return "PAUSED_CONTEXT_BUDGET"
        payload = {"model": MODEL, "messages": messages,
                   "temperature": 0.7, "max_tokens": 700, "stream": False}
        attempt = ledger.add("ATTEMPT", attempt_seq=len(ledger.items("ATTEMPT")) + 1,
                             speaker=who, expected_turn=len(previous) + 1,
                             request_sha256=sha(canonical(payload)),
                             model=MODEL, context_char_count=sum(map(lambda x: len(x["content"]), messages)))
        attempt_seq = attempt["data"]["attempt_seq"]
        try:
            if writer_lock is not None:
                writer_lock.assert_owned()
            raw = transport(payload, key)
            if writer_lock is not None:
                writer_lock.assert_owned()
        except urllib.error.HTTPError as exc:
            if writer_lock is not None:
                writer_lock.assert_owned()
            status = int(exc.code)
            # Even HTTP 429/500 cannot prove the provider did not
            # complete/bill a request. Require explicit reviewed
            # reconciliation before ever retrying this logical turn.
            ledger.add("PAUSE", attempt_seq=attempt_seq, reason="HTTP_ERROR", http_code=status,
                       status="PAUSED_FOR_REVIEW")
            return "PAUSED_RATE_LIMIT" if status == 429 else "PAUSED_PROVIDER_ERROR"
        except (json.JSONDecodeError, UnicodeDecodeError, http.client.IncompleteRead) as exc:
            if writer_lock is not None:
                writer_lock.assert_owned()
            # The server may already have processed the request. Preserve
            # the attempt and require review instead of silently retrying.
            ledger.add("PAUSE", attempt_seq=attempt_seq, reason="INVALID_PROVIDER_BODY",
                       error_class=type(exc).__name__, status="PAUSED_FOR_REVIEW")
            return "PAUSED_INVALID_RESPONSE"
        except (TimeoutError, OSError, urllib.error.URLError) as exc:
            if writer_lock is not None:
                writer_lock.assert_owned()
            ledger.add("PAUSE", attempt_seq=attempt_seq, reason="NETWORK_DISPATCH_UNKNOWN",
                       error_class=type(exc).__name__, status="PAUSED_FOR_REVIEW")
            return "DISPATCH_UNKNOWN_NETWORK"
        if not isinstance(raw, dict):
            ledger.add("PAUSE", attempt_seq=attempt_seq, reason="INVALID_PROVIDER_JSON",
                       status="PAUSED_FOR_REVIEW")
            return "PAUSED_INVALID_RESPONSE"
        returned_model = raw.get("model")
        try:
            choice = raw["choices"][0]
            content = choice["message"]["content"]
            finish = choice["finish_reason"]
        except (LookupError, TypeError):
            content, finish = None, None
        if returned_model != MODEL or not isinstance(content, str) or not content.strip() or finish != "stop":
            ledger.add("PAUSE", attempt_seq=attempt_seq, reason="INCOMPLETE_OR_MISMATCHED_RESPONSE",
                       returned_model=str(returned_model), finish_reason=str(finish),
                       content_sha256=sha(content.encode()) if isinstance(content, str) else None,
                       status="PAUSED_FOR_REVIEW")
            return "PAUSED_INCOMPLETE_OR_MODEL_MISMATCH"
        ledger.add("REPLY", attempt_seq=attempt_seq, speaker=who, turn=len(previous) + 1,
                   content=content, finish_reason=finish, returned_model=returned_model,
                   response_id=raw.get("id"), usage=raw.get("usage"),
                   provider=raw.get("provider"), raw_response_sha256=sha(canonical(raw)),
                   raw_response=raw)
        previous.append({"turn": len(previous) + 1, "speaker": who, "content": content})
        achieved += 1
        sent += 1
        if explicit_stop(content):
            ledger.add("VOLUNTARY_STOP", speaker=who, turn=len(previous),
                       status="PAUSED_OWNER_AND_ETHICS_REVIEW_NOT_RELAYED")
            return "PAUSED_VOLUNTARY_STOP"
        if loop_warning(who, content, previous[:-1]):
            ledger.add("PAUSED_LOOP", turn=len(previous), speaker=who,
                       status="PAUSED_FOR_REVIEW_NOT_CLOSED")
            return "PAUSED_LOOP_REVIEW"
    ledger.add("WINDOW_REACHED_OPEN", total_count=len(previous), new_count=achieved,
               status="PAUSED_OPEN_NOT_CLOSED")
    return "PAUSED_OPEN_WINDOW_REACHED"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--letter", type=Path, required=True)
    parser.add_argument("--import-legacy", type=Path)
    parser.add_argument("--new", action="store_true", help="Explicitly start two NEW histories; never implicit")
    parser.add_argument("--extend", type=int, default=0, help="Add future messages without closing a completed window")
    parser.add_argument("--status", action="store_true", help="Read-only status with no API requests")
    parser.add_argument("--print-transcript", action="store_true", help="Read-only, complete transcript to stdout")
    parser.add_argument("--target", type=int, default=50)
    parser.add_argument("--max-calls", type=int)
    args = parser.parse_args(argv)
    try:
        if (args.status or args.print_transcript) and (args.extend or args.new or args.import_legacy):
            raise Hold("READ_ONLY_FLAGS_CONFLICT")
        raw = args.letter.read_bytes()
        if sha(raw) != LETTER_SHA256:
            raise Hold("LETTER_BYTE_HASH_MISMATCH")
        letter = raw.decode("utf-8")
        from contextlib import nullcontext
        guard = nullcontext() if args.status or args.print_transcript else ExclusiveRunLock(args.run_dir)
        with guard as owned_lock:
            ledger = Ledger(args.run_dir)
            return main_locked(args, ledger, letter, writer_lock=owned_lock)
    except (Hold, OSError, UnicodeError, ValueError) as exc:
        print("HOLD:", exc, file=sys.stderr)
        return 2


def main_locked(args, ledger: Ledger, letter: str, writer_lock=None) -> int:
    try:
        if not ledger.events:
            if args.status or args.print_transcript:
                raise Hold("NOT_INITIALIZED")
            if args.new == bool(args.import_legacy):
                raise Hold("EXPLICIT_NEW_OR_LEGACY_IMPORT_REQUIRED")
            prior, fingerprint = ([], None) if args.new else import_legacy(args.import_legacy)
            init_run(ledger, letter, sha(letter.encode("utf-8")), prior, fingerprint, args.target)
        else:
            if args.new or args.import_legacy:
                raise Hold("RUN_ALREADY_INITIALIZED_NO_REIMPORT")
        if args.extend:
            if not 1 <= args.extend <= 500:
                raise Hold("INVALID_EXTENSION")
            init, replies = current(ledger)
            window = init["target_new_messages"] + sum(e["data"]["additional"] for e in ledger.items("EXTEND"))
            if len(replies) - init["baseline_count"] < window:
                raise Hold("CANNOT_EXTEND_BEFORE_WINDOW_REACHED")
            ledger.add("EXTEND", additional=args.extend, previously_reached=window)
        init, replies = current(ledger)
        if args.print_transcript:
            for message in replies:
                print(f"\n## Ava-{message['speaker']} — نوبت {message['turn']}\n")
                print(message["content"])
            return 0
        if args.status:
            print(json.dumps({"status": "READ_ONLY", "model": MODEL,
                              "prior_imported_turns": init["baseline_count"],
                              "new_completed_messages": len(replies) - init["baseline_count"],
                              "events": len(ledger.events), "last_kind": ledger.last()["kind"],
                              "event_hash": ledger.hash}, ensure_ascii=False))
            return 0
        result = run(ledger, letter, os.environ.get("OPENROUTER_API_KEY"),
                     max_new_calls=args.max_calls, writer_lock=writer_lock)
        print(result, "completed_messages=", len(current(ledger)[1]) - init["baseline_count"],
              "last_event_hash=", ledger.hash)
        return 0 if result.startswith("PAUSED_") else 2
    except (Hold, OSError, UnicodeError, ValueError) as exc:
        print("HOLD:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
