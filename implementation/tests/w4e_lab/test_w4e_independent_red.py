"""Independent extra negative probes against W4-E synthetic review labels.

These tests do not assert verified real-world identity or evidence admission.
They check if known disclosed conflicts or insufficient plurality can trigger
an overly helpful LAB_PACKET_READY_FOR_EXTERNAL_REVIEW suggestion.
"""
from dataclasses import replace
import unittest
import w4e_structural_probe as lab
from test_w4e_structural_probe import fixture

class W4ESecondPass(unittest.TestCase):
    def assert_hold(self, case):
        result=lab.inspect(case)
        self.assertIn(result.status, {'UNKNOWN','REJECTED'})
        self.assertEqual(result.procedural_step,'HOLD', result)
        self.assertEqual(result.review_authorization,'UNKNOWN')
        self.assertEqual(result.admission,'NOT_EVALUATED')
        self.assertEqual(result.truth,'UNKNOWN')

    def test_one_governance_steward_is_not_plurality(self):
        c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True)
        self.assert_hold(replace(c,declared_stewards=c.declared_stewards[:1]))

    def test_one_witness_is_not_source_plurality(self):
        c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True)
        self.assert_hold(replace(c,declared_witnesses=c.declared_witnesses[:1]))

    def test_steward_self_issuer_declared_overlap(self):
        c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True)
        stewards=list(c.declared_stewards)
        stewards[0]=replace(stewards[0],declared_issuer=stewards[0].principal_id)
        self.assert_hold(replace(c,declared_stewards=tuple(stewards)))

    def test_issuer_is_another_governing_steward(self):
        c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True)
        stewards=list(c.declared_stewards)
        stewards[0]=replace(stewards[0],declared_issuer=stewards[1].principal_id)
        self.assert_hold(replace(c,declared_stewards=tuple(stewards)))

    def test_issuer_is_proposer(self):
        c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True)
        stewards=list(c.declared_stewards)
        stewards[0]=replace(stewards[0],declared_issuer=c.proposer_id)
        self.assert_hold(replace(c,declared_stewards=tuple(stewards)))

    def test_issuer_is_reviewer(self):
        c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True)
        stewards=list(c.declared_stewards)
        stewards[0]=replace(stewards[0],declared_issuer=c.reviewer_id)
        self.assert_hold(replace(c,declared_stewards=tuple(stewards)))

    def test_issuer_is_declared_witness_controller(self):
        c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True)
        stewards=list(c.declared_stewards)
        stewards[0]=replace(stewards[0],declared_issuer=c.declared_witnesses[0].declared_controller)
        self.assert_hold(replace(c,declared_stewards=tuple(stewards)))

    def test_proposer_equals_declared_witness_controller(self):
        c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True)
        self.assert_hold(replace(c,proposer_id=c.declared_witnesses[0].declared_controller))

    def test_reviewer_equals_declared_witness_controller(self):
        c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True)
        self.assert_hold(replace(c,reviewer_id=c.declared_witnesses[0].declared_controller))

    def test_steward_controller_is_proposer(self):
        c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True)
        stewards=list(c.declared_stewards)
        stewards[0]=replace(stewards[0],declared_controller=c.proposer_id)
        self.assert_hold(replace(c,declared_stewards=tuple(stewards)))

    def test_steward_controller_is_reviewer(self):
        c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True)
        stewards=list(c.declared_stewards)
        stewards[0]=replace(stewards[0],declared_controller=c.reviewer_id)
        self.assert_hold(replace(c,declared_stewards=tuple(stewards)))

    def test_steward_controller_equals_other_issuer(self):
        c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True)
        stewards=list(c.declared_stewards)
        stewards[0]=replace(stewards[0],declared_controller=stewards[1].declared_issuer)
        self.assert_hold(replace(c,declared_stewards=tuple(stewards)))

    def test_steward_principal_equals_witness_controller(self):
        c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True)
        witnesses=list(c.declared_witnesses)
        witnesses[0]=replace(witnesses[0],declared_controller=c.declared_stewards[0].principal_id)
        self.assert_hold(replace(c,declared_witnesses=tuple(witnesses)))

    def test_nominal_structural_packet_still_possible(self):
        c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True)
        o=lab.inspect(c)
        self.assertEqual(o.procedural_step,'LAB_PACKET_READY_FOR_EXTERNAL_REVIEW')
        self.assertEqual(o.identity,'UNKNOWN')
        self.assertEqual(o.admission,'NOT_EVALUATED')

if __name__=='__main__':unittest.main()
