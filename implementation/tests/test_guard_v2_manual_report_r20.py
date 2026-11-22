"""R22 regression: a successful report must explicitly carry graph reason."""
import json

from research import guard_v2_trusted_manual as reader
from research.guard_v2_manual_report import main
from test_guard_v2_trusted_manual import FakeRest, SOURCE_SHA
from test_guard_v2_review_graph import FakeGraphQL, HEAD

PR = 295


def successful_reader_output():
    return reader.observe(
        PR, HEAD, rest_reader=FakeRest(), graph_reader=FakeGraphQL(),
        source_sha=SOURCE_SHA,
    )


def validate(tmp_path, report, reader_exit):
    path = tmp_path / "manual-report.json"
    path.write_text(json.dumps(report, sort_keys=True, ensure_ascii=True) + "\n",
                    encoding="utf-8")
    return main([str(path), str(PR), HEAD, SOURCE_SHA, str(reader_exit)])


def test_success_without_review_graph_reason_is_rejected(tmp_path):
    report = successful_reader_output()
    assert report["review_graph_reason"] == "TWO_COMPLETE_GRAPH_SAMPLES_MATCH"
    del report["review_graph_reason"]

    # RED on the old validator: it supplies SUCCESS_GRAPH_REASON as a default.
    assert validate(tmp_path, report, 0) == 2


def test_success_with_explicit_review_graph_reason_remains_valid(tmp_path):
    report = successful_reader_output()
    assert report["review_graph_reason"] == "TWO_COMPLETE_GRAPH_SAMPLES_MATCH"
    assert validate(tmp_path, report, 0) == 0


def test_incomplete_hold_without_review_graph_reason_remains_valid(tmp_path):
    report = reader._hold("MISSING_READ_ONLY_TOKEN")
    assert "review_graph_reason" not in report
    assert validate(tmp_path, report, 2) == 0
