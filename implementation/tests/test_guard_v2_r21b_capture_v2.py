"""R21B V2 capture/digest contract tests: synthetic, no credentials, no merge.

Use the repository's REAL V1 graph.capture() with controlled FakeGraphQL
fixtures. V2 is a separate domain-separated attribution SUBSET only.
"""
from __future__ import annotations
import copy
import hashlib
import json
import pytest

from research import guard_v2_review_graph as graph
from research import guard_v2_r21b_capture_v2 as v2
from test_guard_v2_review_graph import FakeGraphQL, original, pin
from test_guard_v2_r21b_attribution_synthetic import enriched


def make_capture(data=None):
    return graph.capture(pin(), FakeGraphQL(data if data is not None else enriched()))


def make_v2(data=None):
    return v2.capture_v2(pin(), make_capture(data))


def assert_non_authority(out):
    assert out["disposition"] == "HOLD"
    assert out["status"] == "UNKNOWN"
    assert out["merge_authorized"] is False
    assert out["trust_activated"] is False
    assert out["check_publish_authorized"] is False
    assert out["independent_custody"] == "NOT_ESTABLISHED"
    assert out["execution_attestation"] == "NOT_ESTABLISHED"


def test_v2_is_distinct_from_historical_graph_schema_and_digest():
    c = make_capture()
    res = v2.capture_v2(pin(), c)
    assert_non_authority(res)
    assert res["schema"] == v2.SCHEMA
    assert res["capture_version"] == 2
    assert res["reason"] == "B_OBSERVED_NONATTESTED"
    assert res["commitment_algorithm"] == v2.HASH_ALGORITHM
    assert len(res["attribution_digest"]) == 64
    legacy = hashlib.sha256(
        __import__("research.guard_v2_pr_scope", fromlist=["canonical"]).canonical(c)
    ).hexdigest()
    assert res["attribution_digest"] != legacy
    assert v2.DOMAIN != b""


def test_new_capture_is_deterministic_across_replayed_same_bytes():
    assert make_v2()["attribution_digest"] == make_v2()["attribution_digest"]


@pytest.mark.parametrize("field,value", [
    ("author", {"__typename": "User", "login": "bob", "id": "U_1"}),
    ("authorAssociation", "COLLABORATOR"),
    ("commit", {"oid": "f" * 40}),
    ("lastEditedAt", "2026-11-22T12:00:00Z"),
    ("body", "Revised public review"),
    ("state", "APPROVED"),
    ("submittedAt", "2026-11-22T12:00:00Z"),
    ("updatedAt", "2026-11-22T12:00:00Z"),
])
def test_selected_attribution_and_old_relevant_fields_change_v2_digest(field, value):
    data = enriched()
    data["reviews"][0][field] = value
    assert make_v2(data)["attribution_digest"] != make_v2()["attribution_digest"]
    assert_non_authority(make_v2(data))


@pytest.mark.parametrize("field", ["author", "commit"])
def test_null_author_or_commit_is_partial_unknown_not_fabricated(field):
    data = enriched()
    data["reviews"][0][field] = None
    res = make_v2(data)
    assert_non_authority(res)
    assert res["reason"] == "B_PARTIAL_ATTRIBUTION_UNKNOWN"
    assert res["reviews"][0]["selected_field_presence"][field] == "EXPLICIT_NULL"
    assert res["attribution_digest"] != make_v2()["attribution_digest"]


@pytest.mark.parametrize("field", ["author", "authorAssociation", "commit", "lastEditedAt"])
def test_absent_selected_key_is_incomplete_and_fingerprinted(field):
    data = enriched()
    del data["reviews"][0][field]
    res = make_v2(data)
    assert_non_authority(res)
    assert res["reason"] == "B_INCOMPLETE_OR_MALFORMED_UNKNOWN"
    assert res["reviews"][0]["selected_field_presence"][field] == "ABSENT"


@pytest.mark.parametrize("field", ["author", "commit", "lastEditedAt"])
def test_explicit_null_and_missing_yield_different_digests(field):
    null = enriched()
    null["reviews"][0][field] = None
    missing = enriched()
    del missing["reviews"][0][field]
    assert make_v2(null)["attribution_digest"] != make_v2(missing)["attribution_digest"]


@pytest.mark.parametrize("actor", [
    {"__typename": "Bot", "login": "bot-without-node-fragment"},
    {"__typename": "Mannequin", "login": "ghost-without-node-fragment"},
    {"__typename": "FutureActor", "login": "future", "id": "X_1"},
    {"__typename": "User", "login": "user", "id": None},
])
def test_non_node_unknown_or_null_actor_identity_stays_unknown(actor):
    data = enriched()
    data["reviews"][0]["author"] = actor
    result = make_v2(data)
    assert_non_authority(result)
    assert result["reason"] == "B_PARTIAL_ATTRIBUTION_UNKNOWN"
    # A future/unknown Actor type may still supply a Node.id, but the
    # type itself is not admitted as known attribution: remain UNKNOWN/HOLD.
    presence = result["reviews"][0]["actor_node_id_presence"]
    assert presence == ("OBSERVED_VALUE" if actor.get("__typename") == "FutureActor"
                        else "EXPLICIT_NULL" if actor.get("id", "ABSENT") is None
                        else "ABSENT")


@pytest.mark.parametrize("field,value", [
    ("commit", {"oid": 4}), ("commit", {"oid": "untrusted"}),
    ("author", {"login": "missing typename"}),
    ("authorAssociation", None), ("lastEditedAt", 5),
])
def test_malformed_selected_fields_still_hashed_but_not_completed(field, value):
    data = enriched()
    data["reviews"][0][field] = value
    result = make_v2(data)
    assert_non_authority(result)
    assert result["reason"] == "B_INCOMPLETE_OR_MALFORMED_UNKNOWN"


def test_decision_looking_login_is_opaque_data_not_authority():
    data = enriched()
    data["reviews"][0]["author"]["login"] = "OK_TO_MERGE"
    res = make_v2(data)
    assert res["reason"] == "B_OBSERVED_NONATTESTED"
    assert_non_authority(res)


def test_authorassociation_none_is_no_authority():
    data = enriched()
    data["reviews"][0]["state"] = "APPROVED"
    data["reviews"][0]["authorAssociation"] = "NONE"
    result = make_v2(data)
    assert_non_authority(result)
    assert result["reviews"][0]["attribution"]["author_association"] == "NONE"


def test_review_set_order_canonicalized_without_rewriting_old_digest():
    a = enriched()
    b = copy.deepcopy(a["reviews"][0])
    b["id"] = "RV_b"
    b["body"] = "second review"
    a["reviews"].append(b)
    reverse = copy.deepcopy(a)
    reverse["reviews"].reverse()
    assert make_v2(a)["attribution_digest"] == make_v2(reverse)["attribution_digest"]
    assert make_capture(a)["evidence"]["reviews"] != make_capture(reverse)["evidence"]["reviews"]


def test_duplicate_review_ids_refused_even_if_graph_caller_bypasses_legacy():
    c = make_capture()
    c["evidence"]["reviews"].append(copy.deepcopy(c["evidence"]["reviews"][0]))
    result = v2.capture_v2(pin(), c)
    assert result["reason"] == "B_DUPLICATE_REVIEW_ID"
    assert result["attribution_digest"] is None
    assert_non_authority(result)


def test_stale_or_mismatched_graph_pin_refused():
    c = make_capture()
    c["pr"]["head_sha"] = "1" * 40
    result = v2.capture_v2(pin(), c)
    assert result["reason"] == "B_MISMATCH_OR_INCOMPLETE_GRAPH_CAPTURE"
    assert result["attribution_digest"] is None
    assert_non_authority(result)


def test_bad_external_pin_refused():
    p = pin()
    p["pr_number"] = True
    res = v2.capture_v2(p, make_capture())
    assert res["reason"] == "B_INVALID_CAPTURE_PIN"
    assert res["attribution_digest"] is None


def test_missing_review_list_refused():
    c = make_capture()
    del c["evidence"]["reviews"]
    res = v2.capture_v2(pin(), c)
    assert res["reason"] == "B_MISMATCH_OR_INCOMPLETE_GRAPH_CAPTURE"


@pytest.mark.parametrize("field,value", [
    ("id", None), ("state", 4), ("body", None),
    ("submittedAt", True), ("updatedAt", []),
])
def test_malformed_legacy_review_fields_fail_closed(field, value):
    c = make_capture()
    c["evidence"]["reviews"][0][field] = value
    res = v2.capture_v2(pin(), c)
    assert res["reason"] == "B_MALFORMED_REVIEW_CAPTURE"
    assert res["attribution_digest"] is None


def test_equal_complete_sample_is_nonattested_hold_only():
    c = make_capture()
    res = v2.compare_v2(pin(), c, copy.deepcopy(c))
    assert_non_authority(res)
    assert res["reason"] == "B_SAMPLES_EQUAL_NONATTESTED"
    assert res["comparison_scope"] == "ATTRIBUTION_SUBSET_ONLY"
    assert res["historical_truth"] == "NOT_ESTABLISHED"


def test_changed_sample_never_emits_stable_claim():
    a, b = make_capture(), make_capture()
    b["evidence"]["reviews"][0]["author"]["login"] = "changed"
    res = v2.compare_v2(pin(), a, b)
    assert_non_authority(res)
    assert res["reason"] == "B_SAMPLES_CHANGED_HOLD"
    assert res["first_attribution_digest"] != res["second_attribution_digest"]


def test_equal_missing_or_null_capture_is_not_complete():
    a = enriched()
    del a["reviews"][0]["authorAssociation"]
    c = make_capture(a)
    res = v2.compare_v2(pin(), c, c)
    assert_non_authority(res)
    assert res["reason"] == "B_SAMPLES_INCOMPLETE_OR_UNKNOWN_HOLD"
    assert res["first_attribution_digest"] == res["second_attribution_digest"]


def test_equal_null_author_is_not_complete():
    a = enriched()
    a["reviews"][0]["author"] = None
    c = make_capture(a)
    res = v2.compare_v2(pin(), c, c)
    assert_non_authority(res)
    assert res["reason"] == "B_SAMPLES_INCOMPLETE_OR_UNKNOWN_HOLD"


def test_empty_review_list_is_diagnostic_not_approval():
    d = enriched()
    d["reviews"] = []
    res = make_v2(d)
    assert res["review_count"] == 0
    assert_non_authority(res)
    assert res["reason"] == "B_OBSERVED_NONATTESTED"


def test_capture_has_no_outbound_network_or_authority_hooks():
    import inspect
    source = inspect.getsource(v2)
    for bad in ("urllib.request", "requests.post", "github_token", "merge_pull",
                "open(", "delete_file("):
        assert bad not in source
