"""Adversarial synthetic W4-D governance tests. No real rights or credentials."""
from dataclasses import replace
import pytest
import w4d_governance_lab as lab

D = "a" * 64
H = "b" * 64


def council(action="REVIEW_CANDIDATE", n=3, **kwargs):
    members = tuple(lab.Steward(f"Steward{i}", f"Group{i}") for i in range(1, 6))
    draft = lab.Motion("Motion1", action, D, 7, "Proposer", "Source", "ClaimX",
                       "ArioW4DLab", "OneTimeNonce1", 5, 15)
    motion = replace(draft, digest=lab.mock_motion_digest(draft))
    votes = tuple(lab.Vote(f"Ballot{i}", f"Steward{i}", motion.digest, 7, "SUPPORT")
                  for i in range(1, n + 1))
    ctx = lab.CouncilFixture(members, votes, motion, 10, 7)
    return replace(ctx, **kwargs)


def assert_non_authority(out):
    assert out.status in {"UNKNOWN", "REJECTED"}
    assert out.authentic_identity == "UNKNOWN"
    assert out.real_controller_independence == "UNKNOWN"
    assert out.reviewer_authorization == "UNKNOWN"
    assert out.evidence_admission == "NOT_EVALUATED"
    assert out.claim_truth == "UNKNOWN"


def test_nominal_review_only_conditional_lab():
    v = lab.evaluate_council(council())
    assert v.rule == "W4D_LAB_QUORUM_ONLY"
    assert v.lab_step == "LAB_PROCEDURAL_REVIEW_RECOMMENDATION"
    assert_non_authority(v)


def test_no_live_trust_even_when_all_five_agree():
    v = lab.evaluate_council(council(n=5))
    assert v.status == "UNKNOWN"
    assert_non_authority(v)


@pytest.mark.parametrize("action,n,expected_step", [
    ("REVIEW_CANDIDATE", 2, "HOLD"),
    ("REVOKE_REVIEW_GRANT", 2, "HOLD"),
    ("FREEZE", 1, "HOLD"),
    ("FREEZE", 2, "LAB_FREEZE_RECOMMENDATION"),
    ("REVOKE_REVIEW_GRANT", 3, "LAB_PROCEDURAL_REVIEW_RECOMMENDATION"),
])
def test_declared_council_threshold(action, n, expected_step):
    r = lab.evaluate_council(council(action, n))
    assert r.lab_step == expected_step
    assert_non_authority(r)


@pytest.mark.parametrize("action,flags,expected", [
    ("UNFREEZE", dict(currently_frozen=True, independent_recovery_attestation_claimed=True,
                      post_compromise_epoch_claimed=True), "LAB_RECOVERY_REVIEW_RECOMMENDATION"),
    ("ROTATE_ROOT", dict(independent_recovery_attestation_claimed=True,
                          post_compromise_epoch_claimed=True), "LAB_RECOVERY_REVIEW_RECOMMENDATION"),
    ("UNFREEZE", dict(currently_frozen=True, independent_recovery_attestation_claimed=False,
                       post_compromise_epoch_claimed=True), "HOLD"),
    ("UNFREEZE", dict(currently_frozen=True, independent_recovery_attestation_claimed=True,
                       post_compromise_epoch_claimed=False), "HOLD"),
    ("UNFREEZE", dict(currently_frozen=False, independent_recovery_attestation_claimed=True,
                       post_compromise_epoch_claimed=True), "REJECTED"),
    ("ROTATE_ROOT", dict(independent_recovery_attestation_claimed=False,
                          post_compromise_epoch_claimed=True), "HOLD"),
])
def test_stronger_recovery_gates(action, flags, expected):
    c = council(action, 4, **flags)
    r = lab.evaluate_council(c)
    assert (r.lab_step if expected != "REJECTED" else r.status) == expected
    assert_non_authority(r)


@pytest.mark.parametrize("action", ["UNFREEZE", "ROTATE_ROOT"])
def test_three_of_five_insufficient_for_high_risk_action(action):
    c = council(action, 3, **dict(currently_frozen=(action == "UNFREEZE"),
                                 independent_recovery_attestation_claimed=True,
                                 post_compromise_epoch_claimed=True))
    assert lab.evaluate_council(c).rule == "W4D_CONDITIONAL_QUORUM_NOT_MET"


@pytest.mark.parametrize("field,value,rule", [
    ("roster_complete_claimed", False, "W4D_MISSING_FRESH_ROSTER_CLOCK_OR_REVOCATION"),
    ("fresh_revocations_claimed", False, "W4D_MISSING_FRESH_ROSTER_CLOCK_OR_REVOCATION"),
    ("clock_checked_claimed", False, "W4D_MISSING_FRESH_ROSTER_CLOCK_OR_REVOCATION"),
    ("fork_declared", True, "W4D_FORK_OR_PARTITION"),
    ("partition_declared", True, "W4D_FORK_OR_PARTITION"),
    ("root_compromise_declared", True, "W4D_DECLARED_COMPROMISE"),
    ("currently_frozen", True, "W4D_FROZEN"),
])
def test_missing_context_or_freeze_is_not_approved(field, value, rule):
    assert lab.evaluate_council(replace(council(), **{field: value})).rule == rule


def test_declared_shared_controller_is_not_two_votes():
    c = council(n=3)
    members = list(c.members)
    members[1] = replace(members[1], declared_control_group="Group1")
    r = lab.evaluate_council(replace(c, members=tuple(members)))
    assert r.rule == "W4D_SHARED_DECLARED_CONTROLLER"
    assert_non_authority(r)


@pytest.mark.parametrize("conflict_group", ["Proposer", "Source"])
def test_known_conflicted_voter_cannot_ratify_review(conflict_group):
    c = council(n=3)
    members = list(c.members)
    members[0] = replace(members[0], declared_control_group=conflict_group)
    assert lab.evaluate_council(replace(c, members=tuple(members))).rule == "W4D_REVIEWER_PROPOSER_SOURCE_CONFLICT"


def test_duplicate_steward_id_rejected():
    c = council()
    m = list(c.members)
    m[1] = replace(m[1], steward_id="Steward1")
    assert lab.evaluate_council(replace(c, members=tuple(m))).rule == "W4D_ROSTER_SHAPE_OR_DUPLICATE"


@pytest.mark.parametrize("mutant,expected", [
    (lambda c: replace(c, votes=(c.votes[0], c.votes[0])), "W4D_DUPLICATE_BALLOT_OR_VOTER"),
    (lambda c: replace(c, votes=(c.votes[0], replace(c.votes[0], ballot_id="Another"))), "W4D_DUPLICATE_BALLOT_OR_VOTER"),
    (lambda c: replace(c, votes=(replace(c.votes[0], steward_id="Unregistered"),)), "W4D_UNENROLLED_VOTER"),
    (lambda c: replace(c, votes=(replace(c.votes[0], motion_digest=H),)), "W4D_VOTE_SCOPE_OR_EPOCH_REPLAY"),
    (lambda c: replace(c, votes=(replace(c.votes[0], epoch=6),)), "W4D_VOTE_SCOPE_OR_EPOCH_REPLAY"),
    (lambda c: replace(c, current_epoch=8), "W4D_STALE_OR_REPLAYED_EPOCH"),
    (lambda c: replace(c, motion=replace(c.motion, action="ADMIT_EVIDENCE")), "W4D_MOTION_SHAPE_OR_FORBIDDEN_ACTION"),
    (lambda c: replace(c, motion=replace(c.motion, action="ASSERT_TRUTH")), "W4D_MOTION_SHAPE_OR_FORBIDDEN_ACTION"),
    (lambda c: replace(c, motion=replace(c.motion, digest="A" * 64)), "W4D_MOTION_SHAPE_OR_FORBIDDEN_ACTION"),
    (lambda c: replace(c, observed_tick=2**2000), "W4D_BOUNDS_OR_TYPE"),
    (lambda c: replace(c, observed_tick=True), "W4D_BOUNDS_OR_TYPE"),
    (lambda c: replace(c, members=list(c.members)), "W4D_MALFORMED_COUNCIL"),
    (lambda c: replace(c, votes=[c.votes[0]]), "W4D_MALFORMED_COUNCIL"),
    (lambda c: replace(c, members=(replace(c.members[0], steward_id=[]),) + c.members[1:]), "W4D_ROSTER_SHAPE_OR_DUPLICATE"),
    (lambda c: replace(c, members=(replace(c.members[0], steward_id="Ｓteward1"),) + c.members[1:]), "W4D_ROSTER_SHAPE_OR_DUPLICATE"),
    (lambda c: replace(c, members=(replace(c.members[0], steward_id="S" * 200),) + c.members[1:]), "W4D_ROSTER_SHAPE_OR_DUPLICATE"),
    (lambda c: replace(c, motion=replace(c.motion, action=[])), "W4D_MOTION_SHAPE_OR_FORBIDDEN_ACTION"),
    (lambda c: replace(c, motion=replace(c.motion, policy_version="W4D-LAB-9.9")), "W4D_MOTION_SHAPE_OR_FORBIDDEN_ACTION"),
    (lambda c: replace(c, votes=(replace(c.votes[0], choice="ADMITTED"),)), "W4D_BALLOT_SHAPE"),
    (lambda c: replace(c, votes=(replace(c.votes[0], ballot_id="b" * 100),)), "W4D_BALLOT_SHAPE"),
])
def test_mutated_council_fails_closed(mutant, expected):
    r = lab.evaluate_council(mutant(council()))
    assert r.rule == expected
    assert_non_authority(r)


def appeal():
    return lab.AppealFixture("Appeal1", "Decision1", "AppellantP", "NEW_EVIDENCE",
                             ("Group1", "Group2"), ("Group3", "Group4", "Group5"), True, True, True,
                             original_panel_complete_claimed=True)


def test_appeal_intake_not_decision_reversal():
    r = lab.evaluate_appeal(appeal())
    assert r.lab_step == "LAB_APPEAL_FOR_INDEPENDENT_SCREENING"
    assert_non_authority(r)


@pytest.mark.parametrize("field,value,expected", [
    ("original_panel_groups", ("Group3",), "W4D_APPEAL_REVIEWER_CONFLICT"),
    ("proposed_appeal_panel_groups", ("Group3", "Group3", "Group5"), "W4D_APPEAL_PANEL_SHARED_CONTROLLER"),
    ("case_is_known_claimed", False, "W4D_APPEAL_ORIGINAL_CASE_UNRESOLVED"),
    ("external_auth_claimed", False, "W4D_APPEAL_SUBJECT_BINDING_UNKNOWN"),
    ("previous_appeal_ids", ("Appeal1",), "W4D_APPEAL_REPLAY"),
    ("appeal_id", "آوا", "W4D_APPEAL_SHAPE"),
    ("proposed_appeal_panel_groups", ["Group3", "Group4", "Group5"], "W4D_APPEAL_SHAPE"),
    ("grounds_code", None, "W4D_APPEAL_SHAPE"),
])
def test_appeal_attacks(field, value, expected):
    r = lab.evaluate_appeal(replace(appeal(), **{field: value}))
    assert r.rule == expected
    assert_non_authority(r)


def disclosure():
    return lab.DisclosureFixture("Case1", "Reader1", "CASE_AUDIT", ("CASE_STATE", "RULE_ID"), "GRANTED")


def test_minimized_public_metadata_is_not_real_permission():
    r = lab.evaluate_disclosure(disclosure())
    assert r.lab_step == "LAB_MINIMIZED_REQUEST_FOR_SEPARATE_AUTHORIZATION"
    assert r.reviewer_authorization == "UNKNOWN"
    assert_non_authority(r)


@pytest.mark.parametrize("field,value,expected", [
    ("consent", "WITHDRAWN", "W4D_PRIVACY_WITHDRAWN_OR_EXPIRED"),
    ("consent", "UNKNOWN", "W4D_PRIVACY_CONSENT_UNRESOLVED"),
    ("access_expired_claimed", True, "W4D_PRIVACY_WITHDRAWN_OR_EXPIRED"),
    ("fields", ("RAW_PAYLOAD",), "W4D_PRIVACY_OVERDISCLOSURE"),
    ("fields", ("WITNESS_NAME",), "W4D_PRIVACY_OVERDISCLOSURE"),
    ("fields", ("CONTACT",), "W4D_PRIVACY_OVERDISCLOSURE"),
    ("fields", ("CASE_STATE", "CASE_STATE"), "W4D_PRIVACY_SHAPE"),
    ("fields", (), "W4D_PRIVACY_SHAPE"),
    ("fields", ["CASE_STATE"], "W4D_PRIVACY_SHAPE"),
    ("consent", [], "W4D_PRIVACY_SHAPE"),
    ("purpose", [], "W4D_PRIVACY_SHAPE"),
    ("fields", ("REDACTED_POINTER",), "W4D_RESTRICTED_METADATA_AUTH_UNKNOWN"),
    ("fields", ("NOT_ALLOWED_FIELD",), "W4D_PRIVACY_OVERDISCLOSURE"),
    ("case_id", "Case🔥", "W4D_PRIVACY_SHAPE"),
])
def test_disclosure_attacks(field, value, expected):
    r = lab.evaluate_disclosure(replace(disclosure(), **{field: value}))
    assert r.rule == expected
    assert_non_authority(r)


def test_appeal_purpose_must_have_open_appeal():
    r = lab.evaluate_disclosure(replace(disclosure(), purpose="APPEAL_SCREENING"))
    assert r.rule == "W4D_NO_OPEN_APPEAL"


def test_restricted_meta_remains_only_a_candidate():
    r = lab.evaluate_disclosure(replace(disclosure(), fields=("REDACTED_POINTER",),
                                        reviewer_authorization_claimed=True))
    assert r.status == "UNKNOWN"
    assert r.lab_step == "LAB_MINIMIZED_REQUEST_FOR_SEPARATE_AUTHORIZATION"
    assert_non_authority(r)


def history():
    h0 = lab.AuditHeader(0, "0" * 64, "CASE_SUBMITTED", "Case1", D)
    x0 = lab.lab_entry_hash(h0)
    h1 = lab.AuditHeader(1, x0, "CASE_CONTESTED", "Case1", H)
    x1 = lab.lab_entry_hash(h1)
    return (h0, h1), (x0, x1)


def test_hash_chain_is_consistency_not_external_proof():
    r = lab.check_mock_history(*history())
    assert r.lab_step == "LAB_HISTORY_STRUCTURALLY_CONSISTENT"
    assert_non_authority(r)


@pytest.mark.parametrize("mutator,expected", [
    (lambda a,b: (a, (b[1], b[0])), "W4D_AUDIT_MISMATCH"),
    (lambda a,b: (a[:-1], b), "W4D_AUDIT_BOUNDS"),
    (lambda a,b: (a, (b[0], "0" * 64)), "W4D_AUDIT_MISMATCH"),
    (lambda a,b: ((a[0], replace(a[1], prev_hash="0" * 64)), b), "W4D_AUDIT_BROKEN_PREDECESSOR"),
    (lambda a,b: ((a[0], replace(a[1], sequence=9)), b), "W4D_AUDIT_BAD_HEADER"),
    (lambda a,b: ((a[0], replace(a[1], payload_commitment="PERSONAL_ID")), b), "W4D_AUDIT_BAD_HEADER"),
    (lambda a,b: (list(a), b), "W4D_AUDIT_SHAPE"),
    (lambda a,b: (a, (b[0], [])), "W4D_AUDIT_BAD_HEADER"),
])
def test_audit_tamper_detected_without_truth_elevation(mutator, expected):
    a,b = history()
    s = lab.check_mock_history(*mutator(a,b))
    assert s.rule == expected
    assert_non_authority(s)


def test_ordinary_vote_can_never_escape_unknown():
    # Guards against accidental adoption of a lab predicate as permission.
    with pytest.raises(ValueError, match="LAB_CANNOT_GRANT"):
        lab.Finding("VERIFIED_FOR_REVIEW_ONLY", "FAKE")
    with pytest.raises(ValueError, match="LAB_CANNOT_GRANT"):
        lab.Finding("UNKNOWN", "FAKE", evidence_admission="ADMITTED")
    with pytest.raises(ValueError, match="LAB_CANNOT_GRANT"):
        lab.Finding("UNKNOWN", "FAKE", claim_truth="TRUE")


def test_empty_history_cannot_be_positive_history_consistency():
    r = lab.check_mock_history((), ())
    assert r.rule == "W4D_EMPTY_HISTORY"
    assert r.lab_step == "HOLD"
    assert_non_authority(r)


def test_duplicate_prior_appeal_ids_rejected():
    r = lab.evaluate_appeal(replace(appeal(), previous_appeal_ids=("AppealOld", "AppealOld")))
    assert r.rule == "W4D_APPEAL_HISTORY_DUPLICATE"
    assert_non_authority(r)


def test_unknown_object_cannot_turn_into_approval():
    assert lab.evaluate_council({"approved": True}).status == "REJECTED"
    assert lab.evaluate_appeal({"approved": True}).status == "REJECTED"
    assert lab.evaluate_disclosure({"approved": True}).status == "REJECTED"
