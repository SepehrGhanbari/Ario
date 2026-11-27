"""RESEARCH_ONLY: recover public synthetic capsule from an untrusted archive.
Trust inputs are pinned independently of the archive. Not a freshness oracle.
"""
import argparse, base64, hashlib, json, os, pathlib, zipfile
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
ORIGIN='github.com/SepehrGhanbari/Ario/kladje-test-v1'
LOG=ORIGIN+'+50e6b45c+AQUBDEa9qhxEeT6UJrwEbedbzLvmntBhPS1oJO0hUw3s'
WIT='markovianprotocol.com/witness+41b8827f+BJKLl8rBYM0oUxSaWh9rjTldTprEpYj/SWVIGgacA9XC'
FLOOR_SHA='0eff86c73212a6a4796df1482c1558dddffb87188e7cad6c0fe5b8b0c5a60395'
FILES={'entries','capsule-size-1.json','capsule-size-2.json'}
def need(ok,msg):
    if not ok: raise ValueError(msg)
def sha(b): return hashlib.sha256(b).digest()
def dec(s):
    b=base64.b64decode(s,validate=True); need(base64.b64encode(b).decode()==s,'base64'); return b
def canonical(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
def obj(b):
    v=json.loads(b); need(type(v) is dict and canonical(v)==b,'noncanonical object'); return v
def key(v,kind):
    n,k,s=v.split('+'); b=dec(s); need(len(b)==33 and b[0]==kind and sha(n.encode()+b'\n'+b)[:4].hex()==k,'key'); return n,bytes.fromhex(k),Ed25519PublicKey.from_public_bytes(b[1:])
def floor(note):
    need(sha(note).hex()==FLOOR_SHA,'unexpected checkpoint (pinned size-2 evidence required)')
    body,lines=note.split(b'\n\n',1); body+=b'\n'; o,n,r=body.decode('ascii').splitlines(); need(o==ORIGIN and n=='2','origin/size'); root=dec(r); need(len(root)==32,'root')
    lines=lines.decode().splitlines(); need(len(lines)==2,'signature count')
    for i,(v,kind) in enumerate(((LOG,1),(WIT,4))):
        name,k,pub=key(v,kind); prefix='— '+name+' '; need(lines[i].startswith(prefix),'signature name'); b=dec(lines[i][len(prefix):]); need(b[:4]==k,'key ID')
        if i==0: need(len(b)==68,'signature length'); pub.verify(b[4:],body)
        else:
            need(len(b)==76,'cosignature length'); ts=int.from_bytes(b[4:12],'big'); pub.verify(b[12:],b'cosignature/v1\ntime '+str(ts).encode()+b'\n'+body)
    return root
def recover(archive,note):
    root=floor(note)
    with zipfile.ZipFile(archive) as z:
        names=z.namelist(); need(len(names)==len(FILES) and set(names)==FILES,'archive inventory')
        need(all(0<x.file_size<=16384 and not x.is_dir() for x in z.infolist()),'archive bounds')
        d={n:z.read(n) for n in names}
    raw=d['entries']; need(raw.endswith(b'\n'),'entry framing'); leaves=raw[:-1].split(b'\n'); need(len(leaves)==2,'leaf count')
    a,b=(sha(b'\x00'+x) for x in leaves); need(sha(b'\x01'+a+b)==root,'Merkle mismatch')
    caps=[]
    for i,leaf in enumerate(leaves,1):
        l=obj(leaf); raw=d[f'capsule-size-{i}.json']; need(raw.endswith(b'\n'),'capsule framing'); raw=raw[:-1]; c=obj(raw)
        need(l['origin']==ORIGIN and l['sequence']==i and l['scope']=='RESEARCH_ONLY' and l['synthetic'] is True,'leaf scope')
        need(l['previous_leaf_sha256']==(sha(leaves[i-2]).hex() if i==2 else None),'leaf lineage')
        need(l['capsule_sha256']==sha(raw).hex() and l['capsule_bytes']==len(raw),'capsule mismatch')
        need(c['scope']=='RESEARCH_ONLY' and c['synthetic'] is True and c['format']=='ario.synthetic-memory-capsule.v1','capsule scope')
        need(type(c['events']) is list and len(c['events'])==i+2,'event count'); caps.append(c)
    need(caps[1]['events'][:-1]==caps[0]['events'],'history prefix')
    return d['capsule-size-2.json']
def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('archive',type=pathlib.Path); p.add_argument('checkpoint',type=pathlib.Path); p.add_argument('output',type=pathlib.Path); a=p.parse_args()
    try:
        result=recover(a.archive,a.checkpoint.read_bytes())
        with a.output.open('xb') as f: f.write(result); f.flush(); os.fsync(f.fileno())
        print('RECOVERED_PINNED_SYNTHETIC_CAPSULE',sha(result).hex(), 'events',len(json.loads(result)['events']))
    except Exception as e: p.exit(2,'HOLD: '+type(e).__name__+': '+str(e)+'\n')
if __name__=='__main__': main()
