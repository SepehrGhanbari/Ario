"""Strict data-only encoding for source-monitoring attribution history.

This module stores historical records only. Active verification authority is
intentionally process-local and is never reconstructed from snapshot bytes.
"""

from __future__ import annotations

from typing import Any

from . import memory_snapshot as _codec
from .source_monitoring import (
    EmpiricalProvenance,
    SourceAttribution,
    SourceMonitoringError,
    SourceMonitoringGuard,
    SourceType,
    VeracityState,
)

_SOURCE_KEYS = {"records"}
_RECORD_KEYS = {"attribution_id", "revisions"}
_ATTRIBUTION_KEYS = {
    "attribution_id",
    "source_type",
    "assertion",
    "veracity_state",
    "provenance",
    "parent_attribution_ids",
    "created_at",
    "falsification_condition",
}
_PROVENANCE_KEYS = {
    "tool",
    "target",
    "exit_code",
    "execution_lock_sha256",
    "stdout_sha256",
    "recorded_at",
    "metadata",
}
_INITIAL_STATES = {
    SourceType.INTERNAL_HYPOTHESIS: {VeracityState.UNVERIFIED_HYPOTHESIS},
    SourceType.EXTERNAL_TESTIMONY: {VeracityState.EXTERNAL_ASSERTION},
    SourceType.LEDGER_REPORT: {VeracityState.REPORTED_UNVERIFIED},
    SourceType.EMPIRICAL_OBSERVATION: {
        VeracityState.VERIFIED_EMPIRICAL,
        VeracityState.UNSUPPORTED,
        VeracityState.ATTRIBUTION_MISMATCH,
    },
}


def _reject(code: str) -> None:
    raise _codec.SnapshotRecoveryError(code)


def _object(value: Any, label: str, keys: set[str]) -> dict[str, Any]:
    return _codec._require_object(value, label, keys)


def _text(value: Any, label: str, *, allow_empty: bool = False) -> str:
    return _codec._require_text(value, label, allow_empty=allow_empty)


def _source_hash(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value.lower())
    )


def _require_json_value(value: Any, depth: int = 0) -> None:
    if depth > _codec.MAX_SNAPSHOT_DEPTH:
        _reject("HOLD_SNAPSHOT_NESTING_LIMIT")
    if value is None or type(value) in (str, bool, int, float):
        return
    if type(value) is list:
        for item in value:
            _require_json_value(item, depth + 1)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                _reject("HOLD_INVALID_SOURCE_METADATA")
            _require_json_value(item, depth + 1)
        return
    _reject("HOLD_INVALID_SOURCE_METADATA")


def _provenance_to_data(value: EmpiricalProvenance | None) -> dict[str, Any] | None:
    if value is None:
        return None
    if type(value) is not EmpiricalProvenance or type(value.metadata) is not dict:
        _reject("HOLD_INVALID_SOURCE_PROVENANCE")
    _require_json_value(value.metadata)
    return {
        "tool": value.tool,
        "target": value.target,
        "exit_code": value.exit_code,
        "execution_lock_sha256": value.execution_lock_sha256,
        "stdout_sha256": value.stdout_sha256,
        "recorded_at": value.recorded_at,
        "metadata": value.metadata,
    }


def _attribution_to_data(value: SourceAttribution) -> dict[str, Any]:
    if (type(value) is not SourceAttribution
            or type(value.source_type) is not SourceType
            or type(value.veracity_state) is not VeracityState
            or type(value.parent_attribution_ids) is not tuple
            or any(type(parent) is not str for parent in value.parent_attribution_ids)):
        _reject("HOLD_INVALID_SOURCE_ATTRIBUTION")
    return {
        "attribution_id": value.attribution_id,
        "source_type": value.source_type.value,
        "assertion": value.assertion,
        "veracity_state": value.veracity_state.value,
        "provenance": _provenance_to_data(value.provenance),
        "parent_attribution_ids": list(value.parent_attribution_ids),
        "created_at": value.created_at,
        "falsification_condition": value.falsification_condition,
    }


def encode_source_monitoring_data(guard: SourceMonitoringGuard) -> dict[str, Any]:
    """Return explicit historical records while the guard lock is held."""
    if type(guard) is not SourceMonitoringGuard:
        _reject("HOLD_INVALID_SOURCE_MONITORING_STATE")
    with guard._lock:
        if (type(guard._attributions) is not dict or type(guard._revisions) is not dict
                or len(guard._attributions) > _codec.MAX_SNAPSHOT_RECORDS
                or len(guard._revisions) > _codec.MAX_SNAPSHOT_RECORDS):
            _reject("HOLD_INVALID_SOURCE_MONITORING_STATE")
        if set(guard._attributions) != set(guard._revisions):
            _reject("HOLD_INCONSISTENT_SOURCE_HISTORY_INDEX")
        records = []
        total_revisions = 0
        for attribution_id, current in guard._attributions.items():
            revisions = guard._revisions[attribution_id]
            total_revisions += len(revisions) if type(revisions) is list else 0
            if total_revisions > _codec.MAX_SNAPSHOT_RECORDS:
                _reject("HOLD_SNAPSHOT_RECORD_LIMIT")
            if (type(attribution_id) is not str or type(revisions) is not list
                    or not revisions or len(revisions) > _codec.MAX_SNAPSHOT_RECORDS
                    or revisions[-1] != current):
                _reject("HOLD_INCONSISTENT_SOURCE_HISTORY_INDEX")
            records.append({
                "attribution_id": attribution_id,
                "revisions": [_attribution_to_data(item) for item in revisions],
            })
        return {"records": records}


def _decode_provenance(value: Any) -> EmpiricalProvenance | None:
    if value is None:
        return None
    raw = _object(value, "SOURCE_PROVENANCE", _PROVENANCE_KEYS)
    tool = _text(raw["tool"], "SOURCE_TOOL")
    target = _text(raw["target"], "SOURCE_TARGET", allow_empty=True)
    exit_code = raw["exit_code"]
    if type(exit_code) is not int:
        _reject("HOLD_INVALID_SOURCE_EXIT_CODE")
    if (not _source_hash(raw["execution_lock_sha256"])
            or not _source_hash(raw["stdout_sha256"])):
        _reject("HOLD_INVALID_SOURCE_PROVENANCE_HASH")
    recorded_at = _text(raw["recorded_at"], "SOURCE_RECORDED_AT")
    metadata = raw["metadata"]
    if type(metadata) is not dict:
        _reject("HOLD_INVALID_SOURCE_METADATA")
    try:
        return EmpiricalProvenance(
            tool=tool,
            target=target,
            exit_code=exit_code,
            execution_lock_sha256=raw["execution_lock_sha256"],
            stdout_sha256=raw["stdout_sha256"],
            recorded_at=recorded_at,
            metadata=metadata,
        )
    except (SourceMonitoringError, TypeError, ValueError) as exc:
        raise _codec.SnapshotRecoveryError("HOLD_INVALID_SOURCE_PROVENANCE") from exc


def _decode_attribution(value: Any) -> SourceAttribution:
    raw = _object(value, "SOURCE_ATTRIBUTION", _ATTRIBUTION_KEYS)
    attribution_id = _text(raw["attribution_id"], "ATTRIBUTION_ID")
    assertion = _text(raw["assertion"], "SOURCE_ASSERTION")
    source_type_text = _text(raw["source_type"], "SOURCE_TYPE")
    state_text = _text(raw["veracity_state"], "SOURCE_VERACITY_STATE")
    try:
        source_type = SourceType(source_type_text)
        veracity_state = VeracityState(state_text)
    except ValueError as exc:
        raise _codec.SnapshotRecoveryError("HOLD_INVALID_SOURCE_ENUM") from exc
    parents = raw["parent_attribution_ids"]
    if (type(parents) is not list or len(parents) > _codec.MAX_SNAPSHOT_RECORDS
            or any(type(parent) is not str or not parent.strip() for parent in parents)):
        _reject("HOLD_INVALID_SOURCE_PARENT_IDS")
    for parent in parents:
        _text(parent, "SOURCE_PARENT_ID")
    created_at = _text(raw["created_at"], "SOURCE_CREATED_AT")
    falsification = raw["falsification_condition"]
    if falsification is not None:
        falsification = _text(falsification, "SOURCE_FALSIFICATION_CONDITION", allow_empty=True)
    provenance = _decode_provenance(raw["provenance"])
    try:
        attribution = SourceAttribution(
            attribution_id=attribution_id,
            source_type=source_type,
            assertion=assertion,
            veracity_state=veracity_state,
            provenance=provenance,
            parent_attribution_ids=tuple(parents),
            created_at=created_at,
            falsification_condition=falsification,
        )
    except (SourceMonitoringError, TypeError, ValueError) as exc:
        raise _codec.SnapshotRecoveryError("HOLD_INVALID_SOURCE_ATTRIBUTION") from exc
    if source_type == SourceType.EMPIRICAL_OBSERVATION:
        if provenance is None:
            _reject("HOLD_INVALID_SOURCE_PROVENANCE")
        canonical_observation = (
            provenance.exit_code == 0
            and assertion == f"tool_exit:{provenance.tool}:{provenance.target}:0"
        )
        if (veracity_state == VeracityState.VERIFIED_EMPIRICAL and not canonical_observation
                or veracity_state == VeracityState.UNSUPPORTED and canonical_observation):
            _reject("HOLD_INVALID_SOURCE_EMPIRICAL_STATE")
    return attribution


def _immutable_fields(value: SourceAttribution) -> tuple[Any, ...]:
    return (
        value.attribution_id,
        value.source_type,
        value.assertion,
        value.provenance,
        value.created_at,
        value.falsification_condition,
    )


def _validate_history(
    attribution_id: str,
    revisions: list[SourceAttribution],
) -> None:
    first = revisions[0]
    if first.attribution_id != attribution_id or first.veracity_state not in _INITIAL_STATES[first.source_type]:
        _reject("HOLD_INVALID_SOURCE_INITIAL_STATE")
    if first.source_type in (SourceType.EMPIRICAL_OBSERVATION, SourceType.LEDGER_REPORT) and len(revisions) != 1:
        _reject("HOLD_INVALID_SOURCE_REVISION")
    for previous, current in zip(revisions, revisions[1:]):
        if (current.attribution_id != attribution_id
                or _immutable_fields(previous) != _immutable_fields(current)
                or current.parent_attribution_ids[:len(previous.parent_attribution_ids)]
                != previous.parent_attribution_ids
                or current == previous):
            _reject("HOLD_MALFORMED_SOURCE_REVISION")
        if previous.source_type not in (SourceType.INTERNAL_HYPOTHESIS, SourceType.EXTERNAL_TESTIMONY):
            _reject("HOLD_UNAUTHORIZED_SOURCE_STATUS_TRANSITION")
        suffix = current.parent_attribution_ids[len(previous.parent_attribution_ids):]
        if not suffix:
            _reject("HOLD_UNAUTHORIZED_SOURCE_STATUS_TRANSITION")
        allowed = {
            VeracityState.UNVERIFIED_HYPOTHESIS: {
                VeracityState.UNSUPPORTED,
                VeracityState.VERIFIED_EMPIRICAL,
            },
            VeracityState.EXTERNAL_ASSERTION: {
                VeracityState.UNSUPPORTED,
                VeracityState.VERIFIED_EMPIRICAL,
            },
            VeracityState.UNSUPPORTED: {
                VeracityState.UNSUPPORTED,
                VeracityState.VERIFIED_EMPIRICAL,
            },
            VeracityState.VERIFIED_EMPIRICAL: {
                VeracityState.VERIFIED_EMPIRICAL,
                VeracityState.UNSUPPORTED,
            },
        }
        if current.veracity_state not in allowed[previous.veracity_state]:
            _reject("HOLD_UNAUTHORIZED_SOURCE_STATUS_TRANSITION")


def decode_source_monitoring_data(
    value: Any,
    *,
    allowlisted_tools: set[str],
    semantic_nodes: dict[str, Any] | None = None,
) -> SourceMonitoringGuard:
    """Validate histories and rebuild current attribution indexes.

    Tool allowlists are caller-owned inputs and are never read from snapshot data.
    Recovered VERIFIED_EMPIRICAL states remain in history but have no active
    verification authority in the new process.
    """
    if type(allowlisted_tools) is not set or any(type(tool) is not str for tool in allowlisted_tools):
        _reject("HOLD_INVALID_SOURCE_TOOL_ALLOWLIST")
    source_data = _object(value, "SOURCE_MONITORING", _SOURCE_KEYS)
    records = source_data["records"]
    if type(records) is not list or len(records) > _codec.MAX_SNAPSHOT_RECORDS:
        _reject("HOLD_SOURCE_RECORD_LIMIT")
    histories: dict[str, list[SourceAttribution]] = {}
    total_revisions = 0
    for raw_record in records:
        record = _object(raw_record, "SOURCE_RECORD", _RECORD_KEYS)
        attribution_id = _text(record["attribution_id"], "ATTRIBUTION_ID")
        if attribution_id in histories:
            _reject("HOLD_DUPLICATE_SOURCE_ATTRIBUTION_ID")
        raw_revisions = record["revisions"]
        if (type(raw_revisions) is not list or not raw_revisions
                or len(raw_revisions) > _codec.MAX_SNAPSHOT_RECORDS):
            _reject("HOLD_INVALID_SOURCE_HISTORY")
        total_revisions += len(raw_revisions)
        if total_revisions > _codec.MAX_SNAPSHOT_RECORDS:
            _reject("HOLD_SNAPSHOT_RECORD_LIMIT")
        revisions = [_decode_attribution(item) for item in raw_revisions]
        _validate_history(attribution_id, revisions)
        histories[attribution_id] = revisions

    # The existing working-memory recall path records one typed-by-convention
    # semantic parent (recall_<node_id>). It is a historical memory reference,
    # never an empirical supporting attribution. Validate it against the
    # jointly recovered engine; do not accept arbitrary missing parent IDs.
    semantic_nodes = {} if semantic_nodes is None else semantic_nodes
    if set(histories).intersection(semantic_nodes):
        _reject("HOLD_AMBIGUOUS_SOURCE_REFERENCE")
    for attribution_id, revisions in histories.items():
        initial = revisions[0]
        for revision in revisions:
            for position, parent in enumerate(revision.parent_attribution_ids):
                if parent in histories:
                    continue
                node = semantic_nodes.get(parent)
                if not (
                    position == 0
                    and initial.parent_attribution_ids == (parent,)
                    and initial.source_type == SourceType.INTERNAL_HYPOTHESIS
                    and attribution_id == "recall_" + parent
                    and node is not None
                    and initial.assertion == node.assertion
                ):
                    _reject("HOLD_DANGLING_SOURCE_REFERENCE")

    attributions = {attribution_id: revisions[-1] for attribution_id, revisions in histories.items()}
    for attribution_id, revisions in histories.items():
        for previous, current in zip(revisions, revisions[1:]):
            if current.veracity_state not in (
                VeracityState.UNSUPPORTED,
                VeracityState.VERIFIED_EMPIRICAL,
            ):
                continue
            suffix = current.parent_attribution_ids[len(previous.parent_attribution_ids):]
            has_matching_observation = any(
                parent in attributions
                and attributions[parent].source_type == SourceType.EMPIRICAL_OBSERVATION
                and attributions[parent].veracity_state == VeracityState.VERIFIED_EMPIRICAL
                and attributions[parent].assertion == current.assertion
                for parent in suffix
            )
            if (current.veracity_state == VeracityState.VERIFIED_EMPIRICAL
                    and not has_matching_observation):
                _reject("HOLD_VERIFIED_SOURCE_WITHOUT_EVIDENCE")
    guard = SourceMonitoringGuard(allowlisted_tools=set(allowlisted_tools))

    guard._attributions = attributions
    guard._revisions = histories
    guard._active_verified_ids = set()
    for attribution_id, attr in attributions.items():
        if attr.veracity_state != VeracityState.VERIFIED_EMPIRICAL:
            continue
        if attr.source_type not in (SourceType.INTERNAL_HYPOTHESIS, SourceType.EXTERNAL_TESTIMONY):
            continue
        has_historical_support = any(
            parent in attributions
            and parent in attributions
                and attributions[parent].source_type == SourceType.EMPIRICAL_OBSERVATION
            and attributions[parent].veracity_state == VeracityState.VERIFIED_EMPIRICAL
            and attributions[parent].assertion == attr.assertion
            for parent in attr.parent_attribution_ids
        )
        if not has_historical_support:
            _reject("HOLD_VERIFIED_SOURCE_WITHOUT_EVIDENCE")
    # Parent lists only grow across revisions. Checking the final graph
    # checks all historical edges as well. One linear traversal avoids
    # quadratic work on a long, otherwise valid attribution chain.
    incoming = {key: 0 for key in attributions}
    children = {key: [] for key in attributions}
    for key, attr in attributions.items():
        for parent in attr.parent_attribution_ids:
            if parent in attributions:
                incoming[key] += 1
                children[parent].append(key)
    ready = [key for key, degree in incoming.items() if degree == 0]
    visited = 0
    while ready:
        key = ready.pop()
        visited += 1
        for child in children[key]:
            incoming[child] -= 1
            if incoming[child] == 0:
                ready.append(child)
    if visited != len(attributions):
        _reject("HOLD_CIRCULAR_SOURCE_DEPENDENCY")
    return guard
