"""Synthetic tests for the bounded AEC interchange adapter."""
import pytest

from aec_interchange import MAX_MESSAGE_BYTES, import_aec_message

BASE = {
    "schema_version": "1.0", "message_id": "MSG-1",
    "sender_id": "AGENT-A", "scope": "SYNTHETIC-SCOPE",
    "observation_id": "OBS-1", "source_id": "SRC-1",
    "source_type": "DECLARED_SOURCE", "record_version": "1",
}


def test_valid_message_maps_to_existing_observation_primitive():
    result = import_aec_message(BASE)
    assert result.status == "ACCEPTED_FOR_LOCAL_REVIEW"
    assert result.observation.observation_id == "OBS-1"
    assert result.observation.provenance_refs[0].reference_id == "SRC-1"
    assert result.ancestry_completeness == "UNKNOWN"


def test_declared_parents_are_not_authenticated_ancestry():
    result = import_aec_message({**BASE, "parent_ids": ["MSG-0"]})
    assert result.ancestry_completeness == "DECLARED_ONLY"
    assert result.parent_references[0].reference_id == "MSG-0"
    assert result.source_authentication == "UNKNOWN"


def test_missing_parent_is_unknown_not_proven_root():
    assert import_aec_message(BASE).ancestry_completeness == "UNKNOWN"


@pytest.mark.parametrize("message,reason", [
    ({**BASE, "schema_version": "2.0"}, "UNSUPPORTED_SCHEMA_MAJOR"),
    ({**BASE, "message_id": ""}, "message_id must be a non-empty string"),
    ({**BASE, "extra": "x"}, "UNSUPPORTED_FIELDS"),
    ({**BASE, "parent_ids": "MSG-0"}, "PARENT_IDS_MUST_BE_A_LIST"),
    ({**BASE, "parent_ids": ["MSG-1"]}, "SELF_PARENT_REFERENCE"),
    ({**BASE, "parent_ids": ["MSG-0", "MSG-0"]}, "DUPLICATE_PARENT_REFERENCE"),
])
def test_invalid_messages_fail_closed(message, reason):
    result = import_aec_message(message)
    assert result.status == "REJECTED"
    assert result.reason == reason


def test_replay_check_is_limited_to_caller_supplied_seen_set():
    result = import_aec_message(BASE, seen_message_ids=frozenset({"MSG-1"}))
    assert result.status == "REJECTED"
    assert result.reason == "REPLAYED_MESSAGE_ID"


def test_sender_label_is_not_authenticated():
    result = import_aec_message(BASE)
    assert result.declared_sender_id == "AGENT-A"
    assert result.source_authentication == "UNKNOWN"


def test_message_count_never_becomes_independence_or_truth():
    result = import_aec_message(BASE)
    assert result.evidence_independence == "UNKNOWN"
    assert result.claim_assessment == "UNKNOWN"
    assert result.truth_authority == "NONE"


def test_ten_relay_messages_do_not_become_ten_independent_roots():
    messages = [
        {**BASE, "message_id": f"MSG-{i}", "parent_ids": [f"MSG-{i-1}"]}
        for i in range(1, 11)
    ]
    results = [import_aec_message(item) for item in messages]
    assert len(results) == 10
    assert all(item.evidence_independence == "UNKNOWN" for item in results)
    assert all(item.claim_assessment == "UNKNOWN" for item in results)


def test_oversized_payload_rejected():
    result = import_aec_message({**BASE, "scope": "x" * MAX_MESSAGE_BYTES})
    assert result.status == "REJECTED"
    assert result.reason == "MESSAGE_TOO_LARGE"


def test_non_json_value_rejected():
    result = import_aec_message({**BASE, "scope": object()})
    assert result.status == "REJECTED"
    assert result.reason == "MESSAGE_NOT_JSON_COMPATIBLE"
