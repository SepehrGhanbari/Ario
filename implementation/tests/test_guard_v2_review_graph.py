"""Bounded GraphQL review-evidence replay. Network is never called in pytest."""
from __future__ import annotations

import copy
import pytest

from research import guard_v2_review_graph as graph

REPO_ID = 1401709791
PR_ID = 5402535550  # deliberately > signed 32-bit GraphQL Int
HEAD = "a" * 40
BASE = "b" * 40


def pin():
    return {"repository_id": REPO_ID, "pr_id": PR_ID, "pr_number": 295,
            "head_sha": HEAD, "base_sha": BASE}


def original():
    return {
        "comments": [
            {"id": "IC_a", "body": "reviewed", "createdAt": "2026-11-21T01:00:00Z",
             "updatedAt": "2026-11-21T01:00:00Z"},
        ],
        "reviews": [
            {"id": "RV_a", "state": "COMMENTED", "body": "examined",
             "submittedAt": "2026-11-21T01:00:00Z",
             "updatedAt": "2026-11-21T01:00:00Z"},
        ],
        "threads": [
            {"id": "TH_a", "isResolved": True, "isOutdated": False,
             "path": "implementation/example.py",
             "comments": {"totalCount": 1,
                          "pageInfo": {"hasNextPage": False, "endCursor": None},
                          "nodes": [{"id": "RC_a", "body": "resolved",
                                     "updatedAt": "2026-11-21T01:00:00Z"}]}},
        ],
    }


class FakeGraphQL:
    def __init__(self, before=None, after=None):
        self.samples = [copy.deepcopy(before or original()),
                        copy.deepcopy(after or before or original())]
        self.cycle = -1
        self.calls = []
        self.head = HEAD
        self.base = BASE
        self.repo_id = str(REPO_ID)
        self.pr_id = str(PR_ID)
        self.pr_number = 295
        self.graph_errors = False
        self.repeat_cursor = False
        self.unstable_total = False
        self.fail_on_call = None

    def get_page(self, kind, number, cursor):
        self.calls.append((kind, number, cursor))
        if self.fail_on_call == len(self.calls):
            raise graph.ReviewGraphUnknown("GRAPHQL_HTTP_403")
        if kind == "comments" and cursor is None:
            self.cycle += 1
        assert self.cycle in (0, 1), "unexpected capture iteration"
        assert number == self.pr_number
        items = self.samples[self.cycle][kind]
        start = 0 if cursor is None else int(cursor.rsplit(":", 1)[1])
        batch = items[start:start + graph.PAGE_SIZE]
        more = start + len(batch) < len(items)
        nxt = f"{kind}:{start + len(batch)}" if more else None
        if self.repeat_cursor and cursor is not None:
            nxt = cursor
        total = len(items) + (1 if self.unstable_total and cursor is not None else 0)
        data = {
            "repository": {
                "fullDatabaseId": self.repo_id,
                "pullRequest": {
                    "fullDatabaseId": self.pr_id,
                    "number": self.pr_number,
                    "headRefOid": self.head,
                    "baseRefOid": self.base,
                    "state": "OPEN", "isDraft": True,
                    {"comments": "comments", "reviews": "reviews",
                     "threads": "reviewThreads"}[kind]: {
                        "totalCount": total, "nodes": copy.deepcopy(batch),
                        "pageInfo": {"hasNextPage": more, "endCursor": nxt},
                    },
                },
            },
        }
        return {"data": data, "errors": [{"message": "partial"}]} if self.graph_errors else {"data": data}


def expected_hold(out):
    assert out["disposition"] == "HOLD"
    assert out["merge_authorized"] is False
    assert out["check_publish_authorized"] is False
    assert out["trust_activated"] is False
    assert out["independent_custody"] == "NOT_ESTABLISHED"
    assert out["execution_attestation"] == "NOT_ESTABLISHED"


def test_same_two_complete_samples_are_stable_but_never_approved():
    r = FakeGraphQL()
    out = graph.compare_twice(pin(), r)
    expected_hold(out)
    assert out["sample_status"] == "SAMPLED_STABLE_UNATTESTED"
    assert out["first_digest"] == out["second_digest"]
    assert len(r.calls) == 6


def test_github_bigint_ids_above_32bit_are_supported_as_strings():
    assert graph._int_id(str(PR_ID)) == PR_ID
    assert graph.compare_twice(pin(), FakeGraphQL())["sample_status"] == "SAMPLED_STABLE_UNATTESTED"


@pytest.mark.parametrize("field", ["body", "updatedAt"])
def test_comment_edit_without_any_pr_updated_at_change_is_detected(field):
    a = original()
    b = copy.deepcopy(a)
    b["comments"][0][field] = "change the review" if field == "body" else "2026-11-21T03:00:00Z"
    out = graph.compare_twice(pin(), FakeGraphQL(a, b))
    expected_hold(out)
    assert out["reason"] == "REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES"


def test_comment_deletion_without_pr_metadata_change_is_detected():
    a = original()
    b = copy.deepcopy(a)
    b["comments"].clear()
    out = graph.compare_twice(pin(), FakeGraphQL(a, b))
    expected_hold(out)
    assert out["reason"] == "REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES"


def test_review_body_edit_is_detected():
    a = original()
    b = copy.deepcopy(a)
    b["reviews"][0]["body"] = "Changed review"
    assert graph.compare_twice(pin(), FakeGraphQL(a, b))["reason"] == "REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES"


def test_review_deletion_is_detected():
    a = original()
    b = copy.deepcopy(a)
    b["reviews"].clear()
    assert graph.compare_twice(pin(), FakeGraphQL(a, b))["reason"] == "REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES"


@pytest.mark.parametrize("field", ["isResolved", "isOutdated"])
def test_thread_state_change_is_detected(field):
    a = original()
    b = copy.deepcopy(a)
    b["threads"][0][field] = not a["threads"][0][field]
    assert graph.compare_twice(pin(), FakeGraphQL(a, b))["reason"] == "REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES"


def test_thread_reply_edit_is_detected():
    a = original()
    b = copy.deepcopy(a)
    b["threads"][0]["comments"]["nodes"][0]["body"] = "Edited inline"
    assert graph.compare_twice(pin(), FakeGraphQL(a, b))["reason"] == "REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES"


def test_thread_delete_is_detected():
    a = original()
    b = copy.deepcopy(a)
    b["threads"].clear()
    assert graph.compare_twice(pin(), FakeGraphQL(a, b))["reason"] == "REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES"


def test_comment_on_second_page_is_not_silently_skipped():
    a = original()
    a["comments"] = [
        {"id": f"IC_{i}", "body": str(i), "createdAt": "2026-11-21T01:00:00Z",
         "updatedAt": "2026-11-21T01:00:00Z"}
        for i in range(101)
    ]
    b = copy.deepcopy(a)
    b["comments"][100]["body"] = "EDITED PAGE TWO"
    reader = FakeGraphQL(a, b)
    out = graph.compare_twice(pin(), reader)
    expected_hold(out)
    assert out["reason"] == "REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES"
    assert any(cursor == "comments:100" for k, _, cursor in reader.calls if k == "comments")


def test_total_count_change_within_collection_fails_closed():
    a = original()
    a["comments"] = [
        {"id": f"IC_{i}", "body": str(i), "createdAt": "Z", "updatedAt": "Z"}
        for i in range(101)
    ]
    reader = FakeGraphQL(a, a)
    reader.unstable_total = True
    out = graph.compare_twice(pin(), reader)
    expected_hold(out)
    assert out["reason"] == "GRAPH_TOTAL_CHANGED_DURING_PAGES"


def test_page_cursor_loop_fails_closed():
    a = original()
    a["comments"] = [
        {"id": f"IC_{i}", "body": str(i), "createdAt": "Z", "updatedAt": "Z"}
        for i in range(201)
    ]
    reader = FakeGraphQL(a, a)
    reader.repeat_cursor = True
    out = graph.compare_twice(pin(), reader)
    expected_hold(out)
    assert out["reason"] == "INVALID_OR_REPEATED_GRAPH_CURSOR"


def test_duplicate_node_ids_fail_closed():
    a = original()
    a["comments"].append(copy.deepcopy(a["comments"][0]))
    assert graph.compare_twice(pin(), FakeGraphQL(a, a))["reason"] == "DUPLICATE_GRAPH_NODE_ID"


def test_more_than_100_replies_not_counted_as_complete_thread():
    a = original()
    a["threads"][0]["comments"]["totalCount"] = 101
    a["threads"][0]["comments"]["pageInfo"]["hasNextPage"] = True
    assert graph.compare_twice(pin(), FakeGraphQL(a, a))["reason"] == "INCOMPLETE_THREAD_REPLIES"


def test_missing_thread_reply_fails_closed():
    a = original()
    a["threads"][0]["comments"]["totalCount"] = 2
    assert graph.compare_twice(pin(), FakeGraphQL(a, a))["reason"] == "INCOMPLETE_THREAD_REPLIES"


def test_unresolved_thread_is_sampled_not_silently_filtered():
    a = original()
    a["threads"][0]["isResolved"] = False
    out = graph.compare_twice(pin(), FakeGraphQL(a, a))
    expected_hold(out)
    assert out["sample_status"] == "SAMPLED_STABLE_UNATTESTED"
    # An unresolved thread is present in the full sample and cannot be
    # elevated to "all resolved" by this non-authoritative collector.
    assert graph.capture(pin(), FakeGraphQL(a, a))["evidence"]["threads"][0]["isResolved"] is False


def test_missing_pages_or_api_errors_never_become_positive():
    reader = FakeGraphQL()
    reader.graph_errors = True
    out = graph.compare_twice(pin(), reader)
    expected_hold(out)
    assert out["reason"] == "GRAPHQL_ERROR_OR_MISSING_PAGE"


def test_read_only_http_403_fails_closed():
    reader = FakeGraphQL()
    reader.fail_on_call = 4
    out = graph.compare_twice(pin(), reader)
    expected_hold(out)
    assert out["reason"] == "GRAPHQL_HTTP_403"


@pytest.mark.parametrize("bad", [True, float(REPO_ID), "0001401709791", 0, None])
def test_rejects_numeric_identity_aliases(bad):
    reader = FakeGraphQL()
    reader.repo_id = bad
    out = graph.compare_twice(pin(), reader)
    expected_hold(out)
    assert out["reason"] == "MALFORMED_BIGINT_ID"


def test_correct_type_wrong_pr_identity_fails():
    reader = FakeGraphQL()
    reader.pr_id = str(PR_ID + 1)
    assert graph.compare_twice(pin(), reader)["reason"] == "GRAPH_PR_IDENTITY_MISMATCH"


@pytest.mark.parametrize("attr", ["head", "base"])
def test_revision_drift_fails_closed(attr):
    reader = FakeGraphQL()
    setattr(reader, attr, "f" * 40)
    out = graph.compare_twice(pin(), reader)
    expected_hold(out)
    assert out["reason"] == "GRAPH_PR_REVISION_CHANGED"


def test_query_cannot_be_caller_generated_or_be_mutation():
    for query in graph.QUERIES.values():
        assert query.startswith("query ArioReviewEvidence")
        assert "mutation" not in query.lower()
        assert "fullDatabaseId" in query
        assert "pageInfo" in query
    assert set(graph.QUERIES) == {"comments", "reviews", "threads"}


def test_no_token_denies_network_client_before_network():
    with pytest.raises(graph.ReviewGraphUnknown, match="MISSING_READ_ONLY_TOKEN"):
        graph.ReadOnlyGraphQL("")


def test_stable_unchanged_but_forged_records_never_establish_independence():
    altered = original()
    altered["comments"][0]["body"] = "fabricated before first capture"
    out = graph.compare_twice(pin(), FakeGraphQL(altered, altered))
    expected_hold(out)
    assert out["sample_status"] == "SAMPLED_STABLE_UNATTESTED"
    assert out["independent_custody"] == "NOT_ESTABLISHED"
