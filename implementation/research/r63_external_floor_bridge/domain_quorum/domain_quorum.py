"""Failure-domain-aware R63 quorum model.

RESEARCH_ONLY. Consumes pre-verified receipts; does NOT perform cryptographic
signature, freshness, persistence, continuity or external-custody verification.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
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
class QuorumDomainProfile:
    witness_count: int
    threshold: int
    minimum_domains_per_quorum: int
    minimum_domain_intersection: int
    minimum_quorum_example: tuple[str, ...]
    intersection_example: tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]

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

def weighted_quorum_domain_profile(witness_domains: Mapping[str, str],
                                   threshold: int) -> QuorumDomainProfile:
    """Audit a key-weighted quorum after collapsing keys to failure domains.

    Returns the minimum number of domains in any threshold-sized quorum and
    the minimum domain intersection between any two threshold-sized quorums.
    This is policy arithmetic only; it does not verify the supplied mapping.
    """
    ids = tuple(sorted(witness_domains))
    if not ids or len(ids) > 12 or threshold < 1 or threshold > len(ids):
        raise ValueError("invalid witness roster or threshold")
    subsets = [tuple(c) for c in combinations(ids, threshold)]
    domain_sets = [frozenset(witness_domains[w] for w in subset) for subset in subsets]
    minimum_domains = min(len(s) for s in domain_sets)
    q_index = next(i for i, s in enumerate(domain_sets) if len(s) == minimum_domains)
    minimum_intersection = len(ids) + 1
    pair = (0, 0)
    for i, left in enumerate(domain_sets):
        for j in range(i, len(domain_sets)):
            size = len(left & domain_sets[j])
            if size < minimum_intersection:
                minimum_intersection = size
                pair = (i, j)
    left_ids, right_ids = subsets[pair[0]], subsets[pair[1]]
    shared = tuple(sorted(domain_sets[pair[0]] & domain_sets[pair[1]]))
    return QuorumDomainProfile(
        len(ids), threshold, minimum_domains, minimum_intersection,
        subsets[q_index], (left_ids, right_ids, shared)
    )

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
    # Check intersection in every control/failure-domain projection, not just
    # the number of witness keys or the operator-name projection.
    for cls in policy.required_domain_classes:
        domains = {
            w.domains.get(cls) for w in policy.roster.values()
            if w.domains.get(cls)
        }
        if not quorum_intersection_holds(
            len(domains), policy.read_quorum, policy.write_quorum,
            policy.max_faulty_domains
        ):
            errors.append(f"READ_WRITE_INTERSECTION_UNSAFE:{cls}")
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
    for cls, count in domain_counts.items():
        required = max(policy.min_distinct_domains, mode_quorum)
        if count < required:
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
