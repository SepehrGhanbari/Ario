"""W4-C test-only distributed registry experiments. NO identity/admission authority.

Test keys are public deterministic test seeds, NEVER production credentials.
"""
from __future__ import annotations
from dataclasses import replace
from hashlib import sha256
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import w4b_profile_lab as w4b
import w4c_distributed_lab as w4c

PAYLOAD = b'{"event":"TASK_FINISHED","status":"COMPLETED","type":"synthetic"}\n'
SEEDS = (
    bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"),
    b"\x02" * 32,
    b"\x03" * 32,
    b"\x04" * 32,
)


def key(i): return Ed25519PrivateKey.from_private_bytes(SEEDS[i])


def pub(i):
    return key(i).public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)


def enrollment(i, **change):
    e=w4c.Enrollment(
        key_id=w4b.public_key_id(pub(i)), public_key=pub(i), witness_id=f"WITNESS-{i}",
        source_id=f"SRC-{i}", custodian_id=f"HOLDER-{i}", controller_id=f"CONTROLLER-{i}",
        control_group_id=f"GROUP-{i}", epoch="SYNTHETIC-01")
    return replace(e,**change)


def registry(entries=None, **change):
    e=(enrollment(0),enrollment(1)) if entries is None else entries
    return replace(w4c.Snapshot(
        revision=7, root_ref="INJECTED-ROOT-A", epoch="SYNTHETIC-01",
        checked_at=100, expires_at=1000, frozen=False,
        enrollments=e, predecessor_digest="MOCK-GENESIS"),**change)


def replicas(view=None, **change):
    view=registry() if view is None else view
    return tuple(w4c.Replica(pid, change.get(pid,view)) for pid in ("PEER-1","PEER-2","PEER-3"))


def request(**change):
    return replace(w4c.Request(
        peer_ids=("PEER-1","PEER-2","PEER-3"), expected_root="INJECTED-ROOT-A",
        registry_revision=7, epoch="SYNTHETIC-01",
        event_namespace="ario.synthetic.lab",event_id="TASK-A",event_type="TASK_FINISHED",
        claim_id="CLAIM-A",claim_scope="task.record.presence",
        requested_use="RECORD_DESCRIPTION",audience="ario.offline.test",mock_tick=120),**change)


def signed_report(i=0, *, enrollment_record=None, attrs=None, **change):
    e=enrollment(i) if enrollment_record is None else enrollment_record
    a=dict(profile=w4b.PROFILE,payload_sha256=sha256(PAYLOAD).hexdigest(),
           payload_byte_length=len(PAYLOAD),event_namespace="ario.synthetic.lab",event_id="TASK-A",
           event_type="TASK_FINISHED",event_epoch="SYNTHETIC-01",claim_id="CLAIM-A",
           claim_scope="task.record.presence",requested_use="RECORD_DESCRIPTION",
           audience="ario.offline.test",request_id=f"REQ-{i}",witness_key_id=e.key_id,
           source_id=e.source_id,custodian_id=e.custodian_id,control_group_id=e.control_group_id,
           parent_refs=[f"EVENT-ROOT-{i}"])
    if attrs:a.update(attrs)
    sig=key(i).sign(w4b.bytes_to_sign(a))
    expected=w4b.Context(**{k:a[k] for k in w4b.Context.__dataclass_fields__})
    return replace(w4c.SignedReport(w4b.encode_wire(a,sig),PAYLOAD,expected),**change)


def reports(*indices):return tuple(signed_report(i) for i in (indices or (0,1)))


def run(*, nodes=None, docs=None, scope=None, marks=None):
    return w4c.assess(
        replicas() if nodes is None else nodes,
        reports() if docs is None else docs,
        request() if scope is None else scope,
        w4c.ReplayView(()) if marks is None else marks,
    )


def fail_closed(out):
    assert out.status in {"UNKNOWN","REJECTED"}
    assert out.source_authentication=="UNKNOWN"
    assert out.source_independence=="UNKNOWN"
    assert out.reviewer_authorization=="UNKNOWN"
    assert out.evidence_admission=="NOT_EVALUATED"
    assert out.claim_truth=="UNKNOWN"


def test_control_distinct_public_test_keys_and_synthetic_fixture_only():
    assert len({w4b.public_key_id(pub(i)) for i in range(4)}) == 4
    result=run()
    assert result.status=="UNKNOWN"
    assert result.reason=="W4C_DISTINCT_DECLARATIONS_NOT_AUTHENTICATED"
    assert result.checked_signatures==2
    assert result.declared_controllers==2
    assert result.mock_registry_consistency=="SYNTHETIC_REPLICAS_AGREE"
    fail_closed(result)


def test_one_signature_not_independent_plurality():
    r=run(docs=reports(0))
    assert r.reason=="W4C_SINGLE_SYNTHETIC_REPORT_ONLY"
    fail_closed(r)


@pytest.mark.parametrize("mutation,reason",[
    ({"controller_id":"CONTROLLER-0"},"W4C_DECLARED_SHARED_CONTROLLER"),
    ({"control_group_id":"GROUP-0"},"W4C_DECLARED_SHARED_CONTROL_GROUP"),
    ({"custodian_id":"HOLDER-0"},"W4C_DECLARED_SHARED_CUSTODIAN"),
    ({"source_id":"SRC-0"},"W4C_DECLARED_SHARED_SOURCE"),
])
def test_sybil_two_valid_keys_with_common_declared_control_cannot_make_independent_evidence(mutation,reason):
    e1=enrollment(1,**mutation)
    r1=signed_report(1,enrollment_record=e1)
    r=run(nodes=replicas(registry((enrollment(0),e1))),docs=(signed_report(0),r1))
    assert r.reason==reason and r.status=="UNKNOWN"
    assert r.checked_signatures==2
    fail_closed(r)


def test_shared_declared_upstream_capture_not_independent():
    r=run(docs=(signed_report(0),signed_report(1,attrs={"parent_refs":["EVENT-ROOT-0"]})))
    assert r.reason=="W4C_DECLARED_COMMON_ANCESTRY"
    fail_closed(r)


def test_unknown_parent_graph_must_not_be_assumed_exhaustive():
    r=run(docs=(signed_report(0),signed_report(1,attrs={"parent_refs":[]})))
    assert r.reason=="W4C_UNKNOWN_PARENT_ROOTS"
    fail_closed(r)


def test_copy_twice_same_report_in_batch_is_replay_not_more_votes():
    r=run(docs=(signed_report(0),signed_report(0)))
    assert r.status=="REJECTED" and r.reason=="W4C_REPLAY_WITHIN_BATCH"
    fail_closed(r)


def test_same_signed_report_known_nonce_in_local_mock_replay_view():
    mark=("ario.offline.test","REQ-0",enrollment(0).key_id,"SYNTHETIC-01")
    r=run(marks=w4c.ReplayView((mark,)))
    assert r.status=="REJECTED" and r.reason=="W4C_REPLAY_IN_INJECTED_VIEW"
    fail_closed(r)


def test_absent_replay_state_always_unknown_even_with_valid_signatures():
    r=run()
    q=w4c.assess(replicas(),reports(),request(),None)
    assert r.checked_signatures==2
    assert q.reason=="W4C_NO_DURABLE_REPLAY_ORACLE"
    fail_closed(q)


def test_duplicate_replay_marks_ambiguous_not_favorably_resolved():
    mark=("ario.offline.test","REQ-0",enrollment(0).key_id,"SYNTHETIC-01")
    q=run(marks=w4c.ReplayView((mark,mark)))
    assert q.reason=="W4C_AMBIGUOUS_REPLAY_VIEW"
    fail_closed(q)


@pytest.mark.parametrize("peer", ["PEER-1","PEER-2","PEER-3"])
def test_network_partition_of_any_expected_replica_freezes_result(peer):
    r=run(nodes=replicas(**{peer:None}))
    assert r.reason=="W4C_PARTITION_OR_REPLICA_UNAVAILABLE"
    fail_closed(r)


@pytest.mark.parametrize("changes",[
    {"revision":8},{"root_ref":"INJECTED-ROOT-OTHER"},{"checked_at":101},
    {"expires_at":800},{"frozen":True},{"epoch":"SYNTHETIC-02"},
    {"revocations":(w4c.Revocation(enrollment(0).key_id,110,"REVOKED"),)},
    {"predecessor_digest":"DIFFERENT-HISTORY"},
])
def test_divergent_replica_views_never_claim_registry_consensus(changes):
    r=run(nodes=replicas(**{"PEER-2":registry(**changes)}))
    assert r.status=="UNKNOWN" and r.reason=="W4C_REGISTRY_FORK_OR_DIVERGENCE"
    fail_closed(r)


def test_all_replicas_agree_on_false_enrollment_still_no_external_authentication():
    r=run()
    assert r.source_authentication=="UNKNOWN"
    assert r.source_independence=="UNKNOWN"
    assert r.mock_registry_consistency=="SYNTHETIC_REPLICAS_AGREE"
    fail_closed(r)


@pytest.mark.parametrize("delta,reason",[
    ({"revision":6},"W4C_REGISTRY_ROLLBACK"),
    ({"revision":8},"W4C_REGISTRY_UNEXPECTED_REVISION"),
    ({"root_ref":"OTHER-SELF-CLAIMED-ROOT"},"W4C_UNPINNED_OR_ROTATED_ROOT"),
    ({"epoch":"SYNTHETIC-02"},"W4C_EPOCH_REBINDING"),
    ({"frozen":True},"W4C_ROOT_COMPROMISE_FREEZE"),
])
def test_all_peers_matching_unacceptable_view_still_fail_closed(delta,reason):
    r=run(nodes=replicas(registry(**delta)))
    assert r.status=="UNKNOWN" and r.reason==reason
    fail_closed(r)


@pytest.mark.parametrize("tick,age,reason",[
    (99,600,"W4C_MOCK_CLOCK_ROLLBACK"),
    (1000,600,"W4C_REGISTRY_VIEW_EXPIRED"),
    (701,600,"W4C_MOCK_REVOCATION_VIEW_STALE"),
    (121,20,"W4C_MOCK_REVOCATION_VIEW_STALE"),
])
def test_mock_clock_and_revocation_freshness(tick,age,reason):
    r=run(scope=request(mock_tick=tick,max_staleness=age))
    assert r.reason==reason and r.status=="UNKNOWN"
    fail_closed(r)


def test_no_trusted_clock_claim_even_when_ticks_fresh():
    r=run(scope=request(mock_tick=120))
    assert r.reason=="W4C_DISTINCT_DECLARATIONS_NOT_AUTHENTICATED"
    assert r.source_authentication=="UNKNOWN"
    fail_closed(r)


@pytest.mark.parametrize("when,expected_reason,expected_status",[
    (90,"W4C_REVOKED_TEST_KEY","REJECTED"),
    (120,"W4C_REVOKED_TEST_KEY","REJECTED"),
    (121,"W4C_FUTURE_REVOCATION_UNRESOLVED","UNKNOWN"),
])
def test_revoked_and_future_revoke_test_key_not_admitted(when,expected_reason,expected_status):
    view=registry(revocations=(w4c.Revocation(enrollment(0).key_id,when,"COMPROMISED"),))
    r=run(nodes=replicas(view))
    assert r.reason==expected_reason and r.status==expected_status
    fail_closed(r)


def test_conflicting_revocation_records_cannot_choose_favorable():
    k=enrollment(0).key_id
    view=registry(revocations=(w4c.Revocation(k,120,"REVOKED"),w4c.Revocation(k,300,"NOT_YET")))
    r=run(nodes=replicas(view))
    assert r.reason=="W4C_CONFLICTING_REVOCATION_RECORDS"
    fail_closed(r)


def test_duplicate_key_enrollments_are_ambiguous_not_counted_twice():
    x=enrollment(0)
    r=run(nodes=replicas(registry((x,x,enrollment(1)))))
    assert r.reason=="W4C_AMBIGUOUS_ENROLLMENT"
    fail_closed(r)


def test_root_bundled_as_new_untrusted_peer_cannot_enrol_itself():
    r=run(nodes=replicas(registry(root_ref="NEW-SIGNED-SELF-ROOT")))
    assert r.reason=="W4C_UNPINNED_OR_ROTATED_ROOT"
    fail_closed(r)


def test_key_id_substitution_against_valid_public_key_is_rejected():
    original=enrollment(0)
    bad=replace(original,key_id=enrollment(1).key_id)
    r=run(nodes=replicas(registry((bad,enrollment(1)))))
    assert r.reason=="W4C_FAKE_KEY_FINGERPRINT"
    assert r.status=="REJECTED"
    fail_closed(r)


def test_unknown_key_in_signed_wire_cannot_enroll_from_request():
    r=run(docs=(signed_report(2),signed_report(1)))
    assert r.reason=="W4C_KEY_NOT_IN_TEST_REGISTRY"
    fail_closed(r)


def test_witness_registry_source_binding_mismatch_detected():
    bad=signed_report(0,attrs={"source_id":"ATTACKER-SOURCE"})
    r=run(docs=(bad,signed_report(1)))
    assert r.reason=="W4C_REGISTRY_RECORD_BINDING_MISMATCH"
    fail_closed(r)


@pytest.mark.parametrize("field,value",[
    ("event_id","OTHER-EVENT"),("event_epoch","SYNTHETIC-02"),
    ("claim_id","OTHER-CLAIM"),("claim_scope","GLOBAL-TRUTH"),
    ("requested_use","INDEPENDENT_TARGET_SUPPORT"),
    ("audience","remote.production"),("event_type","HISTORICAL_PROOF"),
])
def test_cross_event_epoch_claim_use_audience_rebinding_is_rejected(field,value):
    bad=signed_report(0,attrs={field:value})
    r=run(docs=(bad,signed_report(1)))
    assert r.status=="REJECTED" and r.reason=="W4C_INDEPENDENT_CONTEXT_MISMATCH:"+field
    fail_closed(r)


def test_bad_ed25519_signature_rejected_by_unmodified_w4b_verifier():
    x=signed_report(0)
    raw=bytearray(x.wire)
    needle=b'"signature_hex":"'
    loc=raw.index(needle)+len(needle)
    raw[loc]=ord("0") if raw[loc]!=ord("0") else ord("1")
    x=replace(x,wire=bytes(raw))
    r=run(docs=(x,signed_report(1)))
    assert r.reason=="W4C_W4B_CHECK:W4B-INVALID_TEST_SIGNATURE" and r.status=="REJECTED"
    fail_closed(r)


def test_payload_tamper_rejected_by_w4b_bytes_binding():
    x=replace(signed_report(0),payload=PAYLOAD+b"ATTACK")
    r=run(docs=(x,signed_report(1)))
    assert r.reason=="W4C_W4B_CHECK:W4B-PAYLOAD_DIGEST_OR_LENGTH_MISMATCH"
    fail_closed(r)


def test_no_escalation_from_declared_threshold_of_many_keys():
    entries=tuple(enrollment(i) for i in range(4))
    reqs=tuple(signed_report(i) for i in range(4))
    r=run(nodes=replicas(registry(entries)),docs=reqs)
    assert r.checked_signatures==4 and r.declared_controllers==4
    assert r.reason=="W4C_DISTINCT_DECLARATIONS_NOT_AUTHENTICATED"
    fail_closed(r)


def test_many_test_keys_under_one_controller_are_still_one_declared_controller():
    entries=(enrollment(0),)+tuple(enrollment(i,controller_id="CONTROLLER-0") for i in range(1,4))
    docs=tuple(signed_report(i,enrollment_record=entries[i]) for i in range(4))
    r=run(nodes=replicas(registry(entries)),docs=docs)
    assert r.checked_signatures==4 and r.declared_controllers==1
    assert r.reason=="W4C_DECLARED_SHARED_CONTROLLER"
    fail_closed(r)


@pytest.mark.parametrize("change,reason",[
    ({"permitted_action":"ADMIT_EVIDENCE"},"W4C_UNAUTHORIZED_REGISTRY_ROLE"),
    ({"permitted_action":"REVIEW_CANDIDATE"},"W4C_UNAUTHORIZED_REGISTRY_ROLE"),
    ({"permitted_action":"ASSERT_TRUTH"},"W4C_UNAUTHORIZED_REGISTRY_ROLE"),
])
def test_registry_declarations_cannot_grant_admission_or_reviewer_role(change,reason):
    e=enrollment(0,**change)
    r=run(nodes=replicas(registry((e,enrollment(1)))))
    assert r.reason==reason and r.status=="REJECTED"
    fail_closed(r)


@pytest.mark.parametrize("invalid,reason",[
    (None,"W4C_NO_DURABLE_REPLAY_ORACLE"),
    (w4c.ReplayView((('x','y','z','v'),)*129),"W4C_REPLAY_VIEW_INVALID"),
    (w4c.ReplayView((("malformed",),)),"W4C_REPLAY_VIEW_INVALID"),
])
def test_replay_oracle_bounds(invalid,reason):
    r=w4c.assess(replicas(),reports(),request(),invalid)
    assert r.reason==reason
    fail_closed(r)


def test_peer_list_duplicate_is_rejected():
    r=run(scope=request(peer_ids=("PEER-1","PEER-1","PEER-2")))
    assert r.reason=="W4C_PEER_ROSTER_INVALID"
    fail_closed(r)


def test_mismatched_peer_id_no_reliance_on_silent_subset():
    p=replicas()
    nodes=(replace(p[0],peer_id="MALLORY"),p[1],p[2])
    r=run(nodes=nodes)
    assert r.reason=="W4C_REPLICA_IDENTITY_MISMATCH"
    fail_closed(r)


def test_oversized_mock_registry_fails_before_any_signature_check():
    entries=tuple(enrollment(i%4) for i in range(33))
    r=run(nodes=replicas(registry(entries)))
    assert r.reason=="W4C_INVALID_REGISTRY_SNAPSHOT" and r.checked_signatures==0
    fail_closed(r)


def test_no_cryptographic_or_real_authority_from_matching_registry_snapshots():
    r=run()
    assert r.mock_registry_consistency=="SYNTHETIC_REPLICAS_AGREE"
    assert r.source_authentication=="UNKNOWN"
    assert r.reviewer_authorization=="UNKNOWN"
    assert r.evidence_admission=="NOT_EVALUATED"
    fail_closed(r)


@pytest.mark.parametrize("case",["no-freeze","same-root","no-advance","bad-link","same-control","no-owner","still-frozen","bad-clock"])
def test_compromised_root_recovery_preconditions_stay_conservative(case):
    old=registry(frozen=True)
    new=registry(root_ref="INJECTED-ROOT-B",epoch="SYNTHETIC-02",revision=8,
                 predecessor_digest=w4c._digest(old))
    decl=(('REVIEWER-A','GROUP-A'),('REVIEWER-B','GROUP-B'))
    if case=="no-freeze":old=replace(old,frozen=False)
    if case=="same-root":new=replace(new,root_ref=old.root_ref)
    if case=="no-advance":new=replace(new,revision=7)
    if case=="bad-link":new=replace(new,predecessor_digest="UNVERIFIED")
    if case=="same-control":decl=(('REVIEWER-A','SHARED'),('REVIEWER-B','SHARED'))
    if case=="no-owner":approval=False
    else:approval=True
    if case=="still-frozen":new=replace(new,frozen=True)
    clock=9999 if case=="bad-clock" else 130
    result=w4c.examine_recovery(w4c.RecoveryProposal(old,new,decl,approval),new.root_ref,clock)
    assert result.status=="UNKNOWN"
    assert result.reason!="W4C_RECOVERY_REVIEWABLE_FIXTURE_ONLY"
    fail_closed(result)


def test_mock_recovery_can_be_consistent_but_never_becomes_trusted():
    old=registry(frozen=True)
    new=registry(root_ref="INJECTED-ROOT-B",epoch="SYNTHETIC-02",revision=8,
                 predecessor_digest=w4c._digest(old))
    result=w4c.examine_recovery(w4c.RecoveryProposal(old,new,(
        ('REVIEWER-A','GROUP-A'),('REVIEWER-B','GROUP-B')),True),"INJECTED-ROOT-B",130)
    assert result.reason=="W4C_RECOVERY_REVIEWABLE_FIXTURE_ONLY"
    assert result.status=="UNKNOWN"
    fail_closed(result)


def test_recovery_cannot_bypass_missing_new_root_pin():
    old=registry(frozen=True)
    new=registry(root_ref="INJECTED-ROOT-B",epoch="SYNTHETIC-02",revision=8,
                 predecessor_digest=w4c._digest(old))
    r=w4c.examine_recovery(w4c.RecoveryProposal(old,new,(
        ('A','A'),('B','B')),True),"ATTACKER-SELF-PIN",130)
    assert r.reason=="W4C_RECOVERY_ROOT_NOT_EXTERNALLY_PINNED"
    fail_closed(r)


def test_outcome_object_guards_positive_authority_even_when_claimed_by_bug():
    with pytest.raises(ValueError,match="POSITIVE_AUTHORITY"):
        w4c.Outcome("VERIFIED","FAKE")
    with pytest.raises(ValueError,match="PROMOTION"):
        w4c.Outcome("UNKNOWN","FAKE",source_authentication="VERIFIED")
    with pytest.raises(ValueError,match="PROMOTION"):
        w4c.Outcome("UNKNOWN","FAKE",evidence_admission="ADMITTED")


def test_mock_evaluation_does_not_modify_snapshot_or_replay_state():
    snap=registry()
    peer_views=replicas(snap)
    replay=w4c.ReplayView(())
    before=w4c._digest(snap)
    r=w4c.assess(peer_views,reports(),request(),replay)
    assert w4c._digest(snap)==before and replay.marks==()
    assert peer_views[0].view is snap
    fail_closed(r)

@pytest.mark.parametrize("delta", [
    {"root_ref":"INJECTED-ROOT-А"},  # Cyrillic letter confusable
    {"checked_at":-1},
    {"expires_at":99},
    {"predecessor_digest":"BAD ROOT WITH SPACES"},
])
def test_invalid_registry_shape_and_nonascii_identifier_fail_before_aggregation(delta):
    r=run(nodes=replicas(registry(**delta)))
    assert r.status=="REJECTED" and r.reason=="W4C_INVALID_REGISTRY_SNAPSHOT"
    fail_closed(r)


def test_unicode_peer_confusable_rejected_in_strict_fixture_identifier_profile():
    r=run(scope=request(peer_ids=("PEER-1","PEER-2","РEER-3")))
    assert r.status=="REJECTED" and r.reason=="W4C_PEER_ROSTER_INVALID"
    fail_closed(r)


def test_truthy_string_cannot_claim_governance_recovery_approval():
    old=registry(frozen=True)
    new=registry(root_ref="INJECTED-ROOT-B",epoch="SYNTHETIC-02",revision=8,
                 predecessor_digest=w4c._digest(old))
    r=w4c.examine_recovery(w4c.RecoveryProposal(old,new,(
        ("REVIEWER-A","GROUP-A"),("REVIEWER-B","GROUP-B")),"YES"),"INJECTED-ROOT-B",130)
    assert r.status=="REJECTED" and r.reason=="W4C_RECOVERY_DECLARATIONS_INVALID"
    fail_closed(r)
