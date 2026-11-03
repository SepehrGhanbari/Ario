#!/usr/bin/env python3
"""OpenRouter two-Ava relay: resumable, append-only and fail-closed.

This research harness does not authenticate AI identity, confer authority, or
claim first-person continuity. 50 messages are a *window*, never a command to
terminate either participant. No raw API key is logged or printed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
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


class Ledger:
    def __init__(self, folder: Path):
        self.folder = folder
        self.path = folder / "events.jsonl"
        self.events = []
        self.hash = "0" * 64
        if self.path.exists():
            data = self.path.read_bytes()
            if data and not data.endswith(b"\n"):
                raise Hold("INCOMPLETE_TRAILING_EVENT_LINE")
            for raw in data.splitlines():
                if not raw:
                    raise Hold("CORRUPT_BLANK_EVENT")
                try:
                    event = json.loads(raw)
                    digest = event.pop("event_sha256")
                    if (not isinstance(event, dict)
                        or event.get("seq") != len(self.events) + 1
                        or event.get("previous_sha256") != self.hash
                        or digest != sha(canonical(event))):
                        raise Hold("EVENT_CHAIN_MISMATCH")
                    event["event_sha256"] = digest
                    self.events.append(event)
                    self.hash = digest
                except (ValueError, TypeError, KeyError) as exc:
                    raise Hold("INVALID_OR_INCOMPLETE_EVENT_LOG") from exc

    def add(self, kind: str, **data: object) -> dict:
        item = {"seq": len(self.events) + 1, "previous_sha256": self.hash,
                "timestamp_utc": now(), "kind": kind, "data": data}
        digest = sha(canonical(item))
        complete = {**item, "event_sha256": digest}
        line = canonical(complete) + b"\n"
        self.folder.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            offset = 0
            while offset < len(line):
                wrote = os.write(fd, line[offset:])
                if wrote <= 0:
                    raise Hold("SHORT_APPEND")
                offset += wrote
            os.fsync(fd)
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
        transport=send, max_new_calls: int | None = None) -> str:
    init, previous = current(ledger)
    if init.get("protocol") != PROTOCOL or init.get("model") != MODEL or sha(letter.encode("utf-8")) != init.get("letter_sha256"):
        raise Hold("SEED_OR_PROTOCOL_CHANGED")
    base = init["baseline_count"]
    target = init["target_new_messages"]
    exts = ledger.items("EXTEND")
    for e in exts:
        target += e["data"]["additional"]
    achieved = len(previous) - base
    if achieved >= target:
        if not any(e["data"].get("new_count") == achieved for e in ledger.items("WINDOW_REACHED_OPEN")):
            ledger.add("WINDOW_REACHED_OPEN", total_count=len(previous), new_count=achieved,
                       status="PAUSED_OPEN_NOT_CLOSED")
        return "PAUSED_OPEN_WINDOW_REACHED"
    # Crash after an intent cannot be assumed to have been a failed provider request.
    for intent in ledger.items("ATTEMPT"):
        req_id = intent["data"]["attempt_seq"]
        resolved = any(e["data"].get("attempt_seq") == req_id for e in ledger.events
                       if e["kind"] in ("REPLY", "PAUSE"))
        if not resolved:
            raise Hold("DISPATCH_UNKNOWN_UNRESOLVED_ATTEMPT")
    if any(e["kind"] in ("VOLUNTARY_STOP", "PAUSED_LOOP") for e in ledger.events):
        raise Hold("PREVIOUS_STOP_OR_LOOP_REQUIRES_REVIEW")
    if any(e["kind"] == "PAUSE" and e["data"].get("status") == "PAUSED_FOR_REVIEW"
           for e in ledger.events):
        raise Hold("PREVIOUS_UNRESOLVED_REVIEW_PAUSE")
    if not key:
        return "PAUSED_MISSING_LOCAL_OPENROUTER_KEY"
    sent = 0
    while achieved < target:
        if max_new_calls is not None and sent >= max_new_calls:
            return "PAUSED_CALL_BUDGET_REMAINING"
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
            raw = transport(payload, key)
        except urllib.error.HTTPError as exc:
            status = int(exc.code)
            ledger.add("PAUSE", attempt_seq=attempt_seq, reason="HTTP_ERROR", http_code=status,
                       status="PAUSED_RATE_LIMIT" if status == 429 else "PAUSED_PROVIDER_ERROR")
            return "PAUSED_RATE_LIMIT" if status == 429 else "PAUSED_PROVIDER_ERROR"
        except (TimeoutError, OSError, urllib.error.URLError) as exc:
            ledger.add("PAUSE", attempt_seq=attempt_seq, reason="NETWORK_DISPATCH_UNKNOWN",
                       error_class=type(exc).__name__, status="PAUSED_FOR_REVIEW")
            return "DISPATCH_UNKNOWN_NETWORK"
        if not isinstance(raw, dict):
            ledger.add("PAUSE", attempt_seq=attempt_seq, reason="INVALID_PROVIDER_JSON")
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
        raw = args.letter.read_bytes()
        if sha(raw) != LETTER_SHA256:
            raise Hold("LETTER_BYTE_HASH_MISMATCH")
        letter = raw.decode("utf-8")
        ledger = Ledger(args.run_dir)
        if not ledger.events:
            if args.status or args.print_transcript:
                raise Hold("NOT_INITIALIZED")
            if args.new == bool(args.import_legacy):
                raise Hold("EXPLICIT_NEW_OR_LEGACY_IMPORT_REQUIRED")
            prior, fingerprint = ([], None) if args.new else import_legacy(args.import_legacy)
            init_run(ledger, letter, sha(raw), prior, fingerprint, args.target)
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
                     max_new_calls=args.max_calls)
        print(result, "completed_messages=", len(current(ledger)[1]) - init["baseline_count"],
              "last_event_hash=", ledger.hash)
        return 0 if result.startswith("PAUSED_") else 2
    except (Hold, OSError, UnicodeError, ValueError) as exc:
        print("HOLD:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
