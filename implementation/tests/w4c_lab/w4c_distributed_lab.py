"""Ario W4-C: OFFLINE simulation of replicated *declared* trust/custody facts.

This is NOT a source-authentication verifier, real trusted registry, network,
consensus engine, signer, quorum, root enrolment, reviewer authorization,
positive evidence-admission path, or truth assessment. Real Ed25519 verification
is delegated to the unmodified W4-B *test* module using injected public keys.
No keys are generated/stored here. No I/O, network, persistent writes, or clocks.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Mapping

import w4b_profile_lab as w4b

MAX_PEERS = 8
MAX_RECORDS = 32
MAX_REPORTS = 16
MAX_REVOCATIONS = 64
MAX_REPLAY_MARKS = 128
MAX_ROTATION_ENDORSEMENTS = 8
MAX_AGE = 600  # fixture-only integer ticks, NOT a trusted wall clock
MAX_FIXTURE_INTEGER = (1 << 63) - 1  # parser bound, not an authenticated time or revision


def _bounded_nonnegative_int(value) -> bool:
    return type(value) is int and 0 <= value <= MAX_FIXTURE_INTEGER


@dataclass(frozen=True)
class Enrollment:
    key_id: str
    public_key: bytes
    witness_id: str
    source_id: str
    custodian_id: str
    controller_id: str
    control_group_id: str
    epoch: str
    permitted_action: str = "OBSERVE_ONLY"


@dataclass(frozen=True)
class Revocation:
    key_id: str
    revoked_at: int
    reason_code: str


@dataclass(frozen=True)
class Snapshot:
    revision: int
    root_ref: str
    epoch: str
    checked_at: int
    expires_at: int
    frozen: bool
    enrollments: tuple[Enrollment, ...]
    revocations: tuple[Revocation, ...] = ()
    predecessor_digest: str = "GENESIS-INJECTED-UNVERIFIED"


@dataclass(frozen=True)
class Replica:
    peer_id: str
    view: Snapshot | None  # None: partition, unavailable, or unresponsive


@dataclass(frozen=True)
class Request:
    peer_ids: tuple[str, ...]
    expected_root: str
    registry_revision: int
    epoch: str
    event_namespace: str
    event_id: str
    event_type: str
    claim_id: str
    claim_scope: str
    requested_use: str
    audience: str
    mock_tick: int  # external TEST-ONLY clock fixture; no trusted time claim
    max_staleness: int = MAX_AGE


@dataclass(frozen=True)
class SignedReport:
    wire: bytes
    payload: bytes
    expected: w4b.Context  # independently supplied *test assertion*


@dataclass(frozen=True)
class ReplayView:
    marks: tuple[tuple[str, str, str, str], ...]
    # READ ONLY. Records cannot be committed, synchronized, or trusted here.


@dataclass(frozen=True)
class Outcome:
    status: str
    reason: str
    checked_signatures: int = 0
    declared_controllers: int = 0
    mock_registry_consistency: str = "NOT_ESTABLISHED"
    source_authentication: str = "UNKNOWN"
    source_independence: str = "UNKNOWN"
    reviewer_authorization: str = "UNKNOWN"
    evidence_admission: str = "NOT_EVALUATED"
    claim_truth: str = "UNKNOWN"

    def __post_init__(self):
        if self.status not in {"UNKNOWN", "REJECTED"}:
            raise ValueError("W4C_POSITIVE_AUTHORITY_FORBIDDEN")
        if (self.source_authentication != "UNKNOWN" or
                self.source_independence != "UNKNOWN" or
                self.reviewer_authorization != "UNKNOWN" or
                self.evidence_admission != "NOT_EVALUATED" or
                self.claim_truth != "UNKNOWN"):
            raise ValueError("W4C_TRUST_OR_TRUTH_PROMOTION_FORBIDDEN")


def _result(status: str, reason: str, count: int = 0, controllers: int = 0, consistent=False) -> Outcome:
    return Outcome(status, reason, count, controllers, "SYNTHETIC_REPLICAS_AGREE" if consistent else "NOT_ESTABLISHED")


def _digest(view: Snapshot) -> str:
    """Fingerprint only; it is NOT a cryptographic authentication of a view."""
    def record(e: Enrollment):
        return [e.key_id, e.public_key.hex(), e.witness_id, e.source_id,
                e.custodian_id, e.controller_id, e.control_group_id, e.epoch,
                e.permitted_action]
    x = [view.revision, view.root_ref, view.epoch, view.checked_at,
         view.expires_at, view.frozen, view.predecessor_digest,
         [record(e) for e in view.enrollments],
         [[r.key_id, r.revoked_at, r.reason_code] for r in view.revocations]]
    return sha256(json.dumps(x, separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()


def _check_shape(replicas, request, reports, replay):
    if type(request) is not Request or type(replicas) is not tuple or type(reports) is not tuple:
        return "W4C_INVALID_INPUT_SHAPE"
    if not 2 <= len(request.peer_ids) <= MAX_PEERS or (
        any(type(i) is not str or w4b.TOKEN.fullmatch(i) is None for i in request.peer_ids)
        or len(set(request.peer_ids)) != len(request.peer_ids)
    ):
        return "W4C_PEER_ROSTER_INVALID"
    if len(replicas) != len(request.peer_ids) or len(replicas) > MAX_PEERS:
        return "W4C_MISSING_OR_EXTRA_REPLICA"
    if any(type(p) is not Replica or type(p.peer_id) is not str or
           w4b.TOKEN.fullmatch(p.peer_id) is None for p in replicas):
        return "W4C_REPLICA_SHAPE_INVALID"
    if set(p.peer_id for p in replicas) != set(request.peer_ids) or len({p.peer_id for p in replicas}) != len(replicas):
        return "W4C_REPLICA_IDENTITY_MISMATCH"
    if not 1 <= len(reports) <= MAX_REPORTS or any(type(x) is not SignedReport for x in reports):
        return "W4C_REPORTS_INVALID"
    if any(type(getattr(request,k)) is not str or w4b.TOKEN.fullmatch(getattr(request,k)) is None for k in
        ("expected_root", "epoch", "event_namespace", "event_id", "event_type", "claim_id", "claim_scope", "requested_use", "audience")):
        return "W4C_CONTEXT_INVALID"
    if (not _bounded_nonnegative_int(request.mock_tick) or
            not _bounded_nonnegative_int(request.registry_revision) or
            type(request.max_staleness) is not int or not 0 <= request.max_staleness <= MAX_AGE):
        return "W4C_CONTEXT_TIME_OR_REVISION_INVALID"
    if replay is not None and (type(replay) is not ReplayView or
            type(replay.marks) is not tuple or len(replay.marks)>MAX_REPLAY_MARKS or
            any(type(m) is not tuple or len(m)!=4 or any(type(v) is not str or w4b.TOKEN.fullmatch(v) is None for v in m) for m in replay.marks)):
        return "W4C_REPLAY_VIEW_INVALID"
    return None


def _same_view(views: tuple[Snapshot, ...]) -> bool:
    # Conservative *exact* snapshot agreement, not a distributed-consensus claim.
    return len({_digest(v) for v in views}) == 1


def _valid_snapshot(view: Snapshot) -> bool:
    if type(view) is not Snapshot or type(view.enrollments) is not tuple or type(view.revocations) is not tuple:
        return False
    if len(view.enrollments)>MAX_RECORDS or len(view.revocations)>MAX_REVOCATIONS:
        return False
    if not all(_bounded_nonnegative_int(x) for x in
               (view.revision, view.checked_at, view.expires_at)):
        return False
    if (type(view.frozen) is not bool or view.checked_at < 0 or
            view.expires_at <= view.checked_at or
            any(type(v) is not str or w4b.TOKEN.fullmatch(v) is None for v in
                (view.root_ref,view.epoch,view.predecessor_digest))):
        return False
    if any(type(e) is not Enrollment or type(e.public_key) is not bytes or len(e.public_key)!=32 or
        any(type(v) is not str or w4b.TOKEN.fullmatch(v) is None for v in
            (e.key_id,e.witness_id,e.source_id,e.custodian_id,e.controller_id,e.control_group_id,e.epoch,e.permitted_action))
        for e in view.enrollments):
        return False
    if any(type(r) is not Revocation or type(r.key_id) is not str or w4b.TOKEN.fullmatch(r.key_id) is None or
           not _bounded_nonnegative_int(r.revoked_at) or
           type(r.reason_code) is not str or w4b.TOKEN.fullmatch(r.reason_code) is None
           for r in view.revocations):
        return False
    return True


def assess(replicas: tuple[Replica,...], reports: tuple[SignedReport,...],
           request: Request, replay: ReplayView | None) -> Outcome:
    """Read-only fake multi-replica check. Always UNKNOWN/REJECTED.

    All replica histories, enrollments, custody facts, clock ticks and replay
    marks are *injected assertions*; matching replicas cannot establish trust.
    """
    invalid = _check_shape(replicas, request, reports, replay)
    if invalid:
        return _result("REJECTED", invalid)
    if any(p.view is None for p in replicas):
        return _result("UNKNOWN", "W4C_PARTITION_OR_REPLICA_UNAVAILABLE")
    views=tuple(p.view for p in replicas)
    if not all(_valid_snapshot(v) for v in views):
        return _result("REJECTED", "W4C_INVALID_REGISTRY_SNAPSHOT")
    if not _same_view(views):
        return _result("UNKNOWN", "W4C_REGISTRY_FORK_OR_DIVERGENCE")
    view=views[0]
    if view.revision < request.registry_revision:
        return _result("UNKNOWN", "W4C_REGISTRY_ROLLBACK")
    if view.revision > request.registry_revision:
        return _result("UNKNOWN", "W4C_REGISTRY_UNEXPECTED_REVISION")
    if view.root_ref != request.expected_root:
        return _result("UNKNOWN", "W4C_UNPINNED_OR_ROTATED_ROOT")
    if view.epoch != request.epoch:
        return _result("UNKNOWN", "W4C_EPOCH_REBINDING")
    if view.frozen:
        return _result("UNKNOWN", "W4C_ROOT_COMPROMISE_FREEZE")
    if request.mock_tick < view.checked_at:
        return _result("UNKNOWN", "W4C_MOCK_CLOCK_ROLLBACK")
    if request.mock_tick >= view.expires_at:
        return _result("UNKNOWN", "W4C_REGISTRY_VIEW_EXPIRED")
    if request.mock_tick - view.checked_at > request.max_staleness:
        return _result("UNKNOWN", "W4C_MOCK_REVOCATION_VIEW_STALE")
    entries={}
    for e in view.enrollments:
        if e.key_id in entries:
            return _result("UNKNOWN", "W4C_AMBIGUOUS_ENROLLMENT")
        if w4b.public_key_id(e.public_key) != e.key_id:
            return _result("REJECTED", "W4C_FAKE_KEY_FINGERPRINT")
        if e.permitted_action!="OBSERVE_ONLY":
            return _result("REJECTED", "W4C_UNAUTHORIZED_REGISTRY_ROLE")
        entries[e.key_id]=e
    revoked={}
    for r in view.revocations:
        if r.key_id in revoked:
            return _result("UNKNOWN", "W4C_CONFLICTING_REVOCATION_RECORDS")
        revoked[r.key_id]=r
    if replay is None:
        return _result("UNKNOWN", "W4C_NO_DURABLE_REPLAY_ORACLE")
    marks=set()
    if len(replay.marks)!=len(set(replay.marks)):
        return _result("UNKNOWN", "W4C_AMBIGUOUS_REPLAY_VIEW")
    marks.update(replay.marks)
    checked=0
    used=[]
    batch=set()
    for report in reports:
        try:
            a,_=w4b._load_wire(report.wire)
        except (ValueError,TypeError):
            return _result("REJECTED", "W4C_MALFORMED_SIGNED_WIRE",checked)
        if type(report.expected) is not w4b.Context:
            return _result("REJECTED", "W4C_MISSING_INDEPENDENT_TEST_CONTEXT",checked)
        for name in ("event_namespace","event_id","event_type","event_epoch","claim_id","claim_scope","requested_use","audience"):
            expected_val=request.epoch if name=="event_epoch" else getattr(request,name)
            if getattr(report.expected,name)!=expected_val:
                return _result("REJECTED", "W4C_INDEPENDENT_CONTEXT_MISMATCH:"+name,checked)
        key_id=a["witness_key_id"]
        entry=entries.get(key_id)
        if entry is None:
            return _result("UNKNOWN", "W4C_KEY_NOT_IN_TEST_REGISTRY",checked)
        if a["source_id"]!=entry.source_id or a["custodian_id"]!=entry.custodian_id or a["control_group_id"]!=entry.control_group_id or a["event_epoch"]!=entry.epoch:
            return _result("REJECTED", "W4C_REGISTRY_RECORD_BINDING_MISMATCH",checked)
        if key_id in revoked:
            if revoked[key_id].revoked_at <= request.mock_tick:
                return _result("REJECTED", "W4C_REVOKED_TEST_KEY",checked)
            return _result("UNKNOWN", "W4C_FUTURE_REVOCATION_UNRESOLVED",checked)
        checked_result=w4b.inspect(report.wire,lambda value=report.payload:value,{key_id:entry.public_key},report.expected)
        if checked_result.test_signature_check!="VALID_UNDER_INJECTED_TEST_KEY":
            return _result(checked_result.status,"W4C_W4B_CHECK:"+checked_result.reason,checked)
        checked+=1
        marker=(a["audience"],a["request_id"],key_id,a["event_epoch"])
        if marker in batch:
            return _result("REJECTED", "W4C_REPLAY_WITHIN_BATCH",checked)
        if marker in marks:
            return _result("REJECTED", "W4C_REPLAY_IN_INJECTED_VIEW",checked)
        batch.add(marker)
        used.append((entry,a))
    if len(used)<2:
        return _result("UNKNOWN","W4C_SINGLE_SYNTHETIC_REPORT_ONLY",checked,1,True)
    controllers={e.controller_id for e,_ in used}
    groups={e.control_group_id for e,_ in used}
    custodians={e.custodian_id for e,_ in used}
    sources={e.source_id for e,_ in used}
    roots=[set(a["parent_refs"]) for _,a in used]
    if len(controllers)<len(used):
        return _result("UNKNOWN","W4C_DECLARED_SHARED_CONTROLLER",checked,len(controllers),True)
    if len(groups)<len(used):
        return _result("UNKNOWN","W4C_DECLARED_SHARED_CONTROL_GROUP",checked,len(controllers),True)
    if len(custodians)<len(used):
        return _result("UNKNOWN","W4C_DECLARED_SHARED_CUSTODIAN",checked,len(controllers),True)
    if len(sources)<len(used):
        return _result("UNKNOWN","W4C_DECLARED_SHARED_SOURCE",checked,len(controllers),True)
    for index, refs in enumerate(roots):
        if not refs:
            return _result("UNKNOWN","W4C_UNKNOWN_PARENT_ROOTS",checked,len(controllers),True)
        if any(refs.intersection(other) for other in roots[index+1:]):
            return _result("UNKNOWN","W4C_DECLARED_COMMON_ANCESTRY",checked,len(controllers),True)
    return _result("UNKNOWN","W4C_DISTINCT_DECLARATIONS_NOT_AUTHENTICATED",checked,len(controllers),True)


@dataclass(frozen=True)
class RecoveryProposal:
    previous: Snapshot
    replacement: Snapshot
    declarations: tuple[tuple[str,str],...]
    # id pairs of synthetic endorsers and control groups; NO signatures checked
    claimed_owner_approval: bool


def examine_recovery(case: RecoveryProposal, expected_new_root: str, fixture_time: int) -> Outcome:
    """Offline branch/recovery *diagnostic*, never an approval to trust roots."""
    if type(case) is not RecoveryProposal or not _valid_snapshot(case.previous) or not _valid_snapshot(case.replacement):
        return _result("REJECTED","W4C_RECOVERY_INPUT_INVALID")
    old,new=case.previous,case.replacement
    if not old.frozen:
        return _result("UNKNOWN","W4C_RECOVERY_NO_PRIOR_FREEZE")
    if type(expected_new_root) is not str or w4b.TOKEN.fullmatch(expected_new_root) is None or new.root_ref!=expected_new_root:
        return _result("UNKNOWN","W4C_RECOVERY_ROOT_NOT_EXTERNALLY_PINNED")
    if new.root_ref==old.root_ref:
        return _result("UNKNOWN","W4C_RECOVERY_OLD_ROOT_REUSE")
    if new.revision <= old.revision or new.epoch==old.epoch:
        return _result("UNKNOWN","W4C_RECOVERY_NONADVANCING_EPOCH")
    if new.predecessor_digest!=_digest(old):
        return _result("UNKNOWN","W4C_RECOVERY_HISTORY_LINK_MISMATCH")
    if not _bounded_nonnegative_int(fixture_time) or fixture_time < new.checked_at or fixture_time >=new.expires_at:
        return _result("UNKNOWN","W4C_RECOVERY_TIME_UNAVAILABLE")
    if type(case.claimed_owner_approval) is not bool or type(case.declarations) is not tuple or len(case.declarations)>MAX_ROTATION_ENDORSEMENTS or any(type(x) is not tuple or len(x)!=2 or any(type(y) is not str or w4b.TOKEN.fullmatch(y) is None for y in x) for x in case.declarations):
        return _result("REJECTED","W4C_RECOVERY_DECLARATIONS_INVALID")
    if not case.claimed_owner_approval or len({x[0] for x in case.declarations})<2 or len({x[1] for x in case.declarations})<2:
        return _result("UNKNOWN","W4C_RECOVERY_NO_SEPARATE_GOVERNANCE")
    if new.frozen:
        return _result("UNKNOWN","W4C_RECOVERY_STILL_FROZEN")
    return _result("UNKNOWN","W4C_RECOVERY_REVIEWABLE_FIXTURE_ONLY")
