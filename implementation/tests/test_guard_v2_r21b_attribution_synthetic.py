"""Synthetic R21 B attribution controls on the REAL pinned Guard V2 graph reader.

Proves only properties of faked GraphQL pages and a separate lab classifier.
Neither test nor classifier is a trust signal or a live API-schema attestation.
"""
from __future__ import annotations

import copy

import pytest
from research import guard_v2_review_graph as graph
from research import guard_v2_r21b_attribution_lab as lab
from test_guard_v2_review_graph import FakeGraphQL, original, pin

SHA = "d" * 40


def enriched():
    sample = original()
    sample["reviews"][0].update({
        "author": {"__typename": "User", "login": "alice", "id": "U_1"},
        "authorAssociation": "NONE",
        "commit": {"oid": SHA},
        "lastEditedAt": None,
    })
    return sample


def review():
    return copy.deepcopy(enriched()["reviews"][0])


def assert_hold(v):
    assert v["disposition"] == "HOLD"
    assert v["merge_authorized"] is False
    assert v["trust_activated"] is False


def test_query_uses_optional_node_fragment_not_illegal_direct_actor_id():
    assert "author { __typename login ... on Node { id } }" in lab.QUERY_REVIEW_FIELDS
    assert "author { __typename login id }" not in lab.QUERY_REVIEW_FIELDS


def test_human_with_full_visible_observation_is_never_authorized():
    r = review()
    r["state"] = "APPROVED"
    observed = lab.classify(r)
    assert_hold(observed)
    assert observed["reason"] == "B_CAPTURE_COMPLETE_NON_ATTESTED"
    assert observed["attribution"]["author_association"] == "NONE"


def test_bot_with_node_id_remains_non_authoritative():
    r = review()
    r["author"] = {"__typename": "Bot", "login": "ci-bot", "id": "BOT_1"}
    assert lab.classify(r)["reason"] == "B_CAPTURE_COMPLETE_NON_ATTESTED"
    assert_hold(lab.classify(r))


@pytest.mark.parametrize("field", ["author", "commit"])
def test_explicit_null_is_unknown_not_incomplete(field):
    r = review()
    r[field] = None
    diagnostic = lab.classify(r)
    assert_hold(diagnostic)
    assert diagnostic["reason"] == "B_PARTIAL_ATTRIBUTION_UNKNOWN"
    assert diagnostic["attribution"] is not None


@pytest.mark.parametrize("field", ["author", "commit", "lastEditedAt", "authorAssociation"])
def test_omitted_selected_field_is_incomplete_not_silent_null(field):
    r = review()
    del r[field]
    diagnostic = lab.classify(r)
    assert_hold(diagnostic)
    assert diagnostic["reason"] == "B_CAPTURE_INCOMPLETE"
    assert diagnostic["attribution"] is None


@pytest.mark.parametrize("value", [
    {"__typename": "Mannequin", "login": "ghost"},
    {"__typename": "EnterpriseUserAccount", "login": "enterprise"},
    {"__typename": "Bot", "login": "ci-bot"},
    {"__typename": "FutureActorSubtype", "login": "unknown", "id": "X_1"},
    {"__typename": "User", "login": "", "id": "U_1"},
])
def test_missing_node_fragment_or_unknown_actor_type_is_unknown(value):
    r = review()
    r["author"] = value
    diagnostic = lab.classify(r)
    assert_hold(diagnostic)
    assert diagnostic["reason"] == "B_PARTIAL_ATTRIBUTION_UNKNOWN"


@pytest.mark.parametrize("field,value", [
    ("author", []),
    ("author", {"__typename": "User"}),
    ("commit", []),
    ("commit", {"oid": "invalid-sha"}),
    ("commit", {"oid": 7}),
    ("authorAssociation", None),
    ("lastEditedAt", 12),
])
def test_invalid_or_malformed_attribution_never_succeeds(field, value):
    r = review()
    r[field] = value
    diagnostic = lab.classify(r)
    assert_hold(diagnostic)
    assert diagnostic["reason"] in ("B_CAPTURE_MALFORMED", "B_CAPTURE_INCOMPLETE")


def test_username_that_looks_like_a_decision_is_still_only_data():
    r = review()
    r["author"]["login"] = "OK_TO_MERGE"
    diagnostic = lab.classify(r)
    assert_hold(diagnostic)
    assert diagnostic["reason"] == "B_CAPTURE_COMPLETE_NON_ATTESTED"


@pytest.mark.parametrize("field,value", [
    ("author", {"__typename": "User", "login": "bob", "id": "U_1"}),
    ("authorAssociation", "COLLABORATOR"),
    ("commit", {"oid": "e" * 40}),
    ("lastEditedAt", "2026-11-22T01:00:00Z"),
])
def test_lab_digest_changes_when_attribution_changes(field, value):
    left, right = review(), review()
    right[field] = value
    comparison = lab.synthetic_compare(left, right)
    assert_hold(comparison)
    assert comparison["first_digest"] != comparison["second_digest"]
    assert comparison["sample_status"] == "SYNTHETIC_CHANGED_HOLD"


def test_lab_equal_samples_are_not_identity_or_history_proof():
    item = review()
    comparison = lab.synthetic_compare(item, copy.deepcopy(item))
    assert_hold(comparison)
    assert comparison["first_digest"] == comparison["second_digest"]
    assert comparison["sample_status"] == "SYNTHETIC_EQUAL_UNATTESTED"


def test_real_graph_unchanged_sample_with_new_fields_still_non_authoritative():
    r = FakeGraphQL(enriched())
    result = graph.compare_twice(pin(), r)
    assert result["sample_status"] == "SAMPLED_STABLE_UNATTESTED"
    assert result["first_digest"] == result["second_digest"]
    assert result["merge_authorized"] is False
    assert result["independent_custody"] == "NOT_ESTABLISHED"
    assert len(r.calls) == 6


def test_real_graph_digest_version_changes_when_fields_are_added():
    old = graph.compare_twice(pin(), FakeGraphQL(original()))
    new = graph.compare_twice(pin(), FakeGraphQL(enriched()))
    assert old["first_digest"] != new["first_digest"]
    assert old["merge_authorized"] is False
    assert new["merge_authorized"] is False


@pytest.mark.parametrize("field,value", [
    ("author", {"__typename": "User", "login": "bob", "id": "U_1"}),
    ("commit", {"oid": "e" * 40}),
    ("authorAssociation", "MEMBER"),
    ("lastEditedAt", "2026-11-22T01:00:00Z"),
])
def test_real_graph_detects_changed_b_fields_between_two_samples(field, value):
    left = enriched()
    right = copy.deepcopy(left)
    right["reviews"][0][field] = value
    result = graph.compare_twice(pin(), FakeGraphQL(left, right))
    assert result["sample_status"] == "UNKNOWN"
    assert result["reason"] == "REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES"
    assert_hold(result)


def test_real_graph_baseline_does_not_validate_missing_new_b_fields():
    # IMPORTANT DESIGN FINDING: adding GraphQL fields alone is insufficient.
    # The legacy _node schema only knows old review keys and therefore accepts
    # synthetically absent B fields as a stable sample. The proposed lab policy
    # identifies them as incomplete. This is NOT a current R21 A regression.
    left = enriched()
    del left["reviews"][0]["authorAssociation"]
    old = graph.compare_twice(pin(), FakeGraphQL(left))
    new = lab.classify(left["reviews"][0])
    assert old["sample_status"] == "SAMPLED_STABLE_UNATTESTED"
    assert new["reason"] == "B_CAPTURE_INCOMPLETE"
    assert_hold(old)
    assert_hold(new)


def test_real_graph_baseline_null_actor_is_stable_not_identity_proof():
    left = enriched()
    left["reviews"][0]["author"] = None
    old = graph.compare_twice(pin(), FakeGraphQL(left))
    new = lab.classify(left["reviews"][0])
    assert old["sample_status"] == "SAMPLED_STABLE_UNATTESTED"
    assert new["reason"] == "B_PARTIAL_ATTRIBUTION_UNKNOWN"
    assert_hold(old)
    assert_hold(new)
