"""Bounded generic successor validation, no operational admission or writes to a floor."""
import hashlib,io,json,os,stat,subprocess,sys,tempfile,zipfile
from pathlib import Path
import event_codec as f
FIRST='2bedc6d0cc85857cfaed3ceafeb5d7700d78923057e661d9c5675d6925e6262b'
PUB='34cd87aa0e4513878e2d9b740bfed3fe255b082dd739b266f9c7c702b784f358'
NOSTR='fdd57657663f0c55d3e7616fcff642fbda2c7f48645849d7b6af3f3ceca96ccb'
POLICY='sigsum-test1-2025'

def read_once(path,limit):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode): raise ValueError('not regular')
        raw=stream.read(limit+1)
    if not 0<len(raw)<=limit: raise ValueError('file bounds')
    return raw

def bundle(path,old=False):
    raw=read_once(path,262144)
    if old and f.sha(raw)!=FIRST: raise ValueError('anchor archive pin')
    stem='historical-first' if old else 'historical-second'
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or len(names)>32: raise ValueError('archive schema')
        def get(name,limit):
            info=z.getinfo(name)
            if not 0<info.file_size<=limit: raise ValueError('member bounds')
            return z.read(info)
        event=get(stem+'.json',131072); proof=get(stem+'.proof',16384)
        key=get('historical-log.pub',256) if old else None
    return event,proof,key

def link(old_raw,new_raw,pub):
    a=f.parse_json(old_raw,131072); b=f.parse_json(new_raw,131072)
    ar,x,al,_=f.verify_event(a,pub); br,y,bl,_=f.verify_event(b,pub)
    if not (y['seq']>x['seq'] and y['scope']==x['scope'] and y['prior_checkpoint_sha256']==x['prior_checkpoint_sha256'] and y['prior_ledger_sha256']==x['prior_ledger_sha256'] and y['previous_event_id']==a['id'] and y['previous_checksum']==f.checksum(ar) and y['previous_ledger_sha256']==f.sha(al) and len(bl)>len(al) and bl.startswith(al)):
        raise ValueError('HOLD_PREDECESSOR_OR_PREFIX')
    return a,b,x,y,bl

def coordinates(proof):
    d={}
    for line in proof.decode('ascii').splitlines():
        k,sep,v=line.partition('=')
        if sep and k in ('version','log','size','root_hash','leaf_index'):
            if k in d: raise ValueError('duplicate proof field')
            d[k]=v
    if set(d)!={'version','log','size','root_hash','leaf_index'} or d['version']!='2' or d['log']!=f.LOG_ID or not f.HEX64.fullmatch(d['root_hash']): raise ValueError('proof coordinates')
    n,i=int(d['size']),int(d['leaf_index'])
    if not 0<=i<n<2**63: raise ValueError('index bounds')
    return n,i,d['root_hash']

def evaluate(anchor,candidate,verify_bin,live_bin=None):
    a,ap,key=bundle(anchor,True); b,bp,_=bundle(candidate)
    old,new,x,y,ledger=link(a,b,NOSTR)
    with tempfile.TemporaryDirectory(prefix='r22-22g-') as td:
        d=Path(td)
        # Snapshot once, bind the exact event IDs to the exact proof bytes.
        for name,value in [('old.proof',ap),('new.proof',bp),('old.msg',f.event_leaf_message(old)),('new.msg',f.event_leaf_message(new)),('submit.pub',key)]: (d/name).write_bytes(value)
        for prefix in ('old','new'):
            p=subprocess.run([str(verify_bin),'-k',str(d/'submit.pub'),'-P',POLICY,str(d/(prefix+'.proof'))],input=(d/(prefix+'.msg')).read_bytes(),capture_output=True,timeout=30)
            if p.returncode!=0: raise ValueError('HOLD_OFFICIAL_PROOF')
        an,ai,ar=coordinates(ap);bn,bi,br=coordinates(bp)
        if not (bi>ai and bn>=an): raise ValueError('HOLD_LOG_ORDER')
        if live_bin is not None:
            p=subprocess.run([str(live_bin)],cwd=d,capture_output=True,timeout=150)
            if p.returncode!=0: raise ValueError('HOLD_LIVE_CONSISTENCY: '+p.stderr.decode(errors='replace')[:300])
            live=json.loads(p.stdout)
            if live['result']!='VERIFIED_COMMON_HEAD' or live['old_index']!=ai or live['new_index']!=bi or live['candidate_message_sha256']!=f.sha(f.event_leaf_message(new)): raise ValueError('HOLD_LIVE_BINDING')
        else: live=None
    return {'result':'LINKED_SUCCESSOR_RESEARCH_ONLY' if live else 'HOLD_LIVE_CONSISTENCY_NOT_RUN','old_seq':x['seq'],'new_seq':y['seq'],'old_index':ai,'new_index':bi,'ledger_sha256':f.sha(ledger),'live':live,'global_latest':'UNKNOWN','trust_activation':'NO_GO','production':'NO_GO','admission':False}

if __name__=='__main__':
    if len(sys.argv) not in (4,5): raise SystemExit('anchor candidate official-verifier [live-verifier]')
    try: print(json.dumps(evaluate(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]).resolve(),Path(sys.argv[4]).resolve() if len(sys.argv)==5 else None),sort_keys=True))
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,zipfile.BadZipFile,subprocess.SubprocessError) as e: print('HOLD',str(e));raise SystemExit(1)
