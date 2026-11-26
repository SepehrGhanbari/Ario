"""Failure-domain-aware R63 quorum model.

RESEARCH_ONLY. Consumes pre-verified receipts; does NOT perform cryptographic
signature, freshness, persistence, continuity or external-custody verification.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

REQUIRED_DOMAINS = ("operator", "admin", "key_custody", "state_backup")

@dataclass(frozen=True)
class Witness:
    witness_id: str
    key_fingerprint: str
    domains: Mapping[str, str]
    evidence_ref: str
    verified: bool = True

@dataclass(frozen=True)
class Receipt:
    witness_id: str
    key_fingerprint: str
    policy_hash: str
    proposal_hash: str
    sequence: int
    signature_valid: bool
    fresh: bool
    durable: bool
    continuity_proven: bool
    readback_proven: bool = False

@dataclass(frozen=True)
class QuorumPolicy:
    policy_hash: str
    roster: Mapping[str, Witness]
    min_witnesses: int = 3
    min_distinct_domains: int = 3
    required_domain_classes: tuple[str, ...] = REQUIRED_DOMAINS
    read_quorum: int = 3
    write_quorum: int = 3
    max_faulty_domains: int = 1
    expected_sequence: int = 11

@dataclass(frozen=True)
class Decision:
    accepted: bool
    status: str
    witness_count: int
    domain_counts: Mapping[str, int]
    accepted_witnesses: tuple[str, ...]
    reasons: tuple[str, ...]

def quorum_intersection_holds(n_domains: int, read_q: int, write_q: int,
                              max_faulty_domains: int) -> bool:
    """Any read/write quorum pair intersects in more than f independent domains."""
    if min(n_domains, read_q, write_q) < 1 or max_faulty_domains < 0:
        return False
    if read_q > n_domains or write_q > n_domains:
        return False
    return read_q + write_q > n_domains + max_faulty_domains

def validate_policy(policy: QuorumPolicy) -> tuple[str, ...]:
    errors = []
    if not policy.policy_hash:
        errors.append("MISSING_POLICY_HASH")
    if len(policy.roster) < policy.min_witnesses:
        errors.append("ROSTER_TOO_SMALL")
    if policy.min_witnesses < 1 or policy.min_distinct_domains < 1:
        errors.append("INVALID_THRESHOLDS")
    if policy.expected_sequence < 1 or policy.read_quorum < 1 or policy.write_quorum < 1:
        errors.append("INVALID_SEQUENCE_OR_QUORUM")
    if not policy.required_domain_classes:
        errors.append("NO_REQUIRED_FAILURE_DOMAINS")
    seen_keys = set()
    for wid, w in policy.roster.items():
        if wid != w.witness_id or not wid:
            errors.append("WITNESS_ID_MISMATCH")
        if not w.verified or not w.evidence_ref:
            errors.append(f"UNVERIFIED_ROSTER:{wid}")
        if not w.key_fingerprint or w.key_fingerprint in seen_keys:
            errors.append(f"MISSING_OR_DUPLICATE_KEY:{wid}")
        seen_keys.add(w.key_fingerprint)
        for cls in policy.required_domain_classes:
            value = w.domains.get(cls)
            if not value or value.upper() in {"UNKNOWN", "UNRESOLVED", "TBD"}:
                errors.append(f"UNRESOLVED_DOMAIN:{wid}:{cls}")
    operator_domains = {
        w.domains.get("operator") for w in policy.roster.values()
        if w.domains.get("operator")
    }
    if not quorum_intersection_holds(
        len(operator_domains), policy.read_quorum, policy.write_quorum,
        policy.max_faulty_domains
    ):
        errors.append("READ_WRITE_INTERSECTION_UNSAFE")
    return tuple(errors)

def evaluate(policy: QuorumPolicy, proposal_hash: str,
             receipts: Iterable[Receipt], *, mode: str) -> Decision:
    """Count unique witness keys and unique labels in every required domain.

    Multiple keys controlled by one organization/admin/backup controller cannot
    increase that domain's vote. Any untrusted, stale or incomplete receipt fails.
    """
    reasons = list(validate_policy(policy))
    if mode not in ("read", "write"):
        reasons.append("INVALID_MODE")
    valid = {}
    seen_keys = set()
    for r in receipts:
        w = policy.roster.get(r.witness_id)
        if w is None:
            reasons.append(f"UNKNOWN_WITNESS:{r.witness_id}")
            continue
        if r.witness_id in valid:
            reasons.append(f"DUPLICATE_WITNESS:{r.witness_id}")
            continue
        if r.key_fingerprint in seen_keys:
            reasons.append(f"DUPLICATE_RECEIPT_KEY:{r.witness_id}")
            continue
        seen_keys.add(r.key_fingerprint)
        checks = (
            (r.key_fingerprint == w.key_fingerprint, "KEY_MISMATCH"),
            (r.policy_hash == policy.policy_hash, "POLICY_MISMATCH"),
            (r.proposal_hash == proposal_hash, "PROPOSAL_MISMATCH"),
            (r.sequence == policy.expected_sequence, "SEQUENCE_MISMATCH"),
            (r.signature_valid, "BAD_SIGNATURE"),
            (r.fresh, "STALE_READ"),
            (r.durable, "NOT_DURABLE"),
            (r.continuity_proven, "CONTINUITY_UNPROVEN"),
            (mode != "read" or r.readback_proven, "READBACK_UNPROVEN"),
        )
        failed = [code for ok, code in checks if not ok]
        if failed:
            reasons.extend(f"{r.witness_id}:{code}" for code in failed)
            continue
        valid[r.witness_id] = w

    domain_counts = {
        cls: len({w.domains.get(cls) for w in valid.values() if w.domains.get(cls)})
        for cls in policy.required_domain_classes
    }
    witness_count = len(valid)
    mode_quorum = policy.read_quorum if mode == "read" else policy.write_quorum
    if witness_count < max(policy.min_witnesses, mode_quorum):
        reasons.append("INSUFFICIENT_WITNESSES")
    if domain_counts.get("operator", 0) < mode_quorum:
        reasons.append("INSUFFICIENT_INDEPENDENT_OPERATOR_DOMAINS")
    for cls, count in domain_counts.items():
        if cls != "operator" and count < policy.min_distinct_domains:
            reasons.append(f"INSUFFICIENT_INDEPENDENT_{cls.upper()}_DOMAINS")
    if reasons:
        return Decision(False, "HOLD_DOMAIN_QUORUM", witness_count,
                        domain_counts, tuple(sorted(valid)), tuple(sorted(set(reasons))))
    return Decision(True, "DOMAIN_QUORUM_ACCEPTED_RESEARCH_ONLY",
                    witness_count, domain_counts, tuple(sorted(valid)), ())

def build_policy(policy_hash: str, rows: Sequence[tuple[str, str, str, str, str, str]],
                 *, read_q=3, write_q=3, f=1) -> QuorumPolicy:
    """Rows: witness_id, key_fingerprint, operator, admin, key_custody, state_backup."""
    roster = {}
    for row in rows:
        if len(row) != 6:
            raise ValueError("each row must contain 6 fields")
        wid, key, operator, admin, key_custody, state_backup = row
        if wid in roster:
            raise ValueError("duplicate witness id")
        roster[wid] = Witness(
            wid, key,
            {"operator": operator, "admin": admin,
             "key_custody": key_custody, "state_backup": state_backup},
            evidence_ref=f"pinned-evidence:{wid}",
            verified=True,
        )
    return QuorumPolicy(policy_hash, roster, min_witnesses=3,
                        min_distinct_domains=3, read_quorum=read_q,
                        write_quorum=write_q, max_faulty_domains=f)
