"""Research-only XERJ candidate retriever. NO write endpoints or trust activation.

Authored from published Elasticsearch-compatible API contract; no upstream source copied.
XERJ is a replaceable *candidate search index*, not Ario's evidence ledger.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import http.client
import json
import re
from urllib.parse import urlsplit
from typing import Mapping

ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_:.\-]{0,127}\Z")
INDEX_RE = re.compile(r"[a-z][a-z0-9_\-]{0,62}\Z")


@dataclass(frozen=True)
class ArioRecord:
    event_id: str
    text: str
    sha256: str
    root_label: str | None = None
    recorded_at: str | None = None
    valid_at: str | None = None

    @classmethod
    def from_text(cls, event_id: str, text: str, root_label: str | None = None,
                  recorded_at: str | None = None, valid_at: str | None = None) -> "ArioRecord":
        return cls(event_id, text, hashlib.sha256(text.encode("utf-8")).hexdigest(),
                   root_label, recorded_at, valid_at)


@dataclass(frozen=True)
class Candidate:
    event_id: str
    text: str
    sha256: str
    root_label: str | None
    recorded_at: str | None
    valid_at: str | None
    rank: int


def parse_candidates(result: object, ledger: Mapping[str, ArioRecord], *, k: int = 3,
                     expected_index: str | None = None) -> dict:
    """Accept only IDs resolved from Ario's original ledger, never search result text.

    Returning CANDIDATES_ONLY is deliberately NOT a claim of evidence sufficiency.
    Identical root labels do not establish independent witnesses; distinct labels
    are metadata, not independent verification of actual source independence.
    """
    if not 1 <= k <= 10:
        raise ValueError("k must be between 1 and 10")
    if not isinstance(result, dict):
        raise ValueError("invalid search response")
    hits = result.get("hits")
    if not isinstance(hits, dict) or not isinstance(hits.get("hits"), list):
        raise ValueError("missing hits.hits")
    hits = hits["hits"]
    if len(hits) > k:
        raise ValueError("search response exceeds requested k")
    candidates, anomalies, seen = [], [], set()
    # When completion metadata is present, fail closed on malformed types.
    # A non-boolean truthy value such as "true" must never mean success.
    if "timed_out" in result:
        timed_out = result["timed_out"]
        if type(timed_out) is not bool:
            anomalies.append("malformed_timeout_metadata")
        elif timed_out:
            anomalies.append("search_timed_out")
    if "_shards" in result:
        shards = result["_shards"]
        if not isinstance(shards, dict):
            anomalies.append("malformed_shard_metadata")
        elif any(type(shards.get(field)) is not int or shards[field] < 0
                 for field in ("total", "successful", "failed")):
            anomalies.append("malformed_shard_metadata")
        elif (type(shards.get("skipped", 0)) is not int or
              shards.get("skipped", 0) < 0 or
              shards["successful"] + shards["failed"] + shards.get("skipped", 0) > shards["total"]):
            anomalies.append("malformed_shard_metadata")
        elif shards["failed"]:
            anomalies.append("search_shard_failures")
    for rank, hit in enumerate(hits, 1):
        if not isinstance(hit, dict) or not isinstance(hit.get("_id"), str):
            anomalies.append("malformed_hit")
            continue
        eid = hit["_id"]
        if expected_index is not None and hit.get("_index") != expected_index:
            anomalies.append("foreign_or_missing_index")
            continue
        if not ID_RE.fullmatch(eid):
            anomalies.append("malformed_id")
            continue
        if eid in seen:
            anomalies.append("duplicate_id")
            continue
        seen.add(eid)
        record = ledger.get(eid)
        if record is None:
            anomalies.append("unregistered_id")
            continue
        if record.event_id != eid or not isinstance(record.text, str) or not isinstance(record.sha256, str):
            anomalies.append("invalid_ledger_entry")
            continue
        if hashlib.sha256(record.text.encode("utf-8")).hexdigest() != record.sha256:
            anomalies.append("local_digest_mismatch")
            continue
        # Intentionally discard _source, score, highlighted snippets and other
        # untrusted search metadata. Only the original Ario ledger is emitted.
        candidates.append(Candidate(eid,record.text,record.sha256,record.root_label,
                                    record.recorded_at,record.valid_at,rank))
    status = "RETRIEVAL_INCOMPLETE" if anomalies else ("CANDIDATES_ONLY" if candidates else "NO_HITS_UNKNOWN")
    labels = sorted({c.root_label for c in candidates if c.root_label is not None})
    return {"status": status,
            "candidates": [c.__dict__ for c in candidates],
            "anomalies": anomalies,
            "distinct_root_labels": labels,
            "source_independence": "NOT_ESTABLISHED",
            "answer_authorized": False,
            "trust_activated": False}


class XERJReadOnly:
    """Single POST to loopback index/_search; never asks XERJ to decide truth."""
    def __init__(self, base_url: str, index: str, *, api_key: str, timeout: float = 2.0):
        u = urlsplit(base_url)
        if (u.scheme != "http" or u.hostname != "127.0.0.1" or
            u.username is not None or u.password is not None or
            u.path not in ("", "/") or u.query or u.fragment):
            raise ValueError("only literal HTTP loopback 127.0.0.1 origin is allowed")
        try:
            port = u.port
        except ValueError as exc:
            raise ValueError("invalid port") from exc
        if port is None or not 1 <= port <= 65535:
            raise ValueError("explicit port required")
        if not INDEX_RE.fullmatch(index) or index.startswith("."):
            raise ValueError("invalid dedicated index")
        if not isinstance(api_key, str) or not api_key or "\n" in api_key or "\r" in api_key:
            raise ValueError("provide a read-only scoped API key")
        if timeout <= 0 or timeout > 10:
            raise ValueError("bounded timeout required")
        self.port, self.index, self.key, self.timeout = port, index, api_key, timeout

    def search(self, question: str, ledger: Mapping[str, ArioRecord], k: int = 3) -> dict:
        if not isinstance(question, str) or not question.strip() or len(question.encode("utf-8")) > 4000:
            raise ValueError("bounded nonempty query required")
        if not 1 <= k <= 10:
            raise ValueError("invalid k")
        payload = json.dumps({"size": k, "_source": False, "query": {"match": {"text": question}}},
                             separators=(",", ":")).encode("utf-8")
        # http.client uses NO HTTP proxy and does NOT follow redirects.
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=self.timeout)
        try:
            conn.request("POST", f"/{self.index}/_search", body=payload,
                         headers={"Content-Type":"application/json", "Authorization": f"ApiKey {self.key}"})
            resp = conn.getresponse()
            data = resp.read(262145)  # max 256 KiB +1
            if resp.status != 200:
                raise RuntimeError(f"search returned HTTP {resp.status}")
            if len(data) > 262144:
                raise RuntimeError("search returned oversized body")
            try:
                obj = json.loads(data)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise RuntimeError("invalid JSON from search endpoint") from exc
            return parse_candidates(obj, ledger, k=k, expected_index=self.index)
        finally:
            conn.close()
