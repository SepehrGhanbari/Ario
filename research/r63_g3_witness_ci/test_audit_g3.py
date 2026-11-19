"""Offline G3 audit positive/negative fixture tests. Not native Windows evidence."""
from pathlib import Path
import json
import tempfile
import unittest
import zipfile
import spend_chain_v2 as v2
import audit_g3 as auditor

W='S-1-5-21-123-456-789-1000'
R='S-1-5-21-123-456-789-1001'
BASE=[('a'*64,'1'*64),('b'*64,'2'*64)]

def raw(rows):
    journal=b''
    for n,i in rows:
        journal,r=v2.append(journal,n,i)
        if r!='NEW_NEEDS_DURABLE_APPEND':raise RuntimeError(r)
    return journal

def add_snapshot(body,name,rows_v1,rows_v2,phase=None):
    base=name+'/'
    r1=b''.join(v2.canonical(list(pair))+b'\n' for pair in rows_v1)
    r2=raw(rows_v2)
    flag=('SYNTHETIC_CRASH_WINDOW='+phase+'\n').encode() if phase else None
    body[base+'v1.jsonl']=r1
    body[base+'v2.jsonl']=r2
    body[base+'writer-identity.json']=json.dumps({'sid':W,'pid':300}).encode()
    body[base+'inspect.json']=json.dumps(auditor.inspect(r1,r2,flag)).encode()
    if flag:body[base+'uncertain.flag']=flag
    return auditor.inspect(r1,r2,flag)

def fake():
    body={}
    more=[('c'*64,'3'*64),('d'*64,'4'*64),('e'*64,'5'*64)]
    ns=add_snapshot(body,'normal',BASE+more,BASE+more)
    d4={x:'ACCESS_DENIED' for x in ('append_v1','append_v2','overwrite_v1','create_sibling')}
    d5={**d4,'delete_flag':'ACCESS_DENIED'}
    report={'scope':'RESEARCH_ONLY_SYNTHETIC_G3','status':'PASS_SYNTHETIC_G3_ONLY',
            'writer_sid':W,'reader_sid':R,'results':{}}
    report['results']['normal']={'batches':[
        {'count':n,'token':{'sid':R},'replies':['RESERVED_ONLY_NO_SIGN']+['ALREADY_RESERVED_NO_APPEND']*(n-1)}
        for n in (2,8,16)],'direct':{'token':{'sid':R},'denials':d4},
        'direct_live':{'token':{'sid':R},'denials':d4},
        'snapshot':ns,'writer':{'sid':W,'pid':300}}
    for index,phase in enumerate(('pre_v2','post_v2','post_v1')):
        extra=[('f'*64,'6'*64)]
        rv1=BASE+(extra if phase=='post_v1' else [])
        rv2=BASE+(extra if phase!='pre_v2' else [])
        snap1=add_snapshot(body,phase+'-after-crash',rv1,rv2,phase)
        snap2=add_snapshot(body,phase+'-after-recovery',rv1,rv2,phase)
        for base,pid in ((phase+'-after-crash',300+index),(phase+'-after-recovery',400+index)):
            body[base+'/writer-identity.json']=json.dumps({'sid':W,'pid':pid}).encode()
        report['results'][phase]={'parent_exit':73,'parent_pid':300+index,
          'recovery_pid':400+index,'first_response':'NO_ACK','replay_response':'HOLD_UNCERTAIN',
          'after_crash':snap1,'after_recovery':snap2,
          'restricted_direct':{'token':{'sid':R},'denials':d5},
          'recovery_writer':{'sid':W}}
    body['report.json']=json.dumps(report).encode()
    return body

def build(path,body):
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(body.items()):z.writestr(name,data)
        z.writestr('SHA256SUMS.txt',''.join(auditor.sha(data)+'  '+name+'\n'
                  for name,data in sorted(body.items())))

class TestAudit(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'evidence.zip'
        self.body=fake()
        build(self.path,self.body)

    def test_valid_complete_synthetic(self):
        self.assertEqual(auditor.audit(self.path)['verdict'],'PASS_INTERNAL_BYTES_ONLY')

    def test_missing_flag_fails(self):
        self.body.pop('post_v1-after-recovery/uncertain.flag')
        build(self.path,self.body)
        with self.assertRaises((AssertionError,KeyError)):auditor.audit(self.path)

    def test_v2_mutation_fails_even_with_new_manifest(self):
        key='post_v2-after-crash/v2.jsonl'
        self.body[key]=self.body[key][:-2]+b'X\n'
        build(self.path,self.body)
        with self.assertRaises((AssertionError,ValueError)):auditor.audit(self.path)

    def test_v1_mutation_fails_even_with_new_manifest(self):
        key='normal/v1.jsonl';self.body[key]=self.body[key][:-3]+b'BAD'
        build(self.path,self.body)
        with self.assertRaises((AssertionError,ValueError)):auditor.audit(self.path)

    def test_observer_mutation_fails_even_with_new_manifest(self):
        key='pre_v2-after-crash/inspect.json'
        obj=json.loads(self.body[key]);obj['v1_sha256']='0'*64
        self.body[key]=json.dumps(obj).encode()
        build(self.path,self.body)
        with self.assertRaises(AssertionError):auditor.audit(self.path)

    def test_unchanged_manifest_detects_tampering(self):
        with zipfile.ZipFile(self.path,'a') as z:
            z.writestr('random-extra.bin',b'UNEXPECTED')
        with self.assertRaises(AssertionError):auditor.audit(self.path)

    def test_matching_parent_reader_sid_is_rejected(self):
        obj=json.loads(self.body['report.json']);obj['reader_sid']=obj['writer_sid']
        self.body['report.json']=json.dumps(obj).encode()
        build(self.path,self.body)
        with self.assertRaises(AssertionError):auditor.audit(self.path)

if __name__=='__main__':unittest.main(verbosity=2)
