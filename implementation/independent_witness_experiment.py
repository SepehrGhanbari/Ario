"""ARIO-TB-002: bounded synthetic historical-witness comparison.

This module neither creates nor authenticates witnesses. Its immutable-looking
inputs are supplied by a laboratory controller; attacker exclusion and custody
independence are assumptions, NOT enforcement. All results are non-authorizing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any


PROFILE = "ARIO-WITNESS-EXPERIMENT-0.1"
MAX_WITNESSES = 2
MAX_CHECKPOINT_BYTES = 4096
MAX_CANDIDATE_BYTES = 65536
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_CHECKPOINT_KEYS = frozenset({
    "profile", "domain", "ledger_id", "epoch", "branch_id", "record_count",
    "prefix_byte_count", "prefix_sha256", "head_sha256",
    "previous_checkpoint_sha256", "test_identity", "key_descriptor_sha256",
    "checkpoint_sha256",
})
_COMMITMENT_FIELDS = (
    "domain", "ledger_id", "epoch", "branch_id", "record_count",
    "prefix_byte_count", "prefix_sha256", "head_sha256",
    "previous_checkpoint_sha256",
)


@dataclass(frozen=True)
class WitnessEnvelope:
    """A LABORATORY declaration; self-digest is NOT an authentic signature."""

    role: str
    witness_id: str
    custody_domain_label: str
    checkpoint_bytes: bytes
    parent_checkpoint_bytes: bytes | None
    snapshot_reference: str
    capture_sequence: int
    declared_provenance: str
    test_control_digest: str


@dataclass(frozen=True)
class WitnessControl:
    """Frozen only by experiment convention, NOT independent production custody."""

    anchors: tuple[WitnessEnvelope, ...]
    context: Any  # checkpoint_prefix_experiment.Context at runtime
    symbolic_bindings: tuple[tuple[str, bytes], ...]
    known_floor: int | None
    laboratory_isolated_roles: tuple[str, ...] = ()


@dataclass(frozen=True)
class WitnessCase:
    candidate_bytes: bytes | None
    presented: tuple[WitnessEnvelope, ...]
    control: WitnessControl
    candidate_key_descriptor: bytes | None
    attacker_capability: str
    compromised_witness_roles: tuple[str, ...] = ()
    controller_compromised: bool = False


@dataclass(frozen=True)
class Finding:
    status: str
    reason: str


@dataclass(frozen=True)
class WitnessInspection:
    role: str
    witness_id: str
    snapshot_integrity: Finding
    checkpoint_correspondence: Finding
    scope_binding: Finding
    witness_identity_claim: Finding
    checkpoint_floor: Finding
    local_hash_validity: Finding
    descriptor_binding: Finding
    experimental_oracle_evidence: Finding
    authenticity: Finding = field(default_factory=lambda: Finding("UNKNOWN", "NO_REAL_WITNESS_AUTHENTICATION"))
    comparison_verdict: str = "INCONCLUSIVE"


@dataclass(frozen=True)
class WitnessComparisonReport:
    inspections: tuple[WitnessInspection, ...]
    cross_witness_commitment_relation: Finding
    candidate_history_relation: Finding
    known_floor_relation: Finding
    aggregate_verdict: str
    conflict_detected: bool
    custody_independence: str
    attacker_capability: str
    reason_codes: tuple[str, ...]
    independence_basis: str = "ASSUMED_FOR_EXPERIMENT"
    kind: str = field(default="EXPERIMENTAL_WITNESS_COMPARISON", init=False)
    cryptographic_witness_authenticity: str = field(default="NOT_CHECKED", init=False)
    historical_custody_independence: str = field(default="NOT_ESTABLISHED", init=False)
    human_authorization: str = field(default="NOT_EVALUATED", init=False)
    evidence_admission: str = field(default="NOT_EVALUATED", init=False)
    historical_event_truth: str = field(default="UNKNOWN", init=False)
    entity_continuity: str = field(default="UNKNOWN", init=False)
    ontological_continuity: str = field(default="UNKNOWN", init=False)
    production_historical_continuity: str = field(default="INCONCLUSIVE", init=False)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _text(value: Any, maximum: int = 128) -> bool:
    return type(value) is str and 0 < len(value) <= maximum and all(32 <= ord(c) < 127 for c in value)


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        if key in out:
            raise ValueError("DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _bad_number(_value: str) -> None:
    raise ValueError("UNSUPPORTED_JSON_NUMBER")


def _commitment(raw: bytes) -> tuple[Any, ...] | None:
    """Parse minimal commitment only; full byte/hash validation belongs to base comparator."""
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_CHECKPOINT_BYTES:
        return None
    try:
        obj = json.loads(raw.decode("ascii"), object_pairs_hook=_pairs,
                         parse_float=_bad_number, parse_constant=_bad_number,
                         parse_int=lambda n: int(n) if len(n) <= 10 else _bad_number(n))
        if type(obj) is not dict or set(obj) != _CHECKPOINT_KEYS:
            return None
        if json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii") != raw:
            return None
        if obj.get("profile") != "ARIO-PREFIX-EXPERIMENT-0.1":
            return None
        fields = tuple(obj[k] for k in _COMMITMENT_FIELDS)
        if any(not _text(obj[k]) for k in ("domain", "ledger_id", "epoch", "branch_id", "test_identity")):
            return None
        if any(type(v) not in (str, int, type(None)) for v in fields):
            return None
        if type(obj["record_count"]) is not int or obj["record_count"] not in (2, 4):
            return None
        if type(obj["prefix_byte_count"]) is not int or not 1 <= obj["prefix_byte_count"] <= MAX_CANDIDATE_BYTES:
            return None
        for key in ("prefix_sha256", "head_sha256", "checkpoint_sha256", "key_descriptor_sha256"):
            if type(obj.get(key)) is not str or not _HEX.fullmatch(obj[key]):
                return None
        parent = obj["previous_checkpoint_sha256"]
        if parent is not None and (type(parent) is not str or not _HEX.fullmatch(parent)):
            return None
        body = {k: v for k, v in obj.items() if k != "checkpoint_sha256"}
        body_raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        if _sha(body_raw) != obj["checkpoint_sha256"]:
            return None
        return fields
    except (ValueError, KeyError, TypeError, UnicodeError, OverflowError, RecursionError):
        return None


def envelope_digest(envelope: WitnessEnvelope) -> str:
    """Reproducible LABORATORY checksum; cannot establish historical enrollment."""
    record = {
        "profile": PROFILE,
        "role": envelope.role,
        "witness_id": envelope.witness_id,
        "custody_domain_label": envelope.custody_domain_label,
        "checkpoint_sha256": _sha(envelope.checkpoint_bytes),
        "parent_sha256": _sha(envelope.parent_checkpoint_bytes) if envelope.parent_checkpoint_bytes is not None else None,
        "snapshot_reference": envelope.snapshot_reference,
        "capture_sequence": envelope.capture_sequence,
        "declared_provenance": envelope.declared_provenance,
    }
    return _sha(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii"))


def seal_test_envelope(*, role: str, witness_id: str, custody_domain_label: str,
                       checkpoint_bytes: bytes, parent_checkpoint_bytes: bytes | None,
                       snapshot_reference: str, capture_sequence: int,
                       declared_provenance: str) -> WitnessEnvelope:
    """Test-fixture builder only. Self-sealing NEVER creates a trusted witness."""
    pre = WitnessEnvelope(role, witness_id, custody_domain_label, checkpoint_bytes,
                          parent_checkpoint_bytes, snapshot_reference, capture_sequence,
                          declared_provenance, "")
    return WitnessEnvelope(role, witness_id, custody_domain_label, checkpoint_bytes,
                           parent_checkpoint_bytes, snapshot_reference, capture_sequence,
                           declared_provenance, envelope_digest(pre))


def _envelope_ok(env: Any) -> bool:
    if type(env) is not WitnessEnvelope:
        return False
    if not all(_text(getattr(env, name)) for name in (
        "role", "witness_id", "custody_domain_label", "snapshot_reference", "declared_provenance"
    )):
        return False
    if type(env.capture_sequence) is not int or not 0 <= env.capture_sequence <= 999999:
        return False
    if type(env.checkpoint_bytes) is not bytes or not 0 < len(env.checkpoint_bytes) <= MAX_CHECKPOINT_BYTES:
        return False
    if env.parent_checkpoint_bytes is not None and (
        type(env.parent_checkpoint_bytes) is not bytes or
        not 0 < len(env.parent_checkpoint_bytes) <= MAX_CHECKPOINT_BYTES
    ):
        return False
    return type(env.test_control_digest) is str and _HEX.fullmatch(env.test_control_digest) is not None


def _finding(status: str, reason: str) -> Finding:
    return Finding(status, reason)


def _unknown_inspection(anchor: WitnessEnvelope, reason: str) -> WitnessInspection:
    u = _finding("UNKNOWN", reason)
    return WitnessInspection(anchor.role, anchor.witness_id, u, u, u, u, u, u, u, u)


def verify_witnesses(case: WitnessCase) -> WitnessComparisonReport:
    """Read-only, deterministic, bounded synthesis of Ario prefix comparisons."""
    u = _finding("UNKNOWN", "NOT_ESTABLISHED")
    def invalid(reason: str) -> WitnessComparisonReport:
        return WitnessComparisonReport((), u, u, u, "INVALID_INPUT", False, "UNKNOWN",
                                       getattr(case, "attacker_capability", "INVALID"), (reason,),
                                       "NOT_ESTABLISHED")

    if type(case) is not WitnessCase or type(case.control) is not WitnessControl:
        return invalid("INVALID_CASE_OR_CONTROL_TYPE")
    control = case.control
    if (
        type(control.anchors) is not tuple or len(control.anchors) != MAX_WITNESSES or
        type(case.presented) is not tuple or len(case.presented) > MAX_WITNESSES or
        type(control.symbolic_bindings) is not tuple or len(control.symbolic_bindings) > MAX_WITNESSES or
        type(control.laboratory_isolated_roles) is not tuple or
        len(control.laboratory_isolated_roles) > MAX_WITNESSES or
        type(case.compromised_witness_roles) is not tuple or
        len(case.compromised_witness_roles) > MAX_WITNESSES or
        type(case.controller_compromised) is not bool or
        control.known_floor not in (None, 2, 4) or type(control.known_floor) is bool or
        not _text(case.attacker_capability)
    ):
        return invalid("INVALID_BOUND_OR_PROFILE")
    if case.candidate_bytes is not None and (
        type(case.candidate_bytes) is not bytes or len(case.candidate_bytes) > MAX_CANDIDATE_BYTES
    ):
        return invalid("INVALID_CANDIDATE")
    if case.candidate_key_descriptor is not None and (
        type(case.candidate_key_descriptor) is not bytes or len(case.candidate_key_descriptor) > 128
    ):
        return invalid("INVALID_DESCRIPTOR")
    if any(not _envelope_ok(e) or envelope_digest(e) != e.test_control_digest
           for e in control.anchors):
        return invalid("INVALID_FROZEN_CONTROLLER_ANCHOR")
    if any(not _envelope_ok(e) for e in case.presented):
        return invalid("INVALID_PRESENTED_ENVELOPE")
    roles = [a.role for a in control.anchors]
    if len(set(roles)) != MAX_WITNESSES or len(set(a.witness_id for a in control.anchors)) != MAX_WITNESSES:
        return invalid("AMBIGUOUS_CONTROL_ROLES_OR_IDENTITIES")
    # Different role labels must not count one witness's checkpoint twice.
    # This is consistency with a laboratory declaration, NOT real enrollment.
    for anchor in control.anchors:
        if _commitment(anchor.checkpoint_bytes) is None:
            return invalid("INVALID_FROZEN_CHECKPOINT")
        try:
            if json.loads(anchor.checkpoint_bytes)["test_identity"] != anchor.witness_id:
                return invalid("FROZEN_CHECKPOINT_IDENTITY_ROLE_MISMATCH")
            if anchor.parent_checkpoint_bytes is not None and (
                _commitment(anchor.parent_checkpoint_bytes) is None or
                json.loads(anchor.parent_checkpoint_bytes)["test_identity"] != anchor.witness_id
            ):
                return invalid("FROZEN_PARENT_IDENTITY_ROLE_MISMATCH")
        except (ValueError, KeyError, TypeError):
            return invalid("INVALID_FROZEN_WITNESS_IDENTITY")
    if (len(set(a.snapshot_reference for a in control.anchors)) != MAX_WITNESSES or
        len(set(e.role for e in case.presented)) != len(case.presented) or
        any(e.role not in roles for e in case.presented) or
        len(set(control.laboratory_isolated_roles)) != len(control.laboratory_isolated_roles) or
        any(role not in roles for role in control.laboratory_isolated_roles) or
        len(set(case.compromised_witness_roles)) != len(case.compromised_witness_roles) or
        any(type(role) is not str or role not in roles for role in case.compromised_witness_roles)):
        return invalid("AMBIGUOUS_OR_UNENROLLED_WITNESS")
    if (
        any(type(pair) is not tuple or len(pair) != 2 or not _text(pair[0]) or
            type(pair[1]) is not bytes or len(pair[1]) > 128 for pair in control.symbolic_bindings) or
        len(set(pair[0] for pair in control.symbolic_bindings)) != len(control.symbolic_bindings)
    ):
        return invalid("INVALID_SYMBOLIC_BINDINGS")
    # Import the real Ario comparator in the target repository. Never fabricate
    # a successful comparison if its dependency is unavailable.
    try:
        from checkpoint_prefix_experiment import compare_prefix, OracleSnapshot
    except ImportError:
        return invalid("BASE_COMPARATOR_NOT_AVAILABLE")

    presented = {e.role: e for e in case.presented}
    anchors = {a.role: a for a in control.anchors}
    inspected: list[WitnessInspection] = []
    reasons: set[str] = set()
    # Output order is controller role order, independent of presented input order.
    for role in roles:
        anchor = anchors[role]
        observed = presented.get(role)
        if observed is None:
            inspected.append(_unknown_inspection(anchor, "WITNESS_UNAVAILABLE"))
            reasons.add("WITNESS_UNAVAILABLE")
            continue
        anchor_fields = (
            anchor.role, anchor.witness_id, anchor.custody_domain_label,
            anchor.checkpoint_bytes, anchor.parent_checkpoint_bytes,
            anchor.snapshot_reference, anchor.capture_sequence, anchor.declared_provenance,
        )
        observed_fields = (
            observed.role, observed.witness_id, observed.custody_domain_label,
            observed.checkpoint_bytes, observed.parent_checkpoint_bytes,
            observed.snapshot_reference, observed.capture_sequence, observed.declared_provenance,
        )
        snapshot_match = observed_fields == anchor_fields and observed.test_control_digest == anchor.test_control_digest and envelope_digest(observed) == observed.test_control_digest
        snapshot = _finding("MATCH" if snapshot_match else "MISMATCH",
                            "MATCHES_FROZEN_LAB_SNAPSHOT" if snapshot_match else "DIFFERS_FROM_FROZEN_LAB_SNAPSHOT")
        identity = _finding("MATCH" if observed.witness_id == anchor.witness_id else "MISMATCH",
                            "DECLARED_ID_MATCHES_LAB_ROLE" if observed.witness_id == anchor.witness_id else "DECLARED_ID_SUBSTITUTED")
        ref = _commitment(anchor.checkpoint_bytes)
        if ref is None:
            return invalid("INVALID_FROZEN_CHECKPOINT")
        # Controller controls the oracle; the observed envelope is a declaration.
        oracle_bytes = ((anchor.parent_checkpoint_bytes,) if anchor.parent_checkpoint_bytes is not None else ()) + (anchor.checkpoint_bytes,)
        try:
            result = compare_prefix(
                case.candidate_bytes, observed.checkpoint_bytes,
                OracleSnapshot(checkpoints=oracle_bytes,
                               key_bindings=control.symbolic_bindings,
                               known_floor=control.known_floor),
                control.context,
                candidate_key_descriptor=case.candidate_key_descriptor,
            )
        except (TypeError, ValueError, AttributeError) as exc:
            # A malfunction is not a positive correspondence.
            return invalid("COMPARATOR_ERROR_" + type(exc).__name__.upper())
        try:
            prefix = _finding(result.prefix_correspondence.status, result.prefix_correspondence.reason)
            binding = _finding(result.checkpoint_binding.status, result.checkpoint_binding.reason)
            floor = _finding(result.known_checkpoint_floor.status, result.known_checkpoint_floor.reason)
            local = _finding(result.local_hash_validity.status, result.local_hash_validity.reason)
            desc = _finding(result.symbolic_descriptor_binding.status, result.symbolic_descriptor_binding.reason)
            oracle = _finding(result.oracle_evidence.status, result.oracle_evidence.reason)
            declared_verdict = result.property_verdict
        except (AttributeError, TypeError):
            return invalid("INVALID_COMPARATOR_RESULT")
        if declared_verdict not in ("PASS", "FAIL", "INCONCLUSIVE"):
            return invalid("UNSUPPORTED_COMPARATOR_VERDICT")
        inspected.append(WitnessInspection(role, anchor.witness_id, snapshot, prefix, binding,
                                           identity, floor, local, desc, oracle,
                                           comparison_verdict=declared_verdict))
        if snapshot.status == "MISMATCH":
            reasons.add("FROZEN_WITNESS_DISCREPANCY")
        if prefix.status == "MISMATCH":
            reasons.add("CHECKPOINT_PREFIX_DISCREPANCY")
        if floor.status == "MISMATCH":
            reasons.add("KNOWN_FLOOR_DISCREPANCY")
        if local.status == "MISMATCH":
            reasons.add("LOCAL_CHAIN_INVALID")
        if identity.status == "MISMATCH":
            reasons.add("WITNESS_ID_SUBSTITUTION")
        if desc.status == "MISMATCH":
            reasons.add("SYMBOLIC_DESCRIPTOR_MISMATCH")

    a, b = control.anchors
    ca, cb = _commitment(a.checkpoint_bytes), _commitment(b.checkpoint_bytes)
    if ca is None or cb is None:
        return invalid("INVALID_FROZEN_CHECKPOINT")
    # Witness-specific parent checkpoint hashes may differ even when the
    # underlying historical prefix is identical. Compare the *semantic bytes
    # committed to*, including parent prefix semantics, not identity metadata
    # or the opaque parent checkpoint body digest alone.
    def parent_semantics(envelope: WitnessEnvelope, child: tuple[Any, ...]):
        if child[4] == 2:
            return () if envelope.parent_checkpoint_bytes is None and child[8] is None else None
        if envelope.parent_checkpoint_bytes is None:
            return None
        parsed = _commitment(envelope.parent_checkpoint_bytes)
        if parsed is None or parsed[:4] != child[:4] or parsed[4] != 2:
            return None
        try:
            parent_body = json.loads(envelope.parent_checkpoint_bytes)
            if parent_body["checkpoint_sha256"] != child[8]:
                return None
        except (ValueError, KeyError, TypeError):
            return None
        return parsed[:8]

    pa, pb = parent_semantics(a, ca), parent_semantics(b, cb)
    if len(presented) < MAX_WITNESSES:
        relation = _finding("UNKNOWN", "INSUFFICIENT_WITNESS_RESPONSES")
    elif ca[:5] != cb[:5]:  # external scope and record count
        relation = _finding("UNKNOWN", "NONCOMPARABLE_SCOPE_OR_RECORD_COUNT")
    elif pa is None or pb is None:
        relation = _finding("UNKNOWN", "UNRESOLVED_PARENT_COMMITMENT")
    elif ca[:8] == cb[:8] and pa == pb:
        relation = _finding("AGREE", "FROZEN_HISTORY_COMMITMENTS_EQUAL")
    else:
        relation = _finding("CONFLICT", "FROZEN_HISTORY_COMMITMENTS_DIFFER")
        reasons.add("FROZEN_WITNESS_CONFLICT")
    statuses = [w.checkpoint_correspondence.status for w in inspected]
    if any(x == "MISMATCH" for x in statuses):
        history = _finding("MISMATCH", "CANDIDATE_DIFFERS_FROM_DECLARED_WITNESS")
    elif len(inspected) == 2 and all(x == "MATCH" for x in statuses):
        history = _finding("MATCH", "CANDIDATE_MATCHES_DECLARED_PREFIXES_ONLY")
    else:
        history = _finding("UNKNOWN", "INSUFFICIENT_COMPARABLE_WITNESS_INPUTS")
    floor_statuses = [w.checkpoint_floor.status for w in inspected]
    if "MISMATCH" in floor_statuses:
        known_floor = _finding("MISMATCH", "BELOW_KNOWN_FLOOR")
    elif len(floor_statuses) == 2 and all(x == "MATCH" for x in floor_statuses):
        known_floor = _finding("MATCH", "SUPPLIED_FLOOR_SATISFIED")
    else:
        known_floor = _finding("UNKNOWN", "FRESHNESS_NOT_ESTABLISHED")
    compromised = bool(case.compromised_witness_roles) or case.controller_compromised
    if (
        not compromised and
        set(control.laboratory_isolated_roles) == set(roles) and
        a.custody_domain_label != b.custody_domain_label
    ):
        custody = "ASSUMED_FOR_EXPERIMENT"
    else:
        custody = "UNKNOWN"
    if relation.status == "CONFLICT":
        aggregate = "UNRESOLVED_CONFLICT"
    elif any(w.snapshot_integrity.status == "MISMATCH" for w in inspected) or any(
        w.witness_identity_claim.status == "MISMATCH" for w in inspected
    ):
        aggregate = "DEFINITE_DISCREPANCY"
    elif any(w.comparison_verdict == "FAIL" or w.local_hash_validity.status == "MISMATCH"
             or w.checkpoint_floor.status == "MISMATCH" for w in inspected):
        aggregate = "DEFINITE_DISCREPANCY"
    elif len(inspected) == 2 and relation.status == "AGREE" and all(
        w.comparison_verdict == "PASS" and w.snapshot_integrity.status == "MATCH"
        for w in inspected
    ):
        aggregate = "CONDITIONAL_CORRESPONDENCE"
    else:
        aggregate = "INCONCLUSIVE"
    return WitnessComparisonReport(
        tuple(inspected), relation, history, known_floor, aggregate,
        relation.status == "CONFLICT", custody, case.attacker_capability,
        tuple(sorted(reasons)),
        "COMPROMISED_BY_SCENARIO" if compromised else "ASSUMED_FOR_EXPERIMENT",
    )
