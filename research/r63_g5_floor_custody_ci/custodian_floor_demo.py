"""R63 G5: signed latest-floor and rollback falsification model.

SIMULATED remote custodian only: SQLite files and Ed25519 key live under test
controller's OS administrator; independent administrative custody NOT PROVED.
No Ario key, production receipt, signer, remote upload, or trust activation.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib,json,re,sqlite3
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

DOMAIN='ARIO-R63/G5/EXTERNAL-FLOOR-RESEARCH/v1'
PIN='c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd'

def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def sha(data):return hashlib.sha256(data).hexdigest()
def ishash(x):return type(x) is str and re.fullmatch('[0-9a-f]{64}',x) is not None

def genesis():return '0'*64

@dataclass(frozen=True)
class Receipt:
    body:dict
    signature:bytes
    def json(self):return {'body':self.body,'signature_hex':self.signature.hex()}

class SimulatedCustodian:
    """Counterparty API & storage; not an actual independent service."""
    def __init__(self,db:Path,private_key:Ed25519PrivateKey):
        self.db=db;self.key=private_key
        conn=sqlite3.connect(db)
        try:
            conn.execute('CREATE TABLE IF NOT EXISTS latest (id INTEGER PRIMARY KEY CHECK(id=1), epoch TEXT, seq INTEGER, head TEXT, receipt_hash TEXT)')
            conn.execute('CREATE TABLE IF NOT EXISTS immutable_log (row INTEGER PRIMARY KEY AUTOINCREMENT, epoch TEXT, seq INTEGER, head TEXT, receipt_hash TEXT)')
            conn.commit()
        finally:conn.close()
    @property
    def pub(self):return self.key.public_key()
    def _conn(self):
        c=sqlite3.connect(self.db,timeout=5,isolation_level='IMMEDIATE')
        c.execute('BEGIN IMMEDIATE')
        return c
    def append(self,epoch:str,seq:int,head:str,*,expected_prev:str):
        if not re.fullmatch('[A-Za-z0-9._-]{8,80}',epoch) or type(seq) is not int or seq<1 or not ishash(head) or not ishash(expected_prev):
            raise ValueError('INVALID_G5_FLOOR')
        conn=self._conn()
        try:
            prev=conn.execute('SELECT epoch,seq,head,receipt_hash FROM latest WHERE id=1').fetchone()
            if prev is None:
                if seq!=1 or expected_prev!=genesis():raise ValueError('HOLD_GENESIS_NOT_INDEPENDENTLY_APPROVED')
            else:
                if prev[0]!=epoch or seq!=prev[1]+1 or expected_prev!=prev[3]:
                    raise ValueError('HOLD_NONMONOTONIC_OR_FORK_OR_GAP')
            body={'domain':DOMAIN,'epoch':epoch,'seq':seq,'head':head,'previous_receipt':expected_prev}
            signed=self.key.sign(canonical(body));digest=sha(canonical(body)+signed)
            conn.execute('INSERT INTO immutable_log(epoch,seq,head,receipt_hash) VALUES(?,?,?,?)',(epoch,seq,head,digest))
            conn.execute('INSERT OR REPLACE INTO latest(id,epoch,seq,head,receipt_hash) VALUES(1,?,?,?,?)',(epoch,seq,head,digest))
            conn.commit();return Receipt(body,signed)
        except:conn.rollback();raise
        finally:conn.close()
    def latest(self):
        conn=sqlite3.connect(self.db)
        try:return conn.execute('SELECT epoch,seq,head,receipt_hash FROM latest WHERE id=1').fetchone()
        finally:conn.close()

def verify_latest(journal:bytes,receipt:Receipt,public_key:Ed25519PublicKey,remote_latest,local_min_seq:int,epoch:str):
    """Fail closed if missing remote state; trust of its completeness NOT established."""
    if remote_latest is None:return 'HOLD_REMOTE_LATEST_UNAVAILABLE'
    body=receipt.body
    if set(body)!={'domain','epoch','seq','head','previous_receipt'} or body['domain']!=DOMAIN or body['epoch']!=epoch:
        return 'HOLD_BAD_FLOOR_ENVELOPE'
    try:public_key.verify(receipt.signature,canonical(body))
    except (InvalidSignature,TypeError,ValueError):return 'HOLD_BAD_CUSTODIAN_SIGNATURE'
    if body['seq']<local_min_seq:return 'HOLD_LOCAL_VERIFIER_FLOOR_REGRESSED'
    if not (body['seq']==remote_latest[1] and body['head']==remote_latest[2] and body['epoch']==remote_latest[0]):
        return 'HOLD_NOT_LAST_EXTERNAL_STATE'
    if sha(canonical(body)+receipt.signature)!=remote_latest[3]:return 'HOLD_REMOTE_RECEIPT_MISMATCH'
    if not ishash(body['head']) or type(body['seq']) is not int:return 'HOLD_BAD_FLOOR_FIELDS'
    # import pinned original V9 V2 only for local *research*; must be hashed.
    import importlib.util
    fp=Path(__file__).resolve().parent/'spend_chain_v2.py'
    if sha(fp.read_bytes())!=PIN:raise RuntimeError('PIN_MISMATCH_RESEARCH_ONLY')
    spec=importlib.util.spec_from_file_location('g5_frozen_v2',fp)
    mod=importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    try:mod.review(journal,external_anchor=(body['seq'],body['head']))
    except (ValueError,RuntimeError):return 'HOLD_ROLLBACK_OR_FORK'
    return 'EXTERNALLY_CONSISTENT_SIMULATION_ONLY_NO_SIGNING'
