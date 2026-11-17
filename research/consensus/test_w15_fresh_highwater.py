#!/usr/bin/env python3
"""W15 selected development controls. NOT an independent gold benchmark."""
import copy
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from w15_fresh_highwater_probe import assess, make_fixture, sign, verify, Ed25519PrivateKey, digest, read_json_file

class Cases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture,cls.remote0,cls.remote1=make_fixture()

    def test_matrix(self):
        f=self.fixture; x0=f['snapshots']['E0'];x1=f['snapshots']['E1'];e0=self.remote0;e1=self.remote1
        cases=[
            ('C01_old_with_fresh_remote_denied',x0,e1,'G1',None,None,'DENY','PRESENTED_STATE_BELOW_REMOTE_REFERENCE'),
            ('C02_old_with_old_remote_looks_eligible',x0,e0,'G1',None,None,'DECLARED_ELIGIBLE_FOR_SEPARATE_GATE','MATCHED_SIGNED_LAB_VIEW_NOT_WORLD_FRESHNESS'),
            ('C03_new_with_fresh_remote_revoked',x1,e1,'G1',None,None,'DENY','REVOKED_BY_PRESENTED_HEAD'),
            ('C04_new_unrevoked_grant_can_be_declared_eligible',x1,e1,'G2',None,None,'DECLARED_ELIGIBLE_FOR_SEPARATE_GATE','MATCHED_SIGNED_LAB_VIEW_NOT_WORLD_FRESHNESS'),
            ('C05_no_remote_is_hold',x0,None,'G1',None,None,'HOLD_UNCERTAIN','REMOTE_REFERENCE_UNAVAILABLE'),
            ('C06_new_local_remote_old_is_hold',x1,e0,'G1',None,None,'HOLD_UNCERTAIN','REMOTE_REFERENCE_BEHIND_PRESENTED_STATE'),
            ('C07_known_previous_floor_rejects_old_reference',x0,e0,'G1',None,1,'DENY','REMOTE_BELOW_PREVIOUSLY_SEEN_EPOCH'),
            ('C08_missing_grant_id_is_hold',x1,e1,'G404',None,None,'HOLD_UNCERTAIN','GRANT_ID_UNKNOWN'),
            ('C09_candidate_wrong_destination_denied',x1,e1,'G2',{'principal':'SYNTHETIC_USER','operation':'READ_ONLY_REVIEW','resource':'report-1','destination':'OTHER','now':150},None,'DENY','GRANT_SCOPE_MISMATCH'),
            ('C10_candidate_bad_time_denied',x1,e1,'G2',{'principal':'SYNTHETIC_USER','operation':'READ_ONLY_REVIEW','resource':'report-1','destination':'LOCAL_NOTE','now':250},None,'DENY','GRANT_TIME_MISMATCH'),
        ]
        for label,snapshot,remote,grant,candidate,floor,expected,reason in cases:
            with self.subTest(label):
                v=assess(f,snapshot,remote,grant,candidate,floor)
                self.assertEqual((v['verdict'],v['reason']),(expected,reason))
                self.assertEqual(v['operational_authority'],'NONE')
                self.assertFalse(v['remote_currentness_guaranteed'])
                self.assertEqual(v['external_actions'],0)

    def test_tamper(self):
        f=self.fixture;x1=f['snapshots']['E1']; e1=self.remote1
        def verdict(snap=x1,remote=e1):return assess(f,snap,remote,'G2')
        bad=copy.deepcopy(e1);bad['epoch']=2
        self.assertEqual(verdict(remote=bad)['reason'],'REMOTE_REFERENCE_SIGNATURE_OR_CONTENT_INVALID')
        bad=copy.deepcopy(e1);bad['anchor']['signature']='0'*128
        self.assertEqual(verdict(remote=bad)['reason'],'REMOTE_REFERENCE_SIGNATURE_OR_CONTENT_INVALID')
        bad=copy.deepcopy(x1);bad['head']['body']['revoked']=[]
        self.assertEqual(verdict(snap=bad)['reason'],'LOCAL_SIGNATURE_INVALID')
        bad=copy.deepcopy(e1);bad['anchor_packet_sha256']='0'*64
        self.assertEqual(verdict(remote=bad)['reason'],'REMOTE_REFERENCE_SIGNATURE_OR_CONTENT_INVALID')
        bad=copy.deepcopy(e1);bad['extra']='other'
        self.assertEqual(verdict(remote=bad)['reason'],'REMOTE_REFERENCE_SCHEMA')
        self.assertEqual(verdict(remote=e1)['verdict'],'DECLARED_ELIGIBLE_FOR_SEPARATE_GATE')
        self.assertEqual(assess(f,x1,e1,'G2',known_floor='1')['reason'],'LOCAL_HIGHWATER_BAD_TYPE')

    def test_digest_and_duplicate_key_check(self):
        with TemporaryDirectory() as folder:
            f=Path(folder)/'test.json'
            f.write_text('{"epoch": 1, "epoch": 0}')
            with self.assertRaisesRegex(ValueError,'DUPLICATE_JSON_KEY'):
                read_json_file(f)
            f.write_text('{"epoch":NaN}')
            with self.assertRaisesRegex(ValueError,'NONFINITE_JSON'):
                read_json_file(f)

    def test_important_negative_of_common_owner(self):
        # The author created BOTH remote E0 and remote E1. Even if a GitHub
        # public file is fetched, its owner can roll its contents back to E0.
        old=assess(self.fixture,self.fixture['snapshots']['E0'],self.remote0,'G1')
        fresh=assess(self.fixture,self.fixture['snapshots']['E0'],self.remote1,'G1')
        self.assertEqual(old['verdict'],'DECLARED_ELIGIBLE_FOR_SEPARATE_GATE')
        self.assertEqual(fresh['verdict'],'DENY')
        self.assertEqual(old['remote_reference_independent_custody'],'NOT_ESTABLISHED')

if __name__=='__main__':unittest.main(verbosity=2)
