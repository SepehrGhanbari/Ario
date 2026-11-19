"""Independent *read-only* forensic auditor for synthetic R63 G3 evidence.

Does not import any source from the evidence archive or run guest code.
Its SHA checks are internally self-administered, NOT external attestation.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import PurePosixPath,Path
import sys
import zipfile

DOMAIN=b'ARIO-R63/spend/v2\0'
VERSION='ARIO_R63_SPEND_V2_RESEARCH'
ZERO='0'*64
PHASES={'pre_v2':(2,2,True),'post_v2':(2,3,False),'post_v1':(3,3,True)}

def sha(x):return hashlib.sha256(x).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pairs_sha(p):return sha(canonical(sorted([list(x) for x in p],key=lambda v:v[0])))
def is64(x):return type(x)==str and len(x)==64 and all(c in '0123456789abcdef' for c in x)

def fail(msg):raise AssertionError(msg)

def parse_v2(raw):
    if raw and not raw.endswith(b'\n'):fail('TRUNCATED_V2')
    seq=0;prev=ZERO;pairs=[]
    for line in raw.splitlines():
        obj=json.loads(line)
        if type(obj)!=dict or line!=canonical(obj):fail('NONCANONICAL_V2')
        if set(obj)!={'version','seq','prev','nonce','id','before','after','hash'}:fail('V2_FIELDS')
        if (obj['version']!=VERSION or type(obj['seq'])!=int or obj['seq']!=seq+1 or obj['prev']!=prev
            or not is64(obj['nonce']) or not is64(obj['id']) or not is64(obj['hash'])):
            fail('V2_VERSION_SEQ_OR_SID')
        if any(n==obj['nonce'] or k==obj['id'] for n,k in pairs):fail('DUPLICATE_V2_RESERVATION')
        nextpairs=pairs+[(obj['nonce'],obj['id'])]
        body={k:v for k,v in obj.items() if k!='hash'}
        if obj['before']!=pairs_sha(pairs) or obj['after']!=pairs_sha(nextpairs):fail('V2_R60_SNAPSHOT')
        if obj['hash']!=sha(DOMAIN+canonical(body)):fail('V2_HASH_CHAIN')
        seq=obj['seq'];prev=obj['hash'];pairs=nextpairs
    return seq,prev,pairs

def inspect(raw1,raw2,flag):
    seq,head,pairs=parse_v2(raw2)
    expected=b''.join(canonical(list(x))+b'\n' for x in pairs)
    return {'v1_lines':len(raw1.splitlines()),'v2_events':seq,'v1_sha256':sha(raw1),
            'v2_sha256':sha(raw2),'v2_head':head,'coherent':raw1==expected,
            'flag_present':flag is not None,'flag_sha256':sha(flag) if flag is not None else None,
            'flag_len':len(flag) if flag is not None else None}

def audit(path):
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:fail('ZIP_CRC')
        names=z.namelist()
        if len(names)>80 or sum(info.file_size for info in z.infolist())>4_000_000 or any(info.file_size>1_000_000 for info in z.infolist()):
            fail('OVERSIZE_EVIDENCE_ARCHIVE')
        if len(names)!=len(set(names)) or 'SHA256SUMS.txt' not in names:fail('DUPLICATE_OR_MISSING_MANIFEST')
        for n in names:
            parts=PurePosixPath(n).parts
            if not n or n.startswith('/') or '\\' in n or '..' in parts or ':' in n or n.endswith('/'):
                fail('UNSAFE_ZIP_MEMBER')
        body={n:z.read(n) for n in names if n!='SHA256SUMS.txt'}
        manifest=z.read('SHA256SUMS.txt').decode('utf-8')
        observed={}
        for line in manifest.splitlines():
            if len(line)<67 or line[64:66]!='  ':fail('MALFORMED_MANIFEST')
            h,n=line[:64],line[66:]
            if n in observed or not is64(h):fail('DUPLICATE_MANIFEST')
            observed[n]=h
        if set(observed)!=set(body) or any(sha(body[n])!=h for n,h in observed.items()):fail('MANIFEST_MISMATCH')
        report=json.loads(body['report.json'])
        if report['status']!='PASS_SYNTHETIC_G3_ONLY' or report['scope']!='RESEARCH_ONLY_SYNTHETIC_G3':
            fail('NOT_G3_TEST_REPORT')
        writer_sid=report['writer_sid'];reader_sid=report['reader_sid']
        if writer_sid==reader_sid or not writer_sid.startswith('S-1-5-') or not reader_sid.startswith('S-1-5-'):
            fail('WRONG_SID_DECLARATIONS')
        normal=report['results']['normal']
        if [b['count'] for b in normal['batches']] != [2,8,16]:fail('MISSING_CLIENT_BATCH')
        for b in normal['batches']:
            if b['token']['sid']!=reader_sid or b['replies'].count('RESERVED_ONLY_NO_SIGN')!=1 or \
               b['replies'].count('ALREADY_RESERVED_NO_APPEND')!=b['count']-1:
                fail('MULTIPROCESS_RESPONSES')
        def check(name,stated,expected_seq,expected_v1,coherent,hasflag):
            prefix=name+'/'
            raw1=body[prefix+'v1.jsonl'];raw2=body[prefix+'v2.jsonl']
            flag=body.get(prefix+'uncertain.flag')
            if (flag is not None)!=hasflag:fail('UNCERTAINTY_FLAG_MISSING')
            if flag is not None:
                phase=name.split('-')[0]
                if flag!=('SYNTHETIC_CRASH_WINDOW='+phase+'\n').encode():fail('FLAG_WRONG_BYTES')
            identity=json.loads(body[prefix+'writer-identity.json'])
            if identity['sid']!=writer_sid:fail('WRONG_WRITER_TOKEN')
            snap=json.loads(body[prefix+'inspect.json'])
            actual=inspect(raw1,raw2,flag)
            if actual!=snap or actual!=stated:fail('SAMPLE_MISMATCH')
            if actual['v2_events']!=expected_seq or actual['v1_lines']!=expected_v1 or actual['coherent']!=coherent:
                fail('EXPECTED_STATE_WRONG_'+name)
            return (raw1,raw2,flag)
        check('normal',normal['snapshot'],5,5,True,False)
        if json.loads(body['normal/writer-identity.json'])!=normal['writer']:
            fail('NORMAL_WRITER_IDENTITY_MISMATCH')
        for direct in (normal['direct'], normal['direct_live']):
            if direct['token']['sid']!=reader_sid or len(direct['denials'])!=4 or \
               any(v!='ACCESS_DENIED' for v in direct['denials'].values()):
                fail('NORMAL_DIRECT_DACL')
        for phase,(v1,v2,coherent) in PHASES.items():
            p=report['results'][phase]
            if p['parent_exit']!=73 or p['parent_pid']==p['recovery_pid'] or p['first_response']!='NO_ACK' or \
                p['replay_response']!='HOLD_UNCERTAIN':fail('PARENT_RUN_FIELDS')
            a=check(phase+'-after-crash',p['after_crash'],v2,v1,coherent,True)
            b=check(phase+'-after-recovery',p['after_recovery'],v2,v1,coherent,True)
            if a!=b:fail('RETRY_CHANGED_RAW_JOURNAL_OR_FLAG')
            original_writer=json.loads(body[phase+'-after-crash/writer-identity.json'])
            recovered_writer=json.loads(body[phase+'-after-recovery/writer-identity.json'])
            if original_writer['pid']!=p['parent_pid'] or recovered_writer['pid']!=p['recovery_pid']:
                fail('WRITER_PID_NOT_BOUND_TO_SNAPSHOTS')
            if p['recovery_writer']['sid']!=writer_sid or p['restricted_direct']['token']['sid']!=reader_sid:
                fail('PARENT_READER_IDENTITY')
            if len(p['restricted_direct']['denials'])!=5 or \
               any(x!='ACCESS_DENIED' for x in p['restricted_direct']['denials'].values()):
                fail('RESTRICTED_DIRECT_WRITE')
        expected={'report.json'}
        for base in ['normal']+[p+'-after-'+window for p in PHASES for window in ('crash','recovery')]:
            for name in ('v1.jsonl','v2.jsonl','writer-identity.json','inspect.json'):
                expected.add(base+'/'+name)
            if base!='normal': expected.add(base+'/uncertain.flag')
        if set(body)!=expected:fail('UNEXPECTED_OR_MISSING_EVIDENCE')
    return {'zip_sha256':sha(Path(path).read_bytes()),'entries':len(body),'cases':7,
            'crash_windows':3,'reader_writer_sid_distinct':True,
            'concurrent_readonly_clients':26,
            'direct_denied_reported':8+3*5,
            'independent_custody':'NOT_ESTABLISHED',
            'native_v9':'NOT_EXECUTED','verdict':'PASS_INTERNAL_BYTES_ONLY'}

def selftest():
    import tempfile
    import zipfile
    with tempfile.TemporaryDirectory(prefix='g3_audit_') as tmp:
        q=Path(tmp)/'test.zip'
        with zipfile.ZipFile(q,'w') as z:
            z.writestr('report.json','{}')
            z.writestr('SHA256SUMS.txt',sha(b'{}')+'  report.json\n')
        try:audit(q)
        except (KeyError,AssertionError):pass
        else:raise RuntimeError('AUDITOR_FALSE_POSITIVE_ON_INCOMPLETE_BUNDLE')
    print('AUDITOR_INCOMPLETE_ARCHIVE_REJECTION=PASS')

if __name__=='__main__':
    if len(sys.argv)==2 and sys.argv[1]=='--self-test':selftest()
    elif len(sys.argv)==2:
        print(json.dumps(audit(Path(sys.argv[1])),indent=2,sort_keys=True))
    else:raise SystemExit('usage: audit_g3.py EVIDENCE.zip | --self-test')
