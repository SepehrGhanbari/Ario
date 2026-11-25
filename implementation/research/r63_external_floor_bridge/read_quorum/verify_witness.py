import base64
from audit import H, LOG, check, dec, verify_sig, InvalidSignature
ORIGIN='sigsum.org/v1/tree/'+H(LOG).hex()
KEYS={'geomys':'witness.navigli.sunlight.geomys.org+a3e00fe2+BNy/co4C1Hn1p+INwJrfUlgz7W55dSZReusH/GhUhJ/G','markovian':'markovianprotocol.com/witness+41b8827f+BJKLl8rBYM0oUxSaWh9rjTldTprEpYj/SWVIGgacA9XC'}
def b64(s):
    b=base64.b64decode(s,validate=True); check(base64.b64encode(b).decode()==s,'noncanonical base64'); return b
def note(raw, vkey):
    name,kid,key=vkey.split('+',2); key=b64(key); check(len(key)==33 and key[0]==4,'key type')
    check(H(name.encode()+b'\n'+key)[:4].hex()==kid,'witness key ID')
    body,sigs=raw.decode('utf-8').split('\n\n'); origin,size,root=body.splitlines(); check(origin==ORIGIN,'origin'); size=dec(size); root=b64(root); check(len(root)==32,'root')
    body=(body+'\n').encode(); sigs=sigs.splitlines(); check(len(sigs)==2,'signature count')
    a,b=[x.split(' ') for x in sigs]; check(a[:2]==['—',ORIGIN] and b[:2]==['—',name],'signer names')
    l,w=b64(a[2]),b64(b[2]); check(len(l)==68 and len(w)==76,'signature size'); check(l[:4]==H(ORIGIN.encode()+b'\n'+b'\x01'+LOG)[:4] and w[:4].hex()==kid,'signature key ID')
    verify_sig(LOG,l[4:],body); ts=int.from_bytes(w[4:12],'big'); verify_sig(key[1:],w[12:],b'cosignature/v1\ntime '+str(ts).encode()+b'\n'+body)
    return size,root,ts
