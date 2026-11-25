"""R22.20 disposable synthetic lifecycle checkpoint experiment; no admission."""
import hashlib,json,os,secrets,shutil,sqlite3,subprocess,sys,zipfile
from pathlib import Path
from nonce_ledger import CUSTODIAN,PUBLISHER,PINS,digest
PIN='b7f1702b88241f6062c6e9c3975e5969620e98b6fc47321ca7e91956c7500f8e'
PROFILE='ARIO-R22.20-PUBLIC-SYNTHETIC-LIFECYCLE-v1'

def encode(o): return (json.dumps(o,sort_keys=True,separators=(',',':'))+'\n').encode('ascii')
def checksum(b): return digest(hashlib.sha256(b).digest())
def read_state(db):
    with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True) as c:
        epoch=c.execute('SELECT epoch FROM session WHERE id=1').fetchone()[0]
        rows=c.execute('SELECT nonce,query_hash,epoch,state,response_hash FROM challenges ORDER BY nonce').fetchall()
    return {'epoch':epoch,'requests':[dict(zip(('nonce','query_hash','epoch','state','response_hash'),r)) for r in rows]}
def envelope(scope,state,previous):
    return {'profile':PROFILE,'scope':scope,'state':state,'previous_checksum':previous,'synthetic':True,'authoritative':False,'trust_activation':'NO_GO','production':'NO_GO'}
def child(root,uid,args):
    r=subprocess.run(args,user=uid,group=uid,extra_groups=[],cwd=root,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=40)
    if r.returncode: raise RuntimeError(r.stderr)
    return r.stdout.strip()
def prepare(root,archive):
    assert os.geteuid()==0 and digest(archive.read_bytes())==PIN
    root.mkdir(mode=0o755); root.chmod(0o755)
    for n in ('first','second','fixtures','custodian','publisher'): (root/n).mkdir()
    for n,uid in [('custodian',CUSTODIAN),('publisher',PUBLISHER)]:
        os.chown(root/n,uid,uid); (root/n).chmod(0o700)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for n in ('ca.pem','tsa.pem','a.tsq','b.tsq','a.tsr','b.tsr'):
            p=root/'fixtures'/n; p.write_bytes(z.read(n)); p.chmod(0o444)
    for n,h in PINS.items(): assert digest((root/'fixtures'/n).read_bytes())==h
    for n in ('lifecycle.py','nonce_ledger.py'):
        p=root/n; shutil.copyfile(Path(__file__).with_name(n),p); p.chmod(0o444)
    db=root/'custodian/state.sqlite'; f=root/'fixtures'; pub=root/'publisher/state.json'
    def call(op,e=1,n='a.tsq',r='-',want=''):
        got=child(root,CUSTODIAN,[sys.executable,'-B',str(root/'lifecycle.py'),str(db),str(f),op,str(e),n,str(f/r) if r!='-' else '-','none'])
        assert got==want,(op,got,want)
    def setpub(state):
        child(root,PUBLISHER,[sys.executable,'-c','import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])',str(pub),encode(state).decode()])
    call('init',want='INITIALIZED:1'); call('issue',want='ISSUED:1')
    old=read_state(db); assert old['epoch']==1 and [r['state'] for r in old['requests']]==['ISSUED']
    setpub(old); shutil.copyfile(db,root/'old.sqlite'); (root/'old.sqlite').chmod(0o600); shutil.copyfile(pub,root/'old-publisher.json')
    scope=secrets.token_hex(24); a=encode(envelope(scope,old,'GENESIS')); (root/'first/envelope.json').write_bytes(a)
    call('rotate',want='ROTATED:2'); call('issue',2,'b.tsq',want='ISSUED:2'); call('consume',2,'b.tsq','b.tsr',want='CONSUMED_RESEARCH_ONLY')
    new=read_state(db); assert new['epoch']==2 and {r['state'] for r in new['requests']}=={'ABANDONED','CONSUMED'}
    setpub(new); (root/'second/envelope.json').write_bytes(encode(envelope(scope,new,checksum(a))))
    print('LIFECYCLE_REAL epoch1 ISSUED -> epoch2 ABANDONED + CONSUMED')
def restore(root):
    db=root/'custodian/state.sqlite'; pub=root/'publisher/state.json'; old=json.loads((root/'first/envelope.json').read_bytes())['state']; new=json.loads((root/'second/envelope.json').read_bytes())['state']
    assert read_state(db)==new and json.loads(pub.read_bytes())==new
    # Shared root really restores both files, with no child running.
    db.write_bytes((root/'old.sqlite').read_bytes()); pub.write_bytes((root/'old-publisher.json').read_bytes())
    assert read_state(db)==old and json.loads(pub.read_bytes())==old
    (root/'first/restored.json').write_bytes(encode({'ledger':read_state(db),'publisher':json.loads(pub.read_bytes())}))
    print('JOINT_RESTORE_REAL epoch1 ISSUED; local-only rollback is RED')
def compare(local,a,b,discovery):
    # Only called after official proof verification and authenticated discovery in workflow.
    # This comparator alone cannot authenticate any of its inputs.
    if discovery is None: return 'HOLD_EXTERNAL_UNAVAILABLE'
    try:
        x,y=json.loads(a),json.loads(b)
        if x['profile']!=PROFILE or y['profile']!=PROFILE or x['scope']!=y['scope'] or y['previous_checksum']!=checksum(a): return 'HOLD_CONTEXT_OR_LINK'
        for v in (x,y):
            if v['synthetic'] is not True or v['authoritative'] is not False or v['trust_activation']!='NO_GO' or v['production']!='NO_GO': return 'HOLD_BOUNDARY'
        if discovery!=checksum(b): return 'HOLD_CONTENT_MISMATCH'
        old,new=x['state'],y['state']; o=old['requests']; n=new['requests']
        if old['epoch']!=1 or new['epoch']!=2 or len(o)!=1 or len(n)!=2 or o[0]['state']!='ISSUED' or o[0]['epoch']!=1 or o[0]['response_hash'] is not None: return 'HOLD_TRANSITION'
        prev=[r for r in n if r['nonce']==o[0]['nonce']]; other=[r for r in n if r['nonce']!=o[0]['nonce']]
        if len(prev)!=1 or len(other)!=1 or prev[0]!={**o[0],'state':'ABANDONED'} or other[0]['epoch']!=2 or other[0]['state']!='CONSUMED' or other[0]['query_hash']!=PINS['b.tsq'] or other[0]['response_hash']!='996001d25b8928eacaf343dd2a941990127864b181f74acc4deb7ecd4251ee05' or o[0]['query_hash']!=PINS['a.tsq']: return 'HOLD_TRANSITION'
        if local['ledger']!=local['publisher']: return 'HOLD_LOCAL_SPLIT'
        if local['ledger']==old: return 'HOLD_JOINT_ROLLBACK_BELOW_EXTERNAL_EVIDENCE'
        if local['ledger']==new: return 'MATCH_EXTERNAL_EVIDENCE_NOT_FRESHNESS'
        return 'HOLD_LOCAL_STATE_UNKNOWN'
    except (KeyError,TypeError,ValueError): return 'HOLD_INVALID_INPUT'
def checks(first,second,discovered):
    a=(first/'envelope.json').read_bytes(); b=(second/'envelope.json').read_bytes(); local=json.loads((first/'restored.json').read_bytes()); new=json.loads(b)['state']
    def mutate(fn):
        v=json.loads(b); fn(v); return encode(v)
    badscope=mutate(lambda v:v.update(scope='wrong')); badlink=mutate(lambda v:v.update(previous_checksum='wrong')); badstate=mutate(lambda v:v['state']['requests'][0].update(state='ISSUED')); badauth=mutate(lambda v:v.update(authoritative=True))
    cases=[('restored_both',local,b,discovered,'HOLD_JOINT_ROLLBACK_BELOW_EXTERNAL_EVIDENCE'),('matching_new',{'ledger':new,'publisher':new},b,discovered,'MATCH_EXTERNAL_EVIDENCE_NOT_FRESHNESS'),('external_missing',local,b,None,'HOLD_EXTERNAL_UNAVAILABLE'),('old_content_replayed',local,a,discovered,'HOLD_CONTEXT_OR_LINK'),('wrong_discovered_checksum',local,b,'0'*64,'HOLD_CONTENT_MISMATCH'),('scope',local,badscope,checksum(badscope),'HOLD_CONTEXT_OR_LINK'),('link',local,badlink,checksum(badlink),'HOLD_CONTEXT_OR_LINK'),('terminal_mutation',local,badstate,checksum(badstate),'HOLD_TRANSITION'),('authority_mutation',local,badauth,checksum(badauth),'HOLD_BOUNDARY'),('split',{'ledger':local['ledger'],'publisher':new},b,discovered,'HOLD_LOCAL_SPLIT')]
    for name,l,r,d,want in cases:
        got=compare(l,a,r,d); assert got==want,(name,got,want); print(name,got,'PASS')
    print('10/10 COMPARATOR CASES PASS; NO_ADMISSION; GLOBAL_FRESHNESS=UNKNOWN')
if __name__=='__main__':
    op=sys.argv[1]
    if op=='prepare': prepare(Path(sys.argv[2]).resolve(),Path(sys.argv[3]).resolve())
    elif op=='restore': restore(Path(sys.argv[2]).resolve())
    elif op=='check': checks(Path(sys.argv[2]),Path(sys.argv[3]),sys.argv[4])
