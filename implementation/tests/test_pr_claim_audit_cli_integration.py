"""Public audit CLI reuses #290's offline comparator; no authority or writes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

import pr_claim_audit_log_parser_v0_8 as v08
from ario_cli import execute_pr_claim_diagnostic
from test_pr_claim_audit_log_parser_v0_7 import claim_text, evidence, make_log, SUMMARY

CLI = Path(__file__).resolve().parents[1] / "ario_cli.py"


def files(root, body=None, snapshot=None):
    bp, ep = root / "pr.txt", root / "snapshot.json"
    bp.write_bytes((claim_text() if body is None else body).encode("utf-8"))
    ep.write_bytes(json.dumps(evidence() if snapshot is None else snapshot).encode("utf-8"))
    return bp, ep


def call(paths, *extra):
    return subprocess.run([sys.executable, "-B", str(CLI), "--pr-claim",
                           *map(str, paths), *extra], cwd=CLI.parent,
                          capture_output=True, text=True, check=False)


def test_main_cli_reuses_comparator_and_reports_exact_input_hashes(tmp_path):
    paths = files(tmp_path)
    before = [p.read_bytes() for p in paths]
    child = call(paths)
    assert child.returncode == 1, child.stderr
    report = json.loads(child.stdout)
    assert report["diagnostic"] == v08.assess(claim_text(), evidence(), extended_counts=True)
    assert report["diagnostic"]["claim_correspondence"] == "MATCH"
    assert report["diagnostic"]["status"] == "UNKNOWN"
    assert report["diagnostic"]["execution_attestation"] == "NOT_ESTABLISHED"
    assert report["merge_authorized"] is False
    assert report["input_sha256"] == dict(zip(("pr_body", "snapshot"),
                                             (hashlib.sha256(raw).hexdigest() for raw in before)))
    assert [p.read_bytes() for p in paths] == before


def test_current_ci_summary_preserves_unclaimed_expected_failures():
    # Exact summary observed in job 140490808924, #444; excerpt only.
    log = make_log(summary="2026-11-27T11:57:53.7773433Z 2320 passed, 7 skipped, 2 xfailed, 2 warnings, 379 subtests passed in 27.07s")
    ev = evidence(log)
    body = claim_text(passed=2320).replace('"skipped": 2', '"skipped": 7').replace('"subtests_passed": 124', '"subtests_passed": 379')
    legacy = v08.assess(body, ev)
    assert legacy["claim_correspondence"] == "UNKNOWN"
    result = v08.assess(body, ev, extended_counts=True)
    assert result["claim_correspondence"] == "MATCH"
    assert result["correspondence_scope"] == "DECLARED_V01_FIELDS_ONLY"
    assert result["observed"]["passed"] == 2320
    assert result["unclaimed_counts"] == {"xfailed": 2, "xpassed": 0, "warnings": 2}
    assert result["status"] == "UNKNOWN"


@pytest.mark.parametrize("summary", [
    SUMMARY.replace("2 warnings", "2 xfailed, 1 xfailed"),
    SUMMARY.replace("2 warnings", "2 unrecognized"),
])
def test_extended_unknown_or_duplicate_counts_fail_closed(summary):
    result = v08.assess(claim_text(), evidence(make_log(summary)), extended_counts=True)
    assert result["claim_correspondence"] == "UNKNOWN"
    assert result["unclaimed_counts"] is None


def test_extended_reports_xpass_without_promoting_it():
    result = v08.assess(claim_text(passed=9999),
                        evidence(make_log(SUMMARY.replace("2 warnings", "1 xpassed"))),
                        extended_counts=True)
    assert result["claim_correspondence"] == "MISMATCH"
    assert result["differences"] == ["passed"]
    assert result["unclaimed_counts"]["xpassed"] == 1
    assert result["status"] == "UNKNOWN"


@pytest.mark.parametrize("kind", ["duplicate", "missing", "oversize", "bad_hash"])
def test_invalid_snapshot_stays_unknown(tmp_path, kind):
    paths = files(tmp_path)
    if kind == "duplicate":
        paths[1].write_bytes(b'{"run":{},"run":{}}')
    elif kind == "missing":
        paths[1].unlink()
    elif kind == "oversize":
        with paths[1].open("wb") as stream:
            stream.truncate(2 * 1024 * 1024 + 1)
    else:
        ev = evidence()
        ev["job_log_sha256"] = "0"*64
        paths[1].write_text(json.dumps(ev), encoding="utf-8")
    report = execute_pr_claim_diagnostic(*paths)
    assert report["diagnostic"]["claim_correspondence"] == "UNKNOWN"
    assert report["merge_authorized"] is False


def test_pr_claim_diagnostic_cannot_write_m0_ledger(tmp_path):
    paths = files(tmp_path)
    ledger = tmp_path / "output.jsonl"
    result = call(paths, "--ledger", str(ledger))
    assert result.returncode == 2
    assert not ledger.exists()
