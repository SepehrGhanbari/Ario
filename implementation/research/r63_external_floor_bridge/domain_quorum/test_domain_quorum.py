import unittest
from dataclasses import replace
from domain_quorum import *

P="policy-r63-domain-v1"
H="proposal-v11"
ROWS=[
 ("geomys","k1","geomys","admin-g","key-g","backup-g"),
 ("ipng","k2","ipng","admin-i","key-i","backup-i"),
 ("mullvad","k3","mullvad","admin-m","key-m","backup-m"),
 ("trustfabric","k4","trustfabric","admin-t","key-t","backup-t"),
]
def setup():
    return build_policy(P, ROWS)
def receipt(w, **kw):
    base=Receipt(w.witness_id,w.key_fingerprint,P,H,11,True,True,True,True,True)
    return replace(base,**kw)
class DomainQuorumTests(unittest.TestCase):
    def setUp(self):
        self.p=setup()
        self.rs=[receipt(w) for w in self.p.roster.values()]
    def test_01_three_independent_admin_domains_pass(self):
        d=evaluate(self.p,H,self.rs[:3],mode="write")
        self.assertTrue(d.accepted)
    def test_02_four_independent_domains_pass(self):
        self.assertTrue(evaluate(self.p,H,self.rs,mode="read").accepted)
    def test_03_two_receipts_hold(self):
        self.assertFalse(evaluate(self.p,H,self.rs[:2],mode="write").accepted)
    def test_04_three_keys_same_operator_not_three_votes(self):
        rows=[("g1","k1","glasklar","g-admin","g-key","g-backup"),
              ("g2","k2","glasklar","g-admin","g-key","g-backup"),
              ("g3","k3","glasklar","g-admin","g-key","g-backup"),
              ("ipng","k4","ipng","i-admin","i-key","i-backup")]
        p=build_policy(P,rows)
        d=evaluate(p,H,[receipt(w) for w in p.roster.values()],mode="write")
        self.assertFalse(d.accepted)
        self.assertEqual(d.domain_counts["operator"],2)
    def test_05_three_operators_shared_admin_controller_hold(self):
        rows=[("a","k1","org-a","common-admin","key-a","backup-a"),
              ("b","k2","org-b","common-admin","key-b","backup-b"),
              ("c","k3","org-c","common-admin","key-c","backup-c"),
              ("d","k4","org-d","common-admin","key-d","backup-d")]
        p=build_policy(P,rows)
        d=evaluate(p,H,[receipt(w) for w in p.roster.values()],mode="write")
        self.assertFalse(d.accepted)
        self.assertEqual(d.domain_counts["admin"],1)
    def test_06_shared_key_custodian_hold(self):
        rows=[("a","k1","org-a","a","common-key","a"),
              ("b","k2","org-b","b","common-key","b"),
              ("c","k3","org-c","c","common-key","c"),
              ("d","k4","org-d","d","common-key","d")]
        p=build_policy(P,rows)
        self.assertFalse(evaluate(p,H,[receipt(w) for w in p.roster.values()],mode="write").accepted)
    def test_07_shared_backup_admin_hold(self):
        rows=[("a","k1","a","aa","ka","common"),
              ("b","k2","b","bb","kb","common"),
              ("c","k3","c","cc","kc","common"),
              ("d","k4","d","dd","kd","common")]
        p=build_policy(P,rows)
        self.assertFalse(evaluate(p,H,[receipt(w) for w in p.roster.values()],mode="write").accepted)
    def test_08_unknown_admin_fails_closed(self):
        rows=list(ROWS); rows[0]=("geomys","k1","geomys","UNKNOWN","key-g","backup-g")
        p=build_policy(P,rows)
        self.assertFalse(evaluate(p,H,[receipt(w) for w in p.roster.values()],mode="write").accepted)
    def test_09_unverified_roster_fails_closed(self):
        roster=dict(self.p.roster); roster["geomys"]=replace(roster["geomys"],verified=False)
        p=replace(self.p,roster=roster)
        self.assertFalse(evaluate(p,H,self.rs,mode="write").accepted)
    def test_10_missing_evidence_fails_closed(self):
        roster=dict(self.p.roster); roster["geomys"]=replace(roster["geomys"],evidence_ref="")
        p=replace(self.p,roster=roster)
        self.assertFalse(evaluate(p,H,self.rs,mode="write").accepted)
    def test_11_duplicate_witness_fails(self):
        d=evaluate(self.p,H,[self.rs[0],self.rs[0],self.rs[1],self.rs[2]],mode="write")
        self.assertFalse(d.accepted)
        self.assertIn("DUPLICATE_WITNESS:geomys",d.reasons)
    def test_12_unknown_witness_fails(self):
        x=replace(self.rs[0],witness_id="unknown")
        self.assertFalse(evaluate(self.p,H,[x,*self.rs[1:3]],mode="write").accepted)
    def test_13_key_mismatch_fails(self):
        x=replace(self.rs[0],key_fingerprint="wrong")
        self.assertFalse(evaluate(self.p,H,[x,*self.rs[1:3]],mode="write").accepted)
    def test_14_duplicate_keys_fails_policy(self):
        rows=list(ROWS); rows[1]=("ipng","k1","ipng","admin-i","key-i","backup-i")
        p=build_policy(P,rows)
        self.assertFalse(evaluate(p,H,[receipt(w) for w in p.roster.values()],mode="write").accepted)
    def test_15_policy_mismatch_fails(self):
        x=replace(self.rs[0],policy_hash="old")
        self.assertFalse(evaluate(self.p,H,[x,*self.rs[1:3]],mode="write").accepted)
    def test_16_proposal_mismatch_fails(self):
        x=replace(self.rs[0],proposal_hash="old")
        self.assertFalse(evaluate(self.p,H,[x,*self.rs[1:3]],mode="write").accepted)
    def test_17_bad_signature_fails(self):
        x=replace(self.rs[0],signature_valid=False)
        self.assertFalse(evaluate(self.p,H,[x,*self.rs[1:3]],mode="write").accepted)
    def test_18_stale_receipt_fails(self):
        x=replace(self.rs[0],fresh=False)
        self.assertFalse(evaluate(self.p,H,[x,*self.rs[1:3]],mode="read").accepted)
    def test_19_not_durable_fails(self):
        x=replace(self.rs[0],durable=False)
        self.assertFalse(evaluate(self.p,H,[x,*self.rs[1:3]],mode="write").accepted)
    def test_20_no_continuity_proof_fails(self):
        x=replace(self.rs[0],continuity_proven=False)
        self.assertFalse(evaluate(self.p,H,[x,*self.rs[1:3]],mode="write").accepted)
    def test_21_read_requires_readback(self):
        x=[replace(r,readback_proven=False) for r in self.rs[:3]]
        self.assertFalse(evaluate(self.p,H,x,mode="read").accepted)
    def test_22_write_does_not_require_readback(self):
        x=[replace(r,readback_proven=False) for r in self.rs[:3]]
        self.assertTrue(evaluate(self.p,H,x,mode="write").accepted)
    def test_23_readback_quorum_passes(self):
        self.assertTrue(evaluate(self.p,H,self.rs[:3],mode="read").accepted)
    def test_24_invalid_mode_fails(self):
        self.assertFalse(evaluate(self.p,H,self.rs,mode="other").accepted)
    def test_25_wrong_sequence_fails(self):
        x=replace(self.rs[0],sequence=10)
        self.assertFalse(evaluate(self.p,H,[x,*self.rs[1:3]],mode="write").accepted)
    def test_26_write_read_intersection_3_of_4_f1(self):
        self.assertTrue(quorum_intersection_holds(4,3,3,1))
    def test_27_write2_read3_not_safe_for_f1(self):
        self.assertFalse(quorum_intersection_holds(4,2,3,1))
    def test_28_write3_read2_not_safe_for_f1(self):
        self.assertFalse(quorum_intersection_holds(4,3,2,1))
    def test_29_write3_read3_f2_not_safe(self):
        self.assertFalse(quorum_intersection_holds(4,3,3,2))
    def test_30_write4_read4_f2_safe(self):
        self.assertTrue(quorum_intersection_holds(5,4,4,2))
    def test_31_insufficient_independent_operator_domains(self):
        rows=[("a","k1","same","a","a","a"),("b","k2","same","b","b","b"),
              ("c","k3","same","c","c","c"),("d","k4","other","d","d","d")]
        p=build_policy(P,rows)
        self.assertFalse(evaluate(p,H,[receipt(w) for w in p.roster.values()],mode="write").accepted)
    def test_32_missing_roster_domain_class_fails(self):
        roster=dict(self.p.roster); d=dict(roster["geomys"].domains); d.pop("state_backup")
        roster["geomys"]=replace(roster["geomys"],domains=d)
        p=replace(self.p,roster=roster)
        self.assertFalse(evaluate(p,H,self.rs,mode="write").accepted)
    def test_33_two_admin_groups_plus_distinct_keys_not_enough(self):
        rows=[("a","k1","a","admin-x","ka","ba"),("b","k2","b","admin-x","kb","bb"),
              ("c","k3","c","admin-y","kc","bc"),("d","k4","d","admin-y","kd","bd")]
        p=build_policy(P,rows)
        self.assertFalse(evaluate(p,H,[receipt(w) for w in p.roster.values()],mode="write").accepted)
    def test_34_three_independent_admin_but_one_shared_backup(self):
        rows=[("a","k1","a","aa","ka","backup-x"),("b","k2","b","bb","kb","backup-x"),
              ("c","k3","c","cc","kc","backup-x"),("d","k4","d","dd","kd","backup-y")]
        p=build_policy(P,rows)
        self.assertFalse(evaluate(p,H,[receipt(w) for w in p.roster.values()],mode="write").accepted)
    def test_35_four_distinct_failure_domain_classes(self):
        d=evaluate(self.p,H,self.rs,mode="write")
        self.assertEqual(d.domain_counts,{"operator":4,"admin":4,"key_custody":4,"state_backup":4})
    def test_36_policy_requires_nonempty_domain_classes(self):
        p=replace(self.p,required_domain_classes=())
        self.assertFalse(evaluate(p,H,self.rs,mode="write").accepted)
    def test_37_roster_too_small(self):
        p=replace(self.p,roster={k:v for k,v in list(self.p.roster.items())[:2]})
        self.assertFalse(evaluate(p,H,self.rs[:2],mode="write").accepted)
    def test_38_intersection_out_of_bounds(self):
        self.assertFalse(quorum_intersection_holds(3,4,3,1))
    def test_39_distinct_admin_but_shared_operator_is_still_one_operator(self):
        rows=[("a","k1","same","a","ka","ba"),("b","k2","same","b","kb","bb"),
              ("c","k3","other1","c","kc","bc"),("d","k4","same","d","kd","bd")]
        p=build_policy(P,rows)
        self.assertFalse(evaluate(p,H,[receipt(w) for w in p.roster.values()],mode="write").accepted)
    def test_40_distinct_operator_but_shared_keycustody(self):
        rows=[("a","k1","a","a","kc","a"),("b","k2","b","b","kc","b"),
              ("c","k3","c","c","kc","c"),("d","k4","d","d","kd","d")]
        p=build_policy(P,rows)
        self.assertFalse(evaluate(p,H,[receipt(w) for w in p.roster.values()],mode="write").accepted)

    def test_41_intersection_uses_domains_not_key_count(self):
        rows=[("g1","k1","glasklar","g-admin","g-key","g-backup"),
              ("g2","k2","glasklar","g-admin","g-key","g-backup"),
              ("g3","k3","glasklar","g-admin","g-key","g-backup"),
              ("ipng","k4","ipng","i-admin","i-key","i-backup"),
              ("mullvad","k5","mullvad","m-admin","m-key","m-backup")]
        p=build_policy(P,rows,read_q=3,write_q=3,f=2)
        # Only 3 independent operators, not 5 witness keys. A 3/3 quorum
        # intersects in 3 domains, so it can tolerate f=2 here.
        self.assertTrue(evaluate(p,H,[receipt(w) for w in p.roster.values()],mode="write").accepted)
        self.assertNotIn("READ_WRITE_INTERSECTION_UNSAFE",validate_policy(p))
    def test_42_quorum_counts_operator_domains(self):
        rows=[("g1","k1","glasklar","g-admin","g-key","g-backup"),
              ("g2","k2","glasklar","g-admin","g-key","g-backup"),
              ("ipng","k3","ipng","i-admin","i-key","i-backup"),
              ("mullvad","k4","mullvad","m-admin","m-key","m-backup")]
        p=build_policy(P,rows)
        d=evaluate(p,H,[receipt(w) for w in p.roster.values()],mode="write")
        self.assertTrue(d.accepted)
        self.assertEqual(d.domain_counts["operator"],3)
    def test_43_read_quorum_threshold_applies_to_domains(self):
        p=replace(self.p,read_quorum=4)
        d=evaluate(p,H,self.rs[:3],mode="read")
        self.assertFalse(d.accepted)
    def test_44_write_quorum_threshold_applies_to_domains(self):
        p=replace(self.p,write_quorum=4)
        d=evaluate(p,H,self.rs[:3],mode="write")
        self.assertFalse(d.accepted)

if __name__=="__main__": unittest.main(verbosity=2)
