"""R22.18 bounded archived-response lab, NOT a production service or admission."""
import hashlib
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

CUSTODIAN = 65533
PUBLISHER = 65534
PINS = {
    'ca.pem':'2151b61137ffa86bf664691ba67e7da0b19f98c758e3d228d5d8ebf27e044438',
    'tsa.pem':'8bfb0305bb64e2571ca507552ef3245cb1c2fee8728e0ff8689225081ea13467',
    'a.tsq':'8922d598550e8863a81675faef61a671f027df3c112c05f55e2fd8dc3e2f0855',
    'b.tsq':'3db90ef0dfc422cb1ebe6865a342e80c141717726eb1a9526eb2986b8a4b0938',
}
SCOPE = 'R22.17-FREETSA-SYNTHETIC-ONLY'

def digest(b): return hashlib.sha256(b).hexdigest()

def pinned(path):
    raw = path.read_bytes()
    if digest(raw) != PINS[path.name]: raise ValueError('pin')
    return raw

def command(args, env=None):
    return subprocess.run(['/usr/bin/openssl', *args], capture_output=True, timeout=8, env=env)

def nonce(query):
    r = command(['ts','-query','-in',str(query),'-text'])
    m = re.findall(rb'^Nonce: 0x([0-9A-Fa-f]+)$', r.stdout, re.M)
    if r.returncode or len(m)!=1: raise ValueError('nonce')
    return format(int(m[0],16),'x')

def connect(db, create=False):
    c = sqlite3.connect(db.resolve().as_uri()+('?mode=rwc' if create else '?mode=rw'),uri=True,timeout=15,isolation_level=None)
    c.execute('PRAGMA synchronous=FULL')
    return c

def initialize(db, fixtures):
    # Trusted lab supervisor provisions exact historical requests; not live issuance.
    if os.getuid()!=CUSTODIAN or db.exists(): raise ValueError('init denied')
    with connect(db,True) as c:
        c.execute('BEGIN IMMEDIATE')
        c.execute('CREATE TABLE challenges (scope TEXT NOT NULL, nonce TEXT NOT NULL, query_hash TEXT NOT NULL, response_hash TEXT, PRIMARY KEY(scope,nonce))')
        for name in ('a.tsq','b.tsq'):
            p=fixtures/name
            c.execute('INSERT INTO challenges VALUES(?,?,?,NULL)',(SCOPE,nonce(p),digest(pinned(p))))
        c.commit()

def verify(fixtures,qraw,rraw):
    # Capture input once; verify precisely the bytes hashed/stored. No shell interpolation.
    ca,tsa=(pinned(fixtures/n) for n in ('ca.pem','tsa.pem'))
    with tempfile.TemporaryDirectory() as d:
        p=Path(d); (p/'empty').mkdir()
        for n,b in [('ca.pem',ca),('tsa.pem',tsa),('query',qraw),('response',rraw)]: (p/n).write_bytes(b)
        env=dict(os.environ,SSL_CERT_FILE=str(p/'ca.pem'),SSL_CERT_DIR=str(p/'empty'),LC_ALL='C',TZ='UTC')
        # Fixed historical validation epoch: reproduction, not trusted current time.
        if command(['ts','-reply','-in',str(p/'response'),'-token_out','-out',str(p/'token')],env).returncode: return False
        if command(['cms','-verify','-binary','-inform','DER','-in',str(p/'token'),'-noverify','-nointern','-certfile',str(p/'tsa.pem'),'-out',str(p/'info')],env).returncode: return False
        r=command(['ts','-verify','-in',str(p/'response'),'-queryfile',str(p/'query'),'-CAfile',str(p/'ca.pem'),'-CApath',str(p/'empty'),'-untrusted',str(p/'tsa.pem'),'-attime','1795478400'],env)
        return r.returncode==0 and b'Verification: OK' in r.stdout

def consume(db,fixtures,qraw,rraw,crash='none'):
    if os.getuid()!=CUSTODIAN: return 'HOLD_WRONG_UID'
    if not (0<len(qraw)<=4096 and 0<len(rraw)<=65536): return 'HOLD_SIZE'
    qhash,rhash=digest(qraw),digest(rraw)
    # Exactly two enrolled historical requests; no caller-provided scope, key, or nonce.
    names=[n for n in ('a.tsq','b.tsq') if PINS[n]==qhash]
    if len(names)!=1: return 'HOLD_UNKNOWN_REQUEST'
    try:
        qpath=fixtures/names[0]
        if pinned(qpath)!=qraw: return 'HOLD_REQUEST_PIN'
        n=nonce(qpath)
        with connect(db) as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT query_hash,response_hash FROM challenges WHERE scope=? AND nonce=?',(SCOPE,n)).fetchone()
            if row is None or row[0]!=qhash: return 'HOLD_NOT_ENROLLED'
            if row[1] is not None:
                return 'HOLD_ALREADY_CONSUMED:'+row[1]
            if not verify(fixtures,qraw,rraw): return 'HOLD_INVALID_RESPONSE'
            cursor=c.execute('UPDATE challenges SET response_hash=? WHERE scope=? AND nonce=? AND response_hash IS NULL',(rhash,SCOPE,n))
            if cursor.rowcount!=1: return 'HOLD_CONFLICT'
            if crash=='before': os._exit(75)
            c.commit()
            if crash=='after': os._exit(76)
            return 'CONSUMED_RESEARCH_ONLY:'+rhash
    except (sqlite3.Error,OSError,ValueError,subprocess.SubprocessError): return 'HOLD_LEDGER_OR_VERIFIER_UNAVAILABLE'

if __name__=='__main__':
    db,fixtures=map(Path,sys.argv[1:3])
    if sys.argv[3]=='init': initialize(db,fixtures); print('INITIALIZED')
    else:
        q,r=map(Path,sys.argv[4:6])
        with q.open('rb') as f: qb=f.read(4097)
        with r.open('rb') as f: rb=f.read(65537)
        print(consume(db,fixtures,qb,rb,sys.argv[6] if len(sys.argv)>6 else 'none'))
