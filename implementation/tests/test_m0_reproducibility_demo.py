"""Real-engine outcomes, input replay, and deterministic demo output."""

import copy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from ario_cli import execute_request
import m0_reproducibility_demo as demo


def pytest_make_parametrize_id(val, argname):
    """Optional -p plugin: bound display IDs, preserving full parameter values.

    An existing W4-B test supplies 65,537 bytes. Its default pytest ID exceeds
    Windows' environment-variable limit before the test can execute.
    """
    if isinstance(val, bytes) and len(val) > 256:
        return f"{argname}-bytes-{len(val)}-sha256-{sha256(val).hexdigest()}"
    return None


def test_parameter_display_ids_are_bounded_and_do_not_change_payload():
    payload = b"x" * 65537
    before = payload
    display_id = pytest_make_parametrize_id(payload, "bad_data")
    assert len(display_id) < 128
    assert str(len(payload)) in display_id and sha256(payload).hexdigest() in display_id
    assert pytest_make_parametrize_id(b"y" * 65537, "bad_data") != display_id
    assert pytest_make_parametrize_id(b"small", "bad_data") is None
    assert payload == before


@pytest.mark.parametrize(
    "name,verdict,violations,disposition,presence",
    [
        ("empty_input", "UNKNOWN", [], None, None),
        ("record_presence", "PASS", [], "RECORD_DESCRIPTION_ONLY", "MATCH"),
        ("self_support", "FAIL", ["EVIDENCE_INADMISSIBLE"],
         "KNOWN_INADMISSIBLE", "NOT_EVALUATED"),
    ],
)
def test_real_engine_outcomes(name, verdict, violations, disposition, presence):
    case = next(case for case in demo.run_demo()["cases"] if case["case"] == name)
    result, findings = case["result"], case["ancestry_findings"]
    assert result["verdict"] == verdict
    assert result["violations"] == violations
    assert result["inspector_version"] == "M0-1.2"
    assert result["rule_versions"] == ["M0-1.0"]
    assert findings["mandatory_guards"] == ["M0-REF-GUARD-1.0", "M0-EAG-0.1"]
    assert findings["report_complete"] is True
    assert findings["claim_truth"] == findings["entity_continuity"] == "UNKNOWN"
    assert findings["independent_admission_authority"] == "NONE"
    if disposition is None:
        assert findings["assessments"] == []
    else:
        row, = findings["assessments"]
        assert row["use_disposition"] == disposition
        assert row["record_presence"] == presence
        assert row["source_authentication"] == "UNKNOWN"
        assert row["ancestry"] == "TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT"


def test_inputs_replay_without_mutation_or_claim_promotion():
    # JSON round-trip exercises the published input format, not Python-only types.
    requests = json.loads(json.dumps(demo.build_requests()))
    before = copy.deepcopy(requests)
    observed = {case["case"]: case["result"] for case in demo.run_demo()["cases"]}
    assert set(requests) == set(observed) == {
        "empty_input", "record_presence", "self_support"
    }
    for name, request in requests.items():
        assert execute_request(request) == observed[name]
        for claim in request["artifacts"]["claims"]:
            assert claim["status"] == "UNKNOWN"
    assert requests == before
    requests["record_presence"]["artifacts"]["claims"].clear()
    assert demo.build_requests() == before


def test_presence_control_rejects_missing_target():
    request = demo.build_requests()["record_presence"]
    request["artifacts"]["claims"] = []
    result = execute_request(request)
    assert result["verdict"] == "FAIL"
    assert "UNKNOWN" in result["violations"]


def test_demo_preserves_runtime_verdicts(monkeypatch):
    # Fault control: a returned result must never be replaced with an expected PASS.
    actual_execute = demo.execute_request
    calls = []

    def altered_result(request):
        calls.append(request["audit_id"])
        result = actual_execute(request)
        result["verdict"] = "UNKNOWN"
        result["violations"] = ["SYNTHETIC_TEST_FAULT"]
        return result

    monkeypatch.setattr(demo, "execute_request", altered_result)
    output = demo.run_demo()
    assert len(calls) == 3
    for case in output["cases"]:
        assert case["result"]["verdict"] == "UNKNOWN"
        assert case["result"]["violations"] == ["SYNTHETIC_TEST_FAULT"]


def test_cli_is_reproducible_and_inputs_replay_via_existing_cli(tmp_path):
    script = Path(demo.__file__).resolve()

    def run(path, *args, seed="1"):
        env = os.environ.copy()
        env.update(PYTHONHASHSEED=seed, PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(
            [sys.executable, "-B", str(path), *args],
            cwd=tmp_path, env=env, capture_output=True, check=True, timeout=30,
        )

    first = run(script)
    second = run(script, seed="8675309")
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout
    assert json.loads(first.stdout) == demo.run_demo()
    inputs = run(script, "--inputs")
    assert inputs.stderr == b""
    assert json.loads(inputs.stdout) == json.loads(json.dumps(demo.build_requests()))
    for case in json.loads(first.stdout)["cases"]:
        request_path = tmp_path / f"{case['case']}.json"
        request_path.write_text(
            json.dumps(json.loads(inputs.stdout)[case["case"]]), encoding="utf-8"
        )
        replay = run(script.with_name("ario_cli.py"), "--input", str(request_path))
        assert replay.stderr == b""
        assert json.loads(replay.stdout) == case["result"]
