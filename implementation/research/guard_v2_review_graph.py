"""Bounded read-only GitHub review-graph observer for Ario Guard V2 research.

Only fixed GraphQL *query* operations; GraphQL HTTP POST is a transport, NOT
a GitHub mutation. Does not write Checks, merge PRs or attest independent custody.
NEVER execute this PR-controlled module with a privileged publisher credential.
"""
from __future__ import annotations

import hashlib
import http.client
import json
import re
import ssl
import urllib.error
import urllib.request
from typing import Any

from research import guard_v2_pr_scope as guard

SCHEMA = "ARIO-GUARD-V2-REVIEW-GRAPH-LAB-0.1"
API = "https://api.github.com/graphql"
OWNER = "SepehrGhanbari"
REPO = "Ario"
PAGE_SIZE = 100
MAX_PAGES = 12
MAX_ITEMS = 1200
MAX_RESPONSE_BYTES = 400_000
SHA = re.compile(r"[0-9a-f]{40}\Z")

# Query text is compiled in, not derived from untrusted PR input.
# BigInt fullDatabaseId avoids GitHub's deprecated 32-bit databaseId field.
_QUERY_HEADER = """query ArioReviewEvidence($owner:String!,$repo:String!,$number:Int!,$cursor:String) {
  repository(owner:$owner,name:$repo) {
    fullDatabaseId
    pullRequest(number:$number) {
      fullDatabaseId number headRefOid baseRefOid state isDraft
"""
_QUERY_TAIL = """    }
  }
}"""
_FIELDS = {
    "comments": """comments(first:100,after:$cursor) {
        totalCount pageInfo { hasNextPage endCursor }
        nodes { id body createdAt updatedAt }
      }""",
    "reviews": """reviews(first:100,after:$cursor) {
        totalCount pageInfo { hasNextPage endCursor }
        nodes { id state body submittedAt updatedAt }
      }""",
    "threads": """reviewThreads(first:100,after:$cursor) {
        totalCount pageInfo { hasNextPage endCursor }
        nodes {
          id isResolved isOutdated path
          comments(first:100) {
            totalCount pageInfo { hasNextPage endCursor }
            nodes { id body updatedAt }
          }
        }
      }""",
}
QUERIES = {kind: _QUERY_HEADER + field + "\n" + _QUERY_TAIL
           for kind, field in _FIELDS.items()}


class ReviewGraphUnknown(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ReviewGraphUnknown(reason)


def _int_id(value: Any) -> int:
    # GraphQL BigInt may be returned as a JSON integer or decimal string.
    if type(value) is int and value > 0:
        return value
    if (isinstance(value, str) and len(value) <= 20 and
            value.isascii() and value.isdecimal() and
            value[0] != "0" and int(value) > 0):
        return int(value)
    raise ReviewGraphUnknown("MALFORMED_BIGINT_ID")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class ReadOnlyGraphQL:
    """Authenticated TLS GraphQL query transport with fixed query templates."""

    def __init__(self, token: str):
        require(isinstance(token, str) and bool(token.strip()),
                "MISSING_READ_ONLY_TOKEN")
        self._token = token
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            _NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        )

    def get_page(self, kind: str, number: int, cursor: str | None) -> dict:
        require(kind in QUERIES and guard.positive(number), "INVALID_GRAPHQL_TARGET")
        require(cursor is None or (isinstance(cursor, str) and bool(cursor) and
                                  len(cursor) <= 1024), "INVALID_PAGE_CURSOR")
        # HTTP POST carries a GraphQL *query*. No mutations or caller-generated
        # GraphQL documents are accepted.
        payload = json.dumps({
            "query": QUERIES[kind],
            "variables": {"owner": OWNER, "repo": REPO,
                          "number": number, "cursor": cursor},
        }, separators=(",", ":")).encode("utf-8")
        req = urllib.request.Request(API, data=payload, method="POST", headers={
            "Authorization": "Bearer " + self._token,
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Ario-Review-Graph-ReadOnly-Research",
        })
        try:
            with self._opener.open(req, timeout=12) as response:
                require(response.status == 200, "GRAPHQL_HTTP_NOT_200")
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                require(len(raw) <= MAX_RESPONSE_BYTES, "GRAPHQL_RESPONSE_TOO_LARGE")
        except urllib.error.HTTPError as exc:
            raise ReviewGraphUnknown("GRAPHQL_HTTP_" + str(exc.code)) from exc
        except (OSError, urllib.error.URLError, TimeoutError,
                http.client.HTTPException) as exc:
            raise ReviewGraphUnknown("GRAPHQL_NETWORK_UNKNOWN") from exc
        try:
            parsed = guard.strict_json(raw)
        except guard.EvidenceError as exc:
            raise ReviewGraphUnknown("MALFORMED_GRAPHQL_JSON") from exc
        require(isinstance(parsed, dict), "MALFORMED_GRAPHQL_ENVELOPE")
        return parsed


def _identity(root: dict, pin: dict) -> dict:
    repo = root.get("repository")
    require(isinstance(repo, dict), "REPOSITORY_NOT_VISIBLE")
    pr = repo.get("pullRequest")
    require(isinstance(pr, dict), "PULL_REQUEST_NOT_VISIBLE")
    require(_int_id(repo.get("fullDatabaseId")) == pin["repository_id"]
            and _int_id(pr.get("fullDatabaseId")) == pin["pr_id"]
            and type(pr.get("number")) is int and pr["number"] == pin["pr_number"],
            "GRAPH_PR_IDENTITY_MISMATCH")
    require(pr.get("headRefOid") == pin["head_sha"]
            and pr.get("baseRefOid") == pin["base_sha"],
            "GRAPH_PR_REVISION_CHANGED")
    require(pr.get("state") in ("OPEN", "CLOSED", "MERGED") and
            type(pr.get("isDraft")) is bool, "INVALID_GRAPH_PR_STATE")
    return {"repository_id": pin["repository_id"], "pr_id": pin["pr_id"],
            "pr_number": pin["pr_number"], "head_sha": pr["headRefOid"],
            "base_sha": pr["baseRefOid"], "state": pr["state"],
            "draft": pr["isDraft"]}


def _node(kind: str, item: Any) -> dict:
    require(isinstance(item, dict) and isinstance(item.get("id"), str)
            and bool(item["id"]), "INVALID_GRAPH_NODE")
    if kind == "comments":
        require(isinstance(item.get("body"), str) and
                isinstance(item.get("updatedAt"), str) and
                isinstance(item.get("createdAt"), str),
                "INVALID_ISSUE_COMMENT")
    elif kind == "reviews":
        require(isinstance(item.get("body"), str) and
                isinstance(item.get("state"), str) and
                isinstance(item.get("updatedAt"), str) and
                (item.get("submittedAt") is None or
                 isinstance(item["submittedAt"], str)),
                "INVALID_REVIEW")
    else:
        require(type(item.get("isResolved")) is bool and
                type(item.get("isOutdated")) is bool and
                isinstance(item.get("path"), str),
                "INVALID_THREAD_STATE")
        inner = item.get("comments")
        require(isinstance(inner, dict) and type(inner.get("totalCount")) is int and
                isinstance(inner.get("nodes"), list) and
                len(inner["nodes"]) == inner["totalCount"] and
                0 <= inner["totalCount"] <= PAGE_SIZE and
                isinstance(inner.get("pageInfo"), dict) and
                inner["pageInfo"].get("hasNextPage") is False,
                "INCOMPLETE_THREAD_REPLIES")
        ids = set()
        for reply in inner["nodes"]:
            require(isinstance(reply, dict) and
                    isinstance(reply.get("id"), str) and
                    bool(reply["id"]) and reply["id"] not in ids and
                    isinstance(reply.get("body"), str) and
                    isinstance(reply.get("updatedAt"), str),
                    "INVALID_OR_DUPLICATE_THREAD_REPLY")
            ids.add(reply["id"])
    return item


def capture(pin: dict, reader: Any) -> dict:
    """Read all bounded pages. Any missing/unstable response fails closed."""
    guard._validate_pin({**pin, "review_digest": pin.get("review_digest", "0" * 64)})
    identity = None
    result = {}
    for kind, field in (("comments", "comments"), ("reviews", "reviews"),
                        ("threads", "reviewThreads")):
        seen_cursors = set()
        seen_ids = set()
        nodes = []
        total = None
        cursor = None
        for _ in range(MAX_PAGES):
            page = reader.get_page(kind, pin["pr_number"], cursor)
            require(isinstance(page, dict) and not page.get("errors"),
                    "GRAPHQL_ERROR_OR_MISSING_PAGE")
            payload = page.get("data")
            require(isinstance(payload, dict), "GRAPHQL_DATA_MISSING")
            current = _identity(payload, pin)
            if identity is not None:
                require(identity == current, "IDENTITY_CHANGED_DURING_PAGINATION")
            identity = current
            # These are native GitHub GraphQL connections with pageInfo, not
            # arbitrarily chosen subsets supplied by a PR.
            conn = payload["repository"]["pullRequest"].get(field)
            require(isinstance(conn, dict) and isinstance(conn.get("pageInfo"), dict)
                    and isinstance(conn.get("nodes"), list) and
                    type(conn.get("totalCount")) is int and
                    0 <= conn["totalCount"] <= MAX_ITEMS,
                    "MALFORMED_GRAPH_CONNECTION")
            count = conn["totalCount"]
            require(total is None or total == count, "GRAPH_TOTAL_CHANGED_DURING_PAGES")
            total = count
            page_nodes = conn["nodes"]
            require(len(page_nodes) <= PAGE_SIZE, "GRAPH_PAGE_TOO_LARGE")
            for item in page_nodes:
                node = _node(kind, item)
                require(node["id"] not in seen_ids, "DUPLICATE_GRAPH_NODE_ID")
                seen_ids.add(node["id"])
                nodes.append(node)
            require(len(nodes) <= MAX_ITEMS, "GRAPH_COLLECTION_OVERFLOW")
            info = conn["pageInfo"]
            require(type(info.get("hasNextPage")) is bool,
                    "MALFORMED_GRAPH_PAGE_INFO")
            if info["hasNextPage"] is False:
                require(len(nodes) == total, "INCOMPLETE_GRAPH_COLLECTION")
                result[kind] = nodes
                break
            nxt = info.get("endCursor")
            require(isinstance(nxt, str) and bool(nxt) and
                    len(nxt) <= 1024 and nxt != cursor and
                    nxt not in seen_cursors and bool(page_nodes),
                    "INVALID_OR_REPEATED_GRAPH_CURSOR")
            seen_cursors.add(nxt)
            cursor = nxt
        else:
            raise ReviewGraphUnknown("MAX_GRAPH_PAGES_EXCEEDED")
    return {"pr": identity, "evidence": result}


def compare_twice(pin: dict, reader: Any) -> dict:
    """Two complete samples; never treats a stable response as merge approval."""
    out = {"schema": SCHEMA, "disposition": "HOLD", "merge_authorized": False,
           "check_publish_authorized": False, "trust_activated": False,
           "execution_attestation": "NOT_ESTABLISHED",
           "independent_custody": "NOT_ESTABLISHED",
           "sample_status": "UNKNOWN", "reason": "UNASSESSED"}
    try:
        first = capture(pin, reader)
        second = capture(pin, reader)
        first_sha = hashlib.sha256(guard.canonical(first)).hexdigest()
        second_sha = hashlib.sha256(guard.canonical(second)).hexdigest()
        out["first_digest"] = first_sha
        out["second_digest"] = second_sha
        require(first_sha == second_sha and
                guard.canonical(first) == guard.canonical(second),
                "REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES")
        out.update(sample_status="SAMPLED_STABLE_UNATTESTED",
                   reason="TWO_COMPLETE_GRAPH_SAMPLES_MATCH")
    except (ReviewGraphUnknown, guard.EvidenceError, KeyError, TypeError,
            ValueError, OSError, OverflowError, RecursionError) as exc:
        out["reason"] = (str(exc) if isinstance(exc, ReviewGraphUnknown)
                         else "MALFORMED_OR_UNAVAILABLE_GRAPH")
    return out
