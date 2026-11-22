"""RECALL-FIRST-01: independent synthetic append-only answer-recall comparator.

NOT the Ario runtime. No positive evidence/trust admission. SHA chain is local
integrity only; it DOES NOT prevent clean rollback by the journal controller.
Single-writer, bounded research prototype, stdlib only.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path


class RecallHold(ValueError):
    """Malformed, ambiguous, or non-admissible synthetic recall state."""


def normalized_question(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise RecallHold("HOLD_EMPTY_OR_INVALID_QUESTION")
    # NFC is an experimental exact-string convention, NOT a versioned Ario
    # semantic-identity policy or proof of question equivalence.
    value = unicodedata.normalize("NFC", text).casefold()
    value = re.sub(r"\s+", " ", value).strip()
    value = value.rstrip("?؟!. ")
    if not value:
        raise RecallHold("HOLD_EMPTY_OR_INVALID_QUESTION")
    return value


def _parse_json_strict(text: str):
    def unique_object(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise RecallHold("HOLD_DUPLICATE_JSON_KEY")
            obj[key] = value
        return obj
    try:
        return json.loads(text, object_pairs_hook=unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(RecallHold("HOLD_NONFINITE_JSON")))
    except (ValueError, TypeError) as exc:
        raise RecallHold("HOLD_INVALID_JOURNAL_JSON") from exc


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: dict) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


class AnswerRecallLab:
    MAX_LOG_BYTES = 4 * 1024 * 1024
    MAX_LINE_BYTES = 64 * 1024
    GENESIS = "0" * 64
    SCHEMA = 1

    def __init__(self, journal_path: str | Path):
        self.path = Path(journal_path)
        self.answers: dict[str, list[dict]] = {}
        self.index: dict[tuple[str, str], set[str]] = {}
        self.sequence = 0
        self.head = self.GENESIS
        self.disk_size = 0
        self.lookup_count = 0
        self.recomputation_calls = 0  # Prototype has no generative/verification interface.
        self.reload()

    @staticmethod
    def _check_string(text, label):
        if not isinstance(text, str) or not text.strip() or len(text) > 12000:
            raise RecallHold(f"HOLD_INVALID_{label}")

    def _apply(self, answers, index, event):
        typ = event["kind"]
        if typ == "ANSWER":
            required = {"kind", "answer_id", "scope", "question", "answer", "source_ref", "stability"}
        elif typ == "ALIAS":
            required = {"kind", "answer_id", "scope", "question"}
        elif typ == "REVISION":
            required = {"kind", "answer_id", "previous_version", "answer", "source_ref", "stability"}
        else:
            raise RecallHold("HOLD_UNKNOWN_EVENT_KIND")
        if set(event) != required:
            raise RecallHold("HOLD_UNEXPECTED_EVENT_FIELDS")
        ident = event["answer_id"]
        self._check_string(ident, "ANSWER_ID")
        if typ == "ANSWER":
            if ident in answers:
                raise RecallHold("HOLD_DUPLICATE_ANSWER_ID")
            for key in ("scope", "question", "answer", "source_ref"):
                self._check_string(event[key], key.upper())
            if event["stability"] not in ("STABLE", "TIME_SENSITIVE"):
                raise RecallHold("HOLD_INVALID_STABILITY")
            answers[ident] = [{"version": 1, "scope": event["scope"], "answer": event["answer"],
                              "source_ref": event["source_ref"],
                              "stability": event["stability"],
                              "record_state": "RECORDED"}]
            idx_key = (event["scope"], normalized_question(event["question"]))
            index.setdefault(idx_key, set()).add(ident)
        elif typ == "ALIAS":
            self._check_string(event["scope"], "SCOPE")
            self._check_string(event["question"], "QUESTION")
            if ident not in answers:
                raise RecallHold("HOLD_MISSING_ANSWER_ID")
            if answers[ident][0]["scope"] != event["scope"]:
                raise RecallHold("HOLD_CROSS_SCOPE_ALIAS")
            # Alias equivalence is explicitly asserted by the synthetic operator;
            # do NOT infer it from embedding similarity, or certify truth.
            index.setdefault((event["scope"], normalized_question(event["question"])), set()).add(ident)
        else:
            if ident not in answers:
                raise RecallHold("HOLD_MISSING_ANSWER_ID")
            if type(event["previous_version"]) is not int or event["previous_version"] != len(answers[ident]):
                raise RecallHold("HOLD_REVISION_VERSION_CONFLICT")
            for key in ("answer", "source_ref"):
                self._check_string(event[key], key.upper())
            if event["stability"] not in ("STABLE", "TIME_SENSITIVE"):
                raise RecallHold("HOLD_INVALID_STABILITY")
            answers[ident].append({"version": len(answers[ident]) + 1,
                                   "scope": answers[ident][0]["scope"],
                                   "answer": event["answer"],
                                   "source_ref": event["source_ref"],
                                   "stability": event["stability"],
                                   "record_state": "RECORDED"})

    def reload(self):
        answers: dict[str, list[dict]] = {}
        index: dict[tuple[str, str], set[str]] = {}
        seq = 0
        head = self.GENESIS
        data = self.path.read_bytes() if self.path.exists() else b""
        if len(data) > self.MAX_LOG_BYTES:
            raise RecallHold("HOLD_JOURNAL_TOO_LARGE")
        if data and not data.endswith(b"\n"):
            raise RecallHold("HOLD_PARTIAL_TAIL")
        for line in data.splitlines(keepends=True):
            if not line.endswith(b"\n") or len(line) > self.MAX_LINE_BYTES or line in (b"\n", b"\r\n"):
                raise RecallHold("HOLD_INVALID_JOURNAL_LINE")
            try:
                row = _parse_json_strict(line[:-1].decode("utf-8"))
            except UnicodeError as exc:
                raise RecallHold("HOLD_INVALID_UTF8") from exc
            if not isinstance(row, dict) or set(row) != {"schema", "seq", "prev", "event", "digest"}:
                raise RecallHold("HOLD_INVALID_JOURNAL_SCHEMA")
            if (type(row["schema"]) is not int or row["schema"] != self.SCHEMA
                or type(row["seq"]) is not int or row["seq"] != seq + 1
                or row["prev"] != head or not isinstance(row["event"], dict)
                or row["digest"] != _digest({k:v for k,v in row.items() if k != "digest"})):
                raise RecallHold("HOLD_JOURNAL_INTEGRITY")
            self._apply(answers, index, row["event"])
            seq += 1
            head = row["digest"]
        self.answers, self.index = answers, index
        self.sequence, self.head, self.disk_size = seq, head, len(data)

    def _append(self, event: dict):
        future_answers = copy.deepcopy(self.answers)
        future_index = copy.deepcopy(self.index)
        self._apply(future_answers, future_index, event)
        payload = {"schema": self.SCHEMA, "seq": self.sequence + 1,
                   "prev": self.head, "event": event}
        row = {**payload, "digest": _digest(payload)}
        encoded = _canonical(row) + b"\n"
        if len(encoded) > self.MAX_LINE_BYTES or self.disk_size + len(encoded) > self.MAX_LOG_BYTES:
            raise RecallHold("HOLD_JOURNAL_BUDGET")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Single-writer lab: detects size conflicts, not concurrent same-size rewrites.
        if self.path.exists() and self.path.stat().st_size != self.disk_size:
            raise RecallHold("HOLD_JOURNAL_CHANGED")
        if not self.path.exists() and self.disk_size:
            raise RecallHold("HOLD_JOURNAL_MISSING")
        with self.path.open("ab") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        self.answers, self.index = future_answers, future_index
        self.sequence += 1
        self.head, self.disk_size = row["digest"], self.disk_size + len(encoded)

    def record_answer(self, question, answer, *, scope, source_ref, stability="STABLE") -> str:
        ident = f"ans_{self.sequence + 1:06d}"
        self._append({"kind": "ANSWER", "answer_id": ident, "scope": scope,
                      "question": question, "answer": answer, "source_ref": source_ref,
                      "stability": stability})
        return ident

    def bind_paraphrase(self, answer_id: str, question: str, *, scope: str):
        self._append({"kind": "ALIAS", "answer_id": answer_id, "scope": scope,
                      "question": question})

    def correct_answer(self, answer_id: str, new_answer: str, *, source_ref: str,
                       stability: str = "STABLE"):
        if answer_id not in self.answers:
            raise RecallHold("HOLD_MISSING_ANSWER_ID")
        self._append({"kind": "REVISION", "answer_id": answer_id,
                      "previous_version": len(self.answers[answer_id]),
                      "answer": new_answer, "source_ref": source_ref,
                      "stability": stability})

    def recall(self, question: str, *, scope: str, ask_current: bool = False) -> dict:
        self._check_string(scope, "SCOPE")
        self.lookup_count += 1
        candidates = self.index.get((scope, normalized_question(question)), set())
        if not candidates:
            return {"disposition": "UNKNOWN_MISSING", "answer": None,
                    "recompute_required": False}
        if len(candidates) != 1:
            return {"disposition": "UNKNOWN_AMBIGUOUS", "answer": None,
                    "recompute_required": False}
        ident = next(iter(candidates))
        current = self.answers[ident][-1]
        if ask_current and current["stability"] == "TIME_SENSITIVE":
            result = "RECHECK_REQUIRED"
        else:
            result = "RECALLED_HISTORICAL" if current["stability"] == "TIME_SENSITIVE" else "RECALLED"
        return {"disposition": result, "answer_id": ident,
                "version": current["version"], "answer": current["answer"],
                "source_ref": current["source_ref"], "record_state": "RECORDED",
                "effective_assessment": "NOT_EVALUATED",
                "recompute_required": result == "RECHECK_REQUIRED"}

    def history(self, answer_id: str) -> list[dict]:
        return copy.deepcopy(self.answers.get(answer_id, []))
