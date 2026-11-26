"""RERE-01 v0.4: explicit data-only history for the existing synthetic comparator.

Caller-retained SHA256 checks exact bytes, not source authentication, completeness
or independent freshness. No writer, live-memory admission, or authority API.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict, dataclass

from core.memory_consolidation import _loads_ledger_line, _json_structure_markers
from core.schema import Assessment, Reference, SupportTarget
from research.rere01.revision_comparator_v0_2 import (
    LabAssessment, LabObservation, LabContractError, SyntheticPolicy, Projection,
    Record, MAX_RECORDS, _deduplicate, project,
)

FORMAT = "ario.rere01.synthetic-assessment-history.v1"
MAX_BYTES = 256 * 1024
MAX_TEXT = 4096


def _check(ok, message):
    if not ok:
        raise LabContractError(message)


def _canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _text(value):
    _check(type(value) is str and len(value) <= MAX_TEXT, "invalid text")
    return value


def _policy_data(policy):
    _check(type(policy) is SyntheticPolicy, "invalid policy type")
    for value in (policy.profile, policy.event_id, policy.event_time,
                  policy.calibration_observed_at):
        _text(value)
    for pairs in (policy.pinned_roots, policy.calibration_pairs):
        _check(type(pairs) is tuple and len(pairs) <= MAX_RECORDS, "invalid policy pairs")
        for pair in pairs:
            _check(type(pair) is tuple and len(pair) == 2, "invalid policy pair")
            for value in pair:
                _text(value)
    return asdict(policy)


def _record_data(rec):
    if type(rec) is LabObservation:
        for key, value in vars(rec).items():
            if key != "seq":
                _text(value)
        return {"kind":"OBSERVATION", "payload":asdict(rec)}
    _check(type(rec) is LabAssessment and type(rec.assessment) is Assessment,
           "invalid assessment type")
    a = rec.assessment
    _text(rec.reason_code)
    for name in ("assessment_id", "assessment_version", "rule_version",
                 "condition_evaluation", "assessment_basis", "scope"):
        _text(getattr(a, name))
    _check(a.requested_use is None and type(a.target) is SupportTarget,
           "no requested evidence use or untyped target")
    _text(a.target.property_id)
    _check(type(a.admissible_evidence_refs) is tuple
           and 1 <= len(a.admissible_evidence_refs) <= MAX_RECORDS, "invalid evidence refs")
    for ref in (*a.admissible_evidence_refs, a.target.subject_reference):
        _check(type(ref) is Reference, "invalid reference type")
        _text(ref.reference_id)
        _text(ref.reference_type)
    return {"kind":"ASSESSMENT", "payload":asdict(rec)}


def _row_links(rec, seen):
    """Pin each declared dependency to exact earlier record bytes in this log."""
    refs = []
    if type(rec) is LabObservation and rec.target_record_id:
        refs.append(("CALIBRATION_TARGET", rec.target_record_id, "OBSERVATION"))
    if type(rec) is LabAssessment:
        a = rec.assessment
        target = a.target.subject_reference
        if target.reference_type == "ASSESSMENT":
            refs.append(("PRIOR_ASSESSMENT", target.reference_id, "ASSESSMENT"))
        for ref in a.admissible_evidence_refs:
            _check(ref.reference_type == "LAB_OBSERVATION", "unsupported evidence reference")
            refs.append(("DECLARED_EVIDENCE", ref.reference_id, "OBSERVATION"))
    links = []
    for role, rid, kind in refs:
        _check(rid in seen and seen[rid][0] == kind, "missing or wrong-kind prior dependency")
        links.append({"role":role, "record_id":rid, "record_sha256":seen[rid][1]})
    return links


def encode_history(records: tuple[Record, ...], policy: SyntheticPolicy) -> bytes:
    _check(type(records) is tuple and len(records) <= MAX_RECORDS, "history count/type")
    policy_data = _policy_data(policy)
    for rec in records:
        _record_data(rec)
    ordered = _deduplicate(records)
    project(ordered, policy)
    seen = {}
    rows = []
    previous = _sha(_canonical({"format":FORMAT, "policy":policy_data}))
    for rec in ordered:
        data = _record_data(rec)
        row = {"previous_sha256":previous, "record":data,
               "links":_row_links(rec, seen)}
        previous = _sha(_canonical(row))
        rows.append(row)
        seen[rec.record_id] = (data["kind"], previous)
    raw = _canonical({"format":FORMAT, "policy":policy_data, "rows":rows})
    _check(len(raw) <= MAX_BYTES, "history byte bound")
    return raw


def _decode_policy(data):
    _check(type(data) is dict, "policy object required")
    p = dict(data)
    for name in ("pinned_roots", "calibration_pairs"):
        _check(type(p[name]) is list, "policy pairs array required")
        p[name] = tuple(tuple(pair) for pair in p[name])
    return SyntheticPolicy(**p)


def _decode_record(data):
    _check(type(data) is dict and type(data["payload"]) is dict, "record object required")
    p = dict(data["payload"])
    if data["kind"] == "OBSERVATION":
        return LabObservation(**p)
    _check(data["kind"] == "ASSESSMENT", "unknown record kind")
    a = dict(p["assessment"])
    _check(type(a["admissible_evidence_refs"]) is list, "evidence refs array required")
    a["admissible_evidence_refs"] = tuple(Reference(**v) for v in a["admissible_evidence_refs"])
    target = a["target"]
    a["target"] = SupportTarget(Reference(**target["subject_reference"]), target["property_id"])
    p["assessment"] = Assessment(**a)
    return LabAssessment(**p)


@dataclass(frozen=True)
class RecoveredHistory:
    records: tuple[Record, ...]
    policy: SyntheticPolicy
    projection: Projection
    sha256: str

    def as_of(self, count: int) -> Projection:
        _check(type(count) is int and 0 <= count <= len(self.records), "invalid historical cutoff")
        return project(self.records[:count], self.policy)


def restore_history(raw: bytes, *, expected_sha256: str) -> RecoveredHistory:
    _check(type(raw) is bytes and len(raw) <= MAX_BYTES, "history byte bound/type")
    _check(type(expected_sha256) is str and len(expected_sha256) == 64
           and all(c in "0123456789abcdef" for c in expected_sha256), "invalid history pin")
    digest = _sha(raw)
    _check(hmac.compare_digest(digest, expected_sha256), "history digest mismatch")
    try:
        _json_structure_markers(raw, 100000)
        d = _loads_ledger_line(raw.decode("ascii"))
        _check(type(d) is dict and d["format"] == FORMAT, "history format")
        _check(type(d["rows"]) is list and len(d["rows"]) <= MAX_RECORDS, "history row bound")
        policy = _decode_policy(d["policy"])
        records = tuple(_decode_record(row["record"]) for row in d["rows"])
        # Exact canonical reconstruction validates all row hashes, links,
        # ordering, policy shape and fields. No silent duplicate or extra field.
        _check(encode_history(records, policy) == raw, "noncanonical or altered history")
        return RecoveredHistory(records, policy, project(records, policy), digest)
    except LabContractError:
        raise
    except (ValueError, KeyError, TypeError, AttributeError, RecursionError, OverflowError) as exc:
        raise LabContractError("invalid history schema") from exc
    except Exception as exc:
        raise LabContractError("invalid history input") from exc


def append_history(raw: bytes, *, expected_sha256: str,
                   additions: tuple[Record, ...]) -> bytes:
    before = restore_history(raw, expected_sha256=expected_sha256)
    _check(type(additions) is tuple and len(additions) <= MAX_RECORDS, "addition bound/type")
    after = encode_history(before.records + additions, before.policy)
    verified = restore_history(after, expected_sha256=_sha(after))
    _check(verified.records[:len(before.records)] == before.records, "not append-only")
    return after
