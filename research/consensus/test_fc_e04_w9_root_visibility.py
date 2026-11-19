#!/usr/bin/env python3
"""FC-E04: source-pinned W9 root-visibility probe; research-only, no I/O writes.

The primitive-root oracle is a fixture outside W9, NOT independent custody.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'w9_bounded_receipt_contract.py'
EXPECTED_BLOB = 'f795065ce06d88c2ca017270f5036eb028029220'
raw = SOURCE.read_bytes()
blob = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
assert blob == EXPECTED_BLOB, ('SOURCE_NOT_PINNED', blob)
sys.path.insert(0, str(ROOT))
import w9_bounded_receipt_contract as w

out=[]
def probe(id, receipts, expected, roots=None):
    actual=w.evaluate(w.claim(),receipts)
    assert actual['declared_relation']==expected,(id,actual)
    assert (actual['execution_authenticity'],actual['source_custody'],actual['assessment'],
            actual['world_truth'],actual['action_authority'],actual['memory_admitted']) == (
            'UNKNOWN','NOT_ESTABLISHED','NOT_ASSESSED','UNKNOWN','NONE',False),(id,actual)
    out.append({'id':id,'receipt_count':len(receipts),
                'fixture_roots':len(set(roots)) if roots else None,
                'relation':actual['declared_relation'],'reason':actual['reason']})

a,b=w.receipt(id='R1'),w.receipt(id='R2')
probe('01_one_report',[a],'DECLARED_MATCH',['root-A'])
probe('02_replicated_root',[a,b],'DECLARED_MATCH',['root-A','root-A'])
probe('03_distinct_roots',[a,b],'DECLARED_MATCH',['root-A','root-B'])
probe('04_unavailable_lineage',[a,b],'DECLARED_MATCH')
probe('05_eight_relabels',[w.receipt(id=f'R{i}') for i in range(8)],'DECLARED_MATCH',['root-A']*8)
probe('06_four_reports_two_roots',[w.receipt(id=f'R{i}') for i in range(4)],'DECLARED_MATCH',['root-A','root-A','root-B','root-B'])
probe('07_duplicate_id',[a,a],'UNKNOWN',['root-A','root-A'])
probe('08_over_count',[w.receipt(id=f'R{i}') for i in range(9)],'UNKNOWN',['root-A']*9)
probe('09_conflict',[a,w.receipt(False,id='R2')],'DECLARED_CONFLICT',['root-A','root-B'])
probe('10_contradiction',[w.receipt(False,id='R2')],'DECLARED_CONTRADICTION',['root-A'])
probe('11_cross_target',[a,w.receipt(id='R2',target='B')],'UNKNOWN',['root-A','root-B'])
probe('12_new_root_field',[a,{**b,'primitive_root':'root-A'}],'UNKNOWN',['root-A','root-A'])
probe('13_new_lineage_field',[a,{**b,'derived_from':'R1'}],'UNKNOWN',['root-A','root-A'])
probe('14_relabel_same_bytes',[w.receipt(id=f'R{i}') for i in range(4)],'DECLARED_MATCH',['root-A']*4)
probe('15_bad_self_hash',[a,{**b,'stdout_sha256':'f'*64}],'UNKNOWN',['root-A','root-B'])
probe('16_empty',[],'UNKNOWN')
assert out[1]['relation']==out[2]['relation']==out[3]['relation']=='DECLARED_MATCH'
assert out[1]['fixture_roots']==1 and out[2]['fixture_roots']==2
print(json.dumps({'schema':'ARIO-FC-E04-W9-ROOT-VISIBILITY-v0.1',
                  'pin':EXPECTED_BLOB,'count':len(out),'controls':out,
                  'conclusion':'W9 root-provenance input not supported; no independent evidence verdict claimed',
                  'fc_e04_full_e2e':'NOT_RUN_MISSING_RECOGNITION_ADJUDICATION_INTERFACE',
                  'source_custody':'NOT_ESTABLISHED','authority':'NONE'},
                 indent=2,sort_keys=True))
