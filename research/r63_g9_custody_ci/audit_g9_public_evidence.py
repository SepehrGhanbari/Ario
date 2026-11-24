"""Public-only independent G9 audit. No archived code executed; no private keys.
OS-token/DACL and exact NCryptSignHash call counts remain runner-reported.
"""
from __future__ import annotations
import base64,hashlib,io,json,re,struct,sys,zipfile
from pathlib import Path,PurePosixPath
from cryptography.hazmat.primitives.asymmetric import ec,utils
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature

EPOCH='research_nov_2026_no_signer'
BASE='6e1d74f7860e0173b9b049487a6a89428439a987809cf363fa27503ae0b06ea1'
NEXT='52e1f33cf8bcf325a2cb817abe16473aa2e6a799fc76406b8cf831b912fd6d8c'
VERSION='ARIO_R63_G9_DISPOSABLE_ONLY_V1'

def sha(b):return hashlib.sha256(b).hexdigest()
def need(ok,why):
    if not ok:raise ValueError(why)
def members(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        need(z.testzip() is None,'HOLD_ZIP_CRC')
        names=z.namelist()
        need(len(names)==len(set(names)),'HOLD_DUPLICATE_MEMBER')
        for n in names:
            p=PurePosixPath(n)
            need(not n.startswith('/') and not n.endswith('/') and '\\' not in n and '..' not in p.parts,'HOLD_BAD_ZIP_PATH')
        return {n:z.read(n) for n in names}
def p256(blob):
    need(len(blob)==72,'HOLD_P256_BLOB_LENGTH')
    magic,size=struct.unpack('<II',blob[:8])
    need(magic==0x31534345 and size==32,'HOLD_CNG_MAGIC')
    return ec.EllipticCurvePublicNumbers(int.from_bytes(blob[8:40],'big'),
                                         int.from_bytes(blob[40:72],'big'),
                                         ec.SECP256R1()).public_key()
def signed(pub,msg,raw):
    need(len(raw)==64,'HOLD_P1363_LEN')
    sig=utils.encode_dss_signature(int.from_bytes(raw[:32],'big'),int.from_bytes(raw[32:],'big'))
    try:pub.verify(sig,msg,ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:return False
    return True
def actor_message(case,nonce,ident,role,decision,ph):
    return ('\n'.join((VERSION,EPOCH,BASE,NEXT,case,nonce,ident,role,decision,ph,''))).encode('ascii')
def cng_message(case,nonce,ident,ph):
    return ('\n'.join(('ARIO_R63_G9_NATIVE_SIGN_USE_V1',EPOCH,BASE,NEXT,case,nonce,ident,ph,''))).encode('ascii')
def verify_receipt(raw,case,nonce,ident,ph):
    s=raw.decode('ascii').split('\n')
    need(len(s)==8 and s[0]=='ARIO_R63_G9_RECEIPT_V1' and
         s[1]=='case='+case and s[2]=='nonce='+nonce and s[3]=='ident='+ident and
         s[4]=='payload_sha256='+ph and s[5].startswith('pub=') and
         s[6].startswith('sig=') and s[7]=='','HOLD_RECEIPT_ENVELOPE')
    pub=base64.b64decode(s[5][4:],validate=True)
    sig=base64.b64decode(s[6][4:],validate=True)
    need(signed(p256(pub),cng_message(case,nonce,ident,ph),sig),'HOLD_INVALID_NATIVE_SIGNATURE')
    return pub

def audit_data(r,d):
    required={'payload.bin','payload.sha256','founder.pub','ario.pub','normal/request.txt',
              'observer/first-receipt-public.txt','normal/receipt-public.txt',
              'normal/public-pin.sha256','normal/native-enter.txt','normal/native-return.txt',
              'normal/use-intent.txt'}
    need(required.issubset(d),'HOLD_MISSING_REQUIRED_FILE')
    need(r.get('final_verdict')=='PASS_SYNTHETIC_G9_EXPECTED_SHARED_ADMIN_RED','HOLD_CI_VERDICT')
    need(r.get('cleanup_verified') is True and r.get('independent_admin')=='NOT_ESTABLISHED','HOLD_FALSE_CUSTODY_CLAIM')
    need(r.get('real_ario_key')=='NOT_USED' and r.get('native_v9_signer')=='NOT_EXECUTED','HOLD_REAL_KEY_CLAIM')
    need(r.get('phone_floor')=='SEQ3_UNCHANGED' and r.get('latest_seq4')=='NOT_APPROVED','HOLD_FLOOR_PROMOTION_CLAIM')
    ph=sha(d['payload.bin'])
    need(d['payload.sha256']==(ph+'\n').encode('ascii') and
         r.get('g7_source_bound_payload_sha256')==ph,'HOLD_PAYLOAD_PIN')
    f=p256(d['founder.pub']);a=p256(d['ario.pub'])
    need(d['founder.pub']!=d['ario.pub'],'HOLD_DUPLICATE_ACTORS')
    req=d['normal/request.txt'].decode('ascii').strip().split(' ')
    need(len(req)==8 and req[0:2]==['SIGN','normal'] and req[4]=='ALLOW' and
         req[7]=='CLAIMED_READER','HOLD_REQUEST')
    cas,nonce,ident=req[1:4]
    need(bool(re.fullmatch('[a-f0-9]{64}',nonce)) and bool(re.fullmatch('[a-f0-9]{64}',ident)),'HOLD_ID_FORMAT')
    need(signed(f,actor_message(cas,nonce,ident,'FOUNDER','ALLOW',ph),
                base64.b64decode(req[5],validate=True)),'HOLD_FOUNDER_APPROVAL')
    need(signed(a,actor_message(cas,nonce,ident,'ARIO','ALLOW',ph),
                base64.b64decode(req[6],validate=True)),'HOLD_ARIO_APPROVAL')
    old=d['observer/first-receipt-public.txt'];new=d['normal/receipt-public.txt']
    op=verify_receipt(old,cas,nonce,ident,ph)
    np=verify_receipt(new,cas,nonce,ident,ph)
    need(op==np,'HOLD_CNG_PUBLIC_KEY_CHANGED')
    need(d['normal/public-pin.sha256']==(sha(np)+'\n').encode(),'HOLD_PUBLIC_PIN')
    need(d['normal/native-enter.txt']==b'NCryptSignHash ENTER 1\n' and
         d['normal/native-return.txt']==b'NCryptSignHash RETURN 1\n','HOLD_NATIVE_EVENT_MARKER')
    intent=('ARIO_R63_G9_DURABLE_INTENT_V1\n'+cas+'\n'+nonce+'\n'+ident+'\n'+ph+'\n').encode()
    need(d['normal/use-intent.txt']==intent,'HOLD_INTENT_CONTEXT')
    token=sha(('ARIO-R63/G9/CONSUME/v1|'+EPOCH+'|'+BASE+'|'+NEXT+'|'+cas+'|'+nonce+'|'+ident+'|'+ph).encode())
    marker='custody-final-public-snapshot/'+token+'.used'
    need(marker in d,'HOLD_NO_EXACT_CUSTODY_TOKEN')
    need(d[marker]==('G9_SYNTHETIC_SPENT\n'+token+'\n').encode(),'HOLD_CUSTODY_TOKEN_CORRUPTED')
    good=r['results']['OS_SEPARATE_FLOOR'];red=r['results']['SHARED_ADMIN_RED']
    need(good['retry']=='HOLD_EXTERNAL_SPENT' and good['no_second_CNG_call'] is True and
         good['writer_direct_custody_write']=='ACCESS_DENIED','HOLD_MISSING_CUSTODY_PROTECTION')
    need(good['kept_custody_marker_sha256']==sha(d[marker]),'HOLD_MARKER_HASH')
    need(good['local_rollback']==dict.fromkeys(('intent','native_enter','native_return','receipt'),False),'HOLD_MISSING_ROLLBACK')
    need(red['decision']=='RED_COMMON_ADMIN_CAN_RESIGN_AFTER_ERASING_ALL_LOCAL_USE_STATE' and
         red['native_enter_observed_in_two_broker_processes']==2 and
         red['two_public_receipts_verified'] is True and
         red['same_native_CNG_public_pin'] is True,'HOLD_UNREPORTED_RED')
    need(red['first_receipt_sha256']==good['first_public_receipt_sha256']==sha(old),'HOLD_FIRST_RECEIPT_HASH')
    need(red['second_receipt_sha256']==sha(new),'HOLD_SECOND_RECEIPT_HASH')
    trace=r['custody_trace']
    need(trace.count('RESPONSE=G9_CUSTODY_GRANTED')==2 and
         trace.count('RESPONSE=HOLD_EXTERNAL_SPENT')==1 and
         trace.count('G9_CUSTODY_PEER='+r['sids']['writer'])==3,'HOLD_CUSTODY_TRACE')
    return {'status':'PASS_PUBLIC_BYTES_AND_ECDSA','actor_signatures_verified':2,
            'native_public_receipts_verified':2,
            'native_call_count':'RUNNER_REPORTED_NOT_INDEPENDENTLY_INSTRUMENTED',
            'separate_sid_custody':'OS_TOKEN_GATE_RUNNER_REPORTED',
            'publisher_only_rollback':'HOLD_EXTERNAL_SPENT',
            'same_admin_both_histories_rollback':'RED_RE_SIGN',
            'independent_admin_latest':'NOT_ESTABLISHED','production':'NO_GO',
            'first_receipt_sha256':sha(old),'second_receipt_sha256':sha(new)}
def audit(path):
    p=Path(path)
    # Supports Action's extracted artifact folder or its ZIP
    if p.is_dir():o={f.name:f.read_bytes() for f in p.iterdir() if f.is_file()}
    else:o=members(p.read_bytes())
    reports=[n for n in o if n.startswith('r63-g9-native-report-') and n.endswith('.json')]
    evidences=[n for n in o if n.startswith('r63-g9-native-evidence-') and n.endswith('.zip')]
    need(len(reports)==1 and len(evidences)==1 and len(o)==2,'HOLD_ARTIFACT_LAYOUT')
    r=json.loads(o[reports[0]])
    d=members(o[evidences[0]])
    result=audit_data(r,d)
    result['evidence_sha256']=sha(o[evidences[0]])
    return result

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: audit_g9_public_evidence.py ARTIFACT_DIRECTORY_OR_ZIP')
    print(json.dumps(audit(sys.argv[1]),sort_keys=True,indent=2))
