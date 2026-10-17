"""W4-E OFFLINE structural-only preflight. NOT identity authentication or authority.

No keys, signatures, trusted clock, revocation registry, network, evidence admission,
real source proof or truth evaluation. All inputs are caller-supplied lab assertions.
"""
from __future__ import annotations
from dataclasses import dataclass
import re

TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9._:-]{0,63}\Z", re.ASCII)
HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
MAX_STEWARDS = 9
MAX_WITNESSES = 16


def token(s: object) -> bool:
    return type(s) is str and TOKEN.fullmatch(s) is not None


@dataclass(frozen=True)
class Steward:
    principal_id: str
    key_id: str
    declared_controller: str
    declared_issuer: str


@dataclass(frozen=True)
class Witness:
    witness_id: str
    source_id: str
    declared_controller: str
    upstream_observation_id: str | None
    event_id: str


@dataclass(frozen=True)
class Case:
    case_id: str
    action: str
    audience: str
    digest: str
    proposer_id: str
    reviewer_id: str
    declared_stewards: tuple[Steward, ...]
    declared_witnesses: tuple[Witness, ...]
    stated_grant_scope: str
    current_registry_digest: str | None
    presented_registry_digest: str | None
    revocation_state: str
    consent: str
    appeal_path_declared: bool
    identity_binding_claimed: bool = False
    clock_freshness_claimed: bool = False


@dataclass(frozen=True)
class Finding:
    status: str  # UNKNOWN or REJECTED; NEVER VERIFIED
    rule: str
    procedural_step: str = "HOLD"  # HOLD or LAB_PACKET_READY_FOR_EXTERNAL_REVIEW
    identity: str = "UNKNOWN"
    controller_independence: str = "UNKNOWN"
    witness_independence: str = "UNKNOWN"
    review_authorization: str = "UNKNOWN"
    admission: str = "NOT_EVALUATED"
    truth: str = "UNKNOWN"

    def __post_init__(self):
        if (type(self.status) is not str or self.status not in {"UNKNOWN", "REJECTED"}
            or type(self.rule) is not str or not token(self.rule)
            or type(self.procedural_step) is not str
            or self.procedural_step not in {"HOLD", "LAB_PACKET_READY_FOR_EXTERNAL_REVIEW"}
            or any(type(value) is not str or value != required for value, required in (
                (self.identity, "UNKNOWN"),
                (self.controller_independence, "UNKNOWN"),
                (self.witness_independence, "UNKNOWN"),
                (self.review_authorization, "UNKNOWN"),
                (self.admission, "NOT_EVALUATED"),
                (self.truth, "UNKNOWN")))):
            raise ValueError("W4E_CANNOT_PROMOTE_AUTHORITY_OR_TRUTH")


def unknown(rule: str, step: str = "HOLD") -> Finding:
    return Finding("UNKNOWN", rule, step)


def reject(rule: str) -> Finding:
    return Finding("REJECTED", rule)


def inspect(case: object) -> Finding:
    """Diagnostic precedence: structure > explicit adverse evidence > missing trust.

    LAB_PACKET_READY_FOR_EXTERNAL_REVIEW is NOT enrollment, permission, verified
    independence, evidence, or permission to send private material to anyone.
    """
    if type(case) is not Case:
        return reject("W4E_BAD_CASE_TYPE")
    c = case
    if (any(not token(v) for v in (c.case_id, c.action, c.audience,
                                    c.proposer_id, c.reviewer_id, c.stated_grant_scope))
            or c.action != "REVIEW_CANDIDATE" or c.stated_grant_scope != c.action
            or type(c.digest) is not str or HEX.fullmatch(c.digest) is None
            or type(c.declared_stewards) is not tuple
            or type(c.declared_witnesses) is not tuple
            or not 1 <= len(c.declared_stewards) <= MAX_STEWARDS
            or not 1 <= len(c.declared_witnesses) <= MAX_WITNESSES
            or type(c.revocation_state) is not str
            or c.revocation_state not in {"REVOKED", "UNKNOWN", "FRESH_CLAIMED"}
            or type(c.consent) is not str
            or c.consent not in {"GRANTED_CLAIMED", "WITHDRAWN", "UNKNOWN"}
            or type(c.appeal_path_declared) is not bool
            or type(c.identity_binding_claimed) is not bool
            or type(c.clock_freshness_claimed) is not bool
            or any(x is not None and (type(x) is not str or HEX.fullmatch(x) is None)
                   for x in (c.current_registry_digest, c.presented_registry_digest))):
        return reject("W4E_BAD_ENVELOPE_OR_ACTION")
    for s in c.declared_stewards:
        if type(s) is not Steward or any(not token(x) for x in
              (s.principal_id, s.key_id, s.declared_controller, s.declared_issuer)):
            return reject("W4E_BAD_STEWARD_DECLARATION")
    for w in c.declared_witnesses:
        if type(w) is not Witness or any(not token(x) for x in
              (w.witness_id, w.source_id, w.declared_controller, w.event_id)):
            return reject("W4E_BAD_WITNESS_DECLARATION")
        if w.upstream_observation_id is not None and not token(w.upstream_observation_id):
            return reject("W4E_BAD_UPSTREAM_REFERENCE")
    if c.proposer_id == c.reviewer_id:
        return reject("W4E_SELF_REVIEW")
    if c.revocation_state == "REVOKED":
        return reject("W4E_DECLARED_REVOCATION")
    if c.consent == "WITHDRAWN":
        return reject("W4E_DECLARED_CONSENT_WITHDRAWN")
    principals = [s.principal_id for s in c.declared_stewards]
    keys = [s.key_id for s in c.declared_stewards]
    controllers = [s.declared_controller for s in c.declared_stewards]
    issuers = [s.declared_issuer for s in c.declared_stewards]
    if len(set(principals)) != len(principals) or len(set(keys)) != len(keys):
        return reject("W4E_DUPLICATE_PRINCIPAL_OR_KEY")
    if len(set(controllers)) != len(controllers):
        return unknown("W4E_KNOWN_DECLARED_SHARED_CONTROLLER")
    if len(set(issuers)) != len(issuers):
        return unknown("W4E_KNOWN_DECLARED_SHARED_ISSUER")
    # Declared cross-role collisions are review blockers, NOT proof of one
    # real actor or common economic control. Role namespaces are unverified.
    # Only prevent the synthetic packet-ready hint; do not mint identity facts.
    if set(issuers) & (set(principals) | set(controllers) | {c.proposer_id, c.reviewer_id}):
        return unknown("W4E_DECLARED_ISSUER_ROLE_OVERLAP")
    if {c.proposer_id, c.reviewer_id} & set(controllers):
        return unknown("W4E_DECLARED_GOVERNANCE_ROLE_OVERLAP")
    if c.proposer_id in principals or c.reviewer_id in principals:
        return unknown("W4E_ROLE_CONFLICT_REQUIRES_REVIEW")
    witness_ids = [w.witness_id for w in c.declared_witnesses]
    if len(set(witness_ids)) != len(witness_ids):
        return reject("W4E_DUPLICATE_WITNESS_ID")
    # Equality is a declared label collision only; distinct labels do not prove
    # different people. Deny an overly helpful packet-readiness recommendation.
    if set(witness_ids) & (set(principals) | set(controllers) | set(issuers)
                          | {c.proposer_id, c.reviewer_id}):
        return unknown("W4E_DECLARED_WITNESS_ID_ROLE_OVERLAP")
    sources = [w.source_id for w in c.declared_witnesses]
    ancestors = [w.upstream_observation_id for w in c.declared_witnesses]
    if len(set(sources)) != len(sources):
        return unknown("W4E_KNOWN_DECLARED_SHARED_SOURCE")
    if any(a is None for a in ancestors):
        return unknown("W4E_INCOMPLETE_DECLARED_PROVENANCE")
    if len(set(ancestors)) != len(ancestors):
        return unknown("W4E_KNOWN_DECLARED_SHARED_ANCESTOR")
    witness_controllers = {w.declared_controller for w in c.declared_witnesses}
    if len(witness_controllers) != len(c.declared_witnesses):
        return unknown("W4E_KNOWN_DECLARED_SHARED_WITNESS_CONTROL")
    if witness_controllers & set(controllers):
        return unknown("W4E_WITNESS_AND_GOVERNANCE_CONTROL_OVERLAP")
    if witness_controllers & (set(issuers) | set(principals) | {c.proposer_id, c.reviewer_id}):
        return unknown("W4E_DECLARED_WITNESS_ROLE_OVERLAP")
    if len({w.event_id for w in c.declared_witnesses}) > 1:
        return unknown("W4E_EVENT_INSTANCE_NOT_COMPARABLE")
    if (c.current_registry_digest is None or c.presented_registry_digest is None
            or c.current_registry_digest != c.presented_registry_digest):
        return unknown("W4E_REGISTRY_MISSING_OR_FORKED")
    if c.revocation_state != "FRESH_CLAIMED":
        return unknown("W4E_REVOCATION_FRESHNESS_UNESTABLISHED")
    if c.consent != "GRANTED_CLAIMED":
        return unknown("W4E_CONSENT_UNRESOLVED")
    if not c.appeal_path_declared:
        return unknown("W4E_NO_DECLARED_APPEAL_PATH")
    if not c.identity_binding_claimed or not c.clock_freshness_claimed:
        return unknown("W4E_AUTH_OR_TIME_NOT_ESTABLISHED")
    # This lab's purpose includes independence/plurality; a singleton packet
    # cannot be casually labeled ready for independent plural review. Two
    # declared records are a MINIMUM diagnostic, never sufficient proof.
    if len(c.declared_stewards) < 2 or len(c.declared_witnesses) < 2:
        return unknown("W4E_DECLARED_PLURALITY_INSUFFICIENT")
    # Injected `True` flags are untrusted declarations, even when all pass.
    return unknown("W4E_MOCK_DECLARATIONS_ONLY", "LAB_PACKET_READY_FOR_EXTERNAL_REVIEW")
