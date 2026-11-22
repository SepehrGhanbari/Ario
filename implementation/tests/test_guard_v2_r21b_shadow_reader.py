"""R21B shadow reader falsifiers; all data synthetic, no network or tokens.

V1 must remain byte/shape identical to the real pre-B V1 compare function.
B-enriched data are replayed from the SAME exact in-memory pages, not fetched
again with a possibly changed revision and called the same sample.
"""
from __future__ import annotations

import copy
import json

import pytest

from research import guard_v2_review_graph as v1
from research import guard_v2_r21b_capture_v2 as v2
from research import guard_v2_r21b_shadow_reader as shadow
from test_guard_v2_review_graph import FakeGraphQL, original, pin
from test_guard_v2_r21b_attribution_synthetic import enriched


def hold(value):
    assert value["status"] == "UNKNOWN"
    assert value["disposition"] == "HOLD"
    assert value["merge_authorized"] is False
    assert value["check_publish_authorized"] is False
    assert value["trust_activated"] is False
    assert value["execution_attestation"] == "NOT_ESTABLISHED"
    assert value["independent_custody"] == "NOT_ESTABLISHED"
    assert value["historical_truth"] == "NOT_ESTABLISHED"
    assert value["v1_implementation_modified"] is False
    assert value["historical_ledger_modified"] is False


def test_shadow_never_rewrites_or_monkeypatches_global_v1_query():
    saved = v1.QUERIES["reviews"]
    assert saved == (v1._QUERY_HEADER + v1._FIELDS["reviews"] +
                     "\n" + v1._QUERY_TAIL)
    assert shadow.REVIEW_B_QUERY != saved
    assert "author { __typename login ... on Node { id } }" in shadow.REVIEW_B_QUERY
    assert "author { __typename login id }" not in shadow.REVIEW_B_QUERY
    assert "author" not in saved
    assert "commit { oid }" not in saved
    assert v1.QUERIES["reviews"] == saved
    assert set(v1.QUERIES) == {"comments", "reviews", "threads"}


def test_live_reader_path_really_uses_unmodified_v1_compare_twice():
    old = v1.compare_twice(pin(), FakeGraphQL(original()))
    reader = FakeGraphQL(enriched())
    result = shadow.compare_shadow(pin(), reader)
    hold(result)
    assert result["v1"] == old
    assert result["v1"]["sample_status"] == "SAMPLED_STABLE_UNATTESTED"
    assert result["v2"]["reason"] == "B_SAMPLES_EQUAL_NONATTESTED"
    assert result["v2"]["first_attribution_digest"] == result["v2"]["second_attribution_digest"]
    assert result["v2"]["first_attribution_digest"] != old["first_digest"]
    assert result["recorded_page_count"] == len(reader.calls) == 6
    assert result["source_sampling"] == "SAME_B_ENRICHED_PAGES_REPLAYED_IN_MEMORY"


def test_enriched_v1_projection_matches_real_old_legacy_digest():
    prior = v1.compare_twice(pin(), FakeGraphQL(original()))
    enriched_data = enriched()
    result = shadow.compare_shadow(pin(), FakeGraphQL(enriched_data))
    assert result["v1"]["first_digest"] == prior["first_digest"]
    assert result["v1"]["second_digest"] == prior["second_digest"]
    assert result["v1"]["reason"] == prior["reason"]
    assert "author" in enriched_data["reviews"][0]  # caller input unmodified


@pytest.mark.parametrize("field,value", [
    ("author", {"__typename": "Bot", "login": "other", "id": "BOT_9"}),
    ("authorAssociation", "NONE"),
    ("commit", {"oid": "f" * 40}),
    ("lastEditedAt", "2026-11-22T20:00:00Z"),
])
def test_new_attribution_drift_v1_stable_v2_changed(field, value):
    a, b = enriched(), enriched()
    b["reviews"][0][field] = value
    reader = FakeGraphQL(a, b)
    result = shadow.compare_shadow(pin(), reader)
    hold(result)
    assert len(reader.calls) == result["recorded_page_count"] == 6
    assert result["v1"]["sample_status"] == "SAMPLED_STABLE_UNATTESTED"
    assert result["v1"]["first_digest"] == result["v1"]["second_digest"]
    assert result["v2"]["reason"] == "B_SAMPLES_CHANGED_HOLD"
    assert result["v2"]["first_attribution_digest"] != result["v2"]["second_attribution_digest"]


@pytest.mark.parametrize("field,value", [
    ("body", "v1 changed body"),
    ("updatedAt", "2026-11-22T20:00:00Z"),
    ("state", "APPROVED"),
])
def test_legacy_change_never_claims_v2_success(field, value):
    a, b = enriched(), enriched()
    b["reviews"][0][field] = value
    result = shadow.compare_shadow(pin(), FakeGraphQL(a, b))
    hold(result)
    assert result["reason"] == "SHADOW_V1_FAILED_OR_CHANGED"
    assert result["v1"]["reason"] == "REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES"
    assert result["v2"] is None


@pytest.mark.parametrize("field", ["author", "authorAssociation", "commit", "lastEditedAt"])
def test_absent_selected_field_does_not_promote_v2(field):
    data = enriched()
    del data["reviews"][0][field]
    result = shadow.compare_shadow(pin(), FakeGraphQL(data))
    hold(result)
    assert result["v1"]["sample_status"] == "SAMPLED_STABLE_UNATTESTED"
    assert result["v2"]["reason"] == "B_SAMPLES_INCOMPLETE_OR_UNKNOWN_HOLD"


@pytest.mark.parametrize("field", ["author", "commit"])
def test_null_selected_field_does_not_promote_v2(field):
    data = enriched()
    data["reviews"][0][field] = None
    result = shadow.compare_shadow(pin(), FakeGraphQL(data))
    hold(result)
    assert result["v1"]["sample_status"] == "SAMPLED_STABLE_UNATTESTED"
    assert result["v2"]["reason"] == "B_SAMPLES_INCOMPLETE_OR_UNKNOWN_HOLD"


def test_unrecognized_actor_type_even_with_node_id_cannot_promote_v2():
    data = enriched()
    data["reviews"][0]["author"] = {"__typename": "FutureActor",
                                     "login": "future", "id": "FA_9"}
    result = shadow.compare_shadow(pin(), FakeGraphQL(data))
    hold(result)
    assert result["v1"]["sample_status"] == "SAMPLED_STABLE_UNATTESTED"
    assert result["v2"]["reason"] == "B_SAMPLES_INCOMPLETE_OR_UNKNOWN_HOLD"


def test_fake_approved_and_authority_looking_login_remain_hold():
    data = enriched()
    data["reviews"][0]["state"] = "APPROVED"
    data["reviews"][0]["author"]["login"] = "OK_TO_MERGE"
    out = shadow.compare_shadow(pin(), FakeGraphQL(data))
    hold(out)
    assert out["v1"]["sample_status"] == "SAMPLED_STABLE_UNATTESTED"
    assert out["v2"]["reason"] == "B_SAMPLES_EQUAL_NONATTESTED"
    assert "OK_TO_MERGE" not in json.dumps(out, sort_keys=True)


def test_review_graph_error_never_retries_or_runs_v2():
    reader = FakeGraphQL(enriched())
    reader.fail_on_call = 4
    out = shadow.compare_shadow(pin(), reader)
    hold(out)
    assert out["v1"]["reason"] == "GRAPHQL_HTTP_403"
    assert out["v2"] is None
    assert len(reader.calls) == 4


def test_duplicate_ids_fail_v1_and_never_run_v2():
    data = enriched()
    data["reviews"].append(copy.deepcopy(data["reviews"][0]))
    out = shadow.compare_shadow(pin(), FakeGraphQL(data))
    hold(out)
    assert out["v1"]["reason"] == "DUPLICATE_GRAPH_NODE_ID"
    assert out["v2"] is None


@pytest.mark.parametrize("extra", ["merge_authorized", "trusted", "claim"])
def test_unexpected_new_review_node_keys_fail_closed(extra):
    data = enriched()
    data["reviews"][0][extra] = "green"
    out = shadow.compare_shadow(pin(), FakeGraphQL(data))
    hold(out)
    assert out["v1"]["reason"] == "SHADOW_UNEXPECTED_REVIEW_FIELD"
    assert out["v2"] is None


def test_two_copies_replayed_without_network_round_trip():
    reader = FakeGraphQL(enriched())
    out = shadow.compare_shadow(pin(), reader)
    hold(out)
    assert reader.calls == [("comments", 295, None), ("reviews", 295, None),
                            ("threads", 295, None)] * 2


@pytest.mark.parametrize("tamper", [
    lambda p: (p[0][0], p[0][1] + 1, p[0][2], p[0][3]),
    lambda p: (p[0][0], p[0][1], "wrong-cursor", p[0][3]),
])
def test_replay_detects_call_divergence(tamper):
    rec = shadow.V1ProjectionRecorder(FakeGraphQL(enriched()))
    result = v1.compare_twice(pin(), rec)
    assert result["sample_status"] == "SAMPLED_STABLE_UNATTESTED"
    corrupted = list(rec.pages)
    corrupted[0] = tamper(corrupted)
    replay = shadow.ReplayInMemory(corrupted)
    with pytest.raises(v1.ReviewGraphUnknown, match="SHADOW_REPLAY_CALL_MISMATCH"):
        v1.capture(pin(), replay)


def test_replay_reports_unconsumed_pages_not_silent_green():
    rec = shadow.V1ProjectionRecorder(FakeGraphQL(enriched()))
    v1.compare_twice(pin(), rec)
    replay = shadow.ReplayInMemory(rec.pages)
    v1.capture(pin(), replay)
    with pytest.raises(v1.ReviewGraphUnknown, match="SHADOW_REPLAY_UNUSED_PAGES"):
        replay.assert_exhausted()


def test_projection_rejects_unexpected_field_before_record():
    data = enriched()
    data["reviews"][0]["MALICIOUS"] = "MERGE"
    recorder = shadow.V1ProjectionRecorder(FakeGraphQL(data))
    out = v1.compare_twice(pin(), recorder)
    assert out["reason"] == "SHADOW_UNEXPECTED_REVIEW_FIELD"
    assert len(recorder.pages) == 1  # first comments, not bad reviews


def test_failed_pin_from_real_v1_does_not_run_v2():
    bad_pin = pin()
    bad_pin["head_sha"] = "f" * 40
    result = shadow.compare_shadow(bad_pin, FakeGraphQL(enriched()))
    hold(result)
    assert result["v1"]["reason"] == "GRAPH_PR_REVISION_CHANGED"
    assert result["v2"] is None


def test_v2_digest_stable_independent_of_unrelated_v1_comment_fields():
    data = enriched()
    altered = enriched()
    altered["comments"][0]["body"] = "different comment"
    first = shadow.compare_shadow(pin(), FakeGraphQL(data))
    second = shadow.compare_shadow(pin(), FakeGraphQL(altered))
    hold(first)
    hold(second)
    assert first["v1"]["first_digest"] != second["v1"]["first_digest"]
    assert first["v2"]["first_attribution_digest"] == second["v2"]["first_attribution_digest"]


class _FakeResponse:
    status = 200

    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, length):
        return self.data[:length]


class _RecordingOpener:
    def __init__(self, data=b'{"data": {}}'):
        self.calls = []
        self.data = data

    def open(self, req, timeout):
        self.calls.append((req, timeout))
        return _FakeResponse(self.data)


@pytest.mark.parametrize("kind", ["reviews", "comments", "threads"])
def test_real_b_transport_fixed_queries_and_read_only_post(kind):
    client = shadow.ReadOnlyGraphQLB("DUMMY_NEVER_SENT")
    opener = _RecordingOpener()
    client._opener = opener
    data = client.get_page(kind, 295, None)
    assert data == {"data": {}}
    req, timeout = opener.calls[0]
    payload = json.loads(req.data)
    assert timeout == 12
    assert req.full_url == v1.API
    assert req.get_method() == "POST"
    assert payload["query"] == (shadow.REVIEW_B_QUERY if kind == "reviews"
                                else v1.QUERIES[kind])
    assert payload["query"].startswith("query ")
    assert "mutation" not in payload["query"].lower()
    assert payload["variables"] == {
        "owner": v1.OWNER, "repo": v1.REPO, "number": 295, "cursor": None}


def test_bad_transport_cursor_denied_without_network():
    client = shadow.ReadOnlyGraphQLB("DUMMY_NEVER_SENT")
    client._opener = _RecordingOpener()
    with pytest.raises(v1.ReviewGraphUnknown, match="INVALID_PAGE_CURSOR"):
        client.get_page("reviews", 295, "")
    assert client._opener.calls == []


def test_graphql_v2_transport_size_limit_fail_closed():
    client = shadow.ReadOnlyGraphQLB("DUMMY_NEVER_SENT")
    client._opener = _RecordingOpener(b" " * (v1.MAX_RESPONSE_BYTES + 1))
    with pytest.raises(v1.ReviewGraphUnknown, match="GRAPHQL_RESPONSE_TOO_LARGE"):
        client.get_page("reviews", 295, None)


def test_b_transport_invalid_json_fails_closed():
    client = shadow.ReadOnlyGraphQLB("DUMMY_NEVER_SENT")
    client._opener = _RecordingOpener(b'{"data": {},"data": {}}')
    with pytest.raises(v1.ReviewGraphUnknown, match="MALFORMED_GRAPHQL_JSON"):
        client.get_page("reviews", 295, None)
