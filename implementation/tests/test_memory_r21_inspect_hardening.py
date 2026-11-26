"""R21 RED tests against PR #316 head 50e6bd9 (F1, F2, F4, F5, F6). Research-only.
RED on 50e6bd9; GREEN with r21_inspect_hardening.patch."""
import builtins, json, os, subprocess, sys
from pathlib import Path
import pytest
import core.memory_consolidation as mc
from core.memory_consolidation import ConsolidationEngine as CE, ConsolidationError

ROOT = Path(__file__).resolve().parents[1]
LINES = b"".join(json.dumps({"concept": "c", "assertion": str(i)}).encode() + b"\n" for i in range(100))

def _swap_on_open(monkeypatch, p, new_bytes):
    real = builtins.open
    def swap(path, mode="r", *a, **k):
        if str(path) == str(p) and mode == "rb":
            with real(p, "r+b") as w:
                w.truncate(0); w.write(new_bytes)
        return real(path, mode, *a, **k)
    monkeypatch.setattr(mc, "open", swap, raising=False)

# F1: file changed between stat and read must not be CLEAN
def test_f1_truncated_after_stat_is_not_clean(tmp_path, monkeypatch):
    p = tmp_path / "l.jsonl"; p.write_bytes(LINES)
    _swap_on_open(monkeypatch, p, b'{"concept":"c","assertion":"replaced"}\n')
    r = CE.inspect_ledger_integrity(p)
    assert r.is_clean is False and r.corrupt_line_no is None
    assert r.diagnostic.startswith("HOLD_LEDGER_CHANGED_DURING_INSPECTION")

# F2: valid JSON beyond interpreter limits is HOLD, never CORRUPT
@pytest.mark.parametrize("body", [b"[" * 200000 + b"]" * 200000,
                                  b'{"concept":"c","assertion":"a","n":' + b"9" * 5000 + b"}"],
                         ids=["depth200000", "int5000digits"])
def test_f2_valid_but_unsupported_json_is_hold_not_corrupt(tmp_path, body):
    p = tmp_path / "l.jsonl"; p.write_bytes(body + b"\n")
    r = CE.inspect_ledger_integrity(p)
    assert r.is_clean is False and r.corrupt_line_no is None
    assert r.diagnostic.startswith("HOLD_LEDGER_JSON_UNSUPPORTED")
    with pytest.raises(ConsolidationError, match="HOLD_LEDGER_JSON_UNSUPPORTED"):
        CE().ingest_ledger_file(p)
    assert p.read_bytes() == body + b"\n"

def test_f2_real_corruption_still_corrupt(tmp_path):
    p = tmp_path / "l.jsonl"; p.write_bytes(b'{"a":1}\n{"a":\n')
    r = CE.inspect_ledger_integrity(p)
    assert r.corrupt_line_no == 2 and r.diagnostic.startswith("CORRUPT_JSON_OR_TRUNCATED_TAIL")

# F4: unreadable path gives JSON HOLD, not a traceback
def test_f4_inspect_directory_returns_json_hold(tmp_path):
    d = tmp_path / "dir.jsonl"; d.mkdir()
    pr = subprocess.run([sys.executable, "-B", "ario_memory_cli.py", "--inspect-ledger", "--ledger", str(d)],
                        cwd=ROOT, capture_output=True, text=True)
    assert pr.returncode == 1 and "Traceback" not in pr.stderr
    out = json.loads(pr.stdout)
    assert out["is_clean"] is False and out["corrupt_line_no"] is None
    assert out["diagnostic"].startswith("HOLD_LEDGER_UNREADABLE")

# F5: snapshot max_batch_events validated like the constructor
@pytest.mark.parametrize("bad", ["4096", 0, -5, True, 1.5, None])
def test_f5_snapshot_invalid_max_batch_events_rejected(bad):
    st = CE().__getstate__(); st["max_batch_events"] = bad
    with pytest.raises(ConsolidationError, match="HOLD_INVALID_SNAPSHOT_MAX_BATCH_EVENTS"):
        CE.__new__(CE).__setstate__(st)

def test_f5_legacy_snapshot_without_field_still_defaults():
    st = CE().__getstate__(); st.pop("max_batch_events")
    e = CE.__new__(CE); e.__setstate__(st)
    assert e.max_batch_events == 4096 and e.ingest_event_stream([("a" * 64, {"concept": "c", "assertion": "a"})]) == 1

# F6: CLI accepts only ASCII decimal digits
@pytest.mark.parametrize("v", [" 5000", "+5000", "5_000", "\u0665\u0660\u0660\u0660", "5000 "],
                         ids=["lead_space", "plus", "underscore", "arabic_indic", "trail_space"])
def test_f6_cli_rejects_non_ascii_or_decorated_integers(tmp_path, v):
    p = tmp_path / "l.jsonl"; p.write_bytes(b'{"concept":"c","assertion":"a"}\n')
    pr = subprocess.run([sys.executable, "-B", "ario_memory_cli.py", "--memory-conflicts", "--ledger", str(p),
                         "--memory-max-events", v], cwd=ROOT, capture_output=True, text=True)
    assert pr.returncode == 2

def test_f6_cli_plain_integer_still_works(tmp_path):
    p = tmp_path / "l.jsonl"; p.write_bytes(b'{"concept":"c","assertion":"a"}\n')
    pr = subprocess.run([sys.executable, "-B", "ario_memory_cli.py", "--memory-conflicts", "--ledger", str(p),
                         "--memory-max-events", "5000", "--format", "json"], cwd=ROOT, capture_output=True, text=True)
    assert pr.returncode == 0

def test_clean_ledger_still_clean(tmp_path):
    p = tmp_path / "l.jsonl"; p.write_bytes(LINES)
    r = CE.inspect_ledger_integrity(p)
    assert r.is_clean and r.valid_lines == 100 and r.diagnostic == "CLEAN"
