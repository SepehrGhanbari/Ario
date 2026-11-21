"""G4 archive positive & tamper-negative controls, pure Python, no OS accounts."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile,unittest,zipfile
from audit_g4_evidence import audit,canonical,sha,DOMAIN,V,ZERO
from pack_g4_evidence import pack

SID='S-1-5-21-123-234-345-1000'
ROGUE='S-1-5-21-123-234-345-1001'
ADMIN='S-1-5-21-123-234-345-500'
PIN='c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd'

def state():
    raw=b'';prev=ZERO;before=[]
    for i,(n,k) in enumerate((('a'*64,'1'*64),('b'*64,'2'*64),('c'*64,'3'*64)),1):
        body={'version':V,'seq':i,'prev':prev,'nonce':n,'id':k,
            'before':sha(canonical(sorted([list(e) for e in before],key=lambda e:e[0]))),
            'after':sha(canonical(sorted([list(e) for e in before+[(n,k)]],key=lambda e:e[0])))}
        h=sha(DOMAIN+canonical(body));prev=h
        raw+=canonical({**body,'hash':h})+b'\n';before.append((n,k))
    v1=b''.join(canonical(list(pair))+b'\n' for pair in before)
    return v1,raw,prev

def report():
    a,b,head=state()
    return {'source_sha256':{'frozen_v9_v2':PIN},'result':'PASS_SYNTHETIC_PEER_SID','real_v9':'NOT_EXECUTED','signer':'NOT_EXECUTED',
        'allowed_peer_sid':SID,'rogue_peer_sid':ROGUE,
        'client_replies':{'positive':SID+'|RESERVED_ONLY_NO_SIGN','duplicate':SID+'|ALREADY_RESERVED_NO_APPEND',
                          'rogue_claimed_reader':ROGUE+'|HOLD_PEER_IDENTITY','admin_claimed_reader':ADMIN+'|HOLD_PEER_IDENTITY'},
        'journal':{'coherent':True,'v2_events':3,'v1_rows':3,'head':head,'v1_sha256':sha(a),'v2_sha256':sha(b)},
        'direct_probe':{'results':{'append_v1.jsonl':'ACCESS_DENIED','append_v2.jsonl':'ACCESS_DENIED'}}}

class Checks(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.dir=Path(tmp.name);self.src=self.dir/'src';self.src.mkdir();self.z=self.dir/'evidence.zip'
        a,b,_=state();
        (self.src/'v1.jsonl').write_bytes(a)
        (self.src/'v2.jsonl').write_bytes(b)
        (self.src/'report-before-cleanup.json').write_text(json.dumps(report()))
        (self.src/'server-peer-log.txt').write_text('ALLOW_COUNT=2\nDENY_COUNT=2\nCLIENT_2_SID='+ROGUE+'\nCLIENT_3_SID='+ADMIN+'\n')
        pack(self.src,self.z)
    def change(self,name,data,fix_manifest=False):
        with zipfile.ZipFile(self.z) as z:r={n:z.read(n) for n in z.namelist()}
        r[name]=data
        if fix_manifest:
            r['SHA256SUMS.txt']=''.join(f'{sha(r[n])}  {n}\n' for n in sorted(r) if n!='SHA256SUMS.txt').encode()
        with zipfile.ZipFile(self.z,'w') as z:
            for k,v in r.items():z.writestr(k,v)
    def failure(self):
        with self.assertRaises(ValueError):audit(self.z)
    def test_healthy(self):self.assertEqual(audit(self.z)['v2_seq'],3)
    def test_bad_hash(self):self.change('v1.jsonl',b'evil');self.failure()
    def test_bad_manifest_rebuilt_chain(self):self.change('v2.jsonl',b'FAKE\n',fix_manifest=True);self.failure()
    def test_forged_authorized_response(self):
        r=report();r['client_replies']['rogue_claimed_reader']=SID+'|RESERVED_ONLY_NO_SIGN'
        self.change('report-before-cleanup.json',json.dumps(r).encode(),True);self.failure()
    def test_wrong_authority_sid(self):
        r=report();r['allowed_peer_sid']=ROGUE
        self.change('report-before-cleanup.json',json.dumps(r).encode(),True);self.failure()
    def test_invalid_server_log(self):
        self.change('server-peer-log.txt',b'ALLOW_COUNT=3\nDENY_COUNT=1\n',True);self.failure()
    def test_missing_file(self):
        with zipfile.ZipFile(self.z) as z:r={n:z.read(n) for n in z.namelist() if n!='v2.jsonl'}
        with zipfile.ZipFile(self.z,'w') as z:
            for k,v in r.items():z.writestr(k,v)
        self.failure()
    def test_always_hold_not_valid(self):
        r=report();r['result']='HOLD'
        self.change('report-before-cleanup.json',json.dumps(r).encode(),True);self.failure()
if __name__=='__main__':unittest.main(verbosity=2)
