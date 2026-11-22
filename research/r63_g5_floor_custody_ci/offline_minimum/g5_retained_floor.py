"""Research-only G5: independently PINNED historical minimum, not latest authority.

Verifies actual canonical frozen V9-format V2 and V1 journals. The seq3 pin and
checkpoint digest are fixed constants from the previously Sigstore-verified
synthetic historical checkpoint; they are NEVER learned from the suspect journal.

Threat precondition: verifier code/pin lives outside the publisher's write domain.
This module cannot enforce that physical separation or prove newest remote head.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

DOMAIN=b'ARIO-R63/spend/v2\0'
VERSION='ARIO_R63_SPEND_V2_RESEARCH'
ZERO='0'*64
PINNED_EPOCH='research_nov_2026_no_signer'
PINNED_SEQ=3
PINNED_HEAD='6e1d74f7860e0173b9b049487a6a89428439a987809cf363fa27503ae0b06ea1'
PINNED_CHECKPOINT_SHA256='e218d3d05a613024eb26a8e67052aeb61d77d14d6be8ecdede2ed5c27c1a78db'
PINNED_V9_SOURCE_SHA256='c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd'
REKOR_INDEX=4033996846


def canon(value:object)->bytes:
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')

def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def valid_hash(x):
    return type(x) is str and re.fullmatch('[0-9a-f]{64}',x) is not None

def rows(raw:bytes):
    if type(raw) is not bytes or (raw and not raw.endswith(b'\n')):
        raise ValueError('BAD_LINE_BOUNDARY')
    arr=raw.split(b'\n')[:-1] if raw else []
    if len(arr)>100000:raise ValueError('TOO_MANY_ROWS')
    out=[]
    for line in arr:
        if not line or len(line)>8192:raise ValueError('BAD_ROW_LENGTH')
        try:
            v=json.loads(line.decode('ascii'))
            if canon(v)!=line: raise ValueError('NONCANONICAL')
        except (ValueError,UnicodeError,TypeError,OverflowError,RecursionError) as e:raise ValueError('BAD_ROW') from e
        out.append(v)
    return out

def snapshot(pairs):
    return sha(canon(sorted([list(x) for x in pairs],key=lambda p:p[0])))

def verify_local(v1:bytes,v2:bytes):
    """Return seq,head,prefix_head if two local canonical journals are coherent."""
    pairs=[]
    prev=ZERO
    prefix=None
    events=rows(v2)
    local_v1=rows(v1)
    if len(local_v1)!=len(events):raise ValueError('V1_V2_COUNT_SPLIT')
    for i,e in enumerate(events,1):
        if type(e) is not dict or set(e)!={'version','seq','prev','nonce','id','before','after','hash'}:
            raise ValueError('BAD_V2_FIELDS')
        n,k=e['nonce'],e['id']
        if e['version']!=VERSION or not valid_hash(n) or not valid_hash(k):
            raise ValueError('BAD_V2_ITEM')
        if type(e['seq']) is not int or e['seq']!=i or e['prev']!=prev:
            raise ValueError('BAD_V2_LINK')
        if any(n==p[0] or k==p[1] for p in pairs):
            raise ValueError('V2_DUPLICATE')
        if local_v1[i-1]!=[n,k]:
            raise ValueError('V1_V2_MISMATCH')
        body={k:v for k,v in e.items() if k!='hash'}
        if e['before']!=snapshot(pairs) or e['after']!=snapshot(pairs+[[n,k]]):
            raise ValueError('BAD_R60_COMMITMENT')
        actual=sha(DOMAIN+canon(body))
        if e['hash']!=actual:raise ValueError('BAD_V2_HASH')
        pairs.append([n,k]);prev=actual
        if i==PINNED_SEQ:prefix=prev
    return len(events),prev,prefix

def pinned_checkpoint_ok(data:bytes):
    if sha(data)!=PINNED_CHECKPOINT_SHA256:return False
    try:r=json.loads(data.decode('ascii'))
    except (ValueError,UnicodeError):return False
    return (type(r) is dict and r.get('epoch')==PINNED_EPOCH and
            type(r.get('seq')) is int and r['seq']==PINNED_SEQ and
            r.get('head')==PINNED_HEAD and
            r.get('frozen_v9_v2_sha256')==PINNED_V9_SOURCE_SHA256 and
            r.get('test_only') is True and r.get('no_real_ario_keys') is True and
            r.get('production')=='NO_GO' and r.get('authority')=='NO_TRUST_ACTIVATION')

def verdict(v1:bytes,v2:bytes,checkpoint:bytes,*,independent_pin_retained:bool):
    if not independent_pin_retained:return 'HOLD_INDEPENDENT_PIN_NOT_ESTABLISHED'
    if not pinned_checkpoint_ok(checkpoint):return 'HOLD_BAD_PINNED_CHECKPOINT'
    try:seq,head,prefix=verify_local(v1,v2)
    except (ValueError,TypeError,OverflowError,UnicodeError,RecursionError):
        return 'HOLD_LOCAL_JOURNAL_INVALID'
    if seq<PINNED_SEQ:return 'HOLD_ROLLBACK'
    if prefix!=PINNED_HEAD:return 'HOLD_FORK'
    return 'CONSISTENT_WITH_EXTERNAL_HISTORICAL_MINIMUM_ONLY_NOT_LATEST'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--v1',required=True,type=Path);p.add_argument('--v2',required=True,type=Path)
    p.add_argument('--checkpoint',required=True,type=Path)
    p.add_argument('--independent-pin-confirmed',action='store_true',help='Only when verifier + checkpoint actually retained outside publisher write authority')
    a=p.parse_args()
    result=verdict(a.v1.read_bytes(),a.v2.read_bytes(),a.checkpoint.read_bytes(),
                   independent_pin_retained=a.independent_pin_confirmed)
    print(result)
    # Never auto-execute actions or bless an actual Ario signer.
    raise SystemExit(0 if result=='CONSISTENT_WITH_EXTERNAL_HISTORICAL_MINIMUM_ONLY_NOT_LATEST' else 2)
if __name__=='__main__':main()