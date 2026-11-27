"""Public audit CLI consumes existing #301 diagnostics without changing their authority."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from ario_cli import execute_review_diagnostic
from research.review_evidence import assess
from test_review_evidence import PIN, observation

CLI = Path(__file__).resolve().parents[1] / "ario_cli.py"


def files(root, first=None, last=None):
    if first is None:
        first = observation()
    if last is None:
        last = copy.deepcopy(first)
    paths = [root / name for name in ("pin.json", "first.json", "last.json")]
    for path, obj in zip(paths, (PIN, first, last)):
        path.write_bytes(json.dumps(obj).encode("utf-8"))
    return paths


def call(paths, *extra):
    return subprocess.run([sys.executable, "-B", str(CLI), "--review-evidence",
                           *map(str, paths), *extra], cwd=CLI.parent,
                          capture_output=True, text=True, check=False)


def test_cli_reuses_original_diagnostic_and_exact_input_digests(tmp_path):
    paths = files(tmp_path)
    raw = [path.read_bytes() for path in paths]
    result = call(paths)
    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert report["diagnostic"] == assess(PIN, observation(), observation())
    assert report["diagnostic"]["metadata"] == "CONSISTENT"
    assert report["diagnostic"]["gate"] == "HOLD"
    assert report["diagnostic"]["merge_authorized"] is False
    assert report["diagnostic"]["execution_attestation"] == "UNKNOWN"
    assert report["input_sha256"] == dict(zip(("pin", "first", "last"),
                                              (hashlib.sha256(data).hexdigest() for data in raw)))
    assert report["claim_truth"] == report["source_authentication"] == report["freshness"] == "UNKNOWN"
    assert report["independent_admission_authority"] == "NONE"
    assert [path.read_bytes() for path in paths] == raw


def test_changed_capture_is_unknown(tmp_path):
    first = observation()
    last = copy.deepcopy(first)
    last["reviews"]["nodes"][0]["body"] = "changed"
    report = execute_review_diagnostic(files(tmp_path, first, last))
    assert report["diagnostic"]["metadata"] == "UNKNOWN"
    assert report["diagnostic"]["merge_authorized"] is False
    assert report["input_sha256"]["first"] != report["input_sha256"]["last"]


@pytest.mark.parametrize("kind", ["duplicate", "oversize", "missing"])
def test_invalid_capture_remains_unknown(tmp_path, kind):
    paths = files(tmp_path)
    if kind == "duplicate":
        paths[1].write_bytes(b'{"pr":{},"pr":{}}')
    elif kind == "oversize":
        with paths[1].open("wb") as stream:
            stream.truncate(4 * 1024 * 1024 + 1)
    else:
        paths[1].unlink()
    report = execute_review_diagnostic(paths)
    assert report["diagnostic"]["metadata"] == "UNKNOWN"
    assert report["diagnostic"]["gate"] == "HOLD"
    assert report["diagnostic"]["merge_authorized"] is False


def test_review_diagnostic_cannot_write_m0_ledger(tmp_path):
    paths = files(tmp_path)
    ledger = tmp_path / "events.jsonl"
    result = call(paths, "--ledger", str(ledger))
    assert result.returncode == 2
    assert not ledger.exists()
    assert not result.stdout
