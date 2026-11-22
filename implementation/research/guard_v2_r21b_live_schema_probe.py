"""Ephemeral READ-ONLY GitHub GraphQL schema probe for Ario R21 Patch B.

Run only on the isolated research branch with GitHub Actions' ephemeral token
restricted to repository READ permissions. No mutations and no login/node IDs
or review bodies in output. This is not an independent provenance attestation.
"""
from __future__ import annotations
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

SCHEMA_QUERY = """query ArioR21BTypes {
  review: __type(name:"PullRequestReview") {
    fields { name type { kind name ofType { kind name } } }
  }
  actor: __type(name:"Actor") {
    fields { name type { kind name } }
    possibleTypes { name }
  }
}"""

# GitHub enforces a small introspection-selection reuse limit. Split the four
# types into TWO queries to keep __Type.fields selection count <= 2 per call.
SECOND_SCHEMA_QUERY = """query ArioR21BNodeCommitTypes {
  node: __type(name:"Node") { fields { name } }
  commit: __type(name:"Commit") { fields { name } }
}"""

# Byte-level review-node field selection from the original submitted Patch B.
REVIEW_QUERY = """query ArioR21BExactReviewFields($owner:String!,$repo:String!,$number:Int!) {
  repository(owner:$owner,name:$repo) {
    pullRequest(number:$number) {
      reviews(first:5) {
        totalCount
        nodes {
          id state body submittedAt updatedAt lastEditedAt authorAssociation
          author { __typename login ... on Node { id } }
          commit { oid }
        }
      }
    }
  }
}"""

URL = "https://api.github.com/graphql"
MAX_BYTES = 400_000


def post(token: str, query: str, variables: dict | None = None) -> dict:
    payload = json.dumps({"query": query, "variables": variables or {}},
                         separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(URL, data=payload, method="POST", headers={
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Ario-R21B-Research-Schema-ReadOnly",
    })
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("OVERSIZED_GRAPHQL_RESPONSE")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("MALFORMED_GRAPHQL_ENVELOPE")
    return value


def field_map(type_obj: dict | None) -> dict:
    if not isinstance(type_obj, dict) or not isinstance(type_obj.get("fields"), list):
        return {}
    return {f["name"]: f.get("type") for f in type_obj["fields"]
            if isinstance(f, dict) and isinstance(f.get("name"), str)}


def type_repr(t: dict | None) -> str:
    if not isinstance(t, dict):
        return "UNKNOWN"
    if t.get("kind") == "NON_NULL":
        return type_repr(t.get("ofType")) + "!"
    return str(t.get("name") or t.get("kind") or "UNKNOWN")


def report(status: str, **details) -> int:
    # No tokens, actor logins/IDs or review contents are logged.
    data = {"schema": "ARIO-R21B-LIVE-GRAPHQL-PROBE-0.1",
            "status": status, "disposition": "HOLD",
            "merge_authorized": False, "trust_activated": False,
            "provenance": "GITHUB_ACTIONS_SELF_REPORTED_NOT_INDEPENDENT",
            **details}
    print("ARIO_R21B_LIVE_PROBE " + json.dumps(data, sort_keys=True))
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fp:
            fp.write("### R21B read-only GraphQL live schema probe\n\n")
            fp.write("Status: " + status + " — HOLD / NO_MERGE\n\n")
            fp.write(json.dumps(data, sort_keys=True, indent=2) + "\n")
    return 0 if status == "SCHEMA_AND_QUERY_VERIFIED_NON_AUTHORITATIVE" else 2


def safe_graphql_error_kinds(errors: object) -> list[str]:
    """Classify errors without emitting messages that might contain user data."""
    kinds = []
    for item in errors if isinstance(errors, list) else []:
        msg = str(item.get("message", "")).lower() if isinstance(item, dict) else ""
        if "resource not accessible" in msg or "permission" in msg:
            kinds.append("PERMISSION_OR_SCOPE")
        elif "doesn't exist" in msg or "cannot query field" in msg or "undefinedfield" in msg:
            kinds.append("INVALID_FIELD_OR_SCHEMA")
        elif "introspection" in msg or "__type" in msg:
            kinds.append("INTROSPECTION_RELATED")
        elif "could not resolve" in msg or "not found" in msg:
            kinds.append("RESOURCE_NOT_VISIBLE")
        elif "rate limit" in msg:
            kinds.append("RATE_LIMIT")
        elif "variable" in msg or "argument" in msg:
            kinds.append("QUERY_ARGUMENT_ERROR")
        else:
            kinds.append("UNCLASSIFIED_GRAPHQL_ERROR")
    return sorted(set(kinds))


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return report("NO_EPHEMERAL_TOKEN")
    try:
        # Validate the EXACT proposed field selection even when the token
        # cannot introspect schema types. Never assume introspection access.
        exact = post(token, REVIEW_QUERY, {"owner": "SepehrGhanbari",
                                          "repo": "Ario", "number": 295})
        if exact.get("errors"):
            return report("EXACT_B_QUERY_GRAPHQL_ERROR",
                          graphql_error_count=len(exact["errors"]),
                          safe_error_kinds=safe_graphql_error_kinds(exact["errors"]),
                          query_sha256=hashlib.sha256(REVIEW_QUERY.encode()).hexdigest())
        schema = post(token, SCHEMA_QUERY)
        second_schema = post(token, SECOND_SCHEMA_QUERY)
        errors = (schema.get("errors") or []) + (second_schema.get("errors") or [])
        if errors:
            return report("SCHEMA_INTROSPECTION_ERROR",
                          graphql_error_count=len(errors),
                          safe_error_kinds=safe_graphql_error_kinds(errors),
                          exact_query_syntax_ok=True,
                          query_sha256=hashlib.sha256(REVIEW_QUERY.encode()).hexdigest())
        types = {**(schema.get("data") or {}), **(second_schema.get("data") or {})}
        review = field_map(types.get("review"))
        actor = field_map(types.get("actor"))
        node = field_map(types.get("node"))
        commit = field_map(types.get("commit"))
        required = {"author", "authorAssociation", "commit", "lastEditedAt", "updatedAt"}
        schema_ok = bool(required <= review.keys() and
                         "login" in actor and "id" not in actor and
                         "id" in node and "oid" in commit)
        if not schema_ok:
            return report("SCHEMA_MISMATCH_HOLD", schema_ok=False,
                          review_fields_present=sorted(required & review.keys()),
                          actor_direct_id="id" in actor,
                          node_id="id" in node, commit_oid="oid" in commit)
        repository = (exact.get("data") or {}).get("repository")
        pr = repository.get("pullRequest") if isinstance(repository, dict) else None
        reviews = pr.get("reviews") if isinstance(pr, dict) else None
        nodes = reviews.get("nodes") if isinstance(reviews, dict) else None
        if not isinstance(nodes, list) or not isinstance(reviews.get("totalCount"), int):
            return report("INCOMPLETE_LIVE_B_RESPONSE", schema_ok=True)
        absent = sum(not isinstance(x, dict) or
                     bool({"author", "authorAssociation", "commit", "lastEditedAt"} -
                          x.keys()) for x in nodes)
        null_authors = sum(isinstance(x, dict) and x.get("author") is None for x in nodes)
        null_commits = sum(isinstance(x, dict) and x.get("commit") is None for x in nodes)
        missing_actor_node_id = sum(
            isinstance(x, dict) and isinstance(x.get("author"), dict)
            and "id" not in x["author"] for x in nodes)
        return report(
            "SCHEMA_AND_QUERY_VERIFIED_NON_AUTHORITATIVE",
            schema_ok=True, exact_query_syntax_ok=True,
            query_sha256=hashlib.sha256(REVIEW_QUERY.encode()).hexdigest(),
            review_fields={field: type_repr(review[field]) for field in sorted(required)},
            actor_direct_id="id" in actor, node_id="id" in node,
            actor_possible_types=sorted(t["name"] for t in
                                        types["actor"].get("possibleTypes", [])
                                        if isinstance(t, dict) and t.get("name")),
            reviewed_pr=295, returned_nodes=len(nodes),
            reported_total_count=reviews["totalCount"],
            missing_selected_fields_count=absent,
            null_author_count=null_authors, null_commit_count=null_commits,
            node_fragment_id_absent_count=missing_actor_node_id)
    except urllib.error.HTTPError as exc:
        return report("HTTP_ERROR_HOLD", http_status=int(exc.code))
    except (urllib.error.URLError, OSError, TimeoutError, ValueError, TypeError):
        return report("NETWORK_OR_RESPONSE_UNKNOWN")


if __name__ == "__main__":
    sys.exit(main())
