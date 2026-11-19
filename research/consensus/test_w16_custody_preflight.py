#!/usr/bin/env python3
"""W16 original, author-designed controls — not independent reviewer validation."""
import copy
import json
import unittest
from w16_custody_preflight import assess, sample_local as L, sample_reference as R

class TestW16(unittest.TestCase):
    def setUp(self):
        self.p = R()
        self.q = R(provider='Other provider', admin='Owner-2', witness='Key-2')
        self.result_rows = []

    def test_cases(self):
        cases = [
            ('W16-01',L(),[self.p],None,'HOLD_UNCERTAIN','SAME_DECLARED_ADMIN_ROOT',True),
            ('W16-02',L(),[self.p,self.q],None,'HOLD_UNCERTAIN','DISTINCT_ADMIN_LABELS_UNVERIFIED',True),
            ('W16-03',L(),[self.p,{**self.q,'admin_root':'Owner-1'}],None,'HOLD_UNCERTAIN','SAME_DECLARED_ADMIN_ROOT',True),
            ('W16-04',L(0,'a'),[self.p],None,'DENY','LOCAL_BELOW_LATEST_OBSERVED_REFERENCE',False),
            ('W16-05',L(0,'a'),[R(epoch=0,head='a')],1,'DENY','LOCAL_BELOW_RETAINED_HIGHWATER',False),
            ('W16-06',L(1,'b'),[R(epoch=0,head='a')],1,'DENY','ALL_REFERENCES_BELOW_RETAINED_HIGHWATER',False),
            ('W16-07',L(1,'b'),[R(epoch=0,head='a')],None,'HOLD_UNCERTAIN','REFERENCE_LAGS_LOCAL',False),
            ('W16-08',L(1,'b'),[R(epoch=1,head='c')],None,'DENY','LOCAL_HEAD_CONFLICTS_WITH_DECLARED_REFERENCE',False),
            ('W16-09',L(1,'b'),[self.p,{**self.q,'head_sha256':'c'*64}],None,'DENY','DECLARED_SPLIT_VIEW_SAME_EPOCH',False),
            ('W16-10',L(),[],None,'HOLD_UNCERTAIN','NO_REFERENCE_AVAILABLE',False),
            ('W16-11',L(),None,None,'HOLD_UNCERTAIN','NO_REFERENCE_AVAILABLE',False),
            ('W16-12',L(),[self.p,{**self.q,'witness_key':'Key-1'}],None,'HOLD_UNCERTAIN','DUPLICATE_WITNESS_KEY',False),
            ('W16-13',L(),[{**self.p,'reported_signature_valid':False}],None,'HOLD_UNCERTAIN','REPORTED_SIGNATURE_UNVERIFIED',False),
            ('W16-14',L(),[{**self.p,'reported_signature_valid':'true'}],None,'HOLD_UNCERTAIN','REPORTED_SIGNATURE_TYPE',False),
            ('W16-15',L(),[self.p],True,'HOLD_UNCERTAIN','INVALID_TRUSTED_HIGHWATER_INPUT',False),
            ('W16-16',{'epoch':True,'head_sha256':'b'*64},[self.p],None,'HOLD_UNCERTAIN','INVALID_LOCAL_EPOCH_OR_HASH',False),
            ('W16-17',L(),[self.p, {**self.q, 'epoch':0,'head_sha256':'a'*64}],None,'HOLD_UNCERTAIN','MIXED_REFERENCE_FRESHNESS',True),
            ('W16-18',L(),[self.p]*9,None,'HOLD_UNCERTAIN','REFERENCE_RESOURCE_LIMIT',False),
            ('W16-19',L(),[{**self.p,'extra':'untrusted'}],None,'HOLD_UNCERTAIN','REFERENCE_SCHEMA',False),
            ('W16-20',L(),[{**self.p,'admin_root':''}],None,'HOLD_UNCERTAIN','REFERENCE_STRING_TYPES',False),
            ('W16-21',L(),[{**self.p,'head_sha256':'not-sha256'}],None,'HOLD_UNCERTAIN','REFERENCE_VERSION_OR_HASH',False),
            ('W16-22',L(1,'b'),[self.p,self.q],1,'HOLD_UNCERTAIN','DISTINCT_ADMIN_LABELS_UNVERIFIED',True),
            ('W16-23',L(1,'b'),[R(provider='GitHub',admin='A',witness='K-1'),R(provider='GitHub',admin='A',witness='K-2')],None,'HOLD_UNCERTAIN','SAME_DECLARED_ADMIN_ROOT',True),
            ('W16-24',L(1,'b'),[R(provider='GitHub',admin='A',witness='K-1'),R(provider='Zenodo',admin='A',witness='K-2')],None,'HOLD_UNCERTAIN','SAME_DECLARED_ADMIN_ROOT',True),
        ]
        for name,local,refs,floor,expected,reason,preview in cases:
            with self.subTest(name=name):
                r=assess(local,refs,floor)
                self.assertEqual((r['verdict'],r['reason'],r['read_only_preview']),(expected,reason,preview))
                self.assertEqual(r['operational_authority'],'NONE')
                self.assertEqual(r['external_actions'],0)
                self.assertFalse(r['memory_admitted'])
                self.assertEqual(r['independent_administrative_custody'],'NOT_ESTABLISHED')
                self.result_rows.append({'id':name,'verdict':r['verdict'],'reason':r['reason'],'preview':r['read_only_preview']})
        self.assertEqual(len(self.result_rows),24)

    def test_false_claim_of_independence_never_grants_authority(self):
        p=copy.deepcopy(self.p);q=copy.deepcopy(self.q)
        p['admin_root']='Verified Independent-1';q['admin_root']='Verified Independent-2'
        r=assess(L(),[p,q])
        self.assertEqual(r['reason'],'DISTINCT_ADMIN_LABELS_UNVERIFIED')
        self.assertEqual(r['remote_currentness'],'NOT_ESTABLISHED')
        self.assertEqual(r['operational_authority'],'NONE')

    def test_legacy_stale_pair_has_preview_but_no_permission(self):
        r=assess(L(epoch=0,head='a'), [R(epoch=0,head='a')])
        self.assertTrue(r['read_only_preview'])
        self.assertEqual(r['verdict'],'HOLD_UNCERTAIN')

if __name__ == '__main__':
    unittest.main(verbosity=2)
