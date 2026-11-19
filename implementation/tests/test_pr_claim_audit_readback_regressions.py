"""Cross-version regressions using offline snapshots and in-memory HTTP responses."""
import http.client
import io
import json
from unittest.mock import Mock, patch

import pytest

import pr_claim_audit as v01
import pr_claim_audit_origin_v0_2 as v02
import pr_claim_audit_github_v0_3 as v03
import pr_claim_audit_state_v0_5 as v05
import pr_claim_audit_readback_v0_6 as v06
import pr_claim_audit_log_parser_v0_7 as v07
import pr_claim_audit_log_parser_v0_8 as v08
import provenance_r2_d10_provider_readback as d10
import test_pr_claim_audit as legacy
import test_pr_claim_audit_log_parser_v0_7 as parser
from test_pr_claim_audit_github_v0_3 import FakeGitHub


@pytest.mark.parametrize("module", [v07, v08])
@pytest.mark.parametrize(("step_lines", "expected"), [
    ([parser.CMD, parser.SUMMARY], "MATCH"),
    ([parser.SUMMARY, parser.CMD], "UNKNOWN"),
    ([parser.CMD, "##[group]Run python -m unittest", parser.SUMMARY], "UNKNOWN"),
    ([parser.CMD, "Post job cleanup.", parser.SUMMARY], "UNKNOWN"),
])
def test_summary_belongs_to_step(module, step_lines, expected):
    log = "\n".join([parser.SETUP, *step_lines])
    out = module.assess(parser.claim_text(), parser.evidence(log))
    assert out["claim_correspondence"] == expected
    assert out["status"] == "UNKNOWN"


@pytest.mark.parametrize("module", [v03, v05, v06])
@pytest.mark.parametrize(("field", "value"), [("id", None), ("id", 17), ("number", 250)])
def test_middle_pr_sample_agrees(module, field, value):
    class ChangedMiddle(FakeGitHub):
        def get_json(self, url):
            data = super().get_json(url)
            if url.endswith("/pulls/249") and self.call_count_pr == 2:
                if value is None:
                    del data[field]
                else:
                    data[field] = value
            return data

    out = module.assess_github_pr("SepehrGhanbari", "Ario", 249, reader=ChangedMiddle())
    assert out["correspondence_status"] == "UNKNOWN"
    assert out.get("state_consistency") != "STABLE_AT_SAMPLED_READS"
    assert out["binding"] is None


def test_reader_init_failure_preserves_zero_sample_report():
    with patch.object(v06, "PublicGitHubReader", side_effect=OSError("TLS setup unavailable")):
        out = v06.assess_github_pr("SepehrGhanbari", "Ario", 249)
    assert out["status"] == out["claim_correspondence"] == "UNKNOWN"
    assert out["execution_attestation"] == "NOT_ESTABLISHED"
    assert out["pr_read_samples"] == [] and out["pr_read_count"] == 0
    assert out["final_pr_readback_status"] == "NOT_REACHED"
    assert out["source_delivery"] == "NO_COMPLETE_PR_RESPONSE"


@pytest.mark.parametrize("version", ["v03", "d10"])
@pytest.mark.parametrize(("header", "payload", "complete"), [
    (b"Content-Length: 2\r\n", b"{}", True), (b"", b"{}", True),
    (b"Content-Length: 8\r\n", b"{}", False), (b"Content-Length: bad\r\n", b"{}", False),
    (b"Content-Length: 8\r\nContent-Length: 2\r\n", b"{}", False),
    (b"Transfer-Encoding: chunked\r\n", b"2\r\n{}\r\n0\r\n\r\n", True),
    (b"Transfer-Encoding: chunked\r\n", b"2\r\n{", False),
])
def test_http_body_completeness(version, header, payload, complete):
    wire = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n" + header + b"\r\n" + payload
    response = http.client.HTTPResponse(Mock(makefile=Mock(return_value=io.BytesIO(wire))))
    response.begin()
    with patch("urllib.request.OpenerDirector.open", return_value=response):
        if version == "v03":
            read = v03.PublicGitHubReader().get_job_log
            url = "https://api.github.com/repos/test/project/actions/jobs/1/logs"
            expected, error = "{}", v03.OriginUnknown
        else:
            read = d10.DirectGithubReader().get
            url = "/repos/SepehrGhanbari/Ario/pulls/270"
            expected, error = b"{}", ValueError
        if complete:
            assert read(url) == expected
        else:
            with pytest.raises(error):
                read(url)


def test_interrupted_job_log_returns_unknown():
    reader = FakeGitHub()
    reader.get_job_log = Mock(side_effect=http.client.IncompleteRead(b"", 2))
    out = v03.assess_github_pr("SepehrGhanbari", "Ario", 249, reader=reader)
    assert out["status"] == out["correspondence_status"] == "UNKNOWN"
    assert out["binding"] is None


def test_api_metadata_rejects_duplicate_ids():
    reader = v03.PublicGitHubReader()
    with patch.object(reader, "_fetch", return_value=(200, b'{"id":12,"id":13}', None)):
        with pytest.raises(v03.OriginUnknown):
            reader.get_json("https://api.github.com/repos/test/project/pulls/1")


@pytest.mark.parametrize(("part", "field", "value"), [
    ("run", "id", float(legacy.RUN_ID)), ("run", "run_attempt", True),
    ("job", "id", float(legacy.JOB_ID)), ("job", "run_id", float(legacy.RUN_ID)),
    ("job", "run_attempt", 1.0),
])
def test_snapshot_requires_integer_identity(part, field, value):
    data = legacy.evidence()
    data[part][field] = value
    assert v01.assess(legacy.body(), data)["status"] == "UNKNOWN"
    assert v02.assess(legacy.body(), data)["correspondence_status"] == "UNKNOWN"


@pytest.mark.parametrize("module", [v07, v08])
def test_optional_job_attempt_is_integer(module):
    data = parser.evidence()
    data["job"]["run_attempt"] = 1.0
    assert module.assess(parser.claim_text(), data)["claim_correspondence"] == "UNKNOWN"


@pytest.mark.parametrize("module", [v01, v02])
def test_out_of_range_counter_returns_json(module, tmp_path, capsys):
    body, evidence = tmp_path / "body", tmp_path / "evidence"
    data = legacy.evidence(legacy.LOG.replace("1140 passed", "1" * 5000 + " passed"))
    body.write_text(legacy.body(), encoding="utf-8")
    evidence.write_text(json.dumps(data), encoding="utf-8")
    assert module.main(["--pr-body", str(body), "--evidence", str(evidence)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "UNKNOWN"
