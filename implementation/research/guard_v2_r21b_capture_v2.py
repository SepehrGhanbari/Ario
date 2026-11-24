"""Versioned R21B attribution SUBSET capture, research-only.

This deliberately DOES NOT replace the existing Guard V2 review graph digest,
modify historical fixtures/ledgers, or authenticate any review author.
All observations are HOLD, non-authoritative. No network, token or mutation.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from research import guard_v2_r21b_attribution_lab as attribution

SCHEMA = "ARIO-GUARD-V2-R21B-ATTRIBUTION-SUBSET-LAB-v2"
VERSION = 2
DOMAIN = b"ARIO-GUARD-V2-R21B-ATTRIBUTION-SUBSET-v2\x00"
HASH_ALGORITHM = "SHA256_DOMAIN_SEPARATED_CANONICAL_JSON_V2"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
PIN_KEYS = frozenset({"repository_id", "pr_id", "pr_number", "head_sha", "base_sha"})
SELECTED = ("author", "authorAssociation", "commit", "lastEditedAt")
REVIEW_KEYS = frozenset({"id", "state", "body", "submittedAt", "updatedAt"})


def _hold(reason: str, **more: Any) -> dict[str, Any]:
    return {"schema": SCHEMA, "capture_version": VERSION,
            "disposition": "HOLD", "status": "UNKNOWN",
            "merge_authorized": False, "trust_activated": False,
            "check_publish_authorized": False,
            "execution_attestation": "NOT_ESTABLISHED",
            "independent_custody": "NOT_ESTABLISHED",
            "source_provenance": "SYNTHETIC_OR_CALLER_SUPPLIED_NOT_VERIFIED",
            "reason": reason, **more}


def _pin_ok(pin: Any) -> bool:
    return (type(pin) is dict and set(pin) == PIN_KEYS and
            all(type(pin[key]) is int and pin[key] > 0
                for key in ("repository_id", "pr_id", "pr_number")) and
            all(type(pin[key]) is str and SHA40.fullmatch(pin[key])
                for key in ("head_sha", "base_sha")))


def _field_state(row: dict, name: str) -> str:
    if name not in row:
        return "ABSENT"
    if row[name] is None:
        return "EXPLICIT_NULL"
    return "OBSERVED_VALUE"


def _review_v2(row: Any) -> dict[str, Any] | None:
    if type(row) is not dict or REVIEW_KEYS - row.keys():
        return None
    if (type(row["id"]) is not str or not row["id"] or
        type(row["state"]) is not str or type(row["body"]) is not str or
        type(row["updatedAt"]) is not str or
        (row["submittedAt"] is not None and type(row["submittedAt"]) is not str)):
        return None
    classified = attribution.classify(row)
    # IMPORTANT: this preserves *missing vs explicit null* in the capture
    # commitment, including for the optional Node fragment author.id.
    author = row.get("author")
    actor_id = (("ABSENT" if "id" not in author else
                 "EXPLICIT_NULL" if author["id"] is None else "OBSERVED_VALUE")
                if type(author) is dict else "NOT_APPLICABLE")
    return {
        "review_id": row["id"],
        "state": row["state"],
        "submitted_at": row["submittedAt"],
        "updated_at": row["updatedAt"],
        "body_sha256": hashlib.sha256(row["body"].encode("utf-8")).hexdigest(),
        "selected_field_presence": {key: _field_state(row, key)
                                     for key in SELECTED},
        "actor_node_id_presence": actor_id,
        "attribution_reason": classified["reason"],
        "attribution": classified["attribution"],
    }


def digest_v2(pinned: dict, records: list[dict]) -> str:
    """New domain-separated attribution digest; never an old graph hash."""
    encoded = json.dumps(
        {"capture_schema": SCHEMA, "capture_version": VERSION,
         "scope": pinned, "reviews": records},
        sort_keys=True, ensure_ascii=True, separators=(",", ":"),
        allow_nan=False).encode("utf-8")
    return hashlib.sha256(DOMAIN + encoded).hexdigest()


def capture_v2(pin: Any, graph_capture: Any) -> dict[str, Any]:
    if not _pin_ok(pin):
        return _hold("B_INVALID_CAPTURE_PIN", attribution_digest=None)
    if type(graph_capture) is not dict:
        return _hold("B_MALFORMED_GRAPH_CAPTURE", attribution_digest=None)
    identity = graph_capture.get("pr")
    evidence = graph_capture.get("evidence")
    if (type(identity) is not dict or
        any(identity.get(key) != pin[key] for key in PIN_KEYS) or
        type(evidence) is not dict or type(evidence.get("reviews")) is not list):
        return _hold("B_MISMATCH_OR_INCOMPLETE_GRAPH_CAPTURE",
                     attribution_digest=None)
    records = []
    seen = set()
    for row in evidence["reviews"]:
        record = _review_v2(row)
        if record is None:
            return _hold("B_MALFORMED_REVIEW_CAPTURE", attribution_digest=None)
        if record["review_id"] in seen:
            return _hold("B_DUPLICATE_REVIEW_ID", attribution_digest=None)
        seen.add(record["review_id"])
        records.append(record)
    # Deliberate, explicit V2 canonical order for review SET semantics.
    records.sort(key=lambda item: item["review_id"])
    reasons = {item["attribution_reason"] for item in records}
    if reasons & {"B_CAPTURE_INCOMPLETE", "B_CAPTURE_MALFORMED"}:
        classification = "B_INCOMPLETE_OR_MALFORMED_UNKNOWN"
    elif "B_PARTIAL_ATTRIBUTION_UNKNOWN" in reasons:
        classification = "B_PARTIAL_ATTRIBUTION_UNKNOWN"
    else:
        classification = "B_OBSERVED_NONATTESTED"
    return _hold(classification, capture_scope=pin.copy(),
                 review_count=len(records),
                 commitment_algorithm=HASH_ALGORITHM,
                 attribution_digest=digest_v2(pin, records),
                 reviews=records)


def compare_v2(pin: dict, first: Any, second: Any) -> dict[str, Any]:
    left = capture_v2(pin, first)
    right = capture_v2(pin, second)
    good = "B_OBSERVED_NONATTESTED"
    if left["reason"] != good or right["reason"] != good:
        result = "B_SAMPLES_INCOMPLETE_OR_UNKNOWN_HOLD"
    elif left["attribution_digest"] != right["attribution_digest"]:
        result = "B_SAMPLES_CHANGED_HOLD"
    else:
        result = "B_SAMPLES_EQUAL_NONATTESTED"
    return _hold(result, first_attribution_digest=left.get("attribution_digest"),
                 second_attribution_digest=right.get("attribution_digest"),
                 comparison_scope="ATTRIBUTION_SUBSET_ONLY",
                 historical_truth="NOT_ESTABLISHED")
