#!/usr/bin/env python3
"""Pure-Python BIP340 verification of retained public synthetic Nostr events."""
import hashlib,json,sys,zipfile
P=2**256-2**32-977
N=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G=(0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)
def inv(x): return pow(x,P-2,P)
def add(a,b):
    if a is None:return b
    if b is None:return a
    x,y=a;u,v=b
    if x==u and (y+v)%P==0:return None
    m=(3*x*x*inv(2*y%P) if a==b else (v-y)*inv((u-x)%P))%P
    z=(m*m-x-u)%P
    return z,(m*(x-z)-y)%P
def mul(k,q=G):
    r=None
    while k:
        if k&1:r=add(r,q)
        q=add(q,q);k>>=1
    return r
def tagged(t,m):
    h=hashlib.sha256(t.encode()).digest()
    return hashlib.sha256(h+h+m).digest()
def lift(x):
    if x>=P:return None
    c=(x*x*x+7)%P;y=pow(c,(P+1)//4,P)
    if y*y%P!=c:return None
    return x,(P-y if y&1 else y)
def verify(pk,msg,sig):
    if len(pk)!=32 or len(msg)!=32 or len(sig)!=64:return False
    q=lift(int.from_bytes(pk,'big'))
    if q is None:return False
    r=int.from_bytes(sig[:32],'big');s=int.from_bytes(sig[32:],'big')
    if r>=P or s>=N:return False
    e=int.from_bytes(tagged('BIP0340/challenge',sig[:32]+pk+msg),'big')%N
    R=add(mul(s),mul((N-e)%N,q))
    return R is not None and R[1]%2==0 and R[0]==r
def check(d):
    assert type(d['created_at']) is int and type(d['kind']) is int and type(d['tags']) is list
    pre=json.dumps([0,d['pubkey'],d['created_at'],d['kind'],d['tags'],d['content']],separators=(',',':'),ensure_ascii=False).encode()
    h=hashlib.sha256(pre).digest()
    assert h.hex()==d['id']
    pk=bytes.fromhex(d['pubkey']);sig=bytes.fromhex(d['sig'])
    assert verify(pk,h,sig)
    return d,h,pk,sig
def main(first,reveal):
    count=0
    for z,names in ((first,('event.json','historical-first.json')),(reveal,('event.json','historical-second.json'))):
        with zipfile.ZipFile(z) as a:
            assert a.testzip() is None
            for name in names:
                d,h,pk,sig=check(json.loads(a.read(name)))
                assert d['kind']==1
                count+=1
            if 'deletion.json' in a.namelist():
                d,h,pk,sig=check(json.loads(a.read('deletion.json')))
                assert d['kind']==5 and d['content']=='ARIO synthetic test deletion request; no personal data'
                assert d['tags']==[['e',json.loads(a.read('event.json'))['id']],['k','1']]
                assert not verify(pk,h,sig[:-1]+bytes([sig[-1]^1]))
                count+=1
    assert count==5
    print('NOSTR_BIP340_SIGNATURES 5/5 PASS')
    print('NOSTR_DELETION_TARGET_BINDING PASS')
    print('NOSTR_SIGNATURE_MUTATION REJECTED')
    print('PUBLIC_SYNTHETIC_ONLY; NO_KEYS; NO_PUBLICATION; TRUST=NO_GO')
if __name__=='__main__':
    if len(sys.argv)!=3: raise SystemExit('usage: verify_nostr_bip340.py R22_21_FIRST.zip R22_21_REVEAL.zip')
    main(sys.argv[1],sys.argv[2])
