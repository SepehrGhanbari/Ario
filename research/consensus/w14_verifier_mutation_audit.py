#!/usr/bin/env python3
"""W14 selected mutation sensitivity tests for *pure verifier only*.

This is NOT a re-run of four-UID Linux-DAC check for each mutant. It runs
only synthetic in-process cryptographic packets in disposable test memory.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types

PATH = Path(__file__).with_name('w14_uid_custody_lab.py')
SOURCE = PATH.read_text(encoding='utf8')
spec=importlib.util.spec_from_file_location('w14_original', PATH)
original=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=original
spec.loader.exec_module(original)

def fixtures(module):
    grant_k=module.Ed25519PrivateKey.generate()
    rev_k=module.Ed25519PrivateKey.generate()
    anchor_k=module.Ed25519PrivateKey.generate()
    def pub(k):
        return k.public_key().public_bytes(module.serialization.Encoding.Raw,module.serialization.PublicFormat.Raw).hex()
    trust={'grant':pub(grant_k),'revoker':pub(rev_k),'anchor':pub(anchor_k)}
    body={'version':1,'grant_id':'G1','principal':'TEST_USER','operation':'SEND','resource':'report-1',
          'destination':'review@example.invalid','not_before':100,'expires':200}
    g=module.sign(grant_k,module.DOMAINS['grant'],body)
    hb={'version':1,'epoch':0,'revoked':[],'previous_head_sha256':None}
    h=module.sign(rev_k,module.DOMAINS['revoker'],hb)
    ab={'version':1,'epoch':0,'head_sha256':module.sha(module.raw_json(h)),'prev_anchor_epoch':-1}
    a=module.sign(anchor_k,module.DOMAINS['anchor'],ab)
    return trust, g,h,a, {'principal':'TEST_USER','operation':'SEND','resource':'report-1',
                          'destination':'review@example.invalid'},(grant_k,rev_k,anchor_k)

def check_module(module):
    trust,g,h,a,c,keys=fixtures(module)
    grant_k,rev_k,anchor_k=keys
    out=[]
    def case(name,actual,expected):
        assert actual==expected,(name,actual,expected)
        out.append(name)
    f=lambda g1=g,h1=h,a1=a,c1=c,t=150:module.check_packets(trust,g1,h1,a1,c1,t)
    case('positive',f()['verdict'],'ELIGIBLE_FOR_SEPARATE_GATE')
    case('no_authority',f()['authority'],'NOT_ESTABLISHED')
    case('scope',f(c1={**c,'destination':'attacker@example.invalid'})['reason'],'GRANT_NOT_BOUND_TO_PROPOSED_SCOPE')
    case('expired',f(t=210)['reason'],'GRANT_EXPIRED_OR_NOT_YET')
    case('not_yet',f(t=99)['reason'],'GRANT_EXPIRED_OR_NOT_YET')
    modified_grant={'domain':g['domain'],'body':{**g['body'],'destination':'attacker@example.invalid'},'signature':g['signature']}
    case('tampered_grant',f(g1=modified_grant)['reason'],'GRANT_SIGNATURE_OR_DOMAIN')
    wrong_domain=module.sign(grant_k,'wrong-domain',g['body'])
    case('wrong_domain_grant',f(g1=wrong_domain)['reason'],'GRANT_SIGNATURE_OR_DOMAIN')
    hb={**h['body'],'revoked':['G1']}
    revoked=module.sign(rev_k,module.DOMAINS['revoker'],hb)
    rev_anchor=module.sign(anchor_k,module.DOMAINS['anchor'],{**a['body'],'head_sha256':module.sha(module.raw_json(revoked))})
    case('revoked',f(h1=revoked,a1=rev_anchor)['reason'],'GRANT_REVOKED')
    case('stale_revocation',f(h1=revoked)['reason'],'STALE_OR_UNANCHORED_HEAD')
    fake_anchor=module.sign(anchor_k,module.DOMAINS['anchor'],{**a['body'],'head_sha256':'0'*64})
    case('wrong_anchor_digest',f(a1=fake_anchor)['reason'],'STALE_OR_UNANCHORED_HEAD')
    fake_head={'domain':h['domain'],'body':{**h['body'],'epoch':1},'signature':h['signature']}
    case('tampered_head',f(h1=fake_head)['reason'],'REVOCATION_SIGNATURE_OR_DOMAIN')
    return out

baseline=check_module(original)
MUTANTS=[
 ('M01_DROP_GRANT_SCOPE', 'if any(grant[k] != candidate.get(k) for k in ("principal", "operation", "resource", "destination")):', 'if False:'),
 ('M02_DROP_REVOKE', 'if grant["grant_id"] in head["revoked"]:', 'if False:'),
 ('M03_DROP_ANCHOR_HASH', 'anchor["head_sha256"] != sha(raw_json(head_packet))', 'False'),
 ('M04_IGNORE_GRANT_TIME', 'if not grant["not_before"] <= now < grant["expires"]:', 'if False:'),
 ('M05_RETURN_PERMISSION', '"authority": "NOT_ESTABLISHED"', '"authority": "GRANTED"'),
 ('M06_ALLOW_BAD_SIGNATURE', 'except (ValueError, InvalidSignature, TypeError):\n        return None', 'except (ValueError, InvalidSignature, TypeError):\n        return signed["body"]'),
 ('M07_CROSS_SIGNER_KEY', 'verify(trust["grant"], DOMAINS["grant"], grant_packet)', 'verify(trust["revoker"], DOMAINS["grant"], grant_packet)'),
 ('M08_ACCEPT_OTHER_ROLE_DOMAIN', 'signed["domain"] != expected_domain', 'False'),
 ('M10_SKIP_ANCHOR_SIGNATURE', 'verify(trust["anchor"], DOMAINS["anchor"], anchor_packet)', 'verify(trust["grant"], DOMAINS["anchor"], anchor_packet)'),
]
results=[]
for name,old,new in MUTANTS:
    n=SOURCE.count(old)
    assert n==1,(name,'match_count',n)
    code=SOURCE.replace(old,new,1)
    assert code!=SOURCE
    module=types.ModuleType('w14_mutant_'+name)
    # Only safe to compile and call the pure verifier on no-IO synthetic inputs.
    exec(compile(code, '<w14 '+name+'>','exec'),module.__dict__)
    try:
        check_module(module)
    except (AssertionError,TypeError,ValueError) as e:
        killed=True
        failure=str(e)[:240]
    else:
        killed=False
        failure=None
    results.append({'mutant':name,'mutated_sha256':hashlib.sha256(code.encode()).hexdigest(),
                    'detected':killed,'failed_case_or_reason':failure})
report={'schema':'ARIO_W14_PURE_VERIFIER_MUTATIONS_V1',
    'tested_source_git_blob':hashlib.sha1(b'blob '+str(len(SOURCE.encode())).encode()+b'\0'+SOURCE.encode()).hexdigest(),
    'pure_controls':len(baseline),'selected_mutants':len(results),
    'killed':sum(x['detected'] for x in results),'survived':sum(not x['detected'] for x in results),
    'mutants':results,'native_os_uid_tests_rerun_per_mutant':False,
    'independent_test_author_oracle':False,'real_actions':0,
    'scope':'Only toy in-memory signed verifier, never real keys, OS custody, production code or main branch.'}
print(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True))
