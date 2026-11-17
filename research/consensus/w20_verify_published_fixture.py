#!/usr/bin/env python3
"""Offline read-only W20 fixture replay requiring explicit pinned key AND old head.

Supplying these values from the SAME GitHub repo is NOT independent trust.
They are separate CLI inputs to prevent silent trust in publisher-provided key.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import w20_independent_monitor as monitor


def strict_pairs(items):
    out={}
    for k,v in items:
        if k in out:
            raise ValueError('DUPLICATE_JSON_KEY:'+k)
        out[k]=v
    return out


def strict_file(path):
    if Path(path).stat().st_size > 120_000:
        raise ValueError('FILE_TOO_LARGE')
    return json.loads(Path(path).read_text('utf8'),object_pairs_hook=strict_pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--fixture',required=True)
    ap.add_argument('--prior',required=True,help='Retained trusted prior head from outside candidate publisher')
    ap.add_argument('--pinned-public-key-hex',required=True,help='Pinned trusted key from a separate authenticated route')
    args=ap.parse_args()
    f=strict_file(args.fixture)
    prior=strict_file(args.prior)
    observed=monitor.evaluate_bundle(f,args.pinned_public_key_hex,known_prior=prior)
    print(json.dumps(observed,sort_keys=True))
    return 0 if observed['verdict']=='HISTORICAL_CONSISTENT' else 2

if __name__=='__main__':
    raise SystemExit(main())
