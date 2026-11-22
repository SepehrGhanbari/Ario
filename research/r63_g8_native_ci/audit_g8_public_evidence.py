"""R63 G8 external read-only cross-language forensic audit of synthetic CI ZIP.

Independent from C# broker and PowerShell reporter; never executes archived
source or reads private key material. Uses pyca/cryptography for public-only
P256 ECDSA verification of both actor approvals and native public receipts.
CI Windows SID/process claims remain reporter-originated, not OS-attested.
"""
from __future__ import annotations
import base64
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import zipfile
from cryptography.hazmat.primitives.asymmetric import ec,utils
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature

VERSION='ARIO_R63_G8_DISPOSABLE_ONLY_V1'
EPOCH='research_nov_2026_no_signer'
BASE='6e1d74f7860e0173b9b049487a6a89428439a987809cf363fa27503ae0b06ea1'
NEXT='52e1f33cf8bcf325a2cb817abe16473aa2e6a799fc76406b8cf831b912fd6d8c'
EXPECTED_G7_PAYLOAD_SHA='11d19b0f8b2f83d11944856c0e7b29653f3112fd15cd85e35f80b005b3d31278'
VALID_CASES=('normal','before','after','receipt','veto','bad','revoked','rogue')


def sha(b):return hashlib.sha256(b).hexdigest()
def require(ok,why):
    if not ok:raise ValueError(why)

def public_from_windows_cng_blob(blob):
    require(len(blob)==72, 'HOLD_BAD_PUBLIC_BLOB_LENGTH')
    magic,size=struct.unpack('<II',blob[:8])
    require(magic==0x31534345 and size==32,'HOLD_BAD_ECC_P256_PUBLIC_BLOB')
    x=int.from_bytes(blob[8:40],'big');y=int.from_bytes(blob[40:72],'big')
    return ec.EllipticCurvePublicNumbers(x,y,ec.SECP256R1()).public_key()

def verify_p1363_blob(pub,msg,signature):
    require(len(signature)==64,'HOLD_BAD_P1363_SIGNATURE_LENGTH')
    r=int.from_bytes(signature[:32],'big');s=int.from_bytes(signature[32:],'big')
    sig=utils.encode_dss_signature(r,s)
    try:pub.verify(sig,msg,ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:return False
    return True

def actor_message(case,nonce,ident,role,decision,payload_sha):
    return (VERSION+'\n'+EPOCH+'\n'+BASE+'\n'+NEXT+'\n'+case+'\n'+nonce+'\n'+ident+'\n'+role+'\n'+decision+'\n'+payload_sha+'\n').encode('ascii')

def native_message(case,nonce,ident,payload_sha):
    return ('ARIO_R63_G8_NATIVE_SIGN_USE_V1\n'+EPOCH+'\n'+BASE+'\n'+NEXT+'\n'+case+'\n'+nonce+'\n'+ident+'\n'+payload_sha+'\n').encode('ascii')

def verify_members(z):
    require(z.testzip() is None,'HOLD_BAD_ZIP_CRC')
    names=z.namelist()
    require(len(names)==len(set(names)),'HOLD_DUPLICATE_ZIP_ENTRY')
    for n in names:
        p=Path(n)
        require(not n.startswith('/') and '\\' not in n and '..' not in p.parts and not n.endswith('/'),'HOLD_UNSAFE_ZIP_ENTRY')
    return {n:z.read(n) for n in names}

def audit(outer_path):
    if outer_path.is_dir():
        e={p.name:p.read_bytes() for p in outer_path.iterdir() if p.is_file()}
        outer_digest='EXTRACTED_ACTIONS_ARTIFACT'
    else:
        raw=outer_path.read_bytes()
        outer_digest=sha(raw)
        with zipfile.ZipFile(io.BytesIO(raw)) as outer:
            e=verify_members(outer)
    reports=[(n,b) for n,b in e.items() if n.endswith('.json') and n.startswith('r63-g8-native-report-')]
    archives=[(n,b) for n,b in e.items() if n.endswith('.zip') and n.startswith('r63-g8-native-evidence-')]
    require(len(reports)==1 and len(archives)==1,'HOLD_BAD_OUTER_ARTIFACT_LAYOUT')
    report=json.loads(reports[0][1]);require(type(report) is dict,'HOLD_BAD_REPORT')
    with zipfile.ZipFile(io.BytesIO(archives[0][1])) as z:
        data=verify_members(z)
    require('payload.bin' in data and 'payload.sha256' in data,'HOLD_MISSING_PAYLOAD')
    ph=sha(data['payload.bin'])
    require(ph==EXPECTED_G7_PAYLOAD_SHA,'HOLD_PAYLOAD_NOT_EXACT_G7_SOURCE')
    require(data['payload.sha256']==(ph+'\n').encode(),'HOLD_PAYLOAD_PIN_CHANGED')
    f_pub=public_from_windows_cng_blob(data['founder.pub'])
    a_pub=public_from_windows_cng_blob(data['ario.pub'])
    require(sha(data['founder.pub'])!=sha(data['ario.pub']),'HOLD_DUPLICATE_ACTOR_KEYS')
    results={};native_cnt=0
    for case in VALID_CASES:
        reqfile=case+'/request.txt'
        require(reqfile in data, 'HOLD_MISSING_FIXTURE_'+case)
        t=data[reqfile].decode('ascii').strip().split(' ')
        require(len(t)==8 and t[0]=='SIGN' and t[1]==case,'HOLD_BAD_CASE_INPUT_'+case)
        nonce,ident,decision=t[2],t[3],t[4]
        require(len(nonce)==64 and len(ident)==64,'HOLD_REQUEST_IDS_BAD')
        fsig=base64.b64decode(t[5],validate=True)
        asig=base64.b64decode(t[6],validate=True)
        founder=verify_p1363_blob(f_pub,actor_message(case,nonce,ident,'FOUNDER','ALLOW',ph),fsig)
        ario=verify_p1363_blob(a_pub,actor_message(case,nonce,ident,'ARIO',decision,ph),asig)
        require(founder==(case!='bad') and ario,'HOLD_ACTOR_SIGNATURE_VERDICT_'+case)
        require(decision==('VETO' if case=='veto' else 'ALLOW'),'HOLD_VETO_FLAG_MISMATCH')
        files={key:data.get(case+'/'+key) for key in ('use-intent.txt','native-enter.txt','native-return.txt','receipt-public.txt','public-pin.sha256')}
        if files['native-enter.txt'] is not None:
            require(files['native-enter.txt']==b'NCryptSignHash ENTER 1\n','HOLD_BAD_NATIVE_ENTRY_COUNT')
            native_cnt+=1
        if files['native-return.txt'] is not None:
            require(files['native-return.txt']==b'NCryptSignHash RETURN 1\n','HOLD_BAD_NATIVE_RETURN_COUNT')
        if files['use-intent.txt'] is not None:
            expected=('ARIO_R63_G8_DURABLE_INTENT_V1\n'+case+'\n'+nonce+'\n'+ident+'\n'+ph+'\n').encode('ascii')
            require(files['use-intent.txt']==expected,'HOLD_INTENT_NOT_BOUND_TO_SIGNED_INPUT')
        if files['receipt-public.txt'] is not None:
            b=files['receipt-public.txt'];line=b.decode('ascii').split('\n')
            require(len(line)==8 and line[0]=='ARIO_R63_G8_RECEIPT_V1' and line[1]=='case='+case and
                    line[2]=='nonce='+nonce and line[3]=='ident='+ident and line[4]=='payload_sha256='+ph and line[7]=='',
                    'HOLD_RECEIPT_CONTEXT_'+case)
            require(line[5].startswith('pub=') and line[6].startswith('sig='),'HOLD_BAD_RECEIPT_LAYOUT')
            rpub=base64.b64decode(line[5][4:],validate=True)
            rsig=base64.b64decode(line[6][4:],validate=True)
            require(files['public-pin.sha256']==(sha(rpub)+'\n').encode(),'HOLD_STORED_PUBLIC_PIN_MISMATCH')
            require(verify_p1363_blob(public_from_windows_cng_blob(rpub),native_message(case,nonce,ident,ph),rsig),
                    'HOLD_BAD_NATIVE_PUBLIC_SIGNATURE')
        results[case]={k.replace('.txt','').replace('.sha256',''):v is not None for k,v in files.items()}
    full=report.get('final_verdict')=='PASS_SYNTHETIC_G8_ONLY'
    if full:
        require(report.get('cleanup_verified') is True,'HOLD_CLEANUP_UNKNOWN')
        expected={'normal':(1,1,1,1),'before':(1,0,0,0),'after':(1,1,1,0),
                  'receipt':(1,1,1,1),'veto':(0,0,0,0),'bad':(0,0,0,0),'revoked':(0,0,0,0),'rogue':(0,0,0,0)}
        for case,tup in expected.items():
            x=results[case]
            actual=tuple(int(x[k]) for k in ('use-intent','native-enter','native-return','receipt-public'))
            require(actual==tup,'HOLD_WRONG_CRASH_STATE_'+case)
        require(native_cnt==3,'HOLD_WRONG_TOTAL_NATIVE_USE_COUNT')
        require(set(report.get('results',{}))==set(VALID_CASES)-{'rogue'},'HOLD_REPORT_CASE_SET')
        require(report.get('keys_removed_readback')=='G8_TEMP_CNG_KEYS_REMOVED=3','HOLD_KEY_CLEANUP_NOT_RECORDED')
        require(report.get('sids',{}).get('reader')!=report.get('sids',{}).get('rogue'),'HOLD_READER_ROGUE_SAME_SID')
        normal=report['results']['normal']
        require(normal['first']=='SIGNED_VERIFIED' and normal['same_public_bytes_replayed'] is True
                and normal['rogue_sid_holds'] is True,'HOLD_NORMAL_RPC_OUTCOME')
        require('G8_WRITER_OS_SID='+report['sids']['writer'] in normal['source_logs'], 'HOLD_WRITER_SID_LOG_MISSING')
        require('G8_CLIENT_OS_SID='+report['sids']['rogue'] in normal['source_logs'], 'HOLD_ROGUE_OS_SID_LOG_MISSING')
        require(normal['public_verifier'].endswith(sha(data['normal/receipt-public.txt'])),'HOLD_PUBLIC_VERIFIER_SHA_MISMATCH')
        for case in ('normal','veto','bad','revoked','before','after','receipt'):
            rr=report['results'][case]
            states=[rr['state']] if 'state' in rr else [rr['before'],rr['after']]
            for state in states:
                for kind,field in [('use-intent.txt','intent'),('native-enter.txt','native_enter'),
                                   ('native-return.txt','native_return'),('receipt-public.txt','receipt')]:
                    raw=data.get(case+'/'+kind)
                    require(state[field] is (raw is not None),'HOLD_STATE_REPORT_MISMATCH_'+case+'_'+kind)
                    if raw is not None:
                        require(state.get(kind+'_sha256')==sha(raw),'HOLD_REPORT_SHA_MISMATCH_'+case+'_'+kind)
            if case in ('before','after','receipt'):
                require(rr['before']==rr['after'],'HOLD_RESTART_MODIFIED_REPORTED_STATE_'+case)
                require(rr['crash_exit']==73 and rr['first_reply']=='NO_ACK' and rr['parent_pid']!=rr['recovery_pid'],
                        'HOLD_BAD_CRASH_TELEMETRY_'+case)
                expected_retry='EXACT_STORED_RECEIPT' if case=='receipt' else 'HOLD_UNCERTAIN'
                require(rr['retry']==expected_retry,'HOLD_BAD_RECOVERY_DISPOSITION_'+case)
            if case in ('veto','bad','revoked'):
                expectation={'veto':'HOLD_ARIO_VETO','bad':'HOLD_BAD_ACTOR_APPROVAL',
                             'revoked':'HOLD_REVOKED'}[case]
                require(rr['response']==expectation,'HOLD_NEGATIVE_AUTH_REPORT_'+case)
        candidate_source=Path(__file__).resolve().parent/'G8IntegratedBroker.cs'
        if candidate_source.is_file():
            native= candidate_source.read_bytes()
            candidates={sha(native)}
            if b'\r\n' not in native: candidates.add(sha(native.replace(b'\n',b'\r\n')))
            require(report.get('source_sha256') in candidates,'HOLD_WRONG_CHECKED_OUT_BROKER_SOURCE')
    return {'outer_sha256':outer_digest,'inner_sha256':sha(archives[0][1]),'run_id':report.get('run'),
           'operator_verdict':report.get('final_verdict'),'source_sha256':report.get('source_sha256'),
           'verified_actor_ecdsa':True,'verified_native_public_receipts':sum(v['receipt-public'] for v in results.values()),
           'archived_native_enter_files':native_cnt,'result':'PASS_CROSS_IMPLEMENTATION_BYTES_ONLY' if full else 'PARTIAL_HOLD',
           'limitations':'SAME_RUNNER_ADMIN_NO_INDEPENDENT_CUSTODY_OR_EXTERNAL_OS_TRACING',
           'cases':results}

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('USAGE: python audit_g8_public_evidence.py Actions-artifact.zip')
    print(json.dumps(audit(Path(sys.argv[1])),sort_keys=True,indent=2))
