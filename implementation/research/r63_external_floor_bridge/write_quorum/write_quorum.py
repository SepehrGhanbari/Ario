"""Single-transition R63 RESEARCH_ONLY durability lab. No operational authority."""
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

NAMES = ('w1', 'w2', 'w3', 'w4')
Q = 3
FINAL = 'FINAL_RESEARCH_COMMITMENT_ONLY'
HOLD = 'HOLD_NOT_FINAL'
HEX = re.compile(r'[0-9a-f]{64}\Z')

def need(ok, msg):
    if not ok: raise ValueError(msg)

def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')

def digest(raw): return hashlib.sha256(raw).hexdigest()
def pub(key): return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

def unique(pairs):
    d = {}
    for k,v in pairs:
        need(k not in d, 'duplicate'); d[k] = v
    return d

def decode(raw):
    need(type(raw) is bytes and 0 < len(raw) <= 16384, 'wire length')
    obj = json.loads(raw.decode('ascii'), object_pairs_hook=unique)
    need(canon(obj) == raw, 'noncanonical'); return obj

def hex64(x): return type(x) is str and HEX.fullmatch(x) is not None

def policy(keys, epoch, parent):
    need(type(keys) is dict and set(keys) == set(NAMES), 'roster')
    need(all(hex64(v) for v in keys.values()) and len(set(keys.values())) == 4, 'distinct keys')
    need(hex64(epoch) and hex64(parent), 'epoch/parent')
    return canon(dict(profile='ARIO-R63-WRITE-LAB-v1', keys=keys, epoch=epoch, parent=parent, sequence=11, quorum=Q))

def proposal(p, target):
    need(hex64(target), 'target'); return canon(dict(policy_sha256=digest(p), sequence=11, commitment=target))

def sign(key, tag, body): return key.sign(tag + b'\0' + body).hex()
def verify(key, tag, body, signature):
    need(type(signature) is str and re.fullmatch(r'[0-9a-f]{128}', signature), 'signature syntax')
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(key)).verify(bytes.fromhex(signature), tag+b'\0'+body)

def receipt(p, name, key, proposed):
    body = dict(witness=name, proposal=proposed.decode('ascii'))
    return canon(dict(body=body, signature=sign(key,b'R63-DURABLE-PREPARE',canon(body))))

def check_receipt(p, raw, proposed):
    item=decode(raw); need(type(item) is dict and set(item)=={'body','signature'},'receipt schema')
    body=item['body']; need(type(body) is dict and set(body)=={'witness','proposal'},'body schema')
    name=body['witness']; keys=decode(p)['keys']; need(type(name) is str and name in keys,'witness')
    need(body['proposal']==proposed.decode('ascii'),'proposal mismatch')
    verify(keys[name],b'R63-DURABLE-PREPARE',canon(body),item['signature']); return name

def certificate(p, proposed, receipts):
    need(type(receipts) in (list,tuple) and Q<=len(receipts)<=4,'quorum')
    items={}
    for raw in receipts:
        n=check_receipt(p,raw,proposed); need(n not in items,'duplicate witness'); items[n]=raw.decode('ascii')
    return canon(dict(proposal=proposed.decode('ascii'), receipts=[items[n] for n in sorted(items)]))

def check_certificate(p, proposed, raw):
    c=decode(raw); need(type(c) is dict and set(c)=={'proposal','receipts'},'certificate schema')
    need(c['proposal']==proposed.decode('ascii') and type(c['receipts']) is list,'certificate proposal')
    need(certificate(p,proposed,[s.encode('ascii') for s in c['receipts']])==raw,'certificate canonical'); return raw

def db(path, pin):
    # FULL sync is requested; hardware guarantees and independent custody not proved.
    c=sqlite3.connect(path,timeout=10,isolation_level=None)
    try:
        c.execute('PRAGMA journal_mode=DELETE'); c.execute('PRAGMA synchronous=FULL')
        c.execute('BEGIN IMMEDIATE')
        c.execute('CREATE TABLE IF NOT EXISTS meta (id INTEGER PRIMARY KEY CHECK(id=1), pin TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS slot (id INTEGER PRIMARY KEY CHECK(id=1), value BLOB NOT NULL)')
        c.execute('INSERT OR IGNORE INTO meta VALUES(1,?)',(pin,))
        need(c.execute('SELECT pin FROM meta WHERE id=1').fetchone()==(pin,),'db policy mismatch')
        c.commit(); return c
    except BaseException:
        c.close(); raise

def put_once(path, pin, raw, validate, failpoint=None):
    c=db(path,pin)
    try:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT value FROM slot WHERE id=1').fetchone()
        if row:
            validate(row[0]); need(row[0]==raw,'slot locked'); c.commit(); return row[0]
        validate(raw); c.execute('INSERT INTO slot VALUES(1,?)',(raw,))
        if failpoint: failpoint('before_commit')
        c.commit()
        if failpoint: failpoint('after_commit')
        return raw
    finally: c.close()

def stored(path,pin):
    c=db(path,pin)
    try:
        row=c.execute('SELECT value FROM slot WHERE id=1').fetchone(); return row[0] if row else None
    finally: c.close()

class Witness:
    def __init__(self,path,p,name,key):
        need(name in NAMES and pub(key)==decode(p)['keys'][name],'key mismatch')
        self.path,self.p,self.name,self.key=path,p,name,key
        self.pin=digest(p)+':witness:'+name
    def prepare(self,target,failpoint=None):
        proposed=proposal(self.p,target); raw=receipt(self.p,self.name,self.key,proposed)
        return put_once(self.path,self.pin,raw,lambda r:check_receipt(self.p,r,proposed),failpoint)
    def read(self,nonce):
        need(hex64(nonce),'challenge')
        r=stored(self.path,self.pin)
        body=dict(witness=self.name,policy_sha256=digest(self.p),nonce=nonce,receipt=r.decode('ascii') if r else None)
        return canon(dict(body=body,signature=sign(self.key,b'R63-READ',canon(body))))

def recover(p, target, nonce, replies):
    need(hex64(nonce) and type(replies) in (list,tuple) and Q<=len(replies)<=4,'read quorum')
    proposed=proposal(p,target); keys=decode(p)['keys']; names=set(); rs=[]
    for raw in replies:
        item=decode(raw); need(type(item) is dict and set(item)=={'body','signature'},'read schema')
        b=item['body']; need(type(b) is dict and set(b)=={'witness','policy_sha256','nonce','receipt'},'read body')
        n=b['witness']; need(type(n) is str and n in keys and n not in names,'read identity'); names.add(n)
        need(b['policy_sha256']==digest(p) and b['nonce']==nonce,'stale or wrong scope')
        verify(keys[n],b'R63-READ',canon(b),item['signature'])
        if b['receipt'] is not None:
            need(type(b['receipt']) is str,'read receipt syntax'); r=b['receipt'].encode('ascii')
            need(check_receipt(p,r,proposed)==n,'wrong receipt identity'); rs.append(r)
    return certificate(p,proposed,rs)

class Finalizer:
    def __init__(self,path,p,target):
        self.path,self.p,self.proposed=path,p,proposal(p,target); self.pin=digest(p)+':finalizer:'+digest(self.proposed)
    def finalize(self,receipts,failpoint=None):
        cert=certificate(self.p,self.proposed,receipts)
        return self._persist(cert,failpoint)
    def _persist(self,cert,failpoint=None):
        check_certificate(self.p,self.proposed,cert)
        # Different valid subsets can certify the same target: preserve first valid cert.
        old=stored(self.path,self.pin)
        if old is not None: return check_certificate(self.p,self.proposed,old)
        try: return put_once(self.path,self.pin,cert,lambda c:check_certificate(self.p,self.proposed,c),failpoint)
        except ValueError:
            old=stored(self.path,self.pin)
            if old is None: raise
            return check_certificate(self.p,self.proposed,old)
    def recover(self,nonce,replies):
        target=decode(self.proposed)['commitment']; return self._persist(recover(self.p,target,nonce,replies))
    def status(self):
        old=stored(self.path,self.pin)
        if old is None: return HOLD
        check_certificate(self.p,self.proposed,old); return FINAL
