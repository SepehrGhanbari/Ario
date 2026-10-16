"""Review-only regression probes for exact W4-D PR #87 code.

All expected failures are in the local **synthetic** fixture. They do not assert
production authentication, real network consensus or a real authorization bypass.
"""
from dataclasses import replace
import pytest
import w4d_governance_lab as lab
from test_w4d_governance_lab import council, appeal

@pytest.mark.parametrize('new_action,old_action,count,extra', [
    ('FREEZE', 'REVIEW_CANDIDATE', 2, {}),
    ('UNFREEZE', 'ROTATE_ROOT', 4, {'currently_frozen': True,
        'independent_recovery_attestation_claimed':True, 'post_compromise_epoch_claimed':True}),
])
def test_vote_is_not_reusable_after_changing_signed_action(new_action,old_action,count,extra):
    fixture=council(old_action,count,**extra)
    changed=replace(fixture,motion=replace(fixture.motion,action=new_action))
    assert changed.votes==fixture.votes, 'Control: identical ballots'
    got=lab.evaluate_council(changed)
    assert got.lab_step not in ('LAB_FREEZE_RECOMMENDATION','LAB_RECOVERY_REVIEW_RECOMMENDATION'), got

@pytest.mark.parametrize('field,new_value',[('motion_id','DifferentMotion'),('candidate_scope','UnrelatedClaim')])
def test_vote_is_not_reusable_across_distinct_motion_identity_or_scope(field,new_value):
    fixture=council('REVIEW_CANDIDATE',3)
    changed=replace(fixture,motion=replace(fixture.motion,**{field:new_value}))
    assert fixture.votes==changed.votes
    got=lab.evaluate_council(changed)
    assert got.lab_step != 'LAB_PROCEDURAL_REVIEW_RECOMMENDATION', got

@pytest.mark.parametrize('original_groups',[(),('Group1',),('Group1','Group1')])
def test_missing_or_duplicate_original_appeals_panel_cannot_be_declared_screenable(original_groups):
    fixture=replace(appeal(),original_panel_groups=original_groups)
    got=lab.evaluate_appeal(fixture)
    assert got.lab_step != 'LAB_APPEAL_FOR_INDEPENDENT_SCREENING', got

@pytest.mark.parametrize('forbidden_step',['ADMITTED','VERIFIED_FOR_REVIEW_ONLY','M0_PASS'])
def test_finding_rejects_positive_authority_words_in_lab_step(forbidden_step):
    with pytest.raises(ValueError,match='LAB_CANNOT_GRANT'):
        lab.Finding('UNKNOWN','ATTACKER_CONTROLLED',lab_step=forbidden_step)

# Positive/negative existing controls keep RED result interpretable.
def test_non_authorizing_finding_still_allowed():
    finding=lab.Finding('UNKNOWN','PROBE','HOLD')
    assert finding.evidence_admission=='NOT_EVALUATED'
    assert finding.claim_truth=='UNKNOWN'

@pytest.mark.parametrize('opposition_first',[False,True])
def test_same_declared_controller_cannot_cast_support_and_oppose_in_same_motion(opposition_first):
    c = council('REVIEW_CANDIDATE',3)
    # Group1 votes SUPPORT and OPPOSE under two different enrolled steward labels.
    roster=list(c.members)
    roster[3] = replace(roster[3], declared_control_group='Group1')
    yes=c.votes
    no=lab.Vote('OpposingBallot','Steward4',c.motion.digest,c.motion.epoch,'OPPOSE')
    votes=(no,)+yes if opposition_first else yes+(no,)
    result=lab.evaluate_council(replace(c,members=tuple(roster),votes=votes))
    assert result.lab_step=='HOLD' and result.rule=='W4D_SHARED_DECLARED_CONTROLLER',result
