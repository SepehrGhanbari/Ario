"""R22.16 research only. Explicit hypothetical clock bounds, not time custody."""
import base64
import hashlib
import re
import sys
import zipfile
from pathlib import Path
from dataclasses import dataclass
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

LOG = bytes.fromhex('4644af2abd40f4895a003bca350f9d5912ab301a49c77f13e5b6d905c20a5fe6')
KEYS = tuple(bytes.fromhex(k) for k in ('1c25f8a44c635457e2e391d1efbca7d4c2951a0aef06225a881e46b98962ac6c','28c92a5a3a054d317c86fc2eeb6a7ab2054d6217100d0be67ded5b74323c5806','f4855a0f46e8a3e23bb40faf260ee57ab8a18249fa402f2ca2d28a60e1a3130e'))
sha = lambda b: hashlib.sha256(b).hexdigest()
PINS = ('337fc0e36441c0eb3d4ebeb1736cb83bbea8cb958dd8b5aba846a8c1230fc16d','652ff3f19ce4470b82aaf70acf9c2f6e4b0f3aa00a7f7c17a0adc916ba0fd56e')
HEADS = ('4b03a31a01537968b0636ab18d21d982266cda2b9ce8d82b6e663fd79e8cbb4b','c0c0f5b49ff20a77b36a206d52fc784ef4aa603d7543d4e43a5b345e4c7b3f6b')

@dataclass(frozen=True)
class Head:
    size: int
    root: str
    times: tuple


def verify(raw):
    if type(raw) is not bytes or len(raw)>8192 or not raw.endswith(b'\n'):
        raise ValueError('body')
    lines=raw.decode('ascii').splitlines()
    m=re.fullmatch(r'size=(0|[1-9][0-9]{0,19})',lines[0])
    r=re.fullmatch(r'root_hash=([0-9a-f]{64})',lines[1])
    s=re.fullmatch(r'signature=([0-9a-f]{128})',lines[2])
    if not (m and r and s): raise ValueError('head')
    n=int(m[1]); root=r[1]
    if n>=2**64: raise ValueError('size')
    body=f'sigsum.org/v1/tree/{sha(LOG)}\n{n}\n{base64.b64encode(bytes.fromhex(root)).decode()}\n'.encode()
    Ed25519PublicKey.from_public_bytes(LOG).verify(bytes.fromhex(s[1]),body)
    keys={sha(k):k for k in KEYS}; seen=set(); times=[]
    for line in lines[3:]:
        v=re.fullmatch(r'cosignature=([0-9a-f]{64}) (0|[1-9][0-9]{0,19}) ([0-9a-f]{128})',line)
        if not v or v[1] in seen or int(v[2])>=2**64: raise ValueError('cosignature')
        seen.add(v[1]); t=int(v[2])
        if v[1] in keys:
            try:
                Ed25519PublicKey.from_public_bytes(keys[v[1]]).verify(bytes.fromhex(v[3]),f'cosignature/v1\ntime {t}\n'.encode()+body)
            except InvalidSignature: continue
            times.append((v[1],t))
    if len(times)<2: raise ValueError('quorum')
    return Head(n,root,tuple(sorted(times)))


def assess(raws, bounds, max_age=5, future=0):
    # bounds is an assumed independent clock interval, never obtained from the host clock.
    # Caller-supplied test bounds are not a trust credential. No acceptance or floor update.
    if len(raws)!=2 or any(r is None for r in raws): return 'HOLD_SOURCE_UNAVAILABLE'
    try: heads=[verify(r) for r in raws]
    except (ValueError,InvalidSignature,IndexError,UnicodeError): return 'HOLD_AUTHENTICATION'
    if (heads[0].size,heads[0].root)!=(heads[1].size,heads[1].root): return 'HOLD_SOURCE_DISAGREEMENT'
    if bounds is None: return 'HOLD_CLOCK_UNKNOWN'
    if (type(bounds) is not tuple or len(bounds)!=2 or any(type(v) is not int or not 0<=v<2**63 for v in bounds) or bounds[0]>bounds[1] or type(max_age) is not int or not 0<=max_age<=3600 or type(future) is not int or not 0<=future<=60): return 'HOLD_CLOCK_INVALID'
    lo,hi=bounds
    # Require same two pinned signers to be in-window in BOTH responses.
    valid=[{k for k,t in h.times if hi-max_age<=t<=lo+future} for h in heads]
    if len(valid[0]&valid[1])<2: return 'HOLD_TIME_WINDOW_NOT_ESTABLISHED'
    return 'MATCH_TIME_WINDOW_NOT_FRESHNESS'


def load(path,i):
    raw=path.read_bytes()
    if sha(raw)!=PINS[i]: raise ValueError('archive pin')
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None: raise ValueError('CRC')
        head=z.read('envelope.json.proof').split(b'\n\n')[1]+b'\n'
    if sha(head)!=HEADS[i]: raise ValueError('head pin')
    return head


def main():
    old,new=[load(Path(p),i) for i,p in enumerate(sys.argv[1:3])]
    a,b=verify(old),verify(new)
    assert a.size==281586 and b.size==281587
    assert len(a.times)==len(b.times)==3
    t,u=a.times[0][1],b.times[0][1]
    assert all(x[1]==t for x in a.times) and all(x[1]==u for x in b.times) and u-t==10
    print('VERIFIED_PINNED_WITNESS_TIMES',t,u,'3/3 each; log signatures valid')
    ok='MATCH_TIME_WINDOW_NOT_FRESHNESS'; hold='HOLD_TIME_WINDOW_NOT_ESTABLISHED'
    bad=old.replace(str(t).encode(),str(u).encode())
    cases=[
      ('old_at_new_time',(old,old),(u,u),5,hold),
      ('new_at_new_time',(new,new),(u,u),5,ok),
      ('old_with_rolled_back_clock_RED',(old,old),(t,t),5,ok),
      ('old_no_clock',(old,old),None,5,'HOLD_CLOCK_UNKNOWN'),
      ('new_no_clock',(new,new),None,5,'HOLD_CLOCK_UNKNOWN'),
      ('old_inside_wide_window_RED',(old,old),(u,u),60,ok),
      ('new_future',(new,new),(t,t),5,hold),
      ('uncertain_clock',(new,new),(u,u+6),5,hold),
      ('bounded_clock',(new,new),(u,u+3),5,ok),
      ('source_disagreement',(old,new),(u,u),5,'HOLD_SOURCE_DISAGREEMENT'),
      ('source_outage',(new,None),(u,u),5,'HOLD_SOURCE_UNAVAILABLE'),
      ('tampered_time',(bad,bad),(u,u),5,'HOLD_AUTHENTICATION'),
      ('malformed',(b'bad\n',new),(u,u),5,'HOLD_AUTHENTICATION'),
      ('invalid_interval',(new,new),(u+1,u),5,'HOLD_CLOCK_INVALID'),
      ('bool_clock',(new,new),(True,u),5,'HOLD_CLOCK_INVALID'),
      ('same_response_twice_RED',(old,old),(t,t),5,ok),
      ('window_boundary',(old,old),(t+5,t+5),5,ok),
      ('window_past_boundary',(old,old),(t+6,t+6),5,hold),
    ]
    for name,raws,clock,age,want in cases:
        got=assess(raws,clock,age)
        if got!=want: raise AssertionError((name,got,want))
        print(name,got,'PASS')
    print('18/18 PASS; CLOCK_AND_SOURCE_INDEPENDENCE=NOT_ESTABLISHED; FRESHNESS=UNKNOWN; TRUST=NO_GO; PRODUCTION=NO_GO')

if __name__=='__main__': main()
