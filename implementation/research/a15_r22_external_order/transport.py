"""A15 public synthetic research bridge to the pinned R22 TEST infrastructure.
No real keys, private history, admission or production. Requires existing R22 checkout.
"""
import base64, hashlib, json, os, secrets, shutil, subprocess, sys, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'r22_11_external_content'))
import recovery as env
LOG='4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d'
POLICY='sigsum-test1-2025'
DOMAIN='ARIO_A15_R22_EXTERNAL_ORDER_V08_SYNTHETIC'
PREFIX='ARIO A15 PUBLIC SYNTHETIC v0.8 preimage: '
LIMIT=24000

def require(ok,reason):
    if not ok: raise ValueError(reason)

def sha(raw): return hashlib.sha256(raw).hexdigest()
def read_json(raw): return json.loads(raw.decode('utf-8'),object_pairs_hook=env.unique)
def payload(raw,n):
    require(0<len(raw)<=LIMIT,'HOLD_PAYLOAD_SIZE')
    x=read_json(raw)
    require(type(x) is dict and x.get('domain')==DOMAIN and x.get('kind')==('RESERVE','SIGNED_STAGE','FINAL')[n-1],'HOLD_PAYLOAD_SCOPE')
    # No arbitrary data sources in the runner: input comes only from pinned synthetic v0.7 fixture.
    return x

def proof_fields(raw):
    return dict(line.split('=',1) for line in raw.decode('ascii').splitlines() if line.startswith(('size=','root_hash=','leaf_index=','log=','leaf=')))

def key_bytes(pub):
    b=base64.b64decode(pub.split()[1],validate=True);n=int.from_bytes(b[:4],'big')
    require(b[4:4+n]==b'ssh-ed25519' and int.from_bytes(b[4+n:8+n],'big')==32 and len(b)==8+n+32,'HOLD_PUBLIC_KEY')
    return b[8+n:]

def check_proof(folder,pub):
    with (folder/'envelope.json').open('rb') as f:
        subprocess.run(['sigsum-verify','-k',str(pub),'-P',POLICY,str(folder/'envelope.json.proof')],stdin=f,check=True,timeout=30)
    x=proof_fields((folder/'envelope.json.proof').read_bytes())
    require(x['log']==LOG and x['leaf'].split()[0]==sha(key_bytes(pub.read_bytes())) and int(x['leaf_index'])<int(x['size']),'HOLD_PROOF_PIN')
    return x

def make_event(raw,target):
    from coincurve import PrivateKey
    require(len(raw)<=LIMIT and sha(raw)==target,'HOLD_BLOB_HASH')
    k=PrivateKey();e={'pubkey':k.public_key_xonly.format().hex(),'created_at':int(time.time()),'kind':env.KIND,'tags':[['x',target]],'content':PREFIX+base64.b64encode(raw).decode('ascii')}
    e['id']=env.event_id(e);e['sig']=k.sign_schnorr(bytes.fromhex(e['id'])).hex();return e

def extract(e,target):
    from coincurve import PublicKeyXOnly
    try:
        if e['kind']!=env.KIND or ['x',target] not in e['tags'] or env.event_id(e)!=e['id']:return None
        if not PublicKeyXOnly(bytes.fromhex(e['pubkey'])).verify(bytes.fromhex(e['sig']),bytes.fromhex(e['id'])):return None
        c=e['content']
        if not isinstance(c,str) or not c.startswith(PREFIX) or len(c)>len(PREFIX)+4*((LIMIT+2)//3):return None
        b=base64.b64decode(c[len(PREFIX):],validate=True)
        return b if 0<len(b)<=LIMIT and sha(b)==target else None
    except (ValueError,KeyError,TypeError,AttributeError,RecursionError):return None

def publish_blob(raw,target):
    e=make_event(raw,target);accepted=[]
    for url in env.RELAYS:
        try:
            with env.connect(url) as ws:
                ws.send(json.dumps(['EVENT',e]));deadline=time.monotonic()+12
                for _ in range(16):
                    m=json.loads(ws.recv(timeout=max(.01,deadline-time.monotonic())))
                    if isinstance(m,list) and len(m)>=4 and m[:2]==['OK',e['id']]:
                        if m[2] is True:accepted.append(url)
                        break
                    if time.monotonic()>=deadline:break
        except Exception as exc: print(json.dumps({'relay':url,'blob_publish_error':type(exc).__name__}),flush=True)
    print(json.dumps({'blob_accepted':accepted,'sha256':target}),flush=True)
    require(bool(accepted),'HOLD_EXTERNAL_BLOB_UNAVAILABLE')

def fetch_blob(target):
    found=None;sources=[];sub='ario-a15-v08'
    for url in env.RELAYS:
        try:
            with env.connect(url) as ws:
                ws.send(json.dumps(['REQ',sub,{'kinds':[env.KIND],'#x':[target],'limit':16}]))
                deadline=time.monotonic()+15
                for _ in range(32):
                    m=json.loads(ws.recv(timeout=max(.01,deadline-time.monotonic())))
                    if isinstance(m,list) and len(m)>=3 and m[:2]==['EVENT',sub]:
                        b=extract(m[2],target)
                        if b is not None:
                            require(found is None or found==b,'HOLD_CONFLICTING_BYTES');found=b;sources.append(url);break
                    if isinstance(m,list) and len(m)>=2 and m[0] in ('EOSE','CLOSED') and m[1]==sub:break
                    if time.monotonic()>=deadline:break
        except Exception as exc: print(json.dumps({'relay':url,'blob_read_error':type(exc).__name__}),flush=True)
    return found,sources

def commit(root,n):
    require(n in (1,2,3),'HOLD_PHASE');d=root/f'r{n}';raw=(d/'payload.json').read_bytes();payload(raw,n)
    private=Path(os.environ['A15_EPHEMERAL_SIGSUM_KEY']).resolve();pub=Path(str(private)+'.pub')
    scope=(root/'scope.txt').read_text().strip()
    prev='GENESIS' if n==1 else env.checksum((root/f'r{n-1}'/'envelope.json').read_bytes())
    obj={'profile':env.PROFILE,'scope':scope,'record_count':n,'previous_checksum':prev,'floor_commitment_sha256':sha(raw),'synthetic_nonce':secrets.token_hex(32),'synthetic':True,'authoritative':False,'historical_event_truth':'UNKNOWN','trust_activation':'NO_GO','production':'NO_GO'}
    envelope=env.canonical(obj);env.parse(envelope)
    with (d/'envelope.json').open('xb') as f:f.write(envelope)
    subprocess.run(['sigsum-submit','-P',POLICY,'-k',str(private),str(d/'envelope.json')],check=True,timeout=180)
    current=check_proof(d,pub)
    if n>1:
        p=proof_fields((root/f'r{n-1}'/'envelope.json.proof').read_bytes())
        require(int(current['leaf_index'])>int(p['leaf_index']) and int(current['size'])>int(p['size']),'HOLD_EXTERNAL_ORDER')
    env.publish(envelope)  # Existing pinned R22 envelope transport, unmodified.
    publish_blob(raw,sha(raw)) # Same R22 relays and connection/event-ID primitives, A15-specific preimage schema.
    print(json.dumps({'phase':n,'index':int(current['leaf_index']),'checksum':env.checksum(envelope),'proof_verified':True}),flush=True)

def export(root,first,reveal):
    first.mkdir();reveal.mkdir()
    pub=Path(os.environ['A15_EPHEMERAL_SIGSUM_KEY']+'.pub')
    for n in (1,2,3):
        d=root/f'r{n}';check_proof(d,pub);shutil.copytree(d,reveal/f'r{n}')
    a=root/'r1';x=proof_fields((a/'envelope.json.proof').read_bytes());raw=(a/'envelope.json').read_bytes()
    shutil.copyfile(pub,first/'synthetic-key.pub')
    for name in ('envelope.json','envelope.json.proof'):shutil.copyfile(a/name,first/name)
    boot={'start':int(x['leaf_index']),'size':int(x['size']),'root':x['root_hash'],'public':key_bytes(pub.read_bytes()).hex(),'first_checksum':env.checksum(raw)}
    (first/'bootstrap.json').write_bytes(env.canonical(boot));(first/'local-state.json').write_bytes(env.canonical({'record_count':1,'checkpoint':boot['first_checksum']}))
    require(set(p.name for p in first.iterdir())=={'synthetic-key.pub','envelope.json','envelope.json.proof','bootstrap.json','local-state.json'},'HOLD_BOOTSTRAP_LEAK')
    # No private keys or publisher lab dirs in either artifact.

def verify_discovery(boot,report):
    matches=report.get('matching_signed_leaves');end=report.get('sampled_tree_size')
    require(report.get('disposition')=='HOLD_OPAQUE_NEW_SIGNED_COMMITMENT' and report.get('complete_sampled_suffix') is True and report.get('new_opaque_signed_commitments')==2 and type(matches) is list and len(matches)==3 and type(end) is int,'HOLD_NOT_THREE_MATCHES')
    require(matches[0]=={'index':boot['start'],'checksum':boot['first_checksum']},'HOLD_FIRST_MATCH')
    prior=-1;seen=set()
    for x in matches:
        require(type(x) is dict and set(x)=={'index','checksum'} and type(x['index']) is int and prior<x['index']<end and env.HEX.fullmatch(x['checksum']) and x['checksum'] not in seen,'HOLD_MATCH_ORDER')
        prior=x['index'];seen.add(x['checksum'])
    return matches

def verify_envelope(raw,match,n,previous,scope):
    require(env.checksum(raw)==match['checksum'],'HOLD_ENVELOPE_HASH');x=env.parse(raw)
    require(x['record_count']==n and x['previous_checksum']==previous and x['scope']==scope,'HOLD_ENVELOPE_CHAIN');return x

def recover(first,report_path,out):
    boot=read_json((first/'bootstrap.json').read_bytes());report=json.loads(report_path.read_text().splitlines()[-1]);matches=verify_discovery(boot,report)
    pub=first/'synthetic-key.pub';require(key_bytes(pub.read_bytes()).hex()==boot['public'],'HOLD_BOOTSTRAP_KEY')
    x=check_proof(first,pub);require(int(x['leaf_index'])==boot['start'] and int(x['size'])==boot['size'] and x['root_hash']==boot['root'],'HOLD_BOOTSTRAP_PROOF')
    a=(first/'envelope.json').read_bytes();scope=env.parse(a)['scope'];previous='GENESIS';out.mkdir()
    for n,match in enumerate(matches,1):
        raw,sources=env.fetch(match['checksum']);require(raw is not None and bool(sources),'HOLD_ENVELOPE_UNAVAILABLE')
        if n==1:require(raw==a,'HOLD_FIRST_BYTES')
        x=verify_envelope(raw,match,n,previous,scope);previous=match['checksum']
        p,ps=fetch_blob(x['floor_commitment_sha256']);require(p is not None and bool(ps) and sha(p)==x['floor_commitment_sha256'],'HOLD_PREIMAGE_UNAVAILABLE');obj=payload(p,n)
        d=out/f'r{n}';d.mkdir();(d/'envelope.json').write_bytes(raw);(d/'payload.json').write_bytes(p)
        if n==1:shutil.copyfile(first/'envelope.json.proof',d/'envelope.json.proof')
        if n>1:
            old=out/f'r{n-1}'; embedded=obj[f'proof{n-1}'].encode('ascii')
            if n==2:require(embedded==(old/'envelope.json.proof').read_bytes(),'HOLD_FIRST_PROOF_BYTES')
            else:(old/'envelope.json.proof').write_bytes(embedded)
            pcheck=check_proof(old,pub);require(int(pcheck['leaf_index'])==matches[n-2]['index'],'HOLD_PROOF_SCAN_INDEX')
        print(json.dumps({'phase':n,'envelope_sources':sources,'payload_sources':ps,'index':match['index'],'checksum':match['checksum']}),flush=True)
    # R3 inclusion was checked by fresh R22 scanner against cosigned tree; its standalone proof is withheld until reveal.
    subprocess.run(['node',str(Path(__file__).with_name('bridge.js')),'verify',str(out)],check=True,timeout=30)
    (out/'report.json').write_bytes(env.canonical({'status':'RECOVERED_THREE_LINKED_SYNTHETIC_COMMITMENTS_ONLY','matches':matches,'global_latest':'NOT_ESTABLISHED','independent_custody':'NOT_ESTABLISHED','local_durability_attestation':'NOT_ESTABLISHED','trust_activation':'NO_GO'}))

def reveal(first,withheld,recovered):
    report=read_json((recovered/'report.json').read_bytes());pub=first/'synthetic-key.pub'
    require(report['status']=='RECOVERED_THREE_LINKED_SYNTHETIC_COMMITMENTS_ONLY','HOLD_RECOVERY_REPORT')
    for n in (1,2,3):
        a=withheld/f'r{n}';b=recovered/f'r{n}';p=check_proof(a,pub)
        require(int(p['leaf_index'])==report['matches'][n-1]['index'],'HOLD_REVEAL_INDEX')
        for name in ('envelope.json','payload.json'):require((a/name).read_bytes()==(b/name).read_bytes(),'HOLD_REVEAL_BYTES')
        if n<3:require((a/'envelope.json.proof').read_bytes()==(b/'envelope.json.proof').read_bytes(),'HOLD_REVEAL_PROOF')
    print('A15_R22_THREE_EXTERNAL_PREIMAGES_MATCH_WITHHELD_BYTES; RESEARCH_ONLY; NO_GO')

if __name__=='__main__':
    try:
        cmd,*args=sys.argv[1:]
        if cmd=='commit' and len(args)==2:commit(Path(args[0]),int(args[1]))
        elif cmd=='export' and len(args)==3:export(*map(Path,args))
        elif cmd=='recover' and len(args)==3:recover(*map(Path,args))
        elif cmd=='reveal' and len(args)==3:reveal(*map(Path,args))
        else:raise ValueError('HOLD_ARGUMENTS')
    except Exception as e:print('HOLD:',type(e).__name__,str(e),file=sys.stderr);sys.exit(2)
