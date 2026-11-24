"""R21 B: SYNTHETIC / non-authoritative GraphQL attribution lab only.

Not wired into Guard V2 reader, workflows, signer, checks or merge eligibility.
Research data is never proof of identity, history or independent custody.
This file uses no network or credential and changes no production source.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

SCHEMA = "ARIO-GUARD-V2-R21B-ATTRIBUTION-LAB-0.1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
KNOWN_ACTORS = frozenset({
    "User", "Bot", "Mannequin", "Organization", "EnterpriseUserAccount",
})
# Deliberately use a Node fragment; Actor has no directly selectable id.
# Exact live GraphQL schema validation was NOT performed by this lab.
QUERY_REVIEW_FIELDS = (
    "nodes { id state body submittedAt updatedAt lastEditedAt "
    "authorAssociation author { __typename login ... on Node { id } } "
    "commit { oid } }"
)
B_FIELDS = frozenset({"author", "authorAssociation", "commit", "lastEditedAt"})


def classify(review: Any) -> dict[str, Any]:
    """Classify proposed attribution fields; all results stay UNKNOWN/HOLD.

    Omitted fields differ from explicitly null fields. Never invent a name,
    actor ID, commit, timestamp or reviewer authority.
    """
    result = {
        "schema": SCHEMA,
        "status": "UNKNOWN",
        "disposition": "HOLD",
        "merge_authorized": False,
        "check_publish_authorized": False,
        "trust_activated": False,
        "provenance": "UNVERIFIED_SYNTHETIC_SAMPLE",
        "reason": "B_CAPTURE_MALFORMED",
        "attribution": None,
    }
    if type(review) is not dict:
        return result
    if B_FIELDS - review.keys():
        result["reason"] = "B_CAPTURE_INCOMPLETE"
        return result
    edited, assoc = review["lastEditedAt"], review["authorAssociation"]
    if (edited is not None and type(edited) is not str) or (
        type(assoc) is not str or not assoc
    ):
        return result

    author = review["author"]
    commit = review["commit"]
    if author is not None and type(author) is not dict:
        return result
    if commit is not None and type(commit) is not dict:
        return result

    actor_type, login, node_id = None, None, None
    author_id_present = False
    if author is not None:
        if "__typename" not in author or "login" not in author:
            result["reason"] = "B_CAPTURE_INCOMPLETE"
            return result
        actor_type, login = author["__typename"], author["login"]
        if type(actor_type) is not str or type(login) is not str:
            return result
        author_id_present = "id" in author
        if author_id_present:
            node_id = author["id"]
            if node_id is not None and (type(node_id) is not str or not node_id):
                return result

    commit_oid = None
    if commit is not None:
        if "oid" not in commit:
            result["reason"] = "B_CAPTURE_INCOMPLETE"
            return result
        commit_oid = commit["oid"]
        if type(commit_oid) is not str or SHA40.fullmatch(commit_oid) is None:
            return result

    result["attribution"] = {
        "actor_type": actor_type,
        "login": login,
        "node_id": node_id,
        "node_id_observed": author_id_present,
        "author_association": assoc,
        "commit_oid": commit_oid,
        "last_edited_at": edited,
    }
    # A null author/commit, unrecognized Actor subtype, or absent Node.id is
    # partially observed (UNKNOWN), not a forged identity nor a failed merge.
    result["reason"] = (
        "B_PARTIAL_ATTRIBUTION_UNKNOWN" if
        (author is None or commit is None or actor_type not in KNOWN_ACTORS
         or not login or not node_id)
        else "B_CAPTURE_COMPLETE_NON_ATTESTED"
    )
    return result


def synthetic_compare(left: Any, right: Any) -> dict[str, Any]:
    """Compare only this lab's normalized observations, never historical truth."""
    a, b = classify(left), classify(right)

    def digest(value):
        raw = json.dumps(value, sort_keys=True, ensure_ascii=True,
                         separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    return {
        "schema": SCHEMA,
        "disposition": "HOLD",
        "merge_authorized": False,
        "trust_activated": False,
        "first_digest": digest(a),
        "second_digest": digest(b),
        "sample_status": "SYNTHETIC_EQUAL_UNATTESTED" if a == b
                         else "SYNTHETIC_CHANGED_HOLD",
    }
