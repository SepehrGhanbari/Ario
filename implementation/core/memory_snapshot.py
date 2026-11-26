"""Data-only, bounded persistence for :mod:`memory_consolidation`.

The retained SHA-256 reference is supplied by the caller. It binds bytes only;
it does not authenticate their source, freshness, custody, or semantic claims.
"""

from __future__ import annotations

import errno
import hashlib
import hmac
import json
import math
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Type

from .memory_consolidation import (
    CausalLink,
    ConsolidationEngine,
    ConsolidationError,
    NodeEpistemicStatus,
    SemanticNode,
)

SNAPSHOT_FORMAT = "ario.cognitive-memory"
SNAPSHOT_SCHEMA_VERSION = 1
MAX_SNAPSHOT_BYTES = 32 * 1024 * 1024
MAX_SNAPSHOT_DEPTH = 64
MAX_SNAPSHOT_MARKERS = 500_000
MAX_SNAPSHOT_RECORDS = 100_000
MAX_SNAPSHOT_TEXT_BYTES = 1_048_576
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_STATUS_BY_VALUE = {status.value: status for status in NodeEpistemicStatus}
_PRIVILEGED_STATUSES = {
    NodeEpistemicStatus.ACCEPTED,
    NodeEpistemicStatus.SUPPORTED,
}
_TOP_LEVEL_KEYS = {"format", "schema_version", "engine"}
_ENGINE_KEYS = {
    "decay_rate",
    "retrieval_threshold",
    "node_id_version",
    "default_status",
    "max_batch_events",
    "nodes",
    "links",
    "ledger_hashes",
    "event_payload_digests",
    "event_stable_digests",
}
_NODE_KEYS = {
    "node_id",
    "concept",
    "assertion",
    "status",
    "source_event_hashes",
    "saliency_score",
    "created_at",
    "last_reinforced_at",
    "reinforcement_count",
    "falsification_condition",
}
_LINK_KEYS = {
    "from_node_id",
    "to_node_id",
    "relation",
    "weight",
    "evidence_hashes",
}


class SnapshotRecoveryError(ConsolidationError):
    """A bounded cognitive-memory snapshot failed integrity or schema checks."""


def _reject(code: str) -> None:
    raise SnapshotRecoveryError(code)


def _is_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256.fullmatch(value) is not None


def _require_text(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str or (not allow_empty and not value.strip()):
        _reject(f"HOLD_INVALID_SNAPSHOT_{label}")
    try:
        encoded_length = len(value.encode("utf-8", errors="strict"))
    except UnicodeEncodeError as exc:
        raise SnapshotRecoveryError(f"HOLD_INVALID_SNAPSHOT_{label}") from exc
    if encoded_length > MAX_SNAPSHOT_TEXT_BYTES:
        _reject(f"HOLD_SNAPSHOT_{label}_TOO_LARGE")
    return value


def _require_number(value: Any, label: str, *, minimum: float, maximum: float) -> float:
    if type(value) not in (int, float):
        _reject(f"HOLD_INVALID_SNAPSHOT_{label}")
    try:
        number = float(value)
    except (OverflowError, ValueError):
        _reject(f"HOLD_INVALID_SNAPSHOT_{label}")
    if not math.isfinite(number) or not minimum <= number <= maximum:
        _reject(f"HOLD_INVALID_SNAPSHOT_{label}")
    return number


def _require_hash_list(value: Any, label: str, *, required: bool) -> tuple[str, ...]:
    if type(value) is not list or len(value) > MAX_SNAPSHOT_RECORDS:
        _reject(f"HOLD_INVALID_SNAPSHOT_{label}")
    if required and not value:
        _reject(f"HOLD_INVALID_SNAPSHOT_{label}")
    if any(not _is_sha256(item) for item in value) or len(value) != len(set(value)):
        _reject(f"HOLD_INVALID_SNAPSHOT_{label}")
    return tuple(value)


def _require_object(value: Any, label: str, expected: set[str]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        _reject(f"HOLD_INVALID_SNAPSHOT_{label}")
    return value


def _parse_json_int(text: str) -> int:
    digits = text.lstrip("-")
    if len(digits) > 19:
        _reject("HOLD_SNAPSHOT_INTEGER_TOO_LARGE")
    return int(text)


def _parse_json_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        _reject("HOLD_SNAPSHOT_NONFINITE_NUMBER")
    return value


def _reject_json_constant(text: str) -> Any:
    _reject("HOLD_SNAPSHOT_NONSTANDARD_JSON_CONSTANT")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            _reject("HOLD_SNAPSHOT_DUPLICATE_JSON_KEY")
        value[key] = item
    return value


def _check_json_budget(raw: bytes) -> None:
    quoted = False
    escaped = False
    depth = 0
    markers = 0
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
            continue
        if byte == 34:
            quoted = True
            continue
        if byte in (91, 123):
            depth += 1
            if depth > MAX_SNAPSHOT_DEPTH:
                _reject("HOLD_SNAPSHOT_NESTING_LIMIT")
        elif byte in (93, 125):
            depth -= 1
            if depth < 0:
                _reject("HOLD_INVALID_SNAPSHOT_JSON")
        if byte in (91, 93, 123, 125, 44, 58):
            markers += 1
            if markers > MAX_SNAPSHOT_MARKERS:
                _reject("HOLD_SNAPSHOT_STRUCTURE_LIMIT")
    if quoted or depth != 0:
        _reject("HOLD_INVALID_SNAPSHOT_JSON")


def _canonical_json(document: dict[str, Any]) -> bytes:
    try:
        encoded = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as exc:
        raise SnapshotRecoveryError("HOLD_SNAPSHOT_NOT_CANONICAL_JSON") from exc
    if len(encoded) > MAX_SNAPSHOT_BYTES:
        _reject("HOLD_SNAPSHOT_BYTES_TOO_LARGE")
    return encoded


def _node_to_data(node: SemanticNode) -> dict[str, Any]:
    if type(node) is not SemanticNode or type(node.status) is not NodeEpistemicStatus:
        _reject("HOLD_INVALID_SNAPSHOT_NODE")
    if node.status in _PRIVILEGED_STATUSES:
        _reject("HOLD_UNVERIFIED_SNAPSHOT_ADMISSION")
    return {
        "node_id": node.node_id,
        "concept": node.concept,
        "assertion": node.assertion,
        "status": node.status.value,
        "source_event_hashes": list(node.source_event_hashes),
        "saliency_score": node.saliency_score,
        "created_at": node.created_at,
        "last_reinforced_at": node.last_reinforced_at,
        "reinforcement_count": node.reinforcement_count,
        "falsification_condition": node.falsification_condition,
    }


def _link_to_data(link: CausalLink) -> dict[str, Any]:
    if type(link) is not CausalLink:
        _reject("HOLD_INVALID_SNAPSHOT_LINK")
    return {
        "from_node_id": link.from_node_id,
        "to_node_id": link.to_node_id,
        "relation": link.relation,
        "weight": link.weight,
        "evidence_hashes": list(link.evidence_hashes),
    }


def _engine_to_document(engine: ConsolidationEngine) -> dict[str, Any]:
    with engine._batch_lock:
        if engine._batch_running:
            _reject("HOLD_SNAPSHOT_DURING_BATCH")
        if (type(engine._nodes) is not dict or type(engine._links) is not list
                or type(engine._ledger_hashes) is not set
                or type(engine._event_payload_digests) is not dict
                or type(engine._event_stable_digests) is not dict):
            _reject("HOLD_INVALID_ENGINE_STATE")
        if any(len(collection) > MAX_SNAPSHOT_RECORDS for collection in (
            engine._nodes, engine._links, engine._ledger_hashes,
            engine._event_payload_digests, engine._event_stable_digests,
        )):
            _reject("HOLD_SNAPSHOT_RECORD_LIMIT")
        status = engine.default_status
        if type(status) is not NodeEpistemicStatus or status in _PRIVILEGED_STATUSES:
            _reject("HOLD_UNVERIFIED_SNAPSHOT_ADMISSION")
        return {
            "format": SNAPSHOT_FORMAT,
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "engine": {
                "decay_rate": engine.decay_rate,
                "retrieval_threshold": engine.retrieval_threshold,
                "node_id_version": engine.node_id_version,
                "default_status": status.value,
                "max_batch_events": engine.max_batch_events,
                "nodes": [
                    _node_to_data(node)
                    for node in engine._nodes.values()
                ],
                "links": [_link_to_data(link) for link in engine._links],
                "ledger_hashes": sorted(engine._ledger_hashes),
                "event_payload_digests": dict(engine._event_payload_digests),
                "event_stable_digests": dict(engine._event_stable_digests),
            },
        }


def _decode_document(
    engine_type: Type[ConsolidationEngine], document: Any
) -> ConsolidationEngine:
    top = _require_object(document, "ROOT", _TOP_LEVEL_KEYS)
    if top["format"] != SNAPSHOT_FORMAT:
        _reject("HOLD_UNSUPPORTED_SNAPSHOT_FORMAT")
    if type(top["schema_version"]) is not int:
        _reject("HOLD_INVALID_SNAPSHOT_VERSION")
    if top["schema_version"] != SNAPSHOT_SCHEMA_VERSION:
        _reject("HOLD_UNSUPPORTED_SNAPSHOT_VERSION")

    engine_data = _require_object(top["engine"], "ENGINE", _ENGINE_KEYS)
    decay_rate = _require_number(
        engine_data["decay_rate"], "DECAY_RATE", minimum=0.0, maximum=1.0
    )
    if decay_rate == 0.0 or decay_rate == 1.0:
        _reject("HOLD_INVALID_SNAPSHOT_DECAY_RATE")
    retrieval_threshold = _require_number(
        engine_data["retrieval_threshold"], "RETRIEVAL_THRESHOLD", minimum=0.0, maximum=1.0
    )
    node_id_version = _require_text(engine_data["node_id_version"], "NODE_ID_VERSION")
    if node_id_version not in ("v1", "v2"):
        _reject("HOLD_INVALID_SNAPSHOT_NODE_ID_VERSION")
    status_text = _require_text(engine_data["default_status"], "DEFAULT_STATUS")
    default_status = _STATUS_BY_VALUE.get(status_text)
    if default_status is None:
        _reject("HOLD_INVALID_SNAPSHOT_DEFAULT_STATUS")
    if default_status in _PRIVILEGED_STATUSES:
        _reject("HOLD_UNVERIFIED_SNAPSHOT_ADMISSION")
    max_batch_events = engine_data["max_batch_events"]
    if type(max_batch_events) is not int or not 1 <= max_batch_events < sys.maxsize:
        _reject("HOLD_INVALID_SNAPSHOT_MAX_BATCH_EVENTS")

    raw_hashes = engine_data["ledger_hashes"]
    if type(raw_hashes) is not list or len(raw_hashes) > MAX_SNAPSHOT_RECORDS:
        _reject("HOLD_INVALID_SNAPSHOT_LEDGER_HASHES")
    if any(not _is_sha256(item) for item in raw_hashes):
        _reject("HOLD_INVALID_SNAPSHOT_LEDGER_HASHES")
    ledger_hashes = set(raw_hashes)
    if len(ledger_hashes) != len(raw_hashes):
        _reject("HOLD_INVALID_SNAPSHOT_LEDGER_HASHES")

    def read_digest_index(value: Any, label: str) -> dict[str, str]:
        if type(value) is not dict or len(value) > MAX_SNAPSHOT_RECORDS:
            _reject(f"HOLD_INVALID_SNAPSHOT_{label}")
        if any(not _is_sha256(key) or not _is_sha256(digest)
               for key, digest in value.items()):
            _reject(f"HOLD_INVALID_SNAPSHOT_{label}")
        if set(value) != ledger_hashes:
            _reject(f"HOLD_INVALID_SNAPSHOT_{label}")
        return dict(value)

    payload_digests = read_digest_index(
        engine_data["event_payload_digests"], "PAYLOAD_DIGESTS"
    )
    stable_digests = read_digest_index(
        engine_data["event_stable_digests"], "STABLE_DIGESTS"
    )

    raw_nodes = engine_data["nodes"]
    if type(raw_nodes) is not list or len(raw_nodes) > MAX_SNAPSHOT_RECORDS:
        _reject("HOLD_SNAPSHOT_NODE_LIMIT")
    nodes: dict[str, SemanticNode] = {}
    for raw_node in raw_nodes:
        node_data = _require_object(raw_node, "NODE", _NODE_KEYS)
        node_id = _require_text(node_data["node_id"], "NODE_ID")
        concept = _require_text(node_data["concept"], "CONCEPT")
        assertion = _require_text(node_data["assertion"], "ASSERTION")
        if node_id in nodes or node_id != engine_type.compute_node_id(
            concept, assertion, version=node_id_version
        ):
            _reject("HOLD_INVALID_SNAPSHOT_NODE_ID")
        status_value = _require_text(node_data["status"], "STATUS")
        node_status = _STATUS_BY_VALUE.get(status_value)
        if node_status is None:
            _reject("HOLD_INVALID_SNAPSHOT_STATUS")
        if node_status in _PRIVILEGED_STATUSES:
            _reject("HOLD_UNVERIFIED_SNAPSHOT_ADMISSION")
        source_hashes = _require_hash_list(
            node_data["source_event_hashes"], "SOURCE_EVENT_HASHES", required=True
        )
        if not set(source_hashes).issubset(ledger_hashes):
            _reject("HOLD_INVALID_SNAPSHOT_LINEAGE")
        score = _require_number(
            node_data["saliency_score"], "SALIENCY_SCORE", minimum=0.0, maximum=1.0
        )
        created_at = _require_text(node_data["created_at"], "CREATED_AT")
        last_reinforced_at = _require_text(
            node_data["last_reinforced_at"], "LAST_REINFORCED_AT"
        )
        reinforcement_count = node_data["reinforcement_count"]
        if (type(reinforcement_count) is not int or reinforcement_count < 1
                or reinforcement_count >= sys.maxsize):
            _reject("HOLD_INVALID_SNAPSHOT_REINFORCEMENT_COUNT")
        falsification_condition = node_data["falsification_condition"]
        if falsification_condition is not None:
            falsification_condition = _require_text(
                falsification_condition, "FALSIFICATION_CONDITION", allow_empty=True
            )
        nodes[node_id] = SemanticNode(
            node_id=node_id,
            concept=concept,
            assertion=assertion,
            status=node_status,
            source_event_hashes=source_hashes,
            saliency_score=score,
            created_at=created_at,
            last_reinforced_at=last_reinforced_at,
            reinforcement_count=reinforcement_count,
            falsification_condition=falsification_condition,
        )

    raw_links = engine_data["links"]
    if type(raw_links) is not list or len(raw_links) > MAX_SNAPSHOT_RECORDS:
        _reject("HOLD_SNAPSHOT_LINK_LIMIT")
    links: list[CausalLink] = []
    for raw_link in raw_links:
        link_data = _require_object(raw_link, "LINK", _LINK_KEYS)
        from_node_id = _require_text(link_data["from_node_id"], "LINK_FROM_NODE")
        to_node_id = _require_text(link_data["to_node_id"], "LINK_TO_NODE")
        if from_node_id not in nodes or to_node_id not in nodes:
            _reject("HOLD_INVALID_SNAPSHOT_LINK_REFERENCE")
        relation = _require_text(link_data["relation"], "LINK_RELATION")
        weight = _require_number(link_data["weight"], "LINK_WEIGHT", minimum=0.0, maximum=1.0)
        evidence_hashes = _require_hash_list(
            link_data["evidence_hashes"], "LINK_EVIDENCE_HASHES", required=False
        )
        if not set(evidence_hashes).issubset(ledger_hashes):
            _reject("HOLD_INVALID_SNAPSHOT_LINK_EVIDENCE")
        links.append(CausalLink(
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            relation=relation,
            weight=weight,
            evidence_hashes=evidence_hashes,
        ))

    try:
        candidate = engine_type(
            decay_rate=decay_rate,
            retrieval_threshold=retrieval_threshold,
            node_id_version=node_id_version,
            default_status=default_status,
            max_batch_events=max_batch_events,
        )
    except (TypeError, ValueError, OverflowError) as exc:
        raise SnapshotRecoveryError("HOLD_INVALID_SNAPSHOT_ENGINE_CONFIG") from exc
    candidate._nodes = nodes
    candidate._links = links
    candidate._ledger_hashes = ledger_hashes
    candidate._event_payload_digests = payload_digests
    candidate._event_stable_digests = stable_digests
    aliases: dict[str, str | None] = {}
    if node_id_version == "v2":
        for node_id, node in nodes.items():
            candidate._index_legacy_alias(aliases, node.concept, node.assertion, node_id)
    candidate._legacy_aliases = aliases
    return candidate


def _validated_document(raw: bytes, expected_sha256: str) -> tuple[dict[str, Any], bytes]:
    if type(raw) is not bytes:
        _reject("HOLD_SNAPSHOT_MUST_BE_IMMUTABLE_BYTES")
    if len(raw) > MAX_SNAPSHOT_BYTES:
        _reject("HOLD_SNAPSHOT_BYTES_TOO_LARGE")
    if (type(expected_sha256) is not str or len(expected_sha256) != 64
            or not _SHA256.fullmatch(expected_sha256.lower())):
        _reject("HOLD_INVALID_EXPECTED_SNAPSHOT_SHA256")
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if not hmac.compare_digest(actual_sha256, expected_sha256.lower()):
        _reject("HOLD_SNAPSHOT_SHA256_MISMATCH")
    _check_json_budget(raw)
    try:
        document = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_int=_parse_json_int,
            parse_float=_parse_json_float,
            parse_constant=_reject_json_constant,
        )
    except SnapshotRecoveryError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, MemoryError, ValueError) as exc:
        raise SnapshotRecoveryError("HOLD_INVALID_SNAPSHOT_JSON") from exc
    if type(document) is not dict:
        _reject("HOLD_INVALID_SNAPSHOT_ROOT")
    canonical = _canonical_json(document)
    if canonical != raw:
        _reject("HOLD_NONCANONICAL_SNAPSHOT_BYTES")
    return document, canonical


def encode_engine_snapshot(engine: ConsolidationEngine) -> bytes:
    """Encode validated engine state as canonical JSON without executable data."""
    if not isinstance(engine, ConsolidationEngine):
        _reject("HOLD_INVALID_ENGINE_STATE")
    document = _engine_to_document(engine)
    encoded = _canonical_json(document)
    # Reuse the exact restore validator so the writer cannot emit a snapshot
    # that the recovery path itself would refuse.
    _decode_document(type(engine), document)
    return encoded


def decode_engine_snapshot(
    engine_type: Type[ConsolidationEngine], snapshot: bytes, *, expected_sha256: str
) -> ConsolidationEngine:
    """Verify and decode bytes into a new engine using only explicit data types."""
    document, _ = _validated_document(snapshot, expected_sha256)
    return _decode_document(engine_type, document)


def restore_engine_snapshot(
    engine: ConsolidationEngine, snapshot: bytes, *, expected_sha256: str
) -> None:
    """Install a fully built candidate with one state-dictionary swap."""
    candidate = decode_engine_snapshot(
        type(engine), snapshot, expected_sha256=expected_sha256
    )
    lock = engine._batch_lock
    replacement = candidate.__dict__.copy()
    replacement["_batch_lock"] = lock
    replacement["_batch_running"] = False
    replacement.pop("_local", None)
    with lock:
        engine.__dict__ = replacement


def write_snapshot(engine: ConsolidationEngine, path: str | os.PathLike[str]) -> str:
    """Atomically replace *path* with a data-only snapshot; return its SHA-256.

    The returned digest is integrity metadata, not an authenticity or freshness
    claim. Retain it independently and supply it to recovery explicitly.
    """
    payload = encode_engine_snapshot(engine)
    digest = hashlib.sha256(payload).hexdigest()
    target = Path(path)
    if not target.name:
        _reject("HOLD_INVALID_SNAPSHOT_PATH")
    parent = target.parent
    try:
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=parent
        )
    except OSError as exc:
        raise SnapshotRecoveryError("HOLD_SNAPSHOT_WRITE_FAILED") from exc
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, target)
        _fsync_directory(parent)
    except OSError as exc:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise SnapshotRecoveryError("HOLD_SNAPSHOT_WRITE_FAILED") from exc
    return digest


def _fsync_directory(directory: Path) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(directory, flags)
    except OSError as exc:
        if exc.errno in (errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP, errno.EBADF):
            return
        raise
    try:
        try:
            os.fsync(descriptor)
        except OSError as exc:
            if exc.errno not in (errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP, errno.EBADF):
                raise
    finally:
        os.close(descriptor)


def restore_snapshot_file(
    engine: ConsolidationEngine,
    path: str | os.PathLike[str],
    *,
    expected_sha256: str,
) -> None:
    """Read a regular file under the byte limit and atomically restore it."""
    target = Path(path)
    try:
        metadata = target.stat()
        if not stat.S_ISREG(metadata.st_mode):
            _reject("HOLD_SNAPSHOT_NOT_REGULAR_FILE")
        if metadata.st_size > MAX_SNAPSHOT_BYTES:
            _reject("HOLD_SNAPSHOT_BYTES_TOO_LARGE")
        with target.open("rb") as stream:
            raw = stream.read(MAX_SNAPSHOT_BYTES + 1)
    except SnapshotRecoveryError:
        raise
    except OSError as exc:
        raise SnapshotRecoveryError("HOLD_SNAPSHOT_READ_FAILED") from exc
    if len(raw) > MAX_SNAPSHOT_BYTES:
        _reject("HOLD_SNAPSHOT_BYTES_TOO_LARGE")
    engine.restore_snapshot(raw, expected_sha256=expected_sha256)
