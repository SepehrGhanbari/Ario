"""R22.21B public synthetic first-only capsule. External storage, NOT trust custody."""
import base64,hashlib,io,json,re,sys,time,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'r22_20_external_monotonic_floor'))
import external_floor as f
from coincurve import PrivateKey, PublicKeyXOnly

RELAY='wss://relay.nostr.net'
PIN='2bedc6d0cc85857cfaed3ceafeb5d7700d78923057e661d9c5675d6925e6262b'
PREFIX='ARIO R22.21B public synthetic first-only capsule: '
NAMES={'event-id.txt','event-id.txt.proof','bootstrap.json','event.json','historical-first-id.txt','historical-first.json','historical-first.proof','historical-log.pub','sigsum.pub','third.json'}
def unpack(raw,out=None):
    if not 0<len(raw)<=32768 or f.sha(raw)!=PIN: raise ValueError('HOLD_CAPSULE_PIN')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        info=z.infolist()
        if len(info)!=len(NAMES) or {i.filename for i in info}!=NAMES or any(i.file_size>65536 for i in info): raise ValueError('HOLD_ZIP_SCHEMA')
        if z.testzip() is not None: raise ValueError('HOLD_CRC')
        data={i.filename:z.read(i) for i in info}
    boot=f.parse_json(data['bootstrap.json'],4096)
    event=f.parse_json(data['event.json'],131072)
    old=f.parse_json(data['historical-first.json'],131072)
    f.verify_event(event,event['pubkey']); f.verify_event(old,old['pubkey'])
    if f.target_for_event(event)!=boot['first_checksum'] or data['event-id.txt']!=f.event_leaf_message(event) or data['historical-first-id.txt']!=f.event_leaf_message(old) or f.parse_json(data['third.json'],1024)!= {'relay':RELAY}: raise ValueError('HOLD_BINDING')
    if out is not None:
        out.mkdir()
        for name,b in data.items(): (out/name).write_bytes(b)
    return data

def authenticate(e,expected):
    if type(e) is not dict or set(e)!={'id','pubkey','created_at','kind','tags','content','sig'}: raise ValueError('HOLD_EVENT_SCHEMA')
    if not all(type(e[k]) is str and re.fullmatch('[0-9a-f]{64}',e[k]) for k in ('id','pubkey')) or e['id']!=expected or type(e['kind']) is not int or e['kind']!=1 or type(e['created_at']) is not int or e['created_at']<0 or e['tags']!=[['t','ario-r22-21b-bootstrap'],['x',PIN]]: raise ValueError('HOLD_EVENT_FIELDS')
    if f.nostr_event_id(e)!=expected or not PublicKeyXOnly(bytes.fromhex(e['pubkey'])).verify(bytes.fromhex(e['sig']),bytes.fromhex(expected)): raise ValueError('HOLD_EVENT_SIGNATURE')
    if type(e['content']) is not str or not e['content'].startswith(PREFIX) or len(e['content'])>48000: raise ValueError('HOLD_CONTENT')
    raw=base64.b64decode(e['content'][len(PREFIX):],validate=True)
    unpack(raw)
    return raw

def fetch(expected):
    if not re.fullmatch('[0-9a-f]{64}',expected): raise ValueError('HOLD_POINTER')
    with f.connect(RELAY) as ws:
        ws.send(json.dumps(['REQ','capsule',{'ids':[expected],'kinds':[1],'limit':1}]))
        deadline=time.monotonic()+15
        for _ in range(32):
            msg=json.loads(ws.recv(timeout=max(.01,deadline-time.monotonic())))
            if type(msg) is list and len(msg)==3 and msg[:2]==['EVENT','capsule']:
                return authenticate(msg[2],expected)
            if type(msg) is list and len(msg)>=2 and msg[1]=='capsule' and msg[0] in ('EOSE','CLOSED'): break
            if time.monotonic()>=deadline: break
    raise ValueError('HOLD_EXTERNAL_BOOTSTRAP_UNAVAILABLE')

def publish(archive,pointer):
    raw=archive.read_bytes(); unpack(raw)
    key=PrivateKey()
    e={'pubkey':key.public_key_xonly.format().hex(),'created_at':int(time.time()),'kind':1,'tags':[['t','ario-r22-21b-bootstrap'],['x',PIN]],'content':PREFIX+base64.b64encode(raw).decode('ascii')}
    e['id']=f.nostr_event_id(e); e['sig']=key.sign_schnorr(bytes.fromhex(e['id'])).hex()
    assert authenticate(e,e['id'])==raw
    # No private key exported. Only the old, first-only package is sent.
    ok,errors=f.publish_event(e,(RELAY,))
    if ok!=[RELAY]: raise RuntimeError(('HOLD_PUBLISH',errors))
    if fetch(e['id'])!=raw: raise RuntimeError('HOLD_READBACK')
    pointer.write_text(e['id']+'\n')
    print(json.dumps({'event_id':e['id'],'archive_sha256':PIN,'relay':RELAY,'readback':'MATCH','private_key_exported':False},sort_keys=True),flush=True)
def recover(event_id,out):
    raw=fetch(event_id); unpack(raw,out)
    print(json.dumps({'bootstrap':'EXACT_EXTERNAL_READBACK','archive_sha256':f.sha(raw),'event_id':event_id,'bytes':len(raw),'independent_pointer_custody':'NOT_ESTABLISHED','authority':'NO_GO'},sort_keys=True),flush=True)
if __name__=='__main__':
    if sys.argv[1]=='publish': publish(Path(sys.argv[2]),Path(sys.argv[3]))
    elif sys.argv[1]=='recover': recover(sys.argv[2],Path(sys.argv[3]))
    else: raise SystemExit('arity')
