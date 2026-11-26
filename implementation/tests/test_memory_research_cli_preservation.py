"""Research CLI must never replace an input ledger or previous report."""
import json
from ario_memory_cli import main

def test_output_cannot_overwrite_ledger(tmp_path, capsys):
    ledger = tmp_path / "ledger.jsonl"
    raw = b'{"assertion":"retained"}\n'
    ledger.write_bytes(raw)
    assert main(["--memory-conflicts", "--ledger", str(ledger), "--output", str(ledger)]) == 2
    assert json.loads(capsys.readouterr().err)["error"] == "HOLD_OUTPUT_EXISTS"
    assert ledger.read_bytes() == raw
