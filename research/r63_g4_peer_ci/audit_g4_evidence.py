"""R63 G4 offline raw evidence auditor (does NOT execute archived code)."""
from __future__ import annotations
import hashlib,json,re,sys,zipfile
from pathlib import Path

REQUIRED={'report-before-cleanup.json','server-peer-log.txt','v1.jsonl','v2.jsonl'}
PIN='c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd'
DOMAIN=b'ARIO-R63/spend/v2\0'
V='ARIO_R63_SPEND_V2_RESEARCH'
ZERO='0'*64

def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def check(cond,msg):
    if not cond:raise ValueError(msg)
def v2review(raw):
    check(raw.endswith(b'\n') and raw, 'V2_NOT_TERMINATED')
    prev=ZERO;pairs=[]
    for i,line in enumerate(raw.splitlines(),1):
        obj=json.loads(line)
        check(canonical(obj)==line,'V2_NONCANONICAL')
        check(set(obj)=={'version','seq','prev','nonce','id','before','after','hash'},'V2_EXTRA_FIELDS')
        check(obj['version']==V and type(obj['seq']) is int and obj['seq']==i and obj['prev']==prev,'V2_SEQUENCE')
        n,k=obj['nonce'],obj['id']
        check(all(re.fullmatch('[0-9a-f]{64}',e) for e in (n,k)), 'V2_INVALID_IDS')
        check(not any(n==a or k==b for a,b in pairs),'V2_DUPLICATE')
        before=sha(canonical(sorted([list(e) for e in pairs],key=lambda e:e[0])))
        after=sha(canonical(sorted([list(e) for e in pairs+[(n,k)]],key=lambda e:e[0])))
        check(obj['before']==before and obj['after']==after, 'V2_R60_COMMITMENT')
        check(obj['hash']==sha(DOMAIN+canonical({key:val for key,val in obj.items() if key!='hash'})), 'V2_BAD_EVENT_HASH')
        pairs.append((n,k));prev=obj['hash']
    return {'seq':len(pairs),'head':prev,'pairs':pairs}

def audit(path):
    with zipfile.ZipFile(path) as z:
        check(z.testzip() is None,'ZIP_CRC_ERROR')
        names=z.namelist()
        check(len(names)==len(set(names)),'DUPLICATE_ZIP_NAME')
        check(set(names)==REQUIRED|{'SHA256SUMS.txt'},'EVIDENCE_MISSING_OR_UNEXPECTED_MEMBER')
        hashes=z.read('SHA256SUMS.txt').decode('ascii').splitlines()
        expected={}
        for line in hashes:
            check(re.fullmatch('[0-9a-f]{64}  [a-z0-9.-]+',line) is not None,'SHA_MANIFEST_BAD_FORMAT')
            digest,name=line.split('  ')
            check(name not in expected,'SHA_DUPLICATE')
            expected[name]=digest
        check(set(expected)==REQUIRED,'SHA_MANIFEST_NOT_EXHAUSTIVE')
        raw={name:z.read(name) for name in REQUIRED}
        for name,b in raw.items():check(sha(b)==expected[name],'SHA_CONTENT_MISMATCH_'+name)
    report=json.loads(raw['report-before-cleanup.json'])
    check(report['source_sha256']['frozen_v9_v2']==PIN,'FROZEN_PIN_MISMATCH')
    check(report['result']=='PASS_SYNTHETIC_PEER_SID','GUEST_REPORTED_HOLD')
    check(report['real_v9']=='NOT_EXECUTED' and report['signer']=='NOT_EXECUTED','REAL_SIGNER_SCOPE_MISMATCH')
    c=report['client_replies'];sid=report['allowed_peer_sid'];rogue=report['rogue_peer_sid']
    check(c['positive']==sid+'|RESERVED_ONLY_NO_SIGN','AUTHORIZED_RESPONSE_MISMATCH')
    check(c['duplicate']==sid+'|ALREADY_RESERVED_NO_APPEND','DUPLICATE_RESPONSE_MISMATCH')
    check(c['rogue_claimed_reader']==rogue+'|HOLD_PEER_IDENTITY','ROGUE_NOT_DENIED')
    check(c['admin_claimed_reader'].endswith('|HOLD_PEER_IDENTITY'),'ADMIN_NOT_DENIED')
    check(report['direct_probe']['results']['append_v1.jsonl']=='ACCESS_DENIED' and report['direct_probe']['results']['append_v2.jsonl']=='ACCESS_DENIED','READER_DIRECT_WRITE_DENIAL_MISSING')
    v2=v2review(raw['v2.jsonl'])
    expv1=b''.join(canonical([n,k])+b'\n' for n,k in v2['pairs'])
    check(expv1==raw['v1.jsonl'],'V1_V2_DIVERGENCE')
    check(v2['seq']==3,'EXPECTED_THREE_EVENTS')
    check(report['journal']['coherent'] and report['journal']['v2_events']==3 and report['journal']['v1_rows']==3,'REPORT_COUNTS_MISMATCH')
    check(report['journal']['head']==v2['head'] and report['journal']['v1_sha256']==sha(raw['v1.jsonl']) and report['journal']['v2_sha256']==sha(raw['v2.jsonl']),'REPORT_JOURNAL_RAW_BYTES_MISMATCH')
    slog=raw['server-peer-log.txt'].decode('utf-8').splitlines()
    check('ALLOW_COUNT=2' in slog and 'DENY_COUNT=2' in slog,'SERVER_EVENT_COUNTS')
    check('CLIENT_2_SID='+rogue in slog,'SERVER_ROGUE_SID_NOT_OBSERVED')
    check('CLIENT_3_SID='+c['admin_claimed_reader'].split('|')[0] in slog,'SERVER_ADMIN_SID_NOT_OBSERVED')
    return {'verdict':'G4_LOCAL_RAW_BYTES_AUDIT_PASS','evidence_sha256':sha(Path(path).read_bytes()),'v2_seq':v2['seq'],'v2_head':v2['head'],'reported_authorized_requests':2,'reported_rejected_requests':2,'actual_external_custody':'NOT_ESTABLISHED','native_v9_signer':'NOT_EXECUTED','note':'OS SID evidence remains guest/CI-reported; no independent OS attestation'}
if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('USAGE: audit_g4_evidence.py evidence.zip')
    print(json.dumps(audit(Path(sys.argv[1])),indent=2))
