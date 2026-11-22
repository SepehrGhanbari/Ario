"""R63 G6 research-only pinned historical floor -> one-event extension gate.

This module tests chain extension anchored to a frozen *synthetic* phone-noted
minimum seq=3. It never advances the phone floor, signs, or activates trust.
A publisher who controls this code AND its pin can fake a verdict: genuine
independent verification requires a read-only verifier outside publisher control.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

PINNED_EPOCH='research_nov_2026_no_signer'
PINNED_SEQ=3
PINNED_HEAD='6e1d74f7860e0173b9b049487a6a89428439a987809cf363fa27503ae0b06ea1'
FROZEN_V9_SHA='c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd'
G4_RAW_V1_SHA='2e1918b2c890dcf337b314692d7201a8cbdc223046322ea45953615de3144ec8'
G4_RAW_V2_SHA='9c221fa381fed4cfecc71d89e285bdb8ecc0995bfb49f8572a3177bbd4c66ac0'
REKOR_HISTORICAL_GLOBAL_INDEX=4033996846
CANDIDATE_NONCE='d'*64
CANDIDATE_ID='4'*64
EXPECTED_PIN_FILE='G5-PHONE-PINNED-MINIMUM-SEQ3.json'


def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def frozen_module(source:Path):
    if sha(source.read_bytes())!=FROZEN_V9_SHA:
        raise ValueError('HOLD_FROZEN_V9_SOURCE_CHANGED')
    spec=importlib.util.spec_from_file_location('ario_g6_frozen_sidecar',source)
    mod=importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod


def pin_check(reference:dict|None)->str:
    if type(reference) is not dict:
        return 'HOLD_PHONE_REFERENCE_NOT_PROVIDED'
    # Refuse lower / alternate floor even if publisher passes a self-written pin.
    if (set(reference)!={'epoch','seq','head'} or
        reference.get('epoch')!=PINNED_EPOCH or
        type(reference.get('seq')) is not int or
        reference['seq']!=PINNED_SEQ or
        reference.get('head')!=PINNED_HEAD):
        return 'HOLD_PIN_REBOUND_OR_DOWNGRADED'
    return 'PIN_FIELDS_MATCH_STATIC_RESEARCH_BASELINE'


def audited_journals(v1:bytes,v2:bytes):
    """Recompute canonical seq/prev/nonce/R60 commitments; no executable inputs."""
    if type(v1) is not bytes or type(v2) is not bytes:
        raise ValueError('HOLD_WRONG_INPUT_TYPE')
    if not v1.endswith(b'\n') or not v2.endswith(b'\n'):
        raise ValueError('HOLD_BAD_LINE_ENDING')
    def parse(raw):
        lines=raw.splitlines()
        if len(lines)>20:raise ValueError('HOLD_TOO_MANY_EVENTS')
        out=[]
        for b in lines:
            if len(b)>8192:raise ValueError('HOLD_OVERSIZED_EVENT')
            try:o=json.loads(b.decode('ascii'))
            except (UnicodeError,ValueError):raise ValueError('HOLD_INVALID_JSON')
            if json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')!=b:
                raise ValueError('HOLD_NONCANONICAL')
            out.append(o)
        return out
    a=parse(v1);b=parse(v2)
    if len(a)!=len(b):raise ValueError('HOLD_SPLIT_V1_V2')
    prefix_head=None
    prev='0'*64
    pairs=[]
    seen_nonce=set();seen_id=set()
    def snapshot(ps):
        return sha(json.dumps(sorted(ps,key=lambda x:x[0]),sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())
    for i,e in enumerate(b,1):
        if type(e) is not dict or set(e)!= {'version','seq','prev','nonce','id','before','after','hash'}:
            raise ValueError('HOLD_V2_SCHEMA')
        n,k=e['nonce'],e['id']
        if (e['version']!='ARIO_R63_SPEND_V2_RESEARCH' or type(e['seq']) is not int or e['seq']!=i
                or e['prev']!=prev or type(n) is not str or type(k) is not str
                or re.fullmatch('[a-f0-9]{64}',n) is None or re.fullmatch('[a-f0-9]{64}',k) is None):
            raise ValueError('HOLD_V2_CHAIN')
        if n in seen_nonce or k in seen_id or a[i-1]!=[n,k]:
            raise ValueError('HOLD_V1_V2_OR_DUPLICATE')
        if e['before']!=snapshot(pairs) or e['after']!=snapshot(pairs+[[n,k]]):
            raise ValueError('HOLD_R60_COMMITMENT')
        body={key:val for key,val in e.items() if key!='hash'}
        actual=sha(b'ARIO-R63/spend/v2\0'+json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii'))
        if actual!=e['hash']:raise ValueError('HOLD_V2_HASH')
        pairs.append([n,k]);seen_nonce.add(n);seen_id.add(k)
        prev=actual
        if i==PINNED_SEQ:prefix_head=actual
    return {'seq':len(b),'head':prev,'prefix_head':prefix_head,'v1_sha256':sha(v1),'v2_sha256':sha(v2)}


def assess(v1:bytes,v2:bytes,reference:dict|None,*,operator_reports_phone_is_separate:bool=False):
    """Never uses candidate to choose/advance trusted phone minimum."""
    p=pin_check(reference)
    if p!='PIN_FIELDS_MATCH_STATIC_RESEARCH_BASELINE':return p
    if not operator_reports_phone_is_separate:return 'HOLD_PHONE_SEPARATION_NOT_ATTESTED'
    try:state=audited_journals(v1,v2)
    except (ValueError,TypeError,RecursionError,OverflowError):return 'HOLD_LOCAL_JOURNAL_INVALID'
    if state['seq']<PINNED_SEQ:return 'HOLD_ROLLBACK'
    if state['prefix_head']!=PINNED_HEAD:return 'HOLD_FORK'
    if state['seq']==PINNED_SEQ:return 'PINNED_MINIMUM_PRESENT_NO_NEW_EVENT'
    if state['seq']!=PINNED_SEQ+1:return 'HOLD_UNREVIEWED_MULTI_STEP_ADVANCE'
    return 'CANDIDATE_EXTENDS_PINNED_SEQ3_ONLY_NOT_APPROVED_AS_LATEST'


def build_candidate(v1:bytes,v2:bytes,source:Path):
    if sha(v1)!=G4_RAW_V1_SHA or sha(v2)!=G4_RAW_V2_SHA:
        raise ValueError('HOLD_G4_ORIGINAL_BYTES_CHANGED')
    baseline=audited_journals(v1,v2)
    if baseline['seq']!=PINNED_SEQ or baseline['head']!=PINNED_HEAD:
        raise ValueError('HOLD_G4_SEQ3_NOT_PINNED')
    mod=frozen_module(source)
    raw,status=mod.append(v2,CANDIDATE_NONCE,CANDIDATE_ID)
    if status!='NEW_NEEDS_DURABLE_APPEND' or not raw.startswith(v2) or raw==v2:
        raise ValueError('HOLD_FROZEN_SIDECAR_APPEND_FAILURE')
    v1_next=v1+mod.canonical([CANDIDATE_NONCE,CANDIDATE_ID])+b'\n'
    return v1_next,raw


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--v1',type=Path,required=True)
    ap.add_argument('--v2',type=Path,required=True)
    ap.add_argument('--pin',type=Path,required=True)
    ap.add_argument('--operator-reports-phone-separate',action='store_true')
    ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    # The passed file is treated as a user assertion; it NEVER supersedes
    # the compiled and reviewed baseline seq3/head, and is NOT phone-attested.
    try:ref=json.loads(args.pin.read_text(encoding='utf-8'))
    except (ValueError,OSError,UnicodeError):ref=None
    ans=assess(args.v1.read_bytes(),args.v2.read_bytes(),ref,
               operator_reports_phone_is_separate=args.operator_reports_phone_separate)
    result={
        'schema':'ARIO_R63_G6_EXTENSION_VERDICT_V1','verdict':ans,
        'historical_minimum':{'epoch':PINNED_EPOCH,'seq':PINNED_SEQ,'head':PINNED_HEAD},
        'phone_pin_not_read_directly':True,'phone_minimum_unchanged':True,
        'phone_separate_access':'FOUNDER_REPORTED' if args.operator_reports_phone_separate else 'NOT_ESTABLISHED',
        'publisher_controls_code_and_local_inputs':True,
        'verifier_outside_publisher_admin':'NOT_ESTABLISHED',
        'automatic_remote_latest':'NOT_ESTABLISHED',
        'authority':'NONE','signer':'NOT_TOUCHED','real_ario_keys':'NOT_USED',
        'trust_activation':'NO_GO','production':'NO_GO',
    }
    if args.out:
        if args.out.exists():raise SystemExit('REFUSE_OVERWRITE_EVIDENCE')
        args.out.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,sort_keys=True))
    raise SystemExit(0 if ans.startswith('CANDIDATE_EXTENDS_') or ans.startswith('PINNED_MINIMUM_PRESENT_') else 2)
if __name__=='__main__':main()