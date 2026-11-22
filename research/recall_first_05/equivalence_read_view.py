"""RECALL-FIRST-05: review-gated, revocable paraphrase *read projection*.

Research-only: a replay of existing RF01 answer journal plus caller-provided
review *annotations*. No production Ario access, no writable alias registry,
no automated semantic proof, no external authority or truth admission.

A separately supplied pinned review head is a laboratory check, NOT a
self-authenticating witness. Both review stream and floor may be attacker-owned.
"""
from __future__ import annotations

import copy
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any, Iterable, Mapping

from recall_first_lab import AnswerRecallLab, RecallHold, normalized_question, _parse_json_strict

GENESIS = '0' * 64
MAX_REVIEW_EVENTS = 1000
MAX_REVIEW_BYTES = 512 * 1024
MAX_REVIEW_FIELD = 12000

class ReviewHold(ValueError):
    pass


def canonical(obj: dict) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(obj: dict) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def _valid_str(v: Any, length=MAX_REVIEW_FIELD) -> bool:
    return type(v) is str and bool(v.strip()) and len(v) <= length


def _file_stamp(path: Path) -> tuple[int, int, int, int, int]:
    if path.is_symlink():
        raise ReviewHold('HOLD_SYMLINK')
    try:
        s = path.stat()
    except OSError as exc:
        raise ReviewHold('HOLD_SOURCE_UNAVAILABLE') from exc
    if not stat.S_ISREG(s.st_mode):
        raise ReviewHold('HOLD_NOT_REGULAR')
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def _snapshot(path: Path) -> tuple[bytes, tuple[int, ...]]:
    a = _file_stamp(path)
    if a[2] > AnswerRecallLab.MAX_LOG_BYTES:
        raise ReviewHold('HOLD_JOURNAL_SIZE')
    fd = -1
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0))
        fst = os.fstat(fd)
        b = (fst.st_dev, fst.st_ino, fst.st_size, fst.st_mtime_ns, fst.st_ctime_ns)
        if b != a or not stat.S_ISREG(fst.st_mode):
            raise ReviewHold('HOLD_OPEN_CHANGED')
        data = os.read(fd, AnswerRecallLab.MAX_LOG_BYTES + 1)
        if len(data) != a[2] or _file_stamp(path) != a:
            raise ReviewHold('HOLD_DURING_READ_CHANGED')
        aft = os.fstat(fd)
        if (aft.st_dev, aft.st_ino, aft.st_size, aft.st_mtime_ns, aft.st_ctime_ns) != a:
            raise ReviewHold('HOLD_DURING_READ_CHANGED')
        return data, a
    except OSError as exc:
        raise ReviewHold('HOLD_FILE_UNREADABLE') from exc
    finally:
        if fd >= 0:
            os.close(fd)


def _mode(question: str, asked: str) -> str:
    if asked not in ('HISTORICAL', 'CURRENT_FACT', 'CURRENT_POLICY'):
        return 'HOLD_QUERY_MODE'
    # Conservative independent check of obvious current/reassessment intent.
    # This is NOT a general semantic intent classifier; uncertain cases HOLD.
    lowered = question.casefold().replace('ي', 'ی').replace('ك', 'ک')
    markers = re.compile(r'(?<!\w)(?:today|now|currently|still|latest|up.to.date|valid\s+today|'
                         r'امروز|الان|اکنون|هنوز|همچنان|فعلی|به.?روز|درست\s+است\s+الان)(?!\w)')
    if asked != 'HISTORICAL' or markers.search(lowered):
        return 'RECHECK_REQUIRED'
    return 'HISTORICAL'


# Deliberately bounded *contrast detectors*, not a semantic-equivalence judge.
# Ambiguities are rejected even when a caller supplies a forged review record.
_TOPIC_TERMS = {
    'archive': ('archive', 'archives', 'آرشیو', 'بایگانی'),
    'memory': ('memory', 'memories', 'حافظه'),
    'trust': ('trust', 'اعتماد'),
    'keys': ('keys', 'key', 'کلید'),
    'pizza': ('pizza', 'پیتزا'),
    'kernel': ('kernel', 'لینوکس'),
}


def _words(q: str) -> set[str]:
    normalized = q.casefold().replace('ي', 'ی').replace('ك', 'ک')
    return set(re.findall(r'[\w\u0600-\u06ff]+', normalized, re.UNICODE))


def _intent(q: str) -> str:
    w = _words(q)
    if w & {'why', 'reason', 'چرا', 'دلیل', 'علت'}:
        return 'WHY'
    if w & {'when', 'زمانی', 'زمان', 'موقع'}:
        return 'WHEN'
    if w & {'who', 'whom', 'کیست', 'کسی'} or 'چه کسی' in q or 'چه‌کسی' in q:
        return 'WHO'
    if w & {'how', 'چگونه', 'چطور'}:
        return 'HOW'
    if w & {'what', 'which', 'چی', 'کدام', 'چه'}:
        return 'WHAT'
    if w & {'is', 'are', 'do', 'did', 'does', 'آیا'}:
        return 'YES_NO'
    return 'UNKNOWN'


def semantic_contrast(original: str, alternate: str) -> str | None:
    """Conservative detectably *different* questions; None is NOT equivalence."""
    if _mode(alternate, 'HISTORICAL') != 'HISTORICAL':
        return 'HOLD_CURRENT_INTENT'
    i1, i2 = _intent(original), _intent(alternate)
    if i1 != 'UNKNOWN' and i2 != 'UNKNOWN' and i1 != i2:
        return 'HOLD_INTENT_CONTRAST'
    w1, w2 = _words(original), _words(alternate)
    t1 = {topic for topic, terms in _TOPIC_TERMS.items() if w1.intersection(terms)}
    t2 = {topic for topic, terms in _TOPIC_TERMS.items() if w2.intersection(terms)}
    if t1 and t2 and not t1.intersection(t2):
        return 'HOLD_TOPIC_CONTRAST'
    # Detect numeric answer-identity collisions (2+2 vs 2+3, date change).
    n1 = re.findall(r'[0-9۰-۹]+', original)
    n2 = re.findall(r'[0-9۰-۹]+', alternate)
    if n1 != n2:
        return 'HOLD_NUMERIC_SLOT_CONTRAST'
    neg1 = bool(w1 & {'no', 'not', 'never', 'نیست', 'نباید', 'نکرد', 'نه'})
    neg2 = bool(w2 & {'no', 'not', 'never', 'نیست', 'نباید', 'نکرد', 'نه'})
    if neg1 != neg2:
        return 'HOLD_POLARITY_CONTRAST'
    # PAWS-style danger: same high-overlap words, changed agent/patient order.
    # Conservative HOLD, not a proof that all reordered paraphrases differ.
    ordered1 = re.findall(r'[\w\u0600-\u06ff]+', original.casefold())
    ordered2 = re.findall(r'[\w\u0600-\u06ff]+', alternate.casefold())
    if len(ordered1) > 2 and Counter(ordered1) == Counter(ordered2) and ordered1 != ordered2:
        return 'HOLD_ORDER_SENSITIVE_PARAPHRASE'
    return None


def propose_candidate(original: str, alternate: str) -> dict:
    """For triage only. Candidate != approved identity or source truth."""
    conflict = semantic_contrast(original, alternate)
    if conflict:
        return {'disposition': conflict, 'equivalent': False}
    if normalized_question(original) == normalized_question(alternate):
        return {'disposition': 'EXACT_NORMALIZED_FORM', 'equivalent': None}
    return {'disposition': 'CANDIDATE_NEEDS_REVIEW', 'equivalent': None}


class EquivalenceReadView:
    """Immutable-in-process one-time answer/review snapshot with bounded lookups.

    Review events are supplied in memory by a test harness. They are NOT another
    answer store. No call to the RF01 writing API is made on the original path.
    """

    def __init__(self, journal_path: str | Path, review_events: Iterable[dict] = (),
                 *, pinned_floor: tuple[int, str] | None = None,
                 pinned_review_digests: Mapping[str, str] | None = None):
        self.journal_path = Path(journal_path)
        raw, self._stamp = _snapshot(self.journal_path)
        self.journal_digest = hashlib.sha256(raw).hexdigest()
        self.lookups = 0
        self.reassessments = 0
        self.history_reads = 0
        with tempfile.TemporaryDirectory(prefix='ario-rf05-') as temp:
            replica = Path(temp) / 'frozen.jsonl'
            replica.write_bytes(raw)  # ephemeral replay input; never the original path
            lab = AnswerRecallLab(replica)
            self.answers = copy.deepcopy(lab.answers)
            self.original_index: dict[tuple[str, str], set[str]] = {}
            for line in raw.splitlines(keepends=True):
                row = _parse_json_strict(line[:-1].decode('utf-8'))
                event = row['event']
                if event['kind'] == 'ANSWER':
                    key = (event['scope'], normalized_question(event['question']))
                    self.original_index.setdefault(key, set()).add(event['answer_id'])

        self.events = copy.deepcopy(list(review_events))
        self.review_head = GENESIS
        self.review_sequence = 0
        self._grants: dict[str, dict] = {}
        self._revoked: set[str] = set()
        self._query_bindings: dict[tuple[str, str], set[str]] = {}
        self._pinned_reviews = copy.deepcopy(dict(pinned_review_digests or {}))
        self._floor = pinned_floor
        self._has_unpinned_revocation = False
        self._parse_reviews()

    def _parse_reviews(self):
        if len(self.events) > MAX_REVIEW_EVENTS:
            raise ReviewHold('HOLD_REVIEW_EVENTS_LIMIT')
        try:
            raw_bytes = sum(len(canonical(event)) for event in self.events)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ReviewHold('HOLD_INVALID_REVIEW_FORMAT') from exc
        if raw_bytes > MAX_REVIEW_BYTES:
            raise ReviewHold('HOLD_REVIEW_BYTES_LIMIT')
        head = GENESIS
        for idx, e in enumerate(self.events, 1):
            if type(e) is not dict:
                raise ReviewHold('HOLD_REVIEW_RECORD')
            common = {'schema', 'seq', 'prev', 'kind', 'binding_id', 'basis_ref',
                      'reviewer_label', 'rationale', 'digest'}
            extra = {'scope', 'question', 'original_question', 'answer_id',
                     'answer_version', 'journal_sha256'} if e.get('kind') == 'GRANT' else {'revokes_digest'}
            if set(e) != common | extra:
                raise ReviewHold('HOLD_REVIEW_SCHEMA')
            if type(e['schema']) is not int or e['schema'] != 1 or type(e['seq']) is not int or e['seq'] != idx:
                raise ReviewHold('HOLD_REVIEW_SEQUENCE')
            if e['prev'] != head:
                raise ReviewHold('HOLD_REVIEW_CHAIN')
            if any(not _valid_str(e.get(k)) for k in ('binding_id', 'basis_ref', 'reviewer_label', 'rationale')):
                raise ReviewHold('HOLD_REVIEW_METADATA')
            content = {k: v for k, v in e.items() if k != 'digest'}
            if e['digest'] != digest(content):
                raise ReviewHold('HOLD_REVIEW_DIGEST')
            if e['kind'] == 'GRANT':
                if any(not _valid_str(e.get(k)) for k in ('scope', 'question', 'original_question', 'answer_id')):
                    raise ReviewHold('HOLD_GRANT_FIELDS')
                if type(e['answer_version']) is not int or e['answer_version'] < 1:
                    raise ReviewHold('HOLD_GRANT_VERSION')
                if e['journal_sha256'] != self.journal_digest:
                    raise ReviewHold('HOLD_GRANT_JOURNAL_MISMATCH')
                if e['binding_id'] in self._grants:
                    raise ReviewHold('HOLD_DUPLICATE_BINDING')
                answer = self.answers.get(e['answer_id'])
                if not answer or answer[0]['scope'] != e['scope']:
                    raise ReviewHold('HOLD_GRANT_ANSWER_OR_SCOPE')
                if (e['answer_id'] not in self.original_index.get(
                        (e['scope'], normalized_question(e['original_question'])), set())):
                    raise ReviewHold('HOLD_GRANT_CANONICAL_QUESTION')
                # Obvious semantic contrasts are refused even for a claimed
                # reviewed pair; this guard is incomplete by design.
                self._grants[e['binding_id']] = copy.deepcopy(e)
                key = (e['scope'], normalized_question(e['question']))
                self._query_bindings.setdefault(key, set()).add(e['binding_id'])
            elif e['kind'] == 'REVOKE':
                g = self._grants.get(e['binding_id'])
                if not g or e['binding_id'] in self._revoked or e['revokes_digest'] != g['digest']:
                    raise ReviewHold('HOLD_INVALID_REVOCATION')
                if self._pinned_reviews.get(e['basis_ref']) != e['digest']:
                    self._has_unpinned_revocation = True
                self._revoked.add(e['binding_id'])
            else:
                raise ReviewHold('HOLD_REVIEW_KIND')
            head = e['digest']
        self.review_head = head
        self.review_sequence = len(self.events)

    def _fresh(self) -> bool:
        try:
            return _file_stamp(self.journal_path) == self._stamp
        except ReviewHold:
            return False

    def recall(self, question: str, *, scope: str, mode: str = 'HISTORICAL') -> dict:
        self.lookups += 1
        if not _valid_str(question) or not _valid_str(scope):
            return {'disposition': 'HOLD_QUERY', 'answer': None}
        intent = _mode(question, mode)
        if intent == 'HOLD_QUERY_MODE':
            return {'disposition': intent, 'answer': None}
        if intent != 'HISTORICAL':
            return {'disposition': 'RECHECK_REQUIRED', 'answer': None,
                    'record_state': 'RECORDED', 'effective_assessment': 'NOT_EVALUATED'}
        if not self._fresh():
            return {'disposition': 'HOLD_SOURCE_CHANGED', 'answer': None}
        try:
            key = (scope, normalized_question(question))
        except RecallHold:
            return {'disposition': 'HOLD_QUERY', 'answer': None}
        original_ids = self.original_index.get(key, set())
        if len(original_ids) > 1:
            return {'disposition': 'UNKNOWN_AMBIGUOUS', 'answer': None}
        # Even if exact original question is known, an active conflicting reviewed
        # paraphrase to a different answer makes this question ambiguous.
        binding_ids = self._query_bindings.get(key, set())
        active = [self._grants[i] for i in binding_ids if i not in self._revoked]
        if len({e['answer_id'] for e in active} | original_ids) > 1:
            return {'disposition': 'UNKNOWN_AMBIGUOUS', 'answer': None}
        if original_ids:
            ident = next(iter(original_ids))
            return self._answer(ident, 'RECALLED_EXACT_ORIGINAL', reviewed=False)
        if not binding_ids:
            return {'disposition': 'UNKNOWN_MISSING', 'answer': None}
        if self._floor != (self.review_sequence, self.review_head):
            return {'disposition': 'HOLD_REVIEW_FLOOR_MISSING_OR_STALE', 'answer': None}
        if self._has_unpinned_revocation:
            return {'disposition': 'HOLD_UNPINNED_REVOCATION', 'answer': None}
        if not active:
            return {'disposition': 'HOLD_EQUIVALENCE_REVOKED', 'answer': None}
        for e in active:
            if self._pinned_reviews.get(e['basis_ref']) != e['digest']:
                return {'disposition': 'HOLD_UNPINNED_REVIEW', 'answer': None}
        if len(active) != 1:
            # Multiple active grants of same key intentionally HOLD even if same
            # answer ID; this requires explicit reconciliation, not auto-voting.
            return {'disposition': 'UNKNOWN_DUPLICATE_REVIEW', 'answer': None}
        selected = active[0]
        contrast = semantic_contrast(selected['original_question'], selected['question'])
        if contrast:
            return {'disposition': contrast, 'answer': None}
        ident = selected['answer_id']
        if selected['answer_version'] != len(self.answers[ident]):
            return {'disposition': 'HOLD_REVIEW_TARGET_VERSION_STALE', 'answer': None}
        result = self._answer(ident, 'RECALLED_LAB_REVIEWED_EQUIVALENCE', reviewed=True)
        result['equivalence'] = {
            'binding_id': selected['binding_id'], 'review_event_digest': selected['digest'],
            'basis_ref': selected['basis_ref'], 'reviewer_label': selected['reviewer_label'],
            'review_head': self.review_head,
            'review_authenticity': 'PIN_MATCH_IN_TEST_HARNESS_NOT_INDEPENDENTLY_ATTESTED',
            'semantic_scope': 'ONE_EXACT_REVIEWED_PAIR_ONLY',
        }
        return result

    def _answer(self, ident: str, disposition: str, *, reviewed: bool) -> dict:
        version = self.answers[ident][-1]
        return {
            'disposition': disposition, 'answer_id': ident, 'version': version['version'],
            'answer': version['answer'], 'source_ref': version['source_ref'],
            'record_state': 'RECORDED', 'effective_assessment': 'NOT_EVALUATED',
            'source_authenticity': 'LOCAL_JOURNAL_NOT_INDEPENDENTLY_ATTESTED',
            'equivalence_reviewed_in_lab': reviewed,
            'evidence_promotions': 0, 'recompute_calls': self.reassessments,
        }

    def history(self, answer_id: str) -> list[dict]:
        self.history_reads += 1
        return copy.deepcopy(self.answers.get(answer_id, []))


def review_event(previous: str, seq: int, *, kind: str, binding_id: str,
                 basis_ref: str, reviewer_label: str, rationale: str, **details) -> dict:
    """Helper constructs test fixtures; not an admission/authorization writer."""
    row = dict(schema=1, seq=seq, prev=previous, kind=kind, binding_id=binding_id,
               basis_ref=basis_ref, reviewer_label=reviewer_label, rationale=rationale,
               **details)
    return {**row, 'digest': digest(row)}