"""R22.19 archived challenge lifecycle lab. No live issuance or authority."""
import os, sqlite3, sys, subprocess
from pathlib import Path
from nonce_ledger import CUSTODIAN, PINS, digest, pinned, nonce, verify, connect


def operate(db, fixtures, op, expected, name='', response=None, crash='none'):
    if os.getuid()!=CUSTODIAN: return 'HOLD_WRONG_UID'
    try:
        if op=='init':
            if db.exists(): return 'HOLD_ALREADY_INITIALIZED'
            with connect(db,True) as c:
                c.execute('BEGIN IMMEDIATE')
                c.execute('CREATE TABLE session (id INTEGER PRIMARY KEY CHECK(id=1), epoch INTEGER NOT NULL CHECK(epoch>0))')
                c.execute('INSERT INTO session VALUES(1,1)')
                c.execute("CREATE TABLE challenges (nonce TEXT PRIMARY KEY, query_hash TEXT UNIQUE NOT NULL, epoch INTEGER NOT NULL, state TEXT NOT NULL CHECK(state IN ('ISSUED','CONSUMED','ABANDONED')), response_hash TEXT, CHECK((state='CONSUMED')=(response_hash IS NOT NULL)))")
                c.commit()
            return 'INITIALIZED:1'
        with connect(db) as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT epoch FROM session WHERE id=1').fetchone()
            if not row: return 'HOLD_LEDGER_INVALID'
            epoch=row[0]
            if expected!=epoch: return 'HOLD_EPOCH_MISMATCH'
            if op=='rotate':
                if epoch>=2**63-1: return 'HOLD_EPOCH_EXHAUSTED'
                c.execute("UPDATE challenges SET state='ABANDONED' WHERE state='ISSUED'")
                c.execute('UPDATE session SET epoch=? WHERE id=1',(epoch+1,))
                result='ROTATED:'+str(epoch+1)
            else:
                if name not in ('a.tsq','b.tsq'): return 'HOLD_UNKNOWN_REQUEST'
                qpath=fixtures/name; qraw=pinned(qpath); qhash=digest(qraw); n=nonce(qpath)
                row=c.execute('SELECT query_hash,epoch,state,response_hash FROM challenges WHERE nonce=?',(n,)).fetchone()
                if op=='issue':
                    if row is not None: return 'HOLD_NONCE_ALREADY_ENROLLED'
                    c.execute("INSERT INTO challenges VALUES(?,?,?,'ISSUED',NULL)",(n,qhash,epoch))
                    result='ISSUED:'+str(epoch)
                else:
                    if row is None or row[0]!=qhash: return 'HOLD_NOT_ENROLLED'
                    if row[2]!='ISSUED': return 'HOLD_'+row[2]
                    if row[1]!=epoch: return 'HOLD_STALE_CHALLENGE'
                    if op=='abandon':
                        c.execute("UPDATE challenges SET state='ABANDONED' WHERE nonce=?",(n,))
                        result='ABANDONED'
                    elif op=='consume':
                        if response is None or not 0<len(response)<=65536: return 'HOLD_SIZE'
                        if not verify(fixtures,qraw,response): return 'HOLD_INVALID_RESPONSE'
                        c.execute("UPDATE challenges SET state='CONSUMED',response_hash=? WHERE nonce=?",(digest(response),n))
                        result='CONSUMED_RESEARCH_ONLY'
                    else: return 'HOLD_UNKNOWN_OPERATION'
            if crash=='before': os._exit(75)
            c.commit()
            if crash=='after': os._exit(76)
            return result
    except (OSError,ValueError,sqlite3.Error,subprocess.SubprocessError): return 'HOLD_LEDGER_OR_VERIFIER_UNAVAILABLE'


if __name__=='__main__':
    db,fixtures=map(Path,sys.argv[1:3]); op=sys.argv[3]; expected=int(sys.argv[4]); name=sys.argv[5]; path=sys.argv[6]
    raw=None
    if path!='-':
        with open(path,'rb') as f: raw=f.read(65537)
    print(operate(db,fixtures,op,expected,name,raw,sys.argv[7]))
