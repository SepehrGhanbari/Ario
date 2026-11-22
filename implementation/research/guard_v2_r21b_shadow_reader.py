"""R21B shadow-only reader adapter; legacy V1 contracts stay unchanged.

Opt-in, read-only research. Never import this into a required check, signer,
trusted reader, merge job, or historical ledger. No trust/identity attestation.

Design: the *real* V1 graph.compare_twice uses a projection of exactly the
same bounded B-enriched network pages. The raw pages are replayed IN MEMORY
through the *real* V1 graph.capture into the separate V2 attribution contract.
No second network observation is represented as the same sample.
"""
from __future__ import annotations

import copy
import hashlib
import http.client
import json
import urllib.error
import urllib.request
from typing import Any

from research import guard_v2_pr_scope as guard
from research import guard_v2_review_graph as v1
from research import guard_v2_r21b_capture_v2 as v2

SCHEMA = "ARIO-GUARD-V2-R21B-SHADOW-DUAL-READ-LAB-0.1"
V2_FIELDS = frozenset({"author", "authorAssociation", "commit", "lastEditedAt"})
V1_FIELDS = frozenset({"id", "state", "body", "submittedAt", "updatedAt"})
OLD_REVIEW_SELECTION = "nodes { id state body submittedAt updatedAt }"
NEW_REVIEW_SELECTION = (
    "nodes { id state body submittedAt updatedAt lastEditedAt "
    "authorAssociation author { __typename login ... on Node { id } } "
    "commit { oid } }"
)

# Verify the pinned V1 query shape. No mutation of the global V1 query table.
if v1._FIELDS["reviews"].count(OLD_REVIEW_SELECTION) != 1:
    raise RuntimeError("SHADOW_UNEXPECTED_V1_QUERY")
REVIEW_B_QUERY = (
    v1._QUERY_HEADER
    + v1._FIELDS["reviews"].replace(OLD_REVIEW_SELECTION, NEW_REVIEW_SELECTION)
    + "\n" + v1._QUERY_TAIL
)
REVIEW_B_QUERY_SHA256 = hashlib.sha256(REVIEW_B_QUERY.encode("utf-8")).hexdigest()
assert REVIEW_B_QUERY.startswith("query ArioReviewEvidence")
assert "mutation " not in REVIEW_B_QUERY.lower()


class ReadOnlyGraphQLB(v1.ReadOnlyGraphQL):
    """Fixed B review query; V1 comments/threads use unmodified V1 transport.

    Auth token stays in inherited in-memory private field; no logging, disk or
    artifact writes here. All requests are GraphQL queries, never mutations.
    """

    def get_page(self, kind: str, number: int, cursor: str | None) -> dict:
        if kind != "reviews":
            return super().get_page(kind, number, cursor)
        v1.require(guard.positive(number), "INVALID_GRAPHQL_TARGET")
        v1.require(cursor is None or
                   (type(cursor) is str and 0 < len(cursor) <= 1024),
                   "INVALID_PAGE_CURSOR")
        payload = json.dumps(
            {"query": REVIEW_B_QUERY,
             "variables": {"owner": v1.OWNER, "repo": v1.REPO,
                           "number": number, "cursor": cursor}},
            separators=(",", ":")).encode("utf-8")
        req = urllib.request.Request(v1.API, data=payload, method="POST",
                                     headers={
                                         "Authorization": "Bearer " + self._token,
                                         "Accept": "application/vnd.github+json",
                                         "Content-Type": "application/json",
                                         "X-GitHub-Api-Version": "2022-11-28",
                                         "User-Agent": "Ario-R21B-Shadow-ReadOnly-Research",
                                     })
        try:
            with self._opener.open(req, timeout=12) as response:
                v1.require(response.status == 200, "GRAPHQL_HTTP_NOT_200")
                raw = response.read(v1.MAX_RESPONSE_BYTES + 1)
                v1.require(len(raw) <= v1.MAX_RESPONSE_BYTES,
                           "GRAPHQL_RESPONSE_TOO_LARGE")
        except urllib.error.HTTPError as exc:
            raise v1.ReviewGraphUnknown("GRAPHQL_HTTP_" + str(exc.code)) from exc
        except (OSError, urllib.error.URLError, TimeoutError,
                http.client.HTTPException) as exc:
            raise v1.ReviewGraphUnknown("GRAPHQL_NETWORK_UNKNOWN") from exc
        try:
            parsed = guard.strict_json(raw)
        except guard.EvidenceError as exc:
            raise v1.ReviewGraphUnknown("MALFORMED_GRAPHQL_JSON") from exc
        v1.require(type(parsed) is dict, "MALFORMED_GRAPHQL_ENVELOPE")
        return parsed


def _project_v1(page: Any, kind: str) -> Any:
    """Strip only proposed B fields, never rewrite V1 historical artifacts."""
    old = copy.deepcopy(page)
    if kind != "reviews" or type(old) is not dict:
        return old
    payload = old.get("data")
    if type(payload) is not dict:
        return old
    repo = payload.get("repository")
    pr = repo.get("pullRequest") if type(repo) is dict else None
    conn = pr.get("reviews") if type(pr) is dict else None
    nodes = conn.get("nodes") if type(conn) is dict else None
    if type(nodes) is not list:
        return old
    for node in nodes:
        if type(node) is not dict:
            continue  # legacy V1 _node will reject malformed entries
        unexpected = set(node) - V1_FIELDS - V2_FIELDS
        if unexpected:
            raise v1.ReviewGraphUnknown("SHADOW_UNEXPECTED_REVIEW_FIELD")
        for key in V2_FIELDS:
            node.pop(key, None)
    return old


class V1ProjectionRecorder:
    """Records only the actual pages V1 consumed, then provides a V1 view."""

    def __init__(self, enriched_reader: Any):
        self.reader = enriched_reader
        self.pages: list[tuple[str, int, str | None, Any]] = []

    def get_page(self, kind: str, number: int, cursor: str | None) -> Any:
        # V1 capture bounds per kind, per iteration. Our global budget is
        # at most 2 captures x 3 kinds x 12 bounded pages.
        if len(self.pages) >= 2 * 3 * v1.MAX_PAGES:
            raise v1.ReviewGraphUnknown("SHADOW_REPLAY_BUDGET_EXCEEDED")
        page = self.reader.get_page(kind, number, cursor)
        # One snapshot of the externally supplied page is the common source of
        # BOTH the V1 projection and the raw V2 replay. Previously independent
        # deepcopies of the caller object could observe different values if it
        # was mutated between them (reproduced by R21B race falsifier).
        snapshot = copy.deepcopy(page)
        projected = _project_v1(snapshot, kind)  # can fail before recording
        self.pages.append((kind, number, cursor, snapshot))
        return projected


class ReplayInMemory:
    """Replays the SAME captured pages to V1 graph.capture without network."""

    def __init__(self, pages: list):
        self.pages = pages
        self.index = 0

    def get_page(self, kind: str, number: int, cursor: str | None) -> Any:
        if self.index >= len(self.pages):
            raise v1.ReviewGraphUnknown("SHADOW_REPLAY_EXHAUSTED")
        k, n, c, page = self.pages[self.index]
        if (kind, number, cursor) != (k, n, c):
            raise v1.ReviewGraphUnknown("SHADOW_REPLAY_CALL_MISMATCH")
        self.index += 1
        return copy.deepcopy(page)

    def assert_exhausted(self) -> None:
        if self.index != len(self.pages):
            raise v1.ReviewGraphUnknown("SHADOW_REPLAY_UNUSED_PAGES")


def _hold(reason: str, **more: Any) -> dict:
    return {
        "schema": SCHEMA,
        "status": "UNKNOWN", "disposition": "HOLD", "reason": reason,
        "merge_authorized": False, "check_publish_authorized": False,
        "trust_activated": False, "execution_attestation": "NOT_ESTABLISHED",
        "independent_custody": "NOT_ESTABLISHED",
        "historical_truth": "NOT_ESTABLISHED",
        "source_provenance": "CALLER_SUPPLIED_OR_EPHEMERAL_NOT_INDEPENDENTLY_VERIFIED",
        "v1_implementation_modified": False,
        "historical_ledger_modified": False,
        **more,
    }


def compare_shadow(pin: dict, enriched_reader: Any) -> dict:
    """Two original V1 captures, one network sampling sequence, V2 replay.

    Preserve V1 exactly as returned by graph.compare_twice on B-field-stripped
    pages. The new contract is strictly an additional diagnostic. V2 never
    turns a V1 failure into success, and neither can authorize anything.
    Return only digests/status/reasons, never review content or actor IDs.
    """
    recorder = V1ProjectionRecorder(enriched_reader)
    try:
        v1_result = v1.compare_twice(pin, recorder)  # unchanged REAL V1 path
    except (TypeError, ValueError, KeyError, OSError, RecursionError,
            OverflowError):
        return _hold("SHADOW_V1_COMPARISON_UNKNOWN", v1=None, v2=None)

    # Preserve V1 result byte-for-byte as a dictionary. It must not acquire
    # keys from V2, even if the same reviewer appeared in the enriched pages.
    if v1_result.get("sample_status") != "SAMPLED_STABLE_UNATTESTED":
        return _hold("SHADOW_V1_FAILED_OR_CHANGED",
                     v1=v1_result, v2=None,
                     recorded_page_count=len(recorder.pages))
    try:
        replay = ReplayInMemory(recorder.pages)
        first = v1.capture(pin, replay)
        second = v1.capture(pin, replay)
        replay.assert_exhausted()
        v2_result = v2.compare_v2(pin, first, second)
    except (v1.ReviewGraphUnknown, guard.EvidenceError, KeyError,
            TypeError, ValueError, OSError, RecursionError, OverflowError):
        return _hold("SHADOW_V2_REPLAY_UNKNOWN",
                     v1=v1_result, v2=None,
                     recorded_page_count=len(recorder.pages))

    # In particular, a V2 digest mismatch does not rewrite a V1 digest:
    # V1 can report stable old fields while V2 detects attribution drift.
    return _hold("SHADOW_DUAL_CAPTURE_HOLD",
                 v1=v1_result, v2=v2_result,
                 recorded_page_count=len(recorder.pages),
                 v1_contract="UNCHANGED_V1_PROJECTED_QUERY",
                 v2_contract=v2.SCHEMA,
                 source_sampling="SAME_B_ENRICHED_PAGES_REPLAYED_IN_MEMORY")
