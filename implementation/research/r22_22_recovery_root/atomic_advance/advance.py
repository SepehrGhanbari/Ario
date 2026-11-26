"""Disposable exact-evidence CAS transition. No live authority or new ledger."""
import base64, fcntl, hashlib, json, os, subprocess, sys, tempfile, zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
CUSTODIAN=65533
PUBLISHER=65534
FIRST='2bedc6d0cc85857cfaed3ceafeb5d7700d78923057e661d9c5675d6925e6262b'
SECOND='717fbcf540cba37e7d5c6c83f3740fe301ece42fdc983fe4e9af484a37d56d27'
OLD='d68d83b0418e77937794a7f57fa178177da8dcb5cb473b2379cebcd448e8e51e'
NEW='2f4dc31993e113e884ebdc0befd6b7e7a21b28282093b32e35f68531bcf0faa0'
PREFIX='ARIO R22.20 public synthetic floor (no personal data): '
def sha(b): return hashlib.sha256(b).hexdigest()
def evidence(path,pin):
    raw=path.read_bytes()
    if sha(raw)!=pin: raise ValueError('archive pin')
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None: raise ValueError('archive CRC')
        e=json.loads(z.read('event.json'))
        if not e['content'].startswith(PREFIX): raise ValueError('event profile')
        env,ledger=map(lambda x:base64.b64decode(x,validate=True),e['content'][len(PREFIX):].split('.'))
        return json.loads(env),env,ledger

def exact_transition(a,b):
    x,xraw,old=evidence(a,FIRST); y,_,new=evidence(b,SECOND)
    if not (x['seq']==6 and y['seq']==8 and x['scope']==y['scope'] and sha(old)==OLD and sha(new)==NEW and y['previous_ledger_sha256']==OLD and y['previous_checksum']==sha(hashlib.sha256(xraw).digest()) and new.startswith(old) and len(old.splitlines())==6 and len(new.splitlines())==8): raise ValueError('transition')
    for v in (x,y):
        if v['synthetic'] is not True or v['authoritative'] is not False or v['trust_activation']!='NO_GO' or v['production']!='NO_GO': raise ValueError('boundary')
    return old,new

def advance(root,expected,a,b,crash='none'):
    if os.getuid()!=CUSTODIAN: return 'HOLD_WRONG_UID'
    try:
        old,new=exact_transition(a,b)
        with (root/'lock').open('r+b') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            current=(root/'floor').read_bytes()
            if current not in (old,new): return 'HOLD_INVALID_FLOOR'
            if sha(current)!=expected: return 'HOLD_CAS_MISMATCH'
            if current==new: return 'HOLD_ALREADY_RETAINED'
            temp=root/'pending'
            with temp.open('wb') as f:
                f.write(new); f.flush(); os.fsync(f.fileno())
            if crash=='before': os._exit(75)
            os.replace(temp,root/'floor')
            fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
            try: os.fsync(fd)
            finally: os.close(fd)
            if crash=='after': os._exit(76)
            return 'ADVANCED_RESEARCH_ONLY'
    except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile): return 'HOLD_EVIDENCE_OR_STORE'

def exercise(a,b):
    assert os.geteuid()==0
    old,new=exact_transition(a,b)
    with tempfile.TemporaryDirectory(prefix='r22-22f-') as td:
        root=Path(td);root.chmod(0o755);box=root/'custodian';box.mkdir();os.chown(box,CUSTODIAN,CUSTODIAN);box.chmod(0o700)
        for path,name in ((a,'a.zip'),(b,'b.zip'),(Path(__file__),'advance.py')):
            p=root/name;p.write_bytes(path.read_bytes());p.chmod(0o444)
        bad=root/'bad.zip';bad.write_bytes(b.read_bytes()+b'!');bad.chmod(0o444)
        floor=box/'floor';lock=box/'lock'
        for p,data in ((floor,old),(lock,b'')):
            p.write_bytes(data);os.chown(p,CUSTODIAN,CUSTODIAN);p.chmod(0o600)
        def reset(data):
            floor.write_bytes(data);os.chown(floor,CUSTODIAN,CUSTODIAN);floor.chmod(0o600)
        def run(args,uid):
            return subprocess.run(args,user=uid,group=uid,extra_groups=[],cwd=root,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},capture_output=True,text=True,timeout=30)
        def call(expected=OLD,second='b.zip',crash='none',uid=CUSTODIAN):
            p=run([sys.executable,'-I',str(root/'advance.py'),'advance',str(box),expected,str(root/'a.zip'),str(root/second),crash],uid)
            if p.returncode not in (0,75,76): raise AssertionError(p.stderr)
            return p.stdout.strip() if p.returncode==0 else p.returncode
        count=0
        def check(name,got,want):
            nonlocal count
            if got!=want: raise AssertionError((name,got,want))
            count+=1; print(name,got,'PASS',flush=True)
        check('01_publisher_call',call(uid=PUBLISHER),'HOLD_WRONG_UID')
        for name,code in [('02_publisher_read','p.read_bytes()'),('03_publisher_write','p.write_bytes(b"bad")'),('04_publisher_delete','p.unlink()')]:
            p=run([sys.executable,'-c','from pathlib import Path; import sys; p=Path(sys.argv[1]); '+code,str(floor)],PUBLISHER)
            check(name,p.returncode!=0 and 'PermissionError' in p.stderr,True)
        check('05_wrong_expected',call('0'*64),'HOLD_CAS_MISMATCH')
        check('06_mutated_evidence',call(second='bad.zip'),'HOLD_EVIDENCE_OR_STORE')
        check('07_old_as_successor',call(second='a.zip'),'HOLD_EVIDENCE_OR_STORE')
        check('08_crash_before_replace',call(crash='before'),75);assert floor.read_bytes()==old
        check('09_retry_after_before',call(),'ADVANCED_RESEARCH_ONLY');assert floor.read_bytes()==new
        check('10_stale_cas_replay',call(),'HOLD_CAS_MISMATCH')
        check('11_same_state_retry',call(NEW),'HOLD_ALREADY_RETAINED')
        check('12_no_evidence_for_seq10',call(NEW,'missing.zip'),'HOLD_EVIDENCE_OR_STORE')
        reset(old);check('13_crash_after_replace',call(crash='after'),76);assert floor.read_bytes()==new
        check('14_retry_after_commit',call(NEW),'HOLD_ALREADY_RETAINED')
        reset(old)
        with ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(lambda _:call(),range(8)))
        check('15_concurrent_one_advance',results.count('ADVANCED_RESEARCH_ONLY'),1)
        check('16_concurrent_seven_hold',results.count('HOLD_CAS_MISMATCH'),7);assert floor.read_bytes()==new
        floor.unlink();check('17_missing_floor',call(),'HOLD_EVIDENCE_OR_STORE');assert not floor.exists()
        reset(b'bad');check('18_corrupt_floor',call(),'HOLD_INVALID_FLOOR')
        reset(old);check('19_common_root_rollback_RED',call(),'ADVANCED_RESEARCH_ONLY');assert floor.read_bytes()==new
        print(f'{count}/{count} EXPECTED CONTROLS PASS; COMMON_ROOT_ROLLBACK=RED; SEQ10=UNKNOWN; TRUST=NO_GO; PRODUCTION=NO_GO')
if __name__=='__main__':
    if sys.argv[1]=='test': exercise(*map(Path,sys.argv[2:]))
    elif sys.argv[1]=='advance':
        root,expected,a,b,crash=sys.argv[2:];print(advance(Path(root),expected,Path(a),Path(b),crash))
