"""R21.1 test-first adversarial proposals for Ario PR #316 at 50e6bd9.

RESEARCH_ONLY. These are *proposed* regressions, not claims of full-suite
execution or merge readiness. Tests should be copied only to a disposable tree
and reviewed before adoption. R17/atomic-flush remain separately held.
"""

import builtins
import json
import os
import stat
import sys
from pathlib import Path

import pytest
import core.memory_consolidation as mc
from core.memory_consolidation import ConsolidationEngine as CE, ConsolidationError


def test_append_at_eof_must_not_commit_clean_prefix(tmp_path, monkeypatch):
    """Deterministically append corrupt tail on the first observed EOF.

    R18 and the supplied R21 patch both check only after_size < initial_size
    for ingestion; they can admit the prefix while an appended invalid tail
    remains on the file. This test describes the stricter desired contract.
    """
    ledger = tmp_path / 'concurrent.jsonl'
    ledger.write_bytes(b'{"concept":"c","assertion":"valid"}\n')
    real_open = builtins.open

    class AppendAtEOF:
        def __init__(self, inner):
            self.inner = inner
            self.appended = False
        def __enter__(self):
            self.inner.__enter__()
            return self
        def __exit__(self, *args):
            return self.inner.__exit__(*args)
        def __getattr__(self, name):
            return getattr(self.inner, name)
        def readline(self, *args, **kwargs):
            line = self.inner.readline(*args, **kwargs)
            if not line and not self.appended:
                self.appended = True
                with real_open(ledger, 'ab') as w:
                    w.write(b'{not-json-tail\n')
            return line

    def guarded_open(path, mode='r', *args, **kwargs):
        f = real_open(path, mode, *args, **kwargs)
        if Path(path) == ledger and mode == 'rb':
            return AppendAtEOF(f)
        return f

    monkeypatch.setattr(mc, 'open', guarded_open, raising=False)
    engine = CE()
    with pytest.raises(ConsolidationError, match=r'HOLD_LEDGER_CHANGED_DURING_INGESTION|HOLD_LEDGER_CHANGED_DURING_READ'):
        engine.ingest_ledger_file(ledger)
    assert engine.nodes == {}, 'a changed ledger must not admit its prefix'
    assert engine.known_ledger_hashes == set()
    assert ledger.read_bytes().endswith(b'{not-json-tail\n')


@pytest.mark.parametrize('payload', [b'42\n', b'null\n', b'[1,2]\n', b'"text"\n'])
def test_inspector_must_not_call_non_object_json_clean(tmp_path, payload):
    """A parseable JSON primitive/array is not an admissible event object."""
    ledger = tmp_path / 'primitive.jsonl'
    ledger.write_bytes(payload)
    report = CE.inspect_ledger_integrity(ledger)
    assert report.is_clean is False
    assert report.corrupt_line_no is None
    assert report.diagnostic.startswith('HOLD_EVENT_MUST_BE_JSON_OBJECT')
    with pytest.raises(ConsolidationError, match='HOLD_EVENT_MUST_BE_JSON_OBJECT'):
        CE().ingest_ledger_file(ledger)


def test_nonregular_zero_sized_stream_is_never_empty_clean(tmp_path):
    """On POSIX an unopened FIFO has st_size=0, but is not an empty file."""
    if not hasattr(os, 'mkfifo'):
        pytest.skip('FIFO not supported on this platform')
    path = tmp_path / 'fifo.jsonl'
    os.mkfifo(path)
    assert stat.S_ISFIFO(path.stat().st_mode)
    report = CE.inspect_ledger_integrity(path)
    assert report.is_clean is False
    assert report.diagnostic.startswith('HOLD_LEDGER_NOT_REGULAR_FILE')
    # Important: never open the FIFO; no writer exists and open() would block.


def test_legacy_snapshot_with_missing_replay_index_does_not_invent_identity():
    """Migration must HOLD where replays might otherwise count as new evidence."""
    engine = CE()
    engine.ingest_event_stream([('a' * 64, {'concept': 'c', 'assertion': 'recorded'})])
    state = engine.__getstate__()
    state.pop('_event_payload_digests', None)
    state.pop('_event_stable_digests', None)
    with pytest.raises(ConsolidationError, match='HOLD_LEGACY_SNAPSHOT_REPLAY_INDEX_MISSING'):
        CE.__new__(CE).__setstate__(state)


def test_pristine_legacy_snapshot_can_restore_empty_replay_indexes():
    """Only fully empty legacy state can safely gain blank digest indexes."""
    state = CE().__getstate__()
    state.pop('_event_payload_digests')
    state.pop('_event_stable_digests')
    restored = CE.__new__(CE)
    restored.__setstate__(state)
    assert restored.ingest_event_stream([('a' * 64, {'concept': 'c', 'assertion': 'first'})]) == 1


@pytest.mark.parametrize('bad', [-1, '5', True, sys.maxsize])
def test_invalid_or_unrepresentable_batch_ceiling_is_domain_hold(bad):
    """Constructor or later mutation must never leak islice ValueError/TypeError."""
    try:
        engine = CE(max_batch_events=bad)
    except ConsolidationError:
        return
    with pytest.raises(ConsolidationError, match='HOLD_INVALID_MAX_BATCH_EVENTS|HOLD_BATCH_LIMIT_TOO_LARGE'):
        engine.ingest_event_stream([])


@pytest.mark.parametrize('bad', [-5, '2', True, sys.maxsize])
def test_mutated_batch_limit_is_validated_at_use(bad):
    engine = CE(max_batch_events=2)
    try:
        engine.max_batch_events = bad
    except (ConsolidationError, ValueError, AttributeError):
        return  # read-only/validated setter also satisfies this contract
    with pytest.raises(ConsolidationError, match='HOLD_INVALID_MAX_BATCH_EVENTS|HOLD_BATCH_LIMIT_TOO_LARGE'):
        engine.ingest_event_stream([])

@pytest.mark.parametrize('payload', [
    b'{"concept":"c","assertion":"a","x":1e9999}\n',
    b'{"concept":"c","assertion":"a","x":NaN}\n',
    b'{"concept":"c","assertion":"a","x":Infinity}\n',
])
def test_inspector_never_calls_nonfinite_uningestable_event_clean(tmp_path, payload):
    """JSON decode success is weaker than the actual ingestion predicate.

    CPython json.loads accepts overflowing floats and non-standard NaN/
    Infinity; downstream json.dumps(..., allow_nan=False) rejects them.
    Exact non-object/non-finite classification must be agreed before code change.
    """
    ledger = tmp_path / 'nonfinite.jsonl'
    ledger.write_bytes(payload)
    report = CE.inspect_ledger_integrity(ledger)
    assert report.is_clean is False
    assert report.corrupt_line_no is None or report.diagnostic.startswith('CORRUPT_')
    with pytest.raises(ConsolidationError):
        CE().ingest_ledger_file(ledger)
