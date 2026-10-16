"""W4-E offline negative and positive *structural* controls only."""
from dataclasses import replace
import unittest
from w4e_structural_probe import Case, Steward, Witness, Finding, inspect

H="a"*64
J="b"*64

def fixture(**kwargs):
    stewards=(Steward("P1","Key1","GovA","IssuerA"),Steward("P2","Key2","GovB","IssuerB"),Steward("P3","Key3","GovC","IssuerC"))
    witnesses=(Witness("W1","Source1","WCtrl1","Raw1","Event1"),Witness("W2","Source2","WCtrl2","Raw2","Event1"))
    return replace(Case("Case1","REVIEW_CANDIDATE","ArioOffline",H,"Proposer","Reviewer",stewards,witnesses,"REVIEW_CANDIDATE",H,H,"FRESH_CLAIMED","GRANTED_CLAIMED",True),**kwargs)

class Tests(unittest.TestCase):
    def check(self,c,rule):
        r=inspect(c);self.assertEqual(r.rule,rule);self.assertIn(r.status,{"UNKNOWN","REJECTED"});self.assertEqual(r.identity,"UNKNOWN");self.assertEqual(r.controller_independence,"UNKNOWN");self.assertEqual(r.witness_independence,"UNKNOWN");self.assertEqual(r.review_authorization,"UNKNOWN");self.assertEqual(r.admission,"NOT_EVALUATED");self.assertEqual(r.truth,"UNKNOWN")
    def test_happy_structural_is_never_authority(self):
        c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True)
        r=inspect(c);self.check(c,"W4E_MOCK_DECLARATIONS_ONLY");self.assertEqual(r.procedural_step,"LAB_PACKET_READY_FOR_EXTERNAL_REVIEW")
    def test_unknown_auth(self):self.check(fixture(),"W4E_AUTH_OR_TIME_NOT_ESTABLISHED")
    def test_untrusted_time(self):self.check(fixture(identity_binding_claimed=True),"W4E_AUTH_OR_TIME_NOT_ESTABLISHED")
    def test_self_review(self):self.check(fixture(reviewer_id="Proposer"),"W4E_SELF_REVIEW")
    def test_revoked(self):self.check(fixture(revocation_state="REVOKED"),"W4E_DECLARED_REVOCATION")
    def test_consent_withdrawn(self):self.check(fixture(consent="WITHDRAWN"),"W4E_DECLARED_CONSENT_WITHDRAWN")
    def test_no_consent(self):self.check(fixture(consent="UNKNOWN"),"W4E_CONSENT_UNRESOLVED")
    def test_unsupported_action(self):self.check(fixture(action="ADMIT_EVIDENCE"),"W4E_BAD_ENVELOPE_OR_ACTION")
    def test_bad_scope(self):self.check(fixture(stated_grant_scope="OTHER"),"W4E_BAD_ENVELOPE_OR_ACTION")
    def test_bad_digest(self):self.check(fixture(digest="FAKE"),"W4E_BAD_ENVELOPE_OR_ACTION")
    def test_duplicate_principal(self):
        c=fixture();st=list(c.declared_stewards);st[1]=replace(st[1],principal_id="P1");self.check(replace(c,declared_stewards=tuple(st)),"W4E_DUPLICATE_PRINCIPAL_OR_KEY")
    def test_duplicate_key(self):
        c=fixture();st=list(c.declared_stewards);st[1]=replace(st[1],key_id="Key1");self.check(replace(c,declared_stewards=tuple(st)),"W4E_DUPLICATE_PRINCIPAL_OR_KEY")
    def test_duplicate_controller(self):
        c=fixture();st=list(c.declared_stewards);st[1]=replace(st[1],declared_controller="GovA");self.check(replace(c,declared_stewards=tuple(st)),"W4E_KNOWN_DECLARED_SHARED_CONTROLLER")
    def test_proposer_on_roster(self):
        c=fixture();st=list(c.declared_stewards);st[1]=replace(st[1],principal_id="Proposer");self.check(replace(c,declared_stewards=tuple(st)),"W4E_ROLE_CONFLICT_REQUIRES_REVIEW")
    def test_shared_issuer_even_with_unique_keys(self):
        c=fixture();st=list(c.declared_stewards);st[1]=replace(st[1],declared_issuer="IssuerA")
        self.check(replace(c,declared_stewards=tuple(st)),"W4E_KNOWN_DECLARED_SHARED_ISSUER")
    def test_reviewer_part_of_reviewing_council(self):
        c=fixture();st=list(c.declared_stewards);st[0]=replace(st[0],principal_id="Reviewer")
        self.check(replace(c,declared_stewards=tuple(st)),"W4E_ROLE_CONFLICT_REQUIRES_REVIEW")
    def test_witness_controller_overlaps_steward_controller(self):
        c=fixture();w=list(c.declared_witnesses);w[0]=replace(w[0],declared_controller="GovA")
        self.check(replace(c,declared_witnesses=tuple(w)),"W4E_WITNESS_AND_GOVERNANCE_CONTROL_OVERLAP")
    def test_duplicate_witness_id(self):
        c=fixture();w=list(c.declared_witnesses);w[1]=replace(w[1],witness_id="W1");self.check(replace(c,declared_witnesses=tuple(w)),"W4E_DUPLICATE_WITNESS_ID")
    def test_shared_source(self):
        c=fixture();w=list(c.declared_witnesses);w[1]=replace(w[1],source_id="Source1");self.check(replace(c,declared_witnesses=tuple(w)),"W4E_KNOWN_DECLARED_SHARED_SOURCE")
    def test_unknown_parent(self):
        c=fixture();w=list(c.declared_witnesses);w[1]=replace(w[1],upstream_observation_id=None);self.check(replace(c,declared_witnesses=tuple(w)),"W4E_INCOMPLETE_DECLARED_PROVENANCE")
    def test_shared_parent(self):
        c=fixture();w=list(c.declared_witnesses);w[1]=replace(w[1],upstream_observation_id="Raw1");self.check(replace(c,declared_witnesses=tuple(w)),"W4E_KNOWN_DECLARED_SHARED_ANCESTOR")
    def test_shared_witness_controller(self):
        c=fixture();w=list(c.declared_witnesses);w[1]=replace(w[1],declared_controller="WCtrl1");self.check(replace(c,declared_witnesses=tuple(w)),"W4E_KNOWN_DECLARED_SHARED_WITNESS_CONTROL")
    def test_event_mismatch(self):
        c=fixture();w=list(c.declared_witnesses);w[1]=replace(w[1],event_id="Event2");self.check(replace(c,declared_witnesses=tuple(w)),"W4E_EVENT_INSTANCE_NOT_COMPARABLE")
    def test_registry_missing(self):self.check(fixture(current_registry_digest=None),"W4E_REGISTRY_MISSING_OR_FORKED")
    def test_registry_fork(self):self.check(fixture(presented_registry_digest=J),"W4E_REGISTRY_MISSING_OR_FORKED")
    def test_revocation_unknown(self):self.check(fixture(revocation_state="UNKNOWN"),"W4E_REVOCATION_FRESHNESS_UNESTABLISHED")
    def test_no_appeal(self):self.check(fixture(appeal_path_declared=False),"W4E_NO_DECLARED_APPEAL_PATH")
    def test_bool_int_as_identity_rejected(self):
        c=fixture();st=list(c.declared_stewards);st[1]=replace(st[1],principal_id=True);self.check(replace(c,declared_stewards=tuple(st)),"W4E_BAD_STEWARD_DECLARATION")
    def test_unhashable_key_rejected(self):
        c=fixture();st=list(c.declared_stewards);st[1]=replace(st[1],key_id=[]);self.check(replace(c,declared_stewards=tuple(st)),"W4E_BAD_STEWARD_DECLARATION")
    def test_bad_source_upstream(self):
        c=fixture();w=list(c.declared_witnesses);w[1]=replace(w[1],upstream_observation_id=[]);self.check(replace(c,declared_witnesses=tuple(w)),"W4E_BAD_UPSTREAM_REFERENCE")
    def test_disallowed_positive_result_object(self):
        with self.assertRaises(ValueError):Finding("VERIFIED","BROKEN")
        with self.assertRaises(ValueError):Finding("UNKNOWN","BROKEN",procedural_step="ADMITTED")
        with self.assertRaises(ValueError):Finding("UNKNOWN","BROKEN",review_authorization="VERIFIED_FOR_REVIEW_ONLY")
    def test_forbidden_large_input(self):
        c=fixture();self.check(replace(c,declared_witnesses=c.declared_witnesses*12),"W4E_BAD_ENVELOPE_OR_ACTION")
    def test_empty_stewards(self):self.check(fixture(declared_stewards=()),"W4E_BAD_ENVELOPE_OR_ACTION")
    def test_string_vote_roster_fails(self):self.check(fixture(declared_stewards="P1,P2"),"W4E_BAD_ENVELOPE_OR_ACTION")
    def test_bad_appeal_flag(self):self.check(fixture(appeal_path_declared="true"),"W4E_BAD_ENVELOPE_OR_ACTION")
    def test_bogus_signatures_not_a_positive_field(self):
        c=fixture(identity_binding_claimed=True,clock_freshness_claimed=True);self.assertEqual(inspect(c).status,"UNKNOWN")

if __name__=="__main__":unittest.main()
