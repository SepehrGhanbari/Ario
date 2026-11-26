#!/usr/bin/env python3
"""W21 untrusted HTTP read-only observer; never obtains trust roots from server.

Only loopback permitted in THIS lab. Real remote transport, trusted latest
high-water custody and native C2SP witness are intentionally NOT implemented.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from w20_independent_monitor import evaluate_bundle, _check_head, ORIGIN, result

MAX_RESPONSE=49152

class _NeverFollowRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A loopback-only URL whitelist is meaningless if a localhost HTTP
        # response can redirect the client to a different origin. Fail closed.
        return None

_NO_REDIRECT_OPENER = build_opener(_NeverFollowRedirect)


def _no_dup(pairs):
    out={}
    for k,v in pairs:
        if k in out:
            raise ValueError('DUPLICATE_JSON_KEY')
        out[k]=v
    return out


def _fetch(base:str, path:str):
    req=Request(base+path,headers={'Accept':'application/json','Cache-Control':'no-store'},method='GET')
    with _NO_REDIRECT_OPENER.open(req,timeout=2) as resp:
        if resp.status!=200 or resp.headers.get_content_type()!='application/json':
            raise ValueError('BAD_HTTP_STATUS_OR_CONTENT_TYPE')
        data=resp.read(MAX_RESPONSE+1)
        if len(data)>MAX_RESPONSE:
            raise ValueError('RESPONSE_TOO_LARGE')
    return json.loads(data.decode('utf8'),object_pairs_hook=_no_dup,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError('INVALID_NONFINITE_JSON')))


def observe(base:str,*,pinned_key:str|None,prior:dict|None,highwater:dict|None):
    try:
        parsed=urlsplit(base)
        port=parsed.port  # malformed or out-of-range port may raise ValueError
    except ValueError:
        return result('HOLD_UNCERTAIN','NON_LOOPBACK_OR_INVALID_URL')
    if (parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or parsed.username is not None
            or parsed.password is not None or parsed.path not in ('','/') or parsed.query
            or parsed.fragment or port is None or port <= 0):
        return result('HOLD_UNCERTAIN','NON_LOOPBACK_OR_INVALID_URL')
    base=f'http://127.0.0.1:{port}'
    if pinned_key is None:
        return result('HOLD_UNCERTAIN','NO_OUT_OF_BAND_KEY_PIN')
    if prior is None:
        return result('HOLD_UNCERTAIN','NO_RETAINED_PRIOR_CHECKPOINT')
    if _check_head(prior,pinned_key,ORIGIN) is None:
        return result('HOLD_UNCERTAIN','UNTRUSTED_PRIOR_INVALID')
    try:
        cp=_fetch(base,'/v0/checkpoint')
        if type(cp) is not dict or set(cp)!={'schema','checkpoint'} or cp['schema']!='ARIO_W21_SYNTHETIC_HTTP_CHECKPOINT_V1':
            return result('HOLD_UNCERTAIN','CHECKPOINT_WIRE_SCHEMA')
        head=cp['checkpoint']
        body=_check_head(head,pinned_key,ORIGIN)
        if body is None:
            return result('DENY','HTTP_HEAD_SIGNATURE_INVALID')
        size=body['size']
        oldsize=prior['body']['size']
        events=_fetch(base,'/v0/events')
        if type(events) is not dict or set(events)!={'schema','events','inclusions'} or events['schema']!='ARIO_W21_SYNTHETIC_HTTP_EVENTS_V1':
            return result('HOLD_UNCERTAIN','EVENTS_WIRE_SCHEMA')
        proof=_fetch(base,f'/v0/consistency?old={oldsize}&new={size}')
        if type(proof) is not dict or set(proof)!={'schema','old','new','proof'} or proof['schema']!='ARIO_W21_SYNTHETIC_HTTP_CONSISTENCY_V1' or proof['old']!=oldsize or proof['new']!=size:
            return result('HOLD_UNCERTAIN','CONSISTENCY_WIRE_SCHEMA')
    except (OSError,ValueError,KeyError,UnicodeDecodeError,OverflowError,TypeError) as e:
        # Never claim either success or valid fork without actual signed inputs.
        return result('HOLD_UNCERTAIN','REMOTE_LOOKUP_INVALID_OR_UNAVAILABLE')
    bundle={'schema':'ARIO_W20_NATIVE_LOG_LAB_FIXTURE_V1',
            'old_checkpoint':prior,'new_checkpoint':head,
            'consistency_proof':proof['proof'], 'events':events['events'],'inclusions':events['inclusions']}
    verdict=evaluate_bundle(bundle,pinned_key,known_prior=prior)
    if verdict['verdict']!='HISTORICAL_CONSISTENT':
        return verdict
    if highwater is None:
        z=result('HOLD_UNCERTAIN','NO_SEPARATELY_RETAINED_HIGHWATER')
        z['read_only_preview_valid']=True
        return z
    hb=_check_head(highwater,pinned_key,ORIGIN)
    if hb is None:
        return result('HOLD_UNCERTAIN','HIGHWATER_INVALID_OR_UNTRUSTED')
    if size<hb['size']:
        return result('DENY','HTTP_ROLLBACK_BELOW_PINNED_HIGHWATER')
    if size>hb['size']:
        return result('HOLD_UNCERTAIN','NEEDS_PROOF_FROM_HIGHWATER_TO_NEW_CHECKPOINT')
    if body['root_sha256']!=hb['root_sha256']:
        return result('DENY','HTTP_FORK_AT_HIGHWATER_SIZE')
    # HISTORICAL proof only. No claim of freshness or independent admin.
    return result('HISTORICAL_CONSISTENT','HTTP_RESPONSES_MATCH_SYNTHETIC_RETAINED_HIGHWATER_NOT_WORLD_FRESHNESS')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--url',required=True)
    p.add_argument('--pinned-public-key-file')
    p.add_argument('--prior-file')
    p.add_argument('--highwater-file')
    args=p.parse_args()
    try:
        key=Path(args.pinned_public_key_file).read_text().strip() if args.pinned_public_key_file else None
        prior=json.loads(Path(args.prior_file).read_text(),object_pairs_hook=_no_dup) if args.prior_file else None
        hw=json.loads(Path(args.highwater_file).read_text(),object_pairs_hook=_no_dup) if args.highwater_file else None
        outcome=observe(args.url,pinned_key=key,prior=prior,highwater=hw)
    except (OSError,ValueError,TypeError,UnicodeDecodeError):
        outcome=result('HOLD_UNCERTAIN','LOCAL_TRUST_PIN_UNAVAILABLE_OR_INVALID')
    print(json.dumps(outcome,sort_keys=True))

if __name__=='__main__':main()
