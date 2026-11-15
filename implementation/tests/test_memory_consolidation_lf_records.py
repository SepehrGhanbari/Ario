"""Review-only JSONL line framing regression for Ario memory Draft #229/#230.

Covers CodeRabbit review: bytes.splitlines() incorrectly treated lone CR as a
JSONL record terminator. Source bytes are synthetic, with no user ledger read.
"""

import hashlib
import io

import pytest

from core.memory_consolidation import ConsolidationEngine, ConsolidationError


class _ReadOnlyPath:
    def __init__(self, raw: bytes) -> None:
        self._raw = raw

    def exists(self) -> bool:
        return True

    def open(self, mode: str):
        assert mode == "rb"
        return io.BytesIO(self._raw)


def _ingest(raw: bytes) -> ConsolidationEngine:
    engine = ConsolidationEngine()
    engine.ingest_ledger_file(_ReadOnlyPath(raw))
    return engine


def test_lone_cr_does_not_split_jsonl_records_or_mutate_memory():
    # No LF between the two JSON objects; this must NOT produce two nodes.
    raw = b'{"concept":"x","assertion":"A"}\r{"concept":"x","assertion":"B"}\n'
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError, match="corrupt ledger JSON"):
        engine.ingest_ledger_file(_ReadOnlyPath(raw))
    assert engine.nodes == {}
    assert engine.known_ledger_hashes == set()


def test_two_valid_crlf_records_preserve_byte_exact_digest():
    a = b'{"concept":"x","assertion":"A"}\r\n'
    b = b'{"concept":"x","assertion":"B"}\r\n'
    engine = _ingest(a + b)
    nodes = engine.nodes
    assert len(nodes) == 2
    assert {h for node in nodes.values() for h in node.source_event_hashes} == {
        hashlib.sha256(a).hexdigest(),
        hashlib.sha256(b).hexdigest(),
    }


def test_single_jsonl_record_with_valid_cr_whitespace_is_not_split():
    # JSON allows CR as whitespace, although LF alone terminates a JSONL record.
    raw = b'{"concept":"x",\r "assertion":"A"}\n'
    engine = _ingest(raw)
    node = next(iter(engine.nodes.values()))
    assert len(engine.nodes) == 1
    assert node.assertion == "A"
    assert node.source_event_hashes == (hashlib.sha256(raw).hexdigest(),)


def test_mixed_lf_crlf_records_are_valid_and_stable():
    a = b'{"concept":"x","assertion":"A"}\n'
    b = b'{"concept":"y","assertion":"B"}\r\n'
    engine = _ingest(a + b)
    assert len(engine.known_ledger_hashes) == 2
    assert len(engine.nodes) == 2


def test_unterminated_final_fragment_is_still_rejected_atomically():
    a = b'{"concept":"x","assertion":"A"}\n'
    b = b'{"concept":"x","assertion":"B"}'
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError, match="missing final LF"):
        engine.ingest_ledger_file(_ReadOnlyPath(a + b))
    assert engine.nodes == {}
    assert engine.known_ledger_hashes == set()


def test_vertical_tab_does_not_split_jsonl_into_valid_records():
    raw = b'{"concept":"x","assertion":"A"}\v{"concept":"x","assertion":"B"}\n'
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError, match="corrupt ledger JSON"):
        engine.ingest_ledger_file(_ReadOnlyPath(raw))
    assert engine.nodes == {}
