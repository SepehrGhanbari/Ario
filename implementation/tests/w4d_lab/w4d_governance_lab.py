"""W4-D, draft 0.1. Pure, bounded, SYNTHETIC procedural checks only.

No real identity, custody, signatures, independent quorum, authorization, consensus,
source verification, privacy enforcement, evidence admission or truth assessment.
Assumed lab fields are UNTRUSTED declarations. No writes, network, clocks or keys.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9._:-]{0,63}\Z", re.ASCII)
DIGEST = re.compile(r"[a-f0-9]{64}\Z", re.ASCII)
MAX_TICK = 2**63 - 1
MAX_BALLOTS = 32
MAX_MEMBERS = 15
MAX_HISTORY = 128
MOTION_PROFILE = "W4D-LAB-0.2"  # fixture-only; not an adopted governance protocol
MOTION_HASH_DOMAIN = b"ARIO-W4D-LAB-MOTION-0.2\x00"
ALLOWED_LAB_STEPS = frozenset({
    "HOLD", "REJECTED", "FROZEN_RECOMMENDED",
    "LAB_FREEZE_RECOMMENDATION", "LAB_RECOVERY_REVIEW_RECOMMENDATION",
    "LAB_PROCEDURAL_REVIEW_RECOMMENDATION",
    "LAB_APPEAL_FOR_INDEPENDENT_SCREENING",
    "LAB_MINIMIZED_REQUEST_FOR_SEPARATE_AUTHORIZATION",
    "LAB_HISTORY_STRUCTURALLY_CONSISTENT",
})

THRESHOLDS = {
    "REVIEW_CANDIDATE": 3,  # proposed synthetic example out of five
    "REVOKE_REVIEW_GRANT": 3,
    "FREEZE": 2,
    "UNFREEZE": 4,
    "ROTATE_ROOT": 4,
}


def _tok(x: object) -> bool:
    return type(x) is str and bool(TOKEN.fullmatch(x))


def _digest(x: object) -> bool:
    return type(x) is str and bool(DIGEST.fullmatch(x))


def _tick(x: object) -> bool:
    return type(x) is int and 0 <= x <= MAX_TICK


@dataclass(frozen=True)
class Finding:
    status: str  # NEVER an authority: UNKNOWN or REJECTED
    rule: str
    lab_step: str = "HOLD"
    authentic_identity: str = "UNKNOWN"
    real_controller_independence: str = "UNKNOWN"
    reviewer_authorization: str = "UNKNOWN"
    evidence_admission: str = "NOT_EVALUATED"
    claim_truth: str = "UNKNOWN"

    def __post_init__(self) -> None:
        if (type(self.status) is not str
                or self.status not in {"UNKNOWN", "REJECTED"}
                or type(self.lab_step) is not str
                or self.lab_step not in ALLOWED_LAB_STEPS
                or self.authentic_identity != "UNKNOWN"
                or self.real_controller_independence != "UNKNOWN"
                or self.reviewer_authorization != "UNKNOWN"
                or self.evidence_admission != "NOT_EVALUATED"
                or self.claim_truth != "UNKNOWN"):
            raise ValueError("LAB_CANNOT_GRANT_REAL_AUTHORITY_OR_TRUTH")


def _hold(rule: str, step: str = "HOLD") -> Finding:
    return Finding("UNKNOWN", rule, step)


def _reject(rule: str) -> Finding:
    return Finding("REJECTED", rule, "REJECTED")


@dataclass(frozen=True)
class Steward:
    steward_id: str
    declared_control_group: str


@dataclass(frozen=True)
class Vote:
    ballot_id: str
    steward_id: str
    motion_digest: str
    epoch: int
    choice: str  # SUPPORT or OPPOSE


@dataclass(frozen=True)
class Motion:
    motion_id: str
    action: str
    digest: str
    epoch: int
    proposer_control_group: str
    source_control_group: str
    candidate_scope: str
    audience: str
    nonce: str
    valid_from_tick: int
    valid_until_tick: int
    policy_version: str = MOTION_PROFILE


def mock_motion_digest(m: Motion) -> str:
    """Exact typed, domain-separated **mock** binding (NOT a signature).

    The caller can fabricate every field and digest. Correct bytes alone cannot
    authenticate an identity, authority, witnessed event or historical nonce.
    """
    if (type(m) is not Motion
            or any(not _tok(x) for x in (
                m.motion_id, m.proposer_control_group, m.source_control_group,
                m.candidate_scope, m.audience, m.nonce))
            or type(m.action) is not str or m.action not in THRESHOLDS
            or m.policy_version != MOTION_PROFILE
            or not _tick(m.epoch) or not _tick(m.valid_from_tick)
            or not _tick(m.valid_until_tick)
            or m.valid_from_tick > m.valid_until_tick):
        raise ValueError("W4D_MOCK_MOTION_SHAPE")
    # Fixed ordered JSON ARRAY with ASCII tokens. Exact integer values use
    # versioned INT:decimal strings; JS Numbers cannot represent all uint63 ticks.
    # 'digest' itself is excluded so the binding is non-self-referential.
    fields = [m.policy_version, m.motion_id, m.action, m.candidate_scope,
              f"INT:{m.epoch}", m.proposer_control_group, m.source_control_group,
              m.audience, m.nonce, f"INT:{m.valid_from_tick}",
              f"INT:{m.valid_until_tick}"]
    material = json.dumps(fields, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(MOTION_HASH_DOMAIN + material).hexdigest()


@dataclass(frozen=True)
class CouncilFixture:
    # All input fields are mock declarations, never certified facts.
    members: tuple[Steward, ...]
    votes: tuple[Vote, ...]
    motion: Motion
    observed_tick: int
    current_epoch: int
    roster_complete_claimed: bool = True
    fresh_revocations_claimed: bool = True
    clock_checked_claimed: bool = True
    fork_declared: bool = False
    partition_declared: bool = False
    currently_frozen: bool = False
    root_compromise_declared: bool = False
    independent_recovery_attestation_claimed: bool = False
    post_compromise_epoch_claimed: bool = False


def evaluate_council(f: object) -> Finding:
    """Simulate a procedural recommendation. NEVER a real quorum attestation."""
    if type(f) is not CouncilFixture:
        return _reject("W4D_MALFORMED_COUNCIL")
    m = f.motion
    if type(m) is not Motion or type(f.members) is not tuple or type(f.votes) is not tuple:
        return _reject("W4D_MALFORMED_COUNCIL")
    if (len(f.members) != 5 or len(f.votes) > MAX_BALLOTS
            or not _tick(f.observed_tick) or not _tick(f.current_epoch)
            or type(f.roster_complete_claimed) is not bool
            or type(f.fresh_revocations_claimed) is not bool
            or type(f.clock_checked_claimed) is not bool
            or type(f.fork_declared) is not bool
            or type(f.partition_declared) is not bool
            or type(f.currently_frozen) is not bool
            or type(f.root_compromise_declared) is not bool
            or type(f.independent_recovery_attestation_claimed) is not bool
            or type(f.post_compromise_epoch_claimed) is not bool):
        return _reject("W4D_BOUNDS_OR_TYPE")
    if (not _tok(m.motion_id) or type(m.action) is not str or m.action not in THRESHOLDS
            or not _digest(m.digest) or not _tick(m.epoch)
            or not _tok(m.proposer_control_group)
            or not _tok(m.source_control_group)
            or not _tok(m.candidate_scope) or not _tok(m.audience)
            or not _tok(m.nonce) or not _tick(m.valid_from_tick)
            or not _tick(m.valid_until_tick)
            or m.valid_from_tick > m.valid_until_tick
            or m.policy_version != MOTION_PROFILE):
        return _reject("W4D_MOTION_SHAPE_OR_FORBIDDEN_ACTION")
    if m.digest != mock_motion_digest(m):
        return _hold("W4D_MOTION_DIGEST_NOT_BOUND")
    if not m.valid_from_tick <= f.observed_tick <= m.valid_until_tick:
        return _hold("W4D_MOTION_OUTSIDE_DECLARED_VALIDITY")
    by_id: dict[str, Steward] = {}
    for item in f.members:
        if (type(item) is not Steward or not _tok(item.steward_id)
                or not _tok(item.declared_control_group)
                or item.steward_id in by_id):
            return _reject("W4D_ROSTER_SHAPE_OR_DUPLICATE")
        by_id[item.steward_id] = item
    if m.epoch != f.current_epoch:
        return _reject("W4D_STALE_OR_REPLAYED_EPOCH")
    seen_ballots: set[str] = set()
    seen_stewards: set[str] = set()
    yes_groups: set[str] = set()
    all_voting_groups: set[str] = set()
    for b in f.votes:
        if (type(b) is not Vote or not _tok(b.ballot_id)
                or not _tok(b.steward_id) or not _digest(b.motion_digest)
                or not _tick(b.epoch) or type(b.choice) is not str
                or b.choice not in {"SUPPORT", "OPPOSE"}):
            return _reject("W4D_BALLOT_SHAPE")
        if b.ballot_id in seen_ballots or b.steward_id in seen_stewards:
            return _reject("W4D_DUPLICATE_BALLOT_OR_VOTER")
        seen_ballots.add(b.ballot_id)
        seen_stewards.add(b.steward_id)
        if b.steward_id not in by_id:
            return _reject("W4D_UNENROLLED_VOTER")
        if b.motion_digest != m.digest or b.epoch != m.epoch:
            return _reject("W4D_VOTE_SCOPE_OR_EPOCH_REPLAY")
        group = by_id[b.steward_id].declared_control_group
        if b.choice == "SUPPORT" and group in {m.proposer_control_group, m.source_control_group}:
            if m.action == "REVIEW_CANDIDATE":
                return _hold("W4D_REVIEWER_PROPOSER_SOURCE_CONFLICT")
            if m.action in {"UNFREEZE", "ROTATE_ROOT"}:
                return _hold("W4D_RECOVERY_INTEREST_CONFLICT")
        # Detect shared declared control EVEN across opposing ballots, in any order.
        if group in all_voting_groups:
            return _hold("W4D_SHARED_DECLARED_CONTROLLER")
        all_voting_groups.add(group)
        if b.choice == "SUPPORT":
            yes_groups.add(group)
    if f.fork_declared or f.partition_declared:
        return _hold("W4D_FORK_OR_PARTITION", "FROZEN_RECOMMENDED")
    if not (f.roster_complete_claimed and f.fresh_revocations_claimed and f.clock_checked_claimed):
        return _hold("W4D_MISSING_FRESH_ROSTER_CLOCK_OR_REVOCATION")
    if f.root_compromise_declared and m.action not in {"FREEZE", "UNFREEZE", "ROTATE_ROOT"}:
        return _hold("W4D_DECLARED_COMPROMISE", "FROZEN_RECOMMENDED")
    if f.currently_frozen and m.action not in {"UNFREEZE", "FREEZE", "ROTATE_ROOT"}:
        return _hold("W4D_FROZEN", "FROZEN_RECOMMENDED")
    if m.action in {"UNFREEZE", "ROTATE_ROOT"} and not (
            f.independent_recovery_attestation_claimed and f.post_compromise_epoch_claimed):
        return _hold("W4D_RECOVERY_ATTESTATION_OR_EPOCH_MISSING")
    if m.action == "UNFREEZE" and not f.currently_frozen:
        return _reject("W4D_UNFREEZE_WITHOUT_FREEZE")
    if len(yes_groups) < THRESHOLDS[m.action]:
        return _hold("W4D_CONDITIONAL_QUORUM_NOT_MET")
    if m.action == "FREEZE":
        return _hold("W4D_LAB_QUORUM_ONLY", "LAB_FREEZE_RECOMMENDATION")
    if m.action in {"UNFREEZE", "ROTATE_ROOT"}:
        return _hold("W4D_LAB_QUORUM_ONLY", "LAB_RECOVERY_REVIEW_RECOMMENDATION")
    return _hold("W4D_LAB_QUORUM_ONLY", "LAB_PROCEDURAL_REVIEW_RECOMMENDATION")


@dataclass(frozen=True)
class AppealFixture:
    appeal_id: str
    original_decision_id: str
    appellant_ref: str
    grounds_code: str
    original_panel_groups: tuple[str, ...]
    proposed_appeal_panel_groups: tuple[str, ...]
    case_is_known_claimed: bool
    source_privacy_restricted: bool
    external_auth_claimed: bool
    previous_appeal_ids: tuple[str, ...] = ()
    original_panel_complete_claimed: bool = False  # untrusted claim, explicit gate


def evaluate_appeal(a: object) -> Finding:
    if type(a) is not AppealFixture:
        return _reject("W4D_APPEAL_MALFORMED")
    if (not all(_tok(x) for x in (a.appeal_id, a.original_decision_id, a.appellant_ref, a.grounds_code))
            or type(a.original_panel_groups) is not tuple
            or type(a.proposed_appeal_panel_groups) is not tuple
            or type(a.previous_appeal_ids) is not tuple
            or type(a.case_is_known_claimed) is not bool
            or type(a.source_privacy_restricted) is not bool
            or type(a.external_auth_claimed) is not bool
            or type(a.original_panel_complete_claimed) is not bool
            or len(a.original_panel_groups) > MAX_MEMBERS
            or len(a.proposed_appeal_panel_groups) != 3
            or len(a.previous_appeal_ids) > MAX_HISTORY
            or any(not _tok(x) for seq in (a.original_panel_groups, a.proposed_appeal_panel_groups, a.previous_appeal_ids) for x in seq)):
        return _reject("W4D_APPEAL_SHAPE")
    if len(set(a.previous_appeal_ids)) != len(a.previous_appeal_ids):
        return _reject("W4D_APPEAL_HISTORY_DUPLICATE")
    if a.appeal_id in a.previous_appeal_ids:
        return _reject("W4D_APPEAL_REPLAY")
    if len(set(a.proposed_appeal_panel_groups)) != 3:
        return _hold("W4D_APPEAL_PANEL_SHARED_CONTROLLER")
    if set(a.proposed_appeal_panel_groups) & set(a.original_panel_groups):
        return _hold("W4D_APPEAL_REVIEWER_CONFLICT")
    if (not a.original_panel_complete_claimed
            or len(a.original_panel_groups) < 2
            or len(set(a.original_panel_groups)) != len(a.original_panel_groups)):
        return _hold("W4D_APPEAL_ORIGINAL_PANEL_UNRESOLVED")
    if not a.case_is_known_claimed:
        return _hold("W4D_APPEAL_ORIGINAL_CASE_UNRESOLVED")
    # These are merely supplied declarations, never real authentication or disclosure permission.
    if not a.external_auth_claimed:
        return _hold("W4D_APPEAL_SUBJECT_BINDING_UNKNOWN")
    return _hold("W4D_APPEAL_INTAKE_ONLY", "LAB_APPEAL_FOR_INDEPENDENT_SCREENING")


PUBLIC_META = frozenset({"CASE_STATE", "RULE_ID", "POLICY_VERSION"})
RESTRICTED_META = frozenset({"REDACTED_POINTER", "APPEAL_RECEIPT"})
SECRET_FIELDS = frozenset({"RAW_PAYLOAD", "PERSONAL_ID", "SOURCE_LOCATION", "WITNESS_NAME", "CONTACT"})


@dataclass(frozen=True)
class DisclosureFixture:
    case_id: str
    actor_ref: str
    purpose: str
    fields: tuple[str, ...]
    consent: str  # GRANTED, WITHDRAWN, UNKNOWN -- caller-declared
    access_expired_claimed: bool = False
    reviewer_authorization_claimed: bool = False
    linked_appeal_open: bool = False


def evaluate_disclosure(d: object) -> Finding:
    if type(d) is not DisclosureFixture:
        return _reject("W4D_PRIVACY_MALFORMED")
    if (not _tok(d.case_id) or not _tok(d.actor_ref)
            or type(d.purpose) is not str or d.purpose not in {"CASE_AUDIT", "APPEAL_SCREENING"}
            or type(d.fields) is not tuple or not 1 <= len(d.fields) <= 8
            or any(type(x) is not str or not _tok(x) for x in d.fields)
            or len(set(d.fields)) != len(d.fields)
            or type(d.consent) is not str or d.consent not in {"GRANTED", "WITHDRAWN", "UNKNOWN"}
            or type(d.access_expired_claimed) is not bool
            or type(d.reviewer_authorization_claimed) is not bool
            or type(d.linked_appeal_open) is not bool):
        return _reject("W4D_PRIVACY_SHAPE")
    if set(d.fields) & SECRET_FIELDS or not set(d.fields) <= (PUBLIC_META | RESTRICTED_META):
        return _reject("W4D_PRIVACY_OVERDISCLOSURE")
    if d.consent == "WITHDRAWN" or d.access_expired_claimed:
        return _reject("W4D_PRIVACY_WITHDRAWN_OR_EXPIRED")
    if d.consent != "GRANTED":
        return _hold("W4D_PRIVACY_CONSENT_UNRESOLVED")
    if (set(d.fields) & RESTRICTED_META) and not d.reviewer_authorization_claimed:
        return _hold("W4D_RESTRICTED_METADATA_AUTH_UNKNOWN")
    if d.purpose == "APPEAL_SCREENING" and not d.linked_appeal_open:
        return _hold("W4D_NO_OPEN_APPEAL")
    return _hold("W4D_DECLARATIONS_NOT_PROOF", "LAB_MINIMIZED_REQUEST_FOR_SEPARATE_AUTHORIZATION")


@dataclass(frozen=True)
class AuditHeader:
    sequence: int
    prev_hash: str
    event_kind: str
    case_ref: str
    payload_commitment: str
    # NO personal names, raw witness payload, identity credential or unhashed pseudonym.


def _canonical_header(h: AuditHeader) -> bytes:
    return json.dumps([h.sequence, h.prev_hash, h.event_kind, h.case_ref, h.payload_commitment],
                      ensure_ascii=True, separators=(",", ":")).encode("ascii")


def lab_entry_hash(h: AuditHeader) -> str:
    """SHA-256 consistency within mock metadata, NOT tamper-proof historical custody."""
    return hashlib.sha256(b"ARIO-W4D-MOCK-AUDIT-0.1\x00" + _canonical_header(h)).hexdigest()


def check_mock_history(entries: object, declared_digests: object) -> Finding:
    if type(entries) is not tuple or type(declared_digests) is not tuple:
        return _reject("W4D_AUDIT_SHAPE")
    if len(entries) != len(declared_digests) or len(entries) > MAX_HISTORY:
        return _reject("W4D_AUDIT_BOUNDS")
    if not entries:
        return _hold("W4D_EMPTY_HISTORY")
    prev = "0" * 64
    for i, (h, claimed) in enumerate(zip(entries, declared_digests)):
        if (type(h) is not AuditHeader or not _tick(h.sequence) or h.sequence != i
                or not _digest(h.prev_hash) or not _tok(h.event_kind)
                or not _tok(h.case_ref) or not _digest(h.payload_commitment)
                or not _digest(claimed)):
            return _reject("W4D_AUDIT_BAD_HEADER")
        if h.prev_hash != prev:
            return _reject("W4D_AUDIT_BROKEN_PREDECESSOR")
        digest = lab_entry_hash(h)
        if claimed != digest:
            return _reject("W4D_AUDIT_MISMATCH")
        prev = digest
    return _hold("W4D_LOCAL_HASH_CONSISTENCY_ONLY", "LAB_HISTORY_STRUCTURALLY_CONSISTENT")
