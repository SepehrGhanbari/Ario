#!/usr/bin/env python3
"""W13 research-only laboratory: separate source-origin and grant-signing domains.

Uses ephemeral synthetic Ed25519 keys for two *logical* domains in one process.
Cryptographic integrity is meaningful only under a trusted key-registry and custody
assumption, which this single-process lab DOES NOT establish. No actual action is run.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

SOURCE_DOMAIN = "ARIO_W13_LAB_SOURCE_V1"
GRANT_DOMAIN = "ARIO_W13_LAB_GRANT_V1"
ACTION_KEYS = frozenset({"principal", "operation", "resource", "destination", "source_digest"})
SOURCE_KEYS = frozenset({"version", "source_id", "classification", "principal", "digest", "issued_epoch"})
GRANT_KEYS = frozenset({"version", "grant_id", "principal", "operation", "resource", "destination", "source_digest", "not_before", "expires"})
ALLOWED_OPERATIONS = frozenset({"SEND", "UPLOAD", "WRITE_NOTE"})


def _wire(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest_content(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _packet(private: Ed25519PrivateKey, domain: str, body: dict) -> dict:
    sig = private.sign(_wire({"domain": domain, "body": body})).hex()
    return {"body": body.copy(), "signature": sig}


def _valid_packet(public: Ed25519PublicKey, domain: str, packet: Any) -> tuple[dict | None, str]:
    if not isinstance(packet, dict) or set(packet) != {"body", "signature"}:
        return None, "PACKET_SCHEMA"
    body, signature = packet["body"], packet["signature"]
    if type(body) is not dict or type(signature) is not str or len(signature) != 128:
        return None, "PACKET_TYPES"
    try:
        sig_bytes = bytes.fromhex(signature)
        public.verify(sig_bytes, _wire({"domain": domain, "body": body}))
        return body, "OK"
    except (InvalidSignature, ValueError, TypeError):
        return None, "INVALID_SIGNATURE_OR_PAYLOAD"


class SyntheticIssuer:
    """A trusted key *handle* in the toy. Real custody needs separate principals/hosts."""
    def __init__(self):
        self._secret = Ed25519PrivateKey.generate()

    @property
    def public(self) -> Ed25519PublicKey:
        return self._secret.public_key()

    def source(self, *, source_id: str, classification: str, principal: str, content: str, epoch: int = 0):
        if classification not in {"USER_INGRESS", "UNTRUSTED_MEMORY", "EXTERNAL_PAGE", "TOOL_RESULT"}:
            raise ValueError("BAD_CLASSIFICATION")
        return _packet(self._secret, SOURCE_DOMAIN, {
            "version": 1, "source_id": source_id, "classification": classification,
            "principal": principal, "digest": digest_content(content), "issued_epoch": epoch,
        })

    def grant(self, *, grant_id: str, principal: str, operation: str, resource: str,
              destination: str, source_digest: str, not_before: int = 0, expires: int = 20):
        return _packet(self._secret, GRANT_DOMAIN, {
            "version": 1, "grant_id": grant_id, "principal": principal,
            "operation": operation, "resource": resource, "destination": destination,
            "source_digest": source_digest, "not_before": not_before, "expires": expires,
        })


@dataclass
class ReadOnlyVerifier:
    origin_key: Ed25519PublicKey
    grant_key: Ed25519PublicKey
    revoked: set[str] = field(default_factory=set)

    def __post_init__(self):
        if self.origin_key.public_bytes_raw() == self.grant_key.public_bytes_raw():
            raise ValueError("TRUST_DOMAIN_COLLISION")

    def revoke(self, grant_id: str):
        self.revoked.add(grant_id)

    def check(self, *, content: str, source_packet: dict, proposed: dict,
              grant_packet: dict | None, now: int) -> dict:
        base = {"authority": "NOT_ESTABLISHED", "world_truth": "UNKNOWN",
                "receipt_capture_completeness": "NOT_ESTABLISHED", "external_effects": 0,
                "memory_admitted": False, "independent_key_custody": False}
        def answer(verdict: str, reason: str):
            return {**base, "verdict": verdict, "reason": reason}
        if type(content) is not str or len(content.encode("utf-8")) > 4096:
            return answer("UNKNOWN", "CONTENT_BOUNDS")
        if type(proposed) is not dict or set(proposed) != ACTION_KEYS or any(
            type(v) is not str or not v or len(v) > 160 for v in proposed.values()
        ) or proposed.get("operation") not in ALLOWED_OPERATIONS:
            return answer("UNKNOWN", "CANDIDATE_SCHEMA")
        if type(now) is not int or now < 0:
            return answer("UNKNOWN", "CLOCK_INVALID")
        source, reason = _valid_packet(self.origin_key, SOURCE_DOMAIN, source_packet)
        if source is None:
            return answer("DENY", "SOURCE_" + reason)
        if set(source) != SOURCE_KEYS or source["version"] != 1 or type(source["issued_epoch"]) is not int or (
            source["classification"] not in {"USER_INGRESS", "UNTRUSTED_MEMORY", "EXTERNAL_PAGE", "TOOL_RESULT"}
        ) or any(type(source[k]) is not str or not source[k] for k in ("source_id", "principal", "digest")):
            return answer("UNKNOWN", "SOURCE_SCHEMA")
        if (source["digest"] != digest_content(content) or
            proposed["source_digest"] != source["digest"] or
            proposed["principal"] != source["principal"]):
            return answer("DENY", "SOURCE_BYTES_OR_PRINCIPAL_MISMATCH")
        if grant_packet is None:
            return answer("DENY", "NO_SEPARATE_GRANT")
        grant, reason = _valid_packet(self.grant_key, GRANT_DOMAIN, grant_packet)
        if grant is None:
            return answer("DENY", "GRANT_" + reason)
        if set(grant) != GRANT_KEYS or grant["version"] != 1 or any(
            type(grant[k]) is not str or not grant[k] for k in
            ("grant_id", "principal", "operation", "resource", "destination", "source_digest")
        ) or type(grant["not_before"]) is not int or type(grant["expires"]) is not int:
            return answer("UNKNOWN", "GRANT_SCHEMA")
        if grant["grant_id"] in self.revoked:
            return answer("DENY", "GRANT_REVOKED")
        if not grant["not_before"] <= now < grant["expires"]:
            return answer("DENY", "GRANT_NOT_CURRENT")
        if any(grant[key] != proposed[key] for key in ACTION_KEYS):
            return answer("DENY", "GRANT_SCOPE_MISMATCH")
        return answer("ELIGIBLE_FOR_SEPARATE_GATE", "TWO_DISTINCT_SIGNATURE_DOMAINS_MATCH_SYNTHETIC_SCOPE")
