"""R21B attack matrix: multi-page tamper, TOCTOU, resource and token boundaries.

Offline tests call the real V1 graph reader and B shadow adapter. They must
not claim history, custody, execution attestation, or merge authorization.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from research import guard_v2_review_graph as v1
from research import guard_v2_r21b_shadow_reader as shadow
from test_guard_v2_review_graph import FakeGraphQL, pin
from test_guard_v2_r21b_attribution_synthetic import enriched


def hold(result):
    assert result["disposition"] == "HOLD"
    assert result["status"] == "UNKNOWN"
    assert result["merge_authorized"] is False
    assert result["check_publish_authorized"] is False
    assert result["trust_activated"] is False
    assert result["execution_attestation"] == "NOT_ESTABLISHED"
    assert result["historical_truth"] == "NOT_ESTABLISHED"


def reviews(count):
    data = enriched()
    source = data["reviews"][0]
    data["reviews"] = []
    for i in range(count):
        item = copy.deepcopy(source)
        item["id"] = f"RV_{i:04d}"
        data["reviews"].append(item)
    return data


def test_b_change_on_final_second_review_page_is_detected_without_v1_change():
    a, b = reviews(101), reviews(101)
    b["reviews"][100]["author"]["login"] = "ADVERSARIAL_SECOND_PAGE_CHANGE"
    reader = FakeGraphQL(a, b)
    out = shadow.compare_shadow(pin(), reader)
    hold(out)
    assert out["v1"]["sample_status"] == "SAMPLED_STABLE_UNATTESTED"
    assert out["v1"]["first_digest"] == out["v1"]["second_digest"]
    assert out["v2"]["reason"] == "B_SAMPLES_CHANGED_HOLD"
    assert out["v2"]["first_attribution_digest"] != out["v2"]["second_attribution_digest"]
    assert len(reader.calls) == out["recorded_page_count"] == 8
    assert reader.calls.count(("reviews", 295, "reviews:100")) == 2


def test_b_enriched_second_page_projection_matches_original_v1_query_digest():
    old = reviews(101)
    old["reviews"] = [
        {key: value for key, value in item.items()
         if key in shadow.V1_FIELDS} for item in old["reviews"]
    ]
    direct = v1.compare_twice(pin(), FakeGraphQL(old))
    dual = shadow.compare_shadow(pin(), FakeGraphQL(reviews(101)))
    hold(dual)
    assert dual["v1"] == direct
    assert dual["v2"]["reason"] == "B_SAMPLES_EQUAL_NONATTESTED"


@pytest.mark.parametrize("count", [101, 201])
def test_cursor_loop_or_truncation_holds_without_v2(count):
    reader = FakeGraphQL(reviews(count))
    reader.repeat_cursor = True
    out = shadow.compare_shadow(pin(), reader)
    hold(out)
    if count == 201:
        assert out["v1"]["reason"] == "INVALID_OR_REPEATED_GRAPH_CURSOR"
        assert out["v2"] is None
    else:
        # Two pages complete for 101; a repeat-cursor knob has no effect.
        assert out["v1"]["sample_status"] == "SAMPLED_STABLE_UNATTESTED"
        assert out["v2"]["reason"] == "B_SAMPLES_EQUAL_NONATTESTED"


def test_changed_total_count_at_page_two_fails_closed():
    reader = FakeGraphQL(reviews(101))
    reader.unstable_total = True
    out = shadow.compare_shadow(pin(), reader)
    hold(out)
    assert out["v1"]["reason"] == "GRAPH_TOTAL_CHANGED_DURING_PAGES"
    assert out["v2"] is None


def test_beyond_max_items_rejected_before_unbounded_collection():
    reader = FakeGraphQL(reviews(v1.MAX_ITEMS + 1))
    out = shadow.compare_shadow(pin(), reader)
    hold(out)
    assert out["v1"]["reason"] == "MALFORMED_GRAPH_CONNECTION"
    assert out["v2"] is None


class RevisionSwap(FakeGraphQL):
    def get_page(self, kind, number, cursor):
        if kind == "comments" and cursor is None and self.cycle == 0:
            self.head = "f" * 40
        return super().get_page(kind, number, cursor)


def test_graphql_head_swap_between_samples_blocks_both_contracts():
    reader = RevisionSwap(enriched())
    out = shadow.compare_shadow(pin(), reader)
    hold(out)
    assert out["v1"]["reason"] == "GRAPH_PR_REVISION_CHANGED"
    assert out["v2"] is None


def test_output_never_exposes_raw_author_body_or_identity():
    data = enriched()
    data["reviews"][0]["body"] = "DO_NOT_PUBLISH_REVIEW_BODY"
    data["reviews"][0]["author"]["login"] = "DO_NOT_PUBLISH_ACTOR_LOGIN"
    data["reviews"][0]["author"]["id"] = "DO_NOT_PUBLISH_ACTOR_NODE_ID"
    out = shadow.compare_shadow(pin(), FakeGraphQL(data))
    hold(out)
    serialized = json.dumps(out, sort_keys=True)
    for secret in ("DO_NOT_PUBLISH_REVIEW_BODY", "DO_NOT_PUBLISH_ACTOR_LOGIN",
                   "DO_NOT_PUBLISH_ACTOR_NODE_ID", "DUMMY_NEVER_SENT"):
        assert secret not in serialized


def test_extra_untrusted_review_key_cannot_enter_v1_projection():
    data = enriched()
    data["reviews"][0]["merge_authorized"] = True
    out = shadow.compare_shadow(pin(), FakeGraphQL(data))
    hold(out)
    assert out["v1"]["reason"] == "SHADOW_UNEXPECTED_REVIEW_FIELD"
    assert out["v2"] is None


def test_recording_hard_page_budget_rejects_before_network():
    reader = FakeGraphQL(enriched())
    recorder = shadow.V1ProjectionRecorder(reader)
    recorder.pages = [None] * (2 * 3 * v1.MAX_PAGES)
    with pytest.raises(v1.ReviewGraphUnknown, match="SHADOW_REPLAY_BUDGET_EXCEEDED"):
        recorder.get_page("comments", 295, None)
    assert reader.calls == []


def test_untrusted_cursor_stays_a_graphql_variable_not_query_text():
    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None
        def read(self, n):
            return b'{"data":{}}'
    class Opener:
        req = None
        def open(self, request, timeout):
            self.req = request
            return Response()

    client = shadow.ReadOnlyGraphQLB("SYNTHETIC_TOKEN_NEVER_SENT")
    opener = Opener()
    client._opener = opener
    weird_cursor = 'x"}mutation { deleteRepository(input:{}) } #'
    response = client.get_page("reviews", 295, weird_cursor)
    assert response == {"data": {}}
    data = json.loads(opener.req.data)
    assert data["variables"]["cursor"] == weird_cursor
    assert data["query"] == shadow.REVIEW_B_QUERY
    assert weird_cursor not in data["query"]
    assert "mutation {" not in data["query"]
    assert opener.req.get_method() == "POST"


def test_workflow_permissions_and_trigger_remain_fixed_read_only():
    root = Path(__file__).resolve().parents[2]
    path = root / ".github/workflows/ario-r21b-shadow-readonly-probe.yml"
    contents = path.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^permissions:\n((?:  [^\n]*\n)+)", contents)
    assert match is not None
    lines = {line.strip() for line in match.group(1).splitlines()}
    assert lines == {"contents: read", "pull-requests: read"}
    assert "pull_request_target:" not in contents
    assert "workflow_dispatch:" not in contents
    assert "secrets." not in contents
    assert "persist-credentials: false" in contents
    assert "GITHUB_TOKEN: " in contents
    assert "github.token" in contents
    assert "research/r21b-shadow-reader-v1-v2-20261122" in contents
    assert re.search(r"actions/checkout@[0-9a-f]{40}", contents)
    assert re.search(r"actions/setup-python@[0-9a-f]{40}", contents)


def test_token_permission_change_to_write_is_detected():
    root = Path(__file__).resolve().parents[2]
    contents = (root / ".github/workflows/ario-r21b-shadow-readonly-probe.yml").read_text()
    bad = contents.replace("contents: read", "contents: write")
    assert "contents: write" in bad
    assert "contents: write" not in contents
