"""R18 research-only: read-only ledger inspection must honour R16.1 input budgets.

HOLD (over budget, unexamined) must stay distinguishable from CORRUPT (examined,
unparseable): HOLD reports is_clean=False, corrupt_line_no=None and a HOLD_*
diagnostic; CORRUPT keeps the pre-existing CORRUPT_JSON_OR_TRUNCATED_TAIL contract.
"""
import json
import subprocess
import sys
import tracemalloc
from pathlib import Path

import pytest

from core.memory_consolidation import (
    MAX_LEDGER_BYTES, MAX_LEDGER_LINE_BYTES, ConsolidationEngine, ConsolidationError)

MIB = 1_048_576
CLI_PATH = Path(__file__).resolve().parents[1] / "ario_memory_cli.py"


def _cli_inspect(path):
    proc = subprocess.run([sys.executable, "-B", str(CLI_PATH), "--inspect-ledger", "--ledger", str(path)],
                          cwd=CLI_PATH.parent, capture_output=True, text=True, check=False)
    return proc.returncode, json.loads(proc.stdout)


def _inspect_with_peak(path):
    tracemalloc.start()
    try:
        report = ConsolidationEngine.inspect_ledger_integrity(path)
        return report, tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_budgets_are_the_documented_values():
    assert (MAX_LEDGER_LINE_BYTES, MAX_LEDGER_BYTES) == (MIB, 64 * MIB)


def test_inspect_overlong_line_is_hold_not_clean_not_corrupt_and_bounded(tmp_path):
    p = tmp_path / "long.jsonl"
    p.write_bytes(b'{"concept":"c","assertion":"' + b"x" * (8 * MIB) + b'"}\n')
    report, peak = _inspect_with_peak(p)
    assert report.is_clean is False
    assert report.corrupt_line_no is None
    assert report.diagnostic == "HOLD_LEDGER_LINE_TOO_LARGE: line 1"
    assert peak < 4 * MIB, f"inspection allocated {peak / MIB:.1f} MiB"


def test_inspect_hold_reports_position_after_valid_prefix(tmp_path):
    p = tmp_path / "prefix.jsonl"
    p.write_bytes(b'{"a":1}\n{"a":2}\n' + b'{"x":"' + b"x" * (2 * MIB) + b'"}\n')
    r = ConsolidationEngine.inspect_ledger_integrity(p)
    assert (r.is_clean, r.valid_lines, r.corrupt_line_no) == (False, 2, None)
    assert r.diagnostic == "HOLD_LEDGER_LINE_TOO_LARGE: line 3"


def test_inspect_and_ingest_agree_on_oversized_ledger(tmp_path):
    p = tmp_path / "big.jsonl"
    with open(p, "wb") as f:
        f.truncate(MAX_LEDGER_BYTES + 1)   # never read past the stat check
    r = ConsolidationEngine.inspect_ledger_integrity(p)
    assert (r.is_clean, r.corrupt_line_no, r.diagnostic) == (False, None, "HOLD_LEDGER_BYTES_TOO_LARGE")
    with pytest.raises(ConsolidationError, match="HOLD_LEDGER_BYTES_TOO_LARGE"):
        ConsolidationEngine().ingest_ledger_file(p)


def test_line_budget_includes_terminator(tmp_path):
    body = b'{"concept":"c","assertion":"a"}'
    ok = tmp_path / "ok.jsonl"; ok.write_bytes(body + b" " * (MIB - len(body) - 1) + b"\n")
    crlf = tmp_path / "crlf.jsonl"; crlf.write_bytes(body + b" " * (MIB - len(body) - 2) + b"\r\n")
    over = tmp_path / "over.jsonl"; over.write_bytes(body + b" " * (MIB - len(body)) + b"\n")
    assert ConsolidationEngine.inspect_ledger_integrity(ok).is_clean is True
    assert ConsolidationEngine.inspect_ledger_integrity(crlf).is_clean is True
    assert ConsolidationEngine.inspect_ledger_integrity(over).diagnostic == "HOLD_LEDGER_LINE_TOO_LARGE: line 1"
    assert ConsolidationEngine().ingest_ledger_file(ok) == 1


def test_inspect_normal_ledger_still_clean(tmp_path):
    p = tmp_path / "n.jsonl"
    p.write_bytes("".join(json.dumps({"concept": "c", "assertion": str(i)}) + "\n"
                          for i in range(50)).encode())
    r = ConsolidationEngine.inspect_ledger_integrity(p)
    assert (r.is_clean, r.valid_lines) == (True, 50)


def test_inspect_corrupt_line_still_reported_as_corrupt(tmp_path):
    p = tmp_path / "c.jsonl"; p.write_bytes(b'{"a":1}\n{bad\n')
    r = ConsolidationEngine.inspect_ledger_integrity(p)
    assert (r.is_clean, r.corrupt_line_no) == (False, 2)
    assert r.diagnostic.startswith("CORRUPT_JSON_OR_TRUNCATED_TAIL")


# ---- CLI --inspect-ledger: exit code and JSON contract ----
def test_cli_inspect_clean_hold_corrupt_are_distinguishable(tmp_path):
    clean = tmp_path / "clean.jsonl"; clean.write_bytes(b'{"a":1}\n')
    corrupt = tmp_path / "corrupt.jsonl"; corrupt.write_bytes(b'{"a":1}\n{bad\n')
    held = tmp_path / "held.jsonl"; held.write_bytes(b'{"a":1}\n' + b'{"x":"' + b"x" * (2 * MIB) + b'"}\n')
    rc, data = _cli_inspect(clean)
    assert (rc, data["is_clean"], data["diagnostic"]) == (0, True, "CLEAN")
    rc, data = _cli_inspect(corrupt)
    assert (rc, data["is_clean"], data["corrupt_line_no"]) == (1, False, 2)
    assert data["diagnostic"].startswith("CORRUPT_JSON_OR_TRUNCATED_TAIL")
    rc, data = _cli_inspect(held)
    assert (rc, data["is_clean"], data["corrupt_line_no"], data["valid_lines"]) == (1, False, None, 1)
    assert data["diagnostic"] == "HOLD_LEDGER_LINE_TOO_LARGE: line 2"
    assert not data["diagnostic"].startswith("CORRUPT")


def test_cli_inspect_does_not_modify_ledger(tmp_path):
    held = tmp_path / "held.jsonl"
    original = b'{"a":1}\n' + b'{"x":"' + b"x" * (2 * MIB) + b'"}\n'
    held.write_bytes(original)
    _cli_inspect(held)
    assert held.read_bytes() == original
