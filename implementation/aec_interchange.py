"""Bounded AEC interchange adapter prototype.

Validates an external envelope and maps explicit declarations to existing
Ario M0/EAG primitives. It does not authenticate senders, establish ancestry
completeness, infer independence, or assess proposition truth.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from core.schema import ObservationRecord, Reference

MAX_MESSAGE_BYTES = 16_384
MAX_FIELDS = 16
MAX_IDENTIFIER_BYTES = 128
MAX_PARENT_REFERENCES = 64
MAX_GRAPH_DEPTH = 16
SUPPORTED_MAJOR = 1


@dataclass(frozen=True)
class AECImportResult:
    status: str
    reason: str | None
    message_id: str | None
    declared_sender_id: str | None
    scope: str | None
    observation: ObservationRecord | None
    parent_references: tuple[Reference, ...]
    ancestry_completeness: str
    source_authentication: str = "UNKNOWN"
    evidence_independence: str = "UNKNOWN"
    claim_assessment: str = "UNKNOWN"
    truth_authority: str = "NONE"


def _identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    if len(value.encode("utf-8")) > MAX_IDENTIFIER_BYTES:
        raise ValueError(f"{field} exceeds {MAX_IDENTIFIER_BYTES} UTF-8 bytes")
    return value


def _reject(reason: str, message_id: str | None = None) -> AECImportResult:
    return AECImportResult(
        status="REJECTED", reason=reason, message_id=message_id,
        declared_sender_id=None, scope=None, observation=None,
        parent_references=(), ancestry_completeness="UNKNOWN",
    )


def import_aec_message(
    message: Mapping[str, Any],
    *,
    seen_message_ids: frozenset[str] = frozenset(),
) -> AECImportResult:
    """Validate one untrusted envelope; replay checks are caller-state scoped."""
    if not isinstance(message, Mapping):
        return _reject("MESSAGE_NOT_A_MAPPING")
    if len(message) > MAX_FIELDS:
        return _reject("TOO_MANY_FIELDS")
    try:
        encoded = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        return _reject("MESSAGE_NOT_JSON_COMPATIBLE")
    if len(encoded) > MAX_MESSAGE_BYTES:
        return _reject("MESSAGE_TOO_LARGE")

    allowed = {
        "schema_version", "message_id", "sender_id", "scope",
        "observation_id", "source_id", "source_type", "record_version",
        "parent_ids",
    }
    if set(message) - allowed:
        return _reject("UNSUPPORTED_FIELDS")
    try:
        version = _identifier(message.get("schema_version"), "schema_version")
        major_text = version.split(".", 1)[0]
        if not major_text.isdigit():
            return _reject("INVALID_SCHEMA_VERSION")
        if int(major_text) != SUPPORTED_MAJOR:
            return _reject("UNSUPPORTED_SCHEMA_MAJOR")
        message_id = _identifier(message.get("message_id"), "message_id")
        sender_id = _identifier(message.get("sender_id"), "sender_id")
        scope = _identifier(message.get("scope"), "scope")
        observation_id = _identifier(message.get("observation_id"), "observation_id")
        source_id = _identifier(message.get("source_id"), "source_id")
        source_type = _identifier(message.get("source_type"), "source_type")
        record_version = _identifier(message.get("record_version"), "record_version")
    except (ValueError, AttributeError) as exc:
        return _reject(str(exc))

    if message_id in seen_message_ids:
        return _reject("REPLAYED_MESSAGE_ID", message_id)

    raw_parents = message.get("parent_ids")
    ancestry = "UNKNOWN" if raw_parents is None else "DECLARED_ONLY"
    if raw_parents is None:
        raw_parents = []
    if not isinstance(raw_parents, list):
        return _reject("PARENT_IDS_MUST_BE_A_LIST", message_id)
    if len(raw_parents) > MAX_PARENT_REFERENCES:
        return _reject("TOO_MANY_PARENT_REFERENCES", message_id)
    if len(raw_parents) > MAX_GRAPH_DEPTH:
        return _reject("DECLARED_GRAPH_DEPTH_LIMIT", message_id)

    try:
        parents = tuple(
            Reference(_identifier(parent, "parent_id"), "AEC_MESSAGE")
            for parent in raw_parents
        )
    except ValueError as exc:
        return _reject(str(exc), message_id)
    parent_ids = [ref.reference_id for ref in parents]
    if len(set(parent_ids)) != len(parent_ids):
        return _reject("DUPLICATE_PARENT_REFERENCE", message_id)
    if message_id in parent_ids:
        return _reject("SELF_PARENT_REFERENCE", message_id)

    try:
        source_ref = Reference(source_id, source_type)
        observation = ObservationRecord(
            observation_id=observation_id,
            record_version=record_version,
            provenance_refs=(source_ref,) + parents,
        )
    except ValueError as exc:
        return _reject(f"ARIO_MAPPING_REJECTED: {exc}", message_id)

    return AECImportResult(
        status="ACCEPTED_FOR_LOCAL_REVIEW", reason=None,
        message_id=message_id, declared_sender_id=sender_id, scope=scope,
        observation=observation, parent_references=parents,
        ancestry_completeness=ancestry,
    )
