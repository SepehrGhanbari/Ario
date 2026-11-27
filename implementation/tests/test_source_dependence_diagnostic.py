"""Preserve v0.1 negative controls and exercise report-only reference diagnostic."""
import hashlib
import json
from itertools import combinations
from pathlib import Path
import subprocess
import sys

import pytest

from source_dependence_diagnostic import assess, inspect_file
from undeclared_copy_dependence_probe import DEFAULT_WORLDS, WorldSpec, generate_world

CLI = Path(__file__).resolve().parents[1] / "ario_cli.py"
FLAG = "SHARED_DISCORDANCE_SIGNAL_NOT_EVIDENCE"


def request(world, reference=None):
    return {"item_ids": [str(i) for i in range(len(world.truth))],
            "reference": {"source_id": "supplied-reference",
                          "values": list(world.truth if reference is None else reference)},
            "sources": {key: list(values) for key, values in world.claims.items()}}


@pytest.mark.parametrize("spec,expected_tp,expected_total", [
    (DEFAULT_WORLDS[0], 120, 120),
    (DEFAULT_WORLDS[1], 0, 0),
    (DEFAULT_WORLDS[2], 0, 0),
    (DEFAULT_WORLDS[3], 91, 120),
    (WorldSpec("copier_minority", n_copiers=2, n_independent=7), 60, 60),
])
def test_fixed_synthetic_reference_control(spec, expected_tp, expected_total):
    tp = total = fp = 0
    for seed in range(20):
        world = generate_world(spec, seed)
        data = request(world)
        report = assess(data)
        flags = {tuple(p["sources"]) for p in report["pair_results"] if p["signal"] == FLAG}
        truth_pairs = {p for cluster in world.true_clusters for p in combinations(sorted(cluster), 2)}
        tp += len(flags & truth_pairs)
        total += len(truth_pairs)
        fp += len(flags - truth_pairs)
        assert report["independence"] == report["dependence"] == "UNKNOWN"
        assert not report["automatic_downgrade"]
    assert (tp, total, fp) == (expected_tp, expected_total, 0)


def test_high_agreement_alone_is_not_signal():
    data = {"item_ids": [str(i) for i in range(20)],
            "reference": {"source_id": "r", "values": ["same"] * 20},
            "sources": {"a": ["same"] * 20, "b": ["same"] * 20}}
    pair = assess(data)["pair_results"][0]
    assert pair["agreement"] == 1
    assert pair["signal"] == "INSUFFICIENT_JOINT_DISCORDANCE"


def test_wrong_reference_can_flag_identical_correct_sources_without_authority():
    data = {"item_ids": [str(i) for i in range(20)],
            "reference": {"source_id": "r", "values": ["wrong"] * 20},
            "sources": {"a": ["correct"] * 20, "b": ["correct"] * 20}}
    report = assess(data)
    assert report["pair_results"][0]["signal"] == FLAG
    assert report["reference_authentication"] == report["dependence"] == "UNKNOWN"
    assert not report["automatic_downgrade"]


@pytest.mark.parametrize("kind", ["short", "duplicate_item", "reference_alias", "oversize_value"])
def test_invalid_alignment_refused(kind):
    data = request(generate_world(DEFAULT_WORLDS[0], 0))
    if kind == "short":
        data["sources"]["O"].pop()
    elif kind == "duplicate_item":
        data["item_ids"][1] = data["item_ids"][0]
    elif kind == "reference_alias":
        data["reference"]["source_id"] = "O"
    else:
        data["sources"]["O"][0] = "x" * 257
    result = assess(data)
    assert result["status"] == "UNKNOWN" and not result["pair_results"]


def test_cli_reports_exact_bytes_and_no_mutation(tmp_path):
    path = tmp_path / "request.json"
    raw = json.dumps(request(generate_world(DEFAULT_WORLDS[0], 0))).encode()
    path.write_bytes(raw)
    command = [sys.executable, "-B", str(CLI), "--source-dependence", str(path)]
    child = subprocess.run(command, cwd=CLI.parent, capture_output=True, text=True)
    assert child.returncode == 1, child.stderr
    result = json.loads(child.stdout)
    assert result == inspect_file(path)
    assert result["input_sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["status"] == "DIAGNOSTIC"
    assert path.read_bytes() == raw
    ledger = tmp_path / "output.jsonl"
    rejected = subprocess.run(command + ["--ledger", str(ledger)], cwd=CLI.parent,
                              capture_output=True, text=True)
    assert rejected.returncode == 2 and not ledger.exists()


def test_duplicate_json_is_unknown(tmp_path):
    path = tmp_path / "request.json"
    path.write_bytes(b'{"sources":{},"sources":{}}')
    assert inspect_file(path)["status"] == "UNKNOWN"
