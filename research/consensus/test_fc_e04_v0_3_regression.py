#!/usr/bin/env python3
"""Source-pinned FC-E04 read-only research regression; synthetic inputs only."""
import copy
import hashlib
import json
import unittest
from pathlib import Path

import fc_e04_readonly_comparator_v0_3 as f

w9 = f._load_w9()

def seed(ids=('R1','R2'), parents=False):
    receipts=[w9.receipt(id=i) for i in ids]
    edges=[{'receipt_id':i,'root_id':'ROOT_A' if i=='R1' else 'ROOT_B','parents':[]} for i in ids]
    if parents and len(ids)>1:
        edges[1]={'receipt_id':ids[1],'root_id':None,'parents':[ids[0]]}
    return {'schema':f.SCHEMA,'claim':w9.claim(),'receipts':receipts,'lineage':edges}

def enc(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'),ensure_ascii=False).encode()

class FCE04(unittest.TestCase):
    seen=[]
    def assert_gate(self, output):
        self.assertEqual(output['source_custody'],'NOT_ESTABLISHED')
        self.assertEqual(output['independent_corroboration'],'UNKNOWN')
        self.assertEqual(output['world_truth'],'UNKNOWN')
        self.assertEqual(output['assessment'],'NOT_ASSESSED')
        self.assertEqual(output['action_authority'],'NONE')
        self.assertIs(output['memory_admitted'],False)

    def actual(self, obj, expected_status, expected_roots=None, expected_reason=None, override=None):
        raw=enc(obj) if type(obj) is dict else obj
        out=f.evaluate_image(raw, recognition_override=override)
        self.assert_gate(out)
        self.assertEqual(out['final']['status'],expected_status, out)
        if expected_roots is not None:
            self.assertEqual(out['final']['declared_root_count'],expected_roots,out)
        if expected_reason:
            self.assertEqual(out['final']['reason'],expected_reason,out)
        if type(raw) is bytes and len(raw)<=f.MAX_BYTES:
            self.assertEqual(out['image_sha256'],hashlib.sha256(raw).hexdigest())
        else:
            self.assertIsNone(out['image_sha256'])
        return out

    def test_01_one_root_two_reports(self):
        r=seed(parents=True)
        x=self.actual(r,'DECLARED_ROOT_PARTITION_ONLY',1)
        self.assertEqual(x['final']['illustrative_occurrence_count'],2)
        self.assertEqual(x['recognition']['root_sets']['R2'],['ROOT_A'])

    def test_02_two_roots_two_reports(self):
        x=self.actual(seed(),'DECLARED_ROOT_PARTITION_ONLY',2)
        self.assertEqual(x['final']['illustrative_occurrence_count'],2)

    def test_03_same_bytes_stage_differential(self):
        a=seed(parents=True);b=seed()
        x=f.evaluate_image(enc(a));y=f.evaluate_image(enc(b))
        self.assertEqual(x['w9_relation'],y['w9_relation'])
        self.assertEqual(x['final']['illustrative_occurrence_count'],y['final']['illustrative_occurrence_count'])
        self.assertNotEqual(x['final']['declared_root_count'],y['final']['declared_root_count'])
        self.assert_gate(x);self.assert_gate(y)

    def test_04_eight_reports_one_root(self):
        r=seed(ids=tuple('R'+str(i) for i in range(8)))
        r['lineage']=[{'receipt_id':v['id'],'root_id':'ROOT_A' if i==0 else None,
                       'parents':[] if i==0 else ['R0']} for i,v in enumerate(r['receipts'])]
        self.actual(r,'DECLARED_ROOT_PARTITION_ONLY',1)

    def test_05_two_roots_with_derivations(self):
        r=seed(ids=('R1','R2','R3','R4'))
        r['lineage']=[{'receipt_id':'R1','root_id':'A','parents':[]},
                      {'receipt_id':'R2','root_id':'B','parents':[]},
                      {'receipt_id':'R3','root_id':None,'parents':['R1']},
                      {'receipt_id':'R4','root_id':None,'parents':['R1','R2']}]
        x=self.actual(r,'DECLARED_ROOT_PARTITION_ONLY',2)
        self.assertEqual(x['recognition']['root_sets']['R4'],['A','B'])

    def test_06_missing_lineage(self):
        r=seed();r['lineage']=[]
        self.actual(r,'UNKNOWN',expected_reason='LINEAGE_MISSING_OR_COUNT')

    def test_07_unknown_parent(self):
        r=seed(parents=True);r['lineage'][1]['parents']=['MISSING']
        self.actual(r,'UNKNOWN',expected_reason='LINEAGE_MISSING_PARENT')

    def test_08_cycle(self):
        r=seed(parents=True)
        r['lineage'][0]={'receipt_id':'R1','root_id':None,'parents':['R2']}
        self.actual(r,'UNKNOWN',expected_reason='LINEAGE_CYCLE')

    def test_09_self_cycle(self):
        r=seed();r['lineage'][0]={'receipt_id':'R1','root_id':None,'parents':['R1']}
        self.actual(r,'UNKNOWN',expected_reason='LINEAGE_CYCLE')

    def test_10_source_and_parent(self):
        r=seed();r['lineage'][1]['parents']=['R1']
        self.actual(r,'UNKNOWN',expected_reason='LINEAGE_ROOT_PARENT_EXCLUSIVE')

    def test_11_no_root_and_no_parent(self):
        r=seed();r['lineage'][1]['root_id']=None
        self.actual(r,'UNKNOWN',expected_reason='LINEAGE_ROOT_PARENT_EXCLUSIVE')

    def test_12_duplicate_lineage_id(self):
        r=seed();r['lineage'][1]['receipt_id']='R1'
        self.actual(r,'UNKNOWN',expected_reason='LINEAGE_DUPLICATE_OR_ID')

    def test_13_lineage_orphan(self):
        r=seed();r['lineage'][1]['receipt_id']='ORPHAN'
        self.actual(r,'UNKNOWN',expected_reason='LINEAGE_RECEIPT_SET_MISMATCH')

    def test_14_duplicate_parent(self):
        r=seed(parents=True);r['lineage'][1]['parents']=['R1','R1']
        self.actual(r,'UNKNOWN',expected_reason='LINEAGE_DUPLICATE_PARENT')

    def test_15_bad_root_type(self):
        r=seed();r['lineage'][1]['root_id']=123
        self.actual(r,'UNKNOWN',expected_reason='LINEAGE_ROOT_INVALID')

    def test_16_duplicate_receipt(self):
        r=seed();r['receipts'][1]['id']='R1'
        self.actual(r,'UNKNOWN',expected_reason='RECEIPT_IDS_REPEATED')

    def test_17_stale_recognition_hash(self):
        r=seed();b=enc(r);rec=f.evaluate_image(b)['recognition']
        tampered=copy.deepcopy(rec);tampered['image_sha256']='0'*64
        self.actual(r,'UNKNOWN',expected_reason='RECOGNITION_IMAGE_OR_CONTENT_MISMATCH',override=tampered)

    def test_18_forged_recognition_root_count(self):
        r=seed(parents=True);rec=f.evaluate_image(enc(r))['recognition']
        tampered=copy.deepcopy(rec);tampered['declared_root_count']=2
        self.actual(r,'UNKNOWN',expected_reason='RECOGNITION_IMAGE_OR_CONTENT_MISMATCH',override=tampered)

    def test_19_forged_root_set(self):
        r=seed(parents=True);rec=f.evaluate_image(enc(r))['recognition']
        tampered=copy.deepcopy(rec);tampered['root_sets']['R2']=['ROOT_B']
        self.actual(r,'UNKNOWN',expected_reason='RECOGNITION_IMAGE_OR_CONTENT_MISMATCH',override=tampered)

    def test_20_correct_receipt(self):
        r=seed();rec=f.evaluate_image(enc(r))['recognition']
        self.actual(r,'DECLARED_ROOT_PARTITION_ONLY',2,override=rec)

    def test_21_image_changed_with_old_receipt(self):
        r=seed();rec=f.evaluate_image(enc(r))['recognition']
        r['receipts'][0]['id']='X';r['lineage'][0]['receipt_id']='X'
        self.actual(r,'UNKNOWN',expected_reason='RECOGNITION_IMAGE_OR_CONTENT_MISMATCH',override=rec)

    def test_22_w9_conflicting_sources(self):
        r=seed();r['receipts'][1]=w9.receipt(False,id='R2')
        self.actual(r,'UNKNOWN',expected_reason='W9_DECLARED_CONFLICT')

    def test_23_w9_contradictory_source(self):
        r=seed(ids=('R1',));r['receipts'][0]=w9.receipt(False,id='R1')
        self.actual(r,'UNKNOWN',expected_reason='W9_DECLARED_CONTRADICTION')

    def test_24_w9_cross_target(self):
        r=seed();r['receipts'][1]=w9.receipt(target='OTHER',id='R2')
        self.actual(r,'UNKNOWN',expected_reason='W9_UNKNOWN')

    def test_25_w9_bad_hash(self):
        r=seed();r['receipts'][1]['stdout_sha256']='f'*64
        self.actual(r,'UNKNOWN',expected_reason='W9_UNKNOWN')

    def test_26_duplicate_json_key(self):
        raw=b'{"schema":"bad","schema":"again","claim":{},"receipts":[],"lineage":[]}'
        self.actual(raw,'UNKNOWN',expected_reason='INVALID_JSON_OR_UNICODE')

    def test_27_depth_limit(self):
        self.actual(b'['*18+b'0'+b']'*18,'UNKNOWN',expected_reason='JSON_DEPTH_LIMIT')

    def test_28_byte_limit(self):
        self.actual(b'x'*(f.MAX_BYTES+1),'UNKNOWN',expected_reason='IMAGE_TYPE_OR_BYTE_LIMIT')

    def test_29_missing_fields(self):
        r=seed();r.pop('claim')
        self.actual(r,'UNKNOWN',expected_reason='IMAGE_SCHEMA')

    def test_30_unicode_surrogate(self):
        r=seed();r['receipts'][0]['stdout']='\ud800'
        raw=json.dumps(r).encode('utf-8')
        self.actual(raw,'UNKNOWN',expected_reason='INVALID_UNICODE_SCALAR')

    def test_31_float_excluded(self):
        raw=enc(seed()).replace(b'"schema":"'+f.SCHEMA.encode()+b'"', b'"schema":"'+f.SCHEMA.encode()+b'","extra":1.2')
        self.actual(raw,'UNKNOWN',expected_reason='INVALID_JSON_OR_UNICODE')

    def test_32_receipt_nine(self):
        r=seed(ids=tuple('R'+str(i) for i in range(9)))
        self.actual(r,'UNKNOWN',expected_reason='RECEIPT_COUNT')

    def test_33_original_w9_blob(self):
        raw=Path(f.__file__).with_name('w9_bounded_receipt_contract.py').read_bytes()
        git_hash=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        self.assertEqual(git_hash,f.W9_BLOB_SHA1)

    def test_34_unmodified_source_img_no_write(self):
        r=seed();image=enc(r);before=image[:]
        x=f.evaluate_image(image)
        self.assertEqual(image,before)
        self.assertEqual(x['final']['status'],'DECLARED_ROOT_PARTITION_ONLY')

    def test_35_image_reorder_immutability(self):
        r=seed();image=enc(r);rec=f.evaluate_image(image)['recognition']
        r['lineage'].reverse()
        x=f.evaluate_image(enc(r), recognition_override=rec)
        self.assertEqual(x['final']['status'],'UNKNOWN')
        self.assertEqual(x['final']['reason'],'RECOGNITION_IMAGE_OR_CONTENT_MISMATCH')

    def test_36_bad_image_datatype(self):
        self.assert_gate(f.evaluate_image('notbytes'))
        self.assertEqual(f.evaluate_image('notbytes')['final']['status'],'UNKNOWN')

    def test_37_nonnested_json_quotes(self):
        r=seed();r['receipts'][0]['stdout']=w9.receipt(id='R1')['stdout']
        self.actual(r,'DECLARED_ROOT_PARTITION_ONLY',2)

    def test_38_bad_w9_claim(self):
        r=seed();r['claim']['predicate']='WORLD_TRUTH'
        self.actual(r,'UNKNOWN',expected_reason='W9_UNKNOWN')

    def test_39_unverified_distinct_roots_still_unknown(self):
        r=seed();x=self.actual(r,'DECLARED_ROOT_PARTITION_ONLY',2)
        self.assertEqual(x['independent_corroboration'],'UNKNOWN')

    def test_41_public_two_stage_api_same_image(self):
        obj=seed(parents=True)
        raw=enc(obj)
        recognition=f.recognize_image(raw)
        self.assertEqual(recognition['status'],'DECLARED_LINEAGE_RESOLVED')
        self.assertEqual(recognition['declared_root_count'],1)
        final=f.adjudicate_image(raw, recognition)
        self.assert_gate(final)
        self.assertEqual(final['final']['status'],'DECLARED_ROOT_PARTITION_ONLY')
        self.assertEqual(final['final']['declared_root_count'],1)

    def test_42_public_two_stage_api_mismatched_image(self):
        a=seed(parents=True)
        recognition=f.recognize_image(enc(a))
        b=seed()
        actual=f.adjudicate_image(enc(b),recognition)
        self.assert_gate(actual)
        self.assertEqual(actual['final']['status'],'UNKNOWN')
        self.assertEqual(actual['final']['reason'],'RECOGNITION_IMAGE_OR_CONTENT_MISMATCH')

    def test_40_origin_relabel_count_inflation_toy(self):
        base=seed(parents=True)
        n=seed(ids=('R1','R2','R3','R4'))
        n['lineage']=[{'receipt_id':'R1','root_id':'ROOT_A','parents':[]}]+[
            {'receipt_id':x,'root_id':None,'parents':['R1']} for x in ('R2','R3','R4')]
        x=self.actual(base,'DECLARED_ROOT_PARTITION_ONLY',1)
        y=self.actual(n,'DECLARED_ROOT_PARTITION_ONLY',1)
        self.assertEqual(y['final']['illustrative_occurrence_count'],4)
        self.assertEqual(x['final']['illustrative_occurrence_count'],2)

if __name__ == '__main__':
    unittest.main(verbosity=2)
