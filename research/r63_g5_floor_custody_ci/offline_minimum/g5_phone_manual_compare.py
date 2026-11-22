"""Research-only manual two-device minimum-floor comparison.

The reference MUST be read by a person from a separate device. This tool
cannot attest provenance or prevent the desktop administrator from replacing
its code, input, or output. It never authorizes signing or advances a floor.
"""
from __future__ import annotations
import argparse, json, re, hashlib
from pathlib import Path
from g5_retained_floor import verify_local

def compare(v1:bytes, v2:bytes, *, reference_seq:int|None, reference_head:str|None):
    if reference_seq is None or reference_head is None:
        return 'HOLD_NO_SEPARATE_REFERENCE'
    if type(reference_seq) is not int or reference_seq<1 or not isinstance(reference_head,str) or not re.fullmatch('[a-f0-9]{64}',reference_head):
        return 'HOLD_INVALID_SEPARATE_REFERENCE'
    try:
        seq,head,unused=verify_local(v1,v2)
    except (ValueError,TypeError,OverflowError,UnicodeError,RecursionError):
        return 'HOLD_LOCAL_JOURNAL_INVALID'
    if seq < reference_seq:
        return 'HOLD_ROLLBACK'
    # A future extension must contain the pinned head at the retained index,
    # not merely have a sequence greater than or equal to the phone minimum.
    from g5_retained_floor import rows
    original_rows=rows(v2)
    if original_rows[reference_seq-1]['hash']!=reference_head:
        return 'HOLD_FORK'
    return 'CONSISTENT_WITH_RETAINED_HISTORICAL_MINIMUM_NOT_LATEST'

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--v1',type=Path,required=True)
    ap.add_argument('--v2',type=Path,required=True)
    ap.add_argument('--reference-seq',type=int)
    ap.add_argument('--reference-head')
    ap.add_argument('--output',type=Path)
    ns=ap.parse_args()
    raw1,raw2=ns.v1.read_bytes(),ns.v2.read_bytes()
    outcome=compare(raw1,raw2,reference_seq=ns.reference_seq,reference_head=ns.reference_head)
    result={
        'schema':'ARIO_G5_MANUAL_PHONE_NOTE_COMPARISON_RESEARCH_V1',
        'verdict':outcome,
        'candidate_v1_sha256':hashlib.sha256(raw1).hexdigest(),
        'candidate_v2_sha256':hashlib.sha256(raw2).hexdigest(),
        'reference_origin':'CALLER_SUPPLIED_UNVERIFIED__PHONE_ORIGIN_NOT_ATTESTED',
        'hardware_separation':'FOUNDER_REPORTED_NOT_FORENSICALLY_ATTESTED',
        'phone_contents_cryptographically_verified':False,
        'automatic_external_latest_custody':'NOT_ESTABLISHED',
        'authorization':'NONE','real_ario_signer':'NOT_TOUCHED','production':'NO_GO',
    }
    if ns.output:
        if ns.output.exists():raise SystemExit('REFUSE_OVERWRITE_REPORT')
        ns.output.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,sort_keys=True))
    # Positive historical consistency is not signing authority.
    raise SystemExit(0 if outcome=='CONSISTENT_WITH_RETAINED_HISTORICAL_MINIMUM_NOT_LATEST' else 2)
if __name__=='__main__':main()
