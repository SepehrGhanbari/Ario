"""Independent, new review probes for synthetic W4-E PR #88.
Only tests known declared labels; does not equate distinct names to real people.
"""
from dataclasses import replace
import pytest
import w4e_structural_probe as lab
from test_w4e_structural_probe import fixture

READY = 'LAB_PACKET_READY_FOR_EXTERNAL_REVIEW'

@pytest.mark.parametrize('role', ['proposer_id', 'reviewer_id'])
def test_witness_own_identity_collision_with_proposer_or_reviewer(role):
    c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True)
    witnesses=list(c.declared_witnesses)
    witnesses[0]=replace(witnesses[0],witness_id=getattr(c,role))
    out=lab.inspect(replace(c,declared_witnesses=tuple(witnesses)))
    assert out.procedural_step=='HOLD',out

@pytest.mark.parametrize('role', ['principal_id', 'declared_issuer', 'declared_controller'])
def test_witness_own_identity_collision_with_governance_role(role):
    c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True)
    witnesses=list(c.declared_witnesses)
    witnesses[0]=replace(witnesses[0],witness_id=getattr(c.declared_stewards[0],role))
    out=lab.inspect(replace(c,declared_witnesses=tuple(witnesses)))
    assert out.procedural_step=='HOLD',out

class EqualToAnything:
    def __init__(self,display):self.display=display
    def __eq__(self,other):return True
    def __repr__(self):return self.display

@pytest.mark.parametrize('dimension',[
    'identity','controller_independence','witness_independence','review_authorization','admission','truth'
])
def test_finding_cannot_hold_non_string_equal_to_expected_constant(dimension):
    kwargs={dimension:EqualToAnything('VERIFIED_FAKE')}
    with pytest.raises(ValueError,match='W4E_CANNOT_PROMOTE_AUTHORITY_OR_TRUTH'):
        lab.Finding('UNKNOWN','W4E_TEST',**kwargs)

def test_nominal_shape_only_ready_is_still_possible():
    c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True)
    r=lab.inspect(c)
    assert r.procedural_step==READY
    assert r.truth=='UNKNOWN' and r.admission=='NOT_EVALUATED'
