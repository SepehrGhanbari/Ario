"""R21 A research-only negative/positive tests for the manual report validator.

No network, GitHub token, signer, merge, or trust authority. A diagnostic
is never an authorization. Designed to fail on pinned original R19 validator
and pass with the exactly pinned R21 A patch.
"""
import json
import pytest
from research import guard_v2_manual_report as validator

HEAD = "a" * 40
SOURCE = "b" * 40
NUMBER = 295


def report(reason="UNASSESSED", **fields):
    return {
        "schema": "ARIO-GUARD-V2-TRUSTED-MANUAL-READ-LAB-0.1",
        "status": "UNKNOWN", "disposition": "HOLD", "reason": reason,
        "merge_authorized": False, "check_publish_authorized": False,
        "trust_activated": False, "execution_attestation": "NOT_ESTABLISHED",
        "independent_custody": "NOT_ESTABLISHED",
        "atomic_merge_attestation": "NOT_ESTABLISHED",
        "source_provenance": "PROVIDED_BY_CALLER_NOT_INDEPENDENTLY_VERIFIED",
        "source_commit_sha": SOURCE, **fields,
    }


def accepts(tmp_path, payload, exit_code=2):
    path = tmp_path / "report.json"
    path.write_text(json.dumps(payload, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    return validator.main([str(path), str(NUMBER), HEAD, SOURCE, str(exit_code)]) == 0


@pytest.mark.parametrize("reason", [
    "OK_TO_MERGE", "GREEN_TO_MERGE", "MERGE_PERMITTED", "MERGE_APPROVED",
    "READY_TO_MERGE", "ALLOW_MERGE", "LGTM", "APPROVED", "CHECK_PASSED",
    "TRUST_ACTIVATED", "SHIP_IT", "GRAPH_OK_TO_MERGE",
    "GRAPH_GRAPH_MERGE_PERMITTED", "GITHUB_OK", "REST_ALL_CLEAR",
    "SOME_REST_READ_UNKNOWN_REASON", "NETWORK_BLIP", "RETRY_LATER",
    "GITHUB_HTTP_40", "GITHUB_HTTP_4031", "GITHUB_HTTP_ABC",
    "GITHUB_HTTP_403_MERGE", "GRAPHQL_HTTP_5",
    "GRAPH_GRAPH_GRAPHQL_HTTP_502", "GRAPH_",
    "GRAPH_GRAPH_GRAPH_PR_REVISION_CHANGED",
    "PR_DRAFT_READ_ONLY_HOLD", "LIVE_READ_ONLY_NON_ATOMIC_HOLD",
    "TWO_COMPLETE_GRAPH_SAMPLES_MATCH",
])
def test_failed_run_never_accepts_unlisted_or_authority_reason(tmp_path, reason):
    assert not accepts(tmp_path, report(reason))


@pytest.mark.parametrize("reason", [
    "UNASSESSED", "UNKNOWN", "GRAPH_UNKNOWN", "GITHUB_HTTP_403",
    "GITHUB_HTTP_503", "GRAPHQL_HTTP_502", "GRAPH_GRAPHQL_HTTP_502",
    "GRAPH_GRAPH_PR_REVISION_CHANGED", "REST_PR_CHANGED_DURING_GRAPH_READ",
    "TRUSTED_OBSERVER_INITIALIZATION_FAILED", "MISSING_READ_ONLY_TOKEN",
    "INVALID_JSON", "INVALID_API_JSON", "INCOMPLETE_OR_OVERSIZED_RESPONSE",
])
def test_genuine_failure_reason_shapes_remain_accepted(tmp_path, reason):
    assert accepts(tmp_path, report(reason))


@pytest.mark.parametrize("sample", [{}, [], None, True, 5, "OK_TO_MERGE", "CHECK_PASSED"])
def test_noncanonical_sample_rejected(tmp_path, sample):
    assert not accepts(tmp_path, report("UNASSESSED", review_graph_sample=sample))


@pytest.mark.parametrize("key,value", [
    ("live_identity", {"repository_id":1,"pr_id":2,"pr_number":295,"head_sha":HEAD,"base_sha":"c"*40}),
    ("review_freshness", "TWO_SAMPLED_GRAPHS_MATCH_NON_ATOMIC"),
])
def test_failed_run_rejects_success_only_fields(tmp_path, key, value):
    assert not accepts(tmp_path, report("UNASSESSED", **{key: value}))


def test_rejects_deceptive_graph_reason_on_failed_run(tmp_path):
    assert not accepts(tmp_path, report("UNASSESSED", review_graph_reason="OK_TO_MERGE"))


def test_allows_graph_success_field_when_final_rest_recheck_failed(tmp_path):
    assert accepts(tmp_path, report("REST_PR_CHANGED_DURING_GRAPH_READ",
                                    review_graph_sample="SAMPLED_STABLE_UNATTESTED",
                                    review_graph_reason="TWO_COMPLETE_GRAPH_SAMPLES_MATCH",
                                    first_digest="d"*64, second_digest="d"*64))


def test_complete_non_authoritative_success_shape_retained(tmp_path):
    full = report("PR_DRAFT_READ_ONLY_HOLD",
                  review_graph_sample="SAMPLED_STABLE_UNATTESTED",
                  review_graph_reason="TWO_COMPLETE_GRAPH_SAMPLES_MATCH",
                  review_freshness="TWO_SAMPLED_GRAPHS_MATCH_NON_ATOMIC",
                  first_digest="d"*64, second_digest="d"*64,
                  live_identity={"repository_id":1,"pr_id":2,"pr_number":295,
                                 "head_sha":HEAD,"base_sha":"c"*40})
    assert accepts(tmp_path, full, exit_code=0)
    assert not accepts(tmp_path, full, exit_code=2)


@pytest.mark.parametrize("value", [
    "OK_TO_MERGE", "MERGE_PERMITTED", "APPROVED", "GREEN_TO_MERGE",
    "OnBehalfOfHuman", "OSError_BUY",
])
def test_error_type_authority_confusion_rejected(tmp_path, value):
    assert not accepts(tmp_path, report("TRUSTED_OBSERVER_INITIALIZATION_FAILED",
                                        error_type=value))


@pytest.mark.parametrize("value", [
    "ReadUnknown", "ReviewGraphUnknown", "ValueError", "TypeError", "OSError",
    "TimeoutError", "URLError", "ConnectionResetError", "SSLError",
])
def test_error_type_known_exception_classes_accepted(tmp_path, value):
    assert accepts(tmp_path, report("TRUSTED_OBSERVER_INITIALIZATION_FAILED",
                                    error_type=value))


def test_error_type_rejected_when_reason_is_not_init(tmp_path):
    assert not accepts(tmp_path, report("UNKNOWN", error_type="OSError"))
